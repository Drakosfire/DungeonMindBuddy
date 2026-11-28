"""Run the single-decision Right Action benchmark against one model."""
import argparse
import asyncio
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
from time import monotonic


PROMPT = (
    "Identify the user's intent for this turn. Use the supplied dialogue where needed. "
    "If the available evidence leaves the intent unclear, choose needs_context_to_choose. "
    "Return one action family. Target binding, available tools, and execution are downstream."
)


def load_suite(path):
    raw = path.read_bytes()
    suite = json.loads(raw)
    actions, cases = suite["actions"], suite["cases"]
    if suite["schema"] not in {"buddy.right-action-intent.v1", "buddy.right-action-intent.v2"}:
        raise ValueError("Unexpected benchmark schema")
    if len({case["id"] for case in cases}) != len(cases) or set(actions) != {case["expected"] for case in cases}:
        raise ValueError("Each case needs a unique ID and every action needs Gold")
    for case in cases:
        if (not case["input"].get("user_utterance")
                or set(case["input"]) - {"user_utterance", "dialogue", "history", "prior_dialogue", "prior_dialogue_and_pending_work", "editor_context"}):
            raise ValueError(f"Unexpected model-visible input for {case['id']}")
        editor = case["input"].get("editor_context")
        if editor is not None and (
            set(editor) != {"page_title", "page_markdown", "selected_text"}
            or any(not isinstance(value, str) or not value.strip() for value in editor.values())
            or editor["page_markdown"].count(editor["selected_text"]) != 1
        ):
            raise ValueError(f"Expected one exact selected sentence in {case['id']}")
    return sha256(raw).hexdigest(), actions, cases


def result_summary(rows):
    dispositions = Counter(row["status"] for row in rows)
    timings = [row["elapsed_ms"] for row in rows if row["status"] != "provider_error"]
    return {"cases": len(rows), "dispositions": dict(dispositions),
            "median_decision_ms": round(median(timings), 2) if timings else None}


def grade_choice(choice, expected, actions):
    if choice not in actions:
        return "invalid_output"
    if choice == expected:
        return "correct"
    if choice == "needs_context_to_choose":
        return "unnecessary_deferral"
    if expected == "needs_context_to_choose":
        return "guessed_without_context"
    return "wrong_action"


async def evaluate_suite(cases, actions, decide, concurrency):
    tasks = asyncio.Semaphore(concurrency)

    async def run_case(case):
        body = {"state": case["input"], "action_definitions": actions, "instructions": PROMPT}
        async with tasks:
            started = monotonic()
            try:
                choice, response = await decide(body)
            except Exception as error:
                choice, response = None, {"error": type(error).__name__}
                status = "provider_error"
            else:
                status = grade_choice(choice, case["expected"], actions)
            elapsed = (monotonic() - started) * 1000
        return {"id": case["id"], "tier": case["tier"], "expected": case["expected"],
                "choice": choice, "status": status, "elapsed_ms": round(elapsed, 2), "response": response}
    return await asyncio.gather(*(run_case(case) for case in cases))


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--model", default="jev-1.14.0")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    pin, actions, cases = load_suite(args.suite)
    if args.validate_only:
        print(f"{len(cases)} cases, {len(actions)} actions, SHA-256 {pin}")
        return
    if args.output is None:
        parser.error("Supply --output for a live run")
    if args.output.exists():
        parser.error("The output file already exists")
    if args.credential_file:
        from dotenv import dotenv_values
        os.environ["TYPESAFE_JEV_API_KEY"] = dotenv_values(args.credential_file)["TYPESAFE_JEV_API_KEY"]
    from evals.utterance_intent.proof import sdk_request, selection
    from generationengine import GenerationClient
    from generationengine.types import DecisionRequest

    client = GenerationClient.from_env()

    async def decide(body):
        packet = {"model": args.model, "state": body["state"], "questions": {
            "intent": {"question": body["instructions"], "type": "choice",
                       "options": list(body["action_definitions"]), "option_descriptions": body["action_definitions"]}}}
        response = (await client.decide(DecisionRequest.model_validate(sdk_request(packet)))).model_dump(mode="json")
        try:
            return selection(response, "intent"), response
        except (KeyError, ValueError, TypeError):
            return None, response

    try:
        rows = await evaluate_suite(cases, actions, decide, concurrency=4)
    finally:
        await client.aclose()
    dimensions = {}
    for field in ("tier", "expected"):
        groups = defaultdict(list)
        for row in rows:
            groups[row[field]].append(row)
        dimensions[field] = {key: result_summary(group) for key, group in sorted(groups.items())}
    report = {"suite_sha256": pin, "provider": "typesafe", "model": args.model, "prompt": PROMPT,
              "summary": result_summary(rows), "breakdowns": dimensions, "rows": rows}
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    asyncio.run(main())
