"""Live-control service shell for extract → World Supergraph promote."""


from __future__ import annotations


import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, Mapping


from apps.live_control_server.config import (
    extract_promote_source_root,
    repo_root,
    world_graph_root,
)
from apps.live_control_server.models.extract_promote import (
    SERVER_CONFIRMING_PRINCIPAL,
    SERVER_PREPARED_BY,
    ConfirmAuditStatus,
    ConfirmOutcome,
    ExactRunReviewAssertion,
    ExactRunReviewEvidence,
    ExactRunReviewPackage,
    RecapSemanticDecisionRequest,
    RecapSemanticDecisionResponse,
    ExtractPromoteConfirmReceipt,
    ExtractPromoteConfirmRequest,
    ExtractPromoteDiagnostic,
    ExtractPromoteErrorResponse,
    ExtractPromotePrepareRequest,
    ExtractPromotePrepareResponse,
    ExtractPromoteReviewSummary,
    ExtractPromotionReviewItem,
    ExtractPromoteStatusResponse,
    FirstWorldGraphConfirmReceipt,
    FirstWorldGraphConfirmRequest,
    FirstWorldGraphPlan,
    FirstWorldGraphPrepareRequest,
    WorldbuildingWritePlanConfirmReceipt,
    WorldbuildingWritePlanConfirmRequest,
    WorldbuildingWritePlanPrepareRequest,
    WorldbuildingWritePlanResponse,
)
from apps.live_control_server.models.candidate_graph_admission import (
    CandidateAdmissionIntegrityError,
)
from apps.live_control_server.services.first_world_graph import (
    resolve_first_world_capability,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    VerifiedManagedWorldBinding,
    resolve_managed_world_binding,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
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
    ExtractPromoteWorldError,
    get_extract_promote_status,
    resolve_merged_contribution_from_package,
)
from graph_memory.extract_promote_proposal import (
    PromoteProposalError,
    compute_proposal_digest,
)


_PUBLICATION_TARGET_KEY = "managed_world_publication_target"
_PUBLICATION_TARGET_SCHEMA = "dmb_managed_world_publication_target_v1"
_RECAP_CONTEXT_KEY = "world_campaign_ingest_context"


def _resolve_publication_target(managed_world_id: str) -> VerifiedManagedWorldBinding:
    try:
        return resolve_managed_world_binding(managed_world_id)
    except WorldGraphProjectionServiceError as exc:
        raise ExtractPromoteError(
            "Selected managed World has no verified active native Graph binding; reselect and prepare again.",
            code="publication_target_unavailable",
            status_code=exc.status_code,
            diagnostics=[_diagnostic(exc.code, str(exc))],
        ) from exc


def _target_basis(binding: VerifiedManagedWorldBinding) -> dict[str, Any]:
    return {
        "schema": _PUBLICATION_TARGET_SCHEMA,
        "managed_world_id": binding.managed_world_id,
        "native_world_id": binding.native_world_id,
        "binding_version": binding.binding_version,
    }


def _seal_publication_target(
    package: Mapping[str, Any], binding: VerifiedManagedWorldBinding
) -> dict[str, Any]:
    sealed = dict(package)
    effect = dict(sealed.get("effect") or {})
    if str(effect.get("world_id") or "").strip() != binding.native_world_id:
        raise ExtractPromoteError(
            "Prepared proposal target differs from the verified native World.",
            code="publication_target_mismatch", status_code=409,
        )
    effect[_PUBLICATION_TARGET_KEY] = _target_basis(binding)
    sealed["effect"] = effect
    sealed["proposal_digest"] = compute_proposal_digest(effect)
    return sealed


def _seal_recap_ingest_context(
    package: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, Any]:
    sealed = dict(package)
    effect = dict(sealed.get("effect") or {})
    effect[_RECAP_CONTEXT_KEY] = dict(context)
    sealed["effect"] = effect
    sealed["proposal_digest"] = compute_proposal_digest(effect)
    return sealed


def _assert_current_recap_ingest_context(
    context: Mapping[str, Any], *, managed_world_id: str, campaign_id: str
) -> dict[str, Any]:
    from apps.live_control_server.services.recap_ingest_context import (
        read_recap_ingest_context,
    )

    try:
        current = read_recap_ingest_context(
            managed_world_id=managed_world_id, campaign_id=campaign_id
        ).as_lineage()
    except Exception as exc:  # noqa: BLE001
        raise ExtractPromoteError(
            "World/campaign ingestion authority is unavailable; prepare again.",
            code="recap_ingest_context_changed",
            status_code=409,
        ) from exc
    identity_fields = (
        "schema",
        "managed_world_id",
        "native_world_id",
        "binding_version",
        "campaign_id",
    )
    if any(context.get(key) != current.get(key) for key in identity_fields):
        raise ExtractPromoteError(
            "World/campaign membership or binding changed; prepare again.",
            code="recap_ingest_context_changed",
            status_code=409,
        )
    return current


def _assert_current_publication_target(
    package: Mapping[str, Any]
) -> VerifiedManagedWorldBinding:
    effect = package.get("effect")
    if not isinstance(effect, dict) or package.get("proposal_digest") != compute_proposal_digest(effect):
        raise ExtractPromoteError(
            "Publication proposal seal is missing or changed; prepare again.",
            code="publication_target_changed", status_code=409,
        )
    sealed = effect.get(_PUBLICATION_TARGET_KEY)
    if not isinstance(sealed, dict) or sealed.get("schema") != _PUBLICATION_TARGET_SCHEMA:
        raise ExtractPromoteError(
            "Publication target is not sealed; prepare again.",
            code="publication_target_required", status_code=409,
        )
    managed_world_id = sealed.get("managed_world_id")
    if not isinstance(managed_world_id, str) or not managed_world_id.strip():
        raise ExtractPromoteError(
            "Publication target is invalid; prepare again.",
            code="publication_target_changed", status_code=409,
        )
    try:
        current = _resolve_publication_target(managed_world_id)
    except ExtractPromoteError as exc:
        raise ExtractPromoteError(
            "Publication target binding is unavailable; prepare again.",
            code="publication_target_changed", status_code=409,
        ) from exc
    if sealed != _target_basis(current) or effect.get("world_id") != current.native_world_id:
        raise ExtractPromoteError(
            "Publication target binding changed; prepare again.",
            code="publication_target_changed", status_code=409,
        )
    return current


class WorldGraphNotFoundError(Exception):
    """World graph missing or unreadable (Buddy store path)."""


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
        run_status: str | None = None,
        inspection_status: Literal["ready", "blocked", "invalid_evidence"]
        | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])
        self.failure_payload = failure_payload
        self.run_status = run_status
        self.inspection_status = inspection_status


    def response(self) -> ExtractPromoteErrorResponse:
        return ExtractPromoteErrorResponse(
            code=self.code,
            message=str(self),
            status_code=self.status_code,
            diagnostics=self.diagnostics,
            failure_result=self.failure_payload,
            run_status=self.run_status,
            inspection_status=self.inspection_status,
        )


def _diagnostic(code: str, message: str) -> ExtractPromoteDiagnostic:
    return ExtractPromoteDiagnostic(code=code, message=message, severity="error")


def _review_package_inspection_status(
    diagnostics: list[ExtractPromoteDiagnostic],
) -> Literal["blocked", "invalid_evidence"]:
    codes = {item.code for item in diagnostics}
    if "false_anchor_quote" in codes:
        return "invalid_evidence"
    return "blocked"


def _with_review_package_inspection_context(
    exc: ExtractPromoteError,
    *,
    run_status: str,
) -> ExtractPromoteError:
    """Attach lifecycle + inspection fields to post-resolution package failures.


    Pre-resolution identity failures (unknown run, not reviewable, etc.) are
    outside this helper. Every ``ExtractPromoteError`` raised while building the
    review package after a successful ``resolve_promotable_ingest_run`` is an
    inspection failure: the run may remain ``reviewable`` while the package is
    ``blocked`` or ``invalid_evidence``.
    """
    if exc.run_status is not None and exc.inspection_status is not None:
        return exc
    return ExtractPromoteError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        diagnostics=exc.diagnostics,
        failure_payload=exc.failure_payload,
        run_status=run_status,
        inspection_status=_review_package_inspection_status(exc.diagnostics),
    )


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


def _paragraph_for_span(
    source_lines: list[str], *, start_line: int, end_line: int
) -> str:
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
            _diagnostic(
                "worldbuilding_draft_not_promotable", _WORLDBUILDING_INSPECT_ONLY_REASON
            )
        ],
    )


def _is_worldbuilding_inspect_only(resolved: Any) -> bool:
    return (getattr(resolved, "source_domain", None) or "").strip() == "worldbuilding"



def _candidate_quote_occurrences(*, candidate_payload: dict[str, Any], source_prose: str,
    source_artifact_id: str, span_index: Any) -> list[dict[str, Any]]:
    """Inspect only literal quote failures; all other evidence checks remain strict."""
    from graph_memory.anchor_quotes import find_anchor_quote_matches
    projected = _assert_and_project_candidate_evidence(
        candidate_payload=candidate_payload, source_prose=source_prose,
        source_artifact_id=source_artifact_id, span_index=span_index,
        inspect_false_anchor_quotes=True,
    )
    assertions = {item.assertion_id: item for item in projected}
    failures = []
    for collection, identifier in (("nodes", "node_id"), ("edges", "edge_id")):
        for record in candidate_payload.get(collection, []):
            assertion = assertions[record[identifier]]
            for index, ref in enumerate(record.get("evidence_refs", [])):
                paragraph = assertion.evidence[index].paragraph_text
                for quote_index, quote in enumerate(ref.get("anchor_quotes", [])):
                    if not find_anchor_quote_matches(paragraph, [quote]):
                        failures.append({"record_kind": "node" if collection == "nodes" else "edge",
                            "record_id": record[identifier], "evidence_index": index,
                            "quote_index": quote_index, "quote": quote,
                            "source_span_ref_id": ref.get("source_span_ref_id"),
                            "diagnostic": "false_anchor_quote", "reference": ref})
    return failures

def _assert_and_project_candidate_evidence(
    *,
    candidate_payload: dict[str, Any],
    source_prose: str,
    source_artifact_id: str,
    span_index: Any,
    inspect_false_anchor_quotes: bool = False,
) -> list[ExactRunReviewAssertion]:
    """Fail closed when candidate evidence is not bound to frozen span content.


    Uses the typed candidate validator, requires every promotable node/edge
    evidence ref to resolve against the span index + SourceArtifact, and verifies
    anchor quotes against canonical source paragraph bytes.
    """
    from graph_memory.anchor_quotes import find_anchor_quote_matches
    from apps.live_control_server.services.candidate_graph_admission import (
        validate_candidate_document_integrity,
    )


    try:
        typed = validate_candidate_document_integrity(candidate_payload)
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
                        _diagnostic(
                            "source_artifact_mismatch", artifact_id or "<missing>"
                        ),
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
            invalid_quotes: list[str] = []
            for quote in raw_quotes:
                if not find_anchor_quote_matches(paragraph, [quote]):
                    if inspect_false_anchor_quotes:
                        invalid_quotes.append(quote)
                        continue
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
            projected.append(
                ExactRunReviewEvidence(
                    source_artifact_id=artifact_id,
                    source_span_ref_id=span_id,
                    paragraph_text=paragraph,
                    anchor_quotes=raw_quotes,
                    invalid_anchor_quotes=invalid_quotes,
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


def _recap_semantic_assessment(resolved, run_record=None):
    """Read canonical child and parent; legacy manifest runs have no gate."""
    canonical = (
        getattr(resolved, "source_span_index_path", None) is not None
        or "resolved via canonical ExtractionRun registry" in getattr(resolved, "diagnostics", ())
    )
    if not canonical:
        return None, None
    if getattr(resolved, "source_span_index_path", None) is None:
        raise ExtractPromoteError(
            "canonical extraction run lost its span-index binding",
            code="run_not_promotable", status_code=409,
        )
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run,
    )
    from apps.live_control_server.services.recap_semantic_disposition import (
        assess_recap_semantics,
        is_recap_correction,
    )

    try:
        run = run_record or get_extraction_run(repo_root(), resolved.run_id)
    except GraphRunRegistryError as exc:
        raise ExtractPromoteError(
            "canonical extraction run could not be re-read",
            code="run_not_promotable", status_code=409,
        ) from exc
    if not is_recap_correction(run):
        return run, None
    parent = None
    parent_id = run.lineage.get("parent_run_id")
    if isinstance(parent_id, str) and parent_id.strip():
        try:
            parent = get_extraction_run(repo_root(), parent_id)
        except GraphRunRegistryError as exc:
            if exc.status_code != 404:
                raise ExtractPromoteError(
                    "canonical extraction parent is unavailable",
                    code="run_not_promotable", status_code=exc.status_code,
                ) from exc
            # The child's own exact source package remains inspectable. A
            # missing parent makes its semantic basis invalid and keeps it held.
    return run, assess_recap_semantics(
        run, parent=parent, source_revision_id=resolved.source_revision_id,
        root=repo_root(),
    )


def _bind_recap_semantic_effect(package, run, assessment):
    """Add the exact accepted child pin before the final proposal seal."""
    from apps.live_control_server.services.recap_semantic_disposition import (
        EFFECT_KEY,
        accepted_effect_binding,
    )
    from graph_memory.extract_promote_proposal import compute_proposal_digest

    bound = dict(package)
    effect = dict(bound.get("effect") or {})
    if not effect or EFFECT_KEY in effect:
        raise PromoteProposalError("recap semantic gate cannot be bound")
    effect[EFFECT_KEY] = accepted_effect_binding(run, assessment)
    bound["effect"] = effect
    bound["proposal_digest"] = compute_proposal_digest(effect)
    return bound


def _candidate_owner_for_locator(locator: str):
    """Ask APP-STATE for exact component ownership, including changed statuses."""
    from application_state.errors import ApplicationStateError
    from application_state.ingest.service import (
        lookup_extraction_run_by_candidate_component,
    )

    path = _parse_source_uri_to_path(locator)
    if not path.is_file():
        raise ExtractPromoteError(
            "sealed candidate could not be resolved at confirm",
            code="candidate_binding_invalid", status_code=409,
        )
    try:
        relative = path.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    owners = {}
    try:
        # Both spellings are accepted by the canonical component URI resolver.
        # Two distinct matches are ambiguous even if each lookup is unique.
        for uri in (relative, f"repo://{relative}"):
            result = lookup_extraction_run_by_candidate_component(
                uri=uri, sha256=digest
            )
            if result.kind == "ambiguous":
                raise ExtractPromoteError(
                    "candidate component belongs to multiple extraction runs",
                    code="candidate_binding_invalid", status_code=409,
                )
            if result.kind == "unique":
                owners[result.run.run_id] = result.run
    except ApplicationStateError as exc:
        raise ExtractPromoteError(
            "candidate owner lookup is unavailable",
            code="candidate_binding_invalid", status_code=exc.status_code,
        ) from exc
    if len(owners) > 1:
        raise ExtractPromoteError(
            "candidate component belongs to multiple extraction runs",
            code="candidate_binding_invalid", status_code=409,
        )
    if not owners and path.is_relative_to(
        (repo_root().resolve() / "out" / "graph_memory" / "derived_candidates").resolve()
    ):
        raise ExtractPromoteError(
            "derived candidate has no exact canonical run binding",
            code="candidate_binding_invalid", status_code=409,
        )
    return next(iter(owners.values()), None)


def _assert_recap_semantics_at_confirm(locator: str, review_package) -> None:
    """Re-prove a marked child immediately before the governed World writer."""
    from apps.live_control_server.services.recap_semantic_disposition import (
        EFFECT_KEY,
        assert_current_effect_binding,
        is_recap_correction,
    )

    effect = (review_package or {}).get("effect") or {}
    binding = effect.get(EFFECT_KEY)
    owner = _candidate_owner_for_locator(locator)
    if owner is None or not is_recap_correction(owner):
        if binding is not None:
            raise ExtractPromoteError(
                "recap semantic gate has no matching canonical child",
                code="candidate_binding_invalid", status_code=409,
            )
        return
    if owner.status.value != "reviewable" or owner.source_domain != "recap":
        raise ExtractPromoteError(
            "corrected recap child is no longer reviewable",
            code="recap_semantic_hold", status_code=409,
        )
    try:
        resolved = resolve_promotable_ingest_run(owner.run_id, root=repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc
    if resolved.candidate_graph_path.resolve() != _parse_source_uri_to_path(locator):
        raise ExtractPromoteError(
            "candidate locator disagrees with canonical child",
            code="candidate_binding_invalid", status_code=409,
        )
    current, assessment = _recap_semantic_assessment(resolved)
    if current is None or assessment is None or not assessment.accepted:
        raise ExtractPromoteError(
            "corrected recap child is held for semantic review",
            code="recap_semantic_hold", status_code=409,
        )
    try:
        assert_current_effect_binding(current, assessment, binding)
    except ValueError as exc:
        raise ExtractPromoteError(
            str(exc), code="candidate_binding_invalid", status_code=409,
        ) from exc


def decide_recap_semantic_disposition(
    run_id: str,
    request: RecapSemanticDecisionRequest,
    *,
    reviewer_id: str,
) -> RecapSemanticDecisionResponse:
    """Record an explicit operator decision without altering evidence or World."""
    from application_state.errors import ApplicationStateError
    from application_state.ingest.service import (
        RecapSemanticBasisV1,
        RecapSemanticBasisV2,
        RecapSemanticBasisV3,
        RecapSemanticBasisV4,
        RecapSemanticBasisV5,
        RecapSemanticBasisV6,
        RecapSemanticBasisV7,
        RecapSemanticBasisV8,
        RecapSemanticBasisV9,
        RecapSemanticDispositionCommandV1,
        record_recap_semantic_disposition,
    )
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run,
        get_reviewable_extraction_run,
    )
    from apps.live_control_server.services.recap_semantic_disposition import (
        assess_recap_semantics,
        CANDIDATE_DERIVATION,
        CANDIDATE_DERIVATION_V2,
        CANDIDATE_DERIVATION_V3,
        CANDIDATE_DERIVATION_V4,
        CANDIDATE_DERIVATION_V5,
        CANDIDATE_DERIVATION_V6,
        CANDIDATE_DERIVATION_V7,
        CANDIDATE_DERIVATION_V8,
        is_recap_correction,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        get_source_artifact,
    )

    try:
        run = get_reviewable_extraction_run(repo_root(), run_id)
        if not is_recap_correction(run):
            raise ExtractPromoteError(
                "run is not a corrected recap child",
                code="recap_semantic_decision_invalid", status_code=409,
            )
        parent_id = run.lineage.get("parent_run_id")
        parent = get_extraction_run(repo_root(), parent_id) if isinstance(parent_id, str) else None
        artifact = get_source_artifact(repo_root(), run.source_artifact_id)
    except (GraphRunRegistryError, SourceArtifactRegistryError) as exc:
        raise ExtractPromoteError(
            "canonical corrected recap evidence is unavailable",
            code="recap_semantic_decision_invalid", status_code=409,
        ) from exc
    assessment = assess_recap_semantics(
        run, parent=parent, source_revision_id=artifact.content_sha256,
        root=repo_root(),
    )
    if assessment.basis is None or assessment.basis_sha256 is None:
        raise ExtractPromoteError(
            "corrected recap semantic basis is invalid",
            code="recap_semantic_decision_invalid", status_code=409,
        )
    if request.candidate_sha256 != assessment.basis["candidate_sha256"]:
        raise ExtractPromoteError(
            "candidate digest does not match corrected recap child",
            code="recap_semantic_decision_conflict", status_code=409,
        )
    if request.decision == "accepted":
        resolved = resolve_promotable_ingest_run(run_id, root=repo_root())
        payload = json.loads(resolved.candidate_graph_path.read_text(encoding="utf-8"))
        _assert_candidate_scope_matches_run(payload, campaign_id=run.campaign_id, session_id=run.session_id)
        _assert_and_project_candidate_evidence(
            candidate_payload=payload,
            source_prose=resolved.normalized_recap_path.read_text(encoding="utf-8"),
            source_artifact_id=run.source_artifact_id,
            span_index=_load_frozen_span_index_for_resolved_run(resolved),
        )
    try:
        basis_type = (
            RecapSemanticBasisV9 if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V8
            else RecapSemanticBasisV8 if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V7
            else RecapSemanticBasisV7 if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V6
            else RecapSemanticBasisV6 if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V5
            else RecapSemanticBasisV5 if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V4
            else RecapSemanticBasisV4 if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V3
            else RecapSemanticBasisV3 if run.lineage.get("derivation") == CANDIDATE_DERIVATION_V2
            else RecapSemanticBasisV2 if run.lineage.get("derivation") == CANDIDATE_DERIVATION
            else RecapSemanticBasisV1
        )
        basis = basis_type.model_validate(assessment.basis)
        decision = RecapSemanticDispositionCommandV1(
            state=request.decision,
            review_decision_ref=request.review_decision_ref,
            reviewer_id=reviewer_id,
        )
        decided = record_recap_semantic_disposition(
            run_id, expected_revision=request.expected_revision,
            basis=basis, decision=decision,
        )
    except ApplicationStateError as exc:
        raise ExtractPromoteError(
            "corrected recap decision conflicts with canonical run",
            code="recap_semantic_decision_conflict", status_code=exc.status_code,
        ) from exc
    receipt = decided.lineage["semantic_disposition"]
    return RecapSemanticDecisionResponse(
        run_id=decided.run_id, revision=decided.revision,
        candidate_sha256=assessment.basis["candidate_sha256"],
        state=receipt["state"], basis_sha256=receipt["basis_sha256"],
        review_decision_ref=receipt["review_decision_ref"],
        reviewer_id=receipt["reviewer_id"], decided_at=receipt["decided_at"],
    )


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


    # Entire post-resolution package construction is one inspection boundary:
    # source prose, candidate parse, scope check, frozen span-index load/validate,
    # and evidence projection all share runStatus + inspectionStatus enrichment.
    try:
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
            inspect_false_anchor_quotes=True,
        )

        invalid_evidence_count = sum(
            len(evidence.invalid_anchor_quotes)
            for assertion in assertions
            for evidence in assertion.evidence
        )


        inspect_only = _is_worldbuilding_inspect_only(resolved)
        capability = resolve_first_world_capability(
            repo=repo_root(),
            world_root=world_graph_root(),
            source_domain=resolved.source_domain,
            world_id=getattr(resolved, "world_id", None),
            source_artifact_id=resolved.source_artifact_id,
        )
        from apps.live_control_server.services.graph_run_registry import (
            GraphRunRegistryError,
            get_extraction_run,
        )

        derived_from_run_id: str | None = None
        semantic_assessment = None
        try:
            run_record = get_extraction_run(repo_root(), resolved.run_id)
            if run_record.lineage.get("derivation") == "operator_literal_evidence_correction_v1":
                derived_from_run_id = str(run_record.lineage.get("parent_run_id") or "") or None
            from apps.live_control_server.services.recap_semantic_disposition import (
                is_recap_correction,
            )

            if is_recap_correction(run_record):
                derived_from_run_id = str(run_record.lineage.get("parent_run_id") or "") or None
                _, semantic_assessment = _recap_semantic_assessment(resolved, run_record)
        except GraphRunRegistryError as exc:
            if exc.status_code != 404:
                raise
        semantic_held = semantic_assessment is not None and not semantic_assessment.accepted
        return ExactRunReviewPackage(
            run_id=resolved.run_id,
            derived_from_run_id=derived_from_run_id,
            source_domain=resolved.source_domain,
            source_artifact_id=resolved.source_artifact_id,
            source_revision_id=resolved.source_revision_id,
            campaign_id=resolved.campaign_id or None,
            session_id=resolved.session_id or None,
            source_prose=source_prose,
            assertions=assertions,
            inspection_status="invalid_evidence" if invalid_evidence_count else "ready",
            invalid_evidence_count=invalid_evidence_count,
            diagnostics=[*resolved.diagnostics, *([
                "unresolved_quote_binding:" + json.dumps({
                    "candidate_sha256": hashlib.sha256(resolved.candidate_graph_path.read_bytes()).hexdigest(),
                    "source_sha256": hashlib.sha256(resolved.normalized_recap_path.read_bytes()).hexdigest(),
                    "span_index_sha256": hashlib.sha256(resolved.source_span_index_path.read_bytes()).hexdigest(),
                    "occurrences": [{key: value for key, value in item.items() if key != "reference"}
                        | {"reference_sha256": hashlib.sha256(json.dumps(item["reference"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
                        for item in _candidate_quote_occurrences(candidate_payload=candidate_payload,
                            source_prose=source_prose, source_artifact_id=resolved.source_artifact_id, span_index=span_index)],
                }, ensure_ascii=False, sort_keys=True)
            ] if invalid_evidence_count else [])],
            promotable=not inspect_only and invalid_evidence_count == 0 and not semantic_held,
            promotable_reason=(
                "Candidate evidence contains nonliteral anchor quotes; publication is blocked."
                if invalid_evidence_count
                else _WORLDBUILDING_INSPECT_ONLY_REASON if inspect_only
                else semantic_assessment.reason if semantic_held else None
            ),
            semantic_disposition=(
                {
                    "version": 1,
                    "state": (
                        semantic_assessment.disposition["state"]
                        if semantic_assessment.disposition is not None else "held"
                    ),
                    "basisSha256": semantic_assessment.basis_sha256,
                    "reason": semantic_assessment.reason,
                }
                if semantic_assessment is not None else None
            ),
            world_id=capability.world_id,
            world_state=capability.world_state,
            first_world_publish_eligible=(
                capability.eligible and invalid_evidence_count == 0 and not semantic_held
            ),
            first_world_publish_reason=(
                "Candidate evidence contains nonliteral anchor quotes; publication is blocked."
                if invalid_evidence_count else semantic_assessment.reason if semantic_held
                else capability.reason
            ),
        )
    except ExtractPromoteError as exc:
        raise _with_review_package_inspection_context(
            exc, run_status=resolved.status
        ) from exc


def _require_canonical_source_artifact(source_artifact_id: str):
    """Resolve the run's registry source artifact or fail closed.

    Product prepare must not synthesize a recap SourceArtifact from candidate
    fields when the canonical registry record is missing or malformed.
    """
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        get_source_artifact,
    )

    try:
        return get_source_artifact(repo_root(), source_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise ExtractPromoteError(
            "canonical source artifact is unavailable for recap prepare",
            code="invalid_request",
            status_code=getattr(exc, "status_code", 422) or 422,
            diagnostics=[_diagnostic("source_artifact_missing", str(exc))],
        ) from exc


def prepare(
    request: ExtractPromotePrepareRequest,
) -> ExtractPromotePrepareResponse:
    if request.managed_world_id is None:
        raise ExtractPromoteError(
            "Select a managed World publication target before preparing.",
            code="publication_target_required", status_code=422,
        )
    target = _resolve_publication_target(request.managed_world_id)
    try:
        resolved = resolve_promotable_ingest_run(request.run_id, root=repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc

    declared_world_id = str(getattr(resolved, "world_id", None) or "").strip()
    if declared_world_id and declared_world_id != target.native_world_id:
        raise ExtractPromoteError(
            "Run source World declaration differs from selected native World.",
            code="source_world_mismatch", status_code=409,
        )

    canonical_run, semantic_assessment = _recap_semantic_assessment(resolved)
    if semantic_assessment is not None and not semantic_assessment.accepted:
        raise ExtractPromoteError(
            semantic_assessment.reason or "recap semantic review is required",
            code="recap_semantic_hold",
            status_code=409,
        )

    recap_context = getattr(resolved, "ingest_context", None)
    prepared_recap_context: dict[str, Any] | None = None
    if resolved.source_domain == "recap":
        if isinstance(recap_context, dict):
            if (
                recap_context.get("campaign_id") != resolved.campaign_id
                or recap_context.get("native_world_id") != target.native_world_id
                or recap_context.get("managed_world_id") != target.managed_world_id
            ):
                raise ExtractPromoteError(
                    "Recap run World/campaign context differs from the selected managed World.",
                    code="recap_ingest_context_mismatch",
                    status_code=409,
                )
            prepared_recap_context = _assert_current_recap_ingest_context(
                recap_context,
                managed_world_id=target.managed_world_id,
                campaign_id=resolved.campaign_id,
            )


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


    from apps.live_control_server import config as _config


    source_artifact = _require_canonical_source_artifact(resolved.source_artifact_id)
    artifact_world_id = str(getattr(source_artifact, "world_id", None) or "").strip()
    if artifact_world_id and artifact_world_id != target.native_world_id:
        raise ExtractPromoteError(
            "SourceArtifact World declaration differs from selected native World.",
            code="source_world_mismatch", status_code=409,
        )

    prepare_kwargs = dict(
        candidate_graph=payload,
        source_uri=resolved.sealed_source_uri,
        source_revision_id=resolved.source_revision_id,
        prepared_by=SERVER_PREPARED_BY,
        world_id=target.native_world_id,
        source_artifact_id=resolved.source_artifact_id,
        source_artifact=source_artifact,
        campaign_scope=resolved.campaign_id,
        extraction_profile=extraction_profile,
        node_ids=request.node_ids,
        include_edges=True,
        candidate_graph_path=str(path),
        repo_root=repo_root(),
        disclose_source_digest=False,
        registry_context_graph=registry_payload,
    )
    try:
        if (
            _config.world_graph_authority_mode()
            == _config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
        ):
            from apps.live_control_server.integrations.dungeonmind import (
                world_graph_writes,
            )


            try:
                mutation_context = world_graph_writes.load_production_mutation_context(
                    target.native_world_id
                )
            except world_graph_writes.WorldGraphWriteError as exc:
                raise ExtractPromoteError(
                    str(exc),
                    code=exc.code,
                    status_code=exc.status_code,
                    diagnostics=[_diagnostic(exc.code, str(exc))],
                ) from exc
            if prepared_recap_context is not None and getattr(
                mutation_context, "head_revision_id", None
            ) != prepared_recap_context.get("head_revision_id"):
                raise ExtractPromoteError(
                    "World Graph head changed during review preparation; prepare again.",
                    code="recap_ingest_context_changed",
                    status_code=409,
                )
            from apps.live_control_server.services.candidate_graph_admission import (
                prepare_candidate_graph_admission,
            )

            result = prepare_candidate_graph_admission(
                **prepare_kwargs,
                mutation_context=mutation_context,
            )
            if semantic_assessment is not None:
                assert canonical_run is not None
                package = _bind_recap_semantic_effect(
                    result.review_package, canonical_run, semantic_assessment
                )
                result = replace(
                    result,
                    review_package=package,
                    proposal_digest=str(package["proposal_digest"]),
                )

            sealed = world_graph_writes.bind_identity_ledger_to_package(
                result.review_package, mutation_context
            )
            result = replace(
                result,
                review_package=sealed,
                proposal_digest=str(sealed["proposal_digest"]),
            )
        else:
            from apps.live_control_server.services.candidate_graph_admission import (
                prepare_candidate_graph_admission,
            )

            result = prepare_candidate_graph_admission(
                **prepare_kwargs,
                world_root=world_graph_root(),
            )
            if semantic_assessment is not None:
                assert canonical_run is not None
                package = _bind_recap_semantic_effect(
                    result.review_package, canonical_run, semantic_assessment
                )
                result = replace(
                    result,
                    review_package=package,
                    proposal_digest=str(package["proposal_digest"]),
                )
    except CandidateAdmissionIntegrityError as exc:
        raise ExtractPromoteError(
            str(exc),
            code="candidate_invalid",
            status_code=422,
            diagnostics=[
                _diagnostic(item.code, item.message) for item in exc.diagnostics
            ],
        ) from exc
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
            "active head for the selected native World before merging.",
            code="world_not_initialized",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "world_not_initialized",
                    f"no world graph head for world_id={target.native_world_id!r}",
                )
            ],
        ) from exc

    sealed_target = _seal_publication_target(result.review_package, target)
    if prepared_recap_context is not None:
        if result.parent_revision_id != prepared_recap_context.get("head_revision_id"):
            raise ExtractPromoteError(
                "Prepared publication parent differs from the observed review head.",
                code="recap_ingest_context_changed",
                status_code=409,
            )
        current_prepared_context = _assert_current_recap_ingest_context(
            prepared_recap_context,
            managed_world_id=target.managed_world_id,
            campaign_id=resolved.campaign_id,
        )
        if current_prepared_context != prepared_recap_context:
            raise ExtractPromoteError(
                "World Graph head changed during review preparation; prepare again.",
                code="recap_ingest_context_changed",
                status_code=409,
            )
        sealed_target = _seal_recap_ingest_context(sealed_target, prepared_recap_context)
    # A prepare spanning a binding edit must not return a reviewable stale target.
    _assert_current_publication_target(sealed_target)
    result = replace(
        result,
        review_package=sealed_target,
        proposal_digest=str(sealed_target["proposal_digest"]),
    )


    return ExtractPromotePrepareResponse(
        proposal_id=result.proposal_id,
        proposal_digest=result.proposal_digest,
        parent_revision_id=result.parent_revision_id,
        world_id=result.world_id,
        accepted_proposals_count=result.accepted_proposals_count,
        unresolved_mentions_count=result.unresolved_mentions_count,
        rejected_assertions_count=result.rejected_assertions_count,
        confirmable=result.confirmable,
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
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        prepare_worldbuilding as _prepare,
    )


    return _prepare(request)


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


def confirm_worldbuilding(
    request: WorldbuildingWritePlanConfirmRequest,
) -> WorldbuildingWritePlanConfirmReceipt:
    """Verify one sealed worldbuilding write plan and commit its rebuilt effect."""
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        confirm_worldbuilding as _confirm,
    )


    return _confirm(request)


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
            or ""
        )
        _verified, contribution = resolve_merged_contribution_from_package(
            review_package=review_package,
            confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
            world_id_hint=world_id_hint,
            root=world_root,
            expected_parent_revision_id=None,
            assertion_ids=normalized_assertion_ids,
        )
        accepted_assertion_ids = [
            item.assertion_id for item in contribution.accepted_assertions
        ]
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


    if published and (not result_ok or verification in {"degraded", "failed"}):
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
    if payload.get("accepted_assertion_ids") is not None and payload.get(
        "affected_object_ids"
    ) is not None:
        accepted_assertion_ids = [
            str(item) for item in list(payload.get("accepted_assertion_ids") or [])
        ]
        affected_object_ids = [
            str(item) for item in list(payload.get("affected_object_ids") or [])
        ]
        projection_warnings: list[str] = []
    else:
        projection_root = world_root
        projection_override = str(payload.get("projection_world_root") or "").strip()
        if projection_override:
            projection_root = Path(projection_override)
        accepted_assertion_ids, affected_object_ids, projection_warnings = (
            _project_assertion_fields(
                request.review_package,
                normalized_assertion_ids,
                world_root=projection_root,
            )
        )
    committed_revision_id = str(payload.get("committed_revision_id") or "").strip()
    if not committed_revision_id:
        raise ExtractPromoteError(
            "committed revision missing after confirm",
            code="extract_promote_internal_error",
            status_code=500,
        )
    sealed_world_id = str(
        ((request.review_package or {}).get("effect") or {}).get("world_id") or ""
    ).strip()
    if not sealed_world_id or str(payload.get("world_id") or "").strip() != sealed_world_id:
        raise ExtractPromoteError(
            "Governed publication receipt does not match the sealed native World.",
            code="publication_target_mismatch", status_code=500,
        )
    return ExtractPromoteConfirmReceipt(
        outcome=outcome,
        world_id=sealed_world_id,
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


def confirm(
    request: ExtractPromoteConfirmRequest,
) -> ExtractPromoteConfirmReceipt:
    if str((request.review_package or {}).get("schema") or "").strip() in {
        "dmb_worldbuilding_write_plan_v1",
        "dmb_worldbuilding_write_plan_v2",
    }:
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

    _assert_current_publication_target(request.review_package)
    effect = (request.review_package or {}).get("effect") or {}
    recap_context = effect.get(_RECAP_CONTEXT_KEY) if isinstance(effect, dict) else None
    if isinstance(recap_context, dict):
        managed_world_id = str(recap_context.get("managed_world_id") or "")
        campaign_id = str(recap_context.get("campaign_id") or "")
        _assert_current_recap_ingest_context(
            recap_context,
            managed_world_id=managed_world_id,
            campaign_id=campaign_id,
        )


    normalized_assertion_ids = tuple(request.assertion_ids)
    world_root = world_graph_root()


    sealed_uri = str(
        ((request.review_package or {}).get("effect") or {}).get("verified_source_uri")
        or ""
    ).strip()
    if sealed_uri:
        assert_sealed_source_uri_allowed(sealed_uri)


    from apps.live_control_server import config as _config


    if (
        _config.world_graph_authority_mode()
        == _config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    ):
        from apps.live_control_server.integrations.dungeonmind import (
            world_graph_writes,
        )


        try:
            from apps.live_control_server.services.candidate_graph_admission import (
                confirm_candidate_graph_admission,
            )

            locator = str(
                ((request.review_package or {}).get("effect") or {})
                .get("candidate_admission", {})
                .get("candidate_locator")
                or ""
            ).strip()
            if not locator:
                raise ExtractPromoteError(
                    "sealed candidate admission has no candidate locator",
                    code="candidate_binding_invalid",
                    status_code=409,
                )
            from apps.live_control_server.services.recap_semantic_disposition import (
                is_recap_correction,
            )

            initial_owner = _candidate_owner_for_locator(locator)
            if initial_owner is None or not is_recap_correction(initial_owner):
                assert_sealed_source_uri_allowed(locator)
            try:
                candidate_payload = json.loads(Path(locator).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ExtractPromoteError(
                    "sealed candidate could not be resolved at confirm",
                    code="candidate_binding_invalid",
                    status_code=409,
                    diagnostics=[_diagnostic("candidate_binding_invalid", str(exc))],
                ) from exc
            if not isinstance(candidate_payload, dict):
                raise ExtractPromoteError(
                    "sealed candidate root is not an object",
                    code="candidate_binding_invalid",
                    status_code=409,
                )

            def _governed_confirm():
                _assert_recap_semantics_at_confirm(locator, request.review_package)
                _assert_current_publication_target(request.review_package)
                return world_graph_writes.confirm_extract_promote_via_dungeonmind(
                    request,
                    database_url=_config.world_graph_authority_database_url() or "",
                    confirming_principal=SERVER_CONFIRMING_PRINCIPAL,
                    assertion_ids=normalized_assertion_ids,
                    repo_root=repo_root(),
                )

            payload = confirm_candidate_graph_admission(
                review_package=request.review_package,
                candidate_graph=candidate_payload,
                governed_confirm=_governed_confirm,
            )
        except CandidateGraphMappingError as exc:
            raise ExtractPromoteError(
                str(exc),
                code="candidate_binding_invalid",
                status_code=409,
                diagnostics=[_diagnostic("candidate_binding_invalid", str(exc))],
            ) from None
        except world_graph_writes.WorldGraphWriteError as exc:
            raise ExtractPromoteError(
                str(exc),
                code=exc.code,
                status_code=exc.status_code,
                diagnostics=[_diagnostic(exc.code, str(exc))],
            ) from None
        return _build_confirm_receipt(
            request=request,
            normalized_assertion_ids=normalized_assertion_ids,
            result_ok=True,
            payload=payload,
            world_root=world_root,
        )


    raise ExtractPromoteError(
        "Buddy filesystem extract-promote confirm is retired; DungeonMind authority is required",
        code="authority_unavailable",
        status_code=409,
        diagnostics=[
            _diagnostic(
                "authority_unavailable",
                "Buddy filesystem extract-promote confirm is retired",
            )
        ],
    )


def prepare_first_world(
    request: FirstWorldGraphPrepareRequest,
) -> FirstWorldGraphPlan:
    """Seal an inert first-world initialization plan (no production graph mutation)."""
    from apps.live_control_server.services.first_world_graph_publication import (
        prepare_first_world as _prepare,
    )


    return _prepare(request)


def confirm_first_world(
    request: FirstWorldGraphConfirmRequest,
) -> FirstWorldGraphConfirmReceipt:
    """Verify a sealed first-world plan and atomically initialize W."""
    from apps.live_control_server.services.first_world_graph_publication import (
        confirm_first_world as _confirm,
    )


    return _confirm(request)


__all__ = [
    "ExtractPromoteError",
    "assert_sealed_source_uri_allowed",
    "confirm",
    "confirm_first_world",
    "confirm_worldbuilding",
    "get_exact_run_review_package",
    "get_status",
    "prepare_first_world",
    "prepare_worldbuilding",
    "prepare",
    "resolve_promote_source_uri",
]
