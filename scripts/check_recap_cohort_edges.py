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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        count = validate(json.loads(args.candidate.read_text()), json.loads(args.manifest.read_text()))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Checked {count} explicit edge decisions.")


if __name__ == "__main__":
    main()
