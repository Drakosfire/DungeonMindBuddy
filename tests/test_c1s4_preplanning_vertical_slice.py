from __future__ import annotations

import json
from pathlib import Path

from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import DEFAULT_POLICY_PATH, check_oracle_leakage, load_kb_manifest
from evals.c1s4_preplanning_vertical_slice.step1_retrieval_context import run_step1


def _policy() -> dict:
    return json.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))


def test_kb_policy_declares_c1s1_to_c1s3_only():
    p = _policy()
    assert p["included_sessions"] == [1, 2, 3]
    assert p["heldout_sessions"] == [4]
    assert p["campaign_id"] == "longmont-c1"


def test_kb_policy_forbids_c1s4_oracle_surfaces():
    joined = "\n".join(_policy()["forbidden_oracle_relpaths"]).lower()
    for token in ["session 4 -", "_normalized", "_breadcrumbed", "_session_memory", "oracle_targets"]:
        assert token in joined


def test_step0_loads_only_allowed_sessions():
    manifest, _ = load_kb_manifest()
    assert set(manifest["records_by_session"]).issubset({"1", "2", "3"})
    assert manifest["forbidden_session_hits"] == []
    assert manifest["forbidden_path_hits"] == []
    assert manifest["record_count"] > 0


def test_step0_rejects_injected_session4_record():
    p = _policy()
    leak = check_oracle_leakage(records_or_items=[{"unit_id": "x", "session_number": 4}], heldout_sessions=p["heldout_sessions"], forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    assert leak["forbidden_session_hits"]


def test_step0_rejects_injected_session4_path():
    p = _policy()
    leak = check_oracle_leakage(records_or_items=[{"unit_id": "x", "source_recap_path": "Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md"}], heldout_sessions=p["heldout_sessions"], forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    assert leak["forbidden_path_hits"]


def test_context_bundle_schema_contains_required_fields():
    p = _policy()
    bundle = build_preplanning_context_bundle(kb_id=p["kb_id"], campaign_id=p["campaign_id"], allowed_sessions=[1,2,3], heldout_sessions=[4], query="q", retrieval_result={"hits": []}, forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    for k in ["schema", "kb_id", "campaign_id", "allowed_sessions", "heldout_sessions", "query", "items", "oracle_leakage_check"]:
        assert k in bundle


def test_context_bundle_rejects_c1s4_item():
    p = _policy()
    bundle = build_preplanning_context_bundle(kb_id=p["kb_id"], campaign_id=p["campaign_id"], allowed_sessions=[1,2,3], heldout_sessions=[4], query="q", retrieval_result={"hits": [{"unit_id": "bad", "session_number": 4, "source_recap_path": "x"}]}, forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    assert bundle["oracle_leakage_check"]["forbidden_session_hits"]


def test_step1_retrieval_smoke_produces_oracle_safe_bundle():
    out = run_step1()
    assert out["bundles"]
    for row in out["bundles"]:
        b = row["bundle"]
        assert b["allowed_sessions"] == [1, 2, 3]
        assert b["heldout_sessions"] == [4]
        assert b["oracle_leakage_check"]["forbidden_session_hits"] == []
        assert b["oracle_leakage_check"]["forbidden_path_hits"] == []
