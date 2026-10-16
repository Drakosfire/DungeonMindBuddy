"""Exact source-catalog resolution and non-authoritative Agent delivery."""
from dataclasses import replace
from types import SimpleNamespace as N

import pytest

from apps.live_control_server.services import agent_turn_service as svc
from apps.live_control_server.services.build_source_discovery import discover_build_source
from dungeonmind.application.world_graph_retrieval import (
    ReviewedSourceDiscoveryEntry, ReviewedSourceDiscoveryResult, RetrievalCoverage,
)
from graph_memory.evidence.source_artifact import build_worldbuilding_source_artifact_id


def case(*, count=1, continuation=None, gaps=()):
    basis = svc.BuildSavedSourceBasis("doc", "managed", 2, "a" * 64,
        "City", "worldbuilding", "gazetteer", "reviewed", "internal", "# City")
    artifact_id = build_worldbuilding_source_artifact_id(workspace_document_id="doc",
        workspace_document_revision=2, content_sha256="a" * 64)
    artifact = N(source_artifact_id=artifact_id, world_id="native", source_domain="worldbuilding",
        workspace_document_ref=N(document_id="doc", revision=2), status="active")
    revision = N(source_artifact_id=artifact_id, source_revision_id="collision-aware-native-revision",
        content_sha256="a" * 64)
    requests = []
    result = ReviewedSourceDiscoveryResult(snapshot=None, source_artifact_id=artifact_id,
        source_revision_id=revision.source_revision_id, eligible_count=count, offset=0, max_entries=64,
        entries=(ReviewedSourceDiscoveryEntry(subject_object_id="person:barin", subject_label="Barin",
            subject_kind="character", assertion_id="assertion:barin", observation_kind="description",
            excerpt="Worried about the cult", excerpt_truncated=True, label_truncated=False,
            epistemic_kind="source_report", temporal_scope={"kind": "unspecified"}, source_anchors=()),),
        next_page_token=continuation, coverage=RetrievalCoverage(gap_codes=gaps))
    def discover(request):
        requests.append(request)
        return result
    services = N(bundle=N(sources=N(list_artifacts_for_world=lambda _: [artifact],
        list_revisions=lambda _: [revision])), retrieval=N(discover_reviewed_source_observations=discover))
    return basis, artifact, revision, services, requests


def read(services, basis):
    return discover_build_source(services, basis, native_world_id="native", graph_revision="frozen")


def test_exact_catalog_revision_and_frozen_scope_with_discovery_only_pointers():
    basis, _, _, services, requests = case()
    packet = read(services, basis)
    assert packet["status"] == "complete" and packet["eligible_count"] == 1
    request, = requests
    assert request.source_revision_id == "collision-aware-native-revision"
    assert request.projection.revision_pin == "frozen"
    assert request.projection.world_id == "native" and request.max_entries == 64
    assert str(request.projection.scope_mode) == "world_cross_campaign"
    row, = packet["entries"]
    assert row["subject_object_id"] == "person:barin" and row["discovery_only"]
    assert row["epistemic_kind"] == "source_report" and row["excerpt_truncated"]
    assert "source_anchors" not in row and "evidence_ref_ids" not in row
    assert "not admitted claims" in packet["interpretation"]


def test_absent_source_is_not_complete_empty_discovery():
    basis, _, _, services, requests = case()
    services.bundle.sources.list_artifacts_for_world = lambda _: []
    packet = read(services, basis)
    assert packet["status"] == "source_not_admitted" and packet["eligible_count"] is None
    assert not requests


@pytest.mark.parametrize("axis,value", [("world_id", "other"), ("status", "retracted"),
    ("source_domain", "recap"), ("workspace_document_ref", None),
    ("workspace_document_ref", N(document_id="other", revision=2)),
    ("workspace_document_ref", N(document_id="doc", revision=3))])
def test_wrong_catalog_owner_fails_before_discovery(axis, value):
    basis, artifact, _, services, requests = case()
    setattr(artifact, axis, value)
    with pytest.raises(ValueError, match="ownership"):
        read(services, basis)
    assert not requests


@pytest.mark.parametrize("mode", ["missing", "hash", "artifact", "ambiguous"])
def test_no_hash_fallback_latest_selection_or_ambiguous_revision(mode):
    basis, _, revision, services, requests = case()
    if mode == "hash":
        revision.content_sha256 = "b" * 64
    if mode == "artifact":
        revision.source_artifact_id = "other"
    if mode == "missing":
        services.bundle.sources.list_revisions = lambda _: []
    if mode == "ambiguous":
        services.bundle.sources.list_revisions = lambda _: [revision, revision]
    with pytest.raises(ValueError, match="missing or ambiguous"):
        read(services, basis)
    assert not requests


def test_partial_page_preserves_coverage_and_continuation():
    basis, _, _, services, _ = case(count=100, continuation="cursor", gaps=("gap",))
    packet = read(services, basis)
    assert packet["status"] == "partial" and packet["eligible_count"] == 100
    assert packet["next_page_token"] == "cursor" and packet["coverage"]["gap_codes"] == ("gap",)
    assert "cannot establish an exhaustive roster" in packet["continuation_note"]


def test_exact_discovery_is_part_of_verified_provider_message():
    basis, _, _, services, _ = case()
    packet = read(services, basis)
    work = svc.AgentTurnResolvedWork(kind="build", object_id="doc", revision=2,
        changed_since_expected=False, owner_kind="world", owner_id="managed", build_source=basis,
        build_source_discovery=packet)
    message = svc._build_invocation_message(work, "Who is concerned?")
    assert "person:barin" in message and "discovery_only" in message
    assert svc._build_invocation_message(replace(work, build_source_discovery=None), "Who is concerned?") == basis.invocation_message("Who is concerned?")
    assert packet["entries"][0]["assertion_id"] == "assertion:barin"
