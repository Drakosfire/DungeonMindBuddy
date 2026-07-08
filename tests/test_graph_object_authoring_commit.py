"""Tests for graph object authoring commit service."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.live_control_server.services.graph_authoring_event_log import GraphAuthoringEventLogError
from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from apps.live_control_server.services.graph_object_authoring_commit import (
    commit_graph_object_authoring_write,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringError,
    overlay_file_token,
    prepare_graph_object_authoring_write,
)
from tests.test_graph_object_authoring_prepare import (
    CAMPAIGN_ID,
    TEST_CAMPAIGN_REL,
    link_existing_proposal,
    object_proposal,
    prepare_request,
    relationship_proposal,
)


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    campaign_dir = root / TEST_CAMPAIGN_REL
    campaign_dir.mkdir(parents=True)
    # Sentinel paths that must not be touched.
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
    source_run_id: str | None = None,
    source_graph_id: str | None = None,
    preview_union_store_path: str | None = None,
    campaign_id: str = CAMPAIGN_ID,
) -> GraphObjectAuthoringCommitRequest:
    payload: dict[str, object] = {
        "campaignId": campaign_id,
        "campaignRel": TEST_CAMPAIGN_REL,
        "sessionId": "session-2",
        "proposals": proposals or [object_proposal()],
        "confirmToken": prepare_response.confirm_token,
        "currentOverlayToken": prepare_response.current_overlay_token,
    }
    if source_run_id is not None:
        payload["sourceRunId"] = source_run_id
    if source_graph_id is not None:
        payload["sourceGraphId"] = source_graph_id
    if preview_union_store_path is not None:
        payload["previewUnionStorePath"] = preview_union_store_path
    return GraphObjectAuthoringCommitRequest.model_validate(payload)


def _mtime(path: Path) -> float:
    return path.stat().st_mtime


def test_commit_with_matching_token_writes_overlay(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
    )
    assert response.committed is True
    overlay = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert len(overlay.assertions) == 1
    assert overlay.assertions[0].assertion_kind == "object"


def test_commit_appends_event_log(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(proposals=[object_proposal(), relationship_proposal()]),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare,
            proposals=[object_proposal(), relationship_proposal()],
        ),
        corpus_root=corpus_root,
    )
    events_path = store.events_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert events_path.is_file()
    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == response.event_count
    assert response.event_count == 3  # batch + 2 assertions


def test_commit_with_bad_token_fails(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    request = _commit_request_from_prepare(prepare)
    request = request.model_copy(update={"confirm_token": "deadbeef" * 8})
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(request, corpus_root=corpus_root)
    assert exc.value.code == "confirm_token_mismatch"


def test_commit_requires_source_run_id_when_prepare_included_it(
    store: GraphAuthoringOverlayStore,
    corpus_root: Path,
) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(sourceRunId="run-c1s2", sourceGraphId="graph-c1s2"),
        corpus_root=corpus_root,
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(
            _commit_request_from_prepare(prepare),
            corpus_root=corpus_root,
        )
    assert exc.value.code == "confirm_token_mismatch"

    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare,
            source_run_id="run-c1s2",
            source_graph_id="graph-c1s2",
        ),
        corpus_root=corpus_root,
    )
    assert response.committed is True


def test_commit_with_stale_overlay_token_fails(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    first_commit = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
    )
    assert first_commit.committed is True

    stale_request = GraphObjectAuthoringCommitRequest.model_validate(
        {
            "campaignId": CAMPAIGN_ID,
            "campaignRel": TEST_CAMPAIGN_REL,
            "sessionId": "session-2",
            "proposals": [object_proposal(localProposalId="local-object-2")],
            "confirmToken": prepare.confirm_token,
            "currentOverlayToken": prepare.current_overlay_token,
        }
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(stale_request, corpus_root=corpus_root)
    assert exc.value.code == "stale_overlay"


def test_commit_backs_up_existing_overlay(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare_one = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare_one),
        corpus_root=corpus_root,
    )

    prepare_two = prepare_graph_object_authoring_write(
        prepare_request(proposals=[link_existing_proposal()]),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare_two,
            proposals=[link_existing_proposal()],
        ),
        corpus_root=corpus_root,
    )
    assert response.backup_path is not None
    assert Path(response.backup_path).is_file()


def test_commit_rejects_invalid_object_ref(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    request = GraphObjectAuthoringCommitRequest.model_validate(
        {
            "campaignId": CAMPAIGN_ID,
            "campaignRel": TEST_CAMPAIGN_REL,
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
        commit_graph_object_authoring_write(request, corpus_root=corpus_root)
    assert exc.value.code == "invalid_proposal"


def test_commit_rejects_blank_relationship_type(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(proposals=[relationship_proposal()]),
        corpus_root=corpus_root,
    )
    request = GraphObjectAuthoringCommitRequest.model_validate(
        {
            "campaignId": CAMPAIGN_ID,
            "campaignRel": TEST_CAMPAIGN_REL,
            "proposals": [relationship_proposal(relationshipType="")],
            "confirmToken": prepare.confirm_token,
            "currentOverlayToken": prepare.current_overlay_token,
        }
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(request, corpus_root=corpus_root)
    assert exc.value.code == "invalid_relationship_type"


def test_commit_response_includes_no_mutation_guarantees(
    store: GraphAuthoringOverlayStore,
    corpus_root: Path,
) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
    )
    joined = " ".join(response.no_mutation_guarantees).lower()
    assert "source markdown" in joined
    assert "live run" in joined
    assert "graph gold" in joined


def test_commit_does_not_touch_source_markdown_live_artifact_or_gold(
    store: GraphAuthoringOverlayStore,
    corpus_root: Path,
) -> None:
    campaign_dir = corpus_root / TEST_CAMPAIGN_REL
    recap = campaign_dir / "Session Recaps" / "recap.md"
    gold = campaign_dir / "_graph_gold" / "candidate_graph_gold.json"
    manifest = campaign_dir / "_live_runs" / "run-1" / "manifest.json"
    mtimes = {path: _mtime(path) for path in (recap, gold, manifest)}

    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
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


def test_commit_rejects_unsafe_campaign_rel(store: GraphAuthoringOverlayStore, corpus_root: Path) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    request = _commit_request_from_prepare(prepare).model_copy(
        update={"campaign_rel": "../../../outside"},
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        commit_graph_object_authoring_write(request, corpus_root=corpus_root)
    assert exc.value.code == "unsafe_campaign_rel"


def test_commit_new_overlay_token_matches_written_file(
    store: GraphAuthoringOverlayStore,
    corpus_root: Path,
) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(prepare),
        corpus_root=corpus_root,
    )
    overlay_path = Path(response.overlay_path)
    assert response.new_overlay_token == overlay_file_token(
        overlay_path,
        campaign_id=CAMPAIGN_ID,
    )
    assert response.new_overlay_token != prepare.proposed_assertions_digest


def test_commit_event_log_failure_returns_partial_guarantees(
    store: GraphAuthoringOverlayStore,
    corpus_root: Path,
) -> None:
    prepare = prepare_graph_object_authoring_write(
        prepare_request(),
        corpus_root=corpus_root,
    )
    with patch(
        "apps.live_control_server.services.graph_object_authoring_commit.append_graph_authoring_events",
        side_effect=GraphAuthoringEventLogError("disk full"),
    ):
        response = commit_graph_object_authoring_write(
            _commit_request_from_prepare(prepare),
            corpus_root=corpus_root,
        )

    assert response.committed is False
    assert response.event_count == 0
    joined = " ".join(response.no_mutation_guarantees).lower()
    assert "partial commit" in joined
    assert "event log was not appended" in joined
    assert "committed authored graph memory" not in joined
    assert "appended authoring event log" not in joined

    overlay = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert len(overlay.assertions) == 1


def _lysandra_merge_proposal() -> dict[str, object]:
    from tests.test_graph_object_authoring_merge_prepare import merge_proposal
    from tests.test_a10m_lysandra_durable_identity_dogfood import (
        MERGED_AWAY_NODE_ID,
        SURVIVOR_NODE_ID,
    )

    return merge_proposal(
        survivorObjectRef={
            "refKind": "existing_graph_node",
            "nodeId": SURVIVOR_NODE_ID,
            "label": "Captain Lysandra Ironveil",
            "kind": "companion",
        },
        mergedObjectRefs=[
            {
                "refKind": "existing_graph_node",
                "nodeId": MERGED_AWAY_NODE_ID,
                "label": "Lysandra",
                "kind": "character",
            }
        ],
    )


@pytest.fixture
def merge_materialization_workspace(tmp_path: Path) -> dict[str, Path]:
    from graph_memory.union_supergraph.load import write_union_supergraph_store
    from tests.test_a10m_lysandra_durable_identity_dogfood import (
        _lysandra_pre_reconciliation_store,
    )

    root = tmp_path
    corpus_root = root / "corpus"
    campaign_dir = corpus_root / TEST_CAMPAIGN_REL
    campaign_dir.mkdir(parents=True)
    (campaign_dir / "Session Recaps").mkdir()
    (campaign_dir / "Session Recaps" / "recap.md").write_text("# recap\n", encoding="utf-8")

    store_dir = root / "stores"
    store_dir.mkdir()
    union_store_path = store_dir / "preview_union.json"
    write_union_supergraph_store(union_store_path, _lysandra_pre_reconciliation_store())

    return {
        "root": root,
        "corpus_root": corpus_root,
        "union_store_path": union_store_path,
    }


def test_commit_materializes_merge_when_preview_union_store_path_set(
    merge_materialization_workspace: dict[str, Path],
) -> None:
    from graph_memory.union_supergraph.load import load_union_supergraph_store
    from graph_memory.union_supergraph.redirects import (
        active_identity_redirect_map,
        resolve_union_node_id,
    )
    from tests.test_a10m_lysandra_durable_identity_dogfood import MERGED_AWAY_NODE_ID, SURVIVOR_NODE_ID
    from tests.test_graph_memory_merge_reconciliation_planner import CAMPAIGN_ID as MERGE_CAMPAIGN_ID

    corpus_root = merge_materialization_workspace["corpus_root"]
    root = merge_materialization_workspace["root"]
    union_store_path = merge_materialization_workspace["union_store_path"]
    merge_proposal_payload = _lysandra_merge_proposal()

    prepare = prepare_graph_object_authoring_write(
        prepare_request(proposals=[merge_proposal_payload], campaignId=MERGE_CAMPAIGN_ID),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare,
            proposals=[merge_proposal_payload],
            preview_union_store_path=str(union_store_path),
            campaign_id=MERGE_CAMPAIGN_ID,
        ),
        corpus_root=corpus_root,
        repo_root_override=root,
    )

    assert response.committed is True
    assert response.union_store_materialization is not None
    assert response.union_store_materialization.applied is True
    assert response.union_store_materialization.reason == "materialized"
    assert response.union_store_materialization.redirects_added == 1

    updated_store = load_union_supergraph_store(union_store_path)
    redirect_map = active_identity_redirect_map(updated_store.identity_redirects)
    assert (
        resolve_union_node_id(MERGED_AWAY_NODE_ID, redirect_map) == SURVIVOR_NODE_ID
    )


def test_commit_without_preview_union_store_path_skips_materialization(
    corpus_root: Path,
) -> None:
    merge_proposal_payload = _lysandra_merge_proposal()
    prepare = prepare_graph_object_authoring_write(
        prepare_request(proposals=[merge_proposal_payload]),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare,
            proposals=[merge_proposal_payload],
        ),
        corpus_root=corpus_root,
    )

    assert response.committed is True
    assert response.union_store_materialization is not None
    assert response.union_store_materialization.applied is False
    assert (
        response.union_store_materialization.reason
        == "no_preview_union_store_selected"
    )


def test_commit_after_merge_materialized_reports_no_actionable_assertions(
    merge_materialization_workspace: dict[str, Path],
) -> None:
    from tests.test_graph_memory_merge_reconciliation_planner import CAMPAIGN_ID as MERGE_CAMPAIGN_ID

    corpus_root = merge_materialization_workspace["corpus_root"]
    root = merge_materialization_workspace["root"]
    union_store_path = merge_materialization_workspace["union_store_path"]
    merge_proposal_payload = _lysandra_merge_proposal()

    prepare_merge = prepare_graph_object_authoring_write(
        prepare_request(proposals=[merge_proposal_payload], campaignId=MERGE_CAMPAIGN_ID),
        corpus_root=corpus_root,
    )
    commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare_merge,
            proposals=[merge_proposal_payload],
            preview_union_store_path=str(union_store_path),
            campaign_id=MERGE_CAMPAIGN_ID,
        ),
        corpus_root=corpus_root,
        repo_root_override=root,
    )

    prepare_object = prepare_graph_object_authoring_write(
        prepare_request(
            proposals=[object_proposal(localProposalId="local-object-2")],
            campaignId=MERGE_CAMPAIGN_ID,
        ),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare_object,
            proposals=[object_proposal(localProposalId="local-object-2")],
            preview_union_store_path=str(union_store_path),
            campaign_id=MERGE_CAMPAIGN_ID,
        ),
        corpus_root=corpus_root,
        repo_root_override=root,
    )

    assert response.committed is True
    assert response.union_store_materialization is not None
    assert response.union_store_materialization.applied is False
    assert (
        response.union_store_materialization.reason
        == "no_actionable_merge_assertions"
    )


def test_commit_materialization_failure_does_not_fail_commit(
    merge_materialization_workspace: dict[str, Path],
) -> None:
    from tests.test_graph_memory_merge_reconciliation_planner import CAMPAIGN_ID as MERGE_CAMPAIGN_ID

    corpus_root = merge_materialization_workspace["corpus_root"]
    root = merge_materialization_workspace["root"]
    merge_proposal_payload = _lysandra_merge_proposal()

    prepare = prepare_graph_object_authoring_write(
        prepare_request(proposals=[merge_proposal_payload], campaignId=MERGE_CAMPAIGN_ID),
        corpus_root=corpus_root,
    )
    response = commit_graph_object_authoring_write(
        _commit_request_from_prepare(
            prepare,
            proposals=[merge_proposal_payload],
            preview_union_store_path=str(root / "missing" / "preview_union.json"),
            campaign_id=MERGE_CAMPAIGN_ID,
        ),
        corpus_root=corpus_root,
        repo_root_override=root,
    )

    assert response.committed is True
    assert response.union_store_materialization is not None
    assert response.union_store_materialization.applied is False
    assert response.union_store_materialization.reason == "materialization_failed"
    assert any(
        item.code == "union_store_materialization_failed"
        for item in response.union_store_materialization.diagnostics
    )
