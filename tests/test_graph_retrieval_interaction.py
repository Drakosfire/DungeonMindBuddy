"""Unit tests for graph_memory.interaction (Hermes graph retrieval package)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from graph_memory.interaction.answer_validator import (
    ABSTENTION_ANSWER,
    validate_structured_answer,
)
from graph_memory.interaction.authority_classifier import classify_authority_for_attribute
from graph_memory.interaction.claims import GraphClaim
from graph_memory.interaction.digest_audit import (
    TRIPOD_CONTRIBUTION_ID,
    audit_contribution_source_digests,
)
from graph_memory.interaction.expansion_executor import execute_expand_graph_retrieval
from graph_memory.interaction.forensic import (
    FORENSIC_ENV_FLAG,
    classify_runtime_branch,
    forensic_enabled,
)
from graph_memory.interaction.initial_resolve import create_session_from_preflight
from graph_memory.interaction.schema_constants import DIGEST_AUDIT_SCHEMA
from graph_memory.interaction.session import (
    GraphRetrievalSession,
    SessionSnapshot,
    SourceAnchorState,
    SourceReadEntry,
)
from graph_memory.interaction.session_store import clear_sessions


@pytest.fixture(autouse=True)
def _clear_retrieval_sessions() -> None:
    clear_sessions()
    yield
    clear_sessions()


def _accepted_claim(*, claim_id: str = "assertion:loc") -> GraphClaim:
    return GraphClaim(
        claim_id=claim_id,
        claim_kind="attribute",
        subject_node_id="threat:tripod",
        subject_label="Tripod",
        predicate="location",
        value_text="North Gate",
        revision_id="revision:test",
        authority_class="gm_authored_accepted_assertion",
    )


def _derived_claim() -> GraphClaim:
    return GraphClaim(
        claim_id="summary:tripod",
        claim_kind="navigation_summary",
        subject_node_id="threat:tripod",
        predicate="summary",
        value_text="Scout overview",
        revision_id="revision:test",
        authority_class="derived_summary",
    )


def test_graph_claim_may_state_as_campaign_fact() -> None:
    assert _accepted_claim().may_state_as_campaign_fact() is True
    assert _derived_claim().may_state_as_campaign_fact() is False


def test_create_session_from_preflight_seeds_referents_and_claims() -> None:
    envelope = {
        "world_id": "world:eldyrwild",
        "campaign_id": "campaign:c1",
        "revision_id": "revision:test",
        "matched_node_ids": ["threat:tripod"],
        "nodes": [{"node_id": "threat:tripod", "label": "Tripod Null-Calf"}],
        "attributes": [
            {
                "assertion_id": "assertion:loc",
                "subject_node_id": "threat:tripod",
                "predicate": "location",
                "text_value": "North Gate",
                "authority_class": "accepted_explicit_attribute",
            }
        ],
        "focus": {"kind": "session", "session_id": "session-21"},
        "admissibility": "gm",
    }

    session = create_session_from_preflight(envelope, question="Where is Tripod?")

    assert session.id
    assert [ref.id for ref in session.referents] == ["threat:tripod"]
    assert session.referents[0].origin == "deterministic_match"
    assert session.preflight_candidate_ids == ["threat:tripod"]
    factual = [c for c in session.claims if c.may_state_as_campaign_fact()]
    assert {c.claim_id for c in factual} == {
        "identity:threat:tripod",
        "assertion:loc",
    }
    assert session.question == "Where is Tripod?"


def test_validate_structured_answer_partial_when_claims_and_unreadable_anchors() -> None:
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
            focus={"kind": "session", "session_id": "session-21"},
        ),
        question="Where is Tripod?",
        claims=[_accepted_claim()],
        source_anchors=[
            SourceAnchorState(
                anchor_id="anchor:opaque",
                readable=False,
                opened=False,
                supporting_claim_ids=["assertion:loc"],
            )
        ],
    )

    validated = validate_structured_answer(
        session,
        None,
        model_prose=(
            "Tripod is at the North Gate, controls the Shepherd's army, and "
            "can only be killed with fire."
        ),
    )

    assert validated.outcome == "partial_coverage"
    assert validated.accepted_claim_ids == ["assertion:loc"]
    assert any("Source verification" in warning for warning in validated.warnings)
    assert validated.answer_text == (
        "Graph-grounded facts for this turn:\n"
        "- Tripod: location — North Gate"
    )
    assert "Shepherd's army" not in validated.answer_text
    assert "killed with fire" not in validated.answer_text
    assert "hermes_agent_answer" not in validated.reason_codes
    assert "Source verification" not in validated.answer_text


def test_validate_structured_answer_graph_grounded_without_unreadable_anchors() -> None:
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="Where is Tripod?",
        claims=[_accepted_claim()],
    )

    validated = validate_structured_answer(
        session,
        None,
        model_prose="Tripod is at the North Gate.",
    )

    assert validated.outcome == "graph_grounded"
    assert validated.source_citations == []
    assert "Graph-grounded facts for this turn:" in validated.answer_text


def test_validate_structured_answer_rejects_claim_from_foreign_revision() -> None:
    foreign_claim = _accepted_claim().model_copy(
        update={"revision_id": "revision:foreign"}
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="Where is Tripod?",
        claims=[foreign_claim],
    )

    validated = validate_structured_answer(
        session,
        {
            "sections": [
                {
                    "text": "Tripod is at the North Gate.",
                    "statement_kind": "graph_fact",
                    "supporting_claim_ids": ["assertion:loc"],
                }
            ]
        },
    )

    assert validated.outcome == "abstained"
    assert validated.answer_text == ABSTENTION_ANSWER
    assert validated.rejected_claim_ids == ["assertion:loc"]
    assert "claim_revision_mismatch" in validated.reason_codes


def test_attribute_authority_requires_explicit_provenance() -> None:
    assert classify_authority_for_attribute(
        {
            "assertion_id": "assertion:unknown",
            "predicate": "location",
            "text_value": "North Gate",
        }
    ) == "unknown"

    assert classify_authority_for_attribute(
        {
            "assertion_id": "assertion:explicit",
            "authority_class": "accepted_explicit_attribute",
        }
    ) == "accepted_explicit_attribute"


def test_validate_structured_answer_emits_source_citations_only_for_open_reads() -> None:
    session_with_read = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="Quote the source",
        claims=[_accepted_claim()],
        source_reads=[
            SourceReadEntry(
                source_read_id="read:1",
                anchor_id="anchor:readable",
                outcome="enough",
                content_sha256="abc123",
                source_artifact_id="artifact:session-21",
            )
        ],
    )
    with_read = validate_structured_answer(session_with_read, None, model_prose="Quoted detail.")
    assert len(with_read.source_citations) == 1
    assert with_read.source_citations[0].anchor_id == "anchor:readable"
    assert with_read.outcome == "source_verified"

    session_denied_read = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="Quote the source",
        claims=[_accepted_claim()],
        source_reads=[
            SourceReadEntry(
                source_read_id="read:2",
                anchor_id="anchor:denied",
                outcome="denied",
            )
        ],
    )
    denied = validate_structured_answer(session_denied_read, None, model_prose="No quote.")
    assert denied.source_citations == []
    assert denied.outcome == "graph_grounded"


def test_validate_s1_memory_lag_gap_is_partial_not_generic_abstention(
    tmp_path: Path,
) -> None:
    recap_path = tmp_path / "Session 24 - Recap.md"
    recap_path.write_text(
        "---\ntitle: Session 24\n---\n\n"
        "The party held the North Gate while Tripod Null-Calf pressed the wall.\n\n"
        "Edge called for reinforcement as Mireward's shield line buckled.\n",
        encoding="utf-8",
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:longmont-c2",
            revision_id="rev:5cadc9798562862cdde22350d8a3b56c",
            focus={"kind": "session", "session_id": "session-24"},
        ),
        question="What changed after the latest ingested recap?",
        intent_hint="compare",
        claims=[],
        latest_recap_change={
            "schema": "dmb_latest_recap_change_context_v1",
            "status": "ready",
            "campaign_id": "longmont-c2",
            "outcome": "memory_lag",
            "memory_lag": True,
            "latest_recap": {
                "artifact_id": "longmont-c2/session-24",
                "campaign_id": "longmont-c2",
                "session_id": "session-24",
                "source_recap_path": "Session 24 - Recap.md",
            },
            "comparison_boundary": {
                "kind": "latest_admitted_recap_to_graph_head",
                "recap_session_id": "session-24",
                "graph_latest_session_id": "session-23",
                "graph_revision_id": "rev:5cadc9798562862cdde22350d8a3b56c",
            },
            "diagnostic_codes": ["latest_recap_not_in_graph_head"],
        },
    )

    agent_answer = (
        "After Session 24 the fight is still at the North Gate: Tripod Null-Calf "
        "is under pressure and the meatwings are charming the party. Graph memory "
        "has not caught up past session-23 yet."
    )
    validated = validate_structured_answer(
        session,
        None,
        model_prose=agent_answer,
        corpus_root=tmp_path,
    )

    assert validated.outcome == "partial_coverage"
    assert "no_admissible_claims" not in validated.reason_codes
    assert "named_gap" in validated.reason_codes
    assert "hermes_agent_answer" in validated.reason_codes
    assert "admitted_recap_source_read" in validated.reason_codes
    assert validated.answer_text.startswith("After Session 24")
    assert "North Gate" in validated.answer_text
    assert "memory lag" not in validated.answer_text.lower()
    assert "From the admitted session-24 recap" not in validated.answer_text
    assert validated.support_lag_text is not None
    assert "memory lag" in validated.support_lag_text.lower()
    assert validated.support_excerpt_text is not None
    assert "From the admitted session-24 recap" in validated.support_excerpt_text
    assert "I cannot narrate grounded campaign movement" not in validated.answer_text


def test_validate_s1_keeps_excerpt_out_of_chat_when_agent_silent(tmp_path: Path) -> None:
    recap_path = tmp_path / "Session 24 - Recap.md"
    recap_path.write_text(
        "The party held the North Gate while Tripod Null-Calf pressed the wall.\n",
        encoding="utf-8",
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:longmont-c2",
            revision_id="rev:5cadc9798562862cdde22350d8a3b56c",
            focus={"kind": "session", "session_id": "session-24"},
        ),
        question="What changed after the latest ingested recap?",
        claims=[],
        latest_recap_change={
            "schema": "dmb_latest_recap_change_context_v1",
            "status": "ready",
            "campaign_id": "longmont-c2",
            "outcome": "memory_lag",
            "memory_lag": True,
            "latest_recap": {
                "artifact_id": "longmont-c2/session-24",
                "campaign_id": "longmont-c2",
                "session_id": "session-24",
                "source_recap_path": "Session 24 - Recap.md",
            },
            "comparison_boundary": {
                "kind": "latest_admitted_recap_to_graph_head",
                "recap_session_id": "session-24",
                "graph_latest_session_id": "session-23",
                "graph_revision_id": "rev:5cadc9798562862cdde22350d8a3b56c",
            },
            "diagnostic_codes": ["latest_recap_not_in_graph_head"],
        },
    )
    validated = validate_structured_answer(session, None, corpus_root=tmp_path)
    assert validated.answer_text == "Hermes did not return a chat answer for this turn."
    assert "From the admitted session-24 recap" not in validated.answer_text
    assert validated.support_excerpt_text is not None
    assert "North Gate" in validated.support_excerpt_text
    assert "admitted_recap_source_read" in validated.reason_codes
    assert "hermes_agent_answer" not in validated.reason_codes


def test_validate_empty_graph_without_latest_recap_still_abstains() -> None:
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="What is it connected to?",
        claims=[],
    )

    validated = validate_structured_answer(
        session,
        None,
        model_prose="History prose should not answer this.",
    )

    assert validated.outcome == "abstained"
    assert "no_admissible_claims" in validated.reason_codes
    assert "History prose should not answer this." not in validated.answer_text


def test_validate_zero_tool_calls_with_prose_still_abstains() -> None:
    """Absence of graph calls is not a trusted conversation declaration."""
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="What have we discussed so far?",
        claims=[],
    )

    validated = validate_structured_answer(
        session,
        None,
        model_prose="We covered Tripod Null-Calf's position and the siege timeline.",
    )

    assert validated.outcome == "abstained"
    assert validated.answer_text == ABSTENTION_ANSWER
    assert "conversation_context_no_tool_calls" not in validated.reason_codes
    assert validated.validator_path == "claim_ledger_validation"
    assert validated.accepted_claim_ids == []
    assert validated.graph_references == []
    assert validated.source_citations == []


def test_validate_explicit_answer_scope_preserves_prose() -> None:
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="What have we discussed so far?",
        claims=[],
    )

    validated = validate_structured_answer(
        session,
        None,
        model_prose="Earlier we talked about siege prep and Tripod.",
        answer_scope="conversation_context",
    )

    assert validated.outcome == "conversation_context"
    assert validated.answer_text == "Earlier we talked about siege prep and Tripod."
    assert validated.validator_path == "explicit_conversation_context"
    assert "explicit_conversation_context" in validated.reason_codes


def test_validate_zero_tool_calls_without_prose_still_abstains() -> None:
    """No tool calls and no model prose either — nothing to trust, still abstain."""
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="What have we discussed so far?",
        claims=[],
    )

    validated = validate_structured_answer(
        session,
        None,
        model_prose=None,
    )

    assert validated.outcome == "abstained"
    assert "no_admissible_claims" in validated.reason_codes


def test_validate_nonzero_tool_calls_with_no_claims_still_abstains() -> None:
    """Agent did query the graph this turn but got nothing back — real abstention."""
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:eldyrwild",
            campaign_id="campaign:c1",
            revision_id="revision:test",
        ),
        question="What is it connected to?",
        claims=[],
    )

    validated = validate_structured_answer(
        session,
        None,
        model_prose="Prose after an empty graph query should still be discarded.",
    )

    assert validated.outcome == "abstained"
    assert "Prose after an empty graph query" not in validated.answer_text


def test_forensic_enabled_respects_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(FORENSIC_ENV_FLAG, raising=False)
    assert forensic_enabled() is False
    monkeypatch.setenv(FORENSIC_ENV_FLAG, "true")
    assert forensic_enabled() is True


def test_classify_runtime_branch_no_tool_and_no_completion() -> None:
    assert (
        classify_runtime_branch(tool_events=[], acceptance_state="abstained")
        == "no_tool"
    )
    assert (
        classify_runtime_branch(
            tool_events=[{"state": "start", "tool": "search_campaign_graph"}],
            acceptance_state="abstained",
        )
        == "no_completion"
    )


def test_expand_graph_retrieval_rejects_unknown_session() -> None:
    with pytest.raises(ValueError, match="unknown retrieval session"):
        execute_expand_graph_retrieval(
            {
                "schema": "dmb_expand_graph_retrieval_request_v1",
                "retrieval_session_id": "sess:missing",
                "operation": "object",
                "targets": [{"kind": "node", "id": "threat:tripod"}],
            }
        )


def test_expand_accepts_policy_injected_camelcase_wire_form() -> None:
    """Hermes model + policy inject use camelCase; must not be invalid_arguments."""
    with pytest.raises(ValueError, match="unknown retrieval session"):
        execute_expand_graph_retrieval(
            {
                "schema": "dmb_expand_graph_retrieval_request_v1",
                "retrievalSessionId": "sess:missing",
                "retrieval_session_id": "sess:missing",  # dual inject must normalize
                "operation": "search",
                "queryText": "What changed after the latest ingested recap?",
                "worldId": "world:eldyrwild",  # scope inject must be stripped
            }
        )


def test_tripod_contribution_id_constant() -> None:
    assert TRIPOD_CONTRIBUTION_ID == "contribution:022187fdefdf4557"


def test_audit_contribution_source_digests_returns_schema(tmp_path) -> None:
    contribution_id = "contribution:abc"
    digest = "sha256:deadbeef"
    fake_store = SimpleNamespace(
        revision_id="revision:head",
        contribution_source_payload_sha256={contribution_id: digest},
    )
    fake_head = SimpleNamespace(head_revision_id="revision:head")
    fake_revision = SimpleNamespace(revision_id="revision:head")
    fake_index = SimpleNamespace(
        all_contribution_ids=[contribution_id],
        failed_contribution_ids=[],
    )
    fake_contrib = SimpleNamespace(status="ok")

    with (
        patch(
            "graph_memory.interaction.digest_audit.load_current_world_graph",
            return_value=(fake_head, fake_revision, fake_store),
        ),
        patch(
            "graph_memory.interaction.digest_audit.load_contribution_index",
            return_value=fake_index,
        ),
        patch(
            "graph_memory.interaction.digest_audit.load_contribution_record",
            return_value=fake_contrib,
        ),
        patch(
            "graph_memory.interaction.digest_audit.compute_contribution_source_payload_sha256",
            return_value=digest,
        ),
    ):
        result = audit_contribution_source_digests(tmp_path)

    assert result["schema"] == DIGEST_AUDIT_SCHEMA
    assert result["complete"] is True
    assert result["ok_count"] == 1
    assert result["revision_id"] == "revision:head"
    assert result["highlighted"][TRIPOD_CONTRIBUTION_ID] is None
