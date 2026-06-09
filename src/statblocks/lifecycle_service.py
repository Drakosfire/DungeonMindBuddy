from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from src.statblocks.lifecycle_artifact import (
    StatblockBreadcrumb,
    StatblockCreatedBy,
    StatblockDraftArtifact,
    artifact_from_draft_response,
)
from src.statblocks.lifecycle_commands import (
    STATBLOCK_DRAFT_GENERATE,
    STATBLOCK_DRAFT_RENDER,
    STATBLOCK_GENERATOR_HEALTH,
)
from src.statblocks.v2_client import (
    StatBlockGeneratorClientConfigError,
    StatBlockGeneratorHTTPError,
    StatBlockGeneratorProvider,
)
from src.statblocks.v2_contract import (
    ContractError,
    StatBlockDraftRenderRequest,
    StatBlockDraftRequest,
    StatBlockDraftResponse,
    StatBlockGeneratorHealth,
)

CommandStatus = Literal["ok", "error", "unsupported"]


class StatblockLifecycleCommandRequest(BaseModel):
    command_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "agent"
    idempotency_key: str | None = None
    as_artifact: bool = True
    breadcrumbs: list[StatblockBreadcrumb] = Field(default_factory=list)


class StatblockLifecycleCommandResult(BaseModel):
    command_type: str
    status: CommandStatus
    health: StatBlockGeneratorHealth | None = None
    response: StatBlockDraftResponse | None = None
    artifact: StatblockDraftArtifact | None = None
    error: ContractError | None = None
    diagnostics: list[str] = Field(default_factory=list)


class StatblockLifecycleService:
    def __init__(self, provider: StatBlockGeneratorProvider) -> None:
        self._provider = provider

    def execute(
        self, request: StatblockLifecycleCommandRequest
    ) -> StatblockLifecycleCommandResult:
        if request.command_type == STATBLOCK_GENERATOR_HEALTH:
            return self._execute_health(request)
        if request.command_type == STATBLOCK_DRAFT_GENERATE:
            return self._execute_generate(request)
        if request.command_type == STATBLOCK_DRAFT_RENDER:
            return self._execute_render(request)
        return StatblockLifecycleCommandResult(
            command_type=request.command_type,
            status="unsupported",
            error=ContractError(
                code="unsupported_command",
                message=f"Unsupported statblock lifecycle command: {request.command_type}",
                details={"supported_commands": list(_SUPPORTED_COMMANDS)},
            ),
        )

    def _execute_health(
        self, request: StatblockLifecycleCommandRequest
    ) -> StatblockLifecycleCommandResult:
        try:
            health = self._provider.health()
        except (StatBlockGeneratorClientConfigError, StatBlockGeneratorHTTPError) as exc:
            return _result_from_exception(request.command_type, exc)
        except Exception as exc:  # noqa: BLE001 - command facade converts provider failures into structured errors
            return _result_from_exception(request.command_type, exc)
        return StatblockLifecycleCommandResult(
            command_type=request.command_type,
            status="ok",
            health=health,
        )

    def _execute_generate(
        self, request: StatblockLifecycleCommandRequest
    ) -> StatblockLifecycleCommandResult:
        try:
            draft_request = StatBlockDraftRequest.model_validate(request.payload)
        except ValidationError as exc:
            return _validation_error_result(request.command_type, exc)
        try:
            response = self._provider.generate_draft(draft_request)
        except StatBlockGeneratorHTTPError as exc:
            return _result_from_exception(request.command_type, exc)
        except (StatBlockGeneratorClientConfigError, ValidationError) as exc:
            return _result_from_exception(request.command_type, exc)
        except Exception as exc:  # noqa: BLE001 - command facade converts provider failures into structured errors
            return _result_from_exception(request.command_type, exc)
        return _result_from_response(request, response)

    def _execute_render(
        self, request: StatblockLifecycleCommandRequest
    ) -> StatblockLifecycleCommandResult:
        try:
            render_request = StatBlockDraftRenderRequest.model_validate(request.payload)
        except ValidationError as exc:
            return _validation_error_result(request.command_type, exc)
        try:
            response = self._provider.render_draft(render_request)
        except StatBlockGeneratorHTTPError as exc:
            return _result_from_exception(request.command_type, exc)
        except (StatBlockGeneratorClientConfigError, ValidationError) as exc:
            return _result_from_exception(request.command_type, exc)
        except Exception as exc:  # noqa: BLE001 - command facade converts provider failures into structured errors
            return _result_from_exception(request.command_type, exc)
        return _result_from_response(request, response)


def _result_from_response(
    request: StatblockLifecycleCommandRequest, response: StatBlockDraftResponse
) -> StatblockLifecycleCommandResult:
    artifact: StatblockDraftArtifact | None = None
    diagnostics: list[str] = []
    if response.success and request.as_artifact:
        try:
            artifact = artifact_from_draft_response(
                response,
                created_by=_created_by_from_requested_by(request.requested_by),
                breadcrumbs=request.breadcrumbs,
            )
        except ValueError as exc:
            return StatblockLifecycleCommandResult(
                command_type=request.command_type,
                status="error",
                response=response,
                error=ContractError(
                    code="artifact_mapping_failed",
                    message=_safe_message(str(exc)),
                ),
                diagnostics=["v2 response could not be mapped into a draft artifact"],
            )
    elif response.success and not request.as_artifact:
        diagnostics.append("artifact mapping skipped because as_artifact is false")

    return StatblockLifecycleCommandResult(
        command_type=request.command_type,
        status="ok" if response.success else "error",
        response=response,
        artifact=artifact,
        error=response.error if not response.success else None,
        diagnostics=diagnostics,
    )


def _result_from_exception(
    command_type: str, exc: Exception
) -> StatblockLifecycleCommandResult:
    if isinstance(exc, StatBlockGeneratorHTTPError):
        response = exc.response
        return StatblockLifecycleCommandResult(
            command_type=command_type,
            status="error",
            response=response,
            error=(
                response.error
                if response is not None and response.error is not None
                else ContractError(
                    code="http_error",
                    message=_safe_message(str(exc)),
                    details={"status_code": exc.status_code},
                )
            ),
            diagnostics=[f"provider_http_status={exc.status_code}"],
        )
    return StatblockLifecycleCommandResult(
        command_type=command_type,
        status="error",
        error=ContractError(
            code=_error_code_for_exception(exc),
            message=_safe_message(str(exc) or exc.__class__.__name__),
        ),
        diagnostics=[exc.__class__.__name__],
    )


def _validation_error_result(
    command_type: str, exc: ValidationError
) -> StatblockLifecycleCommandResult:
    return StatblockLifecycleCommandResult(
        command_type=command_type,
        status="error",
        error=ContractError(
            code="invalid_payload",
            message=f"Invalid payload for {command_type}",
            details={"error_count": exc.error_count()},
        ),
        diagnostics=["payload validation failed"],
    )


def _created_by_from_requested_by(requested_by: str) -> StatblockCreatedBy:
    if requested_by in {"human", "agent", "planning_task", "combat_task"}:
        return requested_by  # type: ignore[return-value]
    return "agent"


def _error_code_for_exception(exc: Exception) -> str:
    if isinstance(exc, StatBlockGeneratorClientConfigError):
        return "provider_config_error"
    if isinstance(exc, ValidationError):
        return "invalid_provider_response"
    return "provider_error"


def _safe_message(message: str) -> str:
    safe = message
    secret = os.environ.get("DUNGEONBUDDY_INTERNAL_API_KEY")
    if secret:
        safe = safe.replace(secret, "[redacted]")
    return safe


_SUPPORTED_COMMANDS = (
    STATBLOCK_GENERATOR_HEALTH,
    STATBLOCK_DRAFT_GENERATE,
    STATBLOCK_DRAFT_RENDER,
)
