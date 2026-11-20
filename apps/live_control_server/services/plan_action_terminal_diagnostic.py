"""Bounded Action failure retention and historical owner-scoped read."""
from __future__ import annotations

from collections.abc import Mapping
from application_state.plan_action_dialogue.service import PlanActionDialogueService
from application_state.plan_action_dialogue.types import ActionTerminalDiagnosticV1
from apps.live_control_server.services.hermes_graph_agent_contract import validate_terminal_failure_record

_CATEGORIES = {"provider_lifecycle_unavailable", "request_budget_veto", "hermes_turn_error", "prompt_capture_unavailable"}


def retain_terminal_diagnostic(adapter, result):
    """Best effort metadata only; original failure/uncertainty always wins."""
    action = adapter.stop()
    if action.consultation is None or action.dispatch_token is None:
        return action
    metadata = result.runtime_metadata
    raw = metadata.get("terminal_failure") if isinstance(metadata, Mapping) else None
    failure = validate_terminal_failure_record(raw)
    warnings = result.telemetry_warnings or ()
    unavailable = ("invalid_reported_by_host" if "terminal_failure_diagnostic_invalid" in warnings
                   else "invalid_observed_at_parent" if raw is not None
                   else "missing_or_not_retained")
    category = (getattr(adapter.failure, "code", None) if adapter.failure is not None else result.error_code)
    data = dict(
        world_id=action.basis.world_id, action_id=action.action_id, dispatch_fence=action.fence,
        attribution="action_only", availability="captured" if failure else "unavailable",
        failure=failure, unavailable_reason=None if failure else unavailable,
        runtime_status=result.status if result.status in {"ok", "error"} else "unavailable",
        error_origin="parent_adapter" if adapter.failure is not None else "runtime_result",
        error_category=category if category in _CATEGORIES else "unavailable" if category is None else "other",
    )
    witness = adapter.terminal_callback
    if (failure is not None and witness is not None
            and witness["generation"] == adapter.authorization_generation
            and witness["transition"] == failure["transition"]
            and (witness["transition"] == "outcome_unknown" or witness["parent_acknowledged"] is False)):
        data.update(attribution="provider_attempt", **{key: witness[key] for key in (
            "authorization_event_id", "provider_attempt_id", "callback_sequence", "parent_acknowledged",
        )})
    try:
        diagnostic = ActionTerminalDiagnosticV1.model_validate(data)
        try:
            updated, _ = adapter.store.append_terminal_diagnostic(
                action_id=action.action_id, token=action.dispatch_token, fence=action.fence,
                diagnostic=diagnostic,
            )
        except ValueError:
            # Contradictory provider attribution is not repaired or silently accepted.
            if diagnostic.attribution != "provider_attempt":
                raise
            diagnostic = ActionTerminalDiagnosticV1(
                **{**data, "attribution": "action_only", "availability": "unavailable",
                   "failure": None, "unavailable_reason": "contradictory_binding",
                   "authorization_event_id": None, "provider_attempt_id": None,
                   "callback_sequence": None, "parent_acknowledged": None},
            )
            updated, _ = adapter.store.append_terminal_diagnostic(
                action_id=action.action_id, token=action.dispatch_token, fence=action.fence,
                diagnostic=diagnostic,
            )
        adapter.turn = updated
        if adapter.fence is not None:
            adapter.fence.action = updated
        return updated
    except Exception:
        # Do not log raw diagnostic values or replace the original failure.
        return action


def terminal_diagnostic(world_id, action_id):
    action = PlanActionDialogueService().read_prompt_action(world_id=world_id, action_id=action_id)
    diagnostic = getattr(action.consultation, "terminal_diagnostic", None)
    return {"schema": "dmb_plan_action_terminal_diagnostic_read_v1", "world_id": world_id,
            "action_id": str(action_id), "status": action.status,
            "diagnostic": None if diagnostic is None else diagnostic.model_dump(
                mode="json", exclude={"dispatch_fence"}),
            "availability": "unavailable" if diagnostic is None else diagnostic.availability}
