"""Buddy's native admission boundary uses exact bytes, a pinned head and one command."""
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
    DungeonMindWorldGraphSourceAdmissionAdapter,
)
from apps.live_control_server.ports.world_graph_source_admission import (
    WorldGraphSourceAdmissionError,
    WorldGraphSourceAdmissionRequest,
)
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.domain.errors import PersistenceUnavailableError
from dungeonmind.infrastructure.memory import InMemorySourceRepository, InMemoryWorldGraphRepository

NOW = datetime(2026, 10, 30, tzinfo=UTC)
WORLD = "world:atomic-source"
BODY = b"Synthetic source body, not a published fact.\n"
DIGEST = sha256(BODY).hexdigest()


class AtomicOnlySources(InMemorySourceRepository):
    atomic_calls = 0

    def put_artifact(self, _artifact):
        pytest.fail("Buddy bypassed the native atomic command")

    def put_revision(self, _revision):
        pytest.fail("Buddy wrote a source revision separately")

    def admit_source_revision(self, **kwargs):
        self.atomic_calls += 1
        return super().admit_source_revision(**kwargs)


def _advance(graph, parent=None):
    return graph.publish_revision(PublishRevisionCommand(
        world_id=WORLD, parent_revision_id=parent, expected_parent_revision_id=parent,
        operation_ids=[f"operation:synthetic:{parent or 'genesis'}"],
        graph_schema="dm_union_graph_v1", graph_payload={"world_id": WORLD, "nodes": []},
        created_at=NOW,
    )).revision_id


def _setup(sources=None):
    graph = InMemoryWorldGraphRepository()
    head = _advance(graph)
    sources = sources or AtomicOnlySources()
    artifact = SimpleNamespace(
        source_artifact_id="artifact:atomic", source_domain="worldbuilding",
        campaign_id=None, session_id=None, uri="object://immutable-source-body",
        content_sha256=DIGEST, artifact_kind="markdown", document_class="lore",
        authority_state="reviewed", visibility_state="internal", world_id=WORLD,
        workspace_document_id=None, workspace_document_revision=None,
        lineage={}, status="active", created_at=NOW, updated_at=NOW,
    )
    request = WorldGraphSourceAdmissionRequest(
        world_id=WORLD, campaign_id=None, source_artifact=artifact,
        source_revision_token=f"sha256:{DIGEST}", source_body=BODY,
        expected_head_revision_id=head,
    )
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(sources=sources, world_graph=graph)
    return adapter, sources, graph, request


def test_atomic_source_pair_and_receipt_without_graph_publication():
    adapter, sources, graph, request = _setup()
    first = adapter.prove_or_admit(request)
    assert sources.atomic_calls == 1
    assert sources.get_artifact(first.source_artifact_id) is not None
    assert sources.get_revision(first.source_revision_id) is not None
    assert len(sources._source_admissions) == 1
    receipt = next(iter(sources._source_admissions.values()))
    assert receipt.content_sha256 == DIGEST
    assert receipt.expected_head_revision_id == request.expected_head_revision_id
    assert graph.get_head(WORLD).head_revision_id == request.expected_head_revision_id
    # Existing catalog proof is read-only, even after the World moves on.
    _advance(graph, request.expected_head_revision_id)
    assert adapter.prove_or_admit(request) == first
    assert sources.atomic_calls == 1


@pytest.mark.parametrize("damage", ["body", "missing_head", "stale_head"])
def test_rejection_cannot_leave_a_half_pair(damage):
    adapter, sources, graph, request = _setup()
    if damage == "body":
        request = replace(request, source_body=b"Different bytes despite the claimed token")
    elif damage == "missing_head":
        graph._heads.clear()
    else:
        _advance(graph, request.expected_head_revision_id)
    with pytest.raises(WorldGraphSourceAdmissionError) as failure:
        adapter.prove_or_admit(request)
    assert failure.value.code == "source_identity_conflict"
    assert sources.list_artifacts_for_world(WORLD) == []
    assert sources._revisions == sources._source_admissions == {}
    assert sources.atomic_calls == 0


def test_native_transaction_failure_is_not_recovered_by_two_local_puts():
    class RejectedSources(AtomicOnlySources):
        def admit_source_revision(self, **_kwargs):
            raise PersistenceUnavailableError("synthetic transaction refusal")
    adapter, sources, _graph, request = _setup(RejectedSources())
    with pytest.raises(WorldGraphSourceAdmissionError) as failure:
        adapter.prove_or_admit(request)
    assert failure.value.code == "authority_unavailable"
    assert sources.list_artifacts_for_world(WORLD) == []
    assert sources._revisions == sources._source_admissions == {}


def test_native_receipt_recovers_a_committed_lost_response():
    class LostResponseSources(AtomicOnlySources):
        def admit_source_revision(self, **kwargs):
            super().admit_source_revision(**kwargs)
            raise PersistenceUnavailableError("synthetic response lost after commit")
    adapter, sources, graph, request = _setup(LostResponseSources())
    result = adapter.prove_or_admit(request)
    assert result.content_sha256 == DIGEST
    assert sources.atomic_calls == 1
    assert len(sources._source_admissions) == 1
    assert graph.get_head(WORLD).head_revision_id == request.expected_head_revision_id


def test_existing_pair_requires_real_bytes_not_only_a_claimed_digest():
    adapter, sources, _graph, request = _setup()
    first = adapter.prove_or_admit(request)
    with pytest.raises(WorldGraphSourceAdmissionError) as failure:
        adapter.prove_or_admit(replace(request, source_body=b"wrong", source_uri="object://mirror"))
    assert failure.value.code == "source_identity_conflict"
    assert sources.atomic_calls == 1
    assert adapter.prove_or_admit(replace(request, source_uri="object://verified-mirror")) == first


def test_worldbuilding_prepare_admits_database_bytes_before_native_scope_transport(monkeypatch):
    from apps.live_control_server.services import worldbuilding_graph_publication as service
    from apps.live_control_server.ports import world_graph_source_admission_access as access
    from apps.live_control_server.ports.world_graph_source_admission import AdmittedSourceIdentity

    artifact = SimpleNamespace(
        source_artifact_id="artifact:managed", world_id="managed-world", campaign_id="managed-world",
        content_sha256=DIGEST, model_dump=lambda: {
            "source_artifact_id": "artifact:managed", "world_id": "managed-world",
            "campaign_id": "managed-world", "content_sha256": DIGEST,
        },
    )
    resolved = SimpleNamespace(
        source_artifact_id=artifact.source_artifact_id, source_revision_id=f"sha256:{DIGEST}",
        sealed_source_uri="object://inert-source-locator",
        # There is deliberately no normalized_recap_path: it is not a body authority.
    )
    binding = SimpleNamespace(
        managed_world_id="managed-world", native_world_id=WORLD,
        source_sha256=DIGEST, source_artifact_id=artifact.source_artifact_id,
    )
    reads, requests = [], []

    def body_reader(original):
        assert original is artifact
        assert original.world_id == original.campaign_id == "managed-world"
        reads.append(original.source_artifact_id)
        return BODY

    def admit(request):
        requests.append(request)
        assert request.world_id == request.source_artifact.world_id == WORLD
        assert request.campaign_id is request.source_artifact.campaign_id is None
        assert request.source_body == BODY
        assert request.expected_head_revision_id == "rev:prepared"
        return AdmittedSourceIdentity(
            source_artifact_id=artifact.source_artifact_id,
            source_revision_id="revision:admitted", content_sha256=DIGEST,
            buddy_source_revision_id=resolved.source_revision_id,
            source_locator=resolved.sealed_source_uri, artifact_uri=resolved.sealed_source_uri,
            catalog_fingerprint_sha256="a" * 64,
        )

    monkeypatch.setattr(service, "get_source_artifact", lambda *_: artifact)
    monkeypatch.setattr(service, "load_source_input_bytes", body_reader)
    monkeypatch.setattr(access, "get_world_graph_source_admission_authority",
                        lambda: SimpleNamespace(prove_or_admit=admit))
    result = service._prepare_source_admission(
        resolved, binding, expected_head_revision_id="rev:prepared",
    )
    assert result.content_sha256 == DIGEST
    assert reads == [artifact.source_artifact_id] and len(requests) == 1
    assert artifact.world_id == artifact.campaign_id == "managed-world"


def test_graph_review_missing_database_body_never_calls_native_admission(monkeypatch):
    from apps.live_control_server.services import graph_object_authoring_prepare as service
    from apps.live_control_server.services import source_artifact_registry as registry
    from unittest.mock import Mock

    artifact = SimpleNamespace(world_id=WORLD, campaign_id="campaign:one")
    native = Mock()

    def missing(_artifact):
        raise registry.SourceArtifactRegistryError("synthetic missing database body", status_code=409)

    monkeypatch.setattr(registry, "load_source_input_bytes", missing)
    with pytest.raises(service.GraphObjectAuthoringError) as failure:
        service.prove_or_admit_graph_review_source(
            world_id=WORLD, campaign_id="campaign:one",
            resolved_source=SimpleNamespace(source_artifact=artifact),
            expected_head_revision_id="rev:prepared", source_admission=native,
        )
    assert failure.value.code == "source_inadmissible"
    native.prove_or_admit.assert_not_called()
