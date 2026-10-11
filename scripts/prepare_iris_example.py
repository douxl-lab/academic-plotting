#!/usr/bin/env python3
"""Prepare genuine bundled Iris observations offline; never simulate measurements.

Optional example-only dependency: scikit-learn. Plotting itself does not need it.
Source: Fisher (1936), UCI Iris DOI 10.24432/C56C76, CC BY 4.0.
This uses scikit-learn's two-point corrected variant, not byte-identical UCI data.
"""
import argparse
import csv
import hashlib
import importlib.resources
import json
from pathlib import Path

import sklearn
from sklearn.datasets import load_iris


def prepare(output, chart="bar"):
    if chart not in ("bar", "hbar", "heatmap", "box", "violin", "scatter"):
        raise ValueError("Iris has categorical dimensions, not a training/time sequence")
    target = Path(output)
    target.mkdir(parents=True, exist_ok=False)
    original = importlib.resources.files("sklearn.datasets.data").joinpath("iris.csv").read_bytes()
    (target / "iris-sklearn-original.csv").write_bytes(original)
    iris = load_iris()
    features = ["Sepal length", "Sepal width", "Petal length", "Petal width"]
    with (target / "measurements.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["series", "x", "replicate", "value"])
        for index, (values, species) in enumerate(zip(iris.data, iris.target), 1):
            if chart=="scatter":
                writer.writerow([str(iris.target_names[species]), format(float(values[0]),".1f"),f"plant-{index:03d}",format(float(values[2]),".1f")])
            else:
                for feature, value in zip(features, values):
                    writer.writerow([str(iris.target_names[species]), feature, f"plant-{index:03d}", format(float(value), ".1f")])
    raw = (target / "measurements.csv").read_bytes()
    source = {"sha256": hashlib.sha256(raw).hexdigest(), "title": "Iris measurements: scikit-learn corrected Fisher dataset",
              "uri": "https://archive.ics.uci.edu/dataset/53/iris", "license": "CC BY 4.0 (dataset; attribution below)",
              "citation": "Fisher, R. (1936). Iris [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C56C76",
              "data_role": "public_observations",
              "original_sha256": hashlib.sha256(original).hexdigest(), "original_filename": "iris-sklearn-original.csv",
              "derivation": "Read bundled sklearn iris.csv via load_iris; retain four measured dimensions; reshape 150 rows to 600 long-table rows without rounding beyond source 0.1 cm precision; cm to mm is an explicit plotting display conversion.",
              "dataset_variant": f"scikit-learn {sklearn.__version__}; since 0.20 two source points corrected to Fisher/R version; differs from original UCI iris.data."}
    spec = {"schema_version": "1.0.0", "chart": chart, "source": source,
            "x": {"label": "Measured dimension", "unit": "1", "display_unit": "1", "scale": "linear"},
            "metric": {"name": "Flower dimension", "kind": "length", "unit": "cm", "display_unit": "mm", "direction": "descriptive", "scale": "linear", "valid_min": 0},
            "series_order": list(map(str, iris.target_names)), "x_order": features,
            "repeats": {"basis": "observations", "unit": "individual iris plant", "uncertainty": "sd", "assume_iid": False,
                        "limitations": "50 observed plants per species; error bars show sample SD (ddof=1) of measured dimensions, not SE, CI, repeated model runs, or new experimental results. No i.i.d. population inference is asserted; dimensions on the same plant are correlated."}}
    if chart in ("heatmap","box","violin","scatter"):
        spec["repeats"]["uncertainty"]="none"
    if chart=="scatter":
        spec["x"].update(label="Sepal length",unit="cm",display_unit="mm")
        spec["metric"]["name"]="Petal length"
        spec["x_order"]=[format(float(x),".1f") for x in sorted(set(iris.data[:,0]))]
        spec["source"]["derivation"]="Retain original sepal-length/petal-length pair for each of 150 plants, with species and plant row identity; no averaging, synthetic values or imputation. cm -> mm is explicit display conversion."
        spec["repeats"]["limitations"]="Every point is an original plant's paired measurements, including repeated x coordinates; no aggregation or inferential error bars."
    elif chart in ("box","violin"):
        spec["repeats"]["limitations"]="50 original observations per species/dimension; box uses median/linear quartiles/1.5-IQR whiskers with outliers shown; violin is descriptive Scott-bandwidth smoothing, not a model-run confidence interval. Same-plant dimensions are correlated."
    elif chart=="heatmap":
        spec["repeats"]["limitations"]="Each cell is the arithmetic mean of 50 original plant observations; no error bars, significance claims or population inference."
    (target / "plot-spec.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    (target / "prepare_code.py").write_bytes(Path(__file__).read_bytes())
    (target / "attribution.txt").write_text(
        "Iris dataset: Fisher, R. (1936), UCI Machine Learning Repository, DOI 10.24432/C56C76.\n"
        "https://archive.ics.uci.edu/dataset/53/iris\nDataset license: CC BY 4.0. https://creativecommons.org/licenses/by/4.0/\n"
        "Variant/changes: bundled scikit-learn version, including documented historical corrections; source reshaped to long CSV; display cm -> mm.\n"
        "scikit-learn load_iris documentation: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_iris.html\n"
        "This is a public observational plotting example; it is not a model experiment or evidence of a research contribution.\n", encoding="utf-8")
    return spec


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chart",choices=("bar","hbar","heatmap","box","violin","scatter"),default="bar")
    args = parser.parse_args()
    prepare(args.output,args.chart)
    print(f"Prepared genuine Iris observations: {args.output}")
