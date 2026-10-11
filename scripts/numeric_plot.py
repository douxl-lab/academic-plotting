#!/usr/bin/env python3
"""Offline quantitative plotting with explicit units, repeat semantics and provenance.

Usage: python numeric_plot.py --data measurements.csv --spec plot-spec.json
                             --style style.json --output NEW_DIRECTORY
Input CSV columns: series,x,replicate,value. No input code is executed.
Charts: line, bar, hbar, scatter, heatmap, box, violin. Synthetic fixtures are marked.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


class PlotValidationError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PlotValidationError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda x: (_ for _ in ()).throw(PlotValidationError(f"Nonfinite JSON: {x}")))
        canonical(value)
        return value
    except (ValueError, TypeError, RecursionError) as exc:
        raise PlotValidationError(f"Invalid strict JSON: {exc}") from exc


def keys(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= set(obj) or set(obj) - set(required) - set(optional):
        raise PlotValidationError(f"Expected fields {list(required)}; optional {list(optional)}")


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise PlotValidationError(f"{field} must be nonempty text")
    return value


def number(value, field):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise PlotValidationError(f"{field} must be a finite number")
    return float(value)


def no_links(path):
    """Reject symlinks and Windows junction/reparse points, including ancestors."""
    import stat
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink():
            raise PlotValidationError(f"Path traverses a symlink: {item}")
        if item.exists():
            attrs = getattr(item.lstat(), "st_file_attributes", 0)
            if attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise PlotValidationError(f"Path traverses a reparse point: {item}")
    return path


# Conversion is deliberately explicit and linear. Unknown conversions fail.
UNITS = {
    "1": ("ratio", 1.0), "%": ("ratio", .01),
    "mm": ("length", .001), "cm": ("length", .01), "m": ("length", 1.0),
    "ms": ("time", .001), "s": ("time", 1.0),
    "count": ("count", 1.0), "epoch": ("epoch", 1.0), "step": ("step", 1.0),
}


def unit_factor(source, target):
    text(source, "unit"); text(target, "display_unit")
    if source == target:
        return 1.0
    if source not in UNITS or target not in UNITS or UNITS[source][0] != UNITS[target][0]:
        raise PlotValidationError(f"Unsupported unit conversion: {source} -> {target}")
    return UNITS[source][1] / UNITS[target][1]


def validate_spec(spec):
    keys(spec, ("schema_version", "chart", "source", "x", "metric", "series_order", "x_order", "repeats"))
    if spec["schema_version"] != "1.0.0" or spec["chart"] not in ("line", "bar", "hbar", "scatter", "heatmap", "box", "violin"):
        raise PlotValidationError("Unsupported plot specification version or chart")
    keys(spec["source"], ("sha256", "title", "uri", "license", "citation", "data_role"),
         ("original_sha256", "original_filename", "derivation", "dataset_variant"))
    import re
    if not isinstance(spec["source"]["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", spec["source"]["sha256"]):
        raise PlotValidationError("Source SHA-256 required")
    if spec["source"]["data_role"] not in ("measured", "public_observations", "synthetic_fixture"):
        raise PlotValidationError("Declare data_role: measured, public_observations, or synthetic_fixture")
    for field in ("title", "uri", "license", "citation"):
        text(spec["source"][field], field)
    for field in ("original_filename", "derivation", "dataset_variant"):
        if field in spec["source"]:
            text(spec["source"][field], field)
    if "original_sha256" in spec["source"] and not re.fullmatch("[0-9a-f]{64}", spec["source"]["original_sha256"]):
        raise PlotValidationError("Original source SHA-256 invalid")
    keys(spec["x"], ("label", "unit", "display_unit", "scale"))
    keys(spec["metric"], ("name", "kind", "unit", "display_unit", "direction", "scale"), ("valid_min", "valid_max"))
    for obj, fields in ((spec["x"], ("label",)), (spec["metric"], ("name",))):
        for field in fields:
            text(obj[field], field)
    for axis in (spec["x"], spec["metric"]):
        if axis["scale"] not in ("linear", "log"):
            raise PlotValidationError("Scale must be linear or log")
        unit_factor(axis["unit"], axis["display_unit"])
    metric = spec["metric"]
    if metric["direction"] not in ("higher", "lower", "descriptive") or metric["kind"] not in ("accuracy", "length", "time", "generic"):
        raise PlotValidationError("Metric kind/direction invalid")
    if metric["kind"] == "accuracy" and metric["unit"] not in ("1", "%"):
        raise PlotValidationError("Accuracy must declare fraction (1) or percent (%)")
    if metric["kind"] in ("length", "time") and (metric["unit"] not in UNITS or UNITS[metric["unit"]][0] != metric["kind"]):
        raise PlotValidationError("Metric kind disagrees with its unit")
    for field in ("valid_min", "valid_max"):
        if field in metric:
            number(metric[field], field)
    if metric.get("valid_min", -math.inf) > metric.get("valid_max", math.inf):
        raise PlotValidationError("Metric bounds reversed")
    for field in ("series_order", "x_order"):
        order = spec[field]
        if not isinstance(order, list) or not order or any(not isinstance(v, str) or not v.strip() for v in order) or len(set(order)) != len(order):
            raise PlotValidationError(f"{field} must contain unique nonempty string labels")
    keys(spec["repeats"], ("basis", "unit", "uncertainty", "assume_iid", "limitations"))
    repeats = spec["repeats"]
    if repeats["basis"] not in ("independent_runs", "observations", "single") or repeats["uncertainty"] not in ("none", "sd", "se", "ci95") or type(repeats["assume_iid"]) is not bool:
        raise PlotValidationError("Invalid repeated-measurement semantics")
    text(repeats["unit"], "repeat unit"); text(repeats["limitations"], "statistical limitations")
    if repeats["uncertainty"] in ("se", "ci95") and not repeats["assume_iid"]:
        raise PlotValidationError("SE/CI require an explicit i.i.d. assumption; dependent folds/steps are unsupported")
    if repeats["basis"] == "single" and repeats["uncertainty"] != "none":
        raise PlotValidationError("Single measurements cannot have invented error bars")
    if spec["chart"] in ("scatter", "box", "violin", "heatmap") and repeats["uncertainty"] != "none":
        raise PlotValidationError("Scatter, distribution and heatmap charts do not invent error bars; set uncertainty=none")
    if spec["chart"] in ("box", "violin") and repeats["basis"] == "single":
        raise PlotValidationError("A distribution requires original repeated observations")
    if spec["chart"] in ("bar", "hbar", "heatmap", "box", "violin"):
        if spec["x"]["unit"] != "1" or spec["x"]["display_unit"] != "1" or spec["x"]["scale"] != "linear":
            raise PlotValidationError("Categorical axes require unit=display_unit=1 and a linear scale")
    if spec["chart"] in ("bar", "hbar", "heatmap", "box", "violin") and metric["scale"] != "linear":
        raise PlotValidationError("This categorical helper supports a linear metric only; no hidden log baseline")
    return spec


def validate_style(style):
    keys(style, ("schema_version", "width_in", "height_in", "dpi", "font", "font_size", "palette", "markers", "linestyles"))
    if style["schema_version"] != "1.0.0":
        raise PlotValidationError("Unsupported style specification")
    for field in ("width_in", "height_in", "dpi", "font_size"):
        if number(style[field], field) <= 0:
            raise PlotValidationError(f"{field} must be positive")
    if style["dpi"] < 300 or style["font_size"] < 7:
        raise PlotValidationError("Publication style requires >=300 DPI and >=7pt base font")
    pixels = round(style["width_in"] * style["dpi"]) * round(style["height_in"] * style["dpi"])
    if style["width_in"] > 20 or style["height_in"] > 20 or style["dpi"] > 1200 or pixels > 64_000_000:
        raise PlotValidationError("Figure dimensions exceed the 64-megapixel resource limit")
    text(style["font"], "font")
    import re
    if not isinstance(style["palette"], list) or not style["palette"] or any(not isinstance(c, str) or not re.fullmatch("#[0-9A-Fa-f]{6}", c) for c in style["palette"]):
        raise PlotValidationError("Style requires hex colors")
    for field, allowed in (("markers", ("o", "s", "^", "D", "v", "P", "X")), ("linestyles", ("-", "--", "-.", ":"))):
        if not isinstance(style[field], list) or not style[field] or any(v not in allowed for v in style[field]):
            raise PlotValidationError(f"Unsupported {field}")
    return style


def read_data(raw, spec):
    if digest(raw) != spec["source"]["sha256"]:
        raise PlotValidationError("Raw source CSV checksum mismatch")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        if reader.fieldnames != ["series", "x", "replicate", "value"]:
            raise PlotValidationError("CSV must have exact ordered columns series,x,replicate,value")
        rows = []
        seen = set()
        for line, row in enumerate(reader, 2):
            if set(row) != set(reader.fieldnames) or any(v is None or not v.strip() for v in row.values()):
                raise PlotValidationError(f"Missing/extra CSV fields at line {line}")
            if row["series"] not in spec["series_order"] or row["x"] not in spec["x_order"]:
                raise PlotValidationError(f"Unknown series/x at line {line}; no silent reorder or omission")
            identity = (row["series"], row["x"], row["replicate"])
            if identity in seen:
                raise PlotValidationError(f"Duplicate replicate identity at line {line}")
            seen.add(identity)
            value = float(row["value"])
            if not math.isfinite(value):
                raise PlotValidationError(f"Nonfinite value at line {line}")
            metric = spec["metric"]
            low = metric.get("valid_min", 0 if metric["kind"] in ("accuracy", "length", "time") else -math.inf)
            high = metric.get("valid_max", (1 if metric["unit"] == "1" else 100) if metric["kind"] == "accuracy" else math.inf)
            # Explicit bounds cannot relax an accuracy metric's natural range.
            if metric["kind"] == "accuracy" and not 0 <= value <= (1 if metric["unit"] == "1" else 100):
                raise PlotValidationError("Accuracy value disagrees with fraction/percent unit")
            if not low <= value <= high:
                raise PlotValidationError(f"Value outside metric range at line {line}")
            if spec["chart"] in ("line", "scatter"):
                x = float(row["x"])
                if not math.isfinite(x):
                    raise PlotValidationError("Nonfinite x value")
            rows.append({**row, "value": value})
    except (UnicodeError, csv.Error, ValueError) as exc:
        raise PlotValidationError(str(exc)) from exc
    if not rows:
        raise PlotValidationError("CSV contains no observations")
    if {r["series"] for r in rows} != set(spec["series_order"]) or {r["x"] for r in rows} != set(spec["x_order"]):
        raise PlotValidationError("Declared ordering must exactly match source series/x")
    if spec["chart"] == "line":
        ordered = [float(x) for x in spec["x_order"]]
        if any(b <= a for a, b in zip(ordered, ordered[1:])):
            raise PlotValidationError("Line x_order must be strictly increasing; sorting needs an explicit spec change")
    return rows


def aggregate(rows, spec):
    """Explicit arithmetic summaries; scatter retains every original pair."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["series"], row["x"]].append(row)
    repeats = spec["repeats"]
    scale = unit_factor(spec["metric"]["unit"], spec["metric"]["display_unit"])
    xscale = unit_factor(spec["x"]["unit"], spec["x"]["display_unit"])
    result = []
    for series in spec["series_order"]:
        for xi, x in enumerate(spec["x_order"]):
            cell = grouped.get((series, x), [])
            if not cell and spec["chart"] == "scatter":
                continue  # Scatter is not a fabricated rectangular data grid.
            if not cell:
                raise PlotValidationError(f"Missing series/x cell: {series}/{x}")
            if spec["chart"] == "scatter":
                for row in cell:
                    point = {"series": series, "x_label": x, "replicate": row["replicate"], "x": float(x)*xscale,
                             "n": 1, "mean_raw": row["value"], "sd_raw": None, "se_raw": None,
                             "y": row["value"]*scale, "low": row["value"]*scale, "high": row["value"]*scale}
                    result.append(point)
                continue
            values = [r["value"] for r in cell]
            n = len(values)
            if repeats["basis"] == "single" and n != 1:
                raise PlotValidationError("Single-measurement basis contains repeats")
            if repeats["uncertainty"] != "none" and n < 2:
                raise PlotValidationError("SD/SE/CI require >=2 original repeated observations per cell")
            if spec["chart"] in ("box", "violin") and n < 2:
                raise PlotValidationError("Distribution charts require >=2 original observations per cell")
            if spec["chart"] == "violin" and len(set(values)) < 2:
                raise PlotValidationError("KDE violin requires nonconstant original observations; use box instead")
            mean = float(np.mean(values))
            sd = float(np.std(values, ddof=1)) if n >= 2 else None
            se = sd / math.sqrt(n) if sd is not None else None
            uncertainty = repeats["uncertainty"]
            half = {"none": 0., "sd": sd, "se": se}.get(uncertainty)
            if uncertainty == "ci95":
                half = float(stats.t.ppf(.975, n - 1)) * se
            point = {"series": series, "x_label": x, "x": float(x)*xscale if spec["chart"] == "line" else xi,
                     "n": n, "mean_raw": mean, "sd_raw": sd, "se_raw": se,
                     "y": mean*scale, "low": (mean-half)*scale, "high": (mean+half)*scale}
            if spec["chart"] in ("box", "violin"):
                displayed = np.asarray(values)*scale
                q1, median, q3 = np.quantile(displayed, [.25, .5, .75], method="linear")
                iqr = q3-q1
                inside = displayed[(displayed >= q1-1.5*iqr) & (displayed <= q3+1.5*iqr)]
                point.update(values_raw=values, replicates=[r["replicate"] for r in cell],
                             median=float(median), q1=float(q1), q3=float(q3),
                             whisker_low=float(min(inside)), whisker_high=float(max(inside)),
                             fliers=displayed[(displayed < min(inside)) | (displayed > max(inside))].tolist())
            result.append(point)
    for point in result:
        if any(not math.isfinite(point[key]) for key in ("x", "y", "low", "high")):
            raise PlotValidationError("Numeric transformation overflow; no nonfinite artist coordinates")
        if spec["x"]["scale"] == "log" and point["x"] <= 0:
            raise PlotValidationError("Log x requires positive original x values")
        if spec["metric"]["scale"] == "log" and min(point["y"], point["low"]) <= 0:
            raise PlotValidationError("Log y requires positive points and uncertainty bounds; no clipping")
    return result


def draw(points, spec, style):
    """Check coordinates on real Matplotlib artists, not fabricated test records."""
    validate_style(style)
    with plt.rc_context({"font.family": style["font"], "font.size": style["font_size"],
                         "axes.spines.top": False, "axes.spines.right": False,
                         "legend.frameon": False, "pdf.fonttype": 42, "svg.fonttype": "none"}):
        fig, ax = plt.subplots(figsize=(style["width_in"], style["height_in"]), layout="constrained")
        actual = []
        chart = spec["chart"]
        if chart == "heatmap":
            matrix = np.asarray([[p["y"] for p in points if p["series"] == s] for s in spec["series_order"]])
            artist = ax.imshow(matrix, aspect="auto", cmap="cividis", interpolation="nearest")
            np.testing.assert_allclose(np.asarray(artist.get_array()), matrix, rtol=1e-12, atol=1e-12)
            actual = [{"series": s, "x": [p["x"] for p in points if p["series"] == s],
                       "y": np.asarray(artist.get_array())[i].tolist(), "uncertainty_bounds": []}
                      for i, s in enumerate(spec["series_order"])]
            # pcolormesh keeps the heatmap cells vector-editable in SVG/PDF.
            artist.remove()
            mesh = ax.pcolormesh(np.arange(matrix.shape[1]+1)-.5, np.arange(matrix.shape[0]+1)-.5,
                                 matrix, cmap="cividis", shading="flat", rasterized=False)
            np.testing.assert_allclose(np.asarray(mesh.get_array()).reshape(matrix.shape), matrix)
            ax.set_ylim(matrix.shape[0]-.5, -.5)
            ax.set_xticks(range(len(spec["x_order"])), spec["x_order"])
            ax.set_yticks(range(len(spec["series_order"])), spec["series_order"])
            for i in range(matrix.shape[0]):
                for j in range(matrix.shape[1]):
                    v=float(matrix[i,j]); midpoint=(float(matrix.min())+float(matrix.max()))/2
                    ax.text(j, i, f"{v:.3g}", ha="center", va="center", color="white" if v<midpoint else "black")
            cbar=fig.colorbar(mesh, ax=ax, label=f'{spec["metric"]["name"]} ({spec["metric"]["display_unit"]})')
            if cbar.solids is not None: cbar.solids.set_rasterized(False)
        else:
            for i, series in enumerate(spec["series_order"]):
                data = [p for p in points if p["series"] == series]
                x = np.array([p["x"] for p in data]); y = np.array([p["y"] for p in data])
                low = np.array([p["low"] for p in data]); high = np.array([p["high"] for p in data])
                color = style["palette"][i % len(style["palette"])]
                width = .8 / len(spec["series_order"])
                offset = (i - (len(spec["series_order"])-1)/2)*width
                bounds=[]; distributions=[]
                if chart in ("bar", "hbar"):
                    if chart == "bar":
                        bars=ax.bar(x+offset, y, width*.9, label=series, color=color,
                                    hatch=("", "//", "xx", "..")[i%4], edgecolor="#333333", linewidth=.4)
                        artist_x=np.asarray([b.get_x()+b.get_width()/2-offset for b in bars])
                        artist_y=np.asarray([b.get_height() for b in bars])
                    else:
                        bars=ax.barh(x+offset, y, width*.9, label=series, color=color,
                                     hatch=("", "//", "xx", "..")[i%4], edgecolor="#333333", linewidth=.4)
                        artist_x=np.asarray([b.get_y()+b.get_height()/2-offset for b in bars])
                        artist_y=np.asarray([b.get_width() for b in bars])
                    ex=x+offset
                elif chart == "scatter":
                    artist=ax.scatter(x,y,label=series,color=color,marker=style["markers"][i%len(style["markers"])],s=25)
                    artist_x,artist_y=np.asarray(artist.get_offsets()).T; ex=x
                elif chart in ("box", "violin"):
                    values=[np.asarray(p["values_raw"])*unit_factor(spec["metric"]["unit"],spec["metric"]["display_unit"]) for p in data]
                    if chart == "box":
                        artists=ax.boxplot(values, positions=x+offset, widths=width*.8, patch_artist=True,
                                           manage_ticks=False, whis=1.5, showfliers=True)
                        for box in artists["boxes"]: box.set_facecolor(color); box.set_alpha(.7)
                        for j,p in enumerate(data):
                            median=float(artists["medians"][j].get_ydata()[0])
                            verts=artists["boxes"][j].get_path().vertices
                            q1,q3=float(verts[:,1].min()),float(verts[:,1].max())
                            whiskers=[float(artists["whiskers"][2*j].get_ydata().min()),
                                      float(artists["whiskers"][2*j+1].get_ydata().max())]
                            fliers=artists["fliers"][j].get_ydata().tolist()
                            np.testing.assert_allclose([median,q1,q3,*whiskers], [p["median"],p["q1"],p["q3"],p["whisker_low"],p["whisker_high"]])
                            np.testing.assert_allclose(sorted(fliers), sorted(p["fliers"]))
                            distributions.append({"median":median,"q1":q1,"q3":q3,"whiskers":whiskers,"fliers":fliers})
                    else:
                        artists=ax.violinplot(values, positions=x+offset, widths=width*.8,
                                              showmedians=True, showextrema=True, bw_method="scott", points=100)
                        for body in artists["bodies"]: body.set_facecolor(color); body.set_alpha(.6)
                        segments=artists["cmedians"].get_segments()
                        for segment,p in zip(segments,data):
                            median=float(segment[0,1]); np.testing.assert_allclose(median,p["median"])
                            distributions.append({"median":median,"minimum":min(p["values_raw"])*unit_factor(spec["metric"]["unit"],spec["metric"]["display_unit"]),
                                                  "maximum":max(p["values_raw"])*unit_factor(spec["metric"]["unit"],spec["metric"]["display_unit"]),
                                                  "kde":"Scott bandwidth; 100 sample positions; descriptive smoothing, not inferred uncertainty"})
                    ax.plot([],[],color=color,label=series)
                    artist_x=x; artist_y=y; ex=x
                else:
                    artist,=ax.plot(x,y,label=series,color=color,marker=style["markers"][i%len(style["markers"])],
                                    linestyle=style["linestyles"][i%len(style["linestyles"])],markersize=4,linewidth=1.4)
                    artist_x=np.asarray(artist.get_xdata());artist_y=np.asarray(artist.get_ydata());ex=x
                if spec["repeats"]["uncertainty"] != "none":
                    if chart == "hbar":
                        error=ax.errorbar(y,ex,xerr=np.array([y-low,high-y]),fmt="none",ecolor=color,capsize=3,linewidth=1.)
                        bounds=[segment[:,0].tolist() for segment in error[2][0].get_segments()]
                    else:
                        error=ax.errorbar(ex,y,yerr=np.array([y-low,high-y]),fmt="none",ecolor=color,capsize=3,linewidth=1.)
                        bounds=[segment[:,1].tolist() for segment in error[2][0].get_segments()]
                    np.testing.assert_allclose(bounds,np.column_stack([low,high]),rtol=1e-12,atol=1e-12)
                np.testing.assert_allclose(artist_x,x,rtol=1e-12,atol=1e-12)
                np.testing.assert_allclose(artist_y,y,rtol=1e-12,atol=1e-12)
                record={"series":series,"x":artist_x.tolist(),"y":artist_y.tolist(),"uncertainty_bounds":bounds}
                if distributions: record["distributions"]=distributions
                actual.append(record)
            if chart in ("bar", "box", "violin"):
                ax.set_xticks(range(len(spec["x_order"])),spec["x_order"])
            if chart == "hbar":
                ax.set_yticks(range(len(spec["x_order"])),spec["x_order"]); ax.invert_yaxis()
                lo,hi=ax.get_xlim();ax.set_xlim(min(0,lo),max(0,hi))
            elif chart == "bar":
                lo,hi=ax.get_ylim();ax.set_ylim(min(0,lo),max(0,hi))
            ax.legend(fontsize=style["font_size"])
        if chart in ("line", "scatter"):
            ax.set_xscale(spec["x"]["scale"]); ax.set_yscale(spec["metric"]["scale"])
        x_label=spec["x"]["label"]+(f' ({spec["x"]["display_unit"]})' if spec["x"]["display_unit"] != "1" else "")
        y_label=f'{spec["metric"]["name"]} ({spec["metric"]["display_unit"]})'
        ax.set_xlabel(y_label if chart=="hbar" else x_label)
        ax.set_ylabel(x_label if chart=="hbar" else ("Series" if chart=="heatmap" else y_label))
        suffix={"none":"No error bars", "sd":"Mean +/- sample SD", "se":"Mean +/- SE", "ci95":"95% Student-t CI for mean"}[spec["repeats"]["uncertainty"]]
        if chart=="box": suffix="Median, linear quartiles; whiskers 1.5 IQR; all outliers shown"
        if chart=="violin": suffix="Original observations; Scott-bandwidth KDE and median"
        if chart=="scatter": suffix="Every original observed pair; no averaging"
        ax.set_title(suffix,fontsize=style["font_size"])
        if chart != "heatmap": ax.grid(axis="x" if chart=="hbar" else "y",alpha=.18,linewidth=.5);ax.set_axisbelow(True)
        if spec["source"]["data_role"]=="synthetic_fixture":
            fig.text(.5,.5,"SYNTHETIC TEST: NOT RESEARCH RESULTS",ha="center",va="center",rotation=15,alpha=.22,color="#842A2A",fontsize=12)
        fig.canvas.draw()
    return fig,{"status":"passed","rtol":1e-12,"atol":1e-12,"artists":actual,
                "scope":"Coordinates/error endpoints or distribution summaries checked on actual artists; semantic scientific and visual QA remain separate."}


def validate_artifacts(root):
    """Fully decode PNG and parse real vector formats; no metadata-only pass."""
    import xml.etree.ElementTree as ET
    from PIL import Image
    from pypdf import PdfReader
    root=Path(root)
    with Image.open(root/"figure.png") as im:
        if im.format!="PNG" or im.width*im.height>64_000_000:
            raise PlotValidationError("PNG format or pixel limit invalid")
        im.verify()
    with Image.open(root/"figure.png") as im:
        im.load()  # verify() alone does not decompress IDAT pixels.
        extrema=im.convert("RGB").getextrema()
        if all(lo==hi for lo,hi in extrema):
            raise PlotValidationError("PNG is blank or uniformly colored")
        png={"width":im.width,"height":im.height,"dpi":list(im.info.get("dpi",())) ,"fully_decoded":True}
    svg_raw=(root/"figure.svg").read_bytes()
    if b"<!DOCTYPE" in svg_raw or b"<!ENTITY" in svg_raw:
        # Matplotlib emits a standard static SVG doctype. Reject entities/internal subsets only.
        if b"<!ENTITY" in svg_raw or b"[" in svg_raw.split(b"<!DOCTYPE",1)[1].split(b">",1)[0]:
            raise PlotValidationError("SVG entity declarations are not allowed")
    svg=ET.fromstring(svg_raw)
    names=[e.tag.rsplit("}",1)[-1] for e in svg.iter()]
    if svg.tag.rsplit("}",1)[-1]!="svg" or any(n in names for n in ("image","script","foreignObject")):
        raise PlotValidationError("SVG must contain native vectors and text, not a raster wrapper")
    if "text" not in names or "path" not in names:
        raise PlotValidationError("SVG lacks editable text or vector objects")
    for e in svg.iter():
        for key,value in e.attrib.items():
            if key.lower().startswith("on") or (key.rsplit("}",1)[-1]=="href" and not value.startswith("#")):
                raise PlotValidationError("SVG external/active references are not allowed")
    pdf=PdfReader(root/"figure.pdf",strict=True)
    if len(pdf.pages)!=1 or not pdf.pages[0].extract_text().strip():
        raise PlotValidationError("PDF must have one vector page with selectable text")
    def no_images(resources):
        for obj in resources.get("/XObject",{}).values():
            item=obj.get_object()
            if item.get("/Subtype")=="/Image": raise PlotValidationError("PDF contains raster image objects")
            if item.get("/Subtype")=="/Form": no_images(item.get("/Resources",{}))
    no_images(pdf.pages[0].get("/Resources",{}))
    return {"status":"passed","png":png,"svg":{"editable_text":names.count("text"),"vector_paths":names.count("path"),"embedded_raster_images":0},
            "pdf":{"pages":1,"selectable_text":True,"embedded_raster_images":0},
            "scope":"Complete raster decode and native vector/text structure; not a claim of PPTX editability or scientific validity."}


def read_regular(path, limit):
    import stat
    location=no_links(path)
    if not location.is_file() or not stat.S_ISREG(location.stat().st_mode) or location.stat().st_size>limit:
        raise PlotValidationError("Input must be a bounded ordinary regular file")
    with location.open("rb") as stream: raw=stream.read(limit+1)
    if len(raw)>limit: raise PlotValidationError("Input exceeds size limit")
    return raw


def export(data_path, spec_path, style_path, output, original_path=None, derivation_code_path=None):
    raw = read_regular(data_path, 64*1024*1024)
    spec_raw = read_regular(spec_path, 4*1024*1024); style_raw = read_regular(style_path, 4*1024*1024)
    spec = validate_spec(strict_json(spec_raw)); style = validate_style(strict_json(style_raw))
    original = None
    derivation_code = None
    if "original_sha256" in spec["source"]:
        if original_path is None:
            raise PlotValidationError("Declared original source requires --original; self-reported hashes are not verification")
        original = read_regular(original_path, 64*1024*1024)
        if digest(original) != spec["source"]["original_sha256"]:
            raise PlotValidationError("Original source bytes do not match declared SHA-256")
        if original != raw:
            if derivation_code_path is None or not spec["source"].get("derivation"):
                raise PlotValidationError("Derived data requires a described transformation and --derivation-code for review/reproduction")
            derivation_code = read_regular(derivation_code_path, 4*1024*1024)
    elif original_path is not None or derivation_code_path is not None:
        raise PlotValidationError("Original/derivation files require original_sha256 in the specification")
    rows = read_data(raw, spec); points = aggregate(rows, spec)
    fig, acceptance = draw(points, spec, style)
    target = no_links(output)
    if target.exists():
        plt.close(fig)
        raise FileExistsError(f"Refusing to overwrite output: {target}")
    target.mkdir(parents=True, exist_ok=False)
    try:
        (target / "source.csv").write_bytes(raw)
        (target / "plot-spec.json").write_bytes(spec_raw)
        (target / "style.json").write_bytes(style_raw)
        if original is not None:
            (target / "original-source.csv").write_bytes(original)
        if derivation_code is not None:
            (target / "derivation_code.py").write_bytes(derivation_code)
        # This is this reviewed deterministic implementation, not a model-generated input.
        (target / "plot_code.py").write_bytes(Path(__file__).read_bytes())
        # Font backends consult rcParams during save, after draw's context exits.
        with plt.rc_context({"pdf.fonttype": 42, "svg.fonttype": "none"}):
            for ext in ("pdf", "svg", "png"):
                fig.savefig(target / f"figure.{ext}", dpi=style["dpi"], metadata={"Creator": "academic-plotting"} if ext == "pdf" else None)
        artifact_check = validate_artifacts(target)
        (target / "artifact-acceptance.json").write_text(json.dumps(artifact_check, indent=2) + "\n", encoding="utf-8")
        (target / "numeric-table.json").write_text(json.dumps(points, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (target / "numeric-acceptance.json").write_text(json.dumps(acceptance, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        provenance = {"schema_version": "1.0.0", "source": spec["source"], "source_bytes": len(raw),
                      "spec_sha256": digest(spec_raw), "style_sha256": digest(style_raw),
                      "code_sha256": digest(Path(__file__).read_bytes()),
                      "unit_transform": {"x": unit_factor(spec["x"]["unit"], spec["x"]["display_unit"]),
                                         "y": unit_factor(spec["metric"]["unit"], spec["metric"]["display_unit"])},
                      "repeats": spec["repeats"], "estimator": "arithmetic mean; sample SD ddof=1; SE=SD/sqrt(n); CI=t(0.975,n-1)*SE",
                      "series_order": spec["series_order"], "x_order": spec["x_order"],
                      "versions": {"python": platform.python_version(), "numpy": np.__version__, "matplotlib": matplotlib.__version__, "scipy": __import__("scipy").__version__},
                      "scientific_claims_verified": False, "numeric_acceptance": acceptance["status"],
                      "artifact_acceptance": artifact_check["status"], "data_role": spec["source"]["data_role"],
                      "original_source": {"verified": original is not None, "path": "original-source.csv" if original is not None else None,
                                          "sha256": digest(original) if original is not None else None},
                      "derivation": {"code_path": "derivation_code.py" if derivation_code is not None else None,
                                     "code_sha256": digest(derivation_code) if derivation_code is not None else None,
                                     "code_executed": False, "relationship_verified": False,
                                     "scope": "Original byte identity is verified; transformation meaning/correctness requires separate independent lineage review."},
                      "reproduce": "python plot_code.py --data source.csv --spec plot-spec.json --style style.json --output reproduced"
                                   + (" --original original-source.csv" if original is not None else "")
                                   + (" --derivation-code derivation_code.py" if derivation_code is not None else "")}
        provenance["outputs"] = {p.name: {"sha256": digest(p.read_bytes()), "bytes": p.stat().st_size} for p in target.iterdir() if p.is_file()}
        (target / "provenance.json").write_text(json.dumps(provenance, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(target)
        raise
    finally:
        plt.close(fig)
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("data", "spec", "style", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--original", type=Path)
    parser.add_argument("--derivation-code", type=Path)
    args = parser.parse_args()
    export(args.data, args.spec, args.style, args.output, args.original, args.derivation_code)
    print(f"Saved verified numeric figures to {args.output}")


if __name__ == "__main__":
    main()
