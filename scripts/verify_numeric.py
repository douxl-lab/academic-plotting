#!/usr/bin/env python3
"""Independent CSV-to-table/artist audit, followed by full artifact decoding.

Arithmetic means, sample SD, inclusive quartiles and whiskers use Python's stdlib;
only the Student-t quantile uses SciPy. No plot or derivation input code executes.
The mathematical audit is independent of numeric_plot.aggregate and draw.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from scipy.stats import t
from numeric_plot import no_links, read_regular, strict_json, validate_artifacts


def close(actual, expected):
    if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12):
        raise ValueError(f"Numerical mismatch: {actual} != {expected}")


def verify(output):
    root=no_links(output)
    provenance=strict_json(read_regular(root/"provenance.json",4*1024*1024))
    required={"source.csv","plot-spec.json","style.json","plot_code.py","figure.svg","figure.pdf","figure.png",
              "numeric-table.json","numeric-acceptance.json","artifact-acceptance.json"}
    outputs=provenance["outputs"]
    if not isinstance(outputs,dict) or not required<=set(outputs):
        raise ValueError("Provenance omits required numeric artifacts")
    for name,record in outputs.items():
        if not isinstance(name,str) or not name or any(c in name for c in "/\\:") or name in (".","..") or name.casefold()=="provenance.json":
            raise ValueError("Unsafe provenance artifact name")
        payload=read_regular(root/name,100*1024*1024)
        if set(record)!={"bytes","sha256"} or len(payload)!=record["bytes"] or hashlib.sha256(payload).hexdigest()!=record["sha256"]:
            raise ValueError(f"Artifact hash mismatch: {name}")
    raw=read_regular(root/"source.csv",64*1024*1024)
    spec_raw=read_regular(root/"plot-spec.json",4*1024*1024)
    spec=strict_json(spec_raw)
    if hashlib.sha256(raw).hexdigest()!=spec["source"]["sha256"] or provenance["source"]!=spec["source"]:
        raise ValueError("Raw source/provenance identity mismatch")
    for name,key in (("plot-spec.json","spec_sha256"),("style.json","style_sha256"),("plot_code.py","code_sha256")):
        if hashlib.sha256(read_regular(root/name,4*1024*1024)).hexdigest()!=provenance[key]:
            raise ValueError("Configuration/code identity mismatch")
    if "original_sha256" in spec["source"]:
        original=read_regular(root/"original-source.csv",64*1024*1024)
        original_digest=hashlib.sha256(original).hexdigest()
        if original_digest!=spec["source"]["original_sha256"] or provenance["original_source"]!={"verified":True,"path":"original-source.csv","sha256":original_digest}:
            raise ValueError("Original source identity was not verified from bytes")
        if original!=raw:
            derivation=read_regular(root/"derivation_code.py",4*1024*1024)
            if hashlib.sha256(derivation).hexdigest()!=provenance["derivation"]["code_sha256"]:
                raise ValueError("Derivation code hash mismatch")
            if provenance["derivation"]["code_executed"] or provenance["derivation"]["relationship_verified"]:
                raise ValueError("This verifier cannot assert transformation execution or scientific lineage correctness")
    points=strict_json(read_regular(root/"numeric-table.json",16*1024*1024))
    acceptance=strict_json(read_regular(root/"numeric-acceptance.json",16*1024*1024))
    artists=acceptance["artists"]
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")),strict=True)
    if reader.fieldnames != ["series","x","replicate","value"]:
        raise ValueError("Unexpected source CSV columns")
    groups=defaultdict(list);identities=set();source_count=0
    for row in reader:
        identity=(row["series"],row["x"],row["replicate"])
        if identity in identities: raise ValueError("Duplicate source observation")
        identities.add(identity);value=float(row["value"])
        if not math.isfinite(value): raise ValueError("Nonfinite source observation")
        groups[row["series"],row["x"]].append((row["replicate"],value));source_count+=1
    units={"1":("ratio",1),"%":("ratio",.01),"mm":("length",.001),"cm":("length",.01),"m":("length",1),"ms":("time",.001),"s":("time",1)}
    def factor(axis):
        if axis["unit"]==axis["display_unit"]: return 1
        a,b=units[axis["unit"]],units[axis["display_unit"]]
        if a[0]!=b[0]: raise ValueError("Invalid unit dimensions")
        return a[1]/b[1]
    yf,xf=factor(spec["metric"]),factor(spec["x"])
    close(provenance["unit_transform"]["y"],yf);close(provenance["unit_transform"]["x"],xf)
    cells=[(s,x) for s in spec["series_order"] for x in spec["x_order"]]
    scatter=spec["chart"]=="scatter"
    expected_order=[(s,x,r) for s,x in cells for r,v in groups[s,x]] if scatter else cells
    actual_order=[(p["series"],p["x_label"],p["replicate"]) for p in points] if scatter else [(p["series"],p["x_label"]) for p in points]
    if actual_order!=expected_order or not set(groups)<=set(cells) or (not scatter and set(groups)!=set(cells)):
        raise ValueError("Point order or source cells differ")
    uncertainty=spec["repeats"]["uncertainty"]
    for point in points:
        observations=groups[point["series"],point["x_label"]]
        if scatter: observations=[(r,v) for r,v in observations if r==point["replicate"]]
        values=[v for r,v in observations];n=len(values);mean=statistics.mean(values)
        if point["n"]!=n: raise ValueError("Incorrect replicate count")
        close(point["mean_raw"],mean)
        sd=statistics.stdev(values) if n>1 else None;se=sd/math.sqrt(n) if sd is not None else None
        for key,value in (("sd_raw",sd),("se_raw",se)):
            if value is None:
                if point[key] is not None: raise ValueError("Invented uncertainty for a single observation")
            else: close(point[key],value)
        half={"none":0,"sd":sd,"se":se}.get(uncertainty)
        if uncertainty=="ci95": half=float(t.ppf(.975,n-1))*se
        close(point["y"],mean*yf);close(point["low"],(mean-half)*yf);close(point["high"],(mean+half)*yf)
        expected_x=float(point["x_label"])*xf if spec["chart"] in ("line","scatter") else spec["x_order"].index(point["x_label"])
        close(point["x"],expected_x)
        if spec["chart"] in ("box","violin"):
            if point["values_raw"]!=values or point["replicates"]!=[r for r,v in observations]:
                raise ValueError("Distribution discarded or changed original observations")
            displayed=[v*yf for v in values];q1,median,q3=statistics.quantiles(displayed,n=4,method="inclusive")
            inside=[v for v in displayed if q1-1.5*(q3-q1)<=v<=q3+1.5*(q3-q1)]
            for key,value in (("median",median),("q1",q1),("q3",q3),("whisker_low",min(inside)),("whisker_high",max(inside))): close(point[key],value)
            if sorted(point["fliers"])!=sorted(v for v in displayed if v<min(inside) or v>max(inside)):
                raise ValueError("Distribution outliers were changed or hidden")
    if [a["series"] for a in artists]!=spec["series_order"]: raise ValueError("Artist series order differs")
    for artist in artists:
        data=[p for p in points if p["series"]==artist["series"]]
        if len(artist["x"])!=len(data) or len(artist["y"])!=len(data): raise ValueError("Artist point count differs")
        for i,point in enumerate(data): close(artist["x"][i],point["x"]);close(artist["y"][i],point["y"])
        bounds=artist["uncertainty_bounds"]
        if uncertainty=="none":
            if bounds: raise ValueError("Unexpected uncertainty artists")
        else:
            if len(bounds)!=len(data): raise ValueError("Incorrect errorbar count")
            for interval,point in zip(bounds,data): close(interval[0],point["low"]);close(interval[1],point["high"])
        if spec["chart"] in ("box","violin"):
            distributions=artist.get("distributions",[])
            if len(distributions)!=len(data): raise ValueError("Missing actual distribution artist summaries")
            for record,point in zip(distributions,data):
                close(record["median"],point["median"])
                if spec["chart"]=="box":
                    close(record["q1"],point["q1"]);close(record["q3"],point["q3"])
                    close(record["whiskers"][0],point["whisker_low"]);close(record["whiskers"][1],point["whisker_high"])
                    if sorted(record["fliers"])!=sorted(point["fliers"]): raise ValueError("Outlier artists differ")
                else:
                    close(record["minimum"],min(point["values_raw"])*yf);close(record["maximum"],max(point["values_raw"])*yf)
    artifacts=validate_artifacts(root)
    return {"status":"passed","method":"Independent stdlib mean/stdev/inclusive quartiles/whiskers; scipy t quantile; original CSV and actual artist ledger",
            "points":len(points),"source_rows":source_count,"rtol":1e-12,"atol":1e-12,"artifacts":artifacts,
            "limits":"Hash consistency, numerical summaries and full pixel decode/native vector structure verified. Does not prove source authenticity, i.i.d., causal conclusions, lineage meaning, or that an externally altered figure matches its ledger. Inspect actual figures against the source and caption."}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("output",type=Path);parser.add_argument("--report",type=Path)
    args=parser.parse_args();result=verify(args.output);rendered=json.dumps(result,indent=2)+"\n"
    if args.report:
        with args.report.open("x",encoding="utf-8") as stream: stream.write(rendered)
    print(rendered)
