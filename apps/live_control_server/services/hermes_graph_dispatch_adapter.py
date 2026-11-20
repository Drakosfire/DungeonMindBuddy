"""Buddy adapter to the private dispatcher in pinned Hermes 0.18.2.

A singleton preserves the vendor's cancellation/guardrail/callback path while
keeping its aggregate result budget scoped to exactly that one bounded page.
"""

from copy import copy
import inspect


def install_graph_serial_dispatch(agent) -> None:
    original = getattr(agent, "_execute_tool_calls", None)
    if not callable(original) or list(inspect.signature(original).parameters) != [
        "assistant_message",
        "messages",
        "effective_task_id",
        "api_call_count",
    ]:
        raise ValueError("hermes_graph_dispatch_signature_unsupported")

    def serial(assistant_message, messages, effective_task_id, api_call_count=0):
        for call in assistant_message.tool_calls:
            singleton = copy(assistant_message)
            singleton.tool_calls = [call]
            before = len(messages)
            original(singleton, messages, effective_task_id, api_call_count)
            added = messages[before:]
            if len(added) != 1 or added[0].get("tool_call_id") != call.id:
                raise ValueError("hermes_graph_dispatch_pairing_invalid")

    agent._execute_tool_calls = serial


def verify_graph_page_capacity(agent, page_bytes: int) -> None:
    """Verify the constructed SDK capacity; never raise its persistence budgets."""
    from .graph_tool_transport import PAGE_BYTES, MAX_DETAIL_PAGE_BYTES, PAGED_TOOLS
    if isinstance(page_bytes, bool) or not isinstance(page_bytes, int) or not PAGE_BYTES <= page_bytes <= MAX_DETAIL_PAGE_BYTES:
        raise ValueError("hermes_graph_page_capacity_unsupported")
    if page_bytes == PAGE_BYTES:
        return  # Existing mode is proven against the pinned SDK's minimum floor.
    context = getattr(getattr(agent, "context_compressor", None), "context_length", None)
    if isinstance(context, bool) or not isinstance(context, int) or context <= 0:
        raise ValueError("hermes_graph_page_context_unknown")
    try:
        from agent.tool_executor import _budget_for_agent
        budget = _budget_for_agent(agent)
        thresholds = [budget.resolve_threshold(tool) for tool in PAGED_TOOLS]
        if page_bytes > min(budget.turn_budget, *thresholds):
            raise ValueError("hermes_graph_page_capacity_insufficient")
    except (ImportError, AttributeError, TypeError) as exc:
        raise ValueError("hermes_graph_page_capacity_unsupported") from exc
