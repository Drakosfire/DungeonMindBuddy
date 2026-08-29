"""Tests for graph object authoring prepare service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.ports.world_graph_authority import (
    WorldGraphAuthorityError,
    WorldGraphHead,
    WorldGraphPublicationReceipt,
)
from apps.live_control_server.ports.world_graph_source_admission import (
    AdmittedSourceIdentity,
    WorldGraphSourceAdmissionError,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    BACKUPS_DIR,
    EVENTS_DIR,
    OVERLAYS_DIR,
    GraphAuthoringOverlayStore,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
    GraphObjectAuthoringError,
    GraphObjectAuthoringPrepareRequest,
    build_assertions_from_proposals,
    build_confirm_token,
    classify_graph_review_expressibility,
    prepare_graph_object_authoring_write,
    stable_json_digest,
)

CAMPAIGN_ID = "longmont-c1"
TEST_CAMPAIGN_REL = "Test Campaign/A5"
STAMP = "1970-01-01T00:00:00Z"
SOURCE_ARTIFACT_ID = "art:graph-review-source"
SOURCE_REVISION_ID = "rev:graph-review-source"


@dataclass
class FakeWorldGraphAuthority:
    revision_id: str = "rev:d0"
    fail_publish_after_store: bool = False
    receipts: dict[str, WorldGraphPublicationReceipt] = field(default_factory=dict)
    publish_calls: int = 0
    recover_calls: int = 0
    published_requests: list[object] = field(default_factory=list)

    def current_head(self, world_id: str) -> WorldGraphHead:
        return WorldGraphHead(world_id=world_id, revision_id=self.revision_id)

    def recover(self, world_id: str, authority_operation_id: str, **kwargs):
        self.recover_calls += 1
        return self.receipts.get(authority_operation_id)

    def publish(self, request):
        self.publish_calls += 1
        self.published_requests.append(request)
        child = f"rev:d{self.publish_calls}"
        published = WorldGraphPublicationReceipt(
            world_id=request.world_id,
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=request.expected_parent_revision_id,
            published_revision_id=child,
            reviewed_contribution_id="contrib:graph-review",
            accepted_assertion_ids=(),
            published=True,
            outcome="published",
        )
        self.receipts[request.authority_operation_id] = WorldGraphPublicationReceipt(
            world_id=request.world_id,
            authority_operation_id=request.authority_operation_id,
            parent_revision_id=request.expected_parent_revision_id,
            published_revision_id=child,
            reviewed_contribution_id="contrib:graph-review",
            accepted_assertion_ids=(),
            published=True,
            outcome="already_applied",
        )
        if self.fail_publish_after_store:
            self.fail_publish_after_store = False
            self.revision_id = child
            raise WorldGraphAuthorityError(
                "provider committed but the client response was lost",
                code="publication_failed",
            )
        self.revision_id = child
        return published


@dataclass
class FakeSourceAdmission:
    error: Exception | None = None

    def prove_or_admit(self, request) -> AdmittedSourceIdentity:
        if self.error is not None:
            raise self.error
        artifact_id = str(request.source_artifact.source_artifact_id)
        token = str(request.source_revision_token)
        digest = str(getattr(request.source_artifact, "content_sha256", "") or "")
        return AdmittedSourceIdentity(
            source_artifact_id=artifact_id,
            source_revision_id=token,
            content_sha256=digest,
            buddy_source_revision_id=token,
        )

    def prove(
        self,
        *,
        world_id: str,
        source_artifact_id: str,
        source_revision_id: str,
        source_revision_token: str | None = None,
    ) -> AdmittedSourceIdentity:
        if self.error is not None:
            raise self.error
        token = str(source_revision_token or source_revision_id)
        return AdmittedSourceIdentity(
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            content_sha256="",
            buddy_source_revision_id=token,
        )


def fake_source_artifact(*, campaign_id: str = CAMPAIGN_ID, world_id: str | None = None):
    resolved_world = world_id if world_id is not None else campaign_id
    return SimpleNamespace(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_domain="worldbuilding",
        campaign_id=campaign_id,
        session_id=None,
        uri="object://graph-review-source",
        content_sha256="ab" * 32,
        artifact_kind="markdown",
        document_class="lore",
        authority_state="reviewed",
        visibility_state="internal",
        world_id=resolved_world,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at="1970-01-01T00:00:00Z",
        updated_at="1970-01-01T00:00:00Z",
    )


def fake_resolved_source(*, campaign_id: str = CAMPAIGN_ID, world_id: str | None = None):
    resolved_world = world_id if world_id is not None else campaign_id
    artifact = fake_source_artifact(campaign_id=campaign_id, world_id=resolved_world)
    return SimpleNamespace(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_revision_id=SOURCE_REVISION_ID,
        campaign_id=campaign_id,
        world_id=resolved_world,
        sealed_source_uri=artifact.uri,
        source_artifact=artifact,
    )


@pytest.fixture(autouse=True)
def graph_review_unit_seams(monkeypatch: pytest.MonkeyPatch) -> FakeSourceAdmission:
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "d2c4-unit-test-key")
    fake = FakeSourceAdmission()
    monkeypatch.setattr(
        "apps.live_control_server.ports.world_graph_source_admission_access.get_world_graph_source_admission_authority",
        lambda: fake,
    )
    return fake


def expressible_prepare(request, *, corpus_root: Path, authority=None, resolved_source=None, source_admission=None):
    return prepare_graph_object_authoring_write(
        request,
        corpus_root=corpus_root,
        authority=authority or FakeWorldGraphAuthority(),
        resolved_source=resolved_source or fake_resolved_source(),
        source_admission=source_admission,
    )


def _visibility() -> dict[str, object]:
    return {"visibility": "gm_private", "revealState": "unrevealed"}


def _provenance() -> dict[str, object]:
    return {
        "origin": "human_authored",
        "authoringSurface": "memory_ingest_graph_authoring",
        "sourceGraphId": "graph-c1s2",
    }


def _selection() -> dict[str, object]:
    return {
        "selectionKind": "text_span",
        "selectedText": "gang",
        "normalizedSelectedText": "gang",
        "paragraphOrdinal": 0,
        "tiptapFrom": 0,
        "tiptapTo": 4,
    }


def object_proposal(**overrides) -> dict[str, object]:
    payload = {
        "localProposalId": "local-object-1",
        "proposalKind": "object",
        "status": "staged_local",
        "selection": _selection(),
        "objectRef": {
            "label": "Questionable Company",
            "kind": "party",
            "role": None,
            "aliases": ["gang"],
            "summary": "Mercenary company",
        },
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }
    payload.update(overrides)
    return payload


def link_existing_proposal(**overrides) -> dict[str, object]:
    payload = {
        "localProposalId": "local-link-1",
        "proposalKind": "link_existing",
        "status": "staged_local",
        "selection": _selection(),
        "selectedText": "gang",
        "normalizedSelectedText": "gang",
        "existingObjectRef": {
            "refKind": "manual_ref",
            "label": "Questionable Company",
        },
        "operation": "alias",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }
    payload.update(overrides)
    return payload


def relationship_proposal(**overrides) -> dict[str, object]:
    payload = {
        "localProposalId": "local-rel-1",
        "proposalKind": "relationship",
        "status": "staged_local",
        "sourceObjectRef": {
            "refKind": "manual_ref",
            "label": "Questionable Company",
        },
        "targetObjectRef": {
            "refKind": "existing_graph_node",
            "nodeId": "pc_bonogo",
            "label": "Bonogo",
            "kind": "pc",
        },
        "relationshipType": "has_member",
        "direction": "directed",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }
    payload.update(overrides)
    return payload


def prepare_request(**overrides) -> GraphObjectAuthoringPrepareRequest:
    payload = {
        "campaignId": CAMPAIGN_ID,
        "campaignRel": TEST_CAMPAIGN_REL,
        "sessionId": "session-2",
        "worldId": CAMPAIGN_ID,
        "sourceRunId": "run-c1s2",
        "proposals": [object_proposal()],
    }
    payload.update(overrides)
    return GraphObjectAuthoringPrepareRequest.model_validate(payload)


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    return tmp_path / "corpus"


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def test_prepare_with_empty_proposals_fails() -> None:
    request = GraphObjectAuthoringPrepareRequest.model_validate(
        {"campaignId": CAMPAIGN_ID, "proposals": []},
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(request, corpus_root=Path("/tmp/unused"))
    assert exc.value.code == "empty_proposals"


def test_prepare_object_proposal_returns_object_assertion_preview(store: GraphAuthoringOverlayStore) -> None:
    response = expressible_prepare(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert response.assertion_count == 1
    assert response.assertions_preview[0].assertion_kind == "object"
    assert "Questionable Company" in response.assertions_preview[0].summary


def test_prepare_link_existing_proposal_returns_link_existing_preview(
    store: GraphAuthoringOverlayStore,
) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(proposals=[link_existing_proposal()]),
        corpus_root=store.corpus_root,
    )
    assert response.overlay_summary.link_existing_count == 1


def test_prepare_relationship_proposal_returns_relationship_preview(
    store: GraphAuthoringOverlayStore,
) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(proposals=[relationship_proposal()]),
        corpus_root=store.corpus_root,
    )
    assert response.overlay_summary.relationship_count == 1


def test_prepare_accepts_cross_scope_object_ref_metadata(store: GraphAuthoringOverlayStore) -> None:
    response = prepare_graph_object_authoring_write(
        prepare_request(
            proposals=[
                link_existing_proposal(
                    existingObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "party:bonogo",
                        "label": "Bonogo",
                        "kind": "pc",
                        "graphScope": "party_pc",
                        "sourceLabel": "Party / PCs",
                        "sourceGraphId": "longmont-c2:party",
                        "sourcePath": "_party_registry.json",
                        "visibility": "table_known",
                    }
                ),
                relationship_proposal(
                    targetObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "loc_mirathorn",
                        "label": "Mirathorn",
                        "kind": "location",
                        "graphScope": "worldbuilding",
                        "sourceLabel": "Worldbuilding",
                    }
                ),
            ]
        ),
        corpus_root=store.corpus_root,
    )
    assert response.prepared is True
    assert response.overlay_summary.link_existing_count == 1
    assert response.overlay_summary.relationship_count == 1


def test_build_object_ref_persists_cross_scope_source_metadata() -> None:
    request = prepare_request(
        proposals=[
            link_existing_proposal(
                existingObjectRef={
                    "refKind": "existing_graph_node",
                    "nodeId": "party:bonogo",
                    "label": "Bonogo",
                    "kind": "pc",
                    "graphScope": "party_pc",
                    "sourceLabel": "Party / PCs",
                    "sourceGraphId": "longmont-c2:party",
                    "sourcePath": "_party_registry.json",
                    "visibility": "table_known",
                }
            ),
            relationship_proposal(
                targetObjectRef={
                    "refKind": "existing_graph_node",
                    "nodeId": "loc_mirathorn",
                    "label": "Mirathorn",
                    "kind": "location",
                    "graphScope": "worldbuilding",
                    "sourceLabel": "Worldbuilding",
                }
            ),
        ]
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert not diagnostics
    link_ref = assertions[0].existing_object_ref
    assert link_ref.candidate_graph_scope == "party_pc"
    assert link_ref.source_label == "Party / PCs"
    assert link_ref.source_graph_id == "longmont-c2:party"
    assert link_ref.source_path == "_party_registry.json"
    assert link_ref.source_visibility == "table_known"

    target_ref = assertions[1].target_object_ref
    assert target_ref.candidate_graph_scope == "worldbuilding"
    assert target_ref.source_label == "Worldbuilding"
    assert target_ref.source_graph_id is None
    assert target_ref.source_path is None
    assert target_ref.source_visibility is None


def test_commit_persists_cross_scope_object_ref_metadata(store: GraphAuthoringOverlayStore) -> None:
    from apps.live_control_server.services.graph_object_authoring_commit import (
        GraphObjectAuthoringCommitRequest,
        commit_graph_object_authoring_write,
    )

    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare_response = expressible_prepare(
        prepare_request(
            proposals=[
                link_existing_proposal(
                    existingObjectRef={
                        "refKind": "existing_graph_node",
                        "nodeId": "party:bonogo",
                        "label": "Bonogo",
                        "kind": "pc",
                        "graphScope": "party_pc",
                        "sourceLabel": "Party / PCs",
                    }
                )
            ]
        ),
        corpus_root=store.corpus_root,
        authority=authority,
        resolved_source=source,
    )
    commit_response = commit_graph_object_authoring_write(
        GraphObjectAuthoringCommitRequest.model_validate(
            {
                "campaignId": CAMPAIGN_ID,
                "campaignRel": TEST_CAMPAIGN_REL,
                "sessionId": "session-2",
                "worldId": CAMPAIGN_ID,
                "sourceRunId": "run-c1s2",
                "proposals": [
                    link_existing_proposal(
                        existingObjectRef={
                            "refKind": "existing_graph_node",
                            "nodeId": "party:bonogo",
                            "label": "Bonogo",
                            "kind": "pc",
                            "graphScope": "party_pc",
                            "sourceLabel": "Party / PCs",
                        }
                    )
                ],
                "confirmToken": prepare_response.confirm_token,
                "currentOverlayToken": prepare_response.current_overlay_token,
            }
        ),
        corpus_root=store.corpus_root,
        authority=authority,
        resolved_source=source,
    )
    assert commit_response.committed is True
    assert commit_response.published_revision_id == "rev:d1"
    assert commit_response.parent_revision_id == "rev:d0"
    assert authority.publish_calls == 1
    overlay_path = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert not overlay_path.exists()


def test_prepare_writes_nothing(store: GraphAuthoringOverlayStore) -> None:
    campaign_dir = store.corpus_root / TEST_CAMPAIGN_REL
    expressible_prepare(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    authoring_root = campaign_dir / "_graph_authoring"
    assert not (authoring_root / OVERLAYS_DIR).exists()
    assert not (authoring_root / EVENTS_DIR).exists()
    assert not (authoring_root / BACKUPS_DIR).exists()


def test_prepare_returns_proposed_assertions_digest(store: GraphAuthoringOverlayStore) -> None:
    response = expressible_prepare(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert len(response.proposed_assertions_digest) == 64
    assert response.proposed_assertions_digest != response.current_overlay_token


def test_prepare_returns_confirm_token(store: GraphAuthoringOverlayStore) -> None:
    response = expressible_prepare(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert response.confirm_token.startswith("v1.")
    assert response.expected_parent_revision_id == "rev:d0"
    assert response.authority_operation_id.startswith("grauth:")
    assert response.expressibility == "EXPRESSIBLE"


def test_prepare_token_is_deterministic(
    store: GraphAuthoringOverlayStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 28, 18, 0, tzinfo=UTC)

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_object_authoring_prepare.datetime",
        FrozenDateTime,
    )
    authority = FakeWorldGraphAuthority()
    first = expressible_prepare(
        prepare_request(),
        corpus_root=store.corpus_root,
        authority=authority,
    )
    second = expressible_prepare(
        prepare_request(),
        corpus_root=store.corpus_root,
        authority=authority,
    )
    assert first.confirm_token == second.confirm_token
    assert first.current_overlay_token == second.current_overlay_token
    assert first.proposed_assertions_digest == second.proposed_assertions_digest
    assert first.assertions_preview[0].assertion_id == second.assertions_preview[0].assertion_id


def test_build_assertions_preserves_zero_source_anchor_offsets() -> None:
    request = prepare_request(
        proposals=[
            object_proposal(
                selection={
                    "selectionKind": "text_span",
                    "selectedText": "x",
                    "normalizedSelectedText": "x",
                    "paragraphOrdinal": 0,
                    "tiptapFrom": 0,
                    "tiptapTo": 0,
                }
            )
        ]
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert not diagnostics
    anchor = assertions[0].source_anchor
    assert anchor is not None
    assert anchor.paragraph_ordinal == 0
    assert anchor.tiptap_from == 0
    assert anchor.tiptap_to == 0


def test_prepare_rejects_blank_relationship_type(store: GraphAuthoringOverlayStore) -> None:
    request = prepare_request(proposals=[relationship_proposal(relationshipType="   ")])
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(request, corpus_root=store.corpus_root)
    assert exc.value.code == "invalid_relationship_type"


def test_prepare_rejects_blank_object_ref_label(store: GraphAuthoringOverlayStore) -> None:
    request = prepare_request(
        proposals=[
            object_proposal(
                objectRef={
                    "label": "   ",
                    "kind": "party",
                    "aliases": [],
                }
            )
        ]
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(request, corpus_root=store.corpus_root)
    assert exc.value.code == "invalid_proposal"


def test_prepare_response_includes_no_mutation_guarantees(store: GraphAuthoringOverlayStore) -> None:
    response = expressible_prepare(
        prepare_request(),
        corpus_root=store.corpus_root,
    )
    assert "Prepare wrote nothing." in response.no_mutation_guarantees
    assert any("graph gold" in item.lower() for item in response.no_mutation_guarantees)


def test_confirm_token_uses_stable_json_digest() -> None:
    assert stable_json_digest({"a": 1}) == stable_json_digest({"a": 1})
    assert stable_json_digest({"a": 1}) != stable_json_digest({"a": 2})


def test_build_confirm_token_changes_when_assertions_change() -> None:
    request_a = prepare_request(proposals=[object_proposal()])
    request_b = prepare_request(proposals=[object_proposal(localProposalId="local-object-2")])
    assertions_a, _ = build_assertions_from_proposals(request_a)
    assertions_b, _ = build_assertions_from_proposals(request_b)
    token_a = build_confirm_token(
        campaign_id=CAMPAIGN_ID,
        overlay_path="/tmp/overlay.json",
        current_overlay_token="abc",
        assertions=assertions_a,
    )
    token_b = build_confirm_token(
        campaign_id=CAMPAIGN_ID,
        overlay_path="/tmp/overlay.json",
        current_overlay_token="abc",
        assertions=assertions_b,
    )
    assert token_a != token_b


def test_classify_object_is_expressible() -> None:
    request = prepare_request(proposals=[object_proposal()])
    assert classify_graph_review_expressibility(request.proposals) == "EXPRESSIBLE"


def test_classify_link_without_node_id_is_inexpressible() -> None:
    request = prepare_request(proposals=[link_existing_proposal()])
    assert classify_graph_review_expressibility(request.proposals) == "INEXPRESSIBLE"


def test_classify_unknown_kind_is_inexpressible() -> None:
    class _Unknown:
        proposal_kind = "explode"
        existing_object_ref = None
        source_object_ref = None
        target_object_ref = None

    assert classify_graph_review_expressibility([_Unknown()]) == "INEXPRESSIBLE"


def test_prepare_merge_objects_is_inexpressible_without_source(
    store: GraphAuthoringOverlayStore,
) -> None:
    from tests.test_graph_object_authoring_merge_prepare import merge_proposal

    response = prepare_graph_object_authoring_write(
        prepare_request(proposals=[merge_proposal()], sourceRunId=None),
        corpus_root=store.corpus_root,
    )
    assert response.expressibility == "INEXPRESSIBLE"
    assert response.expected_parent_revision_id is None
    assert any(item.code == "governed_write_inexpressible" for item in response.diagnostics)
    overlay_path = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert not overlay_path.exists()


def test_prepare_object_without_source_run_fails(store: GraphAuthoringOverlayStore) -> None:
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(
            prepare_request(sourceRunId=None),
            corpus_root=store.corpus_root,
            authority=FakeWorldGraphAuthority(),
        )
    assert exc.value.code == "source_unresolved"


def test_prepare_missing_source_artifact_fails_closed(
    store: GraphAuthoringOverlayStore,
    graph_review_unit_seams: FakeSourceAdmission,
) -> None:
    graph_review_unit_seams.error = WorldGraphSourceAdmissionError(
        "source artifact was not found",
        code="source_not_admitted",
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(
            prepare_request(),
            corpus_root=store.corpus_root,
            authority=FakeWorldGraphAuthority(),
            resolved_source=fake_resolved_source(),
        )
    assert exc.value.code == "source_artifact_not_found"


def test_prepare_fails_closed_without_stable_binding_key(
    store: GraphAuthoringOverlayStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, raising=False)
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(
            prepare_request(),
            corpus_root=store.corpus_root,
            authority=FakeWorldGraphAuthority(),
            resolved_source=fake_resolved_source(),
            source_admission=FakeSourceAdmission(),
        )
    assert exc.value.code == "authority_unavailable"


def test_prepare_wrong_world_source_fails_closed(
    store: GraphAuthoringOverlayStore,
) -> None:
    with pytest.raises(GraphObjectAuthoringError) as exc:
        prepare_graph_object_authoring_write(
            prepare_request(),
            corpus_root=store.corpus_root,
            authority=FakeWorldGraphAuthority(),
            resolved_source=fake_resolved_source(world_id="other-world"),
        )
    assert exc.value.code == "source_inadmissible"
