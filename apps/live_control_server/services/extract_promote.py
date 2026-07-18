"""Live-control service shell for extract → World Supergraph promote."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from apps.live_control_server.config import (
    extract_promote_source_root,
    live_world_graph_root,
    repo_root,
    world_graph_root,
)
from apps.live_control_server.models.extract_promote import (
    PRODUCT_CONFIRM_ALLOW_IDEMPOTENT_NOOP,
    PRODUCT_CONFIRM_ALLOW_LIVE_WORLD,
    PRODUCT_CONFIRM_DRY_RUN,
    SERVER_CONFIRMING_PRINCIPAL,
    SERVER_PREPARED_BY,
    ConfirmAuditStatus,
    ConfirmOutcome,
    ExtractPromoteConfirmReceipt,
    ExtractPromoteConfirmRequest,
    ExtractPromoteDiagnostic,
    ExtractPromoteErrorResponse,
    ExtractPromotePrepareRequest,
    ExtractPromotePrepareResponse,
    ExtractPromoteReviewSummary,
    ExtractPromotionReviewItem,
    ExtractPromoteStatusResponse,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    is_under_ingest_runs,
    is_under_world_store,
    resolve_promotable_ingest_run,
)
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.extract_identity_gate import (
    IdentityGateResult,
    build_accepted_contribution_from_proposals,
)
from graph_memory.extract_promote_ops import (
    DEFAULT_WORLD_ID,
    ExtractPromoteEmptySelectionError,
    ExtractPromoteLiveWorldError,
    ExtractPromoteWorldError,
    confirm_extract_promote,
    get_extract_promote_status,
    prepare_extract_promote,
)
from graph_memory.extract_promote_proposal import PromoteProposalError, verify_promote_proposal
from graph_memory.kernel import create_graph_contribution

# Narrow server-owned roots for non-run promote source evidence (confirm of
# legacy/CLI seals, dedicated fixture roots). Product prepare never uses these
# from the browser — run artifacts are registry-resolved only.
_SOURCE_ROOT_NAMES = ("corpus", "Docs", "evals", "tmp")


class ExtractPromoteError(ValueError):
    """Stable, safe service error for API boundaries."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[ExtractPromoteDiagnostic] | None = None,
        failure_payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])
        self.failure_payload = failure_payload

    def response(self) -> ExtractPromoteErrorResponse:
        return ExtractPromoteErrorResponse(
            code=self.code,
            message=str(self),
            status_code=self.status_code,
            diagnostics=self.diagnostics,
            failure_result=self.failure_payload,
        )


def _diagnostic(code: str, message: str) -> ExtractPromoteDiagnostic:
    return ExtractPromoteDiagnostic(code=code, message=message, severity="error")


def _allowed_source_roots() -> list[Path]:
    root = repo_root().resolve()
    roots = [(root / name).resolve() for name in _SOURCE_ROOT_NAMES]
    dedicated = extract_promote_source_root()
    if dedicated is not None:
        roots.append(dedicated)
    seen: set[Path] = set()
    unique: list[Path] = []
    for item in roots:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _path_under_any(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _parse_source_uri_to_path(raw_uri: str) -> Path:
    text = (raw_uri or "").strip()
    if not text:
        raise ExtractPromoteError(
            "sourceUri is required",
            code="invalid_source_uri",
            status_code=422,
            diagnostics=[_diagnostic("invalid_source_uri", "sourceUri is required")],
        )
    root = repo_root().resolve()
    if text.startswith("repo://"):
        rel = text[len("repo://") :].lstrip("/")
        if not rel or any(part in ("", ".", "..") for part in Path(rel).parts):
            raise ExtractPromoteError(
                "sourceUri repo path is invalid",
                code="invalid_source_uri",
                status_code=422,
                diagnostics=[
                    _diagnostic("invalid_source_uri", "sourceUri repo path is invalid")
                ],
            )
        return (root / rel).resolve()
    path = Path(text).expanduser()
    if not path.is_absolute():
        return (root / path).resolve()
    return path.resolve()


def resolve_promote_source_uri(raw_uri: str) -> str:
    """Resolve a non-run promote source URI under server-owned roots.

    Browser clients must not call this for product prepare — prepare is
    ``runId``-only. Kept for confirm defense and dedicated fixture roots.
    Arbitrary ``out/`` paths (including ingest runs) are rejected here; sealed
    run-artifact URIs are accepted only via ``assert_sealed_source_uri_allowed``.
    """
    path = _parse_source_uri_to_path(raw_uri)
    root = repo_root().resolve()
    allowed = _allowed_source_roots()

    if is_under_world_store(path, root=root) or is_under_ingest_runs(path, root=root):
        raise ExtractPromoteError(
            "sourceUri must not reference the world graph store or ingest-run tree "
            "via the path contract",
            code="invalid_source_uri",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_source_uri",
                    "sourceUri must not reference the world graph store or "
                    "ingest-run tree via the path contract",
                )
            ],
        )
    if not path.is_file():
        raise ExtractPromoteError(
            "sourceUri does not exist or is not a readable file under allowlisted roots",
            code="invalid_source_uri",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_source_uri",
                    "sourceUri does not exist or is not a readable file under "
                    "allowlisted roots",
                )
            ],
        )
    if not _path_under_any(path, allowed):
        raise ExtractPromoteError(
            "sourceUri is outside the server-owned source roots",
            code="invalid_source_uri",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_source_uri",
                    "sourceUri is outside the server-owned source roots",
                )
            ],
        )

    try:
        rel_posix = path.relative_to(root).as_posix()
        return f"repo://{rel_posix}"
    except ValueError:
        return str(path)


def assert_sealed_source_uri_allowed(source_uri: str) -> None:
    """Re-check a sealed source URI at confirm time (defense in depth).

    Accepts:
    - registry-sealed ingest-run normalized_recap under any configured
      ``DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT`` / default registry root
    - traditional allowlisted roots (corpus/Docs/evals/tmp/dedicated)

    Always denies durable world-graph store trees.
    """
    path = _parse_source_uri_to_path(source_uri)
    root = repo_root().resolve()
    if is_under_world_store(path, root=root):
        raise ExtractPromoteError(
            "sourceUri must not reference the world graph store",
            code="invalid_source_uri",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_source_uri",
                    "sourceUri must not reference the world graph store",
                )
            ],
        )
    if is_under_ingest_runs(path, root=root):
        if not path.is_file():
            raise ExtractPromoteError(
                "sealed ingest-run sourceUri is missing",
                code="invalid_source_uri",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "invalid_source_uri",
                        "sealed ingest-run sourceUri is missing",
                    )
                ],
            )
        return
    resolve_promote_source_uri(source_uri)


def _public_mapping_error(exc: CandidateGraphMappingError) -> ExtractPromoteError:
    message = str(exc)
    if "source_revision" in message or "mismatch" in message:
        safe = "source_revision_id does not match the resolved source artifact"
        return ExtractPromoteError(
            safe,
            code="source_revision_mismatch",
            status_code=409,
            diagnostics=[_diagnostic("source_revision_mismatch", safe)],
        )
    return ExtractPromoteError(
        message,
        code="mapping_error",
        status_code=409,
        diagnostics=[_diagnostic("mapping_error", message)],
    )


def _promotable_run_error(exc: PromotableIngestRunError) -> ExtractPromoteError:
    return ExtractPromoteError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=[_diagnostic(exc.code, item) for item in exc.diagnostics],
    )


def _assert_candidate_scope_matches_run(
    payload: dict[str, Any],
    *,
    campaign_id: str,
    session_id: str,
) -> None:
    cand_campaign = str(payload.get("campaign_id") or "").strip()
    cand_session = str(payload.get("session_id") or "").strip()
    if not cand_campaign or not cand_session:
        raise ExtractPromoteError(
            "candidate graph is missing campaign_id or session_id",
            code="run_scope_mismatch",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "run_scope_mismatch",
                    "candidate graph is missing campaign_id or session_id",
                ),
                _diagnostic("candidate_campaign", cand_campaign or "<missing>"),
                _diagnostic("candidate_session", cand_session or "<missing>"),
                _diagnostic("manifest_campaign", campaign_id),
                _diagnostic("manifest_session", session_id),
            ],
        )
    if cand_campaign != campaign_id or cand_session != session_id:
        raise ExtractPromoteError(
            "candidate graph campaign/session does not match the run manifest",
            code="run_scope_mismatch",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "run_scope_mismatch",
                    "candidate graph campaign/session does not match the run manifest",
                ),
                _diagnostic("candidate_campaign", cand_campaign),
                _diagnostic("candidate_session", cand_session),
                _diagnostic("manifest_campaign", campaign_id),
                _diagnostic("manifest_session", session_id),
            ],
        )


def get_status(*, world_id: str = DEFAULT_WORLD_ID) -> ExtractPromoteStatusResponse:
    result = get_extract_promote_status(
        world_root=world_graph_root(),
        world_id=world_id or DEFAULT_WORLD_ID,
    )
    return ExtractPromoteStatusResponse(
        world_id=result.world_id,
        initialized=result.initialized,
        world_state=result.world_state,  # type: ignore[arg-type]
        head_revision_id=result.head_revision_id,
        diagnostics=list(result.diagnostics),
    )


def prepare(
    request: ExtractPromotePrepareRequest,
) -> ExtractPromotePrepareResponse:
    try:
        resolved = resolve_promotable_ingest_run(request.run_id, root=repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    # Defense in depth: registry seal must still pass confirm-time rules.
    assert_sealed_source_uri_allowed(resolved.sealed_source_uri)

    path = resolved.candidate_graph_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExtractPromoteError(
            f"failed to read candidate graph: {exc}",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                _diagnostic("invalid_request", f"failed to read candidate graph: {exc}")
            ],
        ) from exc
    if not isinstance(payload, dict):
        raise ExtractPromoteError(
            "candidate graph must be a JSON object",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                _diagnostic("invalid_request", "candidate graph must be a JSON object")
            ],
        )

    _assert_candidate_scope_matches_run(
        payload,
        campaign_id=resolved.campaign_id,
        session_id=resolved.session_id,
    )

    extraction_profile = resolved.extraction_profile or "current_default"

    try:
        result = prepare_extract_promote(
            candidate_graph=payload,
            world_root=world_graph_root(),
            source_uri=resolved.sealed_source_uri,
            source_revision_id=resolved.source_revision_id,
            prepared_by=SERVER_PREPARED_BY,
            world_id=DEFAULT_WORLD_ID,
            source_artifact_id=resolved.source_artifact_id,
            campaign_scope=resolved.campaign_id,
            extraction_profile=extraction_profile,
            node_ids=request.node_ids,
            include_edges=True,
            candidate_graph_path=str(path),
            repo_root=repo_root(),
            disclose_source_digest=False,
        )
    except CandidateGraphMappingError as exc:
        raise _public_mapping_error(exc) from exc
    except PromoteProposalError as exc:
        raise ExtractPromoteError(
            str(exc),
            code="proposal_verification_failed",
            status_code=409,
            diagnostics=[_diagnostic("proposal_verification_failed", str(exc))],
        ) from exc
    except ExtractPromoteWorldError as exc:
        raise ExtractPromoteError(
            str(exc),
            code="world_not_initialized",
            status_code=409,
            diagnostics=[_diagnostic("world_not_initialized", str(exc))],
        ) from exc

    return ExtractPromotePrepareResponse(
        proposal_id=result.proposal_id,
        proposal_digest=result.proposal_digest,
        parent_revision_id=result.parent_revision_id,
        world_id=result.world_id,
        accepted_proposals_count=result.accepted_proposals_count,
        unresolved_mentions_count=result.unresolved_mentions_count,
        rejected_assertions_count=result.rejected_assertions_count,
        review_package=result.review_package,
        review_items=[
            ExtractPromotionReviewItem.model_validate(item)
            for item in result.review_items
        ],
        review_summary=ExtractPromoteReviewSummary.model_validate(
            result.review_summary or {}
        ),
        run_id=resolved.run_id,
        campaign_id=resolved.campaign_id,
        session_id=resolved.session_id,
    )


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


def _project_assertion_fields(
    review_package: dict[str, Any],
    normalized_assertion_ids: tuple[str, ...],
    *,
    world_root: Path,
) -> tuple[list[str], list[str], list[str]]:
    """Project accepted assertion and affected object ids from the sealed package."""
    warnings: list[str] = []
    try:
        verified = verify_promote_proposal(
            review_package,
            confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
            selected_assertion_ids=normalized_assertion_ids,
        )
        gate = _gate_from_verified(verified)
        contribution = build_accepted_contribution_from_proposals(
            gate,
            root=world_root,
            accepted_assertion_ids=normalized_assertion_ids,
            proposal_digest=verified["proposal_digest"],
            contribution_meta=verified["contribution_meta"],
        )
        accepted_assertion_ids = [item.assertion_id for item in contribution.accepted_assertions]
        affected_object_ids: list[str] = []
        seen: set[str] = set()
        for assertion in contribution.accepted_assertions:
            if assertion.assertion_kind == "node" and assertion.subject_node_id:
                node_id = assertion.subject_node_id
                if node_id not in seen:
                    seen.add(node_id)
                    affected_object_ids.append(node_id)
        for assertion in contribution.accepted_assertions:
            if assertion.assertion_kind != "edge":
                continue
            for node_id in (assertion.subject_node_id, assertion.target_node_id):
                if node_id and node_id not in seen:
                    seen.add(node_id)
                    affected_object_ids.append(node_id)
        return accepted_assertion_ids, affected_object_ids, warnings
    except Exception as exc:  # noqa: BLE001 — projection must not undo commit receipt
        warnings.append(f"assertion_projection_failed:{exc.__class__.__name__}")
        return [], [], warnings


def _confirm_outcome_from_ops(
    result_ok: bool,
    payload: Mapping[str, Any],
) -> tuple[ConfirmOutcome, bool, ConfirmAuditStatus, list[str]]:
    outcome_text = str(payload.get("outcome") or "").strip()
    published = bool(payload.get("published"))
    verification = str(payload.get("post_publication_verification") or "").strip()

    if outcome_text == "already_applied" and result_ok:
        return "already_applied", False, "ok", []

    if published and result_ok and verification == "passed":
        return "committed", True, "ok", []

    if published and (
        not result_ok or verification in {"degraded", "failed"}
    ):
        warnings: list[str] = []
        for key in ("failure_reason", "verification_error"):
            value = payload.get(key)
            if value:
                warnings.append(str(value))
        return "published_audit_degraded", True, "degraded", warnings

    raise ExtractPromoteError(
        "merge did not publish",
        code="merge_did_not_publish",
        status_code=409,
        diagnostics=[_diagnostic("merge_did_not_publish", "merge did not publish")],
        failure_payload=dict(payload),
    )


def _build_confirm_receipt(
    *,
    request: ExtractPromoteConfirmRequest,
    normalized_assertion_ids: tuple[str, ...],
    result_ok: bool,
    payload: Mapping[str, Any],
    world_root: Path,
) -> ExtractPromoteConfirmReceipt:
    outcome, head_advanced, audit_status, outcome_warnings = _confirm_outcome_from_ops(
        result_ok, payload
    )
    accepted_assertion_ids, affected_object_ids, projection_warnings = (
        _project_assertion_fields(
            request.review_package,
            normalized_assertion_ids,
            world_root=world_root,
        )
    )
    committed_revision_id = str(payload.get("committed_revision_id") or "").strip()
    if not committed_revision_id:
        raise ExtractPromoteError(
            "committed revision missing after confirm",
            code="extract_promote_internal_error",
            status_code=500,
        )
    return ExtractPromoteConfirmReceipt(
        outcome=outcome,
        world_id=str(payload.get("world_id") or DEFAULT_WORLD_ID),
        proposal_id=str(payload.get("proposal_id") or ""),
        proposal_digest=str(payload.get("proposal_digest") or ""),
        parent_revision_id=str(payload.get("parent_revision_id") or ""),
        committed_revision_id=committed_revision_id,
        head_advanced=head_advanced,
        selected_assertion_ids=list(normalized_assertion_ids),
        accepted_assertion_ids=accepted_assertion_ids,
        affected_object_ids=affected_object_ids,
        applied_assertion_count=len(accepted_assertion_ids),
        audit_status=audit_status,
        warnings=[*outcome_warnings, *projection_warnings],
    )


def _try_already_applied_after_stale_parent(
    request: ExtractPromoteConfirmRequest,
    normalized_assertion_ids: tuple[str, ...],
    *,
    world_root: Path,
) -> ExtractPromoteConfirmReceipt | None:
    """Resolve exact retry when head advanced past the sealed parent.

    Uses existing contribution ledger authority — no second receipt store.
    Returns None when the sealed contribution is not already active/applied
    (true stale proposal → caller re-raises verification failure).
    """
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_index,
        load_contribution_record,
    )
    import graph_memory.kernel as kernel

    try:
        verified = verify_promote_proposal(
            request.review_package,
            confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
            selected_assertion_ids=normalized_assertion_ids,
        )
        gate = _gate_from_verified(verified)
        contribution = build_accepted_contribution_from_proposals(
            gate,
            root=world_root,
            accepted_assertion_ids=normalized_assertion_ids,
            proposal_digest=verified["proposal_digest"],
            contribution_meta=verified["contribution_meta"],
        )
        head, _rev, _store = kernel.open_current_world_graph(world_root, gate.world_id)
        index = load_contribution_index(world_root, gate.world_id)
        if contribution.contribution_id not in index.active_contribution_ids:
            return None
        try:
            existing = load_contribution_record(
                world_root, gate.world_id, contribution.contribution_id
            )
        except FileNotFoundError:
            return None
        if existing is None or existing.status != "active":
            return None
        # Same contribution_id encodes sealed proposal + selection; active ledger
        # membership is the Kernel's durable already-applied authority.
    except Exception:
        return None

    payload = {
        "schema": "dmb_promote_extract_proof_v1",
        "ok": True,
        "published": False,
        "outcome": "already_applied",
        "world_id": gate.world_id,
        "proposal_id": verified["proposal_id"],
        "proposal_digest": verified["proposal_digest"],
        "parent_revision_id": gate.parent_revision_id,
        "committed_revision_id": head.head_revision_id,
        "contribution_id": contribution.contribution_id,
        "post_publication_verification": "skipped",
    }
    return _build_confirm_receipt(
        request=request,
        normalized_assertion_ids=normalized_assertion_ids,
        result_ok=True,
        payload=payload,
        world_root=world_root,
    )


def confirm(
    request: ExtractPromoteConfirmRequest,
) -> ExtractPromoteConfirmReceipt:
    if not request.assertion_ids:
        raise ExtractPromoteError(
            "explicit empty assertion selection refuses to publish",
            code="empty_assertion_selection",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "empty_assertion_selection",
                    "explicit empty assertion selection refuses to publish",
                )
            ],
        )

    normalized_assertion_ids = tuple(request.assertion_ids)
    world_root = world_graph_root()

    sealed_uri = str(
        ((request.review_package or {}).get("effect") or {}).get("verified_source_uri")
        or ""
    ).strip()
    if sealed_uri:
        assert_sealed_source_uri_allowed(sealed_uri)

    try:
        result = confirm_extract_promote(
            review_package=request.review_package,
            world_root=world_root,
            confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
            assertion_ids=normalized_assertion_ids,
            dry_run=PRODUCT_CONFIRM_DRY_RUN,
            allow_live_world=PRODUCT_CONFIRM_ALLOW_LIVE_WORLD,
            allow_idempotent_noop=PRODUCT_CONFIRM_ALLOW_IDEMPOTENT_NOOP,
            live_root=live_world_graph_root(),
            repo_root=repo_root(),
            disclose_source_digest=False,
        )
    except ExtractPromoteEmptySelectionError as exc:
        raise ExtractPromoteError(
            str(exc),
            code="empty_assertion_selection",
            status_code=422,
            diagnostics=[_diagnostic("empty_assertion_selection", str(exc))],
        ) from exc
    except ExtractPromoteLiveWorldError as exc:
        raise ExtractPromoteError(
            str(exc),
            code="live_world_refused",
            status_code=403,
            diagnostics=[_diagnostic("live_world_refused", str(exc))],
        ) from exc
    except ExtractPromoteWorldError as exc:
        raise ExtractPromoteError(
            str(exc),
            code="world_not_initialized",
            status_code=409,
            diagnostics=[_diagnostic("world_not_initialized", str(exc))],
        ) from exc
    except PromoteProposalError as exc:
        # Exact retry after a successful publish: sealed parent no longer matches
        # head, but contribution ledger may prove the selection already applied.
        if PRODUCT_CONFIRM_ALLOW_IDEMPOTENT_NOOP:
            already = _try_already_applied_after_stale_parent(
                request,
                normalized_assertion_ids,
                world_root=world_root,
            )
            if already is not None:
                return already
        raise ExtractPromoteError(
            str(exc),
            code="proposal_verification_failed",
            status_code=409,
            diagnostics=[_diagnostic("proposal_verification_failed", str(exc))],
        ) from exc
    except CandidateGraphMappingError as exc:
        raise _public_mapping_error(exc) from exc

    payload = result.payload
    outcome_text = str(payload.get("outcome") or "").strip()
    published = bool(payload.get("published"))

    if not result.ok and not published and outcome_text != "already_applied":
        raise ExtractPromoteError(
            "merge did not publish",
            code="merge_did_not_publish",
            status_code=409,
            diagnostics=[_diagnostic("merge_did_not_publish", "merge did not publish")],
            failure_payload=dict(payload),
        )

    return _build_confirm_receipt(
        request=request,
        normalized_assertion_ids=normalized_assertion_ids,
        result_ok=result.ok,
        payload=payload,
        world_root=world_root,
    )


__all__ = [
    "ExtractPromoteError",
    "assert_sealed_source_uri_allowed",
    "confirm",
    "get_status",
    "prepare",
    "resolve_promote_source_uri",
]
