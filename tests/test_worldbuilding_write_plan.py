"""Pure contract tests for the inert BLD-10a worldbuilding write plan."""

from __future__ import annotations

import copy
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
    WORLD_BUILDING_WRITE_PLAN_SCHEMA,
    WORLD_BUILDING_WRITE_PLAN_VERSION,
    WORLDBUILDING_BIND_SUPPORT_PREDICATE,
    WorldbuildingWritePlanError,
    WorldbuildingWritePlanVerificationContext,
    build_worldbuilding_write_plan,
    materialize_worldbuilding_contribution,
    verify_worldbuilding_write_plan,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.union_supergraph.model import UnionIdentityRedirect
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


def _build(
    tmp_path: Path,
    dispositions: list[dict[str, str]] | None = None,
    *,
    preview: object | None = None,
):
    inputs = _inputs(tmp_path)
    used_preview = preview or _preview()
    plan = _build_from_inputs(
        inputs,
        dispositions=dispositions,
        preview=used_preview,
    )
    return plan, used_preview, inputs


def _build_from_inputs(
    inputs: dict[str, object],
    *,
    dispositions: list[dict[str, str]] | None = None,
    preview: object | None = None,
    campaign_scope: str | None = CAMPAIGN_ID,
):
    return build_worldbuilding_write_plan(
        preview=preview or _preview(),  # type: ignore[arg-type]
        world_root=inputs["world_root"],  # type: ignore[arg-type]
        world_id=WORLD_ID,
        expected_parent_revision_id=inputs["parent"],  # type: ignore[arg-type]
        run_id="extraction-run:worldbuilding-test",
        source_artifact_id="artifact:worldbuilding:test",
        source_revision_id=inputs["source_revision"],  # type: ignore[arg-type]
        source_uri=inputs["source_uri"],  # type: ignore[arg-type]
        extraction_profile="worldbuilding_shepherds_flock_v0@0.1",
        campaign_scope=campaign_scope,
        dispositions=dispositions or _dispositions(),
    )


def _response_package(plan) -> dict[str, object]:
    return {
        "schema": WORLD_BUILDING_WRITE_PLAN_SCHEMA,
        "version": WORLD_BUILDING_WRITE_PLAN_VERSION,
        "planId": plan.plan_id,
        "planDigest": plan.plan_digest,
        "decisionDigest": plan.decision_digest,
        "worldId": plan.world_id,
        "parentRevisionId": plan.parent_revision_id,
        "runId": plan.run_id,
        "sourceDomain": "worldbuilding",
        "sourceArtifactId": plan.source_artifact_id,
        "sourceRevisionId": plan.source_revision_id,
        "extractionProfile": plan.extraction_profile,
        "candidatePreviewId": plan.candidate_preview_id,
        "candidateSchema": plan.candidate_schema,
        "candidateVersion": plan.candidate_version,
        "effect": copy.deepcopy(plan.effect),
        "summary": copy.deepcopy(plan.summary),
        "diagnostics": list(plan.diagnostics),
        "confirmable": False,
        "confirmableReason": (
            "BLD-10a prepares an inert write plan; graph confirmation is not implemented."
        ),
    }


def _reseal_package(package: dict[str, object]) -> dict[str, object]:
    """Recompute digests after a semantic mutation of a response package."""
    from graph_memory.worldbuilding_write_plan import _canonical_effect, _digest

    effect = _canonical_effect(package["effect"])
    package["effect"] = effect
    decision_digest = _digest(effect["decision_snapshot"])
    plan_identity = {
        "world_id": package["worldId"],
        "parent_revision_id": package["parentRevisionId"],
        "run_id": package["runId"],
        "source_domain": "worldbuilding",
        "source_artifact_id": package["sourceArtifactId"],
        "source_revision_id": package["sourceRevisionId"],
        "extraction_profile": package["extractionProfile"],
        "candidate_preview_id": package["candidatePreviewId"],
        "candidate_schema": package["candidateSchema"],
        "candidate_version": package["candidateVersion"],
        "decision_snapshot": effect["decision_snapshot"],
        "effect": effect,
    }
    plan_digest = _digest(plan_identity)
    package["decisionDigest"] = decision_digest
    package["planDigest"] = plan_digest
    package["planId"] = (
        "worldbuilding-write-plan:"
        f"{plan_digest.removeprefix('sha256:')[:24]}"
    )
    return package


def _verify(
    package: dict[str, object],
    inputs: dict[str, object],
    preview=None,
    *,
    campaign_scope: str | None = CAMPAIGN_ID,
    context: WorldbuildingWritePlanVerificationContext | None = None,
):
    used_preview = preview if preview is not None else _preview()
    used_context = context or WorldbuildingWritePlanVerificationContext(
        world_id=WORLD_ID,
        parent_revision_id=str(inputs["parent"]),
        run_id="extraction-run:worldbuilding-test",
        source_artifact_id="artifact:worldbuilding:test",
        source_revision_id=str(inputs["source_revision"]),
        source_uri=str(inputs["source_uri"]),
        extraction_profile="worldbuilding_shepherds_flock_v0@0.1",
        campaign_scope=campaign_scope,
    )
    return verify_worldbuilding_write_plan(
        package,
        preview=used_preview,
        world_root=inputs["world_root"],  # type: ignore[arg-type]
        context=used_context,
    )


def _recompute_assertion_id(assertion: dict[str, object]) -> str:
    return kernel.compute_assertion_id(
        assertion_kind=assertion["assertion_kind"],  # type: ignore[arg-type]
        subject_node_id=assertion.get("subject_node_id"),  # type: ignore[arg-type]
        target_node_id=assertion.get("target_node_id"),  # type: ignore[arg-type]
        predicate=assertion.get("predicate"),  # type: ignore[arg-type]
        label=assertion.get("label"),  # type: ignore[arg-type]
        value=dict(assertion.get("value") or {}),  # type: ignore[arg-type]
        campaign_scope=assertion.get("campaign_scope"),  # type: ignore[arg-type]
        temporal_scope=assertion.get("temporal_scope"),  # type: ignore[arg-type]
        epistemic_kind=assertion.get("epistemic_kind"),  # type: ignore[arg-type]
        visibility=assertion.get("visibility"),  # type: ignore[arg-type]
    )


def _replace_assertion(
    effect: dict[str, object],
    *,
    old_id: str,
    assertion: dict[str, object],
    candidate_id: str,
) -> None:
    new_id = _recompute_assertion_id(assertion)
    assertion["assertion_id"] = new_id
    for bucket in ("accepted_proposals", "rejected_assertions"):
        items = effect[bucket]
        for index, item in enumerate(items):  # type: ignore[arg-type]
            if item["assertion_id"] == old_id:
                items[index] = assertion  # type: ignore[index]
                break
    mapped = list(effect["candidate_effect_map"][candidate_id])  # type: ignore[index]
    effect["candidate_effect_map"][candidate_id] = [  # type: ignore[index]
        new_id if item == old_id else item for item in mapped
    ]


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


def test_verify_worldbuilding_write_plan_accepts_unmodified_response_package(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    verified = _verify(_response_package(plan), inputs, preview)
    assert verified["plan_id"] == plan.plan_id
    assert verified["plan_digest"] == plan.plan_digest
    assert verified["summary"] == plan.summary
    assert verified["diagnostics"] == plan.diagnostics
    assert verified["confirmable"] is False
    assert verified["confirmable_reason"] == (
        "BLD-10a prepares an inert write plan; graph confirmation is not implemented."
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda package: package["effect"]["accepted_proposals"][0].update(
            label="tampered"
        ),
        lambda package: package["effect"]["decision_snapshot"][0].update(
            target_node_id="node:wrong-target"
        ),
        lambda package: package.update(parentRevisionId="rev:tampered"),
        lambda package: package["effect"]["decision_snapshot"][0].update(
            decision="reject"
        ),
        lambda package: package.update(planDigest="sha256:" + ("0" * 64)),
        lambda package: package.update(planId="worldbuilding-write-plan:tampered"),
    ],
    ids=[
        "assertion-body",
        "bind-target-in-snapshot",
        "parent-revision",
        "decision-snapshot",
        "plan-digest",
        "plan-id",
    ],
)
def test_verify_worldbuilding_write_plan_rejects_tampering(
    tmp_path: Path,
    mutation,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    mutation(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_stripped_evidence_after_digest_recompute(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    assertion = package["effect"]["accepted_proposals"][0]
    assertion["evidence_ref_ids"] = []
    assertion["value"]["evidence"] = []
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_redirected_evidence_after_digest_recompute(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    assertion = package["effect"]["accepted_proposals"][0]
    evidence = assertion["value"]["evidence"][0]
    redirected = "evidence:some-existing-unrelated-id"
    evidence["evidence_ref_id"] = redirected
    evidence["locator"] = "a-different-location"
    assertion["evidence_ref_ids"] = [redirected]
    assertion["assertion_id"] = _recompute_assertion_id(assertion)
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_create_node_rewrite_after_digest_recompute(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    effect = package["effect"]
    candidate_id = "wb_node_0"
    old_id = effect["candidate_effect_map"][candidate_id][0]
    assertion = next(
        item for item in effect["accepted_proposals"] if item["assertion_id"] == old_id
    )
    assertion["label"] = f"{assertion['label']}-rewritten"
    assertion["value"]["summary"] = "rewritten-summary"
    assertion["value"]["kind"] = "location"
    assertion["value"]["role"] = "location"
    assertion["visibility"] = "player"
    assertion["value"]["canon_state"] = "played_canon"
    _replace_assertion(
        effect, old_id=old_id, assertion=assertion, candidate_id=candidate_id
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_edge_substitution_after_digest_recompute(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    effect = package["effect"]
    edge_candidate = next(
        item["assertion_id"]
        for item in effect["decision_snapshot"]
        if item["candidate_kind"] == "edge"
    )
    edge_assertion_id = effect["candidate_effect_map"][edge_candidate][0]
    node_assertion_id = next(
        assertion_id
        for candidate_id, assertion_ids in effect["candidate_effect_map"].items()
        for assertion_id in assertion_ids
        if assertion_id != edge_assertion_id
    )
    effect["candidate_effect_map"][edge_candidate] = [node_assertion_id]
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_edge_endpoint_rewrite_after_digest_recompute(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    effect = package["effect"]
    edge_candidate = next(
        item["assertion_id"]
        for item in effect["decision_snapshot"]
        if item["candidate_kind"] == "edge"
    )
    old_assertion_id = effect["candidate_effect_map"][edge_candidate][0]
    assertion = next(
        item
        for item in effect["accepted_proposals"]
        if item["assertion_id"] == old_assertion_id
    )
    assertion["subject_node_id"], assertion["target_node_id"] = (
        assertion["target_node_id"],
        assertion["subject_node_id"],
    )
    assertion["value"]["edge_id"] = (
        f"edge:{assertion['subject_node_id']}:{assertion['predicate']}:"
        f"{assertion['target_node_id']}"
    )
    _replace_assertion(
        effect,
        old_id=old_assertion_id,
        assertion=assertion,
        candidate_id=edge_candidate,
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_edge_semantic_rewrite_after_digest_recompute(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    effect = package["effect"]
    edge_candidate = next(
        item["assertion_id"]
        for item in effect["decision_snapshot"]
        if item["candidate_kind"] == "edge"
    )
    old_assertion_id = effect["candidate_effect_map"][edge_candidate][0]
    assertion = next(
        item
        for item in effect["accepted_proposals"]
        if item["assertion_id"] == old_assertion_id
    )
    assertion["label"] = "rewritten-edge-label"
    assertion["predicate"] = "rewritten_predicate"
    assertion["visibility"] = "player"
    assertion["epistemic_kind"] = "gm_authored"
    assertion["value"]["predicate"] = "rewritten_predicate"
    assertion["value"]["canon_state"] = "played_canon"
    assertion["value"]["approval_state"] = "candidate"
    assertion["value"]["edge_id"] = (
        f"edge:{assertion['subject_node_id']}:rewritten_predicate:"
        f"{assertion['target_node_id']}"
    )
    _replace_assertion(
        effect,
        old_id=old_assertion_id,
        assertion=assertion,
        candidate_id=edge_candidate,
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_unclaimed_effect_assertion_after_digest_recompute(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    effect = package["effect"]
    clone = copy.deepcopy(effect["accepted_proposals"][0])
    clone["value"] = dict(clone["value"] or {})
    clone["value"]["summary"] = "unclaimed-extra-summary"
    clone["assertion_id"] = _recompute_assertion_id(clone)
    effect["accepted_proposals"].append(clone)
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_tampered_deferred_mention_after_digest_recompute(
    tmp_path: Path,
) -> None:
    preview = _preview()
    inputs = _inputs(tmp_path)
    plan = _build_from_inputs(
        inputs,
        preview=preview,
        dispositions=[
            {"assertion_id": "wb_node_0", "decision": "reject"},
            {"assertion_id": "wb_node_1", "decision": "defer"},
            {"assertion_id": "wb_edge_0", "decision": "defer"},
        ],
    )
    package = _response_package(plan)
    mention = package["effect"]["unresolved_mentions"][0]
    mention["object_kind"] = "location"
    mention["evidence_ref_ids"] = []
    package["effect"]["unresolved_mentions"].append(copy.deepcopy(mention))
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_two_candidates_can_bind_to_the_same_durable_node(
    tmp_path: Path, monkeypatch
) -> None:
    inputs = _inputs(tmp_path)
    current_store = kernel.open_current_world_graph(
        inputs["world_root"], WORLD_ID  # type: ignore[arg-type]
    )[2]
    existing = next(iter(current_store.nodes.values())).model_copy(
        update={
            "node_id": "npc:shared-bind-target",
            "kind": "npc",
            "role": "npc",
            "state": {
                "memory_state": "graph_read_model",
                "identity_canon_state": "canonical",
            },
        }
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: current_store.model_copy(
            update={"nodes": {**current_store.nodes, existing.node_id: existing}}
        ),
    )
    payload = _candidate_graph_payload(session_id=None)
    payload["preview_id"] = "preview:worldbuilding-multi-bind"
    payload["source_artifact_ids"] = ["artifact:worldbuilding:test"]
    payload["session_id"] = None
    for index, node in enumerate(payload["nodes"]):
        node["node_id"] = f"wb_bind_{index}"
        node["node_type"] = "character"
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    for edge in payload["edges"]:
        edge["edge_id"] = "wb_edge_multi_bind"
        edge["from_node_id"] = "wb_bind_0"
        edge["to_node_id"] = "wb_bind_1"
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    preview = candidate_graph_preview_from_dict(payload)
    plan = _build_from_inputs(
        inputs,
        preview=preview,
        dispositions=[
            {
                "assertion_id": "wb_bind_0",
                "decision": "bind_existing",
                "target_node_id": "npc:shared-bind-target",
            },
            {
                "assertion_id": "wb_bind_1",
                "decision": "bind_existing",
                "target_node_id": "npc:shared-bind-target",
            },
            {"assertion_id": "wb_edge_multi_bind", "decision": "accept"},
        ],
    )
    assert plan.effect["node_id_map"] == {
        "wb_bind_0": "npc:shared-bind-target",
        "wb_bind_1": "npc:shared-bind-target",
    }
    support = [
        item
        for item in plan.effect["accepted_proposals"]
        if item["assertion_kind"] == "attribute"
        and item["predicate"] == WORLDBUILDING_BIND_SUPPORT_PREDICATE
    ]
    assert len(support) == 2
    extract_ids = {item["value"]["extract_node_id"] for item in support}
    assert extract_ids == {"wb_bind_0", "wb_bind_1"}
    assert all(
        item["subject_node_id"] == "npc:shared-bind-target" for item in support
    )
    verified = _verify(_response_package(plan), inputs, preview)
    assert verified["plan_id"] == plan.plan_id
    assert set(plan.effect["candidate_effect_map"]) == {
        "wb_bind_0",
        "wb_bind_1",
        "wb_edge_multi_bind",
    }


def test_campaign_lineage_is_embedded_only_for_campaign_scoped_plans(
    tmp_path: Path,
) -> None:
    scoped, _preview_obj, _inputs_obj = _build(tmp_path)
    scoped_artifacts = [
        artifact
        for assertion in scoped.effect["accepted_proposals"]
        for artifact in assertion["value"]["source_artifacts"]
    ]
    assert scoped_artifacts
    assert all(artifact["campaign_id"] == CAMPAIGN_ID for artifact in scoped_artifacts)

    unscoped_root = tmp_path / "unscoped"
    unscoped_root.mkdir()
    unscoped_preview_payload = _candidate_graph_payload(session_id=None)
    unscoped_preview_payload["preview_id"] = "preview:worldbuilding-unscoped"
    unscoped_preview_payload["campaign_id"] = None
    unscoped_preview_payload["source_artifact_ids"] = ["artifact:worldbuilding:test"]
    unscoped_preview_payload["session_id"] = None
    for index, node in enumerate(unscoped_preview_payload["nodes"]):
        node["node_id"] = f"wb_node_{index}"
        node["node_type"] = "character" if index == 0 else "location"
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    for edge in unscoped_preview_payload["edges"]:
        edge["edge_id"] = "wb_edge_0"
        edge["from_node_id"] = "wb_node_0"
        edge["to_node_id"] = "wb_node_1"
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    unscoped = _build_from_inputs(
        _inputs(unscoped_root),
        preview=candidate_graph_preview_from_dict(unscoped_preview_payload),
        campaign_scope=None,
    )
    unscoped_artifacts = [
        artifact
        for assertion in unscoped.effect["accepted_proposals"]
        for artifact in assertion["value"]["source_artifacts"]
    ]
    assert unscoped_artifacts
    assert all("campaign_id" not in artifact for artifact in unscoped_artifacts)


def test_reject_and_defer_remain_distinct(tmp_path: Path) -> None:
    plan, _preview_obj, _inputs_obj = _build(
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
    attribute_assertions = [
        item for item in support_assertions if item["assertion_kind"] == "attribute"
    ]
    assert len(attribute_assertions) == 1
    assert attribute_assertions[0]["predicate"] == WORLDBUILDING_BIND_SUPPORT_PREDICATE
    assert attribute_assertions[0]["predicate"] != "session_observation"
    assert attribute_assertions[0]["temporal_scope"] is None
    assert "session_ids" not in attribute_assertions[0]["value"]
    assert attribute_assertions[0]["value"]["extract_node_id"] == "wb_node_0"
    assert plan.effect["candidate_effect_map"]["wb_node_0"] == [
        attribute_assertions[0]["assertion_id"]
    ]


def _build_with_bind_target(
    tmp_path: Path,
    monkeypatch,
    *,
    candidate_type: str,
    target_kind: str,
):
    inputs = _inputs(tmp_path)
    current_store = kernel.open_current_world_graph(
        inputs["world_root"], WORLD_ID  # type: ignore[arg-type]
    )[2]
    target_id = f"{target_kind}:family-target"
    existing = next(iter(current_store.nodes.values())).model_copy(
        update={
            "node_id": target_id,
            "kind": target_kind,
            "role": target_kind,
            "state": {
                "memory_state": "graph_read_model",
                "identity_canon_state": "canonical",
            },
        }
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: current_store.model_copy(
            update={"nodes": {**current_store.nodes, target_id: existing}}
        ),
    )
    preview_payload = _candidate_graph_payload(session_id=None)
    preview_payload["preview_id"] = "preview:worldbuilding-family"
    preview_payload["source_artifact_ids"] = ["artifact:worldbuilding:test"]
    preview_payload["nodes"][0]["node_type"] = candidate_type
    for node in preview_payload["nodes"]:
        node["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    for edge in preview_payload["edges"]:
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    preview = candidate_graph_preview_from_dict(preview_payload)
    return _build_from_inputs(
        inputs,
        preview=preview,
        dispositions=[
            {
                "assertion_id": "obj_session22_vial",
                "decision": "bind_existing",
                "target_node_id": target_id,
            },
            {"assertion_id": "mystery_puddles", "decision": "create_new"},
            {"assertion_id": "e33", "decision": "accept"},
        ],
    )


@pytest.mark.parametrize(
    ("candidate_type", "target_kind"),
    [
        ("character", "pc"),
        ("character", "npc"),
        ("organization", "faction"),
        ("collective", "party"),
    ],
)
def test_bind_existing_accepts_same_kind_families(
    tmp_path: Path,
    monkeypatch,
    candidate_type: str,
    target_kind: str,
) -> None:
    plan = _build_with_bind_target(
        tmp_path,
        monkeypatch,
        candidate_type=candidate_type,
        target_kind=target_kind,
    )
    assert plan.effect["node_id_map"]["obj_session22_vial"] == (
        f"{target_kind}:family-target"
    )


def test_bind_existing_rejects_cross_family_target(
    tmp_path: Path, monkeypatch
) -> None:
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _build_with_bind_target(
            tmp_path,
            monkeypatch,
            candidate_type="character",
            target_kind="location",
        )
    assert exc.value.code == "bind_target_kind_mismatch"


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
    plan, _preview_obj, _inputs_obj = _build(tmp_path)
    assert plan.plan_id.startswith("worldbuilding-write-plan:")


def _preview_with_node_aliases(aliases: list[str]) -> object:
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
        if index == 0:
            node["aliases"] = list(aliases)
    for edge in payload["edges"]:
        edge["edge_id"] = "wb_edge_0"
        edge["from_node_id"] = "wb_node_0"
        edge["to_node_id"] = "wb_node_1"
        edge["semantic_state"] = dict(DEFAULT_SEMANTIC_STATE)
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = "artifact:worldbuilding:test"
    return candidate_graph_preview_from_dict(payload)


def _bind_fixture(
    tmp_path: Path,
    monkeypatch,
    *,
    target_id: str = "npc:exact-target",
    aliases: list[str] | None = None,
):
    inputs = _inputs(tmp_path)
    current_store = kernel.open_current_world_graph(
        inputs["world_root"], WORLD_ID  # type: ignore[arg-type]
    )[2]
    existing = next(iter(current_store.nodes.values())).model_copy(
        update={
            "node_id": target_id,
            "kind": "npc",
            "role": "npc",
            "state": {
                "memory_state": "graph_read_model",
                "identity_canon_state": "canonical",
            },
        }
    )
    pinned_store = current_store.model_copy(
        update={"nodes": {**current_store.nodes, existing.node_id: existing}}
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: pinned_store,
    )
    preview = (
        _preview_with_node_aliases(aliases)
        if aliases is not None
        else _preview()
    )
    plan = _build_from_inputs(
        inputs,
        preview=preview,
        dispositions=[
            {
                "assertion_id": "wb_node_0",
                "decision": "bind_existing",
                "target_node_id": target_id,
            },
            {"assertion_id": "wb_node_1", "decision": "create_new"},
            {"assertion_id": "wb_edge_0", "decision": "accept"},
        ],
    )
    return plan, preview, inputs, pinned_store


def _reseal_bind_to_target(
    package: dict[str, object],
    *,
    target_node_id: str,
) -> None:
    effect = package["effect"]
    for item in effect["decision_snapshot"]:  # type: ignore[index]
        if item["assertion_id"] == "wb_node_0":
            item["target_node_id"] = target_node_id
    effect["node_id_map"]["wb_node_0"] = target_node_id  # type: ignore[index]
    mapped_ids = list(effect["candidate_effect_map"]["wb_node_0"])  # type: ignore[index]
    replacements: list[tuple[str, dict[str, object]]] = []
    for old_id in mapped_ids:
        assertion = copy.deepcopy(
            next(
                item
                for item in effect["accepted_proposals"]  # type: ignore[index]
                if item["assertion_id"] == old_id
            )
        )
        assertion["subject_node_id"] = target_node_id
        replacements.append((old_id, assertion))
    for old_id, assertion in replacements:
        _replace_assertion(
            effect,  # type: ignore[arg-type]
            old_id=old_id,
            assertion=assertion,
            candidate_id="wb_node_0",
        )
    _reseal_package(package)


def test_verify_rejects_rejected_node_rewrite_after_digest_recompute(
    tmp_path: Path,
) -> None:
    preview = _preview()
    inputs = _inputs(tmp_path)
    plan = _build_from_inputs(
        inputs,
        preview=preview,
        dispositions=[
            {"assertion_id": "wb_node_0", "decision": "reject"},
            {"assertion_id": "wb_node_1", "decision": "create_new"},
            {"assertion_id": "wb_edge_0", "decision": "defer"},
        ],
    )
    package = _response_package(plan)
    effect = package["effect"]
    old_id = effect["candidate_effect_map"]["wb_node_0"][0]
    assertion = next(
        item for item in effect["rejected_assertions"] if item["assertion_id"] == old_id
    )
    assertion["label"] = f"{assertion['label']}-rejected-rewrite"
    assertion["visibility"] = "player"
    assertion["value"]["summary"] = "rejected-rewrite"
    _replace_assertion(
        effect, old_id=old_id, assertion=assertion, candidate_id="wb_node_0"
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_bind_alias_injection_after_digest_recompute(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, _store = _bind_fixture(tmp_path, monkeypatch)
    package = _response_package(plan)
    effect = package["effect"]
    support_id = effect["candidate_effect_map"]["wb_node_0"][0]
    support = next(
        item for item in effect["accepted_proposals"] if item["assertion_id"] == support_id
    )
    injected = copy.deepcopy(support)
    injected["assertion_kind"] = "alias"
    injected["predicate"] = None
    injected["label"] = "Injected Alias"
    injected["value"] = {
        "alias": "Injected Alias",
        "evidence": copy.deepcopy(support["value"]["evidence"]),
        "source_artifacts": copy.deepcopy(support["value"]["source_artifacts"]),
    }
    injected["assertion_id"] = _recompute_assertion_id(injected)
    effect["accepted_proposals"].append(injected)
    effect["candidate_effect_map"]["wb_node_0"] = [support_id, injected["assertion_id"]]
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_bind_support_rewrite_after_digest_recompute(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, _store = _bind_fixture(tmp_path, monkeypatch)
    package = _response_package(plan)
    effect = package["effect"]
    old_id = effect["candidate_effect_map"]["wb_node_0"][0]
    support = next(
        item for item in effect["accepted_proposals"] if item["assertion_id"] == old_id
    )
    support["value"]["summary"] = "rewritten-bind-summary"
    support["value"]["kind"] = "pc"
    evidence = support["value"]["evidence"][0]
    # Keep canonical evidence shape but point at a different span in-artifact.
    evidence["source_span_ref_id"] = "span:rewritten"
    evidence["locator"] = "span:rewritten"
    evidence["evidence_ref_id"] = (
        f"evidence:{evidence['source_artifact_id']}:span:rewritten"
    )
    support["evidence_ref_ids"] = [evidence["evidence_ref_id"]]
    _replace_assertion(
        effect, old_id=old_id, assertion=support, candidate_id="wb_node_0"
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_resealed_missing_bind_target(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, _store = _bind_fixture(tmp_path, monkeypatch)
    package = _response_package(plan)
    effect = package["effect"]
    for item in effect["decision_snapshot"]:
        if item["assertion_id"] == "wb_node_0":
            item["target_node_id"] = "npc:missing-target"
    effect["node_id_map"]["wb_node_0"] = "npc:missing-target"
    old_id = effect["candidate_effect_map"]["wb_node_0"][0]
    support = next(
        item for item in effect["accepted_proposals"] if item["assertion_id"] == old_id
    )
    support["subject_node_id"] = "npc:missing-target"
    _replace_assertion(
        effect, old_id=old_id, assertion=support, candidate_id="wb_node_0"
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_resealed_cross_family_bind_target(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, pinned_store = _bind_fixture(tmp_path, monkeypatch)
    location = next(iter(pinned_store.nodes.values())).model_copy(
        update={
            "node_id": "location:cross-family",
            "kind": "location",
            "role": "location",
            "state": {
                "memory_state": "graph_read_model",
                "identity_canon_state": "canonical",
            },
        }
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: pinned_store.model_copy(
            update={"nodes": {**pinned_store.nodes, location.node_id: location}}
        ),
    )
    package = _response_package(plan)
    effect = package["effect"]
    for item in effect["decision_snapshot"]:
        if item["assertion_id"] == "wb_node_0":
            item["target_node_id"] = "location:cross-family"
    effect["node_id_map"]["wb_node_0"] = "location:cross-family"
    old_id = effect["candidate_effect_map"]["wb_node_0"][0]
    support = next(
        item for item in effect["accepted_proposals"] if item["assertion_id"] == old_id
    )
    support["subject_node_id"] = "location:cross-family"
    _replace_assertion(
        effect, old_id=old_id, assertion=support, candidate_id="wb_node_0"
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_resealed_alternate_same_family_bind_target(
    tmp_path: Path, monkeypatch
) -> None:
    """A different valid same-family target is only accepted via fresh prepare.

    Hand-editing the carried effect/subjects without regenerating the full mapped
    support payload must not verify even when digests are resealed.
    """
    plan, preview, inputs, pinned_store = _bind_fixture(tmp_path, monkeypatch)
    alternate = next(iter(pinned_store.nodes.values())).model_copy(
        update={
            "node_id": "npc:alternate-same-family",
            "kind": "npc",
            "role": "npc",
            "state": {
                "memory_state": "graph_read_model",
                "identity_canon_state": "canonical",
            },
        }
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: pinned_store.model_copy(
            update={"nodes": {**pinned_store.nodes, alternate.node_id: alternate}}
        ),
    )
    package = _response_package(plan)
    effect = package["effect"]
    for item in effect["decision_snapshot"]:
        if item["assertion_id"] == "wb_node_0":
            item["target_node_id"] = "npc:alternate-same-family"
    effect["node_id_map"]["wb_node_0"] = "npc:alternate-same-family"
    old_id = effect["candidate_effect_map"]["wb_node_0"][0]
    support = next(
        item for item in effect["accepted_proposals"] if item["assertion_id"] == old_id
    )
    # Incomplete rewrite: only subjects/targets change; mapped value stays stale.
    support["subject_node_id"] = "npc:alternate-same-family"
    _replace_assertion(
        effect, old_id=old_id, assertion=support, candidate_id="wb_node_0"
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_bind_alias_rewrite_after_digest_recompute(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, _store = _bind_fixture(
        tmp_path, monkeypatch, aliases=["Reviewed Alias"]
    )
    package = _response_package(plan)
    effect = package["effect"]
    mapped_ids = list(effect["candidate_effect_map"]["wb_node_0"])
    aliases = [
        item
        for item in effect["accepted_proposals"]
        if item["assertion_id"] in mapped_ids and item["assertion_kind"] == "alias"
    ]
    assert aliases, "expected bind fixture with aliases to emit an alias assertion"
    old_id = aliases[0]["assertion_id"]
    alias = copy.deepcopy(aliases[0])
    alias["label"] = "Rewritten Alias"
    alias["value"]["alias"] = "Rewritten Alias"
    _replace_assertion(
        effect, old_id=old_id, assertion=alias, candidate_id="wb_node_0"
    )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_resealed_redirected_bind_target(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, pinned_store = _bind_fixture(tmp_path, monkeypatch)
    redirect_source = next(iter(pinned_store.nodes.values())).model_copy(
        update={
            "node_id": "npc:redirect-source",
            "kind": "npc",
            "role": "npc",
            "state": {
                "memory_state": "merged_away",
                "identity_canon_state": "merged_away",
            },
        }
    )
    redirect = UnionIdentityRedirect(
        redirect_id="redirect:npc-redirect-source",
        campaign_id=CAMPAIGN_ID,
        from_node_id="npc:redirect-source",
        to_node_id="npc:exact-target",
        assertion_id="assertion:redirect-source",
        created_at="2026-07-08T00:00:00Z",
        status="active",
        materialization_pass_id="pass:test",
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: pinned_store.model_copy(
            update={
                "nodes": {
                    **pinned_store.nodes,
                    redirect_source.node_id: redirect_source,
                },
                "identity_redirects": [
                    *pinned_store.identity_redirects,
                    redirect,
                ],
            }
        ),
    )
    package = _response_package(plan)
    _reseal_bind_to_target(package, target_node_id="npc:redirect-source")
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_resealed_provisional_bind_target(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, pinned_store = _bind_fixture(tmp_path, monkeypatch)
    provisional = next(iter(pinned_store.nodes.values())).model_copy(
        update={
            "node_id": "npc:provisional-target",
            "kind": "npc",
            "role": "npc",
            "state": {
                "memory_state": "graph_read_model",
                "identity_canon_state": "noncanonical_provisional",
            },
        }
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: pinned_store.model_copy(
            update={"nodes": {**pinned_store.nodes, provisional.node_id: provisional}}
        ),
    )
    package = _response_package(plan)
    _reseal_bind_to_target(package, target_node_id="npc:provisional-target")
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_resealed_rejected_bind_target(
    tmp_path: Path, monkeypatch
) -> None:
    plan, preview, inputs, pinned_store = _bind_fixture(tmp_path, monkeypatch)
    rejected = next(iter(pinned_store.nodes.values())).model_copy(
        update={
            "node_id": "npc:rejected-target",
            "kind": "npc",
            "role": "npc",
            "state": {
                "memory_state": "rejected",
                "identity_canon_state": "rejected",
            },
        }
    )
    monkeypatch.setattr(
        kernel,
        "load_world_graph_revision",
        lambda *_args, **_kwargs: pinned_store.model_copy(
            update={"nodes": {**pinned_store.nodes, rejected.node_id: rejected}}
        ),
    )
    package = _response_package(plan)
    _reseal_bind_to_target(package, target_node_id="npc:rejected-target")
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"


def test_verify_rejects_resealed_run_id_rewrite(tmp_path: Path) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    package["runId"] = "extraction-run:forged"
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "run_id" in str(exc.value)


def test_verify_rejects_fully_resealed_source_revision_rewrite(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    forged_revision = "sha256:" + ("a" * 64)
    forged_digest = forged_revision.removeprefix("sha256:")
    package["sourceRevisionId"] = forged_revision
    effect = package["effect"]
    effect["contribution_meta"]["source_revision_id"] = forged_revision
    for bucket in ("accepted_proposals", "rejected_assertions"):
        for assertion in effect[bucket]:
            old_id = assertion["assertion_id"]
            assertion["source_revision_id"] = forged_revision
            for artifact in assertion["value"].get("source_artifacts") or []:
                artifact["content_sha256"] = forged_digest
            candidate_id = next(
                candidate
                for candidate, ids in effect["candidate_effect_map"].items()
                if old_id in ids
            )
            _replace_assertion(
                effect,
                old_id=old_id,
                assertion=assertion,
                candidate_id=candidate_id,
            )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "source_revision_id" in str(exc.value)


def test_verify_rejects_fully_resealed_campaign_scope_rewrite(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    forged_campaign = "campaign:forged-scope"
    effect = package["effect"]
    effect["contribution_meta"]["campaign_scope"] = forged_campaign
    for bucket in ("accepted_proposals", "rejected_assertions"):
        for assertion in effect[bucket]:
            old_id = assertion["assertion_id"]
            assertion["campaign_scope"] = forged_campaign
            for artifact in assertion["value"].get("source_artifacts") or []:
                artifact["campaign_id"] = forged_campaign
            candidate_id = next(
                candidate
                for candidate, ids in effect["candidate_effect_map"].items()
                if old_id in ids
            )
            _replace_assertion(
                effect,
                old_id=old_id,
                assertion=assertion,
                candidate_id=candidate_id,
            )
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "campaign_scope" in str(exc.value)


def test_verify_rejects_world_id_context_mismatch(tmp_path: Path) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    package["worldId"] = "world:forged"
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "world_id" in str(exc.value)


def test_verify_rejects_parent_revision_context_mismatch(tmp_path: Path) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    package["parentRevisionId"] = "revision:forged-parent"
    _reseal_package(package)
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "parent_revision_id" in str(exc.value)


def test_verify_rejects_summary_count_rewrite_without_effect_mutation(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    package["summary"] = {
        **package["summary"],  # type: ignore[dict-item]
        "accepted_assertion_count": 0,
        "rejected_candidate_count": 500,
    }
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "summary" in str(exc.value)


def test_verify_rejects_inserted_diagnostics_without_effect_mutation(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    package["diagnostics"] = list(package["diagnostics"]) + ["everything is unsafe"]  # type: ignore[operator]
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "diagnostics" in str(exc.value)


def test_verify_rejects_omitted_confirmable_without_effect_mutation(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    del package["confirmable"]
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "confirmable" in str(exc.value)


def test_verify_rejects_rewritten_confirmable_reason_without_effect_mutation(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    package["confirmableReason"] = "ready to commit"
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "plan_verification_failed"
    assert "confirmable_reason" in str(exc.value)


def test_verify_propagates_stale_parent_revision_from_rebuild(
    tmp_path: Path,
) -> None:
    plan, preview, inputs = _build(tmp_path)
    package = _response_package(plan)
    world_root = inputs["world_root"]
    head, _revision, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    kernel.publish_world_graph_revision(
        world_root,  # type: ignore[arg-type]
        WORLD_ID,
        store,
        operation_ids=["op:worldbuilding-write-plan-stale-parent-test"],
        expected_parent_revision_id=head.head_revision_id,
    )
    with pytest.raises(WorldbuildingWritePlanError) as exc:
        _verify(package, inputs, preview)
    assert exc.value.code == "stale_parent_revision"
    assert exc.value.status_code == 409


def test_materialize_contribution_matches_verified_effect(tmp_path: Path) -> None:
    plan, preview, inputs = _build(tmp_path)
    verified = _verify(_response_package(plan), inputs, preview)
    contribution = materialize_worldbuilding_contribution(
        world_id=verified["world_id"],
        plan_digest=verified["plan_digest"],
        effect=verified["effect"],
    )
    assert contribution.contribution_id == kernel.compute_contribution_id(
        world_id=verified["world_id"],
        source_kind="source_extraction",
        source_artifact_id=plan.source_artifact_id,
        source_revision_id=plan.source_revision_id,
        extraction_profile=plan.extraction_profile,
        authored_by="live_control:worldbuilding_write_plan",
        proposal_digest=plan.plan_digest,
    )
    assert contribution.authored_by == "live_control:worldbuilding_write_plan"
    assert contribution.source_kind == "source_extraction"
    assert [item.assertion_id for item in contribution.accepted_assertions] == [
        item["assertion_id"] for item in plan.effect["accepted_proposals"]
    ]


def test_same_plan_materialize_yields_stable_contribution_identity(
    tmp_path: Path,
) -> None:
    plan, _preview, _inputs = _build(tmp_path)
    contrib_a = materialize_worldbuilding_contribution(
        world_id=plan.world_id,
        plan_digest=plan.plan_digest,
        effect=plan.effect,
    )
    contrib_b = materialize_worldbuilding_contribution(
        world_id=plan.world_id,
        plan_digest=plan.plan_digest,
        effect=plan.effect,
    )
    assert contrib_a.contribution_id == contrib_b.contribution_id
    assert kernel.compute_contribution_source_payload_sha256(
        contrib_a
    ) == kernel.compute_contribution_source_payload_sha256(contrib_b)


def test_different_parent_yields_different_contribution_id(tmp_path: Path) -> None:
    plan_first, _preview, inputs = _build(tmp_path)
    world_root = inputs["world_root"]
    head, _revision, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    kernel.publish_world_graph_revision(
        world_root,  # type: ignore[arg-type]
        WORLD_ID,
        store,
        operation_ids=["op:worldbuilding-write-plan-parent-advance"],
        expected_parent_revision_id=head.head_revision_id,
    )
    inputs["parent"] = kernel.open_current_world_graph(world_root, WORLD_ID)[
        0
    ].head_revision_id
    plan_second = _build_from_inputs(inputs)
    assert plan_first.decision_digest == plan_second.decision_digest
    assert plan_first.plan_digest != plan_second.plan_digest
    first = materialize_worldbuilding_contribution(
        world_id=plan_first.world_id,
        plan_digest=plan_first.plan_digest,
        effect=plan_first.effect,
    )
    second = materialize_worldbuilding_contribution(
        world_id=plan_second.world_id,
        plan_digest=plan_second.plan_digest,
        effect=plan_second.effect,
    )
    assert first.contribution_id != second.contribution_id


def test_different_rebuilt_effect_yields_different_contribution_id(
    tmp_path: Path, monkeypatch
) -> None:
    alpha_root = tmp_path / "alpha"
    beta_root = tmp_path / "beta"
    plan_aliases_a, _, _, _ = _bind_fixture(
        alpha_root, monkeypatch, aliases=["Alias Alpha"]
    )
    plan_aliases_b, _, _, _ = _bind_fixture(
        beta_root, monkeypatch, aliases=["Alias Beta"]
    )
    assert plan_aliases_a.decision_digest == plan_aliases_b.decision_digest
    assert plan_aliases_a.plan_digest != plan_aliases_b.plan_digest
    contrib_a = materialize_worldbuilding_contribution(
        world_id=plan_aliases_a.world_id,
        plan_digest=plan_aliases_a.plan_digest,
        effect=plan_aliases_a.effect,
    )
    contrib_b = materialize_worldbuilding_contribution(
        world_id=plan_aliases_b.world_id,
        plan_digest=plan_aliases_b.plan_digest,
        effect=plan_aliases_b.effect,
    )
    assert contrib_a.contribution_id != contrib_b.contribution_id
