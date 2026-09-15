"""Explicit, source-backed recap World genesis.

Prepare is deliberately inert.  Confirm rematerializes the canonical registry
before delegating the only durable action to the reviewed DungeonMind
zero-parent initializer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from apps.live_control_server import config as live_config
from apps.live_control_server.models.recap_world_genesis import (
    RECAP_WORLD_GENESIS_PLAN_SCHEMA,
    RecapWorldGenesisConfirmRequest,
    RecapWorldGenesisPlan,
    RecapWorldGenesisPrepareRequest,
    RecapWorldGenesisReceipt,
)
from apps.live_control_server.models.world_graph_contributions import build_assertion
from apps.live_control_server.models.world_graph_contributions import (
    create_graph_contribution,
    compute_contribution_payload_sha256,
)
from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationAuthority,
    WorldGraphInitializationError,
    WorldGraphInitializationRequest,
)
from apps.live_control_server.ports.world_graph_initialization_access import (
    get_world_graph_initialization_authority,
)
from apps.live_control_server.services.first_world_graph import first_world_initialization_id
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
from graph_memory.party_context import (
    CAMPAIGN_CORPUS,
    PARTY_REGISTRY_SCHEMAS,
    build_party_context_for_campaign,
    party_registry_path,
)
from graph_memory.standing_context_partition import party_registry_artifact_id


class RecapWorldGenesisError(ValueError):
    """Fail-closed service error; no caller data is treated as source authority."""

    def __init__(self, message: str, *, code: str) -> None:
        self.code = code
        super().__init__(message)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _exact_pc_roster(registry: dict[str, Any], key: str) -> list[str]:
    """Select only the exact requested key; genesis never carries a roster forward."""
    if str(registry.get("schema") or "") == "party_registry_v2":
        entry = (registry.get("session_rosters") or {}).get(key)
        pcs = entry.get("pcs") if isinstance(entry, dict) else None
    else:
        pcs = (registry.get("session_pc_rosters") or {}).get(key)
    if not isinstance(pcs, list) or not pcs:
        raise RecapWorldGenesisError("baseline roster is missing or empty", code="invalid_registry")
    result = [str(item).strip() for item in pcs]
    if any(not item for item in result) or len(result) != len(set(result)):
        raise RecapWorldGenesisError("baseline roster has blank or duplicate PC slugs", code="invalid_registry")
    return result


def _materialize_plan(
    request: RecapWorldGenesisPrepareRequest,
    *,
    repo: Path,
) -> tuple[RecapWorldGenesisPlan, GraphMemorySourceArtifact, Any]:
    try:
        configured_root, campaign_rel = CAMPAIGN_CORPUS[request.campaign_id]
    except KeyError as exc:
        raise RecapWorldGenesisError(
            f"unknown campaign_id for party registry: {request.campaign_id}", code="unknown_campaign"
        ) from exc
    # Do not let Path.resolve() in the shared campaign helper capture the
    # process cwd: the service's repository root is the authority boundary.
    corpus_root = (repo.resolve() / configured_root).resolve()
    registry_path = party_registry_path(corpus_root, campaign_rel).resolve()
    try:
        raw = registry_path.read_bytes()
        registry = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise RecapWorldGenesisError("canonical party registry is unreadable", code="invalid_registry") from exc
    if not isinstance(registry, dict) or str(registry.get("schema") or "") not in PARTY_REGISTRY_SCHEMAS:
        raise RecapWorldGenesisError("canonical party registry has unsupported schema", code="invalid_registry")
    if str(registry.get("campaign_id") or "") != request.campaign_id:
        raise RecapWorldGenesisError("canonical party registry campaign_id disagrees", code="invalid_registry")
    roster = _exact_pc_roster(registry, request.baseline_roster_key)
    context = build_party_context_for_campaign(
        request.campaign_id, request.baseline_roster_key, corpus_root=corpus_root, campaign_rel=campaign_rel
    )
    members = {member.slug: member for member in context.pcs()}
    if set(members) != set(roster):
        raise RecapWorldGenesisError("baseline roster did not resolve to PC identities only", code="invalid_registry")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        relpath = registry_path.relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise RecapWorldGenesisError("canonical party registry escapes repository", code="invalid_registry") from exc
    source_id = party_registry_artifact_id(request.campaign_id)
    source_revision = f"sha256:{digest}"
    source_uri = f"repo://{relpath}"
    artifact = GraphMemorySourceArtifact(
        source_artifact_id=source_id, source_domain="party_registry", campaign_id=request.campaign_id,
        session_id=None, uri=source_uri, content_sha256=digest, artifact_kind="party_registry",
        document_class="standing_context", authority_state="canonical", world_id=request.world_id,
        lineage={"genesis": "recap_world", "baseline_roster_key": request.baseline_roster_key},
    )
    assertions = []
    for slug in roster:
        member = members[slug]
        node = member.seed_node()
        assertions.append(build_assertion(
            assertion_kind="node", acceptance_state="accepted", subject_node_id=str(node["node_id"]),
            label=member.display_name, value={"kind": "pc", "role": "pc", "aliases": [member.display_name], "source_domains": ["party_registry"], "canon_state": "canonical", "approval_state": "accepted"},
            evidence_ref_ids=[f"evidence:{source_id}:{slug}"], source_artifact_id=source_id,
            source_revision_id=source_revision, campaign_scope=request.campaign_id,
            epistemic_kind="asserted", visibility="gm", identity_resolution_outcome="created_new",
        ))
    contribution = create_graph_contribution(
        world_id=request.world_id, source_kind="standing_context", source_artifact_id=source_id,
        source_revision_id=source_revision, extraction_profile="party_registry_standing",
        campaign_scope=request.campaign_id, accepted_assertions=assertions,
        authored_by="recap_world_genesis", produced_at="1970-01-01T00:00:00Z",
        diagnostics=["recap_world_genesis: PC identity baseline only"],
    )
    semantic = {
        "schema": RECAP_WORLD_GENESIS_PLAN_SCHEMA, "world_id": request.world_id,
        "campaign_id": request.campaign_id, "baseline_roster_key": request.baseline_roster_key,
        "source_artifact_id": source_id, "source_revision_id": source_revision, "source_uri": source_uri,
        "contribution_id": contribution.contribution_id,
        "contribution_payload_sha256": compute_contribution_payload_sha256(contribution),
        "accepted_assertion_ids": [item.assertion_id for item in contribution.accepted_assertions],
        "pc_object_ids": [str(members[slug].seed_node()["node_id"]) for slug in roster],
        "pc_identity_keys": [members[slug].identity_key() for slug in roster],
    }
    plan_digest = _sha256(semantic)
    plan_id = f"recap-world-genesis:{plan_digest[:24]}"
    plan = RecapWorldGenesisPlan(
        plan_id=plan_id, plan_digest=f"sha256:{plan_digest}",
        initialization_id=first_world_initialization_id(request.world_id, plan_id),
        **semantic,
    )
    return plan, artifact, contribution


def _authority_or_default(authority: WorldGraphInitializationAuthority | None) -> WorldGraphInitializationAuthority:
    return authority or get_world_graph_initialization_authority(world_root=live_config.world_graph_root())


def prepare_recap_world_genesis(
    request: RecapWorldGenesisPrepareRequest, *, repo: Path | None = None,
    authority: WorldGraphInitializationAuthority | None = None,
) -> RecapWorldGenesisPlan:
    """Create an inert sealed plan after a non-authoritative pristine probe."""
    current = _authority_or_default(authority)
    try:
        state = current.probe(request.world_id)
    except WorldGraphInitializationError as exc:
        raise RecapWorldGenesisError(str(exc), code=exc.code) from exc
    if state.state != "uninitialized":
        raise RecapWorldGenesisError("World is not pristine for recap genesis", code="already_initialized")
    plan, _artifact, _contribution = _materialize_plan(request, repo=(repo or live_config.repo_root()))
    return plan


def confirm_recap_world_genesis(
    request: RecapWorldGenesisConfirmRequest, *, repo: Path | None = None,
    authority: WorldGraphInitializationAuthority | None = None,
) -> RecapWorldGenesisReceipt:
    """Rematerialize source authority and run the existing atomic initializer."""
    plan = request.plan
    rematerialized, artifact, contribution = _materialize_plan(
        RecapWorldGenesisPrepareRequest(world_id=plan.world_id, campaign_id=plan.campaign_id,
            baseline_roster_key=plan.baseline_roster_key, requested_by="confirm-rematerialization"),
        repo=(repo or live_config.repo_root()),
    )
    if plan != rematerialized:
        raise RecapWorldGenesisError("sealed recap-genesis plan failed rematerialization", code="plan_verification_failed")
    try:
        receipt = _authority_or_default(authority).initialize(WorldGraphInitializationRequest(
            world_id=plan.world_id, campaign_id=plan.campaign_id, initialization_id=plan.initialization_id,
            source_plan_schema=RECAP_WORLD_GENESIS_PLAN_SCHEMA, source_plan_id=plan.plan_id,
            source_plan_sha256=plan.plan_digest, actor=request.confirming_principal,
            source_artifact=artifact, source_revision_token=plan.source_revision_id,
            source_uri=plan.source_uri, reviewed_contribution=contribution,
        ))
    except WorldGraphInitializationError as exc:
        raise RecapWorldGenesisError(str(exc), code=exc.code) from exc
    return RecapWorldGenesisReceipt(
        world_id=plan.world_id, initialization_id=plan.initialization_id, plan_id=plan.plan_id,
        plan_digest=plan.plan_digest, source_artifact_id=plan.source_artifact_id,
        source_revision_id=plan.source_revision_id, contribution_id=plan.contribution_id,
        published_revision_id=receipt.published_revision_id,
        accepted_assertion_ids=plan.accepted_assertion_ids, pc_object_ids=plan.pc_object_ids,
        outcome=receipt.outcome,
    )
