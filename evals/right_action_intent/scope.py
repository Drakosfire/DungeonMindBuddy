"""Compare the current owner-scoped intent menus on fixed surface fixtures."""
import argparse
import asyncio
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import os

from application_state.agent_conversation.surface_action_catalog import (
    UNIVERSAL_OPENING_ACTIONS,
    opening_action_menu,
)
from evals.right_action_intent.run import PROMPT, evaluate_suite, result_summary


def prepare(path):
    raw = path.read_bytes()
    suite = json.loads(raw)
    if suite["schema"] != "buddy.right-action-surface-probe.v1":
        raise ValueError("Unexpected surface fixture schema")
    cases = suite["cases"]
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Cases require unique IDs")
    scopes = {}
    groups = defaultdict(list)
    for case in cases:
        state = case["input"]
        if set(state) - {"surface", "user_utterance", "page_title", "page_markdown",
                         "selected_text", "prior_dialogue"}:
            raise ValueError(f"Invalid model input fields in {case['id']}")
        if not state["user_utterance"].strip() or not case["reason"].strip():
            raise ValueError(f"Missing utterance or expected-action rationale in {case['id']}")
        if "selected_text" in state and (
            not state["selected_text"].strip()
            or not state.get("page_title")
            or state.get("page_markdown", "").count(state["selected_text"]) != 1
        ):
            raise ValueError(f"Selection must resolve exactly once in {case['id']}")
        surface = state["surface"]
        if surface not in scopes:
            scopes[surface] = opening_action_menu(surface)
        if case["expected"] not in scopes[surface]:
            raise ValueError(f"{case['id']} expects a choice unavailable on {surface}")
        groups[surface].append(case)

    combined = {}
    for menu in scopes.values():
        combined.update(menu)
    menus = {}
    for surface, local in scopes.items():
        aliases = {label for owner_labels in UNIVERSAL_OPENING_ACTIONS.values()
                   for owner, label in owner_labels.items()
                   if owner != surface and label != owner_labels.get(surface)}
        menus[surface] = {"scoped": local, "full": local | {
            label: meaning for label, meaning in combined.items()
            if label not in local and label not in aliases}}
    return sha256(raw).hexdigest(), groups, menus


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("surface-probe.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    digest, groups, menus = prepare(args.fixtures)
    if args.validate_only:
        print(digest, {surface: len(rows) for surface, rows in groups.items()})
        return
    if args.output is None or args.output.exists():
        parser.error("A new --output directory is required")

    from dotenv import dotenv_values
    from evals.utterance_intent.proof import sdk_request, selection
    from generationengine import GenerationClient
    from generationengine.types import DecisionRequest

    if args.credential_file:
        os.environ["TYPESAFE_JEV_API_KEY"] = dotenv_values(args.credential_file)["TYPESAFE_JEV_API_KEY"]
    model = "jev-1.14.0"
    args.output.mkdir()
    frozen = {"fixture_sha256": digest, "model": model, "prompt": PROMPT,
              "menus": menus, "cases": groups}
    (args.output / "frozen-inputs.json").write_text(json.dumps(frozen, indent=2) + "\n")
    client = GenerationClient.from_env()

    async def decide(body):
        menu = body["action_definitions"]
        payload = {"model": model, "state": body["state"], "questions": {"intent": {
            "question": body["instructions"], "options": list(menu), "option_descriptions": menu}}}
        result = (await client.decide(DecisionRequest.model_validate(sdk_request(payload)))).model_dump(mode="json")
        try:
            return selection(result, "intent"), result
        except (KeyError, TypeError, ValueError):
            return None, result

    report = {}
    try:
        for index, (surface, cases) in enumerate(groups.items()):
            report[surface] = {}
            arms = ("full", "scoped") if index % 2 == 0 else ("scoped", "full")
            for arm in arms:
                rows = await evaluate_suite(cases, menus[surface][arm], decide, concurrency=4)
                report[surface][arm] = {"summary": result_summary(rows), "rows": rows}
    finally:
        await client.aclose()
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print({surface: {arm: result["summary"] for arm, result in arms.items()}
           for surface, arms in report.items()})


if __name__ == "__main__":
    asyncio.run(main())
