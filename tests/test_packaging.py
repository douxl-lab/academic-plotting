import importlib.util
import json
from pathlib import Path
import yaml
ROOT=Path(__file__).parents[1]


def test_release_hygiene():
    spec=importlib.util.spec_from_file_location("release_check",ROOT/"scripts/check_release.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.check();assert result["status"]=="passed",result["errors"]


def test_bilingual_matching_corpus_boundaries_without_claiming_host_accuracy():
    corpus=json.loads((ROOT/"tests/agent_matching_cases.json").read_text());cases=corpus["cases"]
    assert len({c["id"] for c in cases})==len(cases) and {c["lang"] for c in cases}=={"zh","en"}
    assert sum(c["activate"] for c in cases)>=8 and sum(not c["activate"] for c in cases)>=5
    assert any(c["expected_route"]=="clarify-unsupported-uncertainty" for c in cases)
    assert sum(c["expected_route"]=="explicit-other-skill" for c in cases)>=2
    assert all(type(c["activate"]) is bool and c["prompt"] and c["scientific_input"] for c in cases)
    assert "not measured" in corpus["notice"]


def test_metadata_auto_discovery_is_not_disabled():
    ui=yaml.safe_load((ROOT/"agents/openai.yaml").read_text())
    assert ui.get("policy",{}).get("allow_implicit_invocation",True)
    assert 25<=len(ui["interface"]["short_description"])<=64
