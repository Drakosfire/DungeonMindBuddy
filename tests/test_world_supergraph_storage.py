"""Tests for World SuperGraph storage + graph-head contract (PR002)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.world_supergraph import (
    WorldGraphStaleParentError,
    WorldGraphValidationError,
    build_world_graph_integrity_report,
    load_current_world_graph,
    load_world_graph_revision,
    open_world_graph_head,
    publish_world_graph_revision,
    rollback_world_graph_head,
)
from graph_memory.world_supergraph import paths as world_paths


WORLD_ID = "eldyrwild"


@pytest.fixture
def fixture_store() -> UnionSupergraphStore:
    return load_union_supergraph_store(DEFAULT_FIXTURE_PATH)


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    return tmp_path


def _mutated_label_store(store: UnionSupergraphStore) -> UnionSupergraphStore:
    payload = store.model_dump(mode="json", by_alias=True)
    payload = copy.deepcopy(payload)
    # Small safe change that still validates.
    first_node_id = next(iter(payload["nodes"]))
    payload["nodes"][first_node_id]["label"] = (
        payload["nodes"][first_node_id]["label"] + " (rev2)"
    )
    return parse_union_supergraph_store(payload)


def _invalid_missing_evidence_store(store: UnionSupergraphStore) -> UnionSupergraphStore:
    payload = store.model_dump(mode="json", by_alias=True)
    payload = copy.deepcopy(payload)
    first_node_id = next(iter(payload["nodes"]))
    payload["nodes"][first_node_id]["evidence_ref_ids"].append("missing:evidence")
    return parse_union_supergraph_store(payload)


def test_publish_initial_revision_creates_head(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    result = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:fixture-seed"],
    )

    head_file = world_paths.head_path(store_root, WORLD_ID)
    assert head_file.is_file()

    head = open_world_graph_head(store_root, WORLD_ID)
    assert head.world_id == WORLD_ID
    assert head.head_revision_id == result.revision.revision_id
    assert result.head.head_revision_id == result.revision.revision_id

    assert world_paths.revision_manifest_path(
        store_root, WORLD_ID, result.revision.revision_id
    ).is_file()
    assert world_paths.graph_payload_path(
        store_root, WORLD_ID, result.revision.revision_id
    ).is_file()

    loaded_head, loaded_revision, loaded_store = load_current_world_graph(
        store_root, WORLD_ID
    )
    assert loaded_head.head_revision_id == result.revision.revision_id
    assert loaded_revision.revision_id == result.revision.revision_id
    assert loaded_revision.parent_revision_id is None
    assert loaded_store.campaign_id == "longmont-c2"
    assert "worldbuilding" in loaded_store.source_domains
    assert "recap" in loaded_store.source_domains


def test_publish_second_revision_records_parent(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    first = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:a"],
    )
    first_graph_path = world_paths.graph_payload_path(
        store_root, WORLD_ID, first.revision.revision_id
    )
    first_bytes = first_graph_path.read_bytes()

    second_store = _mutated_label_store(fixture_store)
    second = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        second_store,
        operation_ids=["op:b"],
        expected_parent_revision_id=first.revision.revision_id,
    )

    assert second.revision.parent_revision_id == first.revision.revision_id
    head = open_world_graph_head(store_root, WORLD_ID)
    assert head.head_revision_id == second.revision.revision_id

    assert first_graph_path.is_file()
    assert first_graph_path.read_bytes() == first_bytes

    # First revision still loadable and unchanged.
    first_loaded = load_world_graph_revision(
        store_root, WORLD_ID, first.revision.revision_id
    )
    assert first_loaded.model_dump(mode="json", by_alias=True) == fixture_store.model_dump(
        mode="json", by_alias=True
    )


def test_failed_validation_leaves_prior_head_readable(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    first = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:valid"],
    )
    invalid = _invalid_missing_evidence_store(fixture_store)

    with pytest.raises(WorldGraphValidationError, match="missing:evidence"):
        publish_world_graph_revision(
            store_root,
            WORLD_ID,
            invalid,
            operation_ids=["op:invalid"],
            expected_parent_revision_id=first.revision.revision_id,
        )

    head = open_world_graph_head(store_root, WORLD_ID)
    assert head.head_revision_id == first.revision.revision_id
    _, _, loaded = load_current_world_graph(store_root, WORLD_ID)
    assert loaded.campaign_id == fixture_store.campaign_id


def test_stale_parent_publish_rejected(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    first = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:a"],
    )
    with pytest.raises(WorldGraphStaleParentError, match="stale parent"):
        publish_world_graph_revision(
            store_root,
            WORLD_ID,
            _mutated_label_store(fixture_store),
            operation_ids=["op:b"],
            expected_parent_revision_id="wrong",
        )

    head = open_world_graph_head(store_root, WORLD_ID)
    assert head.head_revision_id == first.revision.revision_id


def test_rollback_repoints_head_to_existing_revision(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    first = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:a"],
    )
    second = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        _mutated_label_store(fixture_store),
        operation_ids=["op:b"],
        expected_parent_revision_id=first.revision.revision_id,
    )

    rolled = rollback_world_graph_head(
        store_root, WORLD_ID, first.revision.revision_id
    )
    assert rolled.head_revision_id == first.revision.revision_id

    assert world_paths.revision_dir(
        store_root, WORLD_ID, second.revision.revision_id
    ).is_dir()

    head, revision, store = load_current_world_graph(store_root, WORLD_ID)
    assert head.head_revision_id == first.revision.revision_id
    assert revision.revision_id == first.revision.revision_id
    assert store.model_dump(mode="json", by_alias=True) == fixture_store.model_dump(
        mode="json", by_alias=True
    )


def test_integrity_report_contains_head_parent_and_validation_status(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    published = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:seed"],
    )
    report = build_world_graph_integrity_report(store_root, WORLD_ID)

    assert report.load_ok is True
    assert report.validation_ok is True
    assert report.head_revision_id == published.revision.revision_id
    assert report.parent_revision_id is None
    assert report.revision_count >= 1
    assert report.errors == []
    assert world_paths.integrity_latest_path(store_root, WORLD_ID).is_file()

    second = publish_world_graph_revision(
        store_root,
        WORLD_ID,
        _mutated_label_store(fixture_store),
        operation_ids=["op:second"],
        expected_parent_revision_id=published.revision.revision_id,
    )
    report2 = build_world_graph_integrity_report(store_root, WORLD_ID)
    assert report2.head_revision_id == second.revision.revision_id
    assert report2.parent_revision_id == published.revision.revision_id
    assert report2.revision_count >= 2


def test_world_store_does_not_require_latest_ingest_or_preview_path(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    publish_world_graph_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:seed"],
    )
    # Only root + world_id — no preview source, ingest run, session, manifest, or store path.
    head, revision, store = load_current_world_graph(store_root, WORLD_ID)
    assert head.world_id == WORLD_ID
    assert revision.world_id == WORLD_ID
    assert store.focus_session_id == "session-23"

    # Prove the on-disk layout is world/revision based, not preview-run based.
    layout = json.loads(world_paths.head_path(store_root, WORLD_ID).read_text())
    assert set(layout.keys()) == {"world_id", "head_revision_id", "updated_at"}
    assert "preview" not in json.dumps(layout).lower()
    assert "ingest" not in json.dumps(layout).lower()
