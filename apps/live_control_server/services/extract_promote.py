"""Live-control service shell for extract → World Supergraph promote."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.models.extract_promote import (
    ExtractPromoteConfirmRequest,
    ExtractPromoteConfirmResponse,
    ExtractPromoteDiagnostic,
    ExtractPromoteErrorResponse,
    ExtractPromotePrepareRequest,
    ExtractPromotePrepareResponse,
    ExtractPromoteStatusResponse,
)
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.extract_promote_ops import (
    DEFAULT_WORLD_ID,
    ExtractPromoteLiveWorldError,
    ExtractPromoteWorldError,
    confirm_extract_promote,
    default_live_root,
    get_extract_promote_status,
    prepare_extract_promote,
)
from graph_memory.extract_promote_proposal import PromoteProposalError


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
        )


def _diagnostic(code: str, message: str) -> ExtractPromoteDiagnostic:
    return ExtractPromoteDiagnostic(code=code, message=message, severity="error")


def _allowed_roots() -> list[Path]:
    roots = [
        repo_root().resolve(),
        world_graph_root().resolve(),
        (repo_root() / "out").resolve(),
        (repo_root() / "evals").resolve(),
        (repo_root() / "tmp").resolve(),
    ]
    # Deduplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique.append(root)
    return unique


def resolve_candidate_graph_path(raw_path: str) -> Path:
    """Resolve a candidate-graph path under an allowlisted root."""
    text = (raw_path or "").strip()
    if not text:
        raise ExtractPromoteError(
            "candidateGraphPath is required",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_request", "candidateGraphPath is required")],
        )
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = (repo_root() / path).resolve()
    else:
        path = path.resolve()
    if not path.is_file():
        raise ExtractPromoteError(
            "candidateGraphPath does not exist or is not a file",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_request",
                    "candidateGraphPath does not exist or is not a file",
                )
            ],
        )
    allowed = False
    for root in _allowed_roots():
        try:
            path.relative_to(root)
            allowed = True
            break
        except ValueError:
            continue
    if not allowed:
        raise ExtractPromoteError(
            "candidateGraphPath is outside the allowlisted roots",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_request",
                    "candidateGraphPath is outside the allowlisted roots",
                )
            ],
        )
    return path


def get_status(*, world_id: str = DEFAULT_WORLD_ID) -> ExtractPromoteStatusResponse:
    result = get_extract_promote_status(
        world_root=world_graph_root(),
        world_id=world_id or DEFAULT_WORLD_ID,
    )
    return ExtractPromoteStatusResponse(
        world_id=result.world_id,
        initialized=result.initialized,
        head_revision_id=result.head_revision_id,
        diagnostics=list(result.diagnostics),
    )


def prepare(
    request: ExtractPromotePrepareRequest,
) -> ExtractPromotePrepareResponse:
    path = resolve_candidate_graph_path(request.candidate_graph_path)
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

    try:
        result = prepare_extract_promote(
            candidate_graph=payload,
            world_root=world_graph_root(),
            source_uri=request.source_uri,
            source_revision_id=request.source_revision_id,
            prepared_by=request.prepared_by,
            world_id=request.world_id,
            source_artifact_id=request.source_artifact_id,
            campaign_scope=request.campaign_scope,
            node_ids=request.node_ids,
            include_edges=not request.nodes_only,
            candidate_graph_path=str(path),
            repo_root=repo_root(),
        )
    except CandidateGraphMappingError as exc:
        code = (
            "source_revision_mismatch"
            if "source_revision" in str(exc) or "mismatch" in str(exc)
            else "mapping_error"
        )
        raise ExtractPromoteError(
            str(exc),
            code=code,
            status_code=409,
            diagnostics=[_diagnostic(code, str(exc))],
        ) from exc
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
    )


def confirm(
    request: ExtractPromoteConfirmRequest,
) -> ExtractPromoteConfirmResponse:
    try:
        result = confirm_extract_promote(
            review_package=request.review_package,
            world_root=world_graph_root(),
            confirming_principal=request.confirming_principal,
            assertion_ids=request.assertion_ids,
            dry_run=request.dry_run,
            allow_live_world=request.allow_live_world,
            allow_idempotent_noop=request.allow_idempotent_noop,
            live_root=default_live_root(repo_root=repo_root()),
            repo_root=repo_root(),
        )
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
        raise ExtractPromoteError(
            str(exc),
            code="proposal_verification_failed",
            status_code=409,
            diagnostics=[_diagnostic("proposal_verification_failed", str(exc))],
        ) from exc
    except CandidateGraphMappingError as exc:
        message = str(exc)
        code = (
            "source_revision_mismatch"
            if "source_revision" in message or "mismatch" in message
            else "mapping_error"
        )
        raise ExtractPromoteError(
            message,
            code=code,
            status_code=409,
            diagnostics=[_diagnostic(code, message)],
        ) from exc

    if not result.ok:
        raise ExtractPromoteError(
            "merge did not publish",
            code="merge_did_not_publish",
            status_code=409,
            diagnostics=[_diagnostic("merge_did_not_publish", "merge did not publish")],
            failure_payload=result.payload,
        )

    return ExtractPromoteConfirmResponse(
        ok=True,
        dry_run=result.dry_run,
        failure_reason=None,
        result=result.payload,
    )
