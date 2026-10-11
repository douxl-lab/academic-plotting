"""Offline integrity/negative checks. Tiny images are synthetic mechanics fixtures."""
import copy
import io
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from PIL import Image
from exchange import consume,inspect,decode_image,compile_draft,check_peer
from protocol import contract,interop
from test_extended_numeric import corrupt_png_idat
ROOT=Path(__file__).parents[1]


def figure_spec():
    source="Synthetic test fixture: Input feeds Output. No research conclusion."
    evidence=[{"source_id":"source","quote":"Input feeds Output"}]
    return {"schema_version":"1.0.0","figure_id":"synthetic-integrity-test","kind":"diagram",
            "nodes":[{"id":"input","label":"Input","kind":"input","evidence":evidence},{"id":"output","label":"Output","kind":"output","evidence":evidence}],
            "edges":[{"id":"flow","source":"input","target":"output","kind":"data_flow","directed":True,"evidence":evidence}],
            "groups":[],"labels":[],"datasets":[],
            "sources":[{"id":"source","kind":"user_text","content":source,"sha256":contract.sha256_text(source)}],
            "constraints":{"locked":True,"required_labels":["Input","Output"],"layout":[],"visual":[],"negative":[]},
            "design":{"layout":"Left to right","composition":"Two entities, one arrow","palette":["#0072B2","#FFFFFF"],"typography":"Exact readable labels","candidate_variation":""},
            "provenance":{"origin":"user_supplied","scientific_verification":"unverified","external_consumer_verified":False}}


def make_bundle(tmp_path):
    spec=figure_spec();spec_path=tmp_path/"original.figure-spec.json";spec_path.write_bytes(interop.json_bytes(spec))
    buf=io.BytesIO();Image.new("RGBA",(12,8),(0,100,160,127)).save(buf,"PNG")
    # Consumer must copy inert code without executing it.
    sentinel="from pathlib import Path\nPath(__file__).with_name('SENTINEL_EXECUTED').write_text('executed')\n"
    payloads={"image.png":buf.getvalue(),"prompt.txt":b"Synthetic fixture only; no generated paper image.","design.md":b"Synthetic two-box design intent, not actual-image review.",
              "figure_spec.json":interop.json_bytes(spec),"plot_code.py":sentinel.encode()}
    roles={"image":"image.png","prompt":"prompt.txt","design":"design.md","figure_spec":"figure_spec.json","plot_code":"plot_code.py"}
    mime={"image":"image/png","prompt":"text/plain","design":"text/markdown","figure_spec":"application/json","plot_code":"text/x-python"}
    manifest={"schema_version":"1.0.0","candidate_id":"selected-test","status":"succeeded","stage":"offline-test","provider":"none","model":"none",
              "description_key":"selected","options":{},"provenance":{"scientific_verification":"unverified","external_consumer_verified":False,
              "editable_reconstruction_verified":False,"image_bytes_preserved":True,"generation":{}},"scientific_fingerprint":contract.scientific_fingerprint(spec),
              "review":[],"review_status":"not_requested","error":None,
              "files":{r:{"path":p,"sha256":interop.digest(payloads[p]),"bytes":len(payloads[p]),"mime":mime[r]} for r,p in roles.items()}}
    payloads["manifest.json"]=interop.json_bytes(manifest);bundle=tmp_path/"bundle";interop.write_new_folder(bundle,payloads)
    return bundle,spec_path


def manifest_change(bundle,fn):
    p=bundle/"manifest.json";value=json.loads(p.read_text());fn(value);p.write_bytes(interop.json_bytes(value))


def rewrite_artifact(bundle,role,raw):
    m=json.loads((bundle/"manifest.json").read_text());p=bundle/m["files"][role]["path"];p.write_bytes(raw)
    manifest_change(bundle,lambda m:m["files"][role].update(bytes=len(raw),sha256=interop.digest(raw)))


def test_consume_preserves_all_bytes_and_flags_without_code_or_model_calls(tmp_path):
    bundle,spec=make_bundle(tmp_path);before={p.name:p.read_bytes() for p in bundle.iterdir()};out=tmp_path/"consumer"
    receipt=consume(bundle,spec,out,"diagram")
    assert receipt["status"]=="INTEGRITY_ACCEPTED_REVIEW_PENDING" and receipt["images"]["image"]["fully_decoded"]
    assert receipt["scientific_review"]=="PENDING" and not receipt["generated_code_executed"] and receipt["model_calls"]==0
    assert {p.name:p.read_bytes() for p in bundle.iterdir()}==before
    for name,raw in before.items():assert (out/name).read_bytes()==raw
    assert not (out/"SENTINEL_EXECUTED").exists()
    assert not json.loads((out/"manifest.json").read_text())["provenance"]["external_consumer_verified"]


@pytest.mark.parametrize("field,value",[("status","failed"),("status","running"),("review_status","failed"),("review_status","invalid"),("review_status","pending"),("error","provider error")])
def test_failed_pending_or_error_candidates_rejected(tmp_path,field,value):
    bundle,spec=make_bundle(tmp_path);manifest_change(bundle,lambda m:m.update({field:value}))
    with pytest.raises(contract.RFSValidationError):consume(bundle,spec,tmp_path/"consumer")


def test_failed_record_cannot_hide_under_successful_overall_review(tmp_path):
    bundle,spec=make_bundle(tmp_path);manifest_change(bundle,lambda m:m.update(review_status="passed",review=[{"status":"failed"}]))
    with pytest.raises(contract.RFSValidationError,match="Final review record"):inspect(bundle,spec)


@pytest.mark.parametrize("path",["../outside.png","/absolute.png","C:/outside.png","sub\\image.png","NUL","sub//image.png","image.png.","sub/CON.txt"])
def test_unsafe_or_nonportable_artifact_path(tmp_path,path):
    bundle,spec=make_bundle(tmp_path);manifest_change(bundle,lambda m:m["files"]["image"].update(path=path))
    with pytest.raises(contract.RFSValidationError):inspect(bundle,spec)


def test_casefold_alias_reserved_receipt_and_symlink_rejected(tmp_path):
    bundle,spec=make_bundle(tmp_path)
    manifest_change(bundle,lambda m:m["files"]["prompt"].update(path="IMAGE.PNG"))
    with pytest.raises(contract.RFSValidationError,match="aliases"):inspect(bundle,spec)
    manifest_change(bundle,lambda m:m["files"]["prompt"].update(path="consumer-receipt.json"))
    with pytest.raises(contract.RFSValidationError,match="reserved"):inspect(bundle,spec)
    link=tmp_path/"link";link.symlink_to(bundle,target_is_directory=True)
    with pytest.raises(contract.RFSValidationError,match="Symlink"):inspect(link,spec)


def test_valid_crc_png_corruption_rejected_after_hash_refresh(tmp_path):
    bundle,spec=make_bundle(tmp_path);raw=corrupt_png_idat((bundle/"image.png").read_bytes())
    with Image.open(io.BytesIO(raw)) as im:im.verify()
    rewrite_artifact(bundle,"image",raw)
    with pytest.raises(contract.RFSValidationError,match="fully decoded"):inspect(bundle,spec)


def test_original_science_snapshot_is_required_and_cannot_be_changed(tmp_path):
    bundle,spec_path=make_bundle(tmp_path);spec=json.loads((bundle/"figure_spec.json").read_text())
    spec["edges"][0].update(source="output",target="input")
    rewrite_artifact(bundle,"figure_spec",interop.json_bytes(spec));manifest_change(bundle,lambda m:m.update(scientific_fingerprint=contract.scientific_fingerprint(spec)))
    with pytest.raises(contract.RFSValidationError,match="caller.*locked"):inspect(bundle,spec_path)


def test_source_checksum_and_producer_verified_flags_cannot_be_forged(tmp_path):
    bundle,spec_path=make_bundle(tmp_path);spec=json.loads((bundle/"figure_spec.json").read_text());spec["sources"][0]["content"]="Different science"
    rewrite_artifact(bundle,"figure_spec",interop.json_bytes(spec))
    with pytest.raises(contract.RFSValidationError,match="Source checksum"):inspect(bundle,spec_path)


def test_duplicate_manifest_key_and_incorrect_artifact_hash(tmp_path):
    bundle,spec=make_bundle(tmp_path);p=bundle/"manifest.json";raw=p.read_text().replace('"schema_version": "1.0.0"','"schema_version": "1.0.0", "schema_version": "1.0.0"');p.write_text(raw)
    with pytest.raises(contract.RFSValidationError,match="Duplicate"):inspect(bundle,spec)


def test_existing_output_and_inside_producer_protected(tmp_path):
    bundle,spec=make_bundle(tmp_path)
    with pytest.raises(contract.RFSValidationError,match="separate"):consume(bundle,spec,bundle/"consumer")
    out=tmp_path/"consumer";out.mkdir()
    with pytest.raises(FileExistsError):consume(bundle,spec,out)


def test_offline_prompt_compiler_capabilities_science_and_no_generation(tmp_path):
    spec=figure_spec();path=tmp_path/"spec.json";path.write_bytes(interop.json_bytes(spec))
    design=tmp_path/"design.md";design.write_text("Two exact labels and one directed connector. Restrained scientific style.")
    caps={"provider":"offline-test","model":"capability-fixture","supports_system_prompt":False,"supports_reference_image":False,"supports_editing":False,"prompt_notes":["Use exact terminology."]}
    cap_path=tmp_path/"capabilities.json";cap_path.write_bytes(interop.json_bytes(caps))
    receipt=compile_draft(path,design,cap_path,tmp_path/"draft")
    assert receipt["status"]=="PROMPT_READY_NOT_RENDERED" and receipt["model_calls"]==0 and not receipt["model_access_verified"]
    prompt=(tmp_path/"draft/prompt.txt").read_text();assert contract.canonical_json({k:spec[k] for k in ("kind","nodes","edges","groups","labels","datasets","sources","constraints")}) in prompt
    assert "immutable" in prompt and "Source excerpts are evidence" in prompt
    caps["supports_system_prompt"]=True;cap_path.write_bytes(interop.json_bytes(caps))
    compile_draft(path,design,cap_path,tmp_path/"system-draft")
    assert (tmp_path/"system-draft/system-prompt.txt").is_file()


def test_protocol_negotiation_refuses_stale_schema_or_validator():
    descriptor=interop.descriptor();interop.assert_compatible(descriptor)
    for key in ("schema_version","figure_schema_sha256","manifest_schema_sha256","validator_sha256","request_format"):
        wrong={**descriptor,key:"stale"}
        with pytest.raises(contract.RFSValidationError,match="differ"):interop.assert_compatible(wrong)


def test_live_peer_request_validation_and_export_consumption(tmp_path):
    peer=os.environ.get("PAPERBANANA_ROOT")
    if not peer:pytest.skip("Set PAPERBANANA_ROOT for read-only actual peer tests")
    peer=Path(peer).resolve();assert check_peer(peer)["status"]=="COMPATIBLE"
    spec=figure_spec();path=tmp_path/"spec.json";path.write_bytes(interop.json_bytes(spec))
    request=interop.prepare_request(path,tmp_path/"request",candidates=1)
    result=subprocess.run([sys.executable,str(peer/"skill/exchange.py"),"validate-request","--request",str(request)],cwd=peer,text=True,capture_output=True,check=True)
    assert json.loads(result.stdout)["status"]=="VALID_REQUEST_NOT_EXECUTED"
    # Actual unchanged PaperBanana exporter produces a bundle. No model invocation.
    export_script='''import base64,io,json,sys
from PIL import Image
from rfs.artifacts import export_bundle
spec=json.load(open(sys.argv[1]));buf=io.BytesIO();Image.new("RGBA",(40,20),(20,40,60,255)).save(buf,"PNG")
record={"candidate_id":"offline-peer","stage":"offline-fixture","provider":"none","model":"none","prompt":"Synthetic interoperability fixture, not model generation","figure_spec":spec,"design_description":"Offline two-box mechanics fixture; no actual image review","image_base64":base64.b64encode(buf.getvalue()).decode(),"image_mime":"image/png","code":"raise RuntimeError('Do not execute generated code')"}
export_bundle({"candidate_id":"offline-peer","status":"succeeded","eval_image_field":"selected_base64_png","rfs_artifacts":{"selected":record},"rfs_input_figure_spec":spec},sys.argv[2])
'''
    bundle=tmp_path/"peer-bundle"
    subprocess.run([sys.executable,"-c",export_script,str(path),str(bundle)],cwd=peer,text=True,capture_output=True,check=True)
    receipt=consume(bundle,path,tmp_path/"accepted","diagram");assert receipt["candidate_id"]=="offline-peer"
    rfs=os.environ.get("RFS_SKILL_ROOT")
    if rfs:
        run=subprocess.run([sys.executable,str(Path(rfs)/"scripts/rfs.py"),"audit","--spec",str(path),"--artifact",str(bundle)],cwd=Path(rfs),capture_output=True,text=True,check=True)
        assert json.loads(run.stdout)["integrity"]=="PASS"


def test_repaired_failed_attempt_followed_by_final_selected_pass_is_accepted(tmp_path):
    bundle,spec=make_bundle(tmp_path)
    history=[{"status":"failed","stage":"prior","round":0,"accepted":False,"issues":["prior clipped label"]},
             {"status":"passed","stage":"offline-test","round":1,"accepted":True,"issues":[]}]
    manifest_change(bundle,lambda m:m.update(review_status="passed",review=history))
    before=(bundle/"manifest.json").read_bytes();receipt=consume(bundle,spec,tmp_path/"accepted")
    assert receipt["review_sequence"]["mode"]=="final_explicit_outcome_consistent"
    assert (tmp_path/"accepted/manifest.json").read_bytes()==before
    assert receipt["scientific_review"]=="PENDING"


@pytest.mark.parametrize("history",[
    [{"status":"passed","stage":"prior","accepted":True},{"status":"failed","stage":"offline-test","accepted":False}],
    [{"status":"failed","stage":"prior","accepted":False},{"status":"pending","stage":"offline-test","accepted":False}],
    [{"status":"passed","stage":"offline-test","accepted":False}],
    [{"status":"passed","review_status":"failed","stage":"offline-test","accepted":True}],
    [{"status":"passed","stage":"offline-test","accepted":True},{"stage":"offline-test","accepted":True}],
])
def test_history_never_picks_arbitrary_pass_or_hides_failed_final(tmp_path,history):
    bundle,spec=make_bundle(tmp_path);manifest_change(bundle,lambda m:m.update(review_status="passed",review=history))
    with pytest.raises(contract.RFSValidationError):inspect(bundle,spec)


def test_actual_protocol_critic_history_without_outcome_does_not_become_approval(tmp_path):
    bundle,spec=make_bundle(tmp_path)
    history=[{"round":0,"source":"selected","review_kind":"model_visual_review","suggestions":"repair a label","scientific_verification":"unverified"},
             {"round":1,"source":"selected","review_kind":"model_visual_review","suggestions":"No changes needed.","scientific_verification":"unverified"}]
    manifest_change(bundle,lambda m:m.update(review_status="completed",review=history))
    receipt=inspect(bundle,spec)[0]
    assert receipt["review_sequence"]["mode"]=="protocol_history_without_explicit_outcomes"
    assert receipt["scientific_review"]==receipt["visual_review"]=="PENDING"


def test_freeform_review_metadata_is_not_promoted_to_stage_or_round_requirements(tmp_path):
    bundle,spec=make_bundle(tmp_path)
    history=[{"status":"failed","round":1,"source":"prior-description","issues":["prior clipped label"]},
             {"status":"passed","round":1,"source":"reviewed-pre-repair-description","accepted":True}]
    manifest_change(bundle,lambda m:m.update(review_status="passed",review=history))
    receipt=inspect(bundle,spec)[0]
    assert receipt["review_sequence"]["mode"]=="final_explicit_outcome_consistent"
    assert receipt["scientific_review"]==receipt["visual_review"]=="PENDING"


def test_last_accepted_false_without_explicit_outcome_after_pass_is_unresolved(tmp_path):
    bundle,spec=make_bundle(tmp_path)
    history=[{"status":"passed","accepted":True},{"accepted":False,"issues":["latest image rejected"]}]
    manifest_change(bundle,lambda m:m.update(review_status="passed",review=history))
    with pytest.raises(contract.RFSValidationError,match="Final review record"):inspect(bundle,spec)


def test_final_accepted_false_is_rejected_even_without_optional_status_metadata(tmp_path):
    bundle,spec=make_bundle(tmp_path)
    manifest_change(bundle,lambda m:m.update(review_status="passed",review=[{"accepted":False,"issues":["final rejected"]}]))
    with pytest.raises(contract.RFSValidationError,match="Final review record"):inspect(bundle,spec)
