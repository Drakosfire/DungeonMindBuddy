"""Live-control service shell for extract → World Supergraph promote."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.live_control_server.config import (
    extract_promote_source_root,
    live_world_graph_root,
    repo_root,
    world_graph_root,
)
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
    ExtractPromoteEmptySelectionError,
    ExtractPromoteLiveWorldError,
    ExtractPromoteWorldError,
    confirm_extract_promote,
    get_extract_promote_status,
    prepare_extract_promote,
)
from graph_memory.extract_promote_proposal import PromoteProposalError

# Narrow server-owned roots for promote source evidence. Entire repo is NOT
# allowed (would admit .env and other secrets). Graph store trees (out/ and
# world_graph_root) are never source authority — they are the materialized model.
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


def _allowed_candidate_roots() -> list[Path]:
    roots = [
        repo_root().resolve(),
        world_graph_root().resolve(),
        (repo_root() / "out").resolve(),
        (repo_root() / "evals").resolve(),
        (repo_root() / "tmp").resolve(),
    ]
    dedicated = extract_promote_source_root()
    if dedicated is not None:
        roots.append(dedicated)
    seen: set[Path] = set()
    unique: list[Path] = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique.append(root)
    return unique


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


def _graph_store_denied_roots() -> list[Path]:
    """World graph storage is never evidentiary source authority."""
    roots = [
        world_graph_root().resolve(),
        (repo_root() / "out").resolve(),
    ]
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


def _is_under_graph_store(path: Path) -> bool:
    return _path_under_any(path, _graph_store_denied_roots())


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
    if not _path_under_any(path, _allowed_candidate_roots()):
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


def resolve_promote_source_uri(raw_uri: str) -> str:
    """Resolve a promote source URI under server-owned roots; seal a canonical form.

    Client-supplied absolute paths outside the allowlist are rejected. Paths under
    the repo root are sealed as ``repo://…`` so containment stays inspectable.
    Graph-store trees are always denied even when nested under a broader allowlist.
    """
    text = (raw_uri or "").strip()
    if not text:
        raise ExtractPromoteError(
            "sourceUri is required",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_request", "sourceUri is required")],
        )

    root = repo_root().resolve()
    allowed = _allowed_source_roots()

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
        path = (root / rel).resolve()
    else:
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = (root / path).resolve()
        else:
            path = path.resolve()

    if _is_under_graph_store(path):
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
    if not path.is_file():
        raise ExtractPromoteError(
            "sourceUri does not exist or is not a readable file under allowlisted roots",
            code="invalid_source_uri",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_source_uri",
                    "sourceUri does not exist or is not a readable file under allowlisted roots",
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
        # Under a dedicated promote source root outside the repo tree.
        return str(path)


def assert_sealed_source_uri_allowed(source_uri: str) -> None:
    """Re-check a sealed source URI at confirm time (defense in depth)."""
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
    path = resolve_candidate_graph_path(request.candidate_graph_path)
    canonical_source_uri = resolve_promote_source_uri(request.source_uri)
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
            source_uri=canonical_source_uri,
            source_revision_id=request.source_revision_id,
            prepared_by=request.prepared_by,
            world_id=request.world_id,
            source_artifact_id=request.source_artifact_id,
            campaign_scope=request.campaign_scope,
            node_ids=request.node_ids,
            include_edges=not request.nodes_only,
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
    )


def confirm(
    request: ExtractPromoteConfirmRequest,
) -> ExtractPromoteConfirmResponse:
    sealed_uri = str(
        ((request.review_package or {}).get("effect") or {}).get("verified_source_uri")
        or ""
    ).strip()
    if sealed_uri:
        assert_sealed_source_uri_allowed(sealed_uri)

    try:
        result = confirm_extract_promote(
            review_package=request.review_package,
            world_root=world_graph_root(),
            confirming_principal=request.confirming_principal,
            assertion_ids=request.assertion_ids,
            dry_run=request.dry_run,
            allow_live_world=request.allow_live_world,
            allow_idempotent_noop=request.allow_idempotent_noop,
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
        raise ExtractPromoteError(
            str(exc),
            code="proposal_verification_failed",
            status_code=409,
            diagnostics=[_diagnostic("proposal_verification_failed", str(exc))],
        ) from exc
    except CandidateGraphMappingError as exc:
        raise _public_mapping_error(exc) from exc

    if not result.ok:
        # Published-but-audit-failed must remain a truthful confirm response so
        # callers do not retry under the false impression nothing committed.
        if result.payload.get("published") is True:
            return ExtractPromoteConfirmResponse(
                ok=False,
                dry_run=result.dry_run,
                failure_reason=result.failure_reason,
                result=result.payload,
            )
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
