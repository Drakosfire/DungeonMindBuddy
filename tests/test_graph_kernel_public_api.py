"""Public API smoke tests for graph_memory.kernel (PR003)."""

from __future__ import annotations

from pathlib import Path

import graph_memory.kernel as kernel
from graph_memory.kernel.contracts import ALL_RESERVED_KERNEL_APIS
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)


def test_kernel_public_api_can_publish_and_load_world_graph(tmp_path: Path) -> None:
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    published = kernel.publish_world_revision(
        tmp_path,
        "eldyrwild",
        store,
        operation_ids=["op:kernel-smoke"],
    )
    head, revision, loaded = kernel.open_current_world_graph(tmp_path, "eldyrwild")
    assert head.head_revision_id == published.revision.revision_id
    assert revision.revision_id == published.revision.revision_id
    assert loaded.campaign_id == "longmont-c2"
    assert head.world_id == "eldyrwild"


def test_reserved_kernel_apis_are_not_claimed_complete() -> None:
    public_names = set(kernel.__all__)
    assert ALL_RESERVED_KERNEL_APIS == ()
    for name in ALL_RESERVED_KERNEL_APIS:
        assert name not in public_names, f"{name} must not be exported as complete Kernel API"
        assert not hasattr(kernel, name), f"{name} leaked onto graph_memory.kernel"

    # PR004 identity APIs are implemented and exported.
    for name in (
        "resolve_identity",
        "record_identity_decision",
        "merge_identity",
        "split_identity",
        "unmerge_identity",
        "classify_identity_outcome",
    ):
        assert name in public_names
        assert callable(getattr(kernel, name))

    # PR005 contribution APIs are implemented and exported.
    for name in (
        "create_graph_contribution",
        "merge_contribution_to_revision",
        "supersede_graph_contribution",
        "retract_graph_contribution",
        "rebuild_from_contributions",
        "build_contribution_integrity_report",
    ):
        assert name in public_names
        assert callable(getattr(kernel, name))

    # PR007A projection APIs are implemented and exported.
    for name in (
        "project_world_graph",
        "build_projection_payload",
        "resolve_projection_admissibility",
        "search_world_graph_projection",
        "WorldGraphProjectionError",
    ):
        assert name in public_names
        assert callable(getattr(kernel, name)) or name == "WorldGraphProjectionError"

    # PR010A retrieval + source-anchor admission APIs are implemented and exported.
    for name in (
        "search_campaign_graph",
        "get_campaign_object",
        "get_object_neighborhood",
        "get_object_evidence",
        "read_source_anchor",
        "WorldGraphRetrievalError",
    ):
        assert name in public_names
        assert callable(getattr(kernel, name)) or name == "WorldGraphRetrievalError"


def test_opt02_revision_ready_exports_and_no_storage_import() -> None:
    import ast
    import importlib.util
    from pathlib import Path

    public_names = set(kernel.__all__)
    for name in (
        "WorldRevisionReadyNotification",
        "allocate_revision_ready_commit_seq",
        "offer_revision_ready",
        "offer_revision_ready_from_publish",
        "get_revision_ready_mailbox",
        "reset_revision_ready_mailbox",
    ):
        assert name in public_names
        assert hasattr(kernel, name)

    spec = importlib.util.find_spec("graph_memory.kernel.world_revision_ready")
    assert spec is not None and spec.origin
    tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "graph_memory.world_supergraph.storage" not in imported_modules
