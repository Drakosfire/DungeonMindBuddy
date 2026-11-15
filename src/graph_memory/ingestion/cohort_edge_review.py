"""Validate reviewed Event relationship coverage before preparation."""


def validate(candidate, manifest):
    nodes = {node["node_id"]: node for node in candidate["nodes"]}
    events = manifest["event_ids"]
    if len(events) != len(set(events)) or any(
        nodes.get(node_id, {}).get("node_type") != "event" for node_id in events
    ):
        raise ValueError("event_ids must identify distinct candidate Events")
    event_ids = set(events)
    edges = candidate["edges"]
    required = {
        edge["edge_id"]
        for edge in edges
        if edge["from_node_id"] in event_ids or edge["to_node_id"] in event_ids
    }
    decisions = {}
    for row in manifest["edge_decisions"]:
        edge_id = row["edge_id"]
        if edge_id in decisions:
            raise ValueError(f"Duplicate edge decision: {edge_id}")
        decisions[edge_id] = row
    if required != decisions.keys():
        raise ValueError(
            f"Missing decisions: {sorted(required - decisions.keys())}. "
            f"Foreign decisions: {sorted(decisions.keys() - required)}."
        )
    for edge_id, row in decisions.items():
        state = row["decision"]
        if state == "publish":
            fields = ("evidence_ref_ids",)
            for role in ("subject", "target"):
                endpoint_fields = [
                    field for field in (f"{role}_entity_id", f"{role}_candidate_node_id")
                    if field in row
                ]
                if len(endpoint_fields) != 1:
                    raise ValueError(f"{edge_id} requires one {role} binding")
                fields += tuple(endpoint_fields)
        elif state == "already_present":
            fields = ("assertion_id", "subject_entity_id", "target_entity_id", "evidence_ref_ids")
        elif state in {"held", "rejected"}:
            fields = ("reason",)
        else:
            raise ValueError(f"Invalid decision for {edge_id}: {state}")
        for field in fields:
            value = row.get(field)
            values = value if field == "evidence_ref_ids" else [value]
            if not isinstance(values, list) or not values or any(
                not isinstance(item, str) or not item.strip() for item in values
            ):
                raise ValueError(f"{edge_id} requires {field}")
    return len(required)


def validate_prepare(candidate, manifest, request):
    count = validate(candidate, manifest)
    for field in ("managed_world_id", "campaign_id", "run_id", "expected_run_revision",
                  "candidate_sha256", "expected_parent_revision_id",
                  "expected_source_authority_epoch", "source_admission_run_id"):
        if request[field] != manifest["prepare_pin"][field]:
            raise ValueError(f"Prepare request differs from review pin: {field}")

    selections = {}
    for selection in request["selections"]:
        key = selection["kind"], selection["record_id"]
        if key in selections:
            raise ValueError(f"Duplicate prepare selection: {key}")
        selections[key] = selection
    event_ids = set(manifest["event_ids"])
    selected_events = {
        node["node_id"] for node in candidate["nodes"]
        if node["node_type"] == "event"
        and selections.get(("node", node["node_id"]), {}).get("action") in {"create", "use_existing"}
    }
    if not selected_events <= event_ids:
        raise ValueError("Prepare selects Events outside the reviewed cohort")
    placements = {
        record_id for (kind, record_id), selection in selections.items()
        if kind == "placement" and selection["action"] == "create"
    }
    reviewed_placements = set(manifest.get("placement_ids", []))
    if not reviewed_placements <= event_ids or placements != reviewed_placements:
        raise ValueError("Prepare placements differ from reviewed placements")
    published_edges = {
        row["edge_id"] for row in manifest["edge_decisions"] if row["decision"] == "publish"
    }
    requested_edges = {
        record_id for (kind, record_id), selection in selections.items()
        if kind == "edge" and selection["action"] == "create"
    }
    if requested_edges != published_edges:
        raise ValueError("Prepare relationship writes differ from reviewed decisions")

    edges = {edge["edge_id"]: edge for edge in candidate["edges"]}
    for decision in manifest["edge_decisions"]:
        edge_id = decision["edge_id"]
        selection = selections.get(("edge", edge_id), {})
        publishing = decision["decision"] == "publish"
        if publishing != (selection.get("action") == "create"):
            raise ValueError(f"{edge_id} prepare action differs from review")
        if not publishing and decision["decision"] != "already_present":
            continue
        if publishing and sorted(selection["metadata"]["evidence_ref_ids"]) != sorted(decision["evidence_ref_ids"]):
            raise ValueError(f"{edge_id} prepare evidence differs from review")
        for endpoint, role in (("from_node_id", "subject"), ("to_node_id", "target")):
            node_id = edges[edge_id][endpoint]
            bound = selections.get(("node", node_id), {})
            candidate_field = f"{role}_candidate_node_id"
            if publishing and candidate_field in decision:
                matches = bound.get("action") == "create" and decision[candidate_field] == node_id
            else:
                matches = (
                    bound.get("action") == "use_existing"
                    and bound.get("entity_id") == decision[f"{role}_entity_id"]
                )
            if not matches:
                raise ValueError(f"{edge_id} prepare endpoint differs from review: {endpoint}")
    return count


def build_prepare_request(candidate, manifest, request):
    """Build the governed prepare payload from reviewed objects and edge decisions."""
    if "cohort_edge_review" in request or any(
        selection["kind"] == "edge" for selection in request["selections"]
    ):
        raise ValueError("Base request must omit cohort review and edge selections")
    validate(candidate, manifest)
    edges = [
        {
            "kind": "edge",
            "record_id": row["edge_id"],
            "action": "create",
            "metadata": row["metadata"] | {"evidence_ref_ids": row["evidence_ref_ids"]},
        }
        for row in manifest["edge_decisions"]
        if row["decision"] == "publish"
    ]
    prepared = request | {
        "selections": [*request["selections"], *edges],
        "cohort_edge_review": manifest,
    }
    validate_prepare(candidate, manifest, prepared)
    return prepared
