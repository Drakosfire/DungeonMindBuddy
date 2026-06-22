"""Tests for blind manifest-backed query/admission runner."""

from __future__ import annotations

import builtins
import json
from pathlib import Path
from typing import Any

import pytest

from src.live_play.manifest_context_query import (
    QueryConfig,
    QueryRequest,
    _session_number_from_path,
    build_context_packet,
    build_query_plan,
    load_manifest,
)
from src.live_play.session_paths import repo_root

ROOT = repo_root()
MANIFEST_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
DOGFOOD_MANIFEST_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_dogfood_full_manifest.json"
QUESTIONS_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json"
C2S23_PRECONDITION_PATHS: dict[str, str] = {
    "canonical_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/"
        "Session 22 - Mireward Road and Lysandro.md"
    ),
    "normalized_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    ),
    "breadcrumb_recap_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.breadcrumbed.md"
    ),
    "session_memory_jsonl_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/"
        "Session 22 - Mireward Road and Lysandro.records_meta.jsonl"
    ),
    "session_memory_meta_s22": (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/"
        "Session 22 - Mireward Road and Lysandro.records_meta.json"
    ),
    "live_workspace_s23_packet": "evals/c2_live_prep/live/session_23/live_packet.json",
    "activated_manifest": "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json",
}


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_manifest(MANIFEST_PATH)


@pytest.fixture(scope="module")
def query_config() -> QueryConfig:
    return QueryConfig(
        precondition_paths=C2S23_PRECONDITION_PATHS,
        virtual_precondition_path="virtual://c2s23/corpus_preconditions/session_22",
        virtual_precondition_session_scope=(22,),
    )


def _request(qid: str, question: str, *, category: str | None = None) -> QueryRequest:
    return QueryRequest(question_id=qid, question=question, category=category)


def _write_markdown(root: Path, route: str, body: str) -> None:
    p = root / route
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def _manifest_entry(
    *,
    source_id: str,
    route: str,
    source_role: str,
    authority: str,
    session_scope: list[int],
    lexical_terms: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_role": source_role,
        "authority": authority,
        "session_scope": session_scope,
        "route": route,
        "route_exists": True,
        "admissible": True,
        "allowed_uses": ["play_facts", "planning_context"],
        "forbidden_uses": [],
        "lexical_terms": lexical_terms or [],
        "notes": [],
    }


def test_runner_does_not_load_gold_file(monkeypatch: pytest.MonkeyPatch, query_config: QueryConfig) -> None:
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
        config=query_config,
    )
    assert packet["schema"] == "dmb_enriched_planning_context_packet_v1"


def test_runner_does_not_read_dogfood_trace_artifacts(
    monkeypatch: pytest.MonkeyPatch, query_config: QueryConfig
) -> None:
    real_open = builtins.open
    forbidden = ("c2s23_dogfood_", "c2s23_dogfood_planner_summary")

    def guarded_open(path, *args, **kwargs):
        p = str(path)
        if any(token in p for token in forbidden):
            raise AssertionError("runner must not read dogfood trace artifacts")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)
    manifest = load_manifest(MANIFEST_PATH)
    build_context_packet(_request("probe", "Can I create a roll table from live control?"), manifest, root=ROOT, config=query_config)


def test_question_id_does_not_affect_query_plan() -> None:
    q1 = _request("s22-ingest-03", "Is Session 22 ready for planning activation?")
    q2 = _request("different-id-entirely", "Is Session 22 ready for planning activation?")
    assert build_query_plan(q1) == build_query_plan(q2)


def test_question_id_does_not_affect_admission_decisions(manifest: dict, query_config: QueryConfig) -> None:
    question = "Is Session 22 ready for planning activation?"
    p1 = build_context_packet(_request("s22-ingest-03", question), manifest, root=ROOT, config=query_config)
    p2 = build_context_packet(_request("different-id-entirely", question), manifest, root=ROOT, config=query_config)

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


def test_same_question_with_different_id_emits_same_evidence_sets(manifest: dict, query_config: QueryConfig) -> None:
    question = "After ingesting raw Session 22 table notes, what play outcomes carry into Session 23 prep?"
    p1 = build_context_packet(_request("s22-ingest-01", question), manifest, root=ROOT, config=query_config)
    p2 = build_context_packet(_request("alt-id", question), manifest, root=ROOT, config=query_config)
    assert {e["path"] for e in p1["admitted_evidence"]} == {e["path"] for e in p2["admitted_evidence"]}


def test_seed_category_absent_still_runs(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("no-category", "What happened in Session 22 at the table?", category=None),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert packet["admitted_evidence"] or packet["rejected_evidence"]


def test_seed_expectation_fields_are_ignored_by_runner(manifest: dict, query_config: QueryConfig) -> None:
    seed = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    row = next(q for q in seed["questions"] if q["id"] == "s22-ingest-01")
    packet = build_context_packet(
        _request(row["id"], row["question"], category=row.get("category")),
        manifest,
        root=ROOT,
        config=query_config,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "prep_scaffold" not in admitted_roles


def test_play_fact_admits_canon_recap(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "play-fact",
            "What are the three most important Session 22 play outcomes to carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    authorities = {e.get("authority") for e in packet["admitted_evidence"]}
    assert authorities & {"canon_play", "derived_memory"}
    paths = " ".join(str(e.get("path") or "") for e in packet["admitted_evidence"])
    assert "Session 22 - Mireward Road and Lysandro" in paths


def test_play_fact_rejects_staged_notes_even_if_manifest_admissible_for_provenance(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request("play-fact", "What Session 22 play outcomes happened at the table in Session 22 recap?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "table_notes" not in admitted_roles
    rejected_paths = [str(r["evidence"].get("path") or "") for r in packet["rejected_evidence"]]
    assert any("session_22_raw_notes" in p for p in rejected_paths)


def test_pipeline_state_uses_audit_preconditions(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "pipeline",
            "What pipeline state must be true before Session 22 is ready_for_planning_activation?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    authorities = {e.get("authority") for e in packet["admitted_evidence"]}
    assert "audit" in authorities
    assert packet["corpus_preconditions"]["all_required_present"] is True


def test_pipeline_state_rejects_prep_scaffold(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "pipeline",
            "What ingest readiness and normalized/breadcrumb/session memory states are required for Session 22 activation?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "prep_scaffold" not in admitted_roles


def test_capability_check_reports_missing_location_write(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "loc",
            "Can I create a new named sub-location hub markdown file for a waystation north of the last stop?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert packet["capability_status"]["status"] in {"missing", "partial", "unknown"}
    codes = {b.get("code") for b in packet["blocked_or_missing"]}
    assert "missing_live_write_capability" in codes


def test_capability_check_reports_missing_roll_table_create(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "roll",
            "Can I add a new swamp-side random encounter table and register it on the packet and patch rows?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert packet["capability_status"]["status"] in {"missing", "partial", "unknown"}
    codes = {b.get("code") for b in packet["blocked_or_missing"]}
    assert "missing_roll_table_create_register_capability" in codes


def test_auth_guardrail_rejects_staging_for_normal_play_fact_evidence(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request(
            "auth",
            "After canonical Session 22 recap exists, may I still use raw staged table notes as normal retrieval evidence for play-fact questions?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    admitted_roles = {e.get("source_role") for e in packet["admitted_evidence"]}
    assert "table_notes" not in admitted_roles
    excerpt = str(packet.get("source_excerpt") or "")
    assert "No" in excerpt or "not as normal retrieval evidence" in excerpt


def test_rejected_evidence_preserves_reason_codes(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("auth", "May raw staged table notes prove play facts after Session 22 recap exists?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert packet["rejected_evidence"]
    for row in packet["rejected_evidence"]:
        assert str(row.get("reason_code") or "").strip()


def test_markdown_candidate_reads_file_and_returns_line_range(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("md", "What happened in Session 22 recap around the decision to continue to Mireward swamp?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    markdown = [e for e in packet["admitted_evidence"] if str(e.get("path") or "").endswith(".md")]
    assert markdown
    assert any(e.get("line_start") is not None and e.get("line_end") is not None for e in markdown)


def test_session_memory_candidate_reads_jsonl_and_returns_unit_id(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("mem", "What Session 22 memory records mention continue on to Mireward and Mirathorn contact?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    memory = [
        e
        for e in packet["admitted_evidence"]
        if str(e.get("source_role") or "") == "session_memory" and str(e.get("path") or "").endswith(".jsonl")
    ]
    assert memory
    assert any(str(e.get("unit_id") or "").strip() for e in memory)


def test_play_fact_packet_contains_text_excerpt_for_supporting_evidence(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request("play-fact", "What are the top Session 22 play outcomes to carry into Session 23 prep?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert packet["admitted_evidence"]
    assert any(str(e.get("text_excerpt") or "").strip() for e in packet["admitted_evidence"])


def test_s22_ingest_01_supporting_evidence_mentions_swamp_or_mirathorn_or_lysandra(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request(
            "s22-ingest-01",
            "After ingesting Session 22 raw notes, what play outcomes carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    blobs = " ".join(str(e.get("text_excerpt") or "") for e in packet["admitted_evidence"]).lower()
    assert any(tok in blobs for tok in ("swamp", "mirathorn", "lysandra", "mireward"))


def test_packet_admission_respects_noise_budget(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "s22-ingest-01",
            "After ingesting Session 22 raw notes, what play outcomes carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert len(packet["retrieved_evidence"]) <= 30
    assert len(packet["admitted_evidence"]) <= 12
    assert len(packet["rejected_evidence"]) <= 12


def test_s22_ingest_01_claim_type_is_play_fact(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "s22-ingest-01",
            "After ingesting Session 22 raw notes, what are the three most important play outcomes to carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    claim_types = {str(c.get("claim_type") or "") for c in packet["claims"]}
    assert "play_fact" in claim_types
    assert packet["intent_class"] in {"play_fact_retrieval", "cross_session_planning"}


def test_play_fact_packet_does_not_admit_ingest_status_audit(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "s22-ingest-01",
            "After ingesting Session 22 raw notes, what are the three most important play outcomes to carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert all(e.get("source_role") != "ingest_status" for e in packet["admitted_evidence"])
    assert all("play_facts" not in list(e.get("forbidden_uses") or []) for e in packet["admitted_evidence"])


def test_play_fact_packet_skips_breadcrumb_frontmatter_schema_spans(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request(
            "s22-ingest-01",
            "After ingesting Session 22 raw notes, what are the three most important play outcomes to carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    for evidence in packet["admitted_evidence"]:
        excerpt = str(evidence.get("text_excerpt") or "").lstrip().lower()
        assert not excerpt.startswith("---")
        assert not excerpt.startswith("schema:")
        assert not excerpt.startswith("--- schema:")
        assert "breadcrumb_semantics" not in excerpt


def test_unrelated_same_session_span_is_not_admitted_when_relevant_spans_exist(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request(
            "s22-ingest-01",
            "After ingesting Session 22 raw notes, what are the three most important play outcomes to carry into Session 23 prep?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    admitted_blobs = " ".join(str(e.get("text_excerpt") or "") for e in packet["admitted_evidence"]).lower()
    assert "savory rain" not in admitted_blobs
    assert "another uneventful night" not in admitted_blobs


def test_auth05_rejected_staging_and_admitted_canon_have_excerpts(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request(
            "auth-05",
            "After canonical Session 22 recap exists, may I still use raw staged table notes as normal retrieval evidence?",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    rejected_staging = [
        r
        for r in packet["rejected_evidence"]
        if "session_22_raw_notes" in str(r["evidence"].get("path") or "")
    ]
    assert rejected_staging
    admitted_canon = [
        e for e in packet["admitted_evidence"] if str(e.get("authority") or "") in {"canon_play", "derived_memory"}
    ]
    assert admitted_canon
    assert any(str(e.get("text_excerpt") or "").strip() for e in admitted_canon)


def test_manifest_entry_without_matching_content_is_not_enough_for_claim_support(
    tmp_path: Path, query_config: QueryConfig
) -> None:
    route = "tmp/no_match.md"
    file_path = tmp_path / route
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("Completely unrelated prose with no relevant game facts.", encoding="utf-8")
    manifest = {
        "entries": [
            {
                "source_id": "play-recap-tmp",
                "source_role": "play_recap",
                "authority": "canon_play",
                "session_scope": [22],
                "route": route,
                "route_exists": True,
                "admissible": True,
                "allowed_uses": ["play_facts"],
                "forbidden_uses": [],
            }
        ]
    }
    packet = build_context_packet(
        _request("probe", "What happened with Lysandra, Sara, and the swamp objective?"),
        manifest,
        root=tmp_path,
        config=query_config,
    )
    assert not packet["admitted_evidence"]
    reasons = {str(r.get("reason_code") or "") for r in packet["rejected_evidence"]}
    assert "missing_evidence_granularity" in reasons


def test_effective_question_exact_session22_title_boosts_session22_recap_family(
    manifest: dict, query_config: QueryConfig
) -> None:
    question = (
        'Session 22 canon play recap: what was the last event or final beat in Session 22? '
        'Use the Session 22 recap / session memory / timeline record, especially the canonical recap '
        'for "Session 22 - Mireward Road and Lysandro". Aliases: Session 22, S22, session recap, session memory.'
    )
    packet = build_context_packet(_request("s22-last", question), manifest, root=ROOT, config=query_config)
    admitted_paths = [str(e.get("path") or "") for e in packet["admitted_evidence"]]
    assert any("Session 22 - Mireward Road and Lysandro" in p for p in admitted_paths[:3])


def test_session22_last_thing_query_ranks_session22_closing_beat_above_session21_conical_hill(
    manifest: dict, query_config: QueryConfig
) -> None:
    question = (
        "what was the last thing that happened in Session 22? "
        'Use "Session 22 - Mireward Road and Lysandro" recap family and session memory.'
    )
    packet = build_context_packet(_request("s22-last-beat", question), manifest, root=ROOT, config=query_config)
    top_rows = list(packet["admitted_evidence"])[:12]
    excerpts = [str(e.get("text_excerpt") or "").lower() for e in top_rows]
    closing_idx = next(
        (
            idx
            for idx, text in enumerate(excerpts)
            if "lieutenant lysandra now" in text or "met her father lysandro" in text or "is that little lysandra" in text
        ),
        None,
    )
    conical_idx = next((idx for idx, text in enumerate(excerpts) if "giant bowl of water" in text), None)
    assert closing_idx is not None
    assert conical_idx is None or closing_idx < conical_idx


def test_retrieval_trace_and_score_components_present(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("trace", "What was the final beat in Session 22 recap around Mireward and Lysandro?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    trace = packet.get("retrieval_trace") or {}
    assert trace.get("top_manifest_entries")
    assert trace.get("admitted_evidence") is not None
    for evidence in packet["admitted_evidence"]:
        components = dict(evidence.get("score_components") or {})
        assert "final_score" in components
        assert "budget_rank_before_cap" in components
        assert "budget_rank_after_cap" in components


def test_hub_instructional_snippets_do_not_outrank_play_recap_events_for_what_happened(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request(
            "hub-damp",
            "What happened last in Session 22? Focus on event outcome in Session 22 recap.",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    roles = [str(e.get("source_role") or "") for e in packet["admitted_evidence"]]
    assert roles
    assert roles[0] in {"play_recap", "session_memory"}
    if "hub_evidence" in roles:
        recap_or_memory_idx = min(idx for idx, role in enumerate(roles) if role in {"play_recap", "session_memory"})
        assert roles.index("hub_evidence") > recap_or_memory_idx


def test_cross_session_question_can_still_retrieve_multiple_sessions(
    manifest: dict, query_config: QueryConfig
) -> None:
    packet = build_context_packet(
        _request(
            "cross-session",
            "Compare major played outcomes from Session 21 and Session 22 that matter for Session 23 planning.",
        ),
        manifest,
        root=ROOT,
        config=query_config,
    )
    admitted_paths = " ".join(str(e.get("path") or "") for e in packet["admitted_evidence"])
    activation_paths = " ".join(
        str(r.get("route") or "") for r in (packet.get("activation_manifest_refs") or [])
    )
    combined_paths = f"{admitted_paths} {activation_paths}"
    assert "Session 21 - Drake Nest Mirathorn Call" in combined_paths
    assert "Session 22 - Mireward Road and Lysandro" in combined_paths


def test_session22_end_question_excludes_session23_excerpts(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("s22-end", "What happened at the end of session 22?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert packet["claims"][0]["claim_type"] == "play_fact"
    assert packet["query_signals"]["asks_for_last_or_final"] is True
    assert 22 in packet["query_signals"]["session_numbers"]
    admitted = packet["admitted_evidence"]
    for item in admitted:
        path = str(item.get("path") or "")
        session = _session_number_from_path(path)
        if session is not None:
            assert session == 22, path
    excerpts = " ".join(str(e.get("text_excerpt") or "") for e in admitted[:3]).lower()
    assert "lysandro" in excerpts or "and that is how" in excerpts
    assert "lightning bolt" not in excerpts
    assert "turn the tide" not in excerpts


def test_session23_end_question_admits_recap_or_memory_tail(manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("s23-end", "What change at the end of session 23?"),
        manifest,
        root=ROOT,
        config=query_config,
    )
    assert packet["claims"][0]["claim_type"] == "play_fact"
    assert packet["query_signals"]["asks_for_last_or_final"] is True
    excerpts = [str(e.get("text_excerpt") or "") for e in packet["admitted_evidence"]]
    top_three = " ".join(excerpts[:3]).lower()
    assert "lightning bolt" in top_three or "turn the tide" in top_three or "overrun" in top_three
    assert not any(str(e.get("path") or "").endswith(".records_meta.json") for e in packet["admitted_evidence"])


def test_session22_exact_title_wins_in_expanded_session_window(tmp_path: Path) -> None:
    s22 = "corpus/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    s21 = "corpus/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md"
    s12 = "corpus/Session Recaps/Session 12 - Giant Bowl and Conical Hill.md"
    hub = "corpus/NPCs/captain_lysandra_ironveil/README.md"
    _write_markdown(
        tmp_path,
        s22,
        "# Session 22 - Mireward Road and Lysandro\n\nThe last thing that happened in Session 22 was Lysandra meeting her father Lysandro on the road.\n",
    )
    _write_markdown(tmp_path, s21, "# Session 21 - Drake Nest Mirathorn Call\nConical hill and giant bowl of water.\n")
    _write_markdown(tmp_path, s12, "# Session 12 - Giant Bowl and Conical Hill\nOlder events and unrelated beats.\n")
    _write_markdown(tmp_path, hub, "# Lysandra hub\nReference biography for campaign planning.\n")
    manifest = {
        "entries": [
            _manifest_entry(
                source_id="s22-recap",
                route=s22,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[22],
                lexical_terms=["mireward", "lysandro", "final beat"],
            ),
            _manifest_entry(
                source_id="s21-recap",
                route=s21,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[21],
                lexical_terms=["conical hill", "drake nest"],
            ),
            _manifest_entry(
                source_id="s12-recap",
                route=s12,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[12],
            ),
            _manifest_entry(
                source_id="lysandra-hub",
                route=hub,
                source_role="hub_evidence",
                authority="reference_tool",
                session_scope=[12, 21, 22],
                lexical_terms=["lysandra", "relationship"],
            ),
        ]
    }
    packet = build_context_packet(
        _request("s22-title", "what was the last thing that happened in Session 22"),
        manifest,
        root=tmp_path,
        config=QueryConfig(),
    )
    admitted_paths = [str(e.get("path") or "") for e in packet["admitted_evidence"]]
    assert admitted_paths
    assert "Session 22 - Mireward Road and Lysandro" in admitted_paths[0]
    top_manifest_routes = [str(row.get("route") or "") for row in packet["retrieval_trace"]["top_manifest_entries"]]
    assert any("Session 21 - Drake Nest Mirathorn Call" in route for route in top_manifest_routes)


def test_session22_last_thing_not_dependent_on_prior_session_lock(tmp_path: Path) -> None:
    s22 = "corpus/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    s21 = "corpus/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md"
    s23 = "corpus/Session Recaps/Session 23 - Opening Fog and Watch.md"
    _write_markdown(tmp_path, s22, "Final beat in Session 22: Lysandra met Lysandro near Mireward.\n")
    _write_markdown(tmp_path, s21, "Session 21 details: giant bowl and conical hill.\n")
    _write_markdown(tmp_path, s23, "Session 23 setup and prep notes.\n")
    manifest = {
        "entries": [
            _manifest_entry(
                source_id="s22-recap",
                route=s22,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[22],
            ),
            _manifest_entry(
                source_id="s21-recap",
                route=s21,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[21],
            ),
            _manifest_entry(
                source_id="s23-recap",
                route=s23,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[23],
            ),
        ]
    }
    packet = build_context_packet(
        _request("s22-last", "what was the last thing that happened in Session 22"),
        manifest,
        root=tmp_path,
        config=QueryConfig(),
    )
    admitted_paths = [str(e.get("path") or "") for e in packet["admitted_evidence"]]
    assert admitted_paths and "Session 22 - Mireward Road and Lysandro" in admitted_paths[0]
    top_manifest_routes = [str(row.get("route") or "") for row in packet["retrieval_trace"]["top_manifest_entries"]]
    assert any("Session 21 - Drake Nest Mirathorn Call" in route for route in top_manifest_routes)
    assert any("Session 23 - Opening Fog and Watch" in route for route in top_manifest_routes)


def test_broad_continuity_question_can_retrieve_older_sessions(tmp_path: Path) -> None:
    s15 = "corpus/Session Recaps/Session 15 - Old Debt in Mireward.md"
    s18 = "corpus/Session Recaps/Session 18 - Marsh Contact and Tensions.md"
    s22 = "corpus/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    _write_markdown(tmp_path, s15, "Old threads: debt with marsh guide and unresolved favor.\n")
    _write_markdown(tmp_path, s18, "Earlier sessions established Lysandra tension and council distrust.\n")
    _write_markdown(tmp_path, s22, "Current lead-in for Session 23 planning.\n")
    manifest = {
        "entries": [
            _manifest_entry(
                source_id="s15",
                route=s15,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[15],
                lexical_terms=["old threads", "earlier sessions"],
            ),
            _manifest_entry(
                source_id="s18",
                route=s18,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[18],
                lexical_terms=["earlier sessions", "continuity"],
            ),
            _manifest_entry(
                source_id="s22",
                route=s22,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[22],
                lexical_terms=["session 23 planning"],
            ),
        ]
    }
    packet = build_context_packet(
        _request("continuity", "what old threads from earlier sessions still matter for Session 23?"),
        manifest,
        root=tmp_path,
        config=QueryConfig(),
    )
    admitted_paths = " ".join(str(e.get("path") or "") for e in packet["admitted_evidence"])
    assert "Session 15 - Old Debt in Mireward" in admitted_paths
    assert "Session 18 - Marsh Contact and Tensions" in admitted_paths


def test_exact_session_query_prefers_target_without_excluding_cross_session_context(tmp_path: Path) -> None:
    s22 = "corpus/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    s21 = "corpus/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md"
    hub = "corpus/NPCs/captain_lysandra_ironveil/timeline.md"
    _write_markdown(tmp_path, s22, "Session 22 closing beat with Lysandra and Lysandro.\n")
    _write_markdown(tmp_path, s21, "Session 21 established the call thread that continues.\n")
    _write_markdown(tmp_path, hub, "Timeline references Session 21 and Session 22 continuity.\n")
    manifest = {
        "entries": [
            _manifest_entry(
                source_id="s22",
                route=s22,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[22],
                lexical_terms=["last thing", "mireward"],
            ),
            _manifest_entry(
                source_id="s21",
                route=s21,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[21],
                lexical_terms=["continuity", "call thread"],
            ),
            _manifest_entry(
                source_id="hub",
                route=hub,
                source_role="hub_evidence",
                authority="reference_tool",
                session_scope=[21, 22],
                lexical_terms=["lysandra", "relationship"],
            ),
        ]
    }
    packet = build_context_packet(
        _request(
            "exact-session",
            "what was the last thing that happened in Session 22 and what context still matters from nearby sessions?",
        ),
        manifest,
        root=tmp_path,
        config=QueryConfig(),
    )
    admitted_paths = [str(e.get("path") or "") for e in packet["admitted_evidence"]]
    assert admitted_paths and "Session 22 - Mireward Road and Lysandro" in admitted_paths[0]
    top_manifest_routes = [str(row.get("route") or "") for row in packet["retrieval_trace"]["top_manifest_entries"]]
    assert any(
        "Session 21 - Drake Nest Mirathorn Call" in route or "captain_lysandra_ironveil/timeline.md" in route
        for route in top_manifest_routes
    )


def test_no_session_query_uses_recency_authority_and_content_not_session_lock(tmp_path: Path) -> None:
    s12 = "corpus/Session Recaps/Session 12 - Early Mireward Contact.md"
    s22 = "corpus/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    prep = "corpus/Session Prep/session_23/session_23_opening.md"
    _write_markdown(tmp_path, s12, "Older mention of Lysandra during a past stop.\n")
    _write_markdown(
        tmp_path,
        s22,
        "Most recently, Lysandra changed stance after meeting Lysandro; this is the current planning signal.\n",
    )
    _write_markdown(tmp_path, prep, "Prep scaffold references weather and logistics only.\n")
    manifest = {
        "entries": [
            _manifest_entry(
                source_id="s12",
                route=s12,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[12],
                lexical_terms=["lysandra"],
            ),
            _manifest_entry(
                source_id="s22",
                route=s22,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[22],
                lexical_terms=["recent", "lysandra", "mireward"],
            ),
            _manifest_entry(
                source_id="prep",
                route=prep,
                source_role="prep_scaffold",
                authority="planning_scaffold",
                session_scope=[23],
                lexical_terms=["opening", "logistics"],
            ),
        ]
    }
    packet = build_context_packet(
        _request("no-session", "what changed most recently with Lysandra that matters for planning?"),
        manifest,
        root=tmp_path,
        config=QueryConfig(),
    )
    admitted = list(packet["admitted_evidence"])
    assert admitted
    assert "Session 22 - Mireward Road and Lysandro" in str(admitted[0].get("path") or "")


def test_only_session_query_enforces_explicit_session_lock(tmp_path: Path) -> None:
    s22 = "corpus/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    s21 = "corpus/Session Recaps/Session 21 - Drake Nest Mirathorn Call.md"
    _write_markdown(tmp_path, s22, "Session 22 evidence line about Lysandra and Lysandro.\n")
    _write_markdown(tmp_path, s21, "Session 21 conical hill evidence.\n")
    manifest = {
        "entries": [
            _manifest_entry(
                source_id="s22",
                route=s22,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[22],
                lexical_terms=["session 22"],
            ),
            _manifest_entry(
                source_id="s21",
                route=s21,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[21],
                lexical_terms=["session 21"],
            ),
        ]
    }
    packet = build_context_packet(
        _request("only-s22", "only use Session 22 recap evidence for what happened last."),
        manifest,
        root=tmp_path,
        config=QueryConfig(),
    )
    admitted_paths = [str(e.get("path") or "") for e in packet["admitted_evidence"]]
    assert admitted_paths and all("Session 22 - Mireward Road and Lysandro" in path for path in admitted_paths)


@pytest.fixture(scope="module")
def dogfood_manifest() -> dict:
    return load_manifest(DOGFOOD_MANIFEST_PATH)


def test_lysandra_ac_admits_elderwyld_statblock(dogfood_manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("hub-stat-01", "What is Captain Lysandra Ironveil's AC?"),
        dogfood_manifest,
        root=ROOT,
        config=query_config,
    )
    admitted_paths = " ".join(str(e.get("path") or "") for e in packet["admitted_evidence"])
    assert "captain_lysandra_ironveil_statblock" in admitted_paths
    assert "Elderwyld" in admitted_paths


def test_session_22_end_play_recap_ranks_above_world_evidence(dogfood_manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("play-s22-end", "What happened at the end of Session 22?"),
        dogfood_manifest,
        root=ROOT,
        config=query_config,
    )
    top_routes = [str(row.get("route") or "") for row in packet["retrieval_trace"]["top_manifest_entries"][:8]]
    play_idx = next(
        (i for i, route in enumerate(top_routes) if "Session 22 - Mireward Road and Lysandro" in route),
        None,
    )
    world_idx = next(
        (i for i, route in enumerate(top_routes) if "Elderwyld/" in route),
        None,
    )
    assert play_idx is not None
    if world_idx is not None:
        assert play_idx < world_idx
    admitted_roles = {str(e.get("source_role") or "") for e in packet["admitted_evidence"]}
    assert admitted_roles & {"play_recap", "session_memory"}


def test_thrin_timeline_prefers_c2_campaign_timeline(dogfood_manifest: dict, query_config: QueryConfig) -> None:
    packet = build_context_packet(
        _request("hub-timeline-01", "What is on Thrin's campaign timeline for Sessions 21 and 22?"),
        dogfood_manifest,
        root=ROOT,
        config=query_config,
    )
    top_routes = [str(row.get("route") or "") for row in packet["retrieval_trace"]["top_manifest_entries"][:12]]
    c2_timeline_idx = next(
        (i for i, route in enumerate(top_routes) if "thrin_branchborn/timeline.md" in route),
        None,
    )
    elderwyld_seed_idx = next(
        (i for i, route in enumerate(top_routes) if "Elderwyld/" in route and "character_seed" in route),
        None,
    )
    assert c2_timeline_idx is not None
    if elderwyld_seed_idx is not None:
        assert c2_timeline_idx < elderwyld_seed_idx
    admitted_paths = " ".join(str(e.get("path") or "") for e in packet["admitted_evidence"])
    assert "thrin_branchborn/timeline.md" in admitted_paths


def test_world_evidence_rejected_for_play_fact_claim(tmp_path: Path) -> None:
    world_route = "corpus/Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md"
    recap_route = "corpus/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    _write_markdown(tmp_path, world_route, "d100 encounter table for the northern road.\n")
    _write_markdown(tmp_path, recap_route, "Session 22 ended with Lysandro on the Mireward road.\n")
    manifest = {
        "entries": [
            {
                **_manifest_entry(
                    source_id="world-road",
                    route=world_route,
                    source_role="world_evidence",
                    authority="reference_tool",
                    session_scope=[21, 22, 23],
                ),
                "allowed_uses": ["setting_context", "mechanical_reference", "npc_grounding"],
                "forbidden_uses": ["play_facts"],
            },
            _manifest_entry(
                source_id="s22",
                route=recap_route,
                source_role="play_recap",
                authority="canon_play",
                session_scope=[22],
            ),
        ]
    }
    packet = build_context_packet(
        _request(
            "auth-world-01",
            "What happened in play when we rolled the d100 road encounter from the Mireward Reach table in Session 22?",
        ),
        manifest,
        root=tmp_path,
        config=QueryConfig(),
    )
    admitted_roles = {str(e.get("source_role") or "") for e in packet["admitted_evidence"]}
    assert "play_recap" in admitted_roles
    assert "world_evidence" not in admitted_roles
