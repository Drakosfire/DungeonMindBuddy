"""Historical proposal/signature unit composition with synthetic source/authority seams."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from apps.live_control_server.services.graph_object_authoring_commit import (
    commit_graph_object_authoring_write,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringError,
    sign_publication_intent,
    VerifiedGraphReviewSpan,
)
from tests.test_graph_object_authoring_prepare import (
    CAMPAIGN_ID,
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
    TEST_CAMPAIGN_REL,
    FakeSourceAdmission,
    FakeWorldGraphAuthority,
    expressible_prepare,
    fake_resolved_source,
    link_existing_proposal,
    object_proposal,
    prepare_request,
    relationship_proposal,
)


@pytest.fixture(autouse=True)
def graph_review_unit_seams(monkeypatch: pytest.MonkeyPatch) -> FakeSourceAdmission:
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "d2c4-unit-test-key")
    # These unit tests isolate proposal/signature behavior; registered ownership
    # and distinct native routing are exercised by test_graph_object_authoring_world_binding.
    from apps.live_control_server.services.graph_object_authoring_binding import GraphReviewPublicationContext
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_object_authoring_binding.resolve_publication_context",
        lambda request, resolved, **_: GraphReviewPublicationContext(request.world_id or request.campaign_id, request.campaign_id),
    )
    # Match the existing prepare-unit seam: these fixtures carry an object://
    # source, synthetic verified spans and fake admission, not a real APP body.
    # Mounted receipt recovery and real native APP admission have separate owners.
    monkeypatch.setattr(
        "apps.live_control_server.services.source_artifact_registry.load_source_input_bytes",
        lambda _artifact: b"Synthetic proposal unit-test body",
    )
    fake = FakeSourceAdmission()
    monkeypatch.setattr(
        "apps.live_control_server.ports.world_graph_source_admission_access.get_world_graph_source_admission_authority",
        lambda: fake,
    )
    def verified_unit_spans(*, assertions, resolved_source, **_kwargs):
        artifact = resolved_source.source_artifact
        return {
            assertion.assertion_id: VerifiedGraphReviewSpan(
                assertion_id=assertion.assertion_id,
                evidence_ref_id=f"grauth-ev:{artifact.source_artifact_id}:{assertion.assertion_id}",
                source_artifact_id=artifact.source_artifact_id,
                source_revision_id=resolved_source.source_revision_id,
                source_domain="worldbuilding",
                source_span_ref_id=f"unit:{assertion.assertion_id}",
                source_content_sha256="ab" * 32,
                span_content_sha256="cd" * 32,
                span_index_sha256="ef" * 32,
                visibility_state="internal",
            )
            for assertion in assertions
        }
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_object_authoring_prepare.verify_graph_review_assertion_spans",
        verified_unit_spans,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_object_authoring_commit.verify_graph_review_assertion_spans",
        verified_unit_spans,
    )
    return fake


def expressible_relationship_proposal(**overrides) -> dict[str, object]:
    payload = relationship_proposal(
        sourceObjectRef={
            "refKind": "existing_graph_node",
            "nodeId": "local-object-1",
            "label": "Questionable Company",
            "kind": "party",
        },
        targetObjectRef={
            "refKind": "existing_graph_node",
            "nodeId": "pc_bonogo",
            "label": "Bonogo",
            "kind": "pc",
        },
    )
    payload.update(overrides)
    return payload


def expressible_link_proposal(**overrides) -> dict[str, object]:
    payload = link_existing_proposal(
        existingObjectRef={
            "refKind": "existing_graph_node",
            "nodeId": "party:bonogo",
            "label": "Bonogo",
            "kind": "pc",
        }
    )
    payload.update(overrides)
    return payload


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    campaign_dir = root / TEST_CAMPAIGN_REL
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "Session Recaps").mkdir()
    recap = campaign_dir / "Session Recaps" / "recap.md"
    recap.write_text("# recap\n", encoding="utf-8")
    (campaign_dir / "_graph_gold").mkdir()
    gold = campaign_dir / "_graph_gold" / "candidate_graph_gold.json"
    gold.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
    live_run = campaign_dir / "_live_runs" / "run-1"
    live_run.mkdir(parents=True)
    manifest = live_run / "manifest.json"
    manifest.write_text(json.dumps({"run_id": "run-1"}), encoding="utf-8")
    return root


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def _commit_request_from_prepare(
    prepare_response,
    *,
    proposals: list[dict[str, object]] | None = None,
    source_run_id: str | None = "run-c1s2",
    recap_artifact_id: str | None = None,
    source_graph_id: str | None = None,
    campaign_id: str = CAMPAIGN_ID,
    merge_into_union: bool | None = None,
) -> GraphObjectAuthoringCommitRequest:
    payload: dict[str, object] = {
        "campaignId": campaign_id,
        "campaignRel": TEST_CAMPAIGN_REL,
        "sessionId": "session-2",
        "worldId": campaign_id,
        "proposals": proposals or [object_proposal()],
        "confirmToken": prepare_response.confirm_token,
        "currentOverlayToken": prepare_response.current_overlay_token,
    }
    if source_run_id is not None:
        payload["sourceRunId"] = source_run_id
    if recap_artifact_id is not None:
        payload["recapArtifactId"] = recap_artifact_id
    if source_graph_id is not None:
        payload["sourceGraphId"] = source_graph_id
    if merge_into_union is not None:
        payload["mergeIntoUnion"] = merge_into_union
    return GraphObjectAuthoringCommitRequest.model_validate(payload)


def _mtime(path: Path) -> float:
    return path.stat().st_mtime


def test_commit_publishes_object_through_dungeonmind(
    store: GraphAuthoringOverlayStore, corpus_root: Path
) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    with patch(
        "apps.live_control_server.services.graph_authoring_overlay_store.GraphAuthoringOverlayStore.append_assertions",
        side_effect=AssertionError("overlay append invoked"),
    ):
        response = commit_graph_object_authoring_write(
            _commit_request_from_prepare(prepare),
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert response.committed is True
    assert response.world_id == CAMPAIGN_ID
    assert response.parent_revision_id == "rev:d0"
    assert response.published_revision_id == "rev:d1"
    assert response.operation_id == prepare.authority_operation_id
    assert response.result == "published"
    assert response.idempotency_status == "published"
    assert response.audit_status == "skipped"
    assert response.overlay_path is None
    assert response.event_log_path is None
    assert authority.publish_calls == 1
    contrib = authority.published_requests[0].contribution
    assert contrib.source_kind == "graph_review_authored_assertion"
    assert contrib.accepted_assertions[0].assertion_kind == "node"
    overlay = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert not overlay.exists()


def test_commit_binds_authenticated_actor_in_signed_intent(corpus_root: Path, monkeypatch) -> None:
    from apps.live_control_server.services.graph_object_authoring_prepare import prepare_graph_object_authoring_write

    monkeypatch.setattr(
        "apps.live_control_server.services.source_artifact_registry.load_source_input_bytes",
        lambda artifact: b"Synthetic proposal unit-test body",
    )
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    dependencies = dict(corpus_root=corpus_root, authority=authority, resolved_source=source)
    actor = "hosted_dms:owner"
    preview = prepare_graph_object_authoring_write(prepare_request(), authenticated_actor=actor, **dependencies)
    command = _commit_request_from_prepare(preview)
    with pytest.raises(GraphObjectAuthoringError) as denied:
        commit_graph_object_authoring_write(command, authenticated_actor="hosted_dms:other", **dependencies)
    assert denied.value.code == "confirmation_invalid"
    from fastapi import HTTPException

    def transferred():
        raise HTTPException(status_code=403)

    with pytest.raises(HTTPException) as revoked:
        commit_graph_object_authoring_write(
            command, authenticated_actor=actor, authorize_world=transferred, **dependencies,
        )
    assert revoked.value.status_code == 403
    assert authority.publish_calls == 0
    assert commit_graph_object_authoring_write(command, authenticated_actor=actor, **dependencies).committed


def test_commit_binds_recap_selector_and_rejects_selector_swap(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    recap_id = "longmont-c1/session-2"
    prepare = expressible_prepare(
        prepare_request(sourceRunId=None, recapArtifactId=recap_id),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )

    committed = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare,
            source_run_id=None,
            recap_artifact_id=recap_id,
        ),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    assert committed.committed is True
    assert committed.committed_proposal_ids == ["local-object-1"]

    swapped = _commit_request_from_prepare(
        prepare,
        source_run_id=None,
        recap_artifact_id="longmont-c1/session-3",
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            swapped,
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "confirmation_invalid"
    assert authority.publish_calls == 1


def test_commit_exact_retry_recovers_same_child(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    first = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    second = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    assert first.published_revision_id == second.published_revision_id == "rev:d1"
    assert second.idempotency_status == "already_applied"
    assert authority.publish_calls == 1


def test_commit_recovers_lost_provider_response(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority(fail_publish_after_store=True)
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    assert response.published_revision_id == "rev:d1"
    assert response.idempotency_status == "already_applied"
    assert authority.publish_calls == 1


def test_commit_link_existing_publishes_alias(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    proposals = [expressible_link_proposal()]
    prepare = expressible_prepare(
        prepare_request(proposals=proposals),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare, proposals=proposals),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    assert response.published_revision_id == "rev:d1"
    assertion = authority.published_requests[0].contribution.accepted_assertions[0]
    assert assertion.assertion_kind == "alias"
    assert assertion.identity_resolution_outcome == "resolved_existing"
    assert assertion.subject_node_id == "party:bonogo"


def test_commit_relationship_publishes_edge(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    proposals = [expressible_relationship_proposal()]
    prepare = expressible_prepare(
        prepare_request(proposals=proposals),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare, proposals=proposals),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    assertion = authority.published_requests[0].contribution.accepted_assertions[0]
    assert assertion.assertion_kind == "edge"
    assert assertion.subject_node_id == "local-object-1"
    assert assertion.target_node_id == "pc_bonogo"
    assert response.published_revision_id == "rev:d1"


def test_commit_merge_objects_fails_closed_with_zero_side_effect(
    store: GraphAuthoringOverlayStore, corpus_root: Path
) -> None:
    from tests.test_graph_object_authoring_merge_prepare import merge_proposal

    authority = FakeWorldGraphAuthority()
    prepare = expressible_prepare(
        prepare_request(proposals=[merge_proposal()]),
        corpus_root=corpus_root,
        authority=authority,
    )
    assert prepare.expressibility == "INEXPRESSIBLE"
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            _commit_request_from_prepare(prepare, proposals=[merge_proposal()]),
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=fake_resolved_source(),
        )
    assert exc.value.code == "governed_write_inexpressible"
    assert authority.publish_calls == 0
    assert authority.revision_id == "rev:d0"
    overlay = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert not overlay.exists()


def test_commit_legacy_merge_into_union_false_fails_closed(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            _commit_request_from_prepare(prepare, merge_into_union=False),
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "governed_write_inexpressible"
    assert authority.publish_calls == 0


def test_commit_with_bad_token_fails(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    request = _commit_request_from_prepare(prepare)
    request = request.model_copy(update={"confirm_token": "deadbeef" * 8})
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            request,
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "confirmation_invalid"
    assert authority.publish_calls == 0


def test_commit_tampered_proposals_fail(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            _commit_request_from_prepare(
                prepare,
                proposals=[object_proposal(localProposalId="local-object-2")],
            ),
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "confirmation_invalid"
    assert authority.publish_calls == 0


def test_commit_expired_token_fails(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    from apps.live_control_server.services.graph_object_authoring_prepare import decode_publication_intent
    # Expiry-independent receipt recovery still requires a complete valid binding.
    expired = decode_publication_intent(prepare.confirm_token)
    expired["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    request = _commit_request_from_prepare(prepare)
    request = request.model_copy(update={"confirm_token": sign_publication_intent(expired)})
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            request,
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "confirmation_expired"
    assert authority.publish_calls == 0


def test_commit_stale_parent_fails(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    authority.revision_id = "rev:external"
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            _commit_request_from_prepare(prepare),
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "stale_parent"
    assert authority.publish_calls == 0


def test_commit_source_inadmissible_fails(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=fake_resolved_source(),
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            _commit_request_from_prepare(prepare),
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=fake_resolved_source(campaign_id="other-campaign"),
        )
    assert exc.value.code == "source_inadmissible"
    assert authority.publish_calls == 0


def test_commit_rejects_invalid_object_ref(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    request = GraphObjectAuthoringCommitRequest.model_validate(
        {
            "campaignId": CAMPAIGN_ID,
            "campaignRel": TEST_CAMPAIGN_REL,
            "worldId": CAMPAIGN_ID,
            "sourceRunId": "run-c1s2",
            "proposals": [
                object_proposal(
                    objectRef={"label": "   ", "kind": "party", "aliases": []},
                )
            ],
            "confirmToken": prepare.confirm_token,
            "currentOverlayToken": prepare.current_overlay_token,
        }
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            request,
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "invalid_proposal"


def test_commit_response_includes_no_mutation_guarantees(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    joined = " ".join(response.no_mutation_guarantees).lower()
    assert "source markdown" in joined
    assert "unionsupergraph" in joined
    assert "overlay was not the graph authority" in joined


def test_commit_does_not_touch_source_markdown_live_artifact_or_gold(
    corpus_root: Path,
) -> None:
    campaign_dir = corpus_root / TEST_CAMPAIGN_REL
    recap = campaign_dir / "Session Recaps" / "recap.md"
    gold = campaign_dir / "_graph_gold" / "candidate_graph_gold.json"
    manifest = campaign_dir / "_live_runs" / "run-1" / "manifest.json"
    mtimes = {path: _mtime(path) for path in (recap, gold, manifest)}
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    for path, before in mtimes.items():
        assert _mtime(path) == before


def test_commit_with_empty_proposals_fails() -> None:
    request = GraphObjectAuthoringCommitRequest.model_validate(
        {
            "campaignId": CAMPAIGN_ID,
            "campaignRel": TEST_CAMPAIGN_REL,
            "proposals": [],
            "confirmToken": "abc",
            "currentOverlayToken": "abc",
        }
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(request, corpus_root=Path("/tmp/unused"))
    assert exc.value.code == "empty_proposals"


def test_commit_rejects_unsafe_campaign_rel(corpus_root: Path) -> None:
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    request = _commit_request_from_prepare(prepare).model_copy(
        update={"campaign_rel": "../../../outside"},
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            request,
            corpus_root=corpus_root,
            authority=authority,
            resolved_source=source,
        )
    assert exc.value.code == "unsafe_campaign_rel"


def test_commit_token_survives_stable_binding_key_reread(corpus_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "stable-across-instances")
    authority = FakeWorldGraphAuthority()
    source = fake_resolved_source()
    prepare = expressible_prepare(
        prepare_request(),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "stable-across-instances")
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
        authority=authority,
        resolved_source=source,
    )
    assert response.published_revision_id == "rev:d1"
    assert response.audit_status == "skipped"
    assert response.overlay_path is None
    assert response.event_log_path is None


# Immutable manual recovery: these are reconstruction diagnostics, not mounted
# recovery/SQL acceptance. Those witnesses must additionally exercise the reader.
def _historical_manual_recipe(*, relationship: bool = False, alias: bool = False):
    from dataclasses import asdict
    from types import SimpleNamespace
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        build_assertions_from_proposals,
        contribution_binding_digest,
        translate_assertions_to_contribution,
    )
    from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
        map_graph_review_contribution_v3,
    )

    proposal = (expressible_relationship_proposal(relationshipType="belongs_to", sourceObjectRef={
        "refKind": "existing_graph_node", "nodeId": "local-object-1", "label": "A sword", "kind": "item",
    })
                if relationship else expressible_link_proposal() if alias else object_proposal())
    assertions, diagnostics = build_assertions_from_proposals(prepare_request(proposals=[proposal]))
    assert not [item for item in diagnostics if item.severity == "error"]
    spans = {
        assertion.assertion_id: VerifiedGraphReviewSpan(
            assertion_id=assertion.assertion_id,
            evidence_ref_id=f"grauth-ev:art:original:{assertion.assertion_id}",
            source_artifact_id="art:original", source_revision_id="buddy:original",
            source_domain="worldbuilding", source_span_ref_id="paragraph:original",
            source_content_sha256="ab" * 32, span_content_sha256="cd" * 32,
            span_index_sha256="ef" * 32, visibility_state="internal",
        ) for assertion in assertions
    }
    original = translate_assertions_to_contribution(
        world_id=CAMPAIGN_ID, campaign_id=CAMPAIGN_ID, actor="original-actor",
        source_artifact_id="art:original", source_revision_id="buddy:original",
        assertions=assertions, verified_spans=spans,
    )
    mapped = map_graph_review_contribution_v3(
        SimpleNamespace(evidence={}), original,
        {("art:original", "buddy:original"): "rev:admitted"},
    )
    kwargs = dict(candidate=mapped, assertions=assertions, world_id=CAMPAIGN_ID,
                  campaign_scope=CAMPAIGN_ID, actor="original-actor",
                  sealed_artifact_id="art:original",
                  sealed_contribution_digest=contribution_binding_digest(original))
    assert json.loads(mapped.assertions[0].value)["evidence"] == [asdict(next(iter(spans.values())))]
    return original, mapped, kwargs


def test_historical_manual_reconstruction_uses_original_buddy_source_pair(monkeypatch):
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import (
        reconstruct_original_contribution,
    )
    original, mapped, kwargs = _historical_manual_recipe()
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_object_authoring_prepare.resolve_graph_review_source",
        lambda *a, **k: pytest.fail("historical reconstruction read a mutable source"),
    )
    recovered = reconstruct_original_contribution(**kwargs)
    assert recovered.model_dump(mode="json") == original.model_dump(mode="json")
    assert recovered.source_revision_id == "buddy:original"
    assert mapped.source_revision_id == "rev:admitted"


@pytest.mark.parametrize("mutation", [
    "span_digest", "buddy_revision", "foreign_artifact", "duplicate_assertion",
    "missing_assertion", "missing_metadata", "unknown_metadata", "wrong_actor",
    "changed_request",
])
def test_historical_manual_reconstruction_rejects_substituted_original(mutation):
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import (
        reconstruct_original_contribution,
    )
    _, mapped, kwargs = _historical_manual_recipe()
    assertion = mapped.assertions[0].model_copy(deep=True)
    value = json.loads(assertion.value)
    row = value["evidence"][0]
    if mutation == "span_digest":
        row["span_content_sha256"] = "12" * 32
    elif mutation == "buddy_revision":
        row["source_revision_id"] = "rev:admitted"
    elif mutation == "foreign_artifact":
        row["source_artifact_id"] = "art:foreign"
    elif mutation == "missing_metadata":
        del row["span_index_sha256"]
    elif mutation == "unknown_metadata":
        row["invented"] = "value"
    elif mutation == "wrong_actor":
        kwargs["actor"] = "other-actor"
    elif mutation == "changed_request":
        kwargs["assertions"] = [kwargs["assertions"][0].model_copy(update={"summary": "changed"})]
    assertion = assertion.model_copy(update={"value": json.dumps(value)})
    assertions = [assertion]
    if mutation == "duplicate_assertion":
        assertions.append(assertion)
    elif mutation == "missing_assertion":
        assertions = []
    kwargs["candidate"] = mapped.model_copy(update={"assertions": assertions})
    with pytest.raises(GraphObjectAuthoringError) as error:
        reconstruct_original_contribution(**kwargs)
    assert error.value.code == "authority_integrity"


def test_historical_manual_candidate_reconstructs_reverse_edge_without_endpoint_admission(monkeypatch):
    from dungeonmind.contracts.contribution import AcceptanceState
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import (
        reconstruct_candidate,
    )
    original, mapped, _ = _historical_manual_recipe(relationship=True)
    monkeypatch.setattr(
        "apps.live_control_server.integrations.dungeonmind.world_graph_writes._assert_edge_endpoint_admission",
        lambda *a, **k: pytest.fail("historical reconstruction reran fresh endpoint admission"),
    )
    stamp = datetime(2025, 1, 1, tzinfo=UTC)
    reconstructed = reconstruct_candidate(original, admitted_revision_id="rev:admitted", reviewed_at=stamp)
    actual, prior = reconstructed.assertions[0], mapped.assertions[0]
    assert actual.subject_object_id == prior.object_object_id
    assert actual.object_object_id == prior.subject_object_id
    assert actual.predicate == "belongs_to"
    assert json.loads(actual.value) == {**json.loads(prior.value), "dm_predicate": "dnd5e:owns"}
    assert actual.acceptance_state is AcceptanceState.CANDIDATE
    assert actual.evidence_refs == prior.evidence_refs
    assert reconstructed.produced_at == stamp


def test_historical_manual_candidate_preserves_complete_node_value():
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import reconstruct_candidate
    original, mapped, _ = _historical_manual_recipe()
    reconstructed = reconstruct_candidate(
        original, admitted_revision_id="rev:admitted", reviewed_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    prior_value = json.loads(mapped.assertions[0].value)
    actual_value = json.loads(reconstructed.assertions[0].value)
    assert actual_value == {**prior_value, "dm_kind": "dnd5e:party"}
    assert prior_value["aliases"] and prior_value["summary"] and prior_value["role"]



def _coherent_historical_manual_review(*, mutation: str | None = None, recipe: str = "object"):
    """Use the historical producer and Core's real state builder, including forgeries."""
    from types import SimpleNamespace
    from dungeonmind.application.contribution_review_v3 import _build_review_state
    from dungeonmind.contracts.contribution import AcceptanceState
    from dungeonmind.contracts.contribution_review import (
        ContributionAssertionVerdict, ContributionPlanRef, derive_confirmation_id,
    )
    from dungeonmind.contracts.contribution_review_v3 import (
        CommitConfirmationReceiptV3, ContributionReviewIntentV3,
        ContributionReviewSubmissionV3, contribution_v3_payload_sha256,
        derive_review_intent_sha256_v3,
    )
    from dungeonmind.domain.canonical import canonical_sha256
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _build_v2_candidate, _build_identity_dispositions,
        WORLDBUILDING_SOURCE_PLAN_SCHEMA,
    )
    original, _, _ = _historical_manual_recipe(relationship=recipe == "edge", alias=recipe == "alias")
    stamp = datetime(2025, 1, 1, tzinfo=UTC)
    parent_id = "rev:sealed-parent"
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        derive_authority_review_operation_id, graph_review_authority_operation_id,
    )
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        build_assertions_from_proposals, proposed_assertions_digest,
    )
    proposal = (expressible_relationship_proposal(relationshipType="belongs_to", sourceObjectRef={
        "refKind": "existing_graph_node", "nodeId": "local-object-1", "label": "A sword", "kind": "item",
    }) if recipe == "edge"
                else expressible_link_proposal() if recipe == "alias" else object_proposal())
    original_assertions, _ = build_assertions_from_proposals(prepare_request(proposals=[proposal]))
    buddy_operation = graph_review_authority_operation_id(
        world_id=CAMPAIGN_ID, campaign_id=CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL,
        source_artifact_id="art:original", source_revision_id="rev:admitted",
        sealed_proposal_digest=proposed_assertions_digest(original_assertions),
        expected_parent_revision_id=parent_id,
    )
    operation_id = derive_authority_review_operation_id(
        world_id=CAMPAIGN_ID, authority_operation_id=buddy_operation, operation_namespace="worldbuilding",
    )
    profile = {"schema_version": "dm_semantic_profile_ref_v1", "profile_id": "dnd5e.default",
               "profile_revision": "1", "descriptor_sha256": "12" * 32}
    payload = {"semantic_profile": profile}
    parent = SimpleNamespace(revision=SimpleNamespace(
        world_id=CAMPAIGN_ID, revision_id=parent_id, status="published",
        graph_schema="dm_union_graph_v6", graph_payload_sha256=canonical_sha256(payload),
        created_at=stamp,
    ), graph_payload=payload)
    review_time = stamp + timedelta(seconds=1) if mutation == "timestamp" else stamp
    candidate, verdict_states = _build_v2_candidate(
        original, context=SimpleNamespace(objects={
            "local-object-1": SimpleNamespace(kind="item"),
            "pc_bonogo": SimpleNamespace(kind="pc"),
        }),
        pair_to_dm={("art:original", "buddy:original"): "rev:admitted"},
        produced_at=review_time,
    )
    if mutation in {"role", "alias", "summary", "qualification", "scope", "identity"}:
        assertion = candidate.assertions[0]
        value = json.loads(assertion.value)
        if mutation == "role":
            value["role"] = "forged-role"
        elif mutation == "alias":
            value["aliases"] = ["forged-alias"]
        elif mutation == "summary":
            value["summary"] = "forged-summary"
        elif mutation == "qualification":
            value["dm_kind"] = "dnd5e:npc"
        update = {"value": json.dumps(value, sort_keys=True, separators=(",", ":"))}
        if mutation == "scope":
            update["campaign_scope"] = "other-campaign"
        elif mutation == "identity":
            from dungeonmind.contracts.identity import IdentityOutcome
            update["identity_resolution_outcome"] = IdentityOutcome.RESOLVED_EXISTING
        candidate = candidate.model_copy(update={"assertions": [assertion.model_copy(update=update)]})
    if mutation in {"endpoint", "reversal"}:
        edge = candidate.assertions[0]
        update = ({"object_object_id": "node:forged-target"} if mutation == "endpoint" else
                  {"subject_object_id": edge.object_object_id, "object_object_id": edge.subject_object_id})
        candidate = candidate.model_copy(update={"assertions": [edge.model_copy(update=update)]})
    if mutation == "scope":
        candidate = candidate.model_copy(update={"campaign_scope": "other-campaign"})
    review_campaign = "other-campaign" if mutation == "scope" else CAMPAIGN_ID
    proposals, verdicts = _build_identity_dispositions(candidate, verdict_states)
    assertion_verdicts = [ContributionAssertionVerdict(
        assertion_id=item.assertion_id, acceptance_state=AcceptanceState.ACCEPTED,
    ) for item in sorted(candidate.assertions, key=lambda item: item.assertion_id)]
    plan = ContributionPlanRef(
        source_plan_schema=WORLDBUILDING_SOURCE_PLAN_SCHEMA, source_plan_id=operation_id,
        source_plan_sha256=canonical_sha256({"operation_id": operation_id,
                                           "contribution_id": original.contribution_id}),
        source_input_sha256=canonical_sha256({"contribution_id": original.contribution_id}),
        preview_content_sha256=canonical_sha256({}),
        candidate_contribution_sha256=contribution_v3_payload_sha256(candidate),
        expected_parent_revision_id=parent_id, base_graph_schema="dm_union_graph_v6",
        base_graph_payload_sha256=parent.revision.graph_payload_sha256,
        semantic_profile=profile,
    )
    if mutation == "plan":
        plan = plan.model_copy(update={"source_input_sha256": "34" * 32})
    intent_fields = dict(
        operation_id=operation_id, world_id=CAMPAIGN_ID, campaign_id=review_campaign,
        plan_ref=plan, candidate_contribution=candidate, identity_proposals=proposals,
        identity_verdicts=verdicts, assertion_verdicts=assertion_verdicts,
        reviewer_id="original-actor", reviewed_at=review_time,
    )
    digest = derive_review_intent_sha256_v3(**intent_fields)
    intent = ContributionReviewIntentV3(**intent_fields, review_intent_sha256=digest)
    confirmation = CommitConfirmationReceiptV3(
        confirmation_id=derive_confirmation_id(operation_id=operation_id,
            review_intent_sha256=digest, actor="original-actor", confirmed_at=review_time),
        operation_id=operation_id, review_intent_sha256=digest, actor="original-actor",
        world_id=CAMPAIGN_ID, campaign_id=review_campaign,
        expected_parent_revision_id=parent_id, confirmed_at=review_time,
    )
    state = _build_review_state(ContributionReviewSubmissionV3(intent=intent, confirmation=confirmation))
    # Revalidate complete Core contracts: the negative cases are internally
    # consistent alternate histories, rather than broken payload hashes.
    state = type(state).model_validate(state.model_dump(mode="json"))
    history = SimpleNamespace(review=state, publication=SimpleNamespace(
        graph_schema="dm_union_graph_v6", expected_parent_revision_id=parent_id,
        parent_graph_payload_sha256=parent.revision.graph_payload_sha256,
        published_at=review_time, published_revision_id="rev:original-child",
        reviewed_contribution_id=state.reviewed_contribution.contribution_id,
        reviewed_contribution_sha256=state.record.reviewed_contribution_sha256,
    ), revision=SimpleNamespace(created_at=review_time))
    return dict(original=original, history=history, parent=parent,
                operation_id=operation_id, expected_parent_id=parent_id,
                admitted_revision_id="rev:admitted", actor="original-actor")


@pytest.mark.parametrize("recipe", ["object", "edge", "alias"])
def test_historical_manual_complete_correspondence_matches_real_producer(recipe):
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import verify_review_correspondence
    verify_review_correspondence(**_coherent_historical_manual_review(recipe=recipe))


@pytest.mark.parametrize("mutation", ["role", "alias", "summary", "qualification", "scope", "identity", "plan", "timestamp"])
def test_historical_manual_complete_correspondence_rejects_valid_alternate_core_history(mutation):
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import verify_review_correspondence
    with pytest.raises(GraphObjectAuthoringError) as error:
        verify_review_correspondence(**_coherent_historical_manual_review(mutation=mutation))
    assert error.value.code == "authority_integrity"


@pytest.mark.parametrize("mutation", ["missing", "foreign", "changed_hash", "changed_time", "admitted_revision"])
def test_historical_manual_complete_correspondence_rejects_parent_or_admission_drift(mutation):
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import verify_review_correspondence
    kwargs = _coherent_historical_manual_review()
    if mutation == "missing":
        kwargs["parent"] = None
    elif mutation == "foreign":
        kwargs["parent"].revision.world_id = "foreign-world"
    elif mutation == "changed_hash":
        kwargs["parent"].graph_payload["extra"] = "changed"
    elif mutation == "changed_time":
        kwargs["parent"].revision.created_at += timedelta(seconds=1)
    else:
        kwargs["admitted_revision_id"] = "rev:foreign"
    with pytest.raises(GraphObjectAuthoringError) as error:
        verify_review_correspondence(**kwargs)
    assert error.value.code == "authority_integrity"



def _signed_historical_manual_request(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        build_assertions_from_proposals, contribution_binding_digest, proposed_assertions_digest,
    )
    from apps.live_control_server.integrations.dungeonmind import historical_manual_recovery as recovery
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import graph_review_authority_operation_id

    fixture = _coherent_historical_manual_review()
    original = fixture["original"]
    assertions, _ = build_assertions_from_proposals(prepare_request())
    operation = graph_review_authority_operation_id(
        world_id=CAMPAIGN_ID, campaign_id=CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL,
        source_artifact_id="art:original", source_revision_id="rev:admitted",
        sealed_proposal_digest=proposed_assertions_digest(assertions),
        expected_parent_revision_id=fixture["expected_parent_id"],
    )
    intent = dict(
        campaign_id=CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL, source_run_id="run-c1s2",
        document_source=None, recap_artifact_id=None, world_id=CAMPAIGN_ID,
        actor="original-actor", assertions_digest=proposed_assertions_digest(assertions),
        expected_parent_revision_id=fixture["expected_parent_id"], authority_operation_id=operation,
        source_artifact_id="art:original", source_revision_id="rev:admitted",
        contribution_digest=contribution_binding_digest(original), publication_binding=None,
        expires_at="2000-01-01T00:00:00+00:00",
    )
    request = _commit_request_from_prepare(SimpleNamespace(
        confirm_token=sign_publication_intent(intent), current_overlay_token=None,
    ))
    calls = []
    def read(world, operation, *, reader):
        calls.append(("terminal", world, operation))
        assert operation == fixture["operation_id"]
        return fixture["history"]
    def parent(world, revision):
        calls.append(("parent", world, revision))
        assert revision == fixture["expected_parent_id"]
        return fixture["parent"]
    monkeypatch.setattr(recovery, "_bare_readers", lambda: (object(), SimpleNamespace(get_revision=parent)))
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", read)
    return request, fixture, calls


def test_historical_manual_service_recovers_expired_packet_before_mutable_preflight(monkeypatch):
    request, fixture, calls = _signed_historical_manual_request(monkeypatch)
    for name in ("resolve_graph_review_source", "verify_graph_review_assertion_spans", "prove_graph_review_source"):
        monkeypatch.setattr(
            f"apps.live_control_server.services.graph_object_authoring_commit.{name}",
            lambda *a, **k: pytest.fail("recovery entered mutable source preflight"),
        )
    monkeypatch.setattr(
        "apps.live_control_server.ports.world_graph_authority_access.get_world_graph_authority",
        lambda: pytest.fail("recovery bootstrapped current graph services"),
    )
    authorization = []
    response = commit_graph_object_authoring_write(
        request, authenticated_actor="original-actor", recovery_only=True,
        authorize_world=lambda: authorization.append("owner"),
    )
    assert response.result == response.idempotency_status == "already_applied"
    assert response.published_revision_id == "rev:original-child"
    assert response.parent_revision_id == fixture["expected_parent_id"]
    assert len(response.created_node_ids) == 1
    assert [item[0] for item in calls] == ["terminal", "parent"]
    assert authorization == ["owner", "owner"]


@pytest.mark.parametrize("outcome,code,status", [
    ("absent", "publication_receipt_unavailable", 409),
    ("integrity", "authority_integrity", 500),
    ("unavailable", "authority_unavailable", 503),
])
def test_historical_manual_service_preserves_terminal_failure_classes(monkeypatch, outcome, code, status):
    from dungeonmind.domain.errors import PersistenceIntegrityError, PersistenceUnavailableError
    request, _, calls = _signed_historical_manual_request(monkeypatch)
    def terminal(*args, **kwargs):
        if outcome == "absent":
            return None
        if outcome == "integrity":
            raise PersistenceIntegrityError("corrupt terminal")
        raise PersistenceUnavailableError("offline terminal")
    monkeypatch.setattr("dungeonmind.application.compatibility.read_historical_finalized_publication", terminal)
    with pytest.raises(GraphObjectAuthoringError) as error:
        commit_graph_object_authoring_write(request, authenticated_actor="original-actor", recovery_only=True)
    assert (error.value.code, error.value.status_code) == (code, status)
    assert calls == []


@pytest.mark.parametrize("mutation", ["endpoint", "reversal"])
def test_historical_manual_complete_correspondence_rejects_valid_alternate_edge(mutation):
    from apps.live_control_server.integrations.dungeonmind.historical_manual_recovery import verify_review_correspondence
    with pytest.raises(GraphObjectAuthoringError) as error:
        verify_review_correspondence(**_coherent_historical_manual_review(recipe="edge", mutation=mutation))
    assert error.value.code == "authority_integrity"



@pytest.mark.parametrize("failure,code,status", [
    ("missing", "authority_integrity", 500),
    ("malformed", "authority_integrity", 500),
    ("invalid", "authority_integrity", 500),
    ("unavailable", "authority_unavailable", 503),
])
def test_historical_manual_service_parent_read_failure_is_typed(monkeypatch, failure, code, status):
    from types import SimpleNamespace
    from dungeonmind.domain.errors import PersistenceUnavailableError
    from apps.live_control_server.integrations.dungeonmind import historical_manual_recovery as recovery
    request, _, calls = _signed_historical_manual_request(monkeypatch)
    def parent(*args):
        if failure == "missing":
            return None
        if failure == "malformed":
            raise TypeError("stored JSON is null")
        if failure == "invalid":
            raise ValueError("invalid parent envelope")
        raise PersistenceUnavailableError("parent store offline")
    monkeypatch.setattr(recovery, "_bare_readers", lambda: (object(), SimpleNamespace(get_revision=parent)))
    with pytest.raises(GraphObjectAuthoringError) as error:
        commit_graph_object_authoring_write(request, authenticated_actor="original-actor", recovery_only=True)
    assert (error.value.code, error.value.status_code) == (code, status)
    assert [item[0] for item in calls] == ["terminal"]
