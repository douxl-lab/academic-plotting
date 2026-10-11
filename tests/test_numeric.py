"""All numeric fixtures here are synthetic software tests, never research results."""
import copy
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from PIL import Image

from numeric_plot import (PlotValidationError, aggregate, digest, draw, export,
                          read_data, strict_json, unit_factor, validate_spec, validate_style)
from verify_numeric import verify


ROOT = Path(__file__).resolve().parents[1]
STYLE = json.loads((ROOT / "assets/style.json").read_text())


def fixture(raw=None):
    raw = raw or b"series,x,replicate,value\nB,1,r1,1\nB,1,r2,2\nB,1,r3,3\nA,1,r1,2\nA,1,r2,3\nA,1,r3,4\n"
    spec = {"schema_version": "1.0.0", "chart": "bar",
            "source": {"sha256": digest(raw), "title": "SYNTHETIC SOFTWARE TEST", "uri": "https://example.org/synthetic-test", "license": "test-only", "citation": "Not research evidence", "data_role": "synthetic_fixture"},
            "x": {"label": "Category", "unit": "1", "display_unit": "1", "scale": "linear"},
            "metric": {"name": "Length", "kind": "length", "unit": "cm", "display_unit": "mm", "direction": "descriptive", "scale": "linear"},
            "series_order": ["A", "B"], "x_order": ["1"],
            "repeats": {"basis": "independent_runs", "unit": "test run", "uncertainty": "sd", "assume_iid": True, "limitations": "Synthetic fixture only"}}
    return raw, spec


def inputs(tmp_path, raw=None, spec=None):
    default_raw, default_spec = fixture()
    raw = raw if raw is not None else default_raw
    spec = spec if spec is not None else default_spec
    data = tmp_path / "input.csv"; data.write_bytes(raw)
    config = tmp_path / "spec.json"; config.write_text(json.dumps(spec))
    style = tmp_path / "style.json"; style.write_text(json.dumps(STYLE))
    return data, config, style


def test_mean_sample_sd_conversion_and_series_order():
    raw, spec = fixture()
    points = aggregate(read_data(raw, validate_spec(spec)), spec)
    assert [p["series"] for p in points] == ["A", "B"]
    assert points[1]["n"] == 3
    assert points[1]["mean_raw"] == 2
    assert points[1]["sd_raw"] == 1  # sample SD, not population SD
    assert points[1]["y"] == 20
    assert points[1]["low"] == 10 and points[1]["high"] == 30


@pytest.mark.parametrize("kind,half", [("sd", 1), ("se", 1 / math.sqrt(3)), ("ci95", 4.302652729696142 / math.sqrt(3)), ("none", 0)])
def test_uncertainty_semantics(kind, half):
    raw, spec = fixture(); spec["repeats"]["uncertainty"] = kind
    point = aggregate(read_data(raw, validate_spec(spec)), spec)[1]
    assert point["low"] == pytest.approx((2 - half) * 10)
    assert point["high"] == pytest.approx((2 + half) * 10)


def test_observational_sd_does_not_claim_iid():
    raw, spec = fixture()
    spec["repeats"].update(basis="observations", assume_iid=False)
    assert aggregate(read_data(raw, validate_spec(spec)), spec)[0]["n"] == 3


@pytest.mark.parametrize("kind", ["se", "ci95"])
def test_dependent_observations_cannot_get_inferential_bars(kind):
    _, spec = fixture(); spec["repeats"].update(uncertainty=kind, assume_iid=False)
    with pytest.raises(PlotValidationError, match="i.i.d"):
        validate_spec(spec)


def test_no_invented_single_observation_errorbar():
    raw = b"series,x,replicate,value\nB,1,r1,2\nA,1,r1,3\n"
    raw, spec = fixture(raw)
    with pytest.raises(PlotValidationError, match=">=2"):
        aggregate(read_data(raw, spec), spec)


def test_single_basis_rejects_repeats():
    raw, spec = fixture(); spec["repeats"].update(basis="single", uncertainty="none")
    with pytest.raises(PlotValidationError, match="contains repeats"):
        aggregate(read_data(raw, validate_spec(spec)), spec)


def test_tampered_source_rejected():
    raw, spec = fixture()
    with pytest.raises(PlotValidationError, match="checksum"):
        read_data(raw + b"A,1,r4,9\n", spec)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "", "not-a-number"])
def test_bad_numeric_source_rejected(value):
    raw, spec = fixture(b"series,x,replicate,value\nA,1,r1,2\nB,1,r1," + value.encode() + b"\n")
    with pytest.raises(PlotValidationError):
        read_data(raw, spec)


def test_duplicate_replicate_rejected():
    raw, spec = fixture(b"series,x,replicate,value\nA,1,r1,2\nB,1,r1,3\nA,1,r1,4\n")
    with pytest.raises(PlotValidationError, match="Duplicate replicate"):
        read_data(raw, spec)


def test_declared_order_cannot_drop_a_series():
    raw, spec = fixture(); spec["series_order"] = ["A"]
    with pytest.raises(PlotValidationError, match="Unknown series"):
        read_data(raw, spec)


def test_metric_fraction_percent_check():
    raw, spec = fixture(); spec["metric"].update(kind="accuracy", unit="1", display_unit="%", valid_max=100)
    with pytest.raises(PlotValidationError, match="fraction/percent"):
        read_data(raw, validate_spec(spec))


def test_percent_display_transforms_all_uncertainty():
    raw, spec = fixture(b"series,x,replicate,value\nA,1,r1,0.6\nA,1,r2,0.8\nB,1,r1,0.4\nB,1,r2,0.6\n")
    spec["metric"].update(kind="accuracy", unit="1", display_unit="%")
    point = aggregate(read_data(raw, validate_spec(spec)), spec)[0]
    assert point["y"] == pytest.approx(70)
    assert point["high"] - point["y"] == pytest.approx(math.sqrt(.02) * 100)


@pytest.mark.parametrize("a,b", [("cm", "ms"), ("arbitrary", "%"), ("s", "epoch")])
def test_incompatible_unit_conversions_rejected(a, b):
    with pytest.raises(PlotValidationError, match="Unsupported"):
        unit_factor(a, b)


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_strict_json(raw):
    with pytest.raises(PlotValidationError):
        strict_json(raw)


def test_line_must_declare_monotonic_numeric_x():
    raw, spec = fixture(); spec.update(chart="line", x_order=["2", "1"])
    raw = raw.replace(b",1,", b",2,") + b"A,1,r1,2\nB,1,r1,3\n"
    spec["source"]["sha256"] = digest(raw)
    with pytest.raises(PlotValidationError, match="strictly increasing"):
        read_data(raw, spec)


def test_log_refuses_nonpositive_uncertainty_bound():
    raw, spec = fixture(); spec.update(chart="line")
    spec["metric"]["scale"] = "log"; spec["repeats"]["uncertainty"] = "ci95"
    with pytest.raises(PlotValidationError, match="no clipping"):
        aggregate(read_data(raw, validate_spec(spec)), spec)


@pytest.mark.parametrize("chart", ["bar", "line", "scatter"])
def test_actual_artist_coordinates_and_bounds(chart):
    raw, spec = fixture(); spec["chart"] = chart
    if chart == "scatter":
        raw, spec = fixture(b"series,x,replicate,value\nA,1,r1,3\nB,1,r1,2\n")
        spec["chart"] = chart; spec["repeats"].update(basis="single", uncertainty="none")
    points = aggregate(read_data(raw, validate_spec(spec)), spec)
    fig, acceptance = draw(points, spec, STYLE)
    assert acceptance["status"] == "passed"
    assert acceptance["artists"][0]["y"] == [30]
    if chart != "scatter":
        assert acceptance["artists"][0]["uncertainty_bounds"] == [[20, 40]]
    plt.close(fig)


@pytest.mark.parametrize("field,value", [("dpi", 72), ("font_size", 6), ("width_in", 0)])
def test_style_bounds(field, value):
    style = copy.deepcopy(STYLE); style[field] = value
    with pytest.raises(PlotValidationError):
        validate_style(style)


def test_export_three_formats_independent_audit_and_reproduce(tmp_path):
    data, config, style = inputs(tmp_path)
    out = tmp_path / "result"
    provenance = export(data, config, style, out)
    assert (out / "figure.pdf").read_bytes().startswith(b"%PDF")
    assert "<svg" in (out / "figure.svg").read_text(encoding="utf-8")
    with Image.open(out / "figure.png") as image:
        assert image.size == (1650, 1020)
        assert image.info["dpi"][0] == pytest.approx(300, abs=.02)
    assert provenance["source"]["sha256"] == digest(data.read_bytes())
    assert verify(out)["status"] == "passed"
    reproduction = tmp_path / "reproduction"
    subprocess.run([sys.executable, str(out / "plot_code.py"), "--data", str(out / "source.csv"),
                    "--spec", str(out / "plot-spec.json"), "--style", str(out / "style.json"), "--output", str(reproduction)], check=True, capture_output=True)
    assert (out / "numeric-table.json").read_bytes() == (reproduction / "numeric-table.json").read_bytes()
    with pytest.raises(FileExistsError):
        export(data, config, style, out)


def test_independent_audit_catches_consistent_hashes_with_wrong_statistics(tmp_path):
    data, config, style = inputs(tmp_path); out = tmp_path / "result"
    export(data, config, style, out)
    table = json.loads((out / "numeric-table.json").read_text()); table[0]["sd_raw"] = .5
    (out / "numeric-table.json").write_text(json.dumps(table))
    p = json.loads((out / "provenance.json").read_text())
    payload = (out / "numeric-table.json").read_bytes()
    p["outputs"]["numeric-table.json"] = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    (out / "provenance.json").write_text(json.dumps(p))
    with pytest.raises(ValueError, match="Numerical mismatch"):
        verify(out)
