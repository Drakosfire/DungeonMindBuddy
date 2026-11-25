"""Extract timing and provider attribution from Buddy's retained trace log."""

import argparse
import json
from pathlib import Path

_TRACE = "dmb_agent_turn_trace "


def extract(lines):
    """Retain timings and outcome metadata without prompt or reply text."""
    results = []
    for line in lines:
        if not line.startswith(_TRACE):
            continue
        event = json.loads(line[len(_TRACE):])
        if event.get("schema") != "dmb_agent_turn_trace_v1":
            continue
        calls = [
            {key: call.get(key) for key in (
                "provider", "requested_model", "response_model", "duration_ms", "status",
            )}
            for call in event["model_calls"]
        ]
        results.append({
            "turn_id": event["turn_id"],
            "status": event["status"],
            "buddy_elapsed_ms": event["elapsed_ms"],
            "provider_calls": calls,
            "trace_retention": event["retention"],
            "spans": [
                {key: span.get(key) for key in ("kind", "name", "duration_ms", "status")}
                for span in event["spans"]
            ],
        })
    return results


def verify_live_turn_traces(run, traces):
    """Require real retained model work for every measured browser turn."""
    turns = run.get("evidence", {}).get("turns", [])
    if len(turns) != 6 or any(turn.get("stage") != "visible_reply_verified" for turn in turns):
        return False
    if [turn.get("ordinal") for turn in turns] != list(range(1, 7)):
        return False
    client_ids = [turn.get("clientTurnId") for turn in turns]
    visible_ids = [turn.get("turnId") for turn in turns]
    if any(not identity for identity in client_ids + visible_ids):
        return False
    if len(set(client_ids)) != 6 or len(set(visible_ids)) != 6:
        return False
    verified_ids = {
        trace["turn_id"] for trace in traces
        if trace["status"] == "ok" and any(call["status"] == "ok" for call in trace["provider_calls"])
    }
    return all({turn["turnId"], turn["clientTurnId"]} & verified_ids for turn in turns)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("buddy_log", type=Path)
    args = parser.parse_args()
    with args.buddy_log.open() as source:
        print(json.dumps(extract(source), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
