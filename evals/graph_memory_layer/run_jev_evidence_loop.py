"""Run one explicitly supplied frozen case through GE's Jev decision port.

No provider fallback, prose generation, runtime adoption or World writes. Gold
is read only after the acquisition loop has finished and never sent to Jev.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

from evals.graph_memory_layer.jev_evidence_loop import run_loop


def score_gold(result: dict, gold: dict) -> dict:
    units = result["selected_evidence"]
    rows = []
    for fact in gold["facts"]:
        matches = []
        for evidence in fact["evidence"]:
            for unit in units:
                if evidence["quote"] in unit["text"] and any(
                    span["start_line"] <= evidence["start_line"]
                    and span["end_line"] >= evidence["end_line"]
                    for span in unit["provenance"]
                ):
                    matches.append(unit["id"])
        rows.append({"fact_id": fact["id"], "source_support_retained": bool(matches),
                     "supporting_unit_ids": sorted(set(matches))})
    covered = sum(r["source_support_retained"] for r in rows)
    return {"metric": "gold_source_passage_coverage_not_generated_answer_accuracy",
            "covered": covered, "total": len(rows),
            "recall": covered / len(rows) if rows else None, "facts": rows,
            "false_sufficient_stop": result["status"] == "provisionally_supported" and covered < len(rows),
            "semantic_judgment_accuracy": "requires_independent_review",
            "answer_accuracy": "not_measured_no_writer"}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credential-file", type=Path)
    args = parser.parse_args()
    if args.credential_file:
        from dotenv import dotenv_values
        value = dotenv_values(args.credential_file).get("TYPESAFE_JEV_API_KEY")
        if value:
            os.environ["TYPESAFE_JEV_API_KEY"] = value
    if not os.getenv("TYPESAFE_JEV_API_KEY"):
        raise SystemExit("Jev credential unavailable; no inference attempted. Configure TYPESAFE_JEV_API_KEY.")
    from generationengine import GenerationClient
    from generationengine.types import DecisionRequest

    snapshot = json.loads(args.snapshot.read_text())
    # Pin actual version; no moving alias or arbitrary model/prose route.
    if snapshot["model"] != "jev-1.14.0":
        raise ValueError("This experiment is pinned to jev-1.14.0")
    client = GenerationClient.from_env()

    async def evaluate(request: dict) -> dict:
        response = await client.decide(DecisionRequest.model_validate(request))
        return response.model_dump(mode="json")

    try:
        result = await run_loop(snapshot, evaluate, output=args.output)
    finally:
        await client.aclose()
    # Gold is opened strictly after acquisition; never part of evaluator state.
    gold_bytes = args.gold.read_bytes()
    score = score_gold(result, json.loads(gold_bytes))
    score["gold_sha256"] = hashlib.sha256(gold_bytes).hexdigest()
    (args.output / "gold-evaluation.json").write_text(json.dumps(score, indent=2))
    print(json.dumps({"status": result["status"], "rounds": len(result["rounds"]),
                      "elapsed_seconds": result["elapsed_seconds"], "usage_status": result["usage_status"],
                      "gold_coverage": [score["covered"], score["total"]], "luna_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())
