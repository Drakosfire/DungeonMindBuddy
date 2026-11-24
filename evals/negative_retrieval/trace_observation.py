"""Project observable acquisition from a saved Buddy turn-context trace.

This is a lower bound, not a complete acquisition journal: catalog discovery
and other activity are not uniformly captured in the trace. Source labels are
provided by the evaluator, never by the product model.
"""

RELATED_POLICY = "selected_exact_related_authored_pages_v1"
UNKNOWN = "<unmapped-acquisition>"


def observed_acquisitions(trace, *, related_labels=None, source_labels=None):
    if not isinstance(trace, dict) or trace.get("schema") != "dmb_turn_context_trace_v1":
        raise ValueError("Expected a turn-context trace")
    events = trace.get("observations")
    if not isinstance(events, list) or any(not isinstance(e, dict) for e in events):
        raise ValueError("Trace observations are missing")
    if [e.get("sequence") for e in events] != list(range(len(events))):
        raise ValueError("Trace sequence is incomplete or unordered")
    related_labels = related_labels or {}
    source_labels = source_labels or {}
    observed = []
    for event in events:
        kind = event.get("kind")
        sequence = event["sequence"]
        if kind == "graph_tool":
            observed.append({"sequence": sequence, "kind": "graph_operation", "label": UNKNOWN})
        elif kind == "source_passage":
            label = source_labels.get(event.get("source_artifact_id"), UNKNOWN)
            observed.append({"sequence": sequence, "kind": "source_read", "label": label})
        elif (kind == "context_decision" and event.get("action") == "retrieved"
              and event.get("policy_version") == RELATED_POLICY):
            items = event.get("item_ids")
            if not isinstance(items, list) or not items or any(not isinstance(x, str) for x in items):
                raise ValueError("Related-page retrieval has no valid item IDs")
            observed.extend({"sequence": sequence, "kind": "related_page_read",
                             "label": related_labels.get(item, UNKNOWN)} for item in items)
        elif kind == "authored_graph_reference_v1":
            execution = event.get("execution_event")
            if not isinstance(execution, dict):
                raise ValueError("Authored reference event is malformed")
            if execution.get("kind") == "build_authored_reference_read_v1":
                observed.append({"sequence": sequence, "kind": "authored_reference_read", "label": UNKNOWN})
    return {
        "observed": observed,
        "trace_capture_status": trace.get("capture_status"),
        "terminal_status": trace.get("terminal_status"),
        # Even complete trace capture does not observe every discovery owner.
        "journal_complete": None,
    }
