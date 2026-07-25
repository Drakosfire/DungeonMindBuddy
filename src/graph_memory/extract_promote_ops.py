"""Shared prepare/confirm orchestration for extract → World Supergraph promote.

Used by the operator CLI and the live-control HTTP layer. Durable contribution
construction always goes through sealed proposal fields only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import graph_memory.kernel as kernel
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
from graph_memory.kernel.contributions import create_graph_contribution

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
        head, _rev, _store = kernel.open_current_world_graph(root, world)
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
    world_root: Path,
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
    root = world_root.resolve()
    verified_revision = verify_source_revision(
        source_uri=source_uri,
        source_revision_id=source_revision_id,
        repo_root=repo_root,
        disclose_computed_digest=disclose_source_digest,
    )
    gate = gate_candidate_graph_against_head(
        preview,
        root=root,
        world_id=world_id or DEFAULT_WORLD_ID,
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
            root=root,
            world_id=world_id or DEFAULT_WORLD_ID,
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
            world_root=str(root),
            candidate_graph_path=candidate_graph_path,
        )
    else:
        package = gate.to_review_package(
            prepared_by=prepared_by,
            world_root=str(root),
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
    root: Path,
    expected_parent_revision_id: str | None,
    assertion_ids: Sequence[str] | None,
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
    package = dict(review_package)
    root_text = str(world_root or package.get("world_root") or "").strip()
    if not root_text:
        raise ExtractPromoteWorldError(
            "world_root is required when review package omits world_root"
        )
    root = Path(root_text).resolve()
    live = live_root.resolve()
    if root == live and not allow_live_world:
        raise ExtractPromoteLiveWorldError(
            "refusing to mutate live world root without allow_live_world"
        )

    world_id_hint = str(
        (package.get("effect") or {}).get("world_id") or DEFAULT_WORLD_ID
    )
    try:
        head, _rev, _store = kernel.open_current_world_graph(root, world_id_hint)
    except Exception as exc:  # noqa: BLE001
        raise ExtractPromoteWorldError(
            f"world graph not initialized or unreadable: {exc}"
        ) from exc

    verified, contribution = resolve_merged_contribution_from_package(
        review_package=package,
        confirming_principal=confirming_principal,
        world_id_hint=world_id_hint,
        root=root,
        expected_parent_revision_id=head.head_revision_id,
        assertion_ids=assertion_ids,
        repo_root=repo_root,
        disclose_source_digest=disclose_source_digest,
        verify_source=True,
    )

    parent_revision_id = str(verified["parent_revision_id"])
    world_id = str(verified["world_id"])
    gate = _gate_from_verified(verified)

    if dry_run:
        payload = {
            "schema": "dmb_accepted_extract_contribution_v1",
            "ok": True,
            "dry_run": True,
            "proposal_id": verified["proposal_id"],
            "proposal_digest": verified["proposal_digest"],
            "confirming_principal": verified["confirming_principal"],
            "world_root": str(root),
            "expected_parent_revision_id": parent_revision_id,
            "contribution_id": contribution.contribution_id,
            "contribution_ids": [contribution.contribution_id],
            "contribution": contribution.model_dump(mode="json"),
            "contributions": [contribution.model_dump(mode="json")],
        }
        return ExtractPromoteConfirmResult(ok=True, dry_run=True, payload=payload)

    result = kernel.merge_contribution_to_revision(
        root,
        world_id=world_id,
        contribution=contribution,
        expected_parent_revision_id=parent_revision_id,
    )
    merge_receipt_single = result.model_dump(mode="json")
    published = bool(result.published)
    committed_revision_id = (
        getattr(result, "revision_id", None) or merge_receipt_single.get("revision_id")
    )
    is_already_applied = (
        not published
        and allow_idempotent_noop
        and "idempotent_noop:contribution_already_applied" in (result.diagnostics or [])
    )

    if not published and not is_already_applied:
        # Single merge call: refusal here means the head never advanced —
        # nothing was published for any slice in this selection.
        return ExtractPromoteConfirmResult(
            ok=False,
            dry_run=False,
            payload={
                "schema": "dmb_promote_extract_proof_v1",
                "ok": False,
                "published": False,
                "outcome": "merge_refused",
                "world_root": str(root),
                "world_id": world_id,
                "proposal_id": verified["proposal_id"],
                "proposal_digest": verified["proposal_digest"],
                "merge": merge_receipt_single,
                "contribution_id": contribution.contribution_id,
            },
            failure_reason="merge_refused",
        )

    merge_receipt = {
        "merges": [merge_receipt_single],
        "contribution_ids": [contribution.contribution_id],
        "last": merge_receipt_single,
    }

    if is_already_applied:
        proof = {
            "schema": "dmb_promote_extract_proof_v1",
            "ok": True,
            "published": False,
            "outcome": "already_applied",
            "world_root": str(root),
            "world_id": gate.world_id,
            "proposal_id": verified["proposal_id"],
            "proposal_digest": verified["proposal_digest"],
            "confirming_principal": verified["confirming_principal"],
            "parent_revision_id": parent_revision_id,
            "committed_revision_id": committed_revision_id or parent_revision_id,
            "contribution_id": contribution.contribution_id,
            "contribution_ids": [contribution.contribution_id],
            "merge": merge_receipt,
            "post_publication_verification": "skipped",
            "retry_guidance": RETRY_GUIDANCE_NONE,
        }
        return ExtractPromoteConfirmResult(ok=True, dry_run=False, payload=proof)

    if not committed_revision_id:
        proof = {
            "schema": "dmb_promote_extract_proof_v1",
            "ok": False,
            "published": True,
            "world_root": str(root),
            "world_id": gate.world_id,
            "proposal_id": verified["proposal_id"],
            "proposal_digest": verified["proposal_digest"],
            "confirming_principal": verified["confirming_principal"],
            "parent_revision_id": str(verified["parent_revision_id"]),
            "committed_revision_id": None,
            "contribution_id": contribution.contribution_id,
            "contribution_ids": [contribution.contribution_id],
            "merge": merge_receipt,
            "failure_reason": "post_publication_verification_failed",
            "post_publication_verification": "failed",
            "verification_error": "missing_committed_revision_id",
            "retry_guidance": RETRY_GUIDANCE_DO_NOT_RETRY,
        }
        return ExtractPromoteConfirmResult(
            ok=False,
            dry_run=False,
            payload=proof,
            failure_reason="post_publication_verification_failed",
        )

    # Publication already advanced the head. Retain the merge receipt and treat
    # rebuild/projection as audit pinned to the committed revision — never audit
    # the mutable current head (a concurrent publish could advance past us).
    verification_status = "passed"
    verification_error: str | None = None
    rebuild_diagnostics: list[str] = []
    rebuild_equivalent = False
    projection_revision_id: str | None = None
    projection_node_count: int | None = None
    projection_relationship_count: int | None = None
    head_advanced_before_verification = False
    verification_head_revision_id: str | None = None

    try:
        rebuild = kernel.rebuild_from_contributions(
            root,
            world_id=gate.world_id,
            publish=False,
            compare_revision_id=str(committed_revision_id),
        )
        rebuild_diagnostics = list(rebuild.diagnostics)
        rebuild_equivalent = (
            "rebuild_equivalent_to_pinned_revision" in rebuild.diagnostics
        )
        head_advanced_before_verification = any(
            d.startswith("head_advanced_past_compare_revision:")
            for d in rebuild_diagnostics
        )
        for item in rebuild_diagnostics:
            if item.startswith("head_advanced_past_compare_revision:"):
                verification_head_revision_id = item.split(":", 1)[1]
                break
        if not rebuild_equivalent:
            verification_status = "degraded"
            verification_error = "rebuild_not_equivalent_to_committed_revision"

        from graph_memory.projection.world_projection import (
            PROJECTION_REQUEST_SCHEMA,
            WorldGraphProjectionFocus,
            WorldGraphProjectionRequest,
        )

        projection = kernel.project_world_graph(
            root,
            WorldGraphProjectionRequest(
                schema=PROJECTION_REQUEST_SCHEMA,
                world_id=gate.world_id,
                campaign_id=contribution.campaign_scope or "longmont-c2",
                focus=WorldGraphProjectionFocus(kind="none"),
                admissibility="gm",
                revision_pin=str(committed_revision_id),
            ),
        )
        projection_revision_id = projection.snapshot.revision_id
        projection_node_count = projection.summary.node_count
        projection_relationship_count = projection.summary.relationship_count
        if projection_revision_id != committed_revision_id:
            verification_status = "failed"
            verification_error = "projection_revision_mismatch"
    except Exception as exc:  # noqa: BLE001 — audit failure must not hide publish
        verification_status = "failed"
        verification_error = f"{exc.__class__.__name__}"

    overall_ok = verification_status == "passed"
    if verification_status == "degraded":
        failure_reason = "post_publication_verification_degraded"
    elif verification_status == "failed":
        failure_reason = "post_publication_verification_failed"
    else:
        failure_reason = None

    proof = {
        "schema": "dmb_promote_extract_proof_v1",
        "ok": overall_ok,
        "published": True,
        "outcome": "published",
        "world_root": str(root),
        "world_id": gate.world_id,
        "proposal_id": verified["proposal_id"],
        "proposal_digest": verified["proposal_digest"],
        "confirming_principal": verified["confirming_principal"],
        "parent_revision_id": gate.parent_revision_id,
        "committed_revision_id": committed_revision_id,
        "contribution_id": contribution.contribution_id,
        "merge": merge_receipt,
        "post_publication_verification": verification_status,
        "verification_error": verification_error,
        "head_advanced_before_verification": head_advanced_before_verification,
        "verification_head_revision_id": verification_head_revision_id,
        "retry_guidance": (
            RETRY_GUIDANCE_DO_NOT_RETRY if not overall_ok else RETRY_GUIDANCE_NONE
        ),
        "rebuild_diagnostics": rebuild_diagnostics,
        "rebuild_equivalent_to_committed_revision": rebuild_equivalent,
        "projection_revision_id": projection_revision_id,
        "projection_node_count": projection_node_count,
        "projection_relationship_count": projection_relationship_count,
    }
    if failure_reason is not None:
        proof["failure_reason"] = failure_reason
    return ExtractPromoteConfirmResult(
        ok=overall_ok,
        dry_run=False,
        payload=proof,
        failure_reason=failure_reason,
    )
