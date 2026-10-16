from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from apps.live_control_server.config import repo_root
from pydantic import BaseModel, ConfigDict, Field

from src.agent.recap_frontmatter_seed import (
    build_frontmatter_seed,
    default_frontmatter_seed_path,
)
from src.corpus.session_recap_paths import (
    breadcrumbed_relpath,
    campaign_number_from_id,
    frontmatter_seed_relpath,
    is_generic_recap_tail,
    normalized_recap_relpath,
    recap_tail,
)
from src.live_play.recap_ingest_pipeline import (
    PipelineOptions,
    inspect_recap_ingest_status,
    reconcile_normalized_recap,
    run_pipeline,
)
from src.live_play.recap_stage_paths import corpus_root as default_corpus_root
from src.live_play.recap_derivative_provenance import (
    provenance_path,
    record_archived_artifacts,
    sha256_bytes,
    sha256_file,
    store_provenanced_artifact,
)
from src.session_memory.breadcrumb_normalize import (
    BreadcrumbNormalizeError,
    extract_meta_from_frontmatter,
    normalize_breadcrumb_artifact,
)
from src.session_memory.breadcrumb_smoke import parse_frontmatter_and_body
from apps.live_control_server.services.recap_graph_preview_ingest import (
    build_recap_graph_preview_bundle,
    ensure_graph_ingest_projection_payload,
    inspect_recap_graph_preview_status,
    materialize_recap_preview_supergraph,
)

router = APIRouter(prefix="/api/live", tags=["live"])

RecapIngestOperation = Literal[
    "stage_preview",
    "generate_recap_memory",
    "apply_normalize",
    "build_frontmatter_seed",
    "run_breadcrumb_ingest",
    "materialize_session_memory",
    "build_graph_preview_bundle",
    "materialize_preview_supergraph",
    "inspect_graph_preview",
    "inspect_status",
    "reconcile_normalized_recap",
]

_CORPUS_ROOT_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"


class RecapIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: RecapIngestOperation
    campaign_id: str = Field(min_length=1)
    # Optional for general corpus maintenance. Required only when creating a
    # canonical graph ExtractionRun for an existing managed World.
    managed_world_id: str | None = None
    session: Annotated[int, Field(ge=1)]
    raw_text: str | None = None
    slug: str | None = None
    title: str | None = None
    keep_basename: str | None = None
    force_stage: bool = False
    force_recap: bool = False
    force_normalize: bool = False
    force_seed: bool = False
    force_breadcrumb: bool = False
    force_session_memory: bool = False
    check: bool = False
    candidate_graph_path: str | None = None
    force_graph_run: bool = False
    extract_graph: bool = False
    graph_model_id: str | None = None
    materialize_after_extract: bool = False
    include_graph_extraction: bool = True
    include_legacy_breadcrumb: bool = False


class RecapIngestStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_: Literal["dmb_raw_recap_ingest_status_v1"] = Field(alias="schema")
    campaign_id: str
    session: int
    status: str
    states: list[str]
    paths: dict[str, str | None]
    authority: dict[str, str]
    warnings: list[str]
    errors: list[str]
    next_actions: list[str]
    ingest_report: dict[str, Any]
    entity_spelling_audit: list[dict[str, Any]]


def _is_non_generic_slug_or_title(*, slug: str | None, title: str | None) -> bool:
    if slug and slug.strip().rstrip(":").lower():
        return not is_generic_recap_tail(slug)
    return not is_generic_recap_tail(title)


def _pipeline_corpus_root() -> Path | None:
    raw = os.environ.get(_CORPUS_ROOT_ENV, "").strip()
    if not raw:
        return None
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(status_code=500, detail=f"invalid {_CORPUS_ROOT_ENV}: {root}")
    return root


def _run_routing_only_breadcrumb(
    *,
    recap_md: Path,
    frontmatter_seed_md: Path,
    corpus_root: Path,
    out_path: Path,
) -> dict[str, Any]:
    from evals.sentence_routing_retrieval_falsification.breadcrumb_prompt import (
        PROMPT_VARIANT_CONTINUATION,
    )
    from evals.sentence_routing_retrieval_falsification.breadcrumb_query_run import (
        _generate_breadcrumb_artifact_routing_only,
        _resolve_breadcrumb_ingest_model,
    )

    return _generate_breadcrumb_artifact_routing_only(
        recap_md=recap_md,
        frontmatter_seed_md=frontmatter_seed_md,
        corpus_root=corpus_root,
        variant=PROMPT_VARIANT_CONTINUATION,
        model=_resolve_breadcrumb_ingest_model(None),
        out_path=out_path,
        min_routed_records=1,
    )


def _validate_breadcrumb_candidate(
    *,
    content: bytes,
    normalized_path: Path,
    corpus_root: Path,
    campaign_id: str,
    session: int,
) -> None:
    """Reject a generated breadcrumb before it can replace a trusted artifact."""
    try:
        artifact_text = content.decode("utf-8")
        frontmatter, _body = parse_frontmatter_and_body(artifact_text)
        if frontmatter is None:
            raise BreadcrumbNormalizeError("missing YAML frontmatter")
        metadata = extract_meta_from_frontmatter(frontmatter)
        expected_source_path = normalized_path.resolve().relative_to(
            corpus_root.resolve()
        ).as_posix()
        if metadata["source_recap_path"] != expected_source_path:
            raise BreadcrumbNormalizeError(
                "source_recap_path does not match the current normalized recap"
            )
        if metadata["campaign_id"] != campaign_id:
            raise BreadcrumbNormalizeError("campaign_id does not match the requested campaign")
        if metadata["session_number"] != session:
            raise BreadcrumbNormalizeError("session number does not match the requested session")
        normalize_breadcrumb_artifact(
            artifact_text=artifact_text,
            corpus_root=corpus_root,
        )
    except (BreadcrumbNormalizeError, OSError, UnicodeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"invalid breadcrumb candidate: {exc}",
        ) from exc


def _add_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _merge_stage_reuse_warning(status: dict[str, Any], staged_status: dict[str, Any] | None) -> dict[str, Any]:
    if not staged_status or "staged_raw_notes_conflict" not in staged_status.get("states", []):
        return status
    for field in ("states", "warnings"):
        values = status.setdefault(field, [])
        for value in staged_status.get(field, []) or []:
            if isinstance(value, str) and (
                value.startswith("staged_raw_notes") or field == "warnings"
            ):
                _add_unique(values, value)
    status.setdefault("ingest_report", {})["staged_raw_notes_reused_existing"] = True
    return status


def _carry_archived_artifacts(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if not previous:
        return current
    previous_report = previous.get("ingest_report", {})
    current_report = current.setdefault("ingest_report", {})
    if isinstance(previous_report, dict) and isinstance(current_report, dict):
        artifacts = previous_report.get("archived_artifacts", [])
        if isinstance(artifacts, list):
            record_archived_artifacts(current_report, artifacts)
    return current


def _build_frontmatter_seed_from_request(body: RecapIngestRequest, corpus: Path) -> dict[str, Any]:
    campaign_number = campaign_number_from_id(body.campaign_id)
    out_path = default_frontmatter_seed_path(
        corpus_root=corpus,
        campaign_number=campaign_number,
        session=body.session,
    ).resolve()
    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    if "normalized_current" not in status.get("states", []):
        if "normalized_reused" in status.get("states", []):
            _add_unique(status["states"], "derivative_reconciliation_required")
            status["status"] = "needs_reconciliation"
            _add_unique(status["next_actions"], "Refresh the normalized recap before building or refreshing the frontmatter seed.")
        return status

    seed = build_frontmatter_seed(
        corpus_root=corpus,
        campaign_number=campaign_number,
        session=body.session,
    )
    seed_bytes = (seed if seed.endswith("\n") else seed + "\n").encode("utf-8")
    normalized_path = corpus / normalized_recap_relpath(
        campaign_number=campaign_number,
        session=body.session,
        corpus_root=corpus,
    )
    outcome, archived = store_provenanced_artifact(
        output_path=out_path,
        corpus_root=corpus,
        stage="frontmatter_seed",
        campaign_number=campaign_number,
        session=body.session,
        input_digests={
            "normalized_recap": sha256_file(normalized_path),
            "generated_seed": sha256_bytes(seed_bytes),
        },
        content=seed_bytes,
        force=body.force_seed,
        allow_edited_current_inputs=True,
    )
    status["ingest_report"]["frontmatter_seed_path"] = str(out_path)
    status["ingest_report"]["frontmatter_seed_provenance_path"] = str(provenance_path(out_path))
    if archived:
        record_archived_artifacts(status["ingest_report"], archived)
    if outcome == "reused":
        _add_unique(status["states"], "frontmatter_seed_reused")
    elif outcome == "edited_current_inputs":
        _add_unique(status["states"], "frontmatter_seed_edited_current_inputs")
    elif outcome in {"created", "refreshed"}:
        _add_unique(status["states"], "frontmatter_seed_refreshed" if outcome == "refreshed" else "frontmatter_seed_built")
    else:
        _add_unique(status["states"], f"frontmatter_seed_{'provenance_unknown' if outcome == 'unknown' else outcome}")
        _add_unique(status["states"], "derivative_reconciliation_required")
        status["status"] = "needs_reconciliation"
        _add_unique(status["warnings"], f"frontmatter seed was preserved because its lineage is {outcome}")
        _add_unique(status["next_actions"], "Review the normalized recap and explicitly refresh the seed to replace the preserved file.")
        return status
    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    _add_unique(status["states"], "frontmatter_seed_edited_current_inputs" if outcome == "edited_current_inputs" else "frontmatter_seed_reused" if outcome == "reused" else "frontmatter_seed_refreshed" if outcome == "refreshed" else "frontmatter_seed_built")
    status["ingest_report"]["frontmatter_seed_path"] = str(out_path)
    status["ingest_report"]["frontmatter_seed_provenance_path"] = str(provenance_path(out_path))
    if archived:
        record_archived_artifacts(status["ingest_report"], archived)
    return status


def _run_breadcrumb_ingest_from_request(body: RecapIngestRequest, corpus: Path) -> dict[str, Any]:
    campaign_number = campaign_number_from_id(body.campaign_id)
    normalized_path = (
        corpus
        / normalized_recap_relpath(
            campaign_number=campaign_number,
            session=body.session,
            corpus_root=corpus,
        )
    ).resolve()
    seed_path = (
        corpus
        / frontmatter_seed_relpath(
            campaign_number=campaign_number,
            session=body.session,
            corpus_root=corpus,
        )
    ).resolve()
    breadcrumb_path = (
        corpus
        / breadcrumbed_relpath(
            campaign_number=campaign_number,
            session=body.session,
            corpus_root=corpus,
        )
    ).resolve()

    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    if not seed_path.is_file():
        raise HTTPException(status_code=422, detail=f"frontmatter seed missing: {seed_path}")
    if "normalized_current" not in status.get("states", []):
        _add_unique(status["states"], "derivative_reconciliation_required")
        status["status"] = "needs_reconciliation"
        _add_unique(status["next_actions"], "Refresh the normalized recap before routing a breadcrumb.")
        return status
    seed_blockers = {
        "frontmatter_seed_stale",
        "frontmatter_seed_provenance_unknown",
        "frontmatter_seed_corrupt",
    }
    if seed_blockers.intersection(status.get("states", [])):
        status["status"] = "needs_reconciliation"
        return status

    if breadcrumb_path.is_file() and not body.force_breadcrumb:
        _add_unique(status["states"], "breadcrumb_ingest_reused")
        status["ingest_report"]["breadcrumbed_recap_path"] = str(breadcrumb_path)
        if "breadcrumb_current" not in status.get("states", []):
            status["status"] = "needs_reconciliation"
        return status

    candidate_path = breadcrumb_path.with_name(
        f".{breadcrumb_path.name}.candidate-{uuid4().hex}"
    )
    candidate_bytes: bytes | None = None
    try:
        report = _run_routing_only_breadcrumb(
            recap_md=normalized_path,
            frontmatter_seed_md=seed_path,
            corpus_root=corpus,
            out_path=candidate_path,
        )
    except SystemExit as exc:
        detail = str(exc) or "breadcrumb ingest failed"
        raise HTTPException(status_code=422, detail=detail) from exc
    finally:
        if candidate_path.exists():
            candidate_bytes = candidate_path.read_bytes()
        candidate_path.unlink(missing_ok=True)

    if candidate_bytes is None:
        raise HTTPException(status_code=422, detail="breadcrumb generator returned without an artifact")
    _validate_breadcrumb_candidate(
        content=candidate_bytes,
        normalized_path=normalized_path,
        corpus_root=corpus,
        campaign_id=body.campaign_id,
        session=body.session,
    )
    outcome, archived = store_provenanced_artifact(
        output_path=breadcrumb_path,
        corpus_root=corpus,
        stage="breadcrumbed_recap",
        campaign_number=campaign_number,
        session=body.session,
        input_digests={
            "normalized_recap": sha256_file(normalized_path),
            "frontmatter_seed": sha256_file(seed_path),
        },
        content=candidate_bytes,
        force=body.force_breadcrumb,
    )
    if outcome not in {"created", "refreshed"}:
        _add_unique(status["states"], f"breadcrumb_{'provenance_unknown' if outcome == 'unknown' else outcome}")
        _add_unique(status["states"], "derivative_reconciliation_required")
        status["status"] = "needs_reconciliation"
        _add_unique(status["warnings"], f"breadcrumb output was preserved because its lineage is {outcome}")
        return status

    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    _add_unique(status["states"], "breadcrumb_ingest_refreshed" if outcome == "refreshed" else "breadcrumb_ingest_ran")
    status["ingest_report"]["breadcrumb_ingest"] = report
    report["artifact_path"] = str(breadcrumb_path)
    status["ingest_report"]["breadcrumbed_recap_path"] = str(breadcrumb_path)
    status["ingest_report"]["breadcrumbed_recap_provenance_path"] = str(provenance_path(breadcrumb_path))
    if archived:
        record_archived_artifacts(status["ingest_report"], archived)
    return status



def _normalized_recap_is_graph_ready(status: dict[str, Any]) -> bool:
    """Graph work requires a verified current normalized recap, but not legacy derivatives."""
    states = set(status.get("states", []))
    if "normalized_current" not in states:
        return False
    if {"normalized_stale", "normalized_provenance_unknown", "canonical_recap_conflict"}.intersection(states):
        return False
    if "normalized_recap_duplicates" in states:
        candidates = status.get("ingest_report", {}).get("normalized_recap_candidates", [])
        if not isinstance(candidates, list) or sum(bool(row.get("recommended")) for row in candidates if isinstance(row, dict)) != 1:
            return False
    return True


def _block_graph_without_current_normalized(status: dict[str, Any]) -> dict[str, Any]:
    status["status"] = "needs_reconciliation"
    _add_unique(status.setdefault("warnings", []), "Graph work was skipped because the normalized recap is not verified current.")
    _add_unique(
        status.setdefault("next_actions", []),
        "Review and explicitly refresh the normalized recap before building or materializing Graph evidence.",
    )
    return status


def _normalized_recap_graph_path(status: dict[str, Any], corpus: Path | None) -> str | None:
    raw = status.get("paths", {}).get("normalized_recap")
    if not raw:
        return None
    path = Path(str(raw))
    if path.is_absolute():
        return str(path) if path.is_file() else None
    roots: list[Path] = []
    if corpus is not None:
        roots.append(corpus)
    roots.append(default_corpus_root())
    for root in roots:
        candidate = (root / path).resolve()
        if candidate.is_file():
            return str(candidate)
    return None


def _append_graph_status(status: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    status.setdefault("ingest_report", {})["graph_preview"] = graph
    states = status.setdefault("states", [])
    graph_state_by_status = {
        "missing": "graph_preview_missing",
        "source_span_bundle_ready": "graph_source_bundle_ready",
        "candidate_validation_ready": "graph_candidate_ready",
        "preview_union_store_ready": "preview_union_store_ready",
        "failed": "graph_preview_failed",
    }
    state = graph_state_by_status.get(str(graph.get("status")))
    if state and state not in states:
        states.append(state)
    next_actions = status.setdefault("next_actions", [])
    for action in graph.get("next_actions", []) or []:
        if action not in next_actions:
            next_actions.append(action)
    return status


def _inspect_status_with_graph(body: RecapIngestRequest, corpus: Path | None) -> dict[str, Any]:
    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    normalized = (
        _normalized_recap_graph_path(status, corpus)
        if _normalized_recap_is_graph_ready(status)
        else None
    )
    graph = inspect_recap_graph_preview_status(
        repo_root=repo_root(),
        campaign_id=body.campaign_id,
        session=body.session,
        normalized_recap_path=normalized,
    )
    return _append_graph_status(status, graph)


def _generate_recap_memory_from_request(body: RecapIngestRequest, corpus: Path | None) -> dict[str, Any]:
    active_corpus = (corpus or default_corpus_root()).resolve()
    staged_reuse_status: dict[str, Any] | None = None

    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )

    if (body.raw_text or "").strip():
        stage_body = body.model_copy(update={"operation": "stage_preview"})
        status = run_pipeline(
            _options_for_request(stage_body),
            stdin=io.StringIO(body.raw_text or ""),
            corpus=corpus,
        )
        if status.get("status") == "error" or ("staged_raw_notes_conflict" in status.get("states", []) and not body.force_stage):
            if status.get("status") == "error":
                return status
            staged_reuse_status = status

    applied = {
        "recap_applied",
        "recap_reused",
        "normalized_created",
        "normalized_refreshed",
        "normalized_reused",
    }
    if (
        not applied.intersection(status.get("states", []))
        or body.force_recap
        or body.force_normalize
    ):
        apply_body = body.model_copy(update={"operation": "apply_normalize"})
        status = _carry_archived_artifacts(
            status,
            run_pipeline(_options_for_request(apply_body), corpus=corpus),
        )
        if status.get("status") == "error":
            return status
        if status.get("status") == "needs_reconciliation" and not _normalized_recap_is_graph_ready(status):
            return status

    if body.include_graph_extraction:
        normalized = _normalized_recap_graph_path(status, corpus)
        if normalized and _normalized_recap_is_graph_ready(status):
            ingest_context = _request_recap_context(body)
            graph = materialize_recap_preview_supergraph(
                repo_root=repo_root(),
                campaign_id=body.campaign_id,
                session=body.session,
                normalized_recap_path=normalized,
                extract_graph=True,
                graph_model_id=body.graph_model_id,
                force_graph_run=body.force_graph_run,
                ingest_context=ingest_context,
            )
            status = _append_graph_status(status, graph)
            if graph.get("extraction_mode") == "llm_blocked" or graph.get("blocked_reason"):
                _add_unique(
                    status.setdefault("warnings", []),
                    f"preview graph extraction blocked: {graph.get('blocked_reason') or 'unknown reason'}",
                )
            if graph.get("status") == "preview_union_store_ready":
                ensure_graph_ingest_projection_payload(
                    repo_root=repo_root(),
                    manifest_path=graph.get("manifest_path"),
                    session_id=f"session-{body.session}",
                )
            if (
                status.get("status") not in {"error", "needs_reconciliation"}
                and graph.get("status") == "preview_union_store_ready"
            ):
                status["status"] = "ready_for_planning_activation"
        elif not _normalized_recap_is_graph_ready(status):
            _block_graph_without_current_normalized(status)
        else:
            _add_unique(
                status.setdefault("warnings", []),
                "preview graph extraction skipped: normalized recap path could not be resolved",
            )

    if body.include_legacy_breadcrumb:
        if "frontmatter_seed_found" not in status.get("states", []) or body.force_seed:
            status = _carry_archived_artifacts(
                status,
                _build_frontmatter_seed_from_request(body, active_corpus),
            )
            if status.get("status") == "error":
                return status
            if status.get("status") == "needs_reconciliation":
                seed_ready = "normalized_current" in status.get("states", []) and bool(
                    {"frontmatter_seed_current", "frontmatter_seed_edited_current_inputs"}
                    .intersection(status.get("states", []))
                )
                if not (body.force_breadcrumb and seed_ready):
                    return status

        if "breadcrumb_found" not in status.get("states", []) or body.force_breadcrumb:
            status = _carry_archived_artifacts(
                status,
                _run_breadcrumb_ingest_from_request(body, active_corpus),
            )
            if status.get("status") == "error":
                return status
            if status.get("status") == "needs_reconciliation" and not (
                body.force_session_memory and "breadcrumb_current" in status.get("states", [])
            ):
                return status

        if "session_memory_materialized" not in status.get("states", []):
            materialize_body = body.model_copy(update={"operation": "materialize_session_memory"})
            status = _carry_archived_artifacts(
                status,
                run_pipeline(_options_for_request(materialize_body), corpus=corpus),
            )
            if status.get("status") in {"error", "needs_reconciliation"}:
                return status
        if (
            status.get("status") != "ready_for_planning_activation"
            and status.get("status") != "needs_reconciliation"
            and "session_memory_current" in status.get("states", [])
        ):
            status["status"] = "ready_for_planning_activation"
    else:
        _add_unique(
            status.setdefault("warnings", []),
            "legacy_breadcrumb_skipped: graph-first ingest did not run frontmatter, breadcrumb, or session memory",
        )

    return _merge_stage_reuse_warning(status, staged_reuse_status)

def _options_for_request(body: RecapIngestRequest) -> PipelineOptions:
    operation = body.operation
    if operation == "stage_preview":
        raw = (body.raw_text or "").strip()
        if not raw:
            raise HTTPException(status_code=422, detail="stage_preview requires non-empty raw_text")
        return PipelineOptions(
            campaign_id=body.campaign_id,
            session=body.session,
            raw_path=None,
            raw_stdin=True,
            title=body.title,
            slug=body.slug,
            stage=True,
            preview=True,
            apply=False,
            normalize=False,
            materialize_session_memory=False,
            check=False,
            force_stage=body.force_stage,
            force_recap=False,
            json_output=True,
            force_normalize=False,
            force_session_memory=False,
        )

    if operation == "apply_normalize":
        if not _is_non_generic_slug_or_title(slug=body.slug, title=body.title):
            raise HTTPException(
                status_code=422,
                detail="apply_normalize requires non-generic slug or title",
            )
        return PipelineOptions(
            campaign_id=body.campaign_id,
            session=body.session,
            raw_path=None,
            raw_stdin=False,
            title=body.title,
            slug=body.slug,
            stage=False,
            preview=True,
            apply=True,
            normalize=True,
            materialize_session_memory=False,
            check=False,
            force_stage=False,
            force_recap=body.force_recap,
            json_output=True,
            force_normalize=body.force_normalize,
            force_session_memory=False,
        )

    if operation == "materialize_session_memory":
        if not _is_non_generic_slug_or_title(slug=body.slug, title=body.title):
            raise HTTPException(
                status_code=422,
                detail="materialize_session_memory requires non-generic slug or title",
            )
        return PipelineOptions(
            campaign_id=body.campaign_id,
            session=body.session,
            raw_path=None,
            raw_stdin=False,
            title=body.title,
            slug=body.slug,
            stage=False,
            preview=False,
            apply=False,
            normalize=False,
            materialize_session_memory=True,
            check=body.check,
            force_stage=False,
            force_recap=False,
            json_output=True,
            force_normalize=False,
            force_session_memory=body.force_session_memory,
        )

    raise HTTPException(status_code=422, detail=f"unsupported operation: {operation}")


def _request_recap_context(body: RecapIngestRequest):
    if not body.managed_world_id:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "managed_world_context_required",
                "message": "Select a managed World before creating a campaign recap graph run.",
            },
        )
    from apps.live_control_server.services.recap_ingest_context import (
        read_recap_ingest_context,
    )

    try:
        return read_recap_ingest_context(
            managed_world_id=body.managed_world_id,
            campaign_id=body.campaign_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 503),
            detail={
                "code": getattr(exc, "code", "ingest_context_unavailable"),
                "message": str(exc),
            },
        ) from exc


@router.post("/recap-ingest", response_model=RecapIngestStatusResponse)
def post_recap_ingest(body: RecapIngestRequest) -> dict[str, Any]:
    try:
        corpus = _pipeline_corpus_root()
        if body.operation == "generate_recap_memory":
            return _generate_recap_memory_from_request(body, corpus)
        if body.operation == "inspect_status":
            return _inspect_status_with_graph(body, corpus)
        if body.operation == "inspect_graph_preview":
            return _inspect_status_with_graph(body, corpus)
        if body.operation in {"build_graph_preview_bundle", "materialize_preview_supergraph"}:
            status = inspect_recap_ingest_status(
                campaign_id=body.campaign_id,
                session=body.session,
                title=body.title,
                slug=body.slug,
                corpus=corpus,
            )
            normalized = _normalized_recap_graph_path(status, corpus)
            if not _normalized_recap_is_graph_ready(status):
                return _block_graph_without_current_normalized(status)
            if not normalized:
                raise HTTPException(status_code=422, detail="normalized recap missing")
            ingest_context = _request_recap_context(body)
            if body.extract_graph and body.candidate_graph_path:
                raise HTTPException(
                    status_code=422,
                    detail="candidate_graph_path cannot be combined with extract_graph=true",
                )
            if body.operation == "build_graph_preview_bundle":
                graph = build_recap_graph_preview_bundle(
                    repo_root=repo_root(),
                    campaign_id=body.campaign_id,
                    session=body.session,
                    normalized_recap_path=normalized,
                    force_graph_run=body.force_graph_run,
                    candidate_graph_path=body.candidate_graph_path,
                    extract_graph=body.extract_graph,
                    graph_model_id=body.graph_model_id,
                    ingest_context=ingest_context,
                )
            else:
                graph = materialize_recap_preview_supergraph(
                    repo_root=repo_root(),
                    campaign_id=body.campaign_id,
                    session=body.session,
                    normalized_recap_path=normalized,
                    candidate_graph_path=body.candidate_graph_path,
                    extract_graph=body.extract_graph or body.materialize_after_extract,
                    graph_model_id=body.graph_model_id,
                    force_graph_run=body.force_graph_run,
                    ingest_context=ingest_context,
                )
            return _append_graph_status(status, graph)
        if body.operation == "build_frontmatter_seed":
            return _build_frontmatter_seed_from_request(
                body,
                corpus=(corpus or default_corpus_root()).resolve(),
            )
        if body.operation == "run_breadcrumb_ingest":
            return _run_breadcrumb_ingest_from_request(
                body,
                corpus=(corpus or default_corpus_root()).resolve(),
            )
        if body.operation == "reconcile_normalized_recap":
            keep = (body.keep_basename or "").strip()
            if not keep:
                raise HTTPException(
                    status_code=422,
                    detail="reconcile_normalized_recap requires keep_basename",
                )
            if is_generic_recap_tail(keep):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"keep_basename {recap_tail(keep)!r} is a generic/tool-shaped recap; "
                        "choose a canonical session title to keep"
                    ),
                )
            return reconcile_normalized_recap(
                campaign_id=body.campaign_id,
                session=body.session,
                keep_basename=keep,
                corpus=(corpus or default_corpus_root()).resolve(),
            )
        options = _options_for_request(body)
        if body.operation == "stage_preview":
            status = run_pipeline(
                options,
                stdin=io.StringIO(body.raw_text or ""),
                corpus=corpus,
            )
        else:
            status = run_pipeline(options, corpus=corpus)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return status
