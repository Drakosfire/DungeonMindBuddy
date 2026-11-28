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
                         "selected_text", "prior_dialogue", "current_scene_title"}:
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
        if "current_scene_title" in state and (
            surface != "play" or not state["current_scene_title"].strip()
        ):
            raise ValueError(f"Invalid current scene in {case['id']}")
        if surface not in scopes:
            scopes[surface] = opening_action_menu(surface)
        if surface == "play":
            play_request(state, scopes[surface])
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


def play_request(state, menu):
    from application_state.agent_conversation.native_play_opening import (
        NativePlayOpeningInputV1,
        prepare_play_opening,
    )

    request = prepare_play_opening(NativePlayOpeningInputV1(
        question=state["user_utterance"],
        current_scene_title=state.get("current_scene_title"),
    ))
    if state != request.state:
        raise ValueError("Play fixture state differs from Buddy's opening request")
    question = request.questions[0]
    if dict(question.option_descriptions) == menu and question.options == tuple(menu):
        return request
    return request.model_copy(update={"questions": (question.model_copy(update={
        "options": tuple(menu), "option_descriptions": menu,
    }),)})


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("surface-probe.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--reuse", type=Path, help="Reuse exact fixtures and menus from this capture")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--surface", choices=("build", "plan", "play"))
    parser.add_argument("--play-destination-wording", action="store_true",
                        help="Compare explicit edit destinations in the Play ballot")
    parser.add_argument("--tier", help="Run only cases in this tier while retaining the original menu union")
    args = parser.parse_args()
    if args.play_destination_wording and args.surface != "play":
        parser.error("--play-destination-wording requires --surface play")
    digest, groups, menus = prepare(args.fixtures)
    if args.surface:
        groups = {args.surface: groups[args.surface]}
        menus = {args.surface: menus[args.surface]}
    if args.tier:
        groups = {surface: [case for case in rows if case["tier"] == args.tier]
                  for surface, rows in groups.items()}
        groups = {surface: rows for surface, rows in groups.items() if rows}
        if not groups:
            parser.error("No cases matched that tier")
        menus = {surface: menus[surface] for surface in groups}
    if args.play_destination_wording:
        for menu in menus["play"].values():
            menu.update({
                "play_edit": "Request a change to the current live session scene in Play.",
                "different_destination": "Request work on a different surface or target, such as editing a saved page outside the live scene, or using a separate operator control.",
            })
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
    if "play" in groups:
        sample = groups["play"][0]["input"]
        play = play_request(sample, menus["play"]["scoped"])
        frozen["play_prompt"] = play.questions[0].question
        frozen["play_question"] = play.questions[0].name
    (args.output / "frozen-inputs.json").write_text(json.dumps(frozen, indent=2) + "\n")
    retained = {}
    if args.reuse:
        prior = json.loads((args.reuse / "frozen-inputs.json").read_bytes())
        prior_report = json.loads((args.reuse / "results.json").read_bytes())
        if (any(prior.get(key) != frozen.get(key) for key in ("model", "prompt", "menus", "play_prompt", "play_question"))
            or any(tuple(menu) != tuple(menus[surface][arm])
                   for surface, arms in prior["menus"].items() for arm, menu in arms.items())
        ):
            raise ValueError("Reuse requires the exact model, prompt and menus")
        for surface, cases in prior["cases"].items():
            by_id = {case["id"]: case for case in cases}
            retained[surface] = {}
            for arm, report in prior_report[surface].items():
                retained[surface][arm] = {
                    row["id"]: (by_id[row["id"]], row) for row in report["rows"]
                }
    client = GenerationClient.from_env()

    async def decide(body):
        menu = body["action_definitions"]
        payload = {"model": model, "state": body["state"], "questions": {"intent": {
            "question": body["instructions"], "options": list(menu), "option_descriptions": menu}}}
        request = (play_request(body["state"], menu) if body["state"]["surface"] == "play"
                   else DecisionRequest.model_validate(sdk_request(payload)))
        result = (await client.decide(request)).model_dump(mode="json")
        try:
            return selection(result, request.questions[0].name), result
        except (KeyError, TypeError, ValueError):
            return None, result

    report = {}
    try:
        for index, (surface, cases) in enumerate(groups.items()):
            report[surface] = {}
            arms = ("full", "scoped") if index % 2 == 0 else ("scoped", "full")
            for arm in arms:
                prior_rows = retained.get(surface, {}).get(arm, {})
                reused = {case["id"]: prior_rows[case["id"]][1] for case in cases
                          if case["id"] in prior_rows and prior_rows[case["id"]][0] == case}
                fresh = await evaluate_suite(
                    [case for case in cases if case["id"] not in reused],
                    menus[surface][arm], decide, concurrency=4,
                )
                by_id = reused | {row["id"]: row for row in fresh}
                rows = [by_id[case["id"]] for case in cases]
                report[surface][arm] = {"summary": result_summary(rows), "rows": rows,
                                        "reused": list(reused)}
    finally:
        await client.aclose()
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print({surface: {arm: result["summary"] for arm, result in arms.items()}
           for surface, arms in report.items()})


if __name__ == "__main__":
    asyncio.run(main())
