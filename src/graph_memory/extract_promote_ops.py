"""Shared prepare/confirm orchestration for extract → World Supergraph promote.

Used by the operator CLI and the live-control HTTP layer. Durable contribution
construction always goes through sealed proposal fields only.
"""

from __future__ import annotations

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
    build_accepted_contribution_from_proposals,
    gate_candidate_graph_against_head,
)
from graph_memory.extract_promote_proposal import (
    PromoteProposalError,
    verify_promote_proposal,
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
    node_ids: Sequence[str] | None = None,
    include_edges: bool = True,
    candidate_graph_path: str | None = None,
    repo_root: Path,
    disclose_source_digest: bool = True,
) -> ExtractPromotePrepareResult:
    """Gate + seal a typed candidate graph against the pinned world head."""
    preview = load_typed_candidate_graph(candidate_graph)
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
        source_uri=source_uri,
        node_ids=tuple(node_ids) if node_ids is not None else None,
        include_edges=include_edges,
    )
    package = gate.to_review_package(
        prepared_by=prepared_by,
        world_root=str(root),
        candidate_graph_path=candidate_graph_path,
    )
    return ExtractPromotePrepareResult(
        review_package=package,
        proposal_id=str(package["proposal_id"]),
        proposal_digest=str(package["proposal_digest"]),
        parent_revision_id=gate.parent_revision_id,
        world_id=gate.world_id,
        accepted_proposals_count=len(gate.accepted_proposals),
        unresolved_mentions_count=len(gate.unresolved_mentions),
        rejected_assertions_count=len(gate.rejected_assertions),
    )


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
    """Verify sealed proposal and merge (or dry-run) against the world head."""
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

    accepted_ids = normalize_assertion_selection(assertion_ids)

    world_id_hint = str(
        (package.get("effect") or {}).get("world_id") or DEFAULT_WORLD_ID
    )
    try:
        head, _rev, _store = kernel.open_current_world_graph(root, world_id_hint)
    except Exception as exc:  # noqa: BLE001
        raise ExtractPromoteWorldError(
            f"world graph not initialized or unreadable: {exc}"
        ) from exc

    verified = verify_promote_proposal(
        package,
        confirming_principal=confirming_principal,
        expected_parent_revision_id=head.head_revision_id,
        selected_assertion_ids=accepted_ids,
    )

    verify_source_revision(
        source_uri=verified["verified_source_uri"],
        source_revision_id=verified["source_revision_id"],
        repo_root=repo_root,
        disclose_computed_digest=disclose_source_digest,
    )

    gate = _gate_from_verified(verified)
    contribution = build_accepted_contribution_from_proposals(
        gate,
        root=root,
        accepted_assertion_ids=accepted_ids,
        proposal_digest=verified["proposal_digest"],
        contribution_meta=verified["contribution_meta"],
    )

    if dry_run:
        payload = {
            "schema": "dmb_accepted_extract_contribution_v1",
            "ok": True,
            "dry_run": True,
            "proposal_id": verified["proposal_id"],
            "proposal_digest": verified["proposal_digest"],
            "confirming_principal": verified["confirming_principal"],
            "world_root": str(root),
            "expected_parent_revision_id": gate.parent_revision_id,
            "contribution_id": contribution.contribution_id,
            "contribution": contribution.model_dump(mode="json"),
        }
        return ExtractPromoteConfirmResult(ok=True, dry_run=True, payload=payload)

    result = kernel.merge_contribution_to_revision(
        root,
        world_id=gate.world_id,
        contribution=contribution,
        expected_parent_revision_id=gate.parent_revision_id,
    )

    published = bool(result.published)
    merge_receipt = result.model_dump(mode="json")
    committed_revision_id = getattr(result, "revision_id", None) or merge_receipt.get(
        "revision_id"
    )

    is_already_applied = (
        not published
        and allow_idempotent_noop
        and "idempotent_noop:contribution_already_applied" in (result.diagnostics or [])
    )
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
            "parent_revision_id": gate.parent_revision_id,
            "committed_revision_id": committed_revision_id,
            "contribution_id": contribution.contribution_id,
            "merge": merge_receipt,
            "post_publication_verification": "skipped",
            "retry_guidance": RETRY_GUIDANCE_NONE,
        }
        return ExtractPromoteConfirmResult(ok=True, dry_run=False, payload=proof)

    if not published:
        proof = {
            "schema": "dmb_promote_extract_proof_v1",
            "ok": False,
            "published": False,
            "world_root": str(root),
            "world_id": gate.world_id,
            "proposal_id": verified["proposal_id"],
            "proposal_digest": verified["proposal_digest"],
            "confirming_principal": verified["confirming_principal"],
            "parent_revision_id": gate.parent_revision_id,
            "committed_revision_id": committed_revision_id,
            "contribution_id": contribution.contribution_id,
            "merge": merge_receipt,
            "failure_reason": "merge_did_not_publish",
            "post_publication_verification": "skipped",
            "retry_guidance": RETRY_GUIDANCE_NONE,
        }
        return ExtractPromoteConfirmResult(
            ok=False,
            dry_run=False,
            payload=proof,
            failure_reason="merge_did_not_publish",
        )

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
            "parent_revision_id": gate.parent_revision_id,
            "committed_revision_id": None,
            "contribution_id": contribution.contribution_id,
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
            or "rebuild_equivalent_to_head" in rebuild.diagnostics
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
        "rebuild_equivalent_to_head": rebuild_equivalent,
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
