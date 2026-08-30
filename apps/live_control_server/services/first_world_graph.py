"""First-world reviewed graph helpers (storage-neutral plan materialization).



Owns managed-world admission, workspace lineage cross-check, and create_new-only

contribution materialization. Native initialization state comes from

``WorldGraphInitializationAuthority.probe()``. Filesystem classification remains

only for explicit buddy_files compatibility.

"""



from __future__ import annotations



import hashlib

import json

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Literal, Mapping, Sequence



from apps.live_control_server.services.source_artifact_registry import (

    get_source_artifact,

)

from apps.live_control_server.services.world_container_registry import (

    WorldContainerRegistryError,

    get_world_container,

)

from apps.live_control_server.services.workspace_document_registry import (

    get_workspace_document_snapshot,

)

from graph_memory.candidate_graph_preview import CandidateGraphPreview

from graph_memory.candidate_graph_to_contribution import (

    CandidateGraphMappingError,

    require_single_verified_source_artifact,

)

from graph_memory.candidate_semantic_promote_matrix import semantic_diagnostics

from apps.live_control_server.models.world_graph_contribution_models import GraphContribution

from apps.live_control_server.models.world_graph_contributions import (

    compute_contribution_payload_sha256,

    create_graph_contribution,

)

from graph_memory.worldbuilding_write_plan import (

    WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY,

    WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,

    WORLDBUILDING_EXTRACTION_PROFILE,

    WorldbuildingDispositionInput,

    WorldbuildingWritePlanError,

    _map_edge,

    _map_node,

    _validate_dispositions,

    materialize_worldbuilding_contribution,

)



FIRST_WORLD_PLAN_SCHEMA = "dmb_first_world_graph_plan_v1"



FirstWorldGraphState = Literal[

    "uninitialized",

    "initialized",

    "unreadable",

    "unmanaged",

]



_FIRST_WORLD_NODE_DECISIONS = frozenset({"create_new", "reject"})

_FIRST_WORLD_EDGE_DECISIONS = frozenset({"accept", "reject"})

_FIXED_PRODUCED_AT = "1970-01-01T00:00:00Z"





@dataclass(frozen=True)

class FirstWorldLineage:

    world_id: str

    source_artifact_id: str

    source_revision_id: str

    workspace_document_id: str

    workspace_document_revision: str

    campaign_scope: str | None

    content_sha256: str





@dataclass(frozen=True)

class FirstWorldCapability:

    world_id: str | None

    world_state: FirstWorldGraphState | None

    eligible: bool

    reason: str | None





@dataclass(frozen=True)

class FirstWorldMaterializedPlan:

    decision_digest: str

    plan_digest: str

    plan_id: str

    effect: dict[str, Any]

    summary: dict[str, int]

    contribution: GraphContribution

    accepted_assertion_ids: list[str]

    rejected_assertion_ids: list[str]

    confirmable: bool

    diagnostics: list[str]





def _canonical_json(payload: object) -> str:

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)





def _digest(payload: object) -> str:

    return f"sha256:{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"





def expected_source_root_relpath(world_id: str) -> str:

    return f"corpus/{world_id}-markdown"





def first_world_initialization_id(world_id: str, plan_id: str) -> str:

    """Deterministic DungeonMind initialization identity for one sealed plan."""

    payload = _canonical_json({"world_id": world_id, "plan_id": plan_id})

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return f"dmb:first-world:{digest}"





def admit_managed_world(repo: Path, world_id: str):

    """Fail closed unless W is a managed world with matching source root."""

    cleaned = (world_id or "").strip()

    if not cleaned:

        raise WorldbuildingWritePlanError(

            "first-world publish requires a non-blank world_id",

            code="world_id_required",

            status_code=422,

        )

    try:

        record = get_world_container(repo, cleaned)

    except WorldContainerRegistryError as exc:

        raise WorldbuildingWritePlanError(

            f"world {cleaned!r} is not a managed world",

            code="world_unmanaged",

            status_code=422,

        ) from exc

    expected = expected_source_root_relpath(cleaned)

    if record.world_id != cleaned:

        raise WorldbuildingWritePlanError(

            "managed world record world_id mismatch",

            code="world_unmanaged",

            status_code=422,

        )

    if record.source_root_relpath != expected:

        raise WorldbuildingWritePlanError(

            f"managed world source root must be {expected!r}",

            code="world_unmanaged",

            status_code=422,

        )

    source_root = (repo / record.source_root_relpath).resolve()

    if not source_root.is_dir():

        raise WorldbuildingWritePlanError(

            f"managed world source root does not exist: {expected}",

            code="world_unmanaged",

            status_code=422,

        )

    return record





def classify_world_graph_state(world_root: Path, world_id: str) -> FirstWorldGraphState:

    """Buddy filesystem world-state classifier — retired in D.3B.



    First-world capability uses DungeonMind initialization ports; this helper

    remains only as an explicit fail-closed stub for any stray caller.

    """

    del world_root, world_id

    return "unreadable"





def cross_check_workspace_lineage(

    repo: Path,

    *,

    source_artifact_id: str,

    expected_world_id: str,

) -> FirstWorldLineage:

    """Prove SourceArtifact ↔ active worldbuilding workspace document lineage."""

    artifact = get_source_artifact(repo, source_artifact_id)

    document_id = (artifact.workspace_document_id or "").strip()

    if not document_id:

        raise WorldbuildingWritePlanError(

            "SourceArtifact is missing workspace_document_id lineage",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    if artifact.workspace_document_revision is None:

        raise WorldbuildingWritePlanError(

            "SourceArtifact is missing workspace_document_revision lineage",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    artifact_world = (artifact.world_id or "").strip()

    if artifact_world != expected_world_id:

        raise WorldbuildingWritePlanError(

            "SourceArtifact world_id does not match resolved first-world target",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    artifact_campaign = (artifact.campaign_id or "").strip()

    if artifact_campaign != expected_world_id:

        raise WorldbuildingWritePlanError(

            "SourceArtifact campaign_id must equal world_id for first-world publish",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    snapshot = get_workspace_document_snapshot(repo, document_id)

    record = snapshot.record

    if record.status != "active":

        raise WorldbuildingWritePlanError(

            "workspace document is not active",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    if record.kind != "worldbuilding_source":

        raise WorldbuildingWritePlanError(

            "workspace document is not an active worldbuilding_source",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    record_world = (record.world_id or "").strip()

    if record_world != expected_world_id:

        raise WorldbuildingWritePlanError(

            "workspace document world_id does not match SourceArtifact world_id",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    record_campaign = (record.campaign_id or "").strip()

    if record_campaign != expected_world_id:

        raise WorldbuildingWritePlanError(

            "workspace document campaign_id must equal world_id for first-world publish",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    if int(record.revision) != int(artifact.workspace_document_revision):

        raise WorldbuildingWritePlanError(

            "workspace document revision disagrees with SourceArtifact lineage",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    artifact_digest = (artifact.content_sha256 or "").removeprefix("sha256:").strip().lower()

    snapshot_digest = (snapshot.content_sha256 or "").removeprefix("sha256:").strip().lower()

    if not artifact_digest or artifact_digest != snapshot_digest:

        raise WorldbuildingWritePlanError(

            "workspace document content digest disagrees with SourceArtifact",

            code="workspace_lineage_mismatch",

            status_code=422,

        )

    source_revision_id = (

        artifact.content_sha256

        if (artifact.content_sha256 or "").startswith("sha256:")

        else f"sha256:{artifact_digest}"

    )

    return FirstWorldLineage(

        world_id=expected_world_id,

        source_artifact_id=artifact.source_artifact_id,

        source_revision_id=source_revision_id,

        workspace_document_id=document_id,

        workspace_document_revision=str(artifact.workspace_document_revision),

        # First-world publish requires campaign_scope == world_id (fail closed above).

        campaign_scope=expected_world_id,

        content_sha256=artifact_digest,

    )





def resolve_first_world_capability(

    *,

    repo: Path,

    world_root: Path,

    source_domain: str,

    world_id: str | None,

    source_artifact_id: str | None = None,

) -> FirstWorldCapability:

    """Classify exact-run first-world publish eligibility (additive review fields)."""

    if (source_domain or "").strip() != "worldbuilding":

        return FirstWorldCapability(

            world_id=None,

            world_state=None,

            eligible=False,

            reason=None,

        )

    cleaned = (world_id or "").strip() or None

    if cleaned is None:

        return FirstWorldCapability(

            world_id=None,

            world_state=None,

            eligible=False,

            reason="exact SourceArtifact world_id is required for first-world publish",

        )

    try:

        admit_managed_world(repo, cleaned)

    except WorldbuildingWritePlanError:

        return FirstWorldCapability(

            world_id=cleaned,

            world_state="unmanaged",

            eligible=False,

            reason=f"world {cleaned!r} is not a managed world",

        )

    from apps.live_control_server.ports.world_graph_initialization import (

        WorldGraphInitializationError,

    )

    from apps.live_control_server.ports.world_graph_initialization_access import (

        get_world_graph_initialization_authority,

    )



    try:

        probed = get_world_graph_initialization_authority(

            world_root=world_root

        ).probe(cleaned)

    except WorldGraphInitializationError as exc:

        return FirstWorldCapability(

            world_id=cleaned,

            world_state="unreadable",

            eligible=False,

            reason=str(exc),

        )

    state: FirstWorldGraphState

    if probed.state == "initialized":

        state = "initialized"

        return FirstWorldCapability(

            world_id=cleaned,

            world_state=state,

            eligible=False,

            reason="World Graph already exists",

        )

    if probed.state == "unreadable":

        state = "unreadable"

        return FirstWorldCapability(

            world_id=cleaned,

            world_state=state,

            eligible=False,

            reason="World Graph storage exists but is unreadable",

        )

    state = "uninitialized"

    if source_artifact_id:

        try:

            cross_check_workspace_lineage(

                repo,

                source_artifact_id=source_artifact_id,

                expected_world_id=cleaned,

            )

        except WorldbuildingWritePlanError as exc:

            return FirstWorldCapability(

                world_id=cleaned,

                world_state=state,

                eligible=False,

                reason=str(exc),

            )

    return FirstWorldCapability(

        world_id=cleaned,

        world_state=state,

        eligible=True,

        reason=None,

    )





def _require_first_world_decisions(

    disposition_map: Mapping[str, tuple[str, str | None]],

    *,

    nodes: Mapping[str, Any],

    edges: Mapping[str, Any],

) -> None:

    for assertion_id, (decision, target) in disposition_map.items():

        if target is not None:

            raise WorldbuildingWritePlanError(

                "first-world decisions must not include bind targets",

                code="invalid_disposition",

            )

        if assertion_id in nodes and decision not in _FIRST_WORLD_NODE_DECISIONS:

            raise WorldbuildingWritePlanError(

                f"node {assertion_id!r} does not permit decision {decision!r} "

                "for first-world publish",

                code="invalid_disposition",

            )

        if assertion_id in edges and decision not in _FIRST_WORLD_EDGE_DECISIONS:

            raise WorldbuildingWritePlanError(

                f"edge {assertion_id!r} does not permit decision {decision!r} "

                "for first-world publish",

                code="invalid_disposition",

            )





def materialize_first_world_plan(

    *,

    preview: CandidateGraphPreview,

    world_id: str,

    run_id: str,

    source_artifact_id: str,

    source_revision_id: str,

    source_uri: str,

    extraction_profile: str,

    campaign_scope: str | None,

    workspace_document_id: str,

    workspace_document_revision: str,

    dispositions: Sequence[WorldbuildingDispositionInput | Mapping[str, Any]],

) -> FirstWorldMaterializedPlan:

    """Materialize a sealed first-world plan with storage-neutral validation."""

    world = (world_id or "").strip()

    run = (run_id or "").strip()

    artifact = (source_artifact_id or "").strip()

    revision = (source_revision_id or "").strip()

    uri = (source_uri or "").strip()

    profile = (extraction_profile or "").strip()

    if not world or not run or not artifact or not revision or not uri:

        raise WorldbuildingWritePlanError(

            "first-world plan identity fields are incomplete",

            code="invalid_request",

        )

    if profile != WORLDBUILDING_EXTRACTION_PROFILE:

        raise WorldbuildingWritePlanError(

            "first-world plans require the exact BLD-08 extraction profile",

            code="unsupported_worldbuilding_profile",

        )

    if preview.session_id not in (None, ""):

        raise WorldbuildingWritePlanError(

            "worldbuilding candidate must keep session_id null",

            code="run_scope_mismatch",

        )



    disposition_map, decision_snapshot, nodes, edges = _validate_dispositions(

        preview, dispositions

    )

    _require_first_world_decisions(disposition_map, nodes=nodes, edges=edges)

    accepted_create_new_ids: set[str] = set()



    try:

        require_single_verified_source_artifact(

            preview=preview,

            verified_artifact_id=artifact,

            nodes=list(nodes.values()),

            edges=list(edges.values()),

        )

    except CandidateGraphMappingError as exc:

        raise WorldbuildingWritePlanError(

            str(exc),

            code="mapping_error",

            status_code=422,

        ) from exc



    accepted = []

    rejected = []

    node_id_map: dict[str, str] = {}

    identity_snapshot: dict[str, str] = {}

    candidate_effect_map: dict[str, list[str]] = {}

    diagnostics: list[str] = []



    for node_id in sorted(nodes):

        node = nodes[node_id]

        decision, _target = disposition_map[node_id]

        diagnostics.extend(semantic_diagnostics(node))

        if decision == "create_new":

            if node_id in accepted_create_new_ids:

                raise WorldbuildingWritePlanError(

                    f"create_new node ID {node_id!r} is duplicated in this plan",

                    code="new_node_id_conflict",

                    status_code=409,

                )

            accepted_create_new_ids.add(node_id)

            assertion = _map_node(

                node,

                source_revision_id=revision,

                source_artifact_id=artifact,

                campaign_scope=campaign_scope,

                source_uri=uri,

                acceptance_state="accepted",

                identity_resolution_outcome="created_new",

            )

            accepted.append(assertion)

            candidate_effect_map[node_id] = [assertion.assertion_id]

            node_id_map[node_id] = node_id

            identity_snapshot[node_id] = "created_new"

        else:

            assertion = _map_node(

                node,

                source_revision_id=revision,

                source_artifact_id=artifact,

                campaign_scope=campaign_scope,

                source_uri=uri,

                acceptance_state="rejected",

                identity_resolution_outcome="rejected_by_operator",

            )

            rejected.append(assertion)

            candidate_effect_map[node_id] = [assertion.assertion_id]

            identity_snapshot[node_id] = "rejected_by_operator"



    for edge_id in sorted(edges):

        edge = edges[edge_id]

        decision, _target = disposition_map[edge_id]

        diagnostics.extend(semantic_diagnostics(edge))

        if decision == "accept":

            from_decision = disposition_map.get(edge.from_node_id)

            to_decision = disposition_map.get(edge.to_node_id)

            if (

                from_decision is None

                or to_decision is None

                or from_decision[0] != "create_new"

                or to_decision[0] != "create_new"

                or edge.from_node_id not in node_id_map

                or edge.to_node_id not in node_id_map

            ):

                raise WorldbuildingWritePlanError(

                    f"accepted edge {edge.edge_id!r} has an unresolved endpoint",

                    code="edge_endpoint_unresolved",

                )

            assertion = _map_edge(

                edge,

                source_revision_id=revision,

                source_artifact_id=artifact,

                campaign_scope=campaign_scope,

                source_uri=uri,

                acceptance_state="accepted",

                identity_resolution_outcome="accepted_by_operator",

                node_id_map=node_id_map,

            )

            accepted.append(assertion)

            candidate_effect_map[edge_id] = [assertion.assertion_id]

            identity_snapshot[edge_id] = "accepted_by_operator"

        else:

            assertion = _map_edge(

                edge,

                source_revision_id=revision,

                source_artifact_id=artifact,

                campaign_scope=campaign_scope,

                source_uri=uri,

                acceptance_state="rejected",

                identity_resolution_outcome="rejected_by_operator",

            )

            rejected.append(assertion)

            candidate_effect_map[edge_id] = [assertion.assertion_id]

            identity_snapshot[edge_id] = "rejected_by_operator"



    decision_digest = _digest(decision_snapshot)

    provisional = create_graph_contribution(

        world_id=world,

        source_kind=WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,  # type: ignore[arg-type]

        source_artifact_id=artifact,

        source_revision_id=revision,

        extraction_profile=profile,

        campaign_scope=campaign_scope,

        accepted_assertions=accepted,

        rejected_assertions=rejected,

        unresolved_mentions=[],

        authored_by=WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY,

        proposal_digest=decision_digest,

        produced_at=_FIXED_PRODUCED_AT,

        diagnostics=[],

    )

    effect: dict[str, Any] = {

        "contribution_meta": {

            "source_kind": WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,

            "source_artifact_id": artifact,

            "source_revision_id": revision,

            "extraction_profile": profile,

            "campaign_scope": campaign_scope,

            "authored_by": WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY,

        },

        "accepted_proposals": [

            assertion.model_dump(mode="json")

            for assertion in provisional.accepted_assertions

        ],

        "rejected_assertions": [

            assertion.model_dump(mode="json")

            for assertion in provisional.rejected_assertions

        ],

        "unresolved_mentions": [],

        "deferred_candidate_ids": [],

        "node_id_map": dict(sorted(node_id_map.items())),

        "identity_outcome_snapshot": dict(sorted(identity_snapshot.items())),

        "candidate_effect_map": {

            candidate_id: list(assertion_ids)

            for candidate_id, assertion_ids in sorted(candidate_effect_map.items())

        },

        "decision_snapshot": decision_snapshot,

    }

    plan_identity = {

        "schema": FIRST_WORLD_PLAN_SCHEMA,

        "world_id": world,

        "run_id": run,

        "source_domain": "worldbuilding",

        "source_artifact_id": artifact,

        "source_revision_id": revision,

        "workspace_document_id": workspace_document_id,

        "workspace_document_revision": workspace_document_revision,

        "extraction_profile": profile,

        "candidate_preview_id": preview.preview_id,

        "candidate_schema": preview.schema,

        "candidate_version": preview.version,

        "decision_snapshot": decision_snapshot,

        "effect": effect,

    }

    plan_digest = _digest(plan_identity)

    plan_id = f"first-world-graph-plan:{plan_digest.removeprefix('sha256:')[:24]}"

    contribution = materialize_worldbuilding_contribution(

        world_id=world,

        plan_digest=plan_digest,

        effect=effect,

    )

    accepted_ids = [item.assertion_id for item in contribution.accepted_assertions]

    rejected_ids = [item.assertion_id for item in contribution.rejected_assertions]

    confirmable = len(accepted_ids) > 0

    if not confirmable:

        diagnostics.append("zero_accepted_assertions:first_world_not_confirmable")

    # Bind payload digest into diagnostics for confirm self-checks.

    payload_sha = compute_contribution_payload_sha256(contribution)

    summary = {

        "create_new_node_count": sum(

            disposition_map[node_id][0] == "create_new" for node_id in nodes

        ),

        "accepted_edge_count": sum(

            disposition_map[edge_id][0] == "accept" for edge_id in edges

        ),

        "rejected_candidate_count": sum(

            disposition_map[assertion_id][0] == "reject"

            for assertion_id in set(nodes) | set(edges)

        ),

        "accepted_assertion_count": len(accepted_ids),

    }

    diagnostics.append(f"contribution_payload_sha256={payload_sha}")

    return FirstWorldMaterializedPlan(

        decision_digest=decision_digest,

        plan_digest=plan_digest,

        plan_id=plan_id,

        effect=effect,

        summary=summary,

        contribution=contribution,

        accepted_assertion_ids=accepted_ids,

        rejected_assertion_ids=rejected_ids,

        confirmable=confirmable,

        diagnostics=diagnostics,

    )
