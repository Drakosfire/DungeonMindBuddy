"""Stable status/prepare/confirm routes for extract → World Supergraph promote."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from apps.live_control_server import config as live_config
from apps.live_control_server.models.ingest_selection_context import IngestSelectionContextRequest
from apps.live_control_server.models.worldbuilding_publication_coverage import WorldbuildingPublicationCoverage
from apps.live_control_server.models.extract_promote import (
    ExtractPromoteConfirmReceipt,
    ExtractPromoteConfirmRequest,
    ExtractPromoteDiagnostic,
    ExtractPromotePrepareRequest,
    ExtractPromotePrepareResponse,
    ExactRunReviewPackage,
    RecapSemanticDecisionRequest,
    RecapSemanticDecisionResponse,
    ExactRunEvidenceCorrectionRequest,
    WorldbuildingEvidenceCorrectionRequest,
    WorldbuildingFrozenSpanCatalog,
    ExactRunEvidenceCorrectionResponse,
    RecapEvidenceCorrectionResponse,
    RecapCandidateCorrectionRequest,
    RecapCandidateCorrectionRequestV2,
    RecapCandidateCorrectionRequestV3,
    RecapCandidateCorrectionRequestV4,
    RecapCandidateCorrectionRequestV5,
    RecapCandidateCorrectionRequestV6,
    RecapCandidateCorrectionRequestV7,
    RecapCandidateCorrectionRequestV8,
    RecapCandidateCorrectionRequestV9,
    RecapCandidateCorrectionRequestV10,
    RecapCandidateCorrectionResponse,
    RecapCandidateCorrectionResponseV2,
    RecapCandidateCorrectionResponseV3,
    RecapCandidateCorrectionResponseV4,
    RecapCandidateCorrectionResponseV5,
    RecapCandidateCorrectionResponseV6,
    RecapCandidateCorrectionResponseV7,
    RecapCandidateCorrectionResponseV8,
    RecapCandidateCorrectionResponseV9,
    RecapCandidateCorrectionResponseV10,
    RecapCandidateCorrectionRequestV11,
    RecapCandidateCorrectionResponseV11,
    FirstWorldGraphConfirmReceipt,
    FirstWorldGraphConfirmRequest,
    FirstWorldGraphPlan,
    FirstWorldGraphPrepareRequest,
    WorldbuildingPublicationCapabilities,
    WorldbuildingWritePlanConfirmReceipt,
    WorldbuildingWritePlanConfirmRequest,
    WorldbuildingWritePlanPrepareRequest,
    WorldbuildingWritePlanResponse,
)
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    confirm,
    confirm_first_world,
    confirm_worldbuilding,
    decide_recap_semantic_disposition,
    get_exact_run_review_package,
    prepare,
    prepare_first_world,
    prepare_worldbuilding,
)
from apps.live_control_server.services.exact_run_evidence_correction import (
    correct_exact_run_evidence,
    get_worldbuilding_frozen_spans,
    correct_recap_run_evidence,
)
from apps.live_control_server.services.recap_semantic_candidate_correction import correct_recap_candidate
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    native_graph_gm_dependency,
)

logger = logging.getLogger(__name__)


def _error_response(exc: ExtractPromoteError) -> JSONResponse:
    body = exc.response().model_dump(mode="json", by_alias=True, exclude_none=True)
    # Interim dogfood inspect until review-package returns inspectable 200s for
    # binding failures (Backlog: false_anchor / run_not_promotable).
    logger.warning(
        "extract-promote error code=%s status=%s message=%s diagnostics=%s",
        exc.code,
        exc.status_code,
        str(exc),
        [
            {"code": item.code, "message": item.message, "severity": item.severity}
            for item in exc.diagnostics
        ],
    )
    return JSONResponse(status_code=exc.status_code, content=body)


def _request_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "extra_forbidden" for error in errors):
        code = "invalid_request"
        message = "Extract-promote request contains unsupported fields."
    elif any(
        "confirming_principal" in {str(item) for item in error.get("loc", ())}
        or "prepared_by" in {str(item) for item in error.get("loc", ())}
        for error in errors
    ):
        code = "invalid_principal"
        message = "Prepared-by / confirming principal must be a bounded non-blank string."
    else:
        code = "invalid_request"
        message = "Extract-promote request does not match the required contract."
    return _error_response(
        ExtractPromoteError(
            message,
            code=code,
            status_code=422,
            diagnostics=[ExtractPromoteDiagnostic(code=code, message=message)],
        )
    )


class _ExtractPromoteAPIRoute(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def wrapped_route_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError as exc:
                return _request_validation_error_response(exc)

        return wrapped_route_handler


router = APIRouter(
    prefix="/api/live/extract-promote",
    tags=["extract-promote"],
    route_class=_ExtractPromoteAPIRoute,
)


@router.get("/runs/{run_id}/worldbuilding-publication-coverage", response_model=WorldbuildingPublicationCoverage)
def get_worldbuilding_publication_coverage_route(
    request: Request,
    run_id: str,
    _principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> dict[str, Any] | JSONResponse:
    """Authenticated historical proof; no publication replay or caller selectors."""
    from apps.live_control_server.services.worldbuilding_publication_coverage import (
        get_worldbuilding_publication_coverage,
    )
    try:
        _reject_selector_query(request)
        return get_worldbuilding_publication_coverage(run_id).model_dump(mode="json", by_alias=True)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(ExtractPromoteError(
            "Publication coverage is unknown because native evidence could not be read.",
            code="publication_coverage_unavailable", status_code=503,
        ))


def _reject_selector_query(request: Request) -> None:
    if request.query_params:
        raise ExtractPromoteError(
            "Extract-promote routes do not accept query parameters.",
            code="invalid_request",
            status_code=422,
            diagnostics=[
                ExtractPromoteDiagnostic(
                    code="invalid_request",
                    message="Extract-promote routes do not accept query parameters.",
                )
            ],
        )


@router.get("/runs/{run_id}/review-package", response_model=ExactRunReviewPackage)
def get_extract_promote_exact_run_review(
    request: Request,
    run_id: str,
) -> dict[str, Any] | JSONResponse:
    """Server-owned exact-run source/evidence projection (no sealed proposal)."""
    try:
        _reject_selector_query(request)
        response = get_exact_run_review_package(run_id)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        return _error_response(
            ExtractPromoteError(
                "The exact-run review package operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.get("/runs/{run_id}/frozen-source-spans", response_model=WorldbuildingFrozenSpanCatalog)
def get_exact_run_frozen_source_spans(request_context: Request, run_id: str):
    try:
        _reject_selector_query(request_context)
        return get_worldbuilding_frozen_spans(run_id).model_dump(mode="json", by_alias=True)
    except ExtractPromoteError as exc:
        return _error_response(exc)


@router.post("/runs/{run_id}/evidence-corrections", response_model=ExactRunEvidenceCorrectionResponse)
def post_exact_run_evidence_corrections(
    request_context: Request,
    run_id: str,
    request: WorldbuildingEvidenceCorrectionRequest,
) -> dict[str, Any] | JSONResponse:
    """Partition exact frozen evidence into an unpublished child."""
    try:
        _reject_selector_query(request_context)
        if run_id != request.parent_run_id:
            raise ExtractPromoteError(
                "path run ID does not match parentRunId",
                code="invalid_request",
                status_code=422,
            )
        response = correct_exact_run_evidence(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        logger.exception("exact-run evidence correction failed unexpectedly")
        return _error_response(
            ExtractPromoteError(
                "The exact-run evidence correction failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/runs/{run_id}/recap-evidence-corrections",
    response_model=RecapEvidenceCorrectionResponse,
)
def post_recap_evidence_corrections(
    request_context: Request,
    run_id: str,
    request: ExactRunEvidenceCorrectionRequest,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> dict[str, Any] | JSONResponse:
    """GM-only literal evidence child; semantic disposition starts held."""
    try:
        _reject_selector_query(request_context)
        if run_id != request.parent_run_id:
            raise ExtractPromoteError(
                "path run ID does not match parentRunId",
                code="invalid_request", status_code=422,
            )
        response = correct_recap_run_evidence(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        logger.exception("recap evidence correction failed unexpectedly")
        return _error_response(
            ExtractPromoteError(
                "The recap evidence correction failed unexpectedly.",
                code="extract_promote_internal_error", status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/runs/{run_id}/recap-candidate-corrections",
    response_model=(
        RecapCandidateCorrectionResponse
        | RecapCandidateCorrectionResponseV2
        | RecapCandidateCorrectionResponseV3
        | RecapCandidateCorrectionResponseV4
        | RecapCandidateCorrectionResponseV5
        | RecapCandidateCorrectionResponseV6
        | RecapCandidateCorrectionResponseV7
        | RecapCandidateCorrectionResponseV8
        | RecapCandidateCorrectionResponseV9
        | RecapCandidateCorrectionResponseV10
        | RecapCandidateCorrectionResponseV11
    ),
)
def post_recap_candidate_corrections(
    request_context: Request,
    run_id: str,
    request: RecapCandidateCorrectionRequest | RecapCandidateCorrectionRequestV2 | RecapCandidateCorrectionRequestV3 | RecapCandidateCorrectionRequestV4 | RecapCandidateCorrectionRequestV5 | RecapCandidateCorrectionRequestV6 | RecapCandidateCorrectionRequestV7 | RecapCandidateCorrectionRequestV8 | RecapCandidateCorrectionRequestV9 | RecapCandidateCorrectionRequestV10 | RecapCandidateCorrectionRequestV11,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> dict[str, Any] | JSONResponse:
    """GM-only bounded semantic candidate child; no World publication."""
    try:
        _reject_selector_query(request_context)
        if run_id != request.parent_run_id:
            raise ExtractPromoteError(
                "path run ID does not match parentRunId",
                code="invalid_request", status_code=422,
            )
        response = correct_recap_candidate(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        logger.exception("recap candidate correction failed unexpectedly")
        return _error_response(ExtractPromoteError(
            "The recap candidate correction failed unexpectedly.",
            code="extract_promote_internal_error", status_code=500,
        ))
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/runs/{run_id}/semantic-disposition",
    response_model=RecapSemanticDecisionResponse,
)
def post_recap_semantic_disposition(
    request_context: Request,
    run_id: str,
    request: RecapSemanticDecisionRequest,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> dict[str, Any] | JSONResponse:
    """GM-only exact-child decision; caller cannot supply reviewer or time."""
    try:
        _reject_selector_query(request_context)
        response = decide_recap_semantic_disposition(
            run_id, request, reviewer_id=principal.subject
        )
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        logger.exception("recap semantic decision failed unexpectedly")
        return _error_response(
            ExtractPromoteError(
                "The recap semantic decision failed unexpectedly.",
                code="extract_promote_internal_error", status_code=500,
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/runs/{run_id}/selection-context", response_model=None)
def post_ingest_selection_context(
    request_context: Request,
    run_id: str,
    request: IngestSelectionContextRequest,
    principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> dict[str, Any] | JSONResponse:
    """Read-only, exact-run selection packet; never invokes a model or Graph write."""
    from apps.live_control_server.services.ingest_selection_context import resolve_ingest_selection_context
    from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
    try:
        _reject_selector_query(request_context)
        return resolve_ingest_selection_context(run_id, request, operator_subject=principal.subject)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except GraphRunRegistryError as exc:
        return _error_response(ExtractPromoteError(str(exc), code="ingest_selection_unavailable", status_code=exc.status_code))
    except Exception:
        logger.exception("ingest selection context failed unexpectedly")
        return _error_response(ExtractPromoteError(
            "Selected ingestion context could not be resolved.",
            code="ingest_selection_unavailable", status_code=503,
        ))


@router.post("/prepare", response_model=ExtractPromotePrepareResponse)
def post_extract_promote_prepare(
    request_context: Request,
    request: ExtractPromotePrepareRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = prepare(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        # Log the full traceback server-side; never echo exception text to clients.
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "extract-promote prepare failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The extract-promote prepare operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.get(
    "/worldbuilding/capabilities",
    response_model=WorldbuildingPublicationCapabilities,
)
def get_worldbuilding_publication_capabilities(
    request_context: Request,
    _principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> WorldbuildingPublicationCapabilities | JSONResponse:
    """Inspect configuration only; confirm remains the plan authority boundary.

    No database connection or source/World lookup is attempted. A configured
    descriptor does not prove reachability, plan validity, or publication success.
    Historical sealed plans (including their inert metadata) remain untouched.
    """
    try:
        _reject_selector_query(request_context)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    reasons = []
    try:
        live_config.world_graph_authority_mode()
    except live_config.WorldGraphAuthorityConfigurationError:
        reasons.append("native_authority_configuration_invalid")
    if live_config.world_graph_authority_database_url() is None:
        reasons.append("native_database_unconfigured")
    return WorldbuildingPublicationCapabilities(
        configured=not reasons, unavailability_reasons=reasons,
    )


@router.post(
    "/worldbuilding/prepare",
    response_model=WorldbuildingWritePlanResponse,
)
def post_worldbuilding_write_plan_prepare(
    request_context: Request,
    request: WorldbuildingWritePlanPrepareRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = prepare_worldbuilding(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "worldbuilding write-plan prepare failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The worldbuilding write-plan prepare operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/worldbuilding/confirm",
    response_model=WorldbuildingWritePlanConfirmReceipt,
)
def post_worldbuilding_write_plan_confirm(
    request_context: Request,
    request: WorldbuildingWritePlanConfirmRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = confirm_worldbuilding(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "worldbuilding write-plan confirm failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The worldbuilding write-plan confirm operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/worldbuilding/first-world/prepare",
    response_model=FirstWorldGraphPlan,
)
def post_first_world_prepare(
    request_context: Request,
    request: FirstWorldGraphPrepareRequest,
    _principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = prepare_first_world(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "first-world prepare failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The first-world prepare operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post(
    "/worldbuilding/first-world/confirm",
    response_model=FirstWorldGraphConfirmReceipt,
)
def post_first_world_confirm(
    request_context: Request,
    request: FirstWorldGraphConfirmRequest,
    _principal: NativeGraphPrincipal = Depends(native_graph_gm_dependency),
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = confirm_first_world(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "first-world confirm failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The first-world confirm operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)


@router.post("/confirm", response_model=ExtractPromoteConfirmReceipt)
def post_extract_promote_confirm(
    request_context: Request,
    request: ExtractPromoteConfirmRequest,
) -> dict[str, Any] | JSONResponse:
    try:
        _reject_selector_query(request_context)
        response = confirm(request)
    except ExtractPromoteError as exc:
        return _error_response(exc)
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception(
            "extract-promote confirm failed unexpectedly correlation_id=%s",
            correlation_id,
        )
        return _error_response(
            ExtractPromoteError(
                "The extract-promote confirm operation failed unexpectedly.",
                code="extract_promote_internal_error",
                status_code=500,
                diagnostics=[
                    ExtractPromoteDiagnostic(
                        code="internal_error",
                        message=f"Internal error. Reference: {correlation_id}",
                        severity="error",
                    )
                ],
            )
        )
    return response.model_dump(mode="json", by_alias=True)
