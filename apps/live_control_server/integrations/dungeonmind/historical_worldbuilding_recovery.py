"""Authenticate retained Worldbuilding requests before immutable receipt recovery.

Original producer output is reconstructed from authenticated retained effect, not
from a current preview or from recorded terminal answers. This module grants no
permission to publish when a terminal receipt is absent.
"""
from __future__ import annotations

from typing import Any

from apps.live_control_server.models.extract_promote import (
    WORLD_BUILDING_WRITE_PLAN_SCHEMA,
    WorldbuildingWritePlanResponse,
)
from apps.live_control_server.services.extract_promote import ExtractPromoteError


def _invalid(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Original Worldbuilding confirmation failed verification: {reason}.",
        code="plan_verification_failed", status_code=409,
    )


def _unsupported(reason: str) -> ExtractPromoteError:
    return ExtractPromoteError(
        f"Historical Worldbuilding recipe is unsupported; retain the original request: {reason}.",
        code="publication_history_unsupported", status_code=409,
    )


def authenticate_original_plan(plan: WorldbuildingWritePlanResponse) -> dict[str, Any]:
    """Prove the full retained plan identity and original prepare signature.

    No current World/source/head/vocabulary service is consulted. The vocabulary
    references below name the historical versions explicitly. This authenticates
    an original request; it cannot replace complete terminal correspondence.
    """
    from graph_memory.worldbuilding_write_plan import (
        WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY, WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,
        WorldbuildingWritePlanError, _canonical_effect, _digest,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import _require_prepare_binding

    if plan.schema_ != WORLD_BUILDING_WRITE_PLAN_SCHEMA or plan.version != 2:
        raise _unsupported("plan generation")
    if (plan.effect.identity_authority is None or plan.publication_binding is None
            or plan.source_admission is None or plan.native_vocabulary_binding is None):
        raise _unsupported("missing original sealed bindings")
    try:
        effect = _canonical_effect(plan.effect.model_dump(mode="json", by_alias=True))
    except WorldbuildingWritePlanError as exc:
        raise _invalid("canonical effect") from exc
    identity = {
        "world_id": plan.world_id, "parent_revision_id": plan.parent_revision_id,
        "run_id": plan.run_id, "source_domain": plan.source_domain,
        "source_artifact_id": plan.source_artifact_id, "source_revision_id": plan.source_revision_id,
        "extraction_profile": plan.extraction_profile, "candidate_preview_id": plan.candidate_preview_id,
        "candidate_schema": plan.candidate_schema, "candidate_version": plan.candidate_version,
        "decision_snapshot": effect["decision_snapshot"], "effect": effect,
    }
    digest = _digest(identity)
    if (digest != plan.plan_digest
            or plan.plan_id != f"worldbuilding-write-plan:{digest.removeprefix('sha256:')[:24]}"
            or plan.decision_digest != _digest(effect["decision_snapshot"])):
        raise _invalid("original plan or decision digest")
    # Authenticate every binding before interpreting it or using it for I/O.
    _require_prepare_binding(plan, effect["identity_authority"])
    meta, admission, binding = effect["contribution_meta"], plan.source_admission, plan.publication_binding
    if (meta["source_kind"] != WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND
            or meta["authored_by"] != WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY
            or meta["source_artifact_id"] != plan.source_artifact_id
            or meta["source_revision_id"] != plan.source_revision_id
            or meta["extraction_profile"] != plan.extraction_profile
            or meta["campaign_scope"] is not None
            or binding.native_world_id != plan.world_id
            or binding.source_artifact_id != plan.source_artifact_id
            or admission.source_artifact_id != plan.source_artifact_id
            or admission.buddy_source_revision_id != plan.source_revision_id
            or admission.content_sha256 != binding.source_sha256):
        raise _invalid("original source, World or contribution bindings")
    from dungeonmind_dnd.application.world_object_vocabulary import builtin_world_object_v6_vocabulary_ref
    from dungeonmind_dnd.application.world_property_vocabulary import builtin_world_property_v4_vocabulary_ref

    vocabulary = plan.native_vocabulary_binding
    if (vocabulary.world_object_vocabulary != builtin_world_object_v6_vocabulary_ref().model_dump(mode="json")
            or vocabulary.world_property_vocabulary != builtin_world_property_v4_vocabulary_ref().model_dump(mode="json")):
        raise _unsupported("historical vocabulary pair")
    decisions = {item["assertion_id"]: item for item in effect["decision_snapshot"]}
    effect_map = effect["candidate_effect_map"]
    if set(decisions) != set(effect_map):
        raise _invalid("decision/effect coverage")
    accepted = {item["assertion_id"]: item for item in effect["accepted_proposals"]}
    rejected = {item["assertion_id"]: item for item in effect["rejected_assertions"]}
    mapped_ids = [identifier for ids in effect_map.values() for identifier in ids]
    if (len(mapped_ids) != len(set(mapped_ids))
            or len(accepted) != len(effect["accepted_proposals"])
            or len(rejected) != len(effect["rejected_assertions"]) or set(accepted) & set(rejected)
            or {identifier for ids in effect_map.values() for identifier in ids} != set(accepted) | set(rejected)):
        raise _invalid("assertion/effect coverage")
    deferred = {identifier for identifier, item in decisions.items() if item["decision"] == "defer"}
    if set(effect["deferred_candidate_ids"]) != deferred:
        raise _invalid("deferred decision coverage")
    node_decisions = {identifier: item for identifier, item in decisions.items()
                      if item["candidate_kind"] == "node" and item["decision"] in {"create_new", "bind_existing"}}
    expected_nodes = {identifier: identifier if item["decision"] == "create_new" else item["target_node_id"]
                      for identifier, item in node_decisions.items()}
    if effect["node_id_map"] != expected_nodes:
        raise _invalid("original node decision targets")
    outcomes = {"create_new": "created_new", "bind_existing": "human_override",
                "accept": "accepted_by_operator", "reject": "rejected_by_operator", "defer": "deferred_by_operator"}
    expected_outcomes = {identifier: outcomes[item["decision"]] for identifier, item in decisions.items()
                         if item["candidate_kind"] != "source_observation"}
    if effect["identity_outcome_snapshot"] != expected_outcomes:
        raise _invalid("identity disposition snapshot")
    for identifier, decision in decisions.items():
        ids, disposition = effect_map[identifier], decision["decision"]
        partition = rejected if disposition == "reject" else accepted
        if (disposition == "defer" and ids) or any(item not in partition for item in ids):
            raise _invalid("decision/assertion partition")
        kind = decision["candidate_kind"]
        if kind == "edge" and disposition != "defer":
            if (len(ids) != 1 or partition[ids[0]]["assertion_kind"] != "edge"
                    or not isinstance(partition[ids[0]]["value"], dict)
                    or partition[ids[0]]["value"].get("extract_edge_id") != identifier):
                raise _invalid("edge decision/effect ownership")
        if kind == "node" and disposition == "reject":
            if (len(ids) != 1 or rejected[ids[0]]["assertion_kind"] != "node"
                    or rejected[ids[0]]["subject_node_id"] != identifier):
                raise _invalid("rejected node decision/effect ownership")
        if kind == "source_observation" or disposition == "bind_existing":
            if any(partition[item]["assertion_kind"] not in {"attribute", "alias", "evidence_ref"} for item in ids):
                raise _invalid("support-only decision/effect ownership")
        if disposition == "create_new" and (len(ids) != 1 or accepted[ids[0]]["assertion_kind"] != "node"):
            raise _invalid("create-new node assertion coverage")
        if decision["candidate_kind"] == "node" and disposition in {"create_new", "bind_existing"}:
            target = effect["node_id_map"].get(identifier)
            if not target or any(accepted[item]["subject_node_id"] != target for item in ids):
                raise _invalid("node target correspondence")
    for assertion in [*accepted.values(), *rejected.values()]:
        if (assertion["source_artifact_id"] != meta["source_artifact_id"]
                or assertion["source_revision_id"] != meta["source_revision_id"]
                or assertion["campaign_scope"] != meta["campaign_scope"]):
            raise _invalid("assertion source correspondence")
    return effect



def reconstruct_original_mapping(plan: WorldbuildingWritePlanResponse) -> tuple[Any, Any]:
    """Reproduce the authenticated typed-V3 producer without current source reads.

    Returns the original Buddy contribution and the pre-review Core mapping.
    Full candidate/review/receipt equality remains a separate required proof.
    """
    import copy
    import json
    from types import SimpleNamespace
    from graph_memory.worldbuilding_write_plan import materialize_worldbuilding_contribution
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        CURRENT_WORLD_BUILDING_V6_TARGET, resolve_buddy_predicate_mapping_v4,
    )
    from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
        ContributionMappingError, map_worldbuilding_extraction_contribution_v3,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import _BuddyEvidenceRecord
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import _worldbuilding_expressible
    from apps.live_control_server.ports.world_graph_authority import WorldGraphAuthorityError

    effect = copy.deepcopy(authenticate_original_plan(plan))
    decisions = {item["assertion_id"]: item for item in effect["decision_snapshot"]}
    for assertion in effect["accepted_proposals"]:
        if assertion["assertion_kind"] != "edge" or assertion["predicate"] != "governs":
            continue
        value = assertion["value"]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise _invalid("governs effect value") from exc
        value = dict(value) if isinstance(value, dict) else {}
        edge_id = str(value.get("extract_edge_id") or "").strip()
        decision = decisions.get(edge_id)
        if (decision is None or decision["candidate_kind"] != "edge" or decision["decision"] != "accept"
                or assertion["assertion_id"] not in effect["candidate_effect_map"].get(edge_id, [])):
            raise _invalid("governs decision/effect binding")
        mapping = resolve_buddy_predicate_mapping_v4("governs", target=CURRENT_WORLD_BUILDING_V6_TARGET)
        if mapping != ("dnd5e:governs", False):
            raise _unsupported("governs historical transformation")
        # The original producer's endpoint admission used the now-unavailable
        # preview. Reproduce its output from the signed effect, not that check.
        assertion["predicate"] = mapping[0]
        assertion["value"] = {**value, "buddy_predicate": "governs", "dm_predicate": mapping[0],
                              "native_vocabulary_binding": plan.native_vocabulary_binding.model_dump(mode="json", by_alias=True)}
    contribution = materialize_worldbuilding_contribution(
        world_id=plan.world_id, plan_digest=plan.plan_digest, effect=effect,
    )
    try:
        wire_contribution = _worldbuilding_expressible(contribution)
    except WorldGraphAuthorityError as exc:
        raise _invalid("original identity outcome transport") from exc
    admission = plan.source_admission
    pair = (plan.source_artifact_id, plan.source_revision_id)
    locator = str(admission.source_locator or "").strip()
    if not locator:
        raise _invalid("sealed immutable source locator")
    records: dict[str, Any] = {}
    for assertion in [*contribution.accepted_assertions, *contribution.rejected_assertions]:
        rows = assertion.value.get("evidence") if isinstance(assertion.value, dict) else None
        ids = list(assertion.evidence_ref_ids)
        if (not ids or len(set(ids)) != len(ids) or any(not item.strip() for item in ids)
                or not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)):
            raise _invalid("typed extraction evidence recipe")
        by_id = {str(row.get("evidence_ref_id") or ""): row for row in rows}
        if len(by_id) != len(rows) or set(by_id) != set(ids):
            raise _invalid("typed extraction evidence coverage")
        for raw_id in ids:
            row = by_id[raw_id]
            span = str(row.get("source_span_ref_id") or "").strip()
            if (row.get("source_artifact_id") != pair[0]
                    or row.get("source_revision_id") not in (None, pair[1])
                    or row.get("source_content_sha256") not in (None, admission.content_sha256)
                    or row.get("source_domain") != "worldbuilding" or not span):
                raise _invalid("authenticated evidence source/span correspondence")
            record = _BuddyEvidenceRecord(
                evidence_ref_id=raw_id, source_artifact_id=pair[0], source_domain="worldbuilding",
                evidence_role="support", can_open_source=bool(locator), can_highlight_span=bool(span),
                locator=span or locator, uri=locator, source_span_ref_id=span,
            )
            if raw_id in records and records[raw_id] != record:
                raise _invalid("operation-wide evidence identity collision")
            records[raw_id] = record
    try:
        mapped = map_worldbuilding_extraction_contribution_v3(
            SimpleNamespace(evidence=records), wire_contribution, {pair: admission.source_revision_id},
        )
    except ContributionMappingError as exc:
        raise _invalid("typed extraction mapping") from exc
    return contribution, mapped
