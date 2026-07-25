"""Pure contract tests for the inert BLD-10a worldbuilding write plan."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
from graph_memory.candidate_semantic_promote_matrix import (
    CandidateSemanticPromoteError,
    map_candidate_semantics_to_kernel,
    map_reviewed_worldbuilding_semantics_to_kernel,
)
from graph_memory.worldbuilding_write_plan import (
    WorldbuildingWritePlanError,
    build_worldbuilding_write_plan,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    DEFAULT_SEMANTIC_STATE,
)
from tests.test_live_extract_promote_api import (
    BUNDLE_PATH,
    CAMPAIGN_ID,
    WORLD_ID,
    _candidate_graph_payload,
    _initialize,
)


def _preview() -> object:
    payload = _candidate_graph_payload(session_id=None)
    payload["preview_id"] = "preview:worldbuilding-write-plan"
    payload["source_artifact_ids"] = ["artifact:worldbuilding:test"]
    payload["session_id"] = None
    for index, node in enumerate(payload["nodes"]):
        node["node_id"] = f"wb_node_{index}"
        node["node_type"] = "character" if index == 0 else "location"
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    for edge in payload["edges"]:
        edge["edge_id"] = "wb_edge_0"
        edge["from_node_id"] = "wb_node_0"
        edge["to_node_id"] = "wb_node_1"
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    return candidate_graph_preview_from_dict(payload)


def _inputs(tmp_path: Path) -> dict[str, object]:
    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir(parents=True)
    world_root.mkdir(parents=True)
    bundle = load_contribution_bundle(BUNDLE_PATH)
    _initialize(world_root, bundle)
    source = repo / "source.md"
    source.write_text("worldbuilding source\n", encoding="utf-8")
    source_revision = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    parent = kernel.open_current_world_graph(world_root, WORLD_ID)[0].head_revision_id
    return {
        "world_root": world_root,
        "source_uri": str(source),
        "source_revision": source_revision,
        "parent": parent,
    }


def _dispositions(*, edge: str = "accept") -> list[dict[str, str]]:
    return [
        {"assertion_id": "wb_node_0", "decision": "create_new"},
        {"assertion_id": "wb_node_1", "decision": "create_new"},
        {"assertion_id": "wb_edge_0", "decision": edge},
    ]


def _build(tmp_path: Path, dispositions: list[dict[str, str]] | None = None):
    inputs = _inputs(tmp_path)
    return _build_from_inputs(
        inputs,
        dispositions=dispositions,
    )


def _build_from_inputs(
    inputs: dict[str, object],
    *,
    dispositions: list[dict[str, str]] | None = None,
):
    return build_worldbuilding_write_plan(
        preview=_preview(),  # type: ignore[arg-type]
        world_root=inputs["world_root"],  # type: ignore[arg-type]
        world_id=WORLD_ID,
        expected_parent_revision_id=inputs["parent"],  # type: ignore[arg-type]
        run_id="extraction-run:worldbuilding-test",
        source_artifact_id="artifact:worldbuilding:test",
        source_revision_id=inputs["source_revision"],  # type: ignore[arg-type]
        source_uri=inputs["source_uri"],  # type: ignore[arg-type]
        extraction_profile="worldbuilding_shepherds_flock_v0@0.1",
        campaign_scope=CAMPAIGN_ID,
        dispositions=dispositions or _dispositions(),
    )


def test_reviewed_worldbuilding_mapping_is_separate_from_recap() -> None:
    # CandidateGraphPreview's dataclass is the public semantic input type.
    from graph_memory.candidate_graph_preview import SemanticState

    state = SemanticState(**DEFAULT_SEMANTIC_STATE)
    with pytest.raises(CandidateSemanticPromoteError):
        map_candidate_semantics_to_kernel(
            object_id="wb",
            semantic=state,
            proposed_action="create",
        )
    mapped = map_reviewed_worldbuilding_semantics_to_kernel(
        object_id="wb",
        semantic=state,
        proposed_action="create",
    )
    assert mapped.canon_state == "canonical"
    assert mapped.approval_state == "accepted"
    assert mapped.epistemic_kind == "source_derived_candidate"
    assert mapped.visibility == "gm"


def test_same_dispositions_in_reverse_order_have_same_authority(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    first = _build_from_inputs(inputs)
    second = _build_from_inputs(
        inputs,
        dispositions=list(reversed(_dispositions())),
    )
    assert first.plan_id == second.plan_id
    assert first.plan_digest == second.plan_digest
    assert first.decision_digest == second.decision_digest
    assert first.effect == second.effect
    assert first.summary == second.summary


def test_reject_and_defer_remain_distinct(tmp_path: Path) -> None:
    plan = _build(
        tmp_path,
        dispositions=[
            {"assertion_id": "wb_node_0", "decision": "reject"},
            {"assertion_id": "wb_node_1", "decision": "defer"},
            {"assertion_id": "wb_edge_0", "decision": "defer"},
        ],
    )
    assert len(plan.effect["rejected_assertions"]) == 1
    assert plan.effect["unresolved_mentions"][0]["mention_id"] == "wb_node_1"
    assert plan.effect["deferred_candidate_ids"] == ["wb_edge_0", "wb_node_1"]
    assert plan.summary["rejected_candidate_count"] == 1
    assert plan.summary["deferred_candidate_count"] == 2


@pytest.mark.parametrize(
    "dispositions, code",
    [
        (
            [
                {"assertion_id": "wb_node_0", "decision": "create_new"},
                {"assertion_id": "wb_node_1", "decision": "create_new"},
            ],
            "invalid_disposition_set",
        ),
        (
            [
                {"assertion_id": "wb_node_0", "decision": "create_new"},
                {"assertion_id": "wb_node_1", "decision": "create_new"},
                {"assertion_id": "wb_edge_0", "decision": "create_new"},
            ],
            "invalid_disposition",
        ),
        (
            [
                {"assertion_id": "wb_node_0", "decision": "create_new"},
                {"assertion_id": "wb_node_1", "decision": "create_new"},
                {"assertion_id": "unknown", "decision": "reject"},
            ],
            "invalid_disposition_set",
        ),
    ],
)
def test_disposition_contract_fails_closed(
    tmp_path: Path,
    dispositions: list[dict[str, str]],
    code: str,
) -> None:
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _build(tmp_path, dispositions=dispositions)
    assert exc.value.code == code


def test_accepted_edge_requires_accepted_endpoints(tmp_path: Path) -> None:
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _build(
            tmp_path,
            dispositions=[
                {"assertion_id": "wb_node_0", "decision": "reject"},
                {"assertion_id": "wb_node_1", "decision": "create_new"},
                {"assertion_id": "wb_edge_0", "decision": "accept"},
            ],
        )
    assert exc.value.code == "edge_endpoint_unresolved"


def test_create_new_rejects_exact_id_conflict(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    conflict_payload = _candidate_graph_payload(session_id=None)
    conflict_payload["source_artifact_ids"] = ["artifact:worldbuilding:test"]
    conflict_payload["session_id"] = None
    conflict_payload["nodes"][0]["node_id"] = "pc:caelynn"
    conflict_payload["nodes"][0]["node_type"] = "character"
    conflict_payload["nodes"][0]["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
    for ref in conflict_payload["nodes"][0]["evidence_refs"]:
        ref["source_artifact_id"] = "artifact:worldbuilding:test"
    for node in conflict_payload["nodes"][1:]:
        node["node_type"] = "location"
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    for edge in conflict_payload["edges"]:
        edge["from_node_id"] = "pc:caelynn"
        edge["to_node_id"] = conflict_payload["nodes"][1]["node_id"]
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        build_worldbuilding_write_plan(
            preview=candidate_graph_preview_from_dict(conflict_payload),
            world_root=inputs["world_root"],  # type: ignore[arg-type]
            world_id=WORLD_ID,
            expected_parent_revision_id=inputs["parent"],  # type: ignore[arg-type]
            run_id="extraction-run:worldbuilding-conflict",
            source_artifact_id="artifact:worldbuilding:test",
            source_revision_id=inputs["source_revision"],  # type: ignore[arg-type]
            source_uri=inputs["source_uri"],  # type: ignore[arg-type]
            extraction_profile="worldbuilding_shepherds_flock_v0@0.1",
            campaign_scope=CAMPAIGN_ID,
            dispositions=[
                {"assertion_id": "pc:caelynn", "decision": "create_new"},
                {
                    "assertion_id": conflict_payload["nodes"][1]["node_id"],
                    "decision": "create_new",
                },
                {
                    "assertion_id": conflict_payload["edges"][0]["edge_id"],
                    "decision": "accept",
                },
            ],
        )
    assert exc.value.code == "new_node_id_conflict"


def test_bind_existing_uses_exact_active_same_kind_target(
    tmp_path: Path, monkeypatch
) -> None:
    inputs = _inputs(tmp_path)
    current_store = kernel.open_current_world_graph(
        inputs["world_root"], WORLD_ID  # type: ignore[arg-type]
    )[2]
    existing = next(iter(current_store.nodes.values())).model_copy(
        update={
            "node_id": "npc:exact-target",
            "kind": "npc",
            "role": "npc",
            "state": {
                "memory_state": "graph_read_model",
                "identity_canon_state": "canonical",
            },
        }
    )
    nodes = dict(current_store.nodes)
    nodes[existing.node_id] = existing
    pinned_store = current_store.model_copy(update={"nodes": nodes})
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: pinned_store,
    )
    plan = _build_from_inputs(
        inputs,
        dispositions=[
            {
                "assertion_id": "wb_node_0",
                "decision": "bind_existing",
                "target_node_id": "npc:exact-target",
            },
            {"assertion_id": "wb_node_1", "decision": "create_new"},
            {"assertion_id": "wb_edge_0", "decision": "accept"},
        ],
    )
    assert plan.effect["node_id_map"]["wb_node_0"] == "npc:exact-target"
    target_assertions = [
        item
        for item in plan.effect["accepted_proposals"]
        if item["subject_node_id"] == "npc:exact-target"
    ]
    assert target_assertions
    support_assertions = [
        item for item in target_assertions if item["assertion_kind"] != "edge"
    ]
    assert support_assertions
    assert all(item["assertion_kind"] != "node" for item in support_assertions)
    assert all(
        item["identity_resolution_outcome"] == "human_override"
        for item in support_assertions
    )


def test_plan_does_not_call_kernel_mutation_apis(tmp_path: Path, monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("mutation API called during BLD-10a prepare")

    for name in (
        "merge_contribution_to_revision",
        "publish_world_graph_revision",
        "publish_world_revision",
        "record_identity_decision",
        "merge_identity",
        "split_identity",
        "unmerge_identity",
    ):
        monkeypatch.setattr(kernel, name, fail)
    plan = _build(tmp_path)
    assert plan.plan_id.startswith("worldbuilding-write-plan:")
