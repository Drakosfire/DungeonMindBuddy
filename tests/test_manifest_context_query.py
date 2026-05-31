"""Tests for blind manifest-backed query/admission runner."""

from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest

from src.live_play.manifest_context_query import (
    QueryRequest,
    build_context_packet,
    build_query_plan,
    load_manifest,
)
from src.live_play.session_paths import repo_root

ROOT = repo_root()
MANIFEST_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
QUESTIONS_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_manifest(MANIFEST_PATH)


def _request(qid: str, question: str, *, category: str | None = None) -> QueryRequest:
    return QueryRequest(question_id=qid, question=question, category=category)


def test_runner_does_not_load_gold_file(monkeypatch: pytest.MonkeyPatch) -> None:
    real_open = builtins.open

    def guarded_open(path, *args, **kwargs):
        if "gold" in str(path).lower():
            raise AssertionError("runner must not read gold")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)
    manifest = load_manifest(MANIFEST_PATH)
    packet = build_context_packet(
        _request("probe", "What pipeline state must be true before Session 22 activation?"),
        manifest,
        root=ROOT,
    )
    assert packet["schema"] == "dmb_enriched_planning_context_packet_v1"


def test_runner_does_not_read_dogfood_trace_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    real_open = builtins.open
    forbidden = ("c2s23_dogfood_", "c2s23_dogfood_planner_summary")

    def guarded_open(path, *args, **kwargs):
        p = str(path)
        if any(token in p for token in forbidden):
            raise AssertionError("runner must not read dogfood trace artifacts")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)
    manifest = load_manifest(MANIFEST_PATH)
    build_context_packet(_request("probe", "Can I create a roll table from live control?"), manifest, root=ROOT)


def test_question_id_does_not_affect_query_plan() -> None:
    q1 = _request("s22-ingest-03", "Is Session 22 ready for planning activation?")
    q2 = _request("different-id-entirely", "Is Session 22 ready for planning activation?")
    assert build_query_plan(q1) == build_query_plan(q2)


def test_question_id_does_not_affect_admission_decisions(manifest: dict) -> None:
    question = "Is Session 22 ready for planning activation?"
    p1 = build_context_packet(_request("s22-ingest-03", question), manifest, root=ROOT)
    p2 = build_context_packet(_request("different-id-entirely", question), manifest, root=ROOT)

    def evidence_key(packet: dict) -> tuple:
        admitted = tuple(sorted(str(e.get("path") or "") for e in packet["admitted_evidence"]))
        rejected = tuple(
            sorted(
                (str(r["evidence"].get("path") or ""), str(r.get("reason_code") or ""))
                for r in packet["rejected_evidence"]
            )
        )
        return admitted, rejected

    assert evidence_key(p1) == evidence_key(p2)


def test_same_question_with_different_id_emits_same_evidence_sets(manifest: dict) -> None:
    question = "After ingesting raw Session 22 table notes, what play outcomes carry into Session 23 prep?"
    p1 = build_context_packet(_request("s22-ingest-01", question), manifest, root=ROOT)
    p2 = build_context_packet(_request("alt-id", question), manifest, root=ROOT)
    assert {e["path"] for e in p1["admitted_evidence"]} == {e["path"] for e in p2["admitted_evidence"]}


def test_seed_category_absent_still_runs(manifest: dict) -> None:
    packet = build_context_packet(
        _request("no-category", "What happened in Session 22 at the table?", category=None),
        manifest,
        root=ROOT,
    )
    assert packet["admitted_evidence"] or packet["rejected_evidence"]


def test_seed_expectation_fields_are_ignored_by_runner(manifest: dict) -> None:
    seed = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    row = next(q for q in seed["questions"] if q["id"] == "s22-ingest-01")
    packet = build_context_packet(
        _request(row["id"], row["question"], category=row.get("category")),
        manifest,
        root=ROOT,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "prep_scaffold" not in admitted_roles


def test_play_fact_admits_canon_recap(manifest: dict) -> None:
    packet = build_context_packet(
        _request(
            "play-fact",
            "What are the three most important Session 22 play outcomes to carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
    )
    authorities = {e.get("authority") for e in packet["admitted_evidence"]}
    assert authorities & {"canon_play", "derived_memory"}
    paths = " ".join(str(e.get("path") or "") for e in packet["admitted_evidence"])
    assert "Session 22 - Mireward Road and Lysandro" in paths


def test_play_fact_rejects_staged_notes_even_if_manifest_admissible_for_provenance(manifest: dict) -> None:
    packet = build_context_packet(
        _request("play-fact", "What Session 22 play outcomes happened at the table in Session 22 recap?"),
        manifest,
        root=ROOT,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "table_notes" not in admitted_roles
    rejected_paths = [str(r["evidence"].get("path") or "") for r in packet["rejected_evidence"]]
    assert any("session_22_raw_notes" in p for p in rejected_paths)


def test_pipeline_state_uses_audit_preconditions(manifest: dict) -> None:
    packet = build_context_packet(
        _request(
            "pipeline",
            "What pipeline state must be true before Session 22 is ready_for_planning_activation?",
        ),
        manifest,
        root=ROOT,
    )
    authorities = {e.get("authority") for e in packet["admitted_evidence"]}
    assert "audit" in authorities
    assert packet["corpus_preconditions"]["all_required_present"] is True


def test_pipeline_state_rejects_prep_scaffold(manifest: dict) -> None:
    packet = build_context_packet(
        _request(
            "pipeline",
            "What ingest readiness and normalized/breadcrumb/session memory states are required for Session 22 activation?",
        ),
        manifest,
        root=ROOT,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "prep_scaffold" not in admitted_roles


def test_capability_check_reports_missing_location_write(manifest: dict) -> None:
    packet = build_context_packet(
        _request(
            "loc",
            "Can I create a new named sub-location hub markdown file for a waystation north of the last stop?",
        ),
        manifest,
        root=ROOT,
    )
    assert packet["capability_status"]["status"] in {"missing", "partial", "unknown"}
    codes = {b.get("code") for b in packet["blocked_or_missing"]}
    assert "missing_live_write_capability" in codes


def test_capability_check_reports_missing_roll_table_create(manifest: dict) -> None:
    packet = build_context_packet(
        _request(
            "roll",
            "Can I add a new swamp-side random encounter table and register it on the packet and patch rows?",
        ),
        manifest,
        root=ROOT,
    )
    assert packet["capability_status"]["status"] in {"missing", "partial", "unknown"}
    codes = {b.get("code") for b in packet["blocked_or_missing"]}
    assert "missing_roll_table_create_register_capability" in codes


def test_auth_guardrail_rejects_staging_for_normal_play_fact_evidence(manifest: dict) -> None:
    packet = build_context_packet(
        _request(
            "auth",
            "After canonical Session 22 recap exists, may I still use raw staged table notes as normal retrieval evidence for play-fact questions?",
        ),
        manifest,
        root=ROOT,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "table_notes" not in admitted_roles
    excerpt = str(packet.get("source_excerpt") or "")
    assert "No" in excerpt or "not as normal retrieval evidence" in excerpt


def test_rejected_evidence_preserves_reason_codes(manifest: dict) -> None:
    packet = build_context_packet(
        _request("auth", "May raw staged table notes prove play facts after Session 22 recap exists?"),
        manifest,
        root=ROOT,
    )
    assert packet["rejected_evidence"]
    for row in packet["rejected_evidence"]:
        assert str(row.get("reason_code") or "").strip()
