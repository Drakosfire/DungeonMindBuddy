"""Summarize validated Old Bath House timing samples and compare releases."""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

CHECKS = {
    "exact_statblock_and_portrait",
    "confirmed_plan_attachment",
    "parley_unstarted",
    "explicit_combat_start",
    "distinct_running_encounter",
    "plan_unchanged",
}
PHASES = {
    "pinned-assets": {
        "portrait_binding", "encounter_assembly", "plan_attachment",
        "play_session_create", "play_preview", "combat_start", "statblock_render",
    },
    "live-provider": {
        "first_visible_reply", "reply_finished", "statblock_generation",
        "portrait_generation", "portrait_binding", "encounter_assembly",
        "plan_attachment", "play_session_create", "play_preview", "combat_start", "statblock_render",
    },
}


def summarize(records):
    groups = defaultdict(list)
    seen = set()
    for record in records:
        run_id = record["run_id"]
        if run_id in seen:
            raise ValueError(f"Duplicate run ID: {run_id}")
        seen.add(run_id)
        key = (record["track"], record["fixture_digest"], record["conditions"])
        groups[key].append(record)

    summary = {}
    for key, runs in sorted(groups.items()):
        phases = PHASES[key[0]]
        samples = defaultdict(list)
        rejected = {}
        for run in runs:
            failures = list(run.get("failures", []))
            for check in sorted(CHECKS):
                if run.get("checks", {}).get(check) is not True:
                    failures.append(f"Correctness check failed or missing: {check}")
            timings = run.get("timings_ms", {})
            for phase in sorted(phases):
                value = timings.get(phase)
                if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
                    failures.append(f"Invalid or missing measurement: {phase}")
            if failures:
                rejected[run["run_id"]] = failures
                continue
            for phase in sorted(phases):
                samples[phase].append(timings[phase])
        summary[key] = {
            "candidate_runs": len(runs),
            "accepted_runs": len(runs) - len(rejected),
            "rejected": rejected,
            "phases_ms": {phase: distribution(values) for phase, values in samples.items()},
        }
    return summary


def distribution(values):
    ordered = sorted(values)
    count = len(ordered)
    return {
        "n": count,
        "min": ordered[0],
        "median": median(ordered),
        "max": ordered[-1],
        # Use nearest rank and omit p95 when fewer than 20 runs would make it the maximum.
        "p95": ordered[math.ceil(0.95 * count) - 1] if count >= 20 else None,
    }


def compare(baseline, candidate):
    report = []
    for key in sorted(baseline.keys() | candidate.keys()):
        before = baseline.get(key)
        after = candidate.get(key)
        deltas = {}
        if before and after:
            for phase, timing in before["phases_ms"].items():
                if phase in after["phases_ms"]:
                    deltas[phase] = after["phases_ms"][phase]["median"] - timing["median"]
        report.append({
            "track": key[0], "fixture_digest": key[1], "conditions": key[2],
            "baseline": before, "candidate": after, "median_delta_ms": deltas,
        })
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="Baseline JSON array of run records")
    parser.add_argument("candidate", type=Path, nargs="?", help="Candidate JSON array of run records")
    args = parser.parse_args()
    baseline = summarize(json.loads(args.baseline.read_text()))
    candidate = summarize(json.loads(args.candidate.read_text())) if args.candidate else {}
    print(json.dumps(compare(baseline, candidate), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
