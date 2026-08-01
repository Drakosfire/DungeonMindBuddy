"""Tests for exact operation-to-revision lookup (SBW09c2a)."""

# PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION:
# Kernel operation-revision lookup tests; may import world_supergraph.paths
# for orphan revision fixtures and world-root snapshot helpers.

from __future__ import annotations

import copy
import json
from pathlib import Path

import graph_memory.kernel as kernel
import pytest
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore
from graph_memory.world_supergraph import WorldGraphIntegrityError, WorldGraphNotFoundError
from graph_memory.world_supergraph import paths as world_paths

WORLD_ID = "eldyrwild"


@pytest.fixture
def fixture_store() -> UnionSupergraphStore:
    return load_union_supergraph_store(DEFAULT_FIXTURE_PATH)


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    return tmp_path


def _mutated_label_store(
    store: UnionSupergraphStore, *, suffix: str = " (rev2)"
) -> UnionSupergraphStore:
    payload = store.model_dump(mode="json", by_alias=True)
    payload = copy.deepcopy(payload)
    first_node_id = next(iter(payload["nodes"]))
    payload["nodes"][first_node_id]["label"] = (
        payload["nodes"][first_node_id]["label"] + suffix
    )
    return parse_union_supergraph_store(payload)


def _snapshot_world_root(root: Path, world_id: str) -> dict[Path, tuple[bytes, float]]:
    world_dir = world_paths.world_dir(root, world_id)
    if not world_dir.is_dir():
        return {}
    snapshot: dict[Path, tuple[bytes, float]] = {}
    for path in sorted(world_dir.rglob("*")):
        if path.is_file():
            stat = path.stat()
            snapshot[path] = (path.read_bytes(), stat.st_mtime_ns)
    return snapshot


def _assert_world_root_unchanged(
    before: dict[Path, tuple[bytes, float]],
    after: dict[Path, tuple[bytes, float]],
) -> None:
    assert set(before.keys()) == set(after.keys())
    for path, (before_bytes, before_mtime) in before.items():
        after_bytes, after_mtime = after[path]
        assert before_bytes == after_bytes, f"bytes changed: {path}"
        assert before_mtime == after_mtime, f"mtime changed: {path}"


def test_lookup_empty_store_returns_empty_tuple(store_root: Path) -> None:
    assert (
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, "op:missing"
        )
        == ()
    )


def test_lookup_no_matching_operation_id_returns_empty_tuple(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:baseline"],
    )
    assert (
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, "op:other"
        )
        == ()
    )


def test_lookup_one_exact_match_returns_typed_manifest(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    published = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:unique-match"],
    )
    matches = kernel.find_world_graph_revisions_by_operation_id(
        store_root, WORLD_ID, "op:unique-match"
    )
    assert len(matches) == 1
    assert matches[0].revision_id == published.revision.revision_id
    assert matches[0].operation_ids == ["op:unique-match"]
    assert matches[0].world_id == WORLD_ID


def test_lookup_rejects_blank_operation_id(store_root: Path) -> None:
    with pytest.raises(ValueError, match="operation_id must be non-empty"):
        kernel.find_world_graph_revisions_by_operation_id(store_root, WORLD_ID, "")
    with pytest.raises(ValueError, match="operation_id must be non-empty"):
        kernel.find_world_graph_revisions_by_operation_id(store_root, WORLD_ID, "   ")


def test_lookup_prefix_and_case_variation_do_not_match(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:Exact-ID"],
    )
    assert (
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, "op:exact-id"
        )
        == ()
    )
    assert (
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, "op:Exact"
        )
        == ()
    )
    assert (
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, "Exact-ID"
        )
        == ()
    )


def test_lookup_finds_revision_behind_newer_head(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    first = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:behind-head"],
    )
    kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        _mutated_label_store(fixture_store),
        operation_ids=["op:newer-head"],
        expected_parent_revision_id=first.revision.revision_id,
    )
    head = kernel.open_world_graph_head(store_root, WORLD_ID)
    assert head.head_revision_id != first.revision.revision_id

    matches = kernel.find_world_graph_revisions_by_operation_id(
        store_root, WORLD_ID, "op:behind-head"
    )
    assert len(matches) == 1
    assert matches[0].revision_id == first.revision.revision_id


def test_lookup_finds_revision_after_head_rollback(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    first = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:rollback-target"],
    )
    second = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        _mutated_label_store(fixture_store),
        operation_ids=["op:rolled-away"],
        expected_parent_revision_id=first.revision.revision_id,
    )
    kernel.rollback_world_graph_head(store_root, WORLD_ID, first.revision.revision_id)
    head = kernel.open_world_graph_head(store_root, WORLD_ID)
    assert head.head_revision_id == first.revision.revision_id

    matches = kernel.find_world_graph_revisions_by_operation_id(
        store_root, WORLD_ID, "op:rolled-away"
    )
    assert len(matches) == 1
    assert matches[0].revision_id == second.revision.revision_id


def test_lookup_returns_all_duplicate_operation_id_matches_in_order(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    shared_op = "op:shared-publication"
    first = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=[shared_op],
    )
    second = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        _mutated_label_store(fixture_store, suffix=" (dup)"),
        operation_ids=[shared_op],
        expected_parent_revision_id=first.revision.revision_id,
    )

    matches = kernel.find_world_graph_revisions_by_operation_id(
        store_root, WORLD_ID, shared_op
    )
    assert len(matches) == 2
    assert [m.revision_id for m in matches] == [
        first.revision.revision_id,
        second.revision.revision_id,
    ]
    assert matches[0].created_at <= matches[1].created_at


def test_lookup_fails_closed_on_missing_enumerated_manifest(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    good = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:good"],
    )
    orphan_id = "rev:0000000000000001"
    orphan_dir = world_paths.revision_dir(store_root, WORLD_ID, orphan_id)
    orphan_dir.mkdir(parents=True)

    with pytest.raises(WorldGraphNotFoundError, match="revision manifest missing"):
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, "op:good"
        )

    # Good revision still exists on disk; lookup must not return partial success.
    assert good.revision.revision_id.startswith("rev:")


def test_lookup_fails_closed_on_malformed_enumerated_manifest(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:valid"],
    )
    bad_id = "rev:0000000000000002"
    bad_dir = world_paths.revision_dir(store_root, WORLD_ID, bad_id)
    bad_dir.mkdir(parents=True)
    manifest_path = world_paths.revision_manifest_path(store_root, WORLD_ID, bad_id)
    manifest_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, "op:valid"
        )


def test_lookup_fails_closed_on_world_id_identity_mismatch(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    search_op = "op:identity-tamper-world"
    published = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=[search_op],
    )
    manifest_path = world_paths.revision_manifest_path(
        store_root, WORLD_ID, published.revision.revision_id
    )
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert search_op in manifest_data["operation_ids"]
    manifest_data["world_id"] = "otherworld"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(WorldGraphIntegrityError, match="manifest identity mismatch"):
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, search_op
        )


def test_lookup_fails_closed_on_revision_id_identity_mismatch(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    search_op = "op:identity-tamper-revision"
    published = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=[search_op],
    )
    manifest_path = world_paths.revision_manifest_path(
        store_root, WORLD_ID, published.revision.revision_id
    )
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert search_op in manifest_data["operation_ids"]
    claimed_revision_id = "rev:0000000000000003"
    assert claimed_revision_id != published.revision.revision_id
    manifest_data["revision_id"] = claimed_revision_id
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(WorldGraphIntegrityError, match="manifest identity mismatch"):
        kernel.find_world_graph_revisions_by_operation_id(
            store_root, WORLD_ID, search_op
        )


def test_lookup_uses_fixed_enumeration_snapshot(
    store_root: Path,
    fixture_store: UnionSupergraphStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import graph_memory.kernel.world_graph as world_graph_module

    baseline = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:snapshot-baseline"],
    )
    snapshot_ids = list(world_graph_module.list_revision_ids(store_root, WORLD_ID))
    real_list_revision_ids = world_graph_module.list_revision_ids
    frozen_calls_remaining = [1]

    def _snapshot_aware_list_revision_ids(root: Path, world_id: str) -> list[str]:
        if frozen_calls_remaining[0] > 0:
            frozen_calls_remaining[0] -= 1
            return list(snapshot_ids)
        return real_list_revision_ids(root, world_id)

    monkeypatch.setattr(
        world_graph_module, "list_revision_ids", _snapshot_aware_list_revision_ids
    )

    concurrent = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        _mutated_label_store(fixture_store),
        operation_ids=["op:snapshot-concurrent"],
        expected_parent_revision_id=baseline.revision.revision_id,
    )

    first_lookup = kernel.find_world_graph_revisions_by_operation_id(
        store_root, WORLD_ID, "op:snapshot-concurrent"
    )
    assert first_lookup == ()

    second_lookup = kernel.find_world_graph_revisions_by_operation_id(
        store_root, WORLD_ID, "op:snapshot-concurrent"
    )
    assert len(second_lookup) == 1
    assert second_lookup[0].revision_id == concurrent.revision.revision_id


def test_lookup_is_read_only(
    store_root: Path, fixture_store: UnionSupergraphStore
) -> None:
    published = kernel.publish_world_revision(
        store_root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:read-only-proof"],
    )
    before = _snapshot_world_root(store_root, WORLD_ID)
    head_before = kernel.open_world_graph_head(store_root, WORLD_ID)

    matches = kernel.find_world_graph_revisions_by_operation_id(
        store_root, WORLD_ID, "op:read-only-proof"
    )
    assert len(matches) == 1

    after = _snapshot_world_root(store_root, WORLD_ID)
    head_after = kernel.open_world_graph_head(store_root, WORLD_ID)

    _assert_world_root_unchanged(before, after)
    assert head_before.model_dump() == head_after.model_dump()
    assert head_after.head_revision_id == published.revision.revision_id


def test_lookup_exported_from_kernel_public_api() -> None:
    assert "find_world_graph_revisions_by_operation_id" in kernel.__all__
    assert callable(kernel.find_world_graph_revisions_by_operation_id)
