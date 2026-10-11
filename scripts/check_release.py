#!/usr/bin/env python3
"""Check candidate packaging, metadata, links, protocol pinning and secret patterns.

Heuristic hygiene only: a passing scan does not authorize publication or prove
all private content is absent. Review the exact staged tree before publishing.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROTOCOL_FILES=("__init__.py","contract.py","interop.py","prompt_compiler.py","schemas/figure-spec-v1.schema.json","schemas/manifest-v1.schema.json","LICENSE-APACHE-2.0")


def candidate_files():
    ignored={".git",".venv","__pycache__",".pytest_cache","outputs",".evidence"}
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and not any(part in ignored for part in p.relative_to(ROOT).parts))


def check():
    import yaml
    errors=[];files=candidate_files()
    for p in files:
        rel=p.relative_to(ROOT).as_posix()
        if p.is_symlink():errors.append(f"Linked file: {rel}")
        if p.suffix in {".pyc",".zip",".pem",".key"} or p.name.startswith(".env"):errors.append(f"Unexpected candidate artifact: {rel}")
        raw=p.read_bytes()
        try:text=raw.decode("utf-8")
        except UnicodeError:continue
        patterns=(r"\b(?:sk|sk-proj)-[A-Za-z0-9_-]{20,}",r"\bgh[pousr]_[A-Za-z0-9]{20,}",r"\bAKIA[A-Z0-9]{16}\b",r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
        if any(re.search(pattern,text) for pattern in patterns):errors.append(f"Possible credential: {rel}")
        if any(marker in text for marker in ("libfile"+"_","/workspace/"+"scratch/","/agent"+"_notes/")):errors.append(f"Private task material: {rel}")
        if p.suffix==".md":
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)",text):
                if link.startswith(("http:","https:","#")):continue
                target=(p.parent/link.split("#",1)[0])
                if not target.exists():errors.append(f"Broken link: {rel} -> {link}")
    body=(ROOT/"SKILL.md").read_text();frontmatter=body.split("---",2)[1];meta=yaml.safe_load(frontmatter)
    if meta.get("name")!="academic-plotting" or not isinstance(meta.get("description"),str) or len(meta["description"])>1024:errors.append("Invalid skill discovery metadata")
    ui=yaml.safe_load((ROOT/"agents/openai.yaml").read_text())
    if "$academic-plotting" not in ui["interface"]["default_prompt"]:errors.append("Invalid UI invocation prompt")
    pin=json.loads((ROOT/"protocol/SOURCE.json").read_text())
    for name in PROTOCOL_FILES:
        sha=hashlib.sha256((ROOT/"protocol"/name).read_bytes()).hexdigest()
        if sha!=pin["files_sha256"].get(name):errors.append(f"Vendored protocol changed: {name}")
    if "Copyright (c) 2025 Claude AI Research Skills Contributors" not in (ROOT/"LICENSE").read_text():errors.append("Original MIT notice missing")
    return {"status":"passed" if not errors else "failed","candidate_files":len(files),"errors":errors,
            "limits":"Pattern/link/pinned-byte checks only. Publication needs review of the exact intended contents and authorized destination."}


if __name__=="__main__":
    report=check();print(json.dumps(report,indent=2));raise SystemExit(0 if report["status"]=="passed" else 1)
