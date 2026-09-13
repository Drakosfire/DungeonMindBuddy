import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from extraction_lab.campaign_memory_exploratory_screen_manifest import (
    BENCHMARK,
    MODELS,
    Execution,
    build_screen_manifest_payload,
    load_screen_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40


def test_manifest_requires_exact_model_order_and_contract() -> None:
    valid = {
        "mode": "flex",
        "cache_policy": "isolated",
        "repetitions": 1,
        "batch_size": 5,
        "reasoning_effort": "medium",
        "fact_contract": "payload_lean_v1",
        "models": list(MODELS),
    }
    assert Execution.model_validate(valid).models == MODELS
    invalid = dict(valid)
    invalid["models"] = list(reversed(valid["models"]))
    with pytest.raises(ValidationError):
        Execution.model_validate(invalid)
    missing = dict(valid)
    missing["models"] = ["gpt-5.6-luna", "gpt-5.6-sol"]
    with pytest.raises(ValidationError):
        Execution.model_validate(missing)
    extra = dict(valid)
    extra["models"] = [*MODELS, "gpt-5.6-sol"]
    with pytest.raises(ValidationError):
        Execution.model_validate(extra)
    bad_effort = dict(valid)
    bad_effort["reasoning_effort"] = "high"
    with pytest.raises(ValidationError):
        Execution.model_validate(bad_effort)


def test_built_manifest_loads_frozen_seven_source_pins(tmp_path: Path) -> None:
    payload = build_screen_manifest_payload(repo_root=ROOT, repository_sha=SHA)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    manifest, ctx = load_screen_manifest(path, repo_root=ROOT)
    assert manifest.execution.models == MODELS
    assert manifest.execution.mode == "flex"
    assert manifest.execution.reasoning_effort == "medium"
    assert manifest.execution.fact_contract == "payload_lean_v1"
    assert manifest.execution.repetitions == 1
    assert len(ctx["sources"]) == 7
    assert ctx["benchmark_path"] == (ROOT / BENCHMARK).resolve()
    assert ctx["entity_gold"].is_file()
    assert ctx["fact_gold"].is_file()


def test_rejects_wrong_gold_pin(tmp_path: Path) -> None:
    payload = build_screen_manifest_payload(repo_root=ROOT, repository_sha=SHA)
    payload["pins"]["gold_fingerprint"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="pins"):
        load_screen_manifest(path, repo_root=ROOT)
