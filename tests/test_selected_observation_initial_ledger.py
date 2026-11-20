from copy import deepcopy
from pathlib import Path

import pytest

from apps.live_control_server.services.agent_context_assembler import (
    assemble_agent_graph_context,
)
from apps.live_control_server.services import (
    selected_observation_initial_ledger as hydration,
)
from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
from graph_memory.interaction.session import RetrievalOperationEvent
from graph_memory.interaction.session_store import clear_sessions, get_session
from tests.test_worldbuilding_observation_consumer import packet


@pytest.fixture(autouse=True)
def sessions():
    clear_sessions()
    yield
    clear_sessions()


def envelope():
    row = packet(count=1)["reviewedSourceObservations"][0]
    return {
        "world_id": "world:test",
        "campaign_id": "",
        "scope_mode": "world",
        "revision_id": "rev:test",
        "admissibility": "gm",
        "focus": {"kind": "none"},
        "matched_node_ids": [row["subjectNodeId"]],
        "nodes": [],
        "relationships": [],
        "attributes": [],
        "excerpt_policy": "provenance_context_not_citation",
        "reviewed_source_observations": [
            {
                "assertion_id": row["assertionId"],
                "subject_node_id": row["subjectNodeId"],
            }
        ],
    }


def install(monkeypatch, *, outcome="enough", revision="rev:test", support=True):
    calls = []

    def expand(args, *, root):
        calls.append((args, root))
        session = get_session(args["retrievalSessionId"])
        response = packet(count=1)
        if not support:
            response["sourceAnchors"] = []
        added = session.upsert_claims(
            claims_from_retrieval_result(response, revision_id=revision)
        )
        session.operations.append(
            RetrievalOperationEvent(
                operation_id="op:fixture",
                requested_by="hermes",
                operation="object",
                status="completed",
                added_claim_ids=added,
            )
        )
        return {
            **response,
            "outcome": outcome,
            "snapshot": {
                "worldId": "world:test",
                "campaignId": "",
                "scopeMode": "world",
                "revisionId": revision,
                "admissibility": "gm",
            },
        }

    monkeypatch.setattr(hydration, "execute_expand_graph_retrieval", expand)
    return calls


def assemble(e, **kwargs):
    return assemble_agent_graph_context(
        question="Discuss the clerk",
        graph_envelope=e,
        root=Path("/tmp/selected-observation-test-root"),
        **kwargs,
    )


def test_initial_invocation_has_classifier_admitted_observation_and_provenance(
    monkeypatch,
):
    calls = install(monkeypatch)
    assembly = assemble(envelope())
    session = get_session(
        assembly.invocation.context_packet.retrieval_session.session_id
    )
    claim = next(c for c in session.claims if c.claim_kind == "source_observation")
    assert claim.review_id and claim.contribution_id and claim.source_revision_id
    assert (
        claim.support.source_anchor_ids
        and claim.observation_kind == "worldbuilding_observation"
    )
    assert claim.temporal_scope is None
    assert session.operations[-1].requested_by == "server_initial"
    ledger = assembly.invocation.context_packet.retrieval_session.packet["claim_ledger"]
    assert any(c["claim_id"] == claim.claim_id for c in ledger)
    assert calls[0][0]["targets"] == [{"kind": "node", "id": claim.subject_node_id}]
    hydration.hydrate_selected_observations(session, envelope(), root=Path("/tmp"))
    assert sum(c.claim_id == claim.claim_id for c in session.claims) == 1


@pytest.mark.parametrize(
    "outcome,revision,support",
    [
        ("truncated", "rev:test", True),
        ("enough", "rev:other", True),
        ("enough", "rev:test", False),
        ("unavailable", "rev:test", True),
    ],
)
def test_incomplete_or_wrong_revision_support_never_enters_initial_ledger(
    monkeypatch, outcome, revision, support
):
    install(monkeypatch, outcome=outcome, revision=revision, support=support)
    assembly = assemble(envelope())
    session = get_session(
        assembly.invocation.context_packet.retrieval_session.session_id
    )
    assert not any(c.claim_kind == "source_observation" for c in session.claims)
    assert (
        "selected_observation_initial_support_unavailable" in session.coverage.gap_codes
    )


@pytest.mark.parametrize(
    "change",
    [
        {"admissibility": "player"},
        {"reviewed_source_observations": []},
        {"excerpt_policy": None},
        {"matched_node_ids": ["one", "two"]},
    ],
)
def test_redacted_or_unselected_context_does_not_hydrate(monkeypatch, change):
    calls = install(monkeypatch)
    e = deepcopy(envelope())
    e.update(change)
    assemble(e)
    assert calls == []


def test_supplied_session_is_not_rehydrated(monkeypatch):
    calls = install(monkeypatch)
    first = assemble(envelope())
    session = get_session(first.invocation.context_packet.retrieval_session.session_id)
    calls.clear()
    assemble(envelope(), retrieval_session=session)
    assert calls == []
