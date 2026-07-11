"""Service-level Graph Review → durable contribution merge seam tests."""

from __future__ import annotations

from pathlib import Path

import graph_memory.kernel as kernel
from apps.live_control_server.services.graph_review_contribution_merge import (
    merge_graph_review_authored_assertions,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from tests.test_graph_authoring_overlay_models import object_assertion

WORLD_ID = "eldyrwild"


def test_graph_review_service_seam_uses_kernel_merge(tmp_path: Path, monkeypatch) -> None:
    store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:baseline-seed"],
    )

    calls: list[str] = []
    real_merge = kernel.merge_contribution_to_revision

    def _spy(root, *, world_id, contribution, expected_parent_revision_id=None):
        calls.append(contribution.source_kind)
        assert contribution.source_kind == "graph_review_authored_assertion"
        return real_merge(
            root,
            world_id=world_id,
            contribution=contribution,
            expected_parent_revision_id=expected_parent_revision_id,
        )

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_review_contribution_merge.kernel.merge_contribution_to_revision",
        _spy,
    )

    assertion = object_assertion(
        assertion_id="assert-seam-npc",
        object_ref={
            "ref_kind": "authored_node",
            "authored_node_id": "npc_seam_authored",
            "label": "Seam Authored NPC",
            "kind": "npc",
            "role": "npc",
        },
        aliases=["Seam Authored NPC"],
    )
    result = merge_graph_review_authored_assertions(
        tmp_path,
        world_id=WORLD_ID,
        source_artifact_id="artifact:graph-review:seam",
        source_revision_id="authored-seam-1",
        authored_by="gm",
        assertions=[assertion],
        campaign_scope="longmont-c1",
    )
    assert result.published is True
    assert calls == ["graph_review_authored_assertion"]

    _head, _rev, head_store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    assert "npc_seam_authored" in head_store.nodes
    assert head_store.nodes["npc_seam_authored"].label == "Seam Authored NPC"
