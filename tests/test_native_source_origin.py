"""Real Core pin resolution and current provenance; no body/provider IO."""
from dataclasses import FrozenInstanceError, replace
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from dungeonmind.contracts.evidence import SourceStatus
from dungeonmind.contracts.projection_v2 import WorldGraphProjectionRequestV2
from dungeonmind.domain.canonical import canonical_sha256
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.integrations.dungeonmind.source_origin import (
    SourceOriginUnavailable, verify_native_source_origin,
)
from tests.test_world_graph_retrieval_contract import _selected_native_fixture


@pytest.fixture
def origin():
    services, request, revision = _selected_native_fixture(unrelated=0)
    found = direct.search_world_graph_direct_v3(services, request)
    pin = t.GraphSourceScopeAnchorV2(**{
        key: value for key, value in vars(found.source_pins[0]).items()
        if key != "graph_revision"})
    donor = t.ValidatedGraphOperationEventV3(
        kind="validated_graph_operation_v3", event_id=uuid4(), sequence=0,
        operation_id=uuid4(), operation="search", request_arguments_sha256="a"*64,
        graph_revision=revision, result_packet_sha256="b"*64,
        assertion_ids=[], relationship_ids=[], evidence_ref_ids=[pin.evidence_ref_id],
        evidence_sufficiency_status="sufficient", coverage_status="complete",
        truncated=False, source_opened=False, returned_source_pins=[pin])
    scope = WorldGraphProjectionRequestV2(world_id=request.world_id,
        scope_mode="world_cross_campaign", admissibility="gm", revision_pin=revision)
    return services, scope, donor, pin


def verify(origin):
    services, scope, donor, pin = origin
    return verify_native_source_origin(services, projection=scope, donor=donor, pin=pin)


def test_real_core_source_proof_retains_structured_identity_without_body(origin):
    proof = verify(origin)
    services, scope, donor, pin = origin
    data = json.loads(proof.proof_json)
    assert proof.donor_event_id == donor.event_id
    assert proof.source_artifact_id == pin.source_artifact_id
    assert proof.native_source_revision_id == pin.source_revision_id
    assert proof.content_sha256 == services.bundle.sources.get_revision(pin.source_revision_id).content_sha256
    assert data["donor"] == donor.model_dump(mode="json")
    assert data["donor_sha256"] == canonical_sha256(data["donor"])
    assert data["projection"] == scope.model_dump(mode="json")
    assert data["resolution"]["artifact"]["world_id"] == scope.world_id
    assert data["resolution"]["evidence"]["evidence_ref_id"] == pin.evidence_ref_id
    assert proof.proof_sha256 == canonical_sha256(data)
    assert "markdown" not in data and "text" not in data
    with pytest.raises(FrozenInstanceError):
        proof.source_artifact_id = "forged"


@pytest.mark.parametrize("change", ["inactive", "unknown_visibility", "foreign_world", "missing"])
def test_old_graph_pin_rechecks_current_source_access(origin, change):
    services, _, _, pin = origin
    sources = services.bundle.sources
    original = sources.get_artifact(pin.source_artifact_id)
    assert verify(origin)
    if change == "missing":
        del sources._artifacts[pin.source_artifact_id]
    else:
        update = {"inactive": {"status": SourceStatus.RETRACTED},
                  "unknown_visibility": {"visibility": None},
                  "foreign_world": {"world_id": "other-world"}}[change]
        sources._artifacts[pin.source_artifact_id] = original.model_copy(update=update)
    with pytest.raises(SourceOriginUnavailable):
        verify(origin)


def test_player_scope_cannot_reuse_gm_pin(origin):
    services, scope, donor, pin = origin
    with pytest.raises(SourceOriginUnavailable):
        verify((services, scope.model_copy(update={"admissibility": "player"}), donor, pin))


def test_old_revision_does_not_follow_mutable_current_source(origin):
    services, _, _, pin = origin
    sources = services.bundle.sources
    first = verify(origin)
    artifact = sources.get_artifact(pin.source_artifact_id)
    revision = sources.get_revision(pin.source_revision_id)
    sources.put_revision(revision.model_copy(update={
        "source_revision_id": "future-revision", "content_sha256": "f"*64}))
    sources._artifacts[pin.source_artifact_id] = artifact.model_copy(update={
        "current_revision_id": "future-revision"})
    after = verify(origin)
    assert after.native_source_revision_id == first.native_source_revision_id
    assert after.content_sha256 == first.content_sha256
    assert json.loads(after.proof_json)["resolution"]["artifact"]["current_revision_id"] == "future-revision"


@pytest.mark.parametrize("change", ["pin", "donor_pin", "revision", "unfrozen", "world"])
def test_invalid_donor_is_rejected_before_native_call(origin, monkeypatch, change):
    services, scope, donor, pin = origin
    if change == "pin":
        pin = pin.model_copy(update={"source_revision_id": "other"})
    elif change == "donor_pin":
        donor = donor.model_copy(update={"returned_source_pins": []})
    elif change == "revision":
        donor = donor.model_copy(update={"graph_revision": "other"})
    elif change == "unfrozen":
        scope = scope.model_copy(update={"revision_pin": None})
    else:
        scope = scope.model_copy(update={"world_id": "other"})
    monkeypatch.setattr(services.retrieval, "resolve_source_anchor",
        lambda *a, **kw: pytest.fail("unadmitted donor reached Core"))
    with pytest.raises(SourceOriginUnavailable):
        verify((services, scope, donor, pin))


@pytest.mark.parametrize("change", ["world_id", "campaign_id", "focus", "scope_mode", "admissibility", "revision_id"])
def test_resolver_snapshot_must_match_every_scope_axis(origin, monkeypatch, change):
    from dungeonmind.contracts.projection import ProjectionFocus
    services, scope, donor, pin = origin
    result = services.retrieval.resolve_source_anchor(scope, anchor_id=direct._dnd_anchor_id(pin.anchor_id))
    value = {"world_id": "other", "campaign_id": "other", "focus": ProjectionFocus(kind="session", session_id="other"),
             "scope_mode": "world", "admissibility": "player", "revision_id": "other"}[change]
    result = replace(result, snapshot=result.snapshot.model_copy(update={change: value}))
    monkeypatch.setattr(services.retrieval, "resolve_source_anchor", lambda *a, **kw: result)
    with pytest.raises(SourceOriginUnavailable):
        verify(origin)


@pytest.mark.parametrize("change", ["missing", "source_revision_id", "source_artifact_id", "content_sha256"])
def test_native_revision_tuple_is_independently_verified(origin, monkeypatch, change):
    services, _, _, pin = origin
    original = services.bundle.sources.get_revision
    revision = original(pin.source_revision_id)
    def get(identity):
        # Core and verifier both see the substituted record; either must deny it.
        if identity != pin.source_revision_id:
            return original(identity)
        return None if change == "missing" else revision.model_copy(update={change: "wrong"})
    monkeypatch.setattr(services.bundle.sources, "get_revision", get)
    with pytest.raises(SourceOriginUnavailable):
        verify(origin)


def test_old_graph_pin_survives_new_graph_head(origin):
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from tests._cutover_direct_dungeonmind_read_helpers import _payload, NOW
    services, scope, _, _ = origin
    published = services.bundle.world_graph.publish_revision(PublishRevisionCommand(
        world_id=scope.world_id, parent_revision_id=scope.revision_pin,
        expected_parent_revision_id=scope.revision_pin, operation_ids=["op:next"],
        graph_schema="dm_union_graph_v6", graph_payload=_payload(), created_at=NOW))
    proof = verify(origin)
    snapshot = json.loads(proof.proof_json)["resolution"]["snapshot"]
    assert snapshot["revision_id"] == scope.revision_pin
    assert snapshot["head_revision_id"] == published.revision_id
    assert not snapshot["is_head"]


@pytest.mark.parametrize("field", ["anchor_id", "evidence_ref_id", "source_artifact_id", "source_revision_id", "can_open_source"])
def test_native_anchor_substitution_is_rejected(origin, monkeypatch, field):
    services, scope, _, pin = origin
    result = services.retrieval.resolve_source_anchor(scope, anchor_id=direct._dnd_anchor_id(pin.anchor_id))
    changed = replace(result.anchor, **{field: False if field == "can_open_source" else "foreign"})
    monkeypatch.setattr(services.retrieval, "resolve_source_anchor", lambda *a, **kw: replace(result, anchor=changed))
    with pytest.raises(SourceOriginUnavailable):
        verify(origin)
