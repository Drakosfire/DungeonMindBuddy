"""Shared prepare/confirm orchestration for extract → World Supergraph promote.


Used by the operator CLI and the live-control HTTP layer. Durable contribution
construction always goes through sealed proposal fields only.
"""


from __future__ import annotations


import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    load_typed_candidate_graph,
    verify_source_revision,
)
from graph_memory.extract_identity_gate import (
    IdentityGateResult,
    build_accepted_contribution_from_multi_slice_proposals,
    gate_candidate_graph_against_head,
)
from apps.live_control_server.models.world_graph_mutation_context import (
    WorldGraphMutationContext,
    mutation_context_from_world_root,
)
from graph_memory.extract_promote_proposal import (
    build_contribution_effect_slice,
    contribution_meta_from_contribution,
    contribution_slice_id_for,
    seal_multi_contribution_promote_proposal,
    verify_promote_proposal,
)
from graph_memory.standing_context_partition import (
    partition_candidate_graph_by_provenance,
    resolve_party_registry_uri,
    stamp_standing_registry_evidence,
)
from graph_memory.extract_promote_review_projection import (
    project_promote_review_as_dicts,
)
from apps.live_control_server.models.world_graph_contributions import (
    create_graph_contribution,
)


def _kernel():
    raise ExtractPromoteWorldError(
        "Buddy World Graph kernel is deleted; use DungeonMind extract-promote paths"
    )


DEFAULT_WORLD_ID = "eldyrwild"
DEFAULT_LIVE_ROOT_NAME = "out"


RETRY_GUIDANCE_DO_NOT_RETRY = "reload_status_inspect_head_do_not_retry_confirm"
RETRY_GUIDANCE_NONE = "none"


class ExtractPromoteLiveWorldError(ValueError):
    """Raised when confirm would mutate the live world root without allow."""


class ExtractPromoteWorldError(ValueError):
    """Raised when the world graph is missing or cannot be opened."""


class ExtractPromoteEmptySelectionError(ValueError):
    """Raised when the caller explicitly selects zero assertions."""


@dataclass(frozen=True)
class ExtractPromotePrepareResult:
    review_package: dict[str, Any]
    proposal_id: str
    proposal_digest: str
    parent_revision_id: str
    world_id: str
    accepted_proposals_count: int
    unresolved_mentions_count: int
    rejected_assertions_count: int
    review_items: list[dict[str, Any]] = field(default_factory=list)
    review_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractPromoteConfirmResult:
    ok: bool
    dry_run: bool
    payload: dict[str, Any]
    failure_reason: str | None = None


@dataclass(frozen=True)
class ExtractPromoteStatusResult:
    world_id: str
    initialized: bool
    world_state: str = "uninitialized"
    head_revision_id: str | None = None
    diagnostics: list[str] = field(default_factory=list)


def default_live_root(*, repo_root: Path) -> Path:
    """CLI default live root (<repo>/out). HTTP uses config.live_world_graph_root."""
    return (repo_root / DEFAULT_LIVE_ROOT_NAME).resolve()


def normalize_assertion_selection(
    assertion_ids: Sequence[str] | None,
) -> tuple[str, ...] | None:
    """Distinguish omitted selection (None → all) from explicit empty (fail closed)."""
    if assertion_ids is None:
        return None
    normalized = tuple(
        str(item).strip() for item in assertion_ids if str(item).strip()
    )
    if not normalized:
        raise ExtractPromoteEmptySelectionError(
            "explicit empty assertion selection refuses to publish; "
            "omit assertionIds to accept the full sealed set, or pass a non-empty list"
        )
    return normalized


def _gate_from_verified(verified: Mapping[str, Any]) -> IdentityGateResult:
    """Rebuild gate state solely from sealed verify() output (no envelope)."""
    meta = verified["contribution_meta"]
    placeholder = create_graph_contribution(
        world_id=str(verified["world_id"]),
        source_kind=meta["source_kind"],
        source_artifact_id=meta["source_artifact_id"],
        source_revision_id=meta["source_revision_id"],
        extraction_profile=meta["extraction_profile"],
        campaign_scope=meta.get("campaign_scope"),
        authored_by=meta["authored_by"],
    )
    return IdentityGateResult(
        parent_revision_id=str(verified["parent_revision_id"]),
        world_id=str(verified["world_id"]),
        contribution=placeholder,
        accepted_proposals=list(verified["accepted_proposals"]),
        unresolved_mentions=list(verified["unresolved_mentions"]),
        rejected_assertions=list(verified["rejected_assertions"]),
        scorer_report={},
        node_id_map=dict(verified["node_id_map"]),
        identity_outcome_snapshot=dict(verified["identity_outcome_snapshot"]),
        diagnostics=[],
        candidate_preview_id=str(verified["candidate_preview_id"]),
        candidate_schema=str(verified["candidate_schema"]),
        candidate_version=str(verified["candidate_version"]),
        source_revision_id=str(verified["source_revision_id"]),
        source_artifact_id=str(verified["source_artifact_id"]),
        verified_source_uri=str(verified["verified_source_uri"]),
    )


def _gate_from_contribution_slice(
    *,
    world_id: str,
    parent_revision_id: str,
    slice_body: Mapping[str, Any],
) -> IdentityGateResult:
    """Rebuild a gate for one sealed contribution slice."""
    from graph_memory.extract_promote_proposal import _parse_assertions, _parse_mentions


    meta = dict(slice_body.get("contribution_meta") or {})
    placeholder = create_graph_contribution(
        world_id=world_id,
        source_kind=str(meta["source_kind"]),  # type: ignore[arg-type]
        source_artifact_id=str(meta["source_artifact_id"]),
        source_revision_id=str(meta["source_revision_id"]),
        extraction_profile=str(meta["extraction_profile"]),
        campaign_scope=meta.get("campaign_scope"),
        authored_by=str(meta["authored_by"]),
    )
    return IdentityGateResult(
        parent_revision_id=parent_revision_id,
        world_id=world_id,
        contribution=placeholder,
        accepted_proposals=_parse_assertions(slice_body.get("accepted_proposals")),
        unresolved_mentions=_parse_mentions(slice_body.get("unresolved_mentions")),
        rejected_assertions=_parse_assertions(slice_body.get("rejected_assertions")),
        scorer_report={},
        node_id_map={
            str(k): str(v) for k, v in dict(slice_body.get("node_id_map") or {}).items()
        },
        identity_outcome_snapshot={
            str(k): str(v)
            for k, v in dict(slice_body.get("identity_outcome_snapshot") or {}).items()
        },
        diagnostics=[],
        candidate_preview_id=str(slice_body.get("candidate_preview_id") or ""),
        candidate_schema=str(slice_body.get("candidate_schema") or ""),
        candidate_version=str(slice_body.get("candidate_version") or ""),
        source_revision_id=str(slice_body.get("source_revision_id") or ""),
        source_artifact_id=str(slice_body.get("source_artifact_id") or ""),
        verified_source_uri=str(slice_body.get("verified_source_uri") or ""),
    )


def get_extract_promote_status(
    *,
    world_root: Path,
    world_id: str = DEFAULT_WORLD_ID,
) -> ExtractPromoteStatusResult:
    """Report whether the configured world has an openable head."""
    root = world_root.resolve()
    world = (world_id or DEFAULT_WORLD_ID).strip() or DEFAULT_WORLD_ID
    try:
        head, _rev, _store = _kernel().open_current_world_graph(root, world)
    except FileNotFoundError as exc:
        return ExtractPromoteStatusResult(
            world_id=world,
            initialized=False,
            world_state="uninitialized",
            head_revision_id=None,
            diagnostics=[f"world_not_initialized:{exc.__class__.__name__}"],
        )
    except PermissionError as exc:
        return ExtractPromoteStatusResult(
            world_id=world,
            initialized=False,
            world_state="unreadable",
            head_revision_id=None,
            diagnostics=[f"world_unreadable:{exc.__class__.__name__}"],
        )
    except Exception as exc:  # noqa: BLE001 — classify remaining open failures
        name = exc.__class__.__name__
        # Missing-head / not-found style errors stay uninitialized; everything
        # else (corruption, parse failures, unexpected IO) is unreadable.
        uninitialized_markers = (
            "NotFound",
            "not found",
            "no graph head",
            "WorldGraphNotFound",
        )
        message = str(exc)
        if any(marker in name or marker in message for marker in uninitialized_markers):
            state = "uninitialized"
            diagnostic = f"world_not_initialized:{name}"
        else:
            state = "unreadable"
            diagnostic = f"world_unreadable:{name}"
        return ExtractPromoteStatusResult(
            world_id=world,
            initialized=False,
            world_state=state,
            head_revision_id=None,
            diagnostics=[diagnostic],
        )
    return ExtractPromoteStatusResult(
        world_id=world,
        initialized=True,
        world_state="initialized",
        head_revision_id=head.head_revision_id,
        diagnostics=[],
    )


def prepare_extract_promote(
    *,
    candidate_graph: Mapping[str, Any],
    source_uri: str,
    source_revision_id: str,
    prepared_by: str,
    world_id: str = DEFAULT_WORLD_ID,
    source_artifact_id: str | None = None,
    campaign_scope: str | None = None,
    extraction_profile: str | None = "current_default",
    node_ids: Sequence[str] | None = None,
    include_edges: bool = True,
    candidate_graph_path: str | None = None,
    repo_root: Path,
    disclose_source_digest: bool = True,
    registry_context_graph: Mapping[str, Any] | None = None,
    mutation_context: WorldGraphMutationContext | None = None,
    world_root: Path | None = None,
) -> ExtractPromotePrepareResult:
    """Gate + seal a typed candidate graph against the pinned world head.


    When standing-context objects are present (sibling registry graph or
    promote-time partition), seals a v3 multi-contribution package: standing
    first, then recap source_extraction.


    Source-extraction contributions always seal as ``source_domain="recap"``.
    Worldbuilding product runs are inspect-only and never reach this Kernel
    prepare path; do not reintroduce a speculative domain parameter here.
    """
    payload = dict(candidate_graph)
    standing_payload: dict[str, Any] | None = None
    if registry_context_graph is not None:
        # Present/declared registry must be typed IR with nodes — never silent
        # recap-only when the caller supplied a registry graph (even {}).
        standing_payload = dict(registry_context_graph)
        standing_typed = load_typed_candidate_graph(standing_payload)
        if not standing_typed.nodes:
            raise CandidateGraphMappingError(
                "registry_context_graph must contain at least one node"
            )
    else:
        recap_payload, maybe_standing, _diag = partition_candidate_graph_by_provenance(
            payload
        )
        if maybe_standing.get("nodes"):
            standing_payload = maybe_standing
            payload = recap_payload


    preview = load_typed_candidate_graph(payload)
    resolved_world_id = world_id or DEFAULT_WORLD_ID
    if mutation_context is None:
        if world_root is None:
            raise CandidateGraphMappingError(
                "mutation_context or world_root is required to prepare extract promote"
            )
        root = world_root.resolve()
        mutation_context = mutation_context_from_world_root(root, resolved_world_id)
    else:
        root = world_root.resolve() if world_root is not None else None
    package_world_root = str(root) if root is not None else None
    verified_revision = verify_source_revision(
        source_uri=source_uri,
        source_revision_id=source_revision_id,
        repo_root=repo_root,
        disclose_computed_digest=disclose_source_digest,
    )
    gate = gate_candidate_graph_against_head(
        preview,
        mutation_context=mutation_context,
        world_id=resolved_world_id,
        source_artifact_id=source_artifact_id,
        source_revision_id=verified_revision,
        campaign_scope=campaign_scope,
        extraction_profile=extraction_profile,
        source_uri=source_uri,
        source_kind="source_extraction",
        source_domain="recap",
        node_ids=tuple(node_ids) if node_ids is not None else None,
        include_edges=include_edges,
    )


    contribution_slices: list[dict[str, Any]] = []
    standing_gate: IdentityGateResult | None = None
    if standing_payload is not None:
        standing_campaign = str(standing_payload.get("campaign_id") or "").strip()
        requested_campaign = (
            campaign_scope or preview.campaign_id or ""
        ).strip()
        if not standing_campaign:
            raise CandidateGraphMappingError(
                "registry_context_graph campaign_id is required"
            )
        if requested_campaign and standing_campaign != requested_campaign:
            raise CandidateGraphMappingError(
                "standing_context campaign_id "
                f"{standing_campaign!r} disagrees with requested campaign "
                f"{requested_campaign!r}"
            )
        campaign_id = standing_campaign
        registry_path, registry_artifact_id, registry_uri = resolve_party_registry_uri(
            campaign_id, repo_root=repo_root
        )
        stamp_standing_registry_evidence(
            standing_payload, source_artifact_id=registry_artifact_id
        )
        standing_payload["source_artifact_ids"] = [registry_artifact_id]
        standing_preview = load_typed_candidate_graph(standing_payload)
        registry_revision = verify_source_revision(
            source_uri=registry_uri,
            source_revision_id=(
                f"sha256:{hashlib.sha256(registry_path.read_bytes()).hexdigest()}"
            ),
            repo_root=repo_root,
            disclose_computed_digest=disclose_source_digest,
        )
        standing_gate = gate_candidate_graph_against_head(
            standing_preview,
            mutation_context=mutation_context,
            world_id=resolved_world_id,
            source_artifact_id=registry_artifact_id,
            source_revision_id=registry_revision,
            campaign_scope=campaign_id,
            extraction_profile=extraction_profile or "party_registry_standing",
            source_uri=registry_uri,
            source_kind="standing_context",
            source_domain="party_registry",
            include_edges=True,
        )
        contribution_slices.append(
            build_contribution_effect_slice(
                source_revision_id=standing_gate.source_revision_id,
                source_artifact_id=standing_gate.source_artifact_id,
                verified_source_uri=str(standing_gate.verified_source_uri),
                candidate_preview_id=standing_gate.candidate_preview_id,
                candidate_schema=standing_gate.candidate_schema,
                candidate_version=standing_gate.candidate_version,
                contribution_meta=contribution_meta_from_contribution(
                    standing_gate.contribution
                ),
                accepted_proposals=standing_gate.accepted_proposals,
                rejected_assertions=standing_gate.rejected_assertions,
                unresolved_mentions=standing_gate.unresolved_mentions,
                node_id_map=standing_gate.node_id_map,
                identity_outcome_snapshot=standing_gate.identity_outcome_snapshot,
            )
        )


    contribution_slices.append(
        build_contribution_effect_slice(
            source_revision_id=gate.source_revision_id,
            source_artifact_id=gate.source_artifact_id,
            verified_source_uri=str(gate.verified_source_uri),
            candidate_preview_id=gate.candidate_preview_id,
            candidate_schema=gate.candidate_schema,
            candidate_version=gate.candidate_version,
            contribution_meta=contribution_meta_from_contribution(gate.contribution),
            accepted_proposals=gate.accepted_proposals,
            rejected_assertions=gate.rejected_assertions,
            unresolved_mentions=gate.unresolved_mentions,
            node_id_map=gate.node_id_map,
            identity_outcome_snapshot=gate.identity_outcome_snapshot,
        )
    )


    if standing_gate is not None:
        package = seal_multi_contribution_promote_proposal(
            world_id=gate.world_id,
            parent_revision_id=gate.parent_revision_id,
            contribution_slices=contribution_slices,
            prepared_by=prepared_by,
            scorer_report=gate.scorer_report,
            diagnostics=[
                *gate.diagnostics,
                *(standing_gate.diagnostics if standing_gate else []),
                "multi_contribution:standing_context+source_extraction",
            ],
            world_root=package_world_root,
            candidate_graph_path=candidate_graph_path,
        )
    else:
        package = gate.to_review_package(
            prepared_by=prepared_by,
            world_root=package_world_root,
            candidate_graph_path=candidate_graph_path,
        )


    # Slice ids are derived from position + source_kind in `contribution_slices`
    # (standing_context first when present, recap source_extraction last) — the
    # same ordered list confirm-time reconstructs from the sealed effect, so
    # both sides compute identical `contributionSliceId` values without
    # storing them in the sealed digest.
    recap_slice_index = len(contribution_slices) - 1
    review_items, review_summary = project_promote_review_as_dicts(
        gate, contribution_slice_id=contribution_slice_id_for(
            recap_slice_index, contribution_slices[recap_slice_index]
        )
    )
    if standing_gate is not None:
        standing_slice_index = 0
        standing_items, standing_summary = project_promote_review_as_dicts(
            standing_gate,
            contribution_slice_id=contribution_slice_id_for(
                standing_slice_index, contribution_slices[standing_slice_index]
            ),
        )
        for item in standing_items:
            item["provenance"] = "standing_context"
        for item in review_items:
            item["provenance"] = "source_extraction"
        review_items = [*standing_items, *review_items]
        review_summary = {
            **review_summary,
            "standing_accepted_proposals_count": standing_summary.get(
                "accepted_proposals_count", len(standing_gate.accepted_proposals)
            ),
        }


    return ExtractPromotePrepareResult(
        review_package=package,
        proposal_id=str(package["proposal_id"]),
        proposal_digest=str(package["proposal_digest"]),
        parent_revision_id=gate.parent_revision_id,
        world_id=gate.world_id,
        accepted_proposals_count=len(package.get("effect", {}).get("accepted_proposals") or gate.accepted_proposals),
        unresolved_mentions_count=len(gate.unresolved_mentions)
        + (len(standing_gate.unresolved_mentions) if standing_gate else 0),
        rejected_assertions_count=len(gate.rejected_assertions)
        + (len(standing_gate.rejected_assertions) if standing_gate else 0),
        review_items=review_items,
        review_summary=review_summary,
    )


def resolve_merged_contribution_from_package(
    *,
    review_package: Mapping[str, Any],
    confirming_principal: str,
    world_id_hint: str,
    expected_parent_revision_id: str | None,
    assertion_ids: Sequence[str] | None,
    mutation_context: WorldGraphMutationContext | None = None,
    root: Path | None = None,
    repo_root: Path | None = None,
    disclose_source_digest: bool = True,
    verify_source: bool = False,
) -> tuple[dict[str, Any], Any]:
    """Verify a sealed package and build the ONE atomic merged contribution.


    Single source of truth for "what would confirm publish": used by
    ``confirm_extract_promote`` (the actual merge) and by display/idempotency
    call sites that must reconstruct an identical ``contribution_id`` without
    mutating the world. Never calls ``kernel.merge_contribution_to_revision``.
    """
    package = dict(review_package)
    accepted_ids = normalize_assertion_selection(assertion_ids)


    verified = verify_promote_proposal(
        package,
        confirming_principal=confirming_principal,
        expected_parent_revision_id=expected_parent_revision_id,
        selected_assertion_ids=accepted_ids,
    )


    slices = list(verified.get("contribution_slices") or [])
    if not slices:
        from graph_memory.extract_promote_proposal import contribution_slices_from_effect


        slices = contribution_slices_from_effect(verified["effect"])


    if verify_source:
        if repo_root is None:
            raise ValueError("repo_root is required when verify_source=True")
        for slice_body in slices:
            verify_source_revision(
                source_uri=str(slice_body["verified_source_uri"]),
                source_revision_id=str(slice_body["source_revision_id"]),
                repo_root=repo_root,
                disclose_computed_digest=disclose_source_digest,
            )


    parent_revision_id = str(verified["parent_revision_id"])
    world_id = str(verified["world_id"]) or world_id_hint
    resolved_selection = verified.get("resolved_selection")


    slice_gates: list[tuple[IdentityGateResult, tuple[str, ...] | None, str]] = []
    for index, slice_body in enumerate(slices):
        slice_gate = _gate_from_contribution_slice(
            world_id=world_id,
            parent_revision_id=parent_revision_id,
            slice_body=slice_body,
        )
        sealed_slice_id = contribution_slice_id_for(index, slice_body)
        if resolved_selection is None:
            slice_ids: tuple[str, ...] | None = None
            if not slice_gate.accepted_proposals:
                continue
        else:
            selected = resolved_selection.get(sealed_slice_id) or set()
            if not selected:
                continue
            slice_ids = tuple(selected)
        slice_gates.append((slice_gate, slice_ids, sealed_slice_id))


    if not slice_gates:
        raise CandidateGraphMappingError("no accepted proposals selected for merge")


    merged_contribution = build_accepted_contribution_from_multi_slice_proposals(
        slice_gates,
        mutation_context=mutation_context,
        root=root,
        proposal_digest=verified["proposal_digest"],
    )
    return verified, merged_contribution


def confirm_extract_promote(
    *,
    review_package: Mapping[str, Any],
    world_root: Path | None,
    confirming_principal: str,
    assertion_ids: Sequence[str] | None = None,
    dry_run: bool = False,
    allow_live_world: bool = False,
    allow_idempotent_noop: bool = False,
    live_root: Path,
    repo_root: Path,
    disclose_source_digest: bool = True,
) -> ExtractPromoteConfirmResult:
    """Verify sealed proposal and merge (or dry-run) against the world head.


    Publishes every sealed contribution slice (standing_context + recap
    source_extraction, when present) as ONE atomic Kernel contribution in a
    single ``merge_contribution_to_revision`` call. The head either advances
    exactly once for the whole selection, or not at all — there is no
    sequential per-slice publish that could advance the head partway through
    a multi-slice promote (PR011A3 review P0).
    """
    raise ExtractPromoteWorldError(
        "Buddy filesystem extract-promote confirm is retired; use DungeonMind confirm paths"
    )
