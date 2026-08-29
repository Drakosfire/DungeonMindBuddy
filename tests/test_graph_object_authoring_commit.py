"""Tests for Graph Review confirmation through DungeonMind authority."""

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
    publication_intent_payload,
    sign_publication_intent,
)
from tests.test_graph_object_authoring_prepare import (
    CAMPAIGN_ID,
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
    SOURCE_ARTIFACT_ID,
    SOURCE_REVISION_ID,
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
    fake = FakeSourceAdmission()
    monkeypatch.setattr(
        "apps.live_control_server.ports.world_graph_source_admission_access.get_world_graph_source_admission_authority",
        lambda: fake,
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
    with (
        patch(
            "apps.live_control_server.services.graph_authoring_overlay_store.GraphAuthoringOverlayStore.append_assertions",
            side_effect=AssertionError("overlay append invoked"),
        ),
        patch(
            "graph_memory.union_supergraph.load.write_union_supergraph_store",
            side_effect=AssertionError("union store write invoked"),
        ),
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
    expired = publication_intent_payload(
        world_id=CAMPAIGN_ID,
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        source_run_id="run-c1s2",
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_revision_id=SOURCE_REVISION_ID,
        expected_parent_revision_id=prepare.expected_parent_revision_id,
        authority_operation_id=prepare.authority_operation_id,
        expressibility="EXPRESSIBLE",
        actor=prepare.actor or "",
        assertions_digest=prepare.proposed_assertions_digest,
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    )
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
