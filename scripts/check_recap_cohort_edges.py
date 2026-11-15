#!/usr/bin/env python3
"""Check that review explicitly accounts for edges incident to selected Events."""

import argparse
import json
from pathlib import Path


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
            fields = ("subject_entity_id", "target_entity_id", "evidence_ref_ids")
        elif state == "already_present":
            fields = ("assertion_id",)
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
    placements = {
        record_id for (kind, record_id), selection in selections.items()
        if kind == "placement" and selection["action"] == "create"
    }
    if placements != event_ids:
        raise ValueError("Prepare placements differ from reviewed Events")

    edges = {edge["edge_id"]: edge for edge in candidate["edges"]}
    for decision in manifest["edge_decisions"]:
        edge_id = decision["edge_id"]
        selection = selections.get(("edge", edge_id), {})
        publishing = decision["decision"] == "publish"
        if publishing != (selection.get("action") == "create"):
            raise ValueError(f"{edge_id} prepare action differs from review")
        if not publishing:
            continue
        if sorted(selection["metadata"]["evidence_ref_ids"]) != sorted(decision["evidence_ref_ids"]):
            raise ValueError(f"{edge_id} prepare evidence differs from review")
        for endpoint, field in (("from_node_id", "subject_entity_id"),
                                ("to_node_id", "target_entity_id")):
            bound = selections.get(("node", edges[edge_id][endpoint]), {})
            if bound.get("action") != "use_existing" or bound.get("entity_id") != decision[field]:
                raise ValueError(f"{edge_id} prepare endpoint differs from review: {endpoint}")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--prepare-request", type=Path)
    args = parser.parse_args()
    try:
        candidate = json.loads(args.candidate.read_text())
        manifest = json.loads(args.manifest.read_text())
        count = (validate_prepare(candidate, manifest, json.loads(args.prepare_request.read_text()))
                 if args.prepare_request else validate(candidate, manifest))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Checked {count} explicit edge decisions.")


if __name__ == "__main__":
    main()
