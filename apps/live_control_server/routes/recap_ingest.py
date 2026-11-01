from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from application_state.errors import ApplicationStateError

from apps.live_control_server.config import repo_root
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from graph_memory.ingestion.native_recap_source import (
    Status as NativeRecapSourceStatus,
    Resume as NativeRecapResume,
    SourceSelection,
)

from src.corpus.session_recap_paths import (
    is_generic_recap_tail,
    recap_tail,
)
from src.live_play.recap_ingest_pipeline import (
    PipelineOptions,
    inspect_recap_ingest_status,
    reconcile_normalized_recap,
    run_pipeline,
)
from src.live_play.recap_stage_paths import corpus_root as default_corpus_root
from src.live_play.recap_derivative_provenance import record_archived_artifacts
from apps.live_control_server.services.ingest_run_catalog import IngestRunCatalogError
from apps.live_control_server.services.recap_graph_preview_ingest import (
    extract_recap,
    inspect_recap_graph_preview_status,
)

from apps.live_control_server.models.session_evidence import SessionEvidenceRef

router = APIRouter(prefix="/api/live", tags=["live"])

RecapIngestOperation = Literal[
    "generate_recap_memory",
    "build_graph_preview_bundle",
    "inspect_status",
    "reconcile_normalized_recap",
]

_CORPUS_ROOT_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"


class RecapIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_recap_source: SourceSelection | None = None
    native_recap_run_id: UUID | None = None
    native_recap_resume: NativeRecapResume | None = None
    session_evidence: list[SessionEvidenceRef] = Field(default_factory=list,max_length=3)
    _resolved_session_evidence: dict | None = PrivateAttr(default=None)
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
    force_graph_run: bool = False
    extract_graph: bool = False
    graph_model_id: str | None = None
    include_graph_extraction: bool = True

    @model_validator(mode='after')
    def native_selector_scope(self):
        if self.native_recap_run_id is not None and (self.operation!='inspect_status' or not self.managed_world_id or self.native_recap_resume is not None or self.raw_text is not None or self.session_evidence):
            raise ValueError('Exact native source status requires inspect_status and its selected World')
        if self.native_recap_source is not None and (
            not _source_only(self)
            or self.native_recap_run_id is not None
            or self.native_recap_resume is not None
        ):
            raise ValueError('Exact source selection requires fresh source-only admission')
        if self.native_recap_resume is not None and not _source_only(self):
            raise ValueError('Explicit native resume requires the exact source-only operation')
        return self


class RecapIngestStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    native_recap_source: NativeRecapSourceStatus | None = None
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


def _add_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


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


def _remove_retired_derivative_details(status: dict[str, Any]) -> dict[str, Any]:
    """Keep legacy derivative readiness out of the graph-first Ingest contract."""
    def is_retired(value: Any) -> bool:
        normalized = str(value).lower()
        return any(part in normalized for part in ("breadcrumb", "frontmatter_seed", "session_memory"))

    cleaned = dict(status)
    states = list(cleaned.get("states", []))
    has_recap = any(
        state in {
            "recap_applied",
            "recap_reused",
            "normalized_created",
            "normalized_refreshed",
            "normalized_reused",
            "normalized_current",
        }
        for state in states
    )
    if cleaned.get("status") == "breadcrumb_required":
        if "staged_raw_notes_conflict" in states:
            cleaned["status"] = "needs_reconciliation"
        else:
            cleaned["status"] = "recap_applied" if has_recap else "initialized"
    cleaned["states"] = [state for state in states if not is_retired(state)]
    for field in ("paths", "authority"):
        values = cleaned.get(field)
        if isinstance(values, dict):
            cleaned[field] = {key: value for key, value in values.items() if not is_retired(key)}
    for field in ("warnings", "errors", "next_actions"):
        values = cleaned.get(field)
        if isinstance(values, list):
            cleaned[field] = [value for value in values if not is_retired(value)]
    report = cleaned.get("ingest_report")
    if isinstance(report, dict):
        report = {
            key: value
            for key, value in report.items()
            if key != "derivative_stages" and not is_retired(key)
        }
        graph_value = report.get("graph_preview")
        if isinstance(graph_value, dict):
            graph = dict(graph_value)
        else:
            graph = None
        if graph is not None and isinstance(graph.get("next_actions"), list):
            graph["next_actions"] = [
                "Process recap" if action == "apply_normalize" else action
                for action in graph["next_actions"]
            ]
            report["graph_preview"] = graph
        impact = report.get("corpus_impact")
        if isinstance(impact, list):
            report["corpus_impact"] = [
                row for row in impact
                if not isinstance(row, dict) or not is_retired(row.get("key", ""))
            ]
        cleaned["ingest_report"] = report
    return cleaned


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
        managed_world_id=body.managed_world_id,
        campaign_id=body.campaign_id,
        session=body.session,
        normalized_recap_path=normalized,
    )
    return _remove_retired_derivative_details(_append_graph_status(status, graph))


def _generate_recap_memory_from_request(body: RecapIngestRequest, corpus: Path | None) -> dict[str, Any]:
    if (body.raw_text or "").strip() and not _is_non_generic_slug_or_title(slug=body.slug, title=body.title):
        raise HTTPException(
            status_code=422,
            detail="generate_recap_memory requires non-generic slug or title",
        )

    # Resolve the World before Process writes any pasted source. The graph-first
    # action must fail closed if its selected World is unavailable.
    ingest_context = _request_recap_context(body) if body.include_graph_extraction else None
    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )

    if (body.raw_text or "").strip():
        status = run_pipeline(
            _stage_recap_options(body),
            stdin=io.StringIO(body.raw_text or ""),
            corpus=corpus,
        )
        if status.get("status") == "error" or (
            "staged_raw_notes_conflict" in status.get("states", []) and not body.force_stage
        ):
            # Never continue against an older staged source after Process receives
            # different pasted text. The caller must explicitly replace it.
            return _remove_retired_derivative_details(status)

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
    ):
        status = _carry_archived_artifacts(
            status,
            run_pipeline(_apply_recap_options(body), corpus=corpus),
        )
        if status.get("status") == "error":
            return _remove_retired_derivative_details(status)
        if status.get("status") == "needs_reconciliation" and not _normalized_recap_is_graph_ready(status):
            return _remove_retired_derivative_details(status)

    if body.include_graph_extraction:
        normalized = _normalized_recap_graph_path(status, corpus)
        if normalized and _normalized_recap_is_graph_ready(status):
            graph = extract_recap(
                repo_root=repo_root(),
                campaign_id=body.campaign_id,
                session=body.session,
                normalized_recap_path=normalized,
                graph_model_id=body.graph_model_id,
                force_graph_run=body.force_graph_run,
                ingest_context=ingest_context,
                **({"supplemental_evidence":body._resolved_session_evidence} if body._resolved_session_evidence is not None else {}),
            )
            status = _append_graph_status(status, graph)
            if graph.get("extraction_mode") == "llm_blocked" or graph.get("blocked_reason"):
                _add_unique(
                    status.setdefault("warnings", []),
                    f"preview graph extraction blocked: {graph.get('blocked_reason') or 'unknown reason'}",
                )
        elif not _normalized_recap_is_graph_ready(status):
            _block_graph_without_current_normalized(status)
        else:
            _add_unique(
                status.setdefault("warnings", []),
                "preview graph extraction skipped: normalized recap path could not be resolved",
            )

    return _remove_retired_derivative_details(status)

def _stage_recap_options(body: RecapIngestRequest) -> PipelineOptions:
    """Stage pasted text inside the atomic Process request; not a public API operation."""
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


def _apply_recap_options(body: RecapIngestRequest) -> PipelineOptions:
    """Persist and normalize staged text inside the atomic Process request."""
    if not _is_non_generic_slug_or_title(slug=body.slug, title=body.title):
        raise HTTPException(
            status_code=422,
            detail="generate_recap_memory requires non-generic slug or title",
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
        # An explicit canonical replacement must refresh its normalized
        # derivative in the same Process request, preserving the old copy.
        force_normalize=body.force_recap,
        force_session_memory=False,
    )


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
        resolve_recap_source_scope,
    )

    try:
        return resolve_recap_source_scope(
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


def _source_only(body):
    return (
        body.operation == "build_graph_preview_bundle"
        and not body.include_graph_extraction
        and not body.extract_graph
        and not body.force_graph_run
        and not body.session_evidence
        and body.raw_text is None
        and body.graph_model_id is None
        and not body.force_stage
        and not body.force_recap
        and body.slug is None
        and body.title is None
        and body.keep_basename is None
    )


def _native_source_envelope(body, native):
    state = "native_source_admitted" if native.state == "admitted" else "native_source_pending"
    return {
        "schema": "dmb_raw_recap_ingest_status_v1",
        "campaign_id": body.campaign_id,
        "session": body.session,
        "status": state,
        "states": ["immutable_app_source_prepared", state],
        "paths": {},
        "authority": {"source": "immutable_app_recap_v1"},
        "warnings": [],
        "errors": [native.failure_code] if native.failure_code else [],
        "next_actions": [],
        "ingest_report": {},
        "entity_spelling_audit": [],
        "native_recap_source": native.model_dump(mode="json"),
    }


async def resolve_native_recap_hosted_world(request: Request) -> str:
    """Authorize only this capability's strict forms through the hosted boundary."""
    from apps.live_control_server import config
    from apps.live_control_server.services.world_container_registry import (
        get_world_container,
    )
    from graph_memory.ingestion.native_recap_source import StatusBody

    payload = await request.json()
    if isinstance(payload, dict) and payload.get("native_recap_run_id") is not None:
        body = StatusBody.model_validate(payload)
    else:
        body = RecapIngestRequest.model_validate(payload)
        if not _source_only(body) or not body.managed_world_id:
            raise ValueError("Hosted recap operation is outside source admission")
    world = get_world_container(
        config.managed_world_data_root(repo_root()), body.managed_world_id
    )
    return world.world_id


def _native_source_actor(body, request):
    from apps.live_control_server import config
    from apps.live_control_server.services import hosted_auth
    from apps.live_control_server.services.agent_graph_auth import (
        enforce_native_graph_gm,
    )
    from apps.live_control_server.services.world_container_registry import (
        get_world_container,
        require_world_permission,
        WorldPermission,
        WorldAccessDenied,
        WorldContainerRegistryError,
    )

    if request is None:
        raise HTTPException(status_code=403, detail={"code": "graph_gm_required"})
    environment, mode = hosted_auth.deployment_environment(), hosted_auth.auth_mode()
    if environment in hosted_auth.LOCAL_ENVIRONMENTS and mode == hosted_auth.LOCAL_MODE:
        principal = enforce_native_graph_gm(request)
        if not principal.subject.strip():
            raise HTTPException(status_code=403, detail={"code": "graph_gm_required"})
        return principal.subject, "local_gm"
    if (
        environment != hosted_auth.PRODUCTION_ENVIRONMENT
        or mode != hosted_auth.HOSTED_MODE
    ):
        raise HTTPException(status_code=503, detail={"code": "hosted_auth_unavailable"})
    principal = getattr(request.state, "dms_principal", None)
    if principal is None or not principal.subject.strip():
        raise HTTPException(status_code=401, detail={"code": "authentication_required"})
    hosted_auth.require_hosted_write_origin(request)
    try:
        world = get_world_container(
            config.managed_world_data_root(repo_root()), body.managed_world_id
        )
        require_world_permission(
            world, subject=principal.subject, permission=WorldPermission.MANAGE
        )
    except (WorldAccessDenied, WorldContainerRegistryError) as exc:
        raise HTTPException(
            status_code=403, detail={"code": "native_recap_world_manage_required"}
        ) from exc
    return principal.subject, "world_manage"


def _native_source_request(body, request):
    from apps.live_control_server.services import (
        native_recap_source_admission as native,
    )

    actor, authority_basis = _native_source_actor(body, request)
    try:
        if body.native_recap_run_id is not None:
            return _native_source_envelope(
                body,
                native.inspect(
                    repo_root(),
                    body.native_recap_run_id,
                    body.managed_world_id,
                    body.campaign_id,
                    body.session,
                ),
            )
        if body.native_recap_resume is not None:
            return _native_source_envelope(
                body,
                native.resume_admission(
                    repo_root(),
                    resume=body.native_recap_resume,
                    world=body.managed_world_id,
                    campaign=body.campaign_id,
                    session=body.session,
                    actor=actor,
                    authority_basis=authority_basis,
                ),
            )
        if body.native_recap_source is None:
            raise HTTPException(
                status_code=422, detail={"code": "native_recap_source_selection_required"}
            )
        if not body.managed_world_id:
            raise HTTPException(
                status_code=422, detail={"code": "managed_world_context_required"}
            )
        from apps.live_control_server import config
        from apps.live_control_server.services.managed_world_graph_projection import (
            resolve_managed_source_identity,
        )
        from graph_memory.ingestion.native_recap_source import SourceScope

        binding = resolve_managed_source_identity(
            body.managed_world_id, root=config.managed_world_data_root(repo_root())
        )
        context = SourceScope(
            managed_world_id=binding.managed_world_id,
            native_world_id=binding.native_world_id,
            binding_version=binding.binding_version,
            campaign_id=body.campaign_id,
        )
        return _native_source_envelope(
            body,
            native.admit(
                repo_root(),
                context=context,
                selection=body.native_recap_source,
                session=body.session,
                actor=actor,
                authority_basis=authority_basis,
            ),
        )
    except HTTPException:
        raise
    except native.NativeRecapError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail={"code": exc.code}
        ) from exc
    except Exception as exc:
        # Never reflect stored commands, source bytes or validation input to a public error.
        import logging

        logging.getLogger(__name__).exception("Native recap source request failed")
        raise HTTPException(
            status_code=409, detail={"code": "native_recap_source_unavailable"}
        ) from exc


@router.post("/recap-ingest", response_model=RecapIngestStatusResponse)
def post_recap_ingest(
    body: RecapIngestRequest, request: Request = None
) -> dict[str, Any]:
    if body.native_recap_run_id is not None or _source_only(body):
        return _native_source_request(body, request)
    # This wire operation remains native source-only intake. File-backed preview
    # construction is retired; it must not fall through to corpus or model work.
    if body.operation == "build_graph_preview_bundle":
        raise HTTPException(status_code=422, detail="Artifact preview construction is retired. Use Process for extraction.")
    if body.session_evidence:
        from apps.live_control_server.services.agent_graph_auth import (
            enforce_native_graph_gm,
        )
        from apps.live_control_server.services.session_evidence import (
            resolve_evidence_refs,
        )

        if request is None:
            raise HTTPException(
                status_code=403,
                detail="Session supplements require authenticated GM access",
            )
        enforce_native_graph_gm(request)
        if not body.managed_world_id:
            raise HTTPException(
                status_code=422, detail="Session evidence requires the selected World"
            )
        try:
            body._resolved_session_evidence = resolve_evidence_refs(
                body.managed_world_id,
                [ref.model_dump() for ref in body.session_evidence],
            )
        except ApplicationStateError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    try:
        corpus = _pipeline_corpus_root()
        if body.operation == "generate_recap_memory":
            return _generate_recap_memory_from_request(body, corpus)
        if body.operation == "inspect_status":
            return _inspect_status_with_graph(body, corpus)
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
            return _remove_retired_derivative_details(
                reconcile_normalized_recap(
                    campaign_id=body.campaign_id,
                    session=body.session,
                    keep_basename=keep,
                    corpus=(corpus or default_corpus_root()).resolve(),
                )
            )
        raise HTTPException(status_code=422, detail=f"unsupported operation: {body.operation}")
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except IngestRunCatalogError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
