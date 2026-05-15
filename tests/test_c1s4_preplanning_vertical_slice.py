from __future__ import annotations

import json

import pytest

from evals.c1s4_preplanning_vertical_slice.preplanning_context_bundle import build_preplanning_context_bundle
from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import (
    DEFAULT_POLICY_PATH,
    check_oracle_leakage,
    find_unexpected_session_hits,
    load_kb_manifest,
)
from evals.c1s4_preplanning_vertical_slice.step1_retrieval_context import C1S4BoundaryError, run_step1


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
    manifest, records = load_kb_manifest()
    assert manifest["forbidden_session_hits"] == []
    assert manifest["forbidden_path_hits"] == []
    assert manifest["unexpected_session_hits"] == []
    assert manifest["record_count"] > 0
    assert {int(r["session_number"]) for r in records}.issubset({1, 2, 3})


def test_step0_rejects_injected_session4_record():
    p = _policy()
    leak = check_oracle_leakage(records_or_items=[{"unit_id": "x", "session_number": 4}], heldout_sessions=p["heldout_sessions"], forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    assert leak["forbidden_session_hits"]


def test_step0_rejects_injected_session4_path():
    p = _policy()
    leak = check_oracle_leakage(records_or_items=[{"unit_id": "x", "source_recap_path": "Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md"}], heldout_sessions=p["heldout_sessions"], forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    assert leak["forbidden_path_hits"]


def test_step0_rejects_injected_unexpected_session5_record():
    hits = find_unexpected_session_hits(records=[{"unit_id": "x", "session_number": 5}], allowed_sessions=[1, 2, 3])
    assert hits


def test_step0_rejects_missing_or_malformed_session_number():
    hits = find_unexpected_session_hits(records=[{"unit_id": "x"}, {"unit_id": "y", "session_number": "bogus"}], allowed_sessions=[1, 2, 3])
    assert len(hits) == 2


def test_context_bundle_schema_contains_required_fields():
    p = _policy()
    bundle = build_preplanning_context_bundle(kb_id=p["kb_id"], campaign_id=p["campaign_id"], allowed_sessions=[1, 2, 3], heldout_sessions=[4], query="q", retrieval_result={"hits": []}, forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    for k in ["schema", "kb_id", "campaign_id", "allowed_sessions", "heldout_sessions", "query", "items", "oracle_leakage_check"]:
        assert k in bundle


def test_context_bundle_rejects_c1s4_item():
    p = _policy()
    bundle = build_preplanning_context_bundle(kb_id=p["kb_id"], campaign_id=p["campaign_id"], allowed_sessions=[1, 2, 3], heldout_sessions=[4], query="q", retrieval_result={"hits": [{"unit_id": "bad", "session_number": 4, "source_recap_path": "x"}]}, forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"])
    assert bundle["oracle_leakage_check"]["forbidden_session_hits"]


def test_context_bundle_hydrates_snippet_from_loaded_records():
    p = _policy()
    bundle = build_preplanning_context_bundle(
        kb_id=p["kb_id"],
        campaign_id=p["campaign_id"],
        allowed_sessions=[1, 2, 3],
        heldout_sessions=[4],
        query="q",
        retrieval_result={"hits": [{"unit_id": "u1", "source_recap_path": "path", "session_number": 1}]},
        forbidden_oracle_relpaths=p["forbidden_oracle_relpaths"],
        records_by_unit_id={"u1": {"unit_id": "u1", "lexical_plain": "Hydrated lexical text"}},
    )
    assert bundle["items"][0]["snippet"] == "Hydrated lexical text"


def test_step1_retrieval_smoke_produces_oracle_safe_bundle():
    out = run_step1()
    assert out["bundles"]
    for row in out["bundles"]:
        b = row["bundle"]
        assert b["allowed_sessions"] == [1, 2, 3]
        assert b["heldout_sessions"] == [4]
        assert b["oracle_leakage_check"]["forbidden_session_hits"] == []
        assert b["oracle_leakage_check"]["forbidden_path_hits"] == []
        if b["items"]:
            assert any((item.get("snippet") or "").strip() for item in b["items"])


def test_step1_refuses_to_continue_if_manifest_has_leakage(monkeypatch: pytest.MonkeyPatch):
    manifest, records = load_kb_manifest()
    bad_manifest = {**manifest, "unexpected_session_hits": ["fake:unexpected_session_5"]}

    def _fake_loader(_policy_path=DEFAULT_POLICY_PATH):
        return bad_manifest, records

    monkeypatch.setattr("evals.c1s4_preplanning_vertical_slice.step1_retrieval_context.load_kb_manifest", _fake_loader)
    with pytest.raises(C1S4BoundaryError):
        run_step1()
