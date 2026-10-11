#!/usr/bin/env python3
"""Read-only RFS/PaperBanana v1 consumer and offline diagram preparation.

No generated-code execution, model SDK, credential lookup, or paid generation.
The vendored protocol is unchanged; stricter file and image checks are local.
"""
from __future__ import annotations
import argparse
import io
import json
import re
import stat
import subprocess
import sys
import warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from protocol import contract,interop,prompt_compiler
from PIL import Image


def safe_path(path):
    p=Path(path).expanduser().absolute()
    for item in (p,*p.parents):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(),"st_file_attributes",0)&getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400)):
            raise contract.RFSValidationError("Symlinks and Windows reparse points are not accepted")
    return p


def portable_relative(value):
    rel=contract.validate_relative_path(value)
    for part in rel.split("/"):
        if not part or part.endswith(("."," ")) or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?",part):
            raise contract.RFSValidationError("Nonportable or ambiguous exchange artifact path")
    return rel


def decode_image(raw,mime):
    """Validate container CRCs AND actually decompress every image pixel."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error",Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as im:
                if im.width*im.height>64_000_000 or Image.MIME.get(im.format)!=mime or im.is_animated:
                    raise contract.RFSValidationError("Image MIME/pixel-limit/animation mismatch")
                im.verify()
            with Image.open(io.BytesIO(raw)) as im:
                im.load()
                return {"width":im.width,"height":im.height,"format":im.format,"fully_decoded":True}
    except (OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
        raise contract.RFSValidationError("Result image cannot be fully decoded") from exc


def validate_review_sequence(manifest):
    """Distinguish discarded attempts from the final selected review.

    The canonical schema intentionally preserves free-form review history. The
    paired runtime appends review rounds and separately records the final overall
    status. Explicit outcome/selection metadata must be consistent with the final
    overall status; an arbitrary historical pass cannot override the last result.
    Ordinary model_visual_review records without outcome fields remain evidence,
    never machine-certified scientific/visual approval.
    """
    failures={"failed","invalid","error","cancelled","partial","rejected","running","pending"}
    successes={"passed","valid","succeeded","accepted","completed"}
    neutral={"not_requested","skipped"}
    overall=manifest["review_status"].strip().casefold()
    if overall in failures or overall not in successes|neutral:
        raise contract.RFSValidationError("Unsuccessful, unknown or pending selected review cannot be accepted")
    history=manifest["review"]
    def outcome(record):
        values=[]
        for field in ("status","review_status"):
            if field in record:
                value=record[field]
                if not isinstance(value,str) or value.strip().casefold() not in failures|successes:
                    raise contract.RFSValidationError("Unknown explicit review outcome")
                values.append(value.strip().casefold())
        if values and any(v in failures for v in values) and any(v in successes for v in values):
            raise contract.RFSValidationError("Contradictory review outcome fields")
        return "failed" if any(v in failures for v in values) else ("passed" if values else None)
    outcomes=[outcome(r) for r in history]
    if history and history[-1].get("accepted") is False:
        raise contract.RFSValidationError("Final review record is explicitly not accepted")
    if not any(o is not None for o in outcomes):
        return {"mode":"protocol_history_without_explicit_outcomes","scientific_and_visual_review":"PENDING"}
    if overall not in successes or not history or outcomes[-1]!="passed":
        raise contract.RFSValidationError("Final review record is failed, unresolved or inconsistent with overall status")
    final=history[-1]
    if "accepted" in final and final["accepted"] is not True:
        raise contract.RFSValidationError("Final successful review was not selected/accepted")
    # Do not reinterpret arbitrary stage/source/round metadata as a stronger
    # selected-image binding. In the actual paired runtime source describes the
    # reviewed pre-repair stage, and the schema has no unique-round constraint.
    # Acceptance remains integrity-only; preserve history and leave visual and
    # scientific approval pending rather than inventing a verification claim.
    return {"mode":"final_explicit_outcome_consistent",
            "historical_attempts_preserved":len(history)-1,"scientific_and_visual_review":"PENDING"}


def inspect(bundle,spec_path,expected_kind=None):
    root=safe_path(bundle)
    if not root.is_dir(): raise contract.RFSValidationError("Bundle must be an existing ordinary directory")
    manifest_raw=interop.read_bytes(safe_path(root/"manifest.json"))
    manifest=contract.strict_json_input(manifest_raw.decode("utf-8"))
    if not isinstance(manifest,dict): raise contract.RFSValidationError("Manifest must be an object")
    files=manifest.get("files")
    if not isinstance(files,dict): raise contract.RFSValidationError("Manifest lacks artifact records")
    names=set()
    for role,entry in files.items():
        if not isinstance(entry,dict): raise contract.RFSValidationError("Invalid artifact record")
        rel=portable_relative(entry.get("path"));normalized=rel.casefold()
        if normalized in names or normalized in {"manifest.json","consumer-receipt.json"}:
            raise contract.RFSValidationError("Case aliases or reserved artifact names")
        names.add(normalized);safe_path(root/rel)
    expected=interop.load_spec(safe_path(spec_path))
    manifest,spec,payloads=interop.verify_result(root,expected)
    if expected_kind is not None and spec["kind"]!=expected_kind:
        raise contract.RFSValidationError("Requested task kind conflicts with the selected FigureSpec")
    review_sequence=validate_review_sequence(manifest)
    decoded={}
    for role,raw in payloads.items():
        mime=manifest["files"][role]["mime"]
        if mime.startswith("image/"): decoded[role]=decode_image(raw,mime)
        if mime=="application/json": contract.strict_json_input(raw.decode("utf-8"))
    receipt={"format":"academic-plotting-consumer/1.0","status":"INTEGRITY_ACCEPTED_REVIEW_PENDING",
             "candidate_id":manifest["candidate_id"],"figure_kind":spec["kind"],
             "protocol":interop.descriptor(),"producer_manifest_sha256":interop.digest(manifest_raw),
             "scientific_fingerprint":contract.scientific_fingerprint(spec),"images":decoded,"review_sequence":review_sequence,
             "producer_flags_preserved":True,"scientific_claims_verified":False,"editable_reconstruction_verified":False,
             "model_calls":0,"generated_code_executed":False,"scientific_review":"PENDING","visual_review":"PENDING",
             "quantitative_review":"independent source/unit/statistical verification required" if spec["kind"] in ("plot","hybrid") else "not_applicable"}
    return receipt,manifest_raw,manifest,payloads


def consume(bundle,spec_path,output,expected_kind=None):
    receipt,manifest_raw,manifest,payloads=inspect(bundle,spec_path,expected_kind)
    source=safe_path(bundle);target=safe_path(output)
    if target.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(target.resolve()):
        raise contract.RFSValidationError("Consumer destination must be separate from producer bundle")
    copies={manifest["files"][role]["path"]:raw for role,raw in payloads.items()}
    copies["manifest.json"]=manifest_raw
    copies["consumer-receipt.json"]=interop.json_bytes(receipt)
    interop.write_new_folder(target,copies)
    try:
        inspect(target,spec_path,expected_kind)
    except BaseException:
        import shutil
        shutil.rmtree(target)
        raise
    return receipt


def check_peer(paperbanana_root):
    root=safe_path(paperbanana_root);entry=safe_path(root/"skill/exchange.py")
    if not entry.is_file(): raise contract.RFSValidationError("Peer must provide skill/exchange.py")
    result=subprocess.run([sys.executable,str(entry),"describe"],cwd=root,text=True,capture_output=True,timeout=30,check=False)
    if result.returncode: raise contract.RFSValidationError("PaperBanana protocol preflight failed in the selected interpreter")
    peer=contract.strict_json_input(result.stdout);interop.assert_compatible(peer)
    return {"status":"COMPATIBLE","protocol":peer,"live_provider_tested":False}


def compile_draft(spec_path,design_path,capabilities_path,output,candidate="0"):
    spec=interop.load_spec(safe_path(spec_path))
    if spec["kind"]!="diagram" or spec["datasets"]:
        raise contract.RFSValidationError("Measured plots/hybrid data cannot be sent to an image generator; split hybrid panels")
    design=interop.read_bytes(safe_path(design_path)).decode("utf-8")
    capabilities=interop.read_object(safe_path(capabilities_path))
    result=prompt_compiler.compile_prompt(spec,design,capabilities,candidate_id=candidate)
    payloads={"figure-spec.json":interop.json_bytes(spec),"prompt.txt":result.prompt.encode("utf-8"),
              "design-intent.md":design.encode("utf-8"),"compiler-metadata.json":interop.json_bytes(result.metadata)}
    if result.system_prompt is not None: payloads["system-prompt.txt"]=result.system_prompt.encode("utf-8")
    receipt={"format":"academic-plotting-draft/1.0","status":"PROMPT_READY_NOT_RENDERED",
             "model_access_verified":False,"model_calls":0,"scientific_review":"PENDING",
             "files_sha256":{name:interop.digest(raw) for name,raw in payloads.items()}}
    payloads["draft-receipt.json"]=interop.json_bytes(receipt)
    interop.write_new_folder(safe_path(output),payloads)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("describe")
    peer=sub.add_parser("check-peer");peer.add_argument("--paperbanana-root",required=True,type=Path)
    prep=sub.add_parser("prepare-request");prep.add_argument("--spec",required=True,type=Path);prep.add_argument("--output",required=True,type=Path)
    prep.add_argument("--candidates",type=int,default=2);prep.add_argument("--image-model");prep.add_argument("--main-model")
    draft=sub.add_parser("compile-prompt")
    for name in ("spec","design","capabilities","output"): draft.add_argument("--"+name,required=True,type=Path)
    draft.add_argument("--candidate",default="0")
    for name in ("inspect","consume"):
        parser=sub.add_parser(name);parser.add_argument("--bundle",required=True,type=Path);parser.add_argument("--spec",required=True,type=Path)
        parser.add_argument("--expected-kind",choices=("diagram","plot","hybrid"))
        if name=="consume": parser.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    try:
        if args.command=="describe": result=interop.descriptor()
        elif args.command=="check-peer": result=check_peer(args.paperbanana_root)
        elif args.command=="compile-prompt": result=compile_draft(args.spec,args.design,args.capabilities,args.output,args.candidate)
        elif args.command=="prepare-request":
            spec_path=safe_path(args.spec);output=safe_path(args.output)
            options={k:getattr(args,k) for k in ("image_model","main_model") if getattr(args,k) is not None}
            req=interop.prepare_request(spec_path,output,candidates=args.candidates,**options)
            result={"status":"REQUEST_READY_NOT_EXECUTED","request":"request.json","model_calls":0,
                    "protocol":interop.descriptor(),"paperbanana_arguments":interop.request_argv(req)}
        elif args.command=="consume": result=consume(args.bundle,args.spec,args.output,args.expected_kind)
        else: result=inspect(args.bundle,args.spec,args.expected_kind)[0]
        print(json.dumps(result,indent=2,ensure_ascii=False));return 0
    except (ValueError,OSError,ImportError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status":"ERROR","reason":str(exc)},ensure_ascii=False),file=sys.stderr);return 2


if __name__=="__main__": raise SystemExit(main())
