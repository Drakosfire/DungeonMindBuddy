"""Project observable acquisition from a saved Buddy turn-context trace.

This is a lower bound, not a complete acquisition journal: catalog discovery
and other activity are not uniformly captured in the trace. Source labels are
provided by the evaluator, never by the product model.
"""

RELATED_POLICY = "selected_exact_related_authored_pages_v1"
UNKNOWN = "<unmapped-acquisition>"
NATIVE_READ_POLICIES = frozenset(
    f"native_{operation}_progress_v{version}"
    for operation in ("assertion_read", "statement_read", "source_document_read",
                      "source_section_read", "source_search")
    for version in (1, 2)
)


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
        elif (kind == "context_decision" and event.get("policy_version") in NATIVE_READ_POLICIES
              and event.get("action") in {"expanded", "retrieved", "retained"}):
            items = event.get("item_ids")
            if not isinstance(items, list) or not items or any(not isinstance(x, str) or not x for x in items):
                raise ValueError("Native read activity has no valid target")
            observed.append({"sequence": sequence, "kind": "native_read_attempt", "label": UNKNOWN})
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


def native_activity_counts(trace):
    """Count fixed native activity stages separately; not distinct source counts."""
    observed_acquisitions(trace)  # Validate the trace shape and sequence first.
    counts = {}
    for event in trace["observations"]:
        policy, action = event.get("policy_version"), event.get("action")
        if event.get("kind") != "context_decision" or policy not in NATIVE_READ_POLICIES:
            continue
        if action not in {"expanded", "retrieved", "retained"}:
            continue
        bucket = counts.setdefault(policy, {"expanded": 0, "retrieved": 0, "retained": 0})
        bucket[action] += 1
    return {"counts_by_policy": counts, "coverage": "partial",
            "limit": "stage observations, not paired operations or distinct sources"}


def controller_observations(trace):
    """Project unvalidated opening votes and provider identity, not host authority.

    The raw provider snapshot is explicitly unvalidated. Related-page vote
    counts describe proposed selection, never prove accepted votes or reads.
    Only fixed host-defined labels are projected; arbitrary model text stays in
    the original capture and is not introduced into another model request.
    """
    import json

    # Reuse structural checks; this does not assert the trace is exhaustive.
    observed_acquisitions(trace)
    allowed = {
        "source_need": {"anchored", "source_lookup", "uncertain"},
        "paragraph_work": {"discuss", "explicit_page_body", "explicit_page_end", "place_paragraph", "unsupported_or_unclear"},
        "paragraph_relation": {"after", "before", "unresolved"},
        "paragraph_scope": {"named", "unresolved", "unscoped"},
        "requested_work": {"build_encounter", "change_mechanics", "clarify_creation", "clarify_request", "discuss",
                           "draft_in_conversation", "other_creation", "place_map_coordinates", "plan", "prepare_image",
                           "publish_relationships", "review_connected_page", "review_lore_page", "review_lore_page_from_conversation",
                           "review_relationship", "review_variant_approval", "save_page", "write_current_page"},
    }
    providers, snapshots = set(), []
    for event in trace["observations"]:
        if event.get("kind") == "provider_call":
            provider, model = event.get("provider"), event.get("model")
            if isinstance(provider, str) and isinstance(model, str):
                providers.add((provider, model))
        if (event.get("kind") != "context_snapshot" or event.get("snapshot_kind") != "provider_response"
                or event.get("stage") != "after"):
            continue
        for item in event.get("materials", []):
            if not isinstance(item, dict) or not str(item.get("item_id", "")).startswith("unvalidated-controller-decision:"):
                continue
            try:
                response = json.loads(item["text"])
                answers = response["answers"]
                if not isinstance(answers, dict):
                    raise ValueError("invalid answer map")
            except (KeyError, TypeError, ValueError):
                snapshots.append({"sequence": event["sequence"], "validation": "unvalidated", "parse_status": "invalid"})
                continue
            selections = {}
            for name, choices in allowed.items():
                if name in answers:
                    answer = answers[name]
                    value = answer.get("selected") if isinstance(answer, dict) else None
                    selections[name] = value if isinstance(value, str) and value in choices else "other_or_invalid"
            votes = {"read": 0, "skip": 0, "other_or_invalid": 0}
            for key, answer in answers.items():
                if not isinstance(key, str) or not key.startswith("related_page_") or not key[len("related_page_"):].isdigit():
                    continue
                value = answer.get("selected") if isinstance(answer, dict) else None
                votes[value if value in ("read", "skip") else "other_or_invalid"] += 1
            snapshots.append({"sequence": event["sequence"], "validation": "unvalidated", "parse_status": "parsed",
                              "selections": selections, "related_page_votes": votes})
    return {"providers": [{"provider": provider, "model": model} for provider, model in sorted(providers)],
            "controller_snapshots": snapshots}
