"""Source kind/time qualifiers survive the actual typed consumer and model context."""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.services.agent_world_graph_query_context import render_world_graph_prompt_block
from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
from graph_memory.interaction.answer_validator import _claim_ledger_text
from graph_memory.interaction.claims import GraphClaim
from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot
from tests.test_reviewed_source_observation_consumer import _observation
from tests.test_worldbuilding_observation_consumer import packet


@pytest.mark.parametrize("kind", ["worldbuilding_observation", "session_observation"])
@pytest.mark.parametrize("scope", [None, {}, {"session_id": "session:fixture", "extra": {"known": False}}])
def test_typed_source_qualifiers_survive_claim_session_and_model_context(kind, scope):
    native = replace(_observation(), observation_kind=kind, temporal_scope=scope)
    view = direct._reviewed_source_observation_view(native)
    payload = packet(kind, count=1)
    # Keep the fixture's distinct assertion/anchor identities, copying typed qualifiers.
    payload["reviewedSourceObservations"][0]["temporalScope"] = view.temporal_scope
    claims = claims_from_retrieval_result(payload, revision_id="rev:published")
    assert claims[0].temporal_scope == scope
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(world_id="world:test", campaign_id="campaign:one",
                                 revision_id="rev:published"), question="What does each source say?",
        claims=claims,
    )
    restored = GraphRetrievalSession.model_validate_json(session.model_dump_json(by_alias=True))
    assert restored.claims == claims
    ledger = _claim_ledger_text(restored.claims)
    assert kind in ledger
    assert "temporal_scope=" in ledger
    if scope is None:
        assert "unspecified" in ledger
        assert "temporal_scope" not in claims[0].model_dump(mode="json")
    elif scope:
        assert "session:fixture" in ledger
    else:
        assert "temporal_scope={}" in ledger
    envelope = {"status": "ready", "reviewed_source_observations": [
        view.model_dump(mode="json", by_alias=False),
    ]}
    rendered = render_world_graph_prompt_block(envelope)
    assert kind in rendered
    assert native.text in rendered
    assert native.source_revision_id in rendered
    assert "publication time do not establish current story state" in rendered
    assert "epistemic_kind=" in rendered and "visibility=" in rendered
    if scope is None:
        assert "temporal_scope=unspecified" in rendered
    elif scope:
        assert "session:fixture" in rendered
    else:
        assert "temporal_scope={}" in rendered


def test_conflicting_source_contexts_remain_separate_without_latest_selection():
    world = packet("worldbuilding_observation", count=1)
    session = packet("session_observation", count=1)
    world["reviewedSourceObservations"][0]["text"] = "The reference describes unawareness."
    session["reviewedSourceObservations"][0]["text"] = "The session describes realization."
    session["reviewedSourceObservations"][0]["assertionId"] = "assertion:session:other"
    session["sourceAnchors"][0]["supportingAssertionIds"] = ["assertion:session:other"]
    session["reviewedSourceObservations"][0]["sourceArtifactId"] = "artifact:session:other"
    session["reviewedSourceObservations"][0]["temporalScope"] = {"session_id": "session:fixture"}
    claims = (claims_from_retrieval_result(world, revision_id="rev:published")
              + claims_from_retrieval_result(session, revision_id="rev:published"))
    assert len(claims) == 2
    assert len({claim.claim_id for claim in claims}) == 2
    assert claims[0].temporal_scope is None
    assert claims[1].temporal_scope == {"session_id": "session:fixture"}
    assert claims[0].observation_kind != claims[1].observation_kind
    assert "unawareness" in _claim_ledger_text(claims)
    assert "realization" in _claim_ledger_text(claims)


def test_malformed_temporal_value_rejects_instead_of_silently_dropping():
    payload = packet(count=1)
    payload["reviewedSourceObservations"][0]["temporalScope"] = "latest"
    with pytest.raises(ValidationError):
        claims_from_retrieval_result(payload, revision_id="rev:published")


def test_missing_new_field_loads_without_inventing_time():
    claim = claims_from_retrieval_result(packet(count=1), revision_id="rev:published")[0]
    wire = claim.model_dump(mode="json")
    wire.pop("temporal_scope", None)
    restored = GraphClaim.model_validate(wire)
    assert restored.temporal_scope is None
    assert "temporal_scope" not in restored.model_dump(mode="json")
