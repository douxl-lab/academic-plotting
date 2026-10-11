"""Chart semantics, real datasets, export corruption and non-mocked renderer QA."""
import copy
import csv
import io
import json
import struct
import zlib
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pytest
from PIL import Image
from numeric_plot import aggregate,draw,export,read_data,validate_spec,validate_style,validate_artifacts,PlotValidationError,digest
from verify_numeric import verify
from test_numeric import fixture,inputs,STYLE


@pytest.mark.parametrize("chart",["hbar","heatmap","box","violin"])
def test_additional_chart_actual_artists_and_native_vectors(tmp_path,chart):
    raw,spec=fixture();spec["chart"]=chart
    if chart in ("heatmap","box","violin"):spec["repeats"]["uncertainty"]="none"
    data,conf,style=inputs(tmp_path,raw,spec)
    out=tmp_path/"result";export(data,conf,style,out)
    assert verify(out)["status"]=="passed"
    assert validate_artifacts(out)["svg"]["embedded_raster_images"]==0
    if chart in ("box","violin"):
        table=json.loads((out/"numeric-table.json").read_text())
        assert table[0]["median"]==30
        assert table[0]["values_raw"]==[2,3,4]


def test_scatter_keeps_original_sparse_pairs_and_duplicate_x(tmp_path):
    raw,spec=fixture(b"series,x,replicate,value\nA,1,p1,2\nA,1,p2,3\nB,2,p3,4\n")
    spec.update(chart="scatter",x_order=["1","2"]);spec["repeats"].update(basis="observations",uncertainty="none",assume_iid=False)
    points=aggregate(read_data(raw,validate_spec(spec)),spec)
    assert [(p["series"],p["replicate"],p["n"],p["y"]) for p in points]==[("A","p1",1,20),("A","p2",1,30),("B","p3",1,40)]
    export(*inputs(tmp_path,raw,spec),tmp_path/"scatter")
    assert verify(tmp_path/"scatter")["source_rows"]==3


@pytest.mark.parametrize("chart",["box","violin","heatmap","hbar"])
def test_categorical_axes_refuse_unsupported_units_or_log(chart):
    _,spec=fixture();spec["chart"]=chart
    if chart in ("box","violin","heatmap"):spec["repeats"]["uncertainty"]="none"
    spec["x"]["scale"]="log"
    with pytest.raises(PlotValidationError,match="Categorical axes"):validate_spec(spec)


def test_violin_rejects_constant_samples_instead_of_inventing_shape():
    raw,spec=fixture(b"series,x,replicate,value\nA,1,r1,2\nA,1,r2,2\nB,1,r1,3\nB,1,r2,3\n")
    spec["chart"]="violin";spec["repeats"]["uncertainty"]="none"
    with pytest.raises(PlotValidationError,match="nonconstant"):aggregate(read_data(raw,validate_spec(spec)),spec)


def corrupt_png_idat(raw):
    """Create a valid-CRC PNG with IDAT that verify() accepts but cannot inflate."""
    result=raw[:8];cursor=8
    while cursor<len(raw):
        length=struct.unpack(">I",raw[cursor:cursor+4])[0];kind=raw[cursor+4:cursor+8];data=raw[cursor+8:cursor+8+length]
        if kind==b"IDAT":data=b"not a zlib compressed pixel stream"
        result+=struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
        cursor+=length+12
    return result


def test_complete_decode_detects_valid_crc_broken_png(tmp_path):
    export(*inputs(tmp_path),tmp_path/"figure");path=tmp_path/"figure/figure.png"
    broken=corrupt_png_idat(path.read_bytes())
    with Image.open(io.BytesIO(broken)) as image:image.verify()  # reproduce the historical validation gap
    path.write_bytes(broken)
    with pytest.raises(OSError):validate_artifacts(path.parent)


def test_audit_rejects_broken_png_even_after_hash_record_refresh(tmp_path):
    out=tmp_path/"figure";export(*inputs(tmp_path),out)
    raw=corrupt_png_idat((out/"figure.png").read_bytes());(out/"figure.png").write_bytes(raw)
    p=json.loads((out/"provenance.json").read_text());p["outputs"]["figure.png"]={"sha256":digest(raw),"bytes":len(raw)}
    (out/"provenance.json").write_text(json.dumps(p))
    with pytest.raises(OSError):verify(out)


def test_svg_raster_wrapper_rejected(tmp_path):
    out=tmp_path/"figure";export(*inputs(tmp_path),out)
    p=out/"figure.svg";p.write_text(p.read_text().replace("</svg>",'<image href="data:image/png;base64,AA=="/></svg>'))
    with pytest.raises(PlotValidationError,match="raster wrapper"):validate_artifacts(out)


def test_negative_bars_always_include_real_zero_baseline():
    raw,spec=fixture(b"series,x,replicate,value\nA,1,r1,-2\nB,1,r1,-3\n")
    spec["metric"].update(kind="generic",unit="1",display_unit="1");spec["repeats"].update(basis="single",uncertainty="none")
    for chart in ("bar","hbar"):
        spec["chart"]=chart;fig,_=draw(aggregate(read_data(raw,validate_spec(spec)),spec),spec,STYLE)
        limits=fig.axes[0].get_ylim() if chart=="bar" else fig.axes[0].get_xlim()
        assert limits[0]<0<=limits[1];plt.close(fig)


def test_style_resource_bounds():
    style=copy.deepcopy(STYLE);style.update(width_in=20,height_in=20,dpi=1200)
    with pytest.raises(PlotValidationError,match="resource limit"):validate_style(style)


def test_source_needs_explicit_measured_or_synthetic_role():
    _,spec=fixture();del spec["source"]["data_role"]
    with pytest.raises(PlotValidationError):validate_spec(spec)


@pytest.mark.parametrize("chart",["bar","hbar","heatmap","box","violin","scatter"])
def test_genuine_iris_full_renderer_and_independent_raw_lineage(tmp_path,chart):
    pytest.importorskip("sklearn")
    from prepare_iris_example import prepare
    inp=tmp_path/"input";spec=prepare(inp,chart)
    original=list(csv.reader(io.StringIO((inp/"iris-sklearn-original.csv").read_text())))
    original=original[1:]
    derived=list(csv.DictReader(io.StringIO((inp/"measurements.csv").read_text())))
    assert len(original)==150 and len(derived)==(150 if chart=="scatter" else 600)
    names=["Sepal length","Sepal width","Petal length","Petal width"]
    for row in derived:
        i=int(row["replicate"].split("-")[1])-1;source=original[i]
        if chart=="scatter":assert float(row["x"])==float(source[0]) and float(row["value"])==float(source[2])
        else:assert float(row["value"])==float(source[names.index(row["x"])])
        assert row["series"]==spec["series_order"][int(source[4])]
    out=tmp_path/"figure"
    export(inp/"measurements.csv",inp/"plot-spec.json",Path(__file__).parents[1]/"assets/style.json",out,
           inp/"iris-sklearn-original.csv",inp/"prepare_code.py")
    report=verify(out)
    assert report["source_rows"]==len(derived) and report["artifacts"]["png"]["fully_decoded"]
    assert spec["source"]["data_role"]=="public_observations"
    assert not json.loads((out/"provenance.json").read_text())["scientific_claims_verified"]


@pytest.mark.parametrize("chart",["bar","box","violin"])
def test_real_categorical_tick_labels_survive_scale_configuration(chart):
    raw,spec=fixture();spec["chart"]=chart
    if chart in ("box","violin"):spec["repeats"]["uncertainty"]="none"
    raw=raw.replace(b",1,",b",measured category,");spec["x_order"]=["measured category"];spec["source"]["sha256"]=digest(raw)
    fig,_=draw(aggregate(read_data(raw,validate_spec(spec)),spec),spec,STYLE)
    assert [t.get_text() for t in fig.axes[0].get_xticklabels()]==["measured category"]
    plt.close(fig)
