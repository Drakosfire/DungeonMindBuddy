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
