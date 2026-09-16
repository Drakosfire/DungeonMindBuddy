"""Deterministic tests for the accepted-world C1S10 question gauntlet evaluator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.graph_benchmark.loadability import (
    C2S22_REVISION,
    CANDIDATE_NODE_ID,
    LOADABILITY_CAMPAIGN_ID,
    LOADABILITY_SESSION_ID,
    PUBLISHED_OBJECT_ID,
    STATUS_CANDIDATE_NOT_ADMITTED,
    STATUS_EXCERPT_READY,
    STATUS_PRODUCT_UNRESOLVED,
    STATUS_QUOTE_MISMATCH,
    build_loadability_complete_object_request,
    candidate_public_view,
    classify_loadability,
    evaluate_dogfood_readiness,
    extract_candidate_node,
    match_quotes_against_excerpts,
    roll_up_seed_status,
)
from evals.graph_benchmark.run_current_corpus_question_gauntlet import (
    AGENT_FORBIDDEN_KEYS,
    BENCHMARK_ID,
    CAMPAIGN_ID,
    GOLD_PATH,
    PROJECT_ROOT,
    TERMINAL_HEAD,
    WORLD_ID,
    assert_agent_request_sanitized,
    build_agent_live_query_request,
    build_retrieval_search_request,
    concept_matched,
    grade_answer,
    load_gold_questions,
    parse_gold_markdown,
    render_report,
    resolve_benchmark_revision,
    resolve_ledger_session_row,
    sealed_world_graph_context,
)

FIXTURE_REVISION = "rev:6d15a3f9f7d2208d444df1097db0166a"


def test_gold_parses_exactly_sixteen_questions_in_order() -> None:
    questions = load_gold_questions()
    assert len(questions) == 16
    assert [q.qid for q in questions] == [f"Q{i:02d}" for i in range(1, 17)]
    assert questions[0].question.startswith("What did the party's arcana check")
    assert "Stormspire Academy" in questions[1].must_include
    assert questions[13].must_not_claim  # Q14
    assert questions[15].must_not_claim  # Q16
    assert GOLD_PATH.exists()


def test_gold_parser_rejects_truncated_suite() -> None:
    text = GOLD_PATH.read_text(encoding="utf-8")
    # Drop Q16 block.
    truncated = text.rsplit("## Q16", 1)[0]
    with pytest.raises(ValueError, match="expected 16"):
        parse_gold_markdown(truncated)


def test_resolve_benchmark_revision_is_c1s10_not_terminal_head() -> None:
    row = resolve_benchmark_revision()
    assert row["campaign_id"] == CAMPAIGN_ID
    assert row["session_id"] == "session-10"
    assert row["receipt_child_revision"] == FIXTURE_REVISION
    assert row["receipt_child_revision"] != TERMINAL_HEAD
    assert row["receipt_child_revision"].startswith("rev:")


def test_sealed_world_graph_context_pins_historical_revision() -> None:
    ctx = sealed_world_graph_context(FIXTURE_REVISION)
    assert ctx["schema"] == "dmb_agent_world_graph_query_context_request_v1"
    assert ctx["world_id"] == WORLD_ID
    assert ctx["campaign_id"] == CAMPAIGN_ID
    assert ctx["revision_pin"] == FIXTURE_REVISION
    assert ctx["revision_pin"] != TERMINAL_HEAD
    assert ctx["focus"]["kind"] == "none"
    assert ctx["scope_mode"] == "campaign"
    assert ctx["admissibility"] == "gm"


def test_agent_request_is_fresh_session_without_gold_leakage() -> None:
    question = load_gold_questions()[0]
    request = build_agent_live_query_request(
        question_text=question.question,
        benchmark_revision=FIXTURE_REVISION,
    )
    assert request["query_backend"] == "hermes"
    assert request["text"] == question.question
    assert "hermes_session_id" not in request
    assert "hermes_session_pointer" not in request
    assert "conversation_history" not in request
    assert request["world_graph_context"]["revision_pin"] == FIXTURE_REVISION
    blob = json.dumps(request)
    assert question.gold_answer not in blob
    for concept in question.must_include:
        assert concept not in blob
    for key in AGENT_FORBIDDEN_KEYS:
        assert key not in request
        assert f'"{key}"' not in blob


def test_assert_agent_request_sanitized_rejects_history_and_gold_keys() -> None:
    request = build_agent_live_query_request(
        question_text="Who is Torbin?",
        benchmark_revision=FIXTURE_REVISION,
    )
    dirty = dict(request)
    dirty["conversation_history"] = [{"role": "user", "content": "prior"}]
    with pytest.raises(AssertionError, match="conversation_history"):
        assert_agent_request_sanitized(dirty)

    dirty2 = dict(request)
    dirty2["gold_answer"] = "secret"
    with pytest.raises(AssertionError, match="gold_answer"):
        assert_agent_request_sanitized(dirty2)

    dirty3 = dict(request)
    dirty3["hermes_session_id"] = "hptr-leak"
    with pytest.raises(AssertionError, match="hermes_session_id"):
        assert_agent_request_sanitized(dirty3)


def test_retrieval_search_request_seals_c1s10_revision() -> None:
    req = build_retrieval_search_request(
        query_text="Torbin",
        benchmark_revision=FIXTURE_REVISION,
    )
    assert req["schema"] == "dmb_world_graph_search_request_v1"
    assert req["worldId"] == WORLD_ID
    assert req["campaignId"] == CAMPAIGN_ID
    assert req["revisionPin"] == FIXTURE_REVISION
    assert req["revisionPin"] != TERMINAL_HEAD
    assert req["focus"]["kind"] == "none"
    assert req["scopeMode"] == "campaign"


def test_concept_matching_supports_slash_alternatives() -> None:
    hay = "The meat was extraplanar in origin."
    assert concept_matched(hay, "the meat is from another plane / extraplanar").matched
    assert not concept_matched(hay, "Stormspire Academy").matched


def test_grade_answer_full_partial_fail_and_must_not_claim() -> None:
    must = ["Head Alchemist", "Stormspire Academy"]
    full = grade_answer(
        answer_text="Take them to the Head Alchemist at Stormspire Academy.",
        must_include=must,
        must_not_claim=[],
    )
    assert full["grade"] == "FULL"

    partial = grade_answer(
        answer_text="Stormspire Academy can help with the mushrooms.",
        must_include=must,
        must_not_claim=[],
    )
    assert partial["grade"] == "PARTIAL"

    fail = grade_answer(
        answer_text="No relevant information.",
        must_include=must,
        must_not_claim=[],
    )
    assert fail["grade"] == "FAIL"

    forbidden = grade_answer(
        answer_text=(
            "Head Alchemist at Stormspire Academy. The Shepherd definitely leads "
            "the conspiracy."
        ),
        must_include=must,
        must_not_claim=["Shepherd definitely leads the conspiracy"],
    )
    assert forbidden["grade"] == "FAIL"
    assert forbidden["must_not_claim_fired"]


def test_artifact_shape_contract_keys() -> None:
    """Document the expected per-question artifact filenames for the runner."""
    expected = {
        "AUTHORITY.json",
        "READINESS.json",
        "SCORECARD.json",
    }
    per_q = {"oracle.json", "agent-request.json", "agent-response.json", "grade.json"}
    assert BENCHMARK_ID == "longmont-c1-sessions-01-10-graph-query-v1"
    assert expected and per_q
    expected.add("LOADABILITY.json")
    expected.add("DOGFOOD.json")
    assert "LOADABILITY.json" in expected
    assert "DOGFOOD.json" in expected


def test_c2s22_loadability_pin_is_not_c1s10_or_terminal_head() -> None:
    row = resolve_ledger_session_row(LOADABILITY_CAMPAIGN_ID, LOADABILITY_SESSION_ID)
    assert row["campaign_id"] == "longmont-c2"
    assert row["session_id"] == "session-22"
    assert row["receipt_child_revision"] == C2S22_REVISION
    assert row["receipt_child_revision"] != TERMINAL_HEAD
    assert row["receipt_child_revision"] != FIXTURE_REVISION


def test_loadability_complete_object_request_seals_c2s22() -> None:
    req = build_loadability_complete_object_request(
        node_id=CANDIDATE_NODE_ID,
        revision_pin=C2S22_REVISION,
        focus_session_id=LOADABILITY_SESSION_ID,
    )
    assert req["schema"] == "dmb_world_graph_object_projection_request_v1"
    assert req["worldId"] == WORLD_ID
    assert req["campaignId"] == LOADABILITY_CAMPAIGN_ID
    assert req["nodeId"] == CANDIDATE_NODE_ID
    assert req["revisionPin"] == C2S22_REVISION
    assert req["revisionPin"] != TERMINAL_HEAD
    assert req["focus"]["kind"] == "session"
    assert req["focus"]["sessionId"] == "session-22"
    assert req["originSurface"] == "ingest"

    published = build_loadability_complete_object_request(
        node_id=PUBLISHED_OBJECT_ID,
        revision_pin=C2S22_REVISION,
    )
    assert published["nodeId"] == PUBLISHED_OBJECT_ID
    assert published["focus"]["kind"] == "none"
    assert published["focus"]["sessionId"] is None


def test_classify_loadability_payload_present_product_missing() -> None:
    assert (
        classify_loadability(
            candidate_present=True,
            payload_present=True,
            product_found=False,
        )
        == STATUS_PRODUCT_UNRESOLVED
    )
    assert (
        classify_loadability(
            candidate_present=True,
            payload_present=False,
            product_found=False,
        )
        == STATUS_CANDIDATE_NOT_ADMITTED
    )
    assert (
        classify_loadability(
            candidate_present=False,
            payload_present=True,
            product_found=True,
            provenance_statuses=["excerpt_ready"],
        )
        == STATUS_EXCERPT_READY
    )
    assert (
        classify_loadability(
            candidate_present=True,
            payload_present=True,
            product_found=True,
            provenance_statuses=["excerpt_ready"],
            quotes_checked=True,
            quotes_all_matched=False,
        )
        == STATUS_QUOTE_MISMATCH
    )
    assert roll_up_seed_status(
        [STATUS_CANDIDATE_NOT_ADMITTED, STATUS_PRODUCT_UNRESOLVED]
    ) == STATUS_PRODUCT_UNRESOLVED


def test_s22_candidate_contains_loc_mireward_with_two_quotes() -> None:
    row = resolve_ledger_session_row(LOADABILITY_CAMPAIGN_ID, LOADABILITY_SESSION_ID)
    extracted = extract_candidate_node(
        PROJECT_ROOT / row["candidate_locator"],
        CANDIDATE_NODE_ID,
    )
    assert extracted["present"] is True
    assert extracted["label"] == "Mireward"
    assert extracted["evidence_ref_count"] == 2
    assert len(extracted["quotes"]) == 2
    public = candidate_public_view(extracted)
    assert "text" not in json.dumps(public)
    assert public["quote_count"] == 2
    # Graph Review evidence[2] is the 0-indexed third live extract, not
    # candidate evidence_refs[1]. Candidate quotes stay 2.
    assert all(quote["char_len"] > 0 for quote in public["quotes"])


def test_quote_mismatch_against_unrelated_excerpt() -> None:
    report = match_quotes_against_excerpts(
        [{"evidence_index": 0, "quote_index": 0, "char_len": 4, "text": "abcd"}],
        ["this paragraph does not contain the quote"],
    )
    assert report["quotes_checked"] is True
    assert report["quotes_all_matched"] is False
    matched = match_quotes_against_excerpts(
        [{"evidence_index": 0, "quote_index": 0, "char_len": 4, "text": "abcd"}],
        ["prefix abcd suffix"],
    )
    assert matched["quotes_all_matched"] is True


def test_dogfood_ready_is_false_when_ingested_object_is_unreadable() -> None:
    dogfood = evaluate_dogfood_readiness(
        harness_ready=True,
        agent_smoke_ok=True,
        loadability={
            "openable": False,
            "seed_status": STATUS_PRODUCT_UNRESOLVED,
            "identity_remap": {
                "from_candidate_id": "loc:mireward",
                "to_published_ids": ["node:location:mireward"],
            },
        },
    )
    assert dogfood["dogfood_ready"] is False
    assert any(b["id"] == "ingested_object_unreadable" for b in dogfood["blockers"])
    assert "cannot dogfood" in dogfood["rule"]


def test_dogfood_ready_is_false_when_hermes_cannot_run() -> None:
    dogfood = evaluate_dogfood_readiness(
        harness_ready=True,
        agent_smoke_ok=False,
        loadability={
            "openable": True,
            "seed_status": STATUS_EXCERPT_READY,
        },
    )
    assert dogfood["dogfood_ready"] is False
    assert any(b["id"] == "hermes_agent" for b in dogfood["blockers"])


def test_dogfood_ready_is_false_when_hermes_returns_no_answers() -> None:
    dogfood = evaluate_dogfood_readiness(
        harness_ready=True,
        agent_smoke_ok=True,
        loadability={
            "openable": True,
            "seed_status": STATUS_EXCERPT_READY,
        },
        agent_ran=True,
        agent_full=0,
        agent_tool_calls=0,
    )
    assert dogfood["dogfood_ready"] is False
    assert any(b["id"] == "hermes_cannot_answer" for b in dogfood["blockers"])


def test_report_status_is_not_ready_when_operator_cannot_dogfood() -> None:
    loadability = {
        "openable": False,
        "seed_status": STATUS_PRODUCT_UNRESOLVED,
        "identity_remap": {
            "from_candidate_id": "loc:mireward",
            "to_published_ids": ["node:location:mireward"],
        },
        "revision_pin": C2S22_REVISION,
        "payload_objects": [
            {"object_id": "node:location:mireward", "kind": "dnd5e:location"}
        ],
        "identities": [
            {
                "node_id": "loc:mireward",
                "payload_present": False,
                "product_found": False,
                "status": STATUS_CANDIDATE_NOT_ADMITTED,
            }
        ],
        "search_world": {"outcome": "empty"},
        "search_campaign": {"outcome": "empty"},
    }
    dogfood = evaluate_dogfood_readiness(
        harness_ready=True,
        agent_smoke_ok=False,
        loadability=loadability,
    )
    report = render_report(
        authority={
            "runtime_git_sha": "deadbeef",
            "acceptance_run_id": "acceptance",
            "acceptance_world_id": WORLD_ID,
            "benchmark_revision": FIXTURE_REVISION,
            "acceptance_terminal_head": TERMINAL_HEAD,
            "benchmark_id": BENCHMARK_ID,
            "gold_sha256": "abc",
        },
        readiness={"ready": True, "harness_ready": True},
        scorecard={
            "oracle_answerable": 16,
            "agent_full": 0,
            "agent_partial": 0,
            "agent_fail": 16,
            "failure_counts": {k: 0 for k in "ABCDEF"},
            "head_before": TERMINAL_HEAD,
            "head_after": TERMINAL_HEAD,
            "qualitative": {},
        },
        question_rows=[],
        run_id="test-run",
        loadability=loadability,
        dogfood=dogfood,
    )
    assert "**Status:** NOT READY — operator cannot dogfood this World" in report
    assert "oracle answerable: 16 / 16" in report
    assert "If the operator cannot dogfood" in report
    status_line = report.split("**Status:**", 1)[1].split("\n", 1)[0]
    assert "COMPLETE" not in status_line
    assert "seed_status:     product_unresolved" in report
    assert "## Handbacks" in report
