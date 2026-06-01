"""Tests for blind manifest-backed query/admission runner."""

from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest

from src.live_play.manifest_context_query import QueryConfig, QueryRequest, build_context_packet, build_query_plan, load_manifest
from src.live_play.session_paths import repo_root

ROOT = repo_root()
MANIFEST_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
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
    assert "Session 21 - Drake Nest Mirathorn Call" in admitted_paths
    assert "Session 22 - Mireward Road and Lysandro" in admitted_paths
