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
    ExactRunReviewAssertion,
    ExactRunReviewEvidence,
    ExactRunReviewPackage,
    ExtractPromoteConfirmReceipt,
    ExtractPromoteConfirmRequest,
    ExtractPromoteDiagnostic,
    ExtractPromoteErrorResponse,
    ExtractPromotePrepareRequest,
    ExtractPromotePrepareResponse,
    ExtractPromoteReviewSummary,
    ExtractPromotionReviewItem,
    ExtractPromoteStatusResponse,
    WorldbuildingWritePlanConfirmReceipt,
    WorldbuildingWritePlanConfirmRequest,
    WorldbuildingWritePlanPrepareRequest,
    WorldbuildingWritePlanResponse,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    is_under_ingest_runs,
    is_under_world_store,
    resolve_promotable_ingest_run,
)
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    load_typed_candidate_graph,
)
from graph_memory.extract_promote_ops import (
    DEFAULT_WORLD_ID,
    ExtractPromoteEmptySelectionError,
    ExtractPromoteLiveWorldError,
    ExtractPromoteWorldError,
    confirm_extract_promote,
    get_extract_promote_status,
    prepare_extract_promote,
    resolve_merged_contribution_from_package,
)
from graph_memory.extract_promote_proposal import PromoteProposalError
from graph_memory.worldbuilding_write_plan import (
    WorldbuildingDispositionInput,
    WorldbuildingWritePlanError,
    WorldbuildingWritePlanVerificationContext,
    build_worldbuilding_write_plan,
    materialize_worldbuilding_contribution,
    verify_worldbuilding_write_plan,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

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
    run_campaign = (campaign_id or "").strip()
    run_session = (session_id or "").strip()

    # Sessionless / campaignless runs: never invent scope the exact run omitted.
    if not run_session:
        if cand_session:
            raise ExtractPromoteError(
                "candidate graph invents a session for a sessionless run",
                code="run_scope_mismatch",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "run_scope_mismatch",
                        "candidate graph invents a session for a sessionless run",
                    ),
                    _diagnostic("candidate_session", cand_session),
                    _diagnostic("manifest_session", "<null>"),
                ],
            )
        if run_campaign:
            if cand_campaign != run_campaign:
                raise ExtractPromoteError(
                    "candidate graph campaign does not match the run",
                    code="run_scope_mismatch",
                    status_code=422,
                    diagnostics=[
                        _diagnostic(
                            "run_scope_mismatch",
                            "candidate graph campaign does not match the run",
                        ),
                        _diagnostic("candidate_campaign", cand_campaign or "<missing>"),
                        _diagnostic("manifest_campaign", run_campaign),
                    ],
                )
        elif cand_campaign:
            raise ExtractPromoteError(
                "candidate graph invents a campaign for a campaignless run",
                code="run_scope_mismatch",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "run_scope_mismatch",
                        "candidate graph invents a campaign for a campaignless run",
                    ),
                    _diagnostic("candidate_campaign", cand_campaign),
                    _diagnostic("manifest_campaign", "<null>"),
                ],
            )
        return

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
                _diagnostic("manifest_campaign", run_campaign),
                _diagnostic("manifest_session", run_session),
            ],
        )
    if cand_campaign != run_campaign or cand_session != run_session:
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
                _diagnostic("manifest_campaign", run_campaign),
                _diagnostic("manifest_session", run_session),
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


def _paragraph_for_span(source_lines: list[str], *, start_line: int, end_line: int) -> str:
    if start_line < 1 or end_line < start_line or end_line > len(source_lines):
        return ""
    return "\n".join(source_lines[start_line - 1 : end_line])


def _load_frozen_span_index_for_resolved_run(resolved: Any) -> Any:
    """Load the SourceSpanIndex pinned by the resolved ExtractionRun component.

    Uses the run's frozen ``source_span_index`` component path carried on
    ``PromotableIngestRun``. Never re-derives the registry's canonical index
    path from ``source_artifact_id`` alone — a run may pin a different
    repo-contained, digest-valid index for the same artifact.
    """
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        get_source_artifact,
    )
    from graph_memory.source_span import (
        source_span_index_from_dict,
        validate_source_span_index,
    )
    from src.live_play.live_store import load_json

    span_path = getattr(resolved, "source_span_index_path", None)
    if span_path is None:
        raise ExtractPromoteError(
            "exact-run source span index is unavailable",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "source_span_index_unavailable",
                    "resolved run does not carry a pinned source_span_index path",
                )
            ],
        )

    try:
        payload = load_json(span_path)
        index = source_span_index_from_dict(payload)
        artifact = get_source_artifact(repo_root(), resolved.source_artifact_id)
        validate_source_span_index(
            index,
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=artifact.content_sha256 or "",
        )
    except SourceArtifactRegistryError as exc:
        raise ExtractPromoteError(
            "exact-run source span index is unavailable",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("source_span_index_unavailable", str(exc))],
        ) from exc
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise ExtractPromoteError(
            "exact-run source span index is unavailable",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("source_span_index_unavailable", str(exc))],
        ) from exc
    return index


_WORLDBUILDING_INSPECT_ONLY_REASON = (
    "Worldbuilding ExtractionRuns are inspect-only in this slice. "
    "Assertions stamped worldbuilding_draft are not eligible for World Graph "
    "prepare/confirm until an approved authority-elevation contract lands."
)


def _worldbuilding_inspect_only_error() -> ExtractPromoteError:
    return ExtractPromoteError(
        _WORLDBUILDING_INSPECT_ONLY_REASON,
        code="not_promote_eligible",
        status_code=422,
        diagnostics=[
            _diagnostic("worldbuilding_draft_not_promotable", _WORLDBUILDING_INSPECT_ONLY_REASON)
        ],
    )


def _is_worldbuilding_inspect_only(resolved: Any) -> bool:
    return (getattr(resolved, "source_domain", None) or "").strip() == "worldbuilding"


def _assert_and_project_candidate_evidence(
    *,
    candidate_payload: dict[str, Any],
    source_prose: str,
    source_artifact_id: str,
    span_index: Any,
) -> list[ExactRunReviewAssertion]:
    """Fail closed when candidate evidence is not bound to frozen span content.

    Uses the typed candidate validator, requires every promotable node/edge
    evidence ref to resolve against the span index + SourceArtifact, and verifies
    anchor quotes against canonical source paragraph bytes.
    """
    from graph_memory.anchor_quotes import find_anchor_quote_matches
    from graph_memory.candidate_graph_to_contribution import (
        CandidateGraphMappingError,
        load_typed_candidate_graph,
    )

    try:
        typed = load_typed_candidate_graph(candidate_payload)
    except CandidateGraphMappingError as exc:
        raise ExtractPromoteError(
            f"candidate graph failed typed validation: {exc}",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("candidate_invalid", str(exc))],
        ) from exc

    span_by_id = {span.source_span_id: span for span in span_index.spans}
    source_lines = source_prose.splitlines()
    expected_artifact = (source_artifact_id or "").strip()
    assertions: list[ExactRunReviewAssertion] = []

    def _project_holder(
        *,
        assertion_id: str,
        kind: str,
        label: str,
        summary: str,
        evidence_refs: Any,
    ) -> ExactRunReviewAssertion:
        if not evidence_refs:
            raise ExtractPromoteError(
                f"assertion {assertion_id!r} is missing evidence_refs",
                code="run_not_promotable",
                status_code=422,
                diagnostics=[
                    _diagnostic("missing_evidence", f"assertion={assertion_id}"),
                ],
            )
        projected: list[ExactRunReviewEvidence] = []
        for index, ref in enumerate(evidence_refs):
            span_id = str(getattr(ref, "source_span_ref_id", "") or "").strip()
            artifact_id = str(getattr(ref, "source_artifact_id", "") or "").strip()
            if not span_id:
                raise ExtractPromoteError(
                    f"assertion {assertion_id!r} evidence[{index}] missing source_span_ref_id",
                    code="run_not_promotable",
                    status_code=422,
                    diagnostics=[
                        _diagnostic(
                            "missing_span_ref",
                            f"assertion={assertion_id} evidence_index={index}",
                        )
                    ],
                )
            if artifact_id != expected_artifact:
                raise ExtractPromoteError(
                    f"assertion {assertion_id!r} evidence[{index}] source_artifact_id "
                    f"does not match the run SourceArtifact",
                    code="run_not_promotable",
                    status_code=422,
                    diagnostics=[
                        _diagnostic("source_artifact_mismatch", artifact_id or "<missing>"),
                        _diagnostic("run_source_artifact", expected_artifact),
                    ],
                )
            span = span_by_id.get(span_id)
            if span is None:
                raise ExtractPromoteError(
                    f"assertion {assertion_id!r} evidence[{index}] references unknown "
                    f"source_span_ref_id {span_id!r}",
                    code="run_not_promotable",
                    status_code=422,
                    diagnostics=[
                        _diagnostic("unknown_span_ref", span_id),
                        _diagnostic("assertion", assertion_id),
                    ],
                )
            paragraph = _paragraph_for_span(
                source_lines,
                start_line=int(span.start_line),
                end_line=int(span.end_line),
            ).strip()
            if not paragraph:
                raise ExtractPromoteError(
                    f"assertion {assertion_id!r} evidence[{index}] span resolves to "
                    "empty source content",
                    code="run_not_promotable",
                    status_code=422,
                    diagnostics=[
                        _diagnostic("empty_span_content", span_id),
                    ],
                )
            raw_quotes = [
                str(item).strip()
                for item in (getattr(ref, "anchor_quotes", None) or [])
                if str(item).strip()
            ]
            if not raw_quotes:
                raise ExtractPromoteError(
                    f"assertion {assertion_id!r} evidence[{index}] is missing anchor_quotes",
                    code="run_not_promotable",
                    status_code=422,
                    diagnostics=[
                        _diagnostic("missing_anchor_quotes", span_id),
                    ],
                )
            verified_quotes: list[str] = []
            for quote in raw_quotes:
                if not find_anchor_quote_matches(paragraph, [quote]):
                    raise ExtractPromoteError(
                        f"assertion {assertion_id!r} evidence[{index}] anchor quote "
                        "does not occur in the canonical span paragraph",
                        code="run_not_promotable",
                        status_code=422,
                        diagnostics=[
                            _diagnostic("false_anchor_quote", quote[:120]),
                            _diagnostic("span_ref", span_id),
                        ],
                    )
                verified_quotes.append(quote)
            projected.append(
                ExactRunReviewEvidence(
                    source_artifact_id=artifact_id,
                    source_span_ref_id=span_id,
                    paragraph_text=paragraph,
                    anchor_quotes=verified_quotes,
                    start_line=int(span.start_line),
                    end_line=int(span.end_line),
                )
            )
        return ExactRunReviewAssertion(
            assertion_id=assertion_id,
            kind=kind,  # type: ignore[arg-type]
            label=label,
            summary=summary,
            evidence=projected,
        )

    for node in typed.nodes:
        node_id = str(node.node_id or "").strip()
        if not node_id:
            continue
        assertions.append(
            _project_holder(
                assertion_id=node_id,
                kind="object",
                label=str(node.label or node_id).strip() or node_id,
                summary=str(getattr(node, "description", "") or "").strip(),
                evidence_refs=node.evidence_refs,
            )
        )
    for edge in typed.edges:
        edge_id = str(edge.edge_id or "").strip()
        if not edge_id:
            continue
        assertions.append(
            _project_holder(
                assertion_id=edge_id,
                kind="relationship",
                label=str(getattr(edge, "label", None) or edge_id).strip() or edge_id,
                summary=(
                    f"{getattr(edge, 'from_node_id', None) or '?'} → "
                    f"{getattr(edge, 'to_node_id', None) or '?'}"
                ),
                evidence_refs=edge.evidence_refs,
            )
        )
    return assertions


def get_exact_run_review_package(run_id: str) -> ExactRunReviewPackage:
    """Build a source/evidence review projection for one exact ExtractionRun.

    Resolves the run through the same server-owned promotable seam as prepare,
    then projects canonical source prose and per-assertion span evidence without
    sealing a proposal or inventing campaign/session scope.
    """
    try:
        resolved = resolve_promotable_ingest_run(run_id, root=repo_root())
    except PromotableIngestRunError as exc:
        raise ExtractPromoteError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
            diagnostics=[
                _diagnostic(exc.code, item) for item in (exc.diagnostics or [str(exc)])
            ],
        ) from exc

    try:
        source_prose = resolved.normalized_recap_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExtractPromoteError(
            "exact-run source prose could not be read",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("source_unreadable", str(exc))],
        ) from exc

    try:
        candidate_payload = json.loads(
            resolved.candidate_graph_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ExtractPromoteError(
            "exact-run candidate graph could not be read",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("candidate_unreadable", str(exc))],
        ) from exc
    if not isinstance(candidate_payload, dict):
        raise ExtractPromoteError(
            "exact-run candidate graph root must be a JSON object",
            code="run_not_promotable",
            status_code=422,
        )

    _assert_candidate_scope_matches_run(
        candidate_payload,
        campaign_id=resolved.campaign_id,
        session_id=resolved.session_id,
    )

    span_index = _load_frozen_span_index_for_resolved_run(resolved)
    assertions = _assert_and_project_candidate_evidence(
        candidate_payload=candidate_payload,
        source_prose=source_prose,
        source_artifact_id=resolved.source_artifact_id,
        span_index=span_index,
    )

    inspect_only = _is_worldbuilding_inspect_only(resolved)
    return ExactRunReviewPackage(
        run_id=resolved.run_id,
        source_domain=resolved.source_domain,
        source_artifact_id=resolved.source_artifact_id,
        source_revision_id=resolved.source_revision_id,
        campaign_id=resolved.campaign_id or None,
        session_id=resolved.session_id or None,
        source_prose=source_prose,
        assertions=assertions,
        diagnostics=list(resolved.diagnostics),
        promotable=not inspect_only,
        promotable_reason=_WORLDBUILDING_INSPECT_ONLY_REASON if inspect_only else None,
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

    # ExtractionRun-backed prepare: every evidence ref must bind to the frozen
    # span index and verify against canonical source bytes before sealing.
    if any(
        "resolved via canonical ExtractionRun registry" in item
        for item in resolved.diagnostics
    ):
        try:
            source_prose = resolved.normalized_recap_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ExtractPromoteError(
                "exact-run source prose could not be read",
                code="run_not_promotable",
                status_code=422,
                diagnostics=[_diagnostic("source_unreadable", str(exc))],
            ) from exc
        span_index = _load_frozen_span_index_for_resolved_run(resolved)
        _assert_and_project_candidate_evidence(
            candidate_payload=payload,
            source_prose=source_prose,
            source_artifact_id=resolved.source_artifact_id,
            span_index=span_index,
        )

    # BLD-07 narrowed: worldbuilding is inspect-only. Fail after evidence
    # validation so binding errors remain visible; never seal draft canon.
    if _is_worldbuilding_inspect_only(resolved):
        raise _worldbuilding_inspect_only_error()

    extraction_profile = resolved.extraction_profile or "current_default"

    registry_payload = None
    registry_path = resolved.registry_context_graph_path
    if registry_path is None:
        sibling = path.parent / "registry_context_graph.json"
        if sibling.is_file():
            registry_path = sibling
    if registry_path is not None:
        try:
            loaded = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExtractPromoteError(
                f"registry context graph is present but unreadable: {exc}",
                code="invalid_request",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "invalid_request",
                        f"registry context graph is present but unreadable: {exc}",
                    )
                ],
            ) from exc
        if not isinstance(loaded, dict):
            raise ExtractPromoteError(
                "registry context graph must be a JSON object",
                code="invalid_request",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "invalid_request",
                        "registry context graph must be a JSON object",
                    )
                ],
            )
        try:
            typed_registry = load_typed_candidate_graph(loaded)
        except CandidateGraphMappingError as exc:
            raise ExtractPromoteError(
                f"registry context graph is present but invalid: {exc}",
                code="invalid_request",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "invalid_request",
                        f"registry context graph is present but invalid: {exc}",
                    )
                ],
            ) from exc
        if not typed_registry.nodes:
            raise ExtractPromoteError(
                "registry context graph must contain at least one node",
                code="invalid_request",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "invalid_request",
                        "registry context graph must contain at least one node",
                    )
                ],
            )
        registry_campaign = str(typed_registry.campaign_id or "").strip()
        if not registry_campaign:
            raise ExtractPromoteError(
                "registry context graph campaign_id is required",
                code="invalid_request",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "invalid_request",
                        "registry context graph campaign_id is required",
                    )
                ],
            )
        if registry_campaign != resolved.campaign_id:
            raise ExtractPromoteError(
                "registry context graph campaign_id "
                f"{registry_campaign!r} disagrees with run campaign "
                f"{resolved.campaign_id!r}",
                code="invalid_request",
                status_code=422,
                diagnostics=[
                    _diagnostic(
                        "invalid_request",
                        "registry context graph campaign_id disagrees with run",
                    )
                ],
            )
        registry_payload = loaded

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
            registry_context_graph=registry_payload,
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
    except WorldGraphNotFoundError as exc:
        # Identity gate opens the head before wrapping; missing head is an
        # expected operator state, not extract_promote_internal_error.
        raise ExtractPromoteError(
            "The World Graph is not initialized. Bootstrap or restore an "
            "eldyrwild head under the configured world root before merging.",
            code="world_not_initialized",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "world_not_initialized",
                    "no world graph head for world_id='eldyrwild'",
                )
            ],
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
        campaign_id=resolved.campaign_id or None,
        session_id=resolved.session_id or None,
    )


def prepare_worldbuilding(
    request: WorldbuildingWritePlanPrepareRequest,
) -> WorldbuildingWritePlanResponse:
    """Prepare one exact BLD-08 worldbuilding run into an inert write plan."""
    try:
        resolved = resolve_promotable_ingest_run(request.run_id, root=repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )

    try:
        plan = build_worldbuilding_write_plan(
            preview=typed_preview,
            world_root=world_graph_root(),
            world_id=DEFAULT_WORLD_ID,
            expected_parent_revision_id=request.expected_parent_revision_id,
            run_id=resolved.run_id,
            source_artifact_id=resolved.source_artifact_id,
            source_revision_id=resolved.source_revision_id,
            source_uri=resolved.sealed_source_uri,
            extraction_profile=expected_profile,
            campaign_scope=resolved.campaign_id or None,
            dispositions=[
                WorldbuildingDispositionInput(
                    assertion_id=item.assertion_id,
                    decision=item.decision,
                    target_node_id=item.target_node_id,
                )
                for item in request.dispositions
            ],
        )
    except WorldbuildingWritePlanError as exc:
        raise ExtractPromoteError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
            diagnostics=[_diagnostic(exc.code, str(exc))],
        ) from exc

    response = WorldbuildingWritePlanResponse(
        plan_id=plan.plan_id,
        plan_digest=plan.plan_digest,
        decision_digest=plan.decision_digest,
        world_id=plan.world_id,
        parent_revision_id=plan.parent_revision_id,
        run_id=plan.run_id,
        source_artifact_id=plan.source_artifact_id,
        source_revision_id=plan.source_revision_id,
        extraction_profile=plan.extraction_profile,  # type: ignore[arg-type]
        candidate_preview_id=plan.candidate_preview_id,
        candidate_schema=plan.candidate_schema,
        candidate_version=plan.candidate_version,
        effect=plan.effect,
        summary=plan.summary,
        diagnostics=plan.diagnostics,
    )
    try:
        verify_worldbuilding_write_plan(
            response.model_dump(mode="json", by_alias=True),
            preview=typed_preview,
            world_root=world_graph_root(),
            context=WorldbuildingWritePlanVerificationContext(
                world_id=DEFAULT_WORLD_ID,
                parent_revision_id=request.expected_parent_revision_id,
                run_id=resolved.run_id,
                source_artifact_id=resolved.source_artifact_id,
                source_revision_id=resolved.source_revision_id,
                source_uri=resolved.sealed_source_uri,
                extraction_profile=expected_profile,
                campaign_scope=resolved.campaign_id or None,
            ),
        )
    except WorldbuildingWritePlanError as exc:
        if exc.code == "stale_parent_revision":
            raise ExtractPromoteError(
                str(exc),
                code=exc.code,
                status_code=exc.status_code,
                diagnostics=[_diagnostic(exc.code, str(exc))],
            ) from exc
        raise ExtractPromoteError(
            "worldbuilding write plan failed self-verification",
            code="plan_verification_failed",
            status_code=500,
            diagnostics=[_diagnostic("plan_verification_failed", str(exc))],
        ) from exc
    return response


def _load_typed_worldbuilding_preview_for_run(resolved):
    """Shared prepare/confirm admission for one exact BLD-08 worldbuilding run."""
    if resolved.source_domain != "worldbuilding":
        raise ExtractPromoteError(
            "operation requires a worldbuilding ExtractionRun",
            code="worldbuilding_run_required",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "worldbuilding_run_required",
                    "resolved ExtractionRun source_domain must be worldbuilding",
                )
            ],
        )
    from graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE_ID,
        WORLDBUILDING_PROFILE_VERSION,
    )

    expected_profile = f"{WORLDBUILDING_PROFILE_ID}@{WORLDBUILDING_PROFILE_VERSION}"
    if resolved.extraction_profile != expected_profile:
        raise ExtractPromoteError(
            "operation requires the exact BLD-08 extraction profile",
            code="unsupported_worldbuilding_profile",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "unsupported_worldbuilding_profile",
                    f"expected {expected_profile}",
                )
            ],
        )
    if resolved.session_id:
        raise ExtractPromoteError(
            "worldbuilding ExtractionRuns must have a null session",
            code="run_scope_mismatch",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "run_scope_mismatch",
                    "worldbuilding ExtractionRuns must have a null session",
                )
            ],
        )

    assert_sealed_source_uri_allowed(resolved.sealed_source_uri)
    try:
        candidate_payload = json.loads(
            resolved.candidate_graph_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ExtractPromoteError(
            "exact-run candidate graph could not be read",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("candidate_unreadable", str(exc))],
        ) from exc
    if not isinstance(candidate_payload, dict):
        raise ExtractPromoteError(
            "exact-run candidate graph root must be a JSON object",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "candidate_unreadable",
                    "exact-run candidate graph root must be a JSON object",
                )
            ],
        )

    _assert_candidate_scope_matches_run(
        candidate_payload,
        campaign_id=resolved.campaign_id,
        session_id=resolved.session_id,
    )
    try:
        typed_preview = load_typed_candidate_graph(candidate_payload)
    except CandidateGraphMappingError as exc:
        raise ExtractPromoteError(
            f"candidate graph failed typed validation: {exc}",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("candidate_invalid", str(exc))],
        ) from exc

    from src.graph_memory.extraction.extraction_profile import get_extraction_profile

    try:
        profile = get_extraction_profile(
            WORLDBUILDING_PROFILE_ID,
            WORLDBUILDING_PROFILE_VERSION,
        )
        profile_errors = [
            str(item)
            for item in (
                profile.post_extraction_validator(candidate_payload)
                if profile.post_extraction_validator is not None
                else ()
            )
            if str(item).strip()
        ]
    except Exception as exc:  # noqa: BLE001 — profile admission fails closed
        raise ExtractPromoteError(
            "worldbuilding profile validation failed",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("profile_validation_failed", str(exc))],
        ) from exc
    if profile_errors:
        message = "; ".join(profile_errors)
        raise ExtractPromoteError(
            "worldbuilding candidate failed its BLD-08 profile validator",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("profile_validation_failed", message)],
        )

    try:
        source_prose = resolved.normalized_recap_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExtractPromoteError(
            "exact-run source prose could not be read",
            code="run_not_promotable",
            status_code=422,
            diagnostics=[_diagnostic("source_unreadable", str(exc))],
        ) from exc
    span_index = _load_frozen_span_index_for_resolved_run(resolved)
    _assert_and_project_candidate_evidence(
        candidate_payload=candidate_payload,
        source_prose=source_prose,
        source_artifact_id=resolved.source_artifact_id,
        span_index=span_index,
    )
    return typed_preview, expected_profile


def _worldbuilding_publication_audit(
    *,
    world_root: Path,
    world_id: str,
    contribution_id: str,
    parent_revision_id: str,
    contribution: Any,
) -> tuple[str | None, list[str]]:
    """Prove whether this plan's contribution published; return its revision + warnings.

    Returns ``(None, warnings)`` when publication is not proven. When proven,
    ``committed_revision_id`` is the immutable revision that introduced the
    contribution — not a later head that merely still carries it.
    """
    import graph_memory.kernel as kernel
    from graph_memory.world_supergraph.contribution_store import (
        load_contribution_record,
    )

    warnings: list[str] = []
    try:
        existing = load_contribution_record(world_root, world_id, contribution_id)
    except Exception as exc:  # noqa: BLE001 — audit must stay best-effort
        warnings.append(f"contribution_record_unreadable:{exc.__class__.__name__}")
        return None, warnings
    if existing is None:
        warnings.append("contribution_record_missing")
        return None, warnings
    if existing.status != "active":
        warnings.append(f"contribution_status:{existing.status}")
        return None, warnings

    try:
        head, _head_revision, head_store = kernel.open_current_world_graph(
            world_root, world_id
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"world_graph_unreadable:{exc.__class__.__name__}")
        return None, warnings

    expected_digest = kernel.compute_contribution_source_payload_sha256(contribution)
    head_digest = (head_store.contribution_source_payload_sha256 or {}).get(
        contribution_id
    )
    if head_digest != expected_digest:
        warnings.append("contribution_source_digest_mismatch_or_missing")
        return None, warnings

    current_id: str | None = head.head_revision_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        try:
            manifest = kernel.load_world_graph_revision_manifest(
                world_root, world_id, current_id
            )
            store = kernel.load_world_graph_revision(world_root, world_id, current_id)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"revision_unreadable:{current_id}:{exc.__class__.__name__}"
            )
            return None, warnings

        digests = store.contribution_source_payload_sha256 or {}
        if digests.get(contribution_id) != expected_digest:
            current_id = manifest.parent_revision_id
            continue

        operations = list(manifest.operation_ids or [])
        introduced_by_ops = contribution_id in operations
        introduced_from_parent = manifest.parent_revision_id == parent_revision_id
        if introduced_by_ops or introduced_from_parent:
            if current_id != head.head_revision_id:
                warnings.append("committed_revision_resolved_via_ancestry_walk")
            return current_id, warnings
        current_id = manifest.parent_revision_id

    warnings.append("contribution_introducing_revision_not_found")
    return None, warnings


def _worldbuilding_confirm_receipt(
    *,
    outcome: str,
    verified: Mapping[str, Any],
    contribution: Any,
    parent_revision_id: str,
    committed_revision_id: str,
    head_advanced: bool,
    accepted_assertion_ids: list[str],
    rejected_assertion_ids: list[str],
    audit_status: ConfirmAuditStatus,
    warnings: list[str],
) -> WorldbuildingWritePlanConfirmReceipt:
    unresolved_mention_ids = [
        mention.mention_id for mention in contribution.unresolved_mentions
    ]
    return WorldbuildingWritePlanConfirmReceipt(
        outcome=outcome,  # type: ignore[arg-type]
        world_id=str(verified["world_id"]),
        plan_id=str(verified["plan_id"]),
        plan_digest=str(verified["plan_digest"]),
        decision_digest=str(verified["decision_digest"]),
        parent_revision_id=parent_revision_id,
        committed_revision_id=committed_revision_id,
        head_advanced=head_advanced,
        contribution_id=contribution.contribution_id,
        applied_assertion_count=len(accepted_assertion_ids),
        accepted_assertion_ids=list(accepted_assertion_ids),
        rejected_assertion_ids=list(rejected_assertion_ids),
        unresolved_mention_ids=unresolved_mention_ids,
        audit_status=audit_status,
        warnings=list(warnings),
    )


def confirm_worldbuilding(
    request: WorldbuildingWritePlanConfirmRequest,
) -> WorldbuildingWritePlanConfirmReceipt:
    """Verify one sealed worldbuilding write plan and commit its rebuilt effect."""
    import graph_memory.kernel as kernel

    plan = request.plan
    plan_payload = plan.model_dump(mode="json", by_alias=True)
    world_root = world_graph_root()
    if (
        world_root.resolve() == live_world_graph_root().resolve()
        and not PRODUCT_CONFIRM_ALLOW_LIVE_WORLD
    ):
        raise ExtractPromoteError(
            "refusing to mutate live world root without allow_live_world",
            code="live_world_refused",
            status_code=403,
            diagnostics=[_diagnostic("live_world_refused", "live world refused")],
        )

    try:
        resolved = resolve_promotable_ingest_run(plan.run_id, root=repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    typed_preview, expected_profile = _load_typed_worldbuilding_preview_for_run(
        resolved
    )
    context = WorldbuildingWritePlanVerificationContext(
        world_id=DEFAULT_WORLD_ID,
        parent_revision_id=plan.parent_revision_id,
        run_id=resolved.run_id,
        source_artifact_id=resolved.source_artifact_id,
        source_revision_id=resolved.source_revision_id,
        source_uri=resolved.sealed_source_uri,
        extraction_profile=expected_profile,
        campaign_scope=resolved.campaign_id or None,
    )

    try:
        head, _rev, _store = kernel.open_current_world_graph(
            world_root, DEFAULT_WORLD_ID
        )
    except (kernel.WorldGraphNotFoundError, ValueError) as exc:
        raise ExtractPromoteError(
            "The World Graph is not initialized.",
            code="world_not_initialized",
            status_code=409,
            diagnostics=[_diagnostic("world_not_initialized", str(exc))],
        ) from exc

    parent = plan.parent_revision_id
    if head.head_revision_id != parent:
        raise ExtractPromoteError(
            "expected parent revision is not the current World Graph head",
            code="stale_parent_revision",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "stale_parent_revision",
                    "expected parent revision is not the current World Graph head",
                )
            ],
        )

    try:
        verified = verify_worldbuilding_write_plan(
            plan_payload,
            preview=typed_preview,
            world_root=world_root,
            context=context,
        )
        contribution = materialize_worldbuilding_contribution(
            world_id=verified["world_id"],
            plan_digest=verified["plan_digest"],
            effect=verified["effect"],
        )
    except WorldbuildingWritePlanError as exc:
        raise ExtractPromoteError(
            str(exc),
            code=exc.code,
            status_code=exc.status_code,
            diagnostics=[_diagnostic(exc.code, str(exc))],
        ) from exc

    if PRODUCT_CONFIRM_DRY_RUN:
        raise ExtractPromoteError(
            "worldbuilding confirm dry_run is not supported",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_request", "dry_run not supported")],
        )

    materialized_accepted = [
        assertion.assertion_id for assertion in contribution.accepted_assertions
    ]
    materialized_rejected = [
        assertion.assertion_id for assertion in contribution.rejected_assertions
    ]

    try:
        result = kernel.merge_contribution_to_revision(
            world_root,
            world_id=verified["world_id"],
            contribution=contribution,
            expected_parent_revision_id=parent,
        )
    except ValueError as exc:
        message = str(exc)
        if "stale parent" in message.lower():
            raise ExtractPromoteError(
                "expected parent revision is not the current World Graph head",
                code="stale_parent_revision",
                status_code=409,
                diagnostics=[_diagnostic("stale_parent_revision", message)],
            ) from exc
        audited_revision, audit_warnings = _worldbuilding_publication_audit(
            world_root=world_root,
            world_id=verified["world_id"],
            contribution_id=contribution.contribution_id,
            parent_revision_id=parent,
            contribution=contribution,
        )
        if audited_revision is not None:
            return _worldbuilding_confirm_receipt(
                outcome="published_audit_degraded",
                verified=verified,
                contribution=contribution,
                parent_revision_id=parent,
                committed_revision_id=audited_revision,
                head_advanced=audited_revision != parent,
                accepted_assertion_ids=materialized_accepted,
                rejected_assertion_ids=materialized_rejected,
                audit_status="degraded",
                warnings=[f"merge_value_error_after_publish:{message}", *audit_warnings],
            )
        raise ExtractPromoteError(
            message,
            code="merge_did_not_publish",
            status_code=409,
            diagnostics=[_diagnostic("merge_did_not_publish", message)],
        ) from exc
    except kernel.WorldGraphNotFoundError as exc:
        raise ExtractPromoteError(
            "The World Graph is not initialized.",
            code="world_not_initialized",
            status_code=409,
            diagnostics=[_diagnostic("world_not_initialized", str(exc))],
        ) from exc
    except Exception as exc:  # noqa: BLE001 — classify post-publication ambiguity
        audited_revision, audit_warnings = _worldbuilding_publication_audit(
            world_root=world_root,
            world_id=verified["world_id"],
            contribution_id=contribution.contribution_id,
            parent_revision_id=parent,
            contribution=contribution,
        )
        if audited_revision is not None:
            return _worldbuilding_confirm_receipt(
                outcome="published_audit_degraded",
                verified=verified,
                contribution=contribution,
                parent_revision_id=parent,
                committed_revision_id=audited_revision,
                head_advanced=audited_revision != parent,
                accepted_assertion_ids=materialized_accepted,
                rejected_assertion_ids=materialized_rejected,
                audit_status="degraded",
                warnings=[
                    f"post_publication_exception:{exc.__class__.__name__}",
                    *audit_warnings,
                ],
            )
        raise ExtractPromoteError(
            "worldbuilding confirm failed before publication was proven",
            code="extract_promote_internal_error",
            status_code=500,
            diagnostics=[
                _diagnostic(
                    "extract_promote_internal_error",
                    f"{exc.__class__.__name__}: {exc}",
                )
            ],
        ) from exc

    published = bool(result.published)
    accepted_assertion_ids = list(result.accepted_assertion_ids or materialized_accepted)
    rejected_assertion_ids = list(result.rejected_assertion_ids or materialized_rejected)
    committed = str(result.revision_id or "").strip()

    if published and committed:
        return _worldbuilding_confirm_receipt(
            outcome="committed",
            verified=verified,
            contribution=contribution,
            parent_revision_id=parent,
            committed_revision_id=committed,
            head_advanced=True,
            accepted_assertion_ids=accepted_assertion_ids,
            rejected_assertion_ids=rejected_assertion_ids,
            audit_status="ok",
            warnings=[],
        )

    audited_revision, audit_warnings = _worldbuilding_publication_audit(
        world_root=world_root,
        world_id=verified["world_id"],
        contribution_id=contribution.contribution_id,
        parent_revision_id=parent,
        contribution=contribution,
    )
    if audited_revision is not None:
        warnings = list(audit_warnings)
        if published and not committed:
            warnings.insert(0, "published_without_revision_id")
        elif not published:
            warnings.insert(0, "merge_reported_unpublished_but_authority_present")
        return _worldbuilding_confirm_receipt(
            outcome="published_audit_degraded",
            verified=verified,
            contribution=contribution,
            parent_revision_id=parent,
            committed_revision_id=audited_revision,
            head_advanced=audited_revision != parent,
            accepted_assertion_ids=accepted_assertion_ids,
            rejected_assertion_ids=rejected_assertion_ids,
            audit_status="degraded",
            warnings=warnings,
        )

    if not published:
        raise ExtractPromoteError(
            "merge did not publish",
            code="merge_did_not_publish",
            status_code=409,
            diagnostics=[_diagnostic("merge_did_not_publish", "merge did not publish")],
            failure_payload=result.model_dump(mode="json"),
        )
    raise ExtractPromoteError(
        "committed revision missing after confirm",
        code="extract_promote_internal_error",
        status_code=500,
        diagnostics=[
            _diagnostic(
                "extract_promote_internal_error",
                "committed revision missing after confirm",
            )
        ],
    )



def _project_assertion_fields(
    review_package: dict[str, Any],
    normalized_assertion_ids: tuple[str, ...],
    *,
    world_root: Path,
) -> tuple[list[str], list[str], list[str]]:
    """Project accepted assertion and affected object ids from the sealed package.

    Reuses ``resolve_merged_contribution_from_package`` — the same helper
    ``confirm_extract_promote`` uses to build the ONE atomic contribution —
    so a multi-slice (standing_context + source_extraction) selection is
    projected identically here and at actual publish time (PR011A3 P0/P1).
    """
    warnings: list[str] = []
    try:
        world_id_hint = str(
            ((review_package or {}).get("effect") or {}).get("world_id")
            or DEFAULT_WORLD_ID
        )
        _verified, contribution = resolve_merged_contribution_from_package(
            review_package=review_package,
            confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
            world_id_hint=world_id_hint,
            root=world_root,
            expected_parent_revision_id=None,
            assertion_ids=normalized_assertion_ids,
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
        world_id_hint = str(
            ((request.review_package or {}).get("effect") or {}).get("world_id")
            or DEFAULT_WORLD_ID
        )
        verified, contribution = resolve_merged_contribution_from_package(
            review_package=request.review_package,
            confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
            world_id_hint=world_id_hint,
            root=world_root,
            expected_parent_revision_id=None,
            assertion_ids=normalized_assertion_ids,
        )
        world_id = str(verified["world_id"])
        head, _rev, _store = kernel.open_current_world_graph(world_root, world_id)
        index = load_contribution_index(world_root, world_id)
        if contribution.contribution_id not in index.active_contribution_ids:
            return None
        try:
            existing = load_contribution_record(
                world_root, world_id, contribution.contribution_id
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
        "world_id": world_id,
        "proposal_id": verified["proposal_id"],
        "proposal_digest": verified["proposal_digest"],
        "parent_revision_id": str(verified["parent_revision_id"]),
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
    if (
        str((request.review_package or {}).get("schema") or "").strip()
        == "dmb_worldbuilding_write_plan_v1"
    ):
        raise ExtractPromoteError(
            "worldbuilding write plans are inert and are not confirmable",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                _diagnostic(
                    "invalid_request",
                    "worldbuilding write plans are not accepted by /confirm",
                )
            ],
        )
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
    "confirm_worldbuilding",
    "get_status",
    "prepare_worldbuilding",
    "prepare",
    "resolve_promote_source_uri",
]
