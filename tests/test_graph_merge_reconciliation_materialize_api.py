"""Tests for graph merge reconciliation materialize prepare/apply API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from apps.live_control_server.services.graph_merge_reconciliation_materialize import (
    GraphMergeReconciliationApplyRequest,
    GraphMergeReconciliationMaterializeError,
    GraphMergeReconciliationPrepareRequest,
    apply_graph_merge_reconciliation_materialization,
    prepare_graph_merge_reconciliation_materialization,
    union_store_file_token,
)
from graph_memory.union_supergraph.load import load_union_supergraph_store, write_union_supergraph_store
from graph_memory.union_supergraph.redirects import active_identity_redirect_map
from tests.test_a10m_lysandra_durable_identity_dogfood import (
    MERGED_AWAY_NODE_ID,
    SURVIVOR_NODE_ID,
    _lysandra_overlay,
    _lysandra_pre_reconciliation_store,
)
from tests.test_graph_memory_merge_reconciliation_planner import (
    CAMPAIGN_ID,
    overlay_with_assertions,
)

TEST_CAMPAIGN_REL = "Test Campaign/A10o"
SESSION_ID = "session-23"


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path | GraphAuthoringOverlayStore]:
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

    overlay_store = GraphAuthoringOverlayStore(corpus_root)
    overlay_store.save_overlay(_lysandra_overlay(), campaign_rel=TEST_CAMPAIGN_REL)

    return {
        "root": root,
        "corpus_root": corpus_root,
        "union_store_path": union_store_path,
        "overlay_store": overlay_store,
    }


def _prepare_request(workspace: dict, **overrides) -> GraphMergeReconciliationPrepareRequest:
    payload = {
        "campaignId": CAMPAIGN_ID,
        "campaignRel": TEST_CAMPAIGN_REL,
        "sessionId": SESSION_ID,
        "previewUnionStorePath": str(workspace["union_store_path"]),
    }
    payload.update(overrides)
    return GraphMergeReconciliationPrepareRequest.model_validate(payload)


def _apply_request(prepare_response, **overrides) -> GraphMergeReconciliationApplyRequest:
    payload = {
        "campaignId": CAMPAIGN_ID,
        "campaignRel": TEST_CAMPAIGN_REL,
        "sessionId": SESSION_ID,
        "previewUnionStorePath": prepare_response.union_store_path,
        "materializationPassId": prepare_response.materialization_pass_id,
        "confirmToken": prepare_response.confirm_token,
        "overlayToken": prepare_response.overlay_token,
        "unionStoreToken": prepare_response.union_store_token,
    }
    payload.update(overrides)
    return GraphMergeReconciliationApplyRequest.model_validate(payload)


def test_prepare_writes_nothing(workspace: dict) -> None:
    union_store_path = workspace["union_store_path"]
    assert isinstance(union_store_path, Path)
    before_bytes = union_store_path.read_bytes()
    before_mtime = union_store_path.stat().st_mtime

    response = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )

    assert response.prepared is True
    assert union_store_path.read_bytes() == before_bytes
    assert union_store_path.stat().st_mtime == before_mtime
    assert response.summary.applicable_assertion_count == 1


def test_prepare_returns_plan_summary_for_merge_overlay(workspace: dict) -> None:
    response = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )

    assert response.summary.merge_assertion_count == 1
    assert response.summary.applicable_assertion_count == 1
    assert response.summary.redirect_count == 1
    assert response.summary.edge_rewire_count == 1
    assert response.confirm_token
    assert response.plan_digest
    assert any(item.code == "merge_plan_created" for item in response.diagnostics)


def test_prepare_returns_no_applicable_plan_without_merge_assertions(workspace: dict) -> None:
    overlay_store = workspace["overlay_store"]
    assert isinstance(overlay_store, GraphAuthoringOverlayStore)
    overlay_store.save_overlay(
        overlay_with_assertions(),
        campaign_rel=TEST_CAMPAIGN_REL,
    )

    response = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )

    assert response.summary.merge_assertion_count == 0
    assert response.summary.applicable_assertion_count == 0


def test_apply_requires_matching_confirm_token(workspace: dict) -> None:
    prepare = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    request = _apply_request(prepare, confirmToken="bad-token")

    with pytest.raises(GraphMergeReconciliationMaterializeError) as exc:
        apply_graph_merge_reconciliation_materialization(
            request,
            corpus_root=workspace["corpus_root"],
            repo_root_override=workspace["root"],
        )
    assert exc.value.code == "confirm_token_mismatch"
    assert exc.value.status_code == 409


def test_apply_rejects_stale_union_store_token(workspace: dict) -> None:
    prepare = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    union_store_path = workspace["union_store_path"]
    assert isinstance(union_store_path, Path)
    union_store_path.write_text('{"tampered": true}', encoding="utf-8")

    request = _apply_request(prepare)

    with pytest.raises(GraphMergeReconciliationMaterializeError) as exc:
        apply_graph_merge_reconciliation_materialization(
            request,
            corpus_root=workspace["corpus_root"],
            repo_root_override=workspace["root"],
        )
    assert exc.value.code == "stale_union_store"
    assert exc.value.status_code == 409


def test_apply_rejects_stale_overlay_token(workspace: dict) -> None:
    prepare = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    overlay_store = workspace["overlay_store"]
    assert isinstance(overlay_store, GraphAuthoringOverlayStore)
    overlay_path = overlay_store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    overlay_path.write_text('{"tampered": true}', encoding="utf-8")

    request = _apply_request(prepare)

    with pytest.raises(GraphMergeReconciliationMaterializeError) as exc:
        apply_graph_merge_reconciliation_materialization(
            request,
            corpus_root=workspace["corpus_root"],
            repo_root_override=workspace["root"],
        )
    assert exc.value.code == "stale_overlay"
    assert exc.value.status_code == 409


def test_apply_writes_backup_and_updated_union_store(workspace: dict) -> None:
    prepare = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    union_store_path = workspace["union_store_path"]
    assert isinstance(union_store_path, Path)
    before_token = union_store_file_token(union_store_path, campaign_id=CAMPAIGN_ID)

    response = apply_graph_merge_reconciliation_materialization(
        _apply_request(prepare),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )

    assert response.applied is True
    assert response.backup_path
    assert Path(response.backup_path).is_file()
    assert union_store_file_token(union_store_path, campaign_id=CAMPAIGN_ID) != before_token

    applied_store = load_union_supergraph_store(union_store_path)
    redirect_map = active_identity_redirect_map(applied_store.identity_redirects)
    assert MERGED_AWAY_NODE_ID in redirect_map
    assert redirect_map[MERGED_AWAY_NODE_ID].to_node_id == SURVIVOR_NODE_ID
    assert response.summary.redirects_added == 1


def test_apply_is_idempotent_for_already_applied_assertions(workspace: dict) -> None:
    prepare = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    first = apply_graph_merge_reconciliation_materialization(
        _apply_request(prepare),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    assert first.applied_assertion_ids

    second_prepare = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    second = apply_graph_merge_reconciliation_materialization(
        _apply_request(second_prepare),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )
    assert second.applied is True
    assert first.applied_assertion_ids[0] in second.skipped_assertion_ids
    assert not second.applied_assertion_ids


def test_path_escaping_is_rejected(workspace: dict) -> None:
    request = _prepare_request(workspace, previewUnionStorePath="../../../etc/passwd")

    with pytest.raises(GraphMergeReconciliationMaterializeError) as exc:
        prepare_graph_merge_reconciliation_materialization(
            request,
            corpus_root=workspace["corpus_root"],
            repo_root_override=workspace["root"],
        )
    assert exc.value.code == "unsafe_union_store_path"


def test_response_diagnostics_include_planner_shape(workspace: dict) -> None:
    response = prepare_graph_merge_reconciliation_materialization(
        _prepare_request(workspace),
        corpus_root=workspace["corpus_root"],
        repo_root_override=workspace["root"],
    )

    assert response.diagnostics
    first = response.diagnostics[0]
    assert first.code
    assert first.message
    assert first.severity in {"info", "warning", "error"}
    dumped = json.loads(response.model_dump_json())
    assert dumped["summary"]["applicable_assertion_count"] == 1
