"""Compare the current owner-scoped intent menus on fixed surface fixtures."""
import argparse
import asyncio
from collections import Counter, defaultdict
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
        elif surface == "plan":
            plan_request(state)
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
        dialogue=tuple(state.get("prior_dialogue", ())),
    ))
    if state != request.state:
        raise ValueError("Play fixture state differs from Buddy's opening request")
    return with_menu(request, menu)


def plan_request(state):
    from application_state.agent_conversation.native_plan_opening import NativePlanIntentInputV1

    return NativePlanIntentInputV1(
        question=state["user_utterance"], page_title=state.get("page_title"),
        selected_text=state.get("selected_text"),
        dialogue=tuple(state.get("prior_dialogue", ())),
    ).prepare()


def with_menu(request, menu):
    question = request.questions[0]
    if dict(question.option_descriptions) == menu and question.options == tuple(menu):
        return request
    return request.model_copy(update={"questions": (question.model_copy(update={
        "options": tuple(menu), "option_descriptions": menu,
    }),)})


def build_wire(state, menu, model, *, intent_only=False):
    from application_state.agent_conversation.build_intentional_response import (
        SCOPED_BUILD_MENU_DIGEST, opening_work_question, source_need_question,
    )

    work = opening_work_question(SCOPED_BUILD_MENU_DIGEST)
    for label, meaning in menu.items():
        if label not in work["criteria"]:
            work["criteria"][label] = None
            work["instructions"] += f"\n{label}: {meaning}"
    selection = state.get("selected_text")
    return {
        "model": model,
        "state": {"user_question": state["user_utterance"], "interaction": {
            "allowed_operations": ["answer_from_sources", "propose_build_insertion"],
            "current_page_title": state.get("page_title", "Current Build page"),
            "history": state.get("prior_dialogue", []),
            "page_target": {"kind": "replace_selection", "text": selection} if selection else None,
            "working_draft_available": False,
        }},
        "questions": {
            "requested_work": work,
            **({} if intent_only else {"source_need": source_need_question()}),
        },
    }


def decision_summary(rows, surface):
    deferrals = {"needs_context_to_choose", "clarify_request", "clarify_creation"}
    if surface == "plan":
        deferrals.add("clarify")
    counts = Counter()
    tied = 0
    for row in rows:
        status = row["status"]
        if status == "correct" and row["expected"] in deferrals:
            status = "valid_deferral"
        elif status == "unnecessary_deferral" or (status == "wrong_action" and row["choice"] in deferrals):
            status = "invalid_deferral"
        counts[status] += 1
        answers = row["response"].get("answers", {})
        question = answers.get("requested_work") or answers.get("intent") or {}
        probabilities = list((question.get("probabilities") or {}).values())
        if probabilities and probabilities.count(max(probabilities)) > 1:
            tied += 1
    original = result_summary(rows)
    return {"cases": len(rows), "dispositions": dict(counts),
            "top_score_ties": tied, "median_decision_ms": original["median_decision_ms"]}


def grouped_summary(rows, surface):
    by_action = defaultdict(list)
    for row in rows:
        by_action[row["expected"]].append(row)
    return {"decision_summary": decision_summary(rows, surface),
            "by_action": {action: decision_summary(group, surface)
                          for action, group in by_action.items()}}


def retained_cohort(path):
    manifest = json.loads(path.read_bytes())
    fixture_digest, groups, menus = prepare(path.parent / manifest["fixtures"])
    if fixture_digest != manifest["fixture_sha256"]:
        raise ValueError("Frozen cohort fixture hash changed")
    results = defaultdict(dict)
    for entry in manifest["captures"]:
        raw = (path.parent / entry["file"]).read_bytes()
        if sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"Retained capture changed: {entry['file']}")
        capture = json.loads(raw)
        for key in entry.get("path", ()):
            capture = capture[key]
        surface = entry["surface"]
        recorded = capture["menus"][surface]
        if (capture["model"] != manifest["model"] or set(recorded) != set(menus[surface])
                or any(list(menu.items()) != list(menus[surface][arm].items())
                       for arm, menu in recorded.items())):
            raise ValueError(f"Retained model or menu differs for {surface}")
        if surface == "build" and "wire_questions" in capture:
            for case in groups[surface]:
                for arm, menu in menus[surface].items():
                    wire = build_wire(case["input"], menu, manifest["model"])
                    if (wire["state"] != capture["wire_states"][case["id"]]
                            or wire["questions"] != capture["wire_questions"][arm]
                            or tuple(wire["questions"]["requested_work"]["criteria"]) != tuple(
                                capture["wire_questions"][arm]["requested_work"]["criteria"]
                            )):
                        raise ValueError(f"Build wire changed for {case['id']} {arm}")
        for arm, data in capture["results"][surface].items():
            rows = results[surface].setdefault(arm, [])
            rows.extend(data["rows"])
    if set(results) != set(groups):
        raise ValueError("Retained cohort omits a fixture surface")
    for surface, cases in groups.items():
        expected = {case["id"]: case["expected"] for case in cases}
        if set(results[surface]) != {"full", "scoped"}:
            raise ValueError(f"Incomplete retained pair for {surface}")
        for rows in results[surface].values():
            if len(rows) != len(expected) or {row["id"]: row["expected"] for row in rows} != expected:
                raise ValueError(f"Retained cohort differs from fixtures for {surface}")
    return {surface: {arm: grouped_summary(rows, surface) for arm, rows in arms.items()}
            for surface, arms in results.items()}


def verify_build_followup_capture(path):
    from application_state.agent_conversation.build_intentional_response import (
        SCOPED_BUILD_MENU_DIGEST, verify_build_intent_opening, verify_build_source_followup,
    )

    capture = json.loads(path.read_bytes())
    inputs = {}
    for name, expected_hash in capture["pins"].items():
        raw = (path.parent / name).read_bytes()
        if sha256(raw).hexdigest() != expected_hash:
            raise ValueError(f"Build source follow-up pin changed: {name}")
        inputs[name] = json.loads(raw)
    intent = inputs["build-intent-only-cohort-jev.json"]
    opening_rows = {row["id"]: row for row in intent["results"]["build"]["scoped"]["rows"]}
    gold = {row["id"]: row["expected"] for row in inputs["build-source-followup-cases.json"]["cases"]}
    if len(capture["rows"]) != len(gold) or {row["id"] for row in capture["rows"]} != set(gold):
        raise ValueError("Build source follow-up case coverage changed")
    count = Counter()
    for row in capture["rows"]:
        case_id, action = row["id"], row["action"]
        opening_row = opening_rows[case_id]
        opening_wire = {
            "model": intent["model"],
            "state": intent["wire_states"][case_id],
            "questions": intent["wire_questions"]["scoped"],
        }
        if verify_build_intent_opening(
            opening_wire, opening_row["response"], menu_digest=SCOPED_BUILD_MENU_DIGEST,
        ) != action or opening_row["choice"] != action:
            raise ValueError("Build source follow-up action differs from its retained first result")
        if action in {"clarify_request", "clarify_creation"}:
            if "request" in row or "response" in row:
                raise ValueError("Build clarification dispatched a source-scope decision")
            choice = "skip"
        else:
            choice = verify_build_source_followup(opening_wire, opening_row["response"],
                menu_digest=SCOPED_BUILD_MENU_DIGEST, wire=row["request"], response=row["response"])
        if choice != row["choice"] or gold[case_id] != row["expected"]:
            raise ValueError("Build source follow-up scoring differs from retained evidence")
        count["correct" if choice == gold[case_id] else "incorrect"] += 1
    return dict(count)


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
    parser.add_argument("--frozen-cohort", type=Path, help="Verify and summarize a pinned set of retained captures")
    parser.add_argument("--summarize", type=Path, help="Summarize a retained paired capture without a provider")
    parser.add_argument("--plan-intent-only", action="store_true",
                        help="Evaluate the shared source-blind intent request for Plan")
    parser.add_argument("--build-wire-shape", action="store_true",
                        help="Use the ordinary Build question instructions and source-need ballot")
    parser.add_argument("--build-intent-only", action="store_true",
                        help="Ablate the source-need question from the scoped ordinary Build request")
    parser.add_argument("--verify-build-followup", type=Path,
                        help="Validate the retained Build follow-up capture without calling a provider")
    args = parser.parse_args()
    if args.verify_build_followup:
        print(json.dumps(verify_build_followup_capture(args.verify_build_followup), indent=2))
        return
    if args.build_intent_only and not args.build_wire_shape:
        parser.error("--build-intent-only requires --build-wire-shape")
    if args.build_wire_shape and args.surface != "build":
        parser.error("--build-wire-shape requires --surface build")
    if args.plan_intent_only and args.surface != "plan":
        parser.error("--plan-intent-only requires --surface plan")
    if args.frozen_cohort:
        print(json.dumps(retained_cohort(args.frozen_cohort), indent=2))
        return
    if args.summarize:
        capture = json.loads(args.summarize.read_bytes())
        results = capture.get("results", capture)
        print(json.dumps({
            surface: {arm: grouped_summary(value["rows"], surface) for arm, value in arms.items()}
            for surface, arms in results.items()
        }, indent=2))
        return
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
    if args.build_intent_only:
        menus["build"] = {"scoped": menus["build"]["scoped"]}
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
    if args.plan_intent_only:
        plan = plan_request(groups["plan"][0]["input"])
        frozen["plan_prompt"] = plan.questions[0].question
        frozen["plan_question"] = plan.questions[0].name
        frozen["plan_wire_state_by_case"] = {row["id"]: plan_request(row["input"]).state
                                            for row in groups["plan"]}
    if args.build_wire_shape:
        frozen["build_wire_by_case"] = {
            row["id"]: {arm: build_wire(row["input"], menu, model, intent_only=args.build_intent_only)
                        for arm, menu in menus["build"].items()}
            for row in groups["build"]
        }
    (args.output / "frozen-inputs.json").write_text(json.dumps(frozen, indent=2) + "\n")
    retained = {}
    if args.reuse:
        prior = json.loads((args.reuse / "frozen-inputs.json").read_bytes())
        prior_report = json.loads((args.reuse / "results.json").read_bytes())
        if (any(prior.get(key) != frozen.get(key) for key in ("model", "prompt", "menus", "play_prompt", "play_question", "plan_prompt", "plan_question", "plan_wire_state_by_case", "build_wire_by_case"))
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
        if args.build_wire_shape:
            request = DecisionRequest.model_validate(sdk_request(build_wire(body["state"], menu, model, intent_only=args.build_intent_only)))
        elif args.plan_intent_only:
            request = with_menu(plan_request(body["state"]), menu)
        else:
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
            for arm in (name for name in arms if name in menus[surface]):
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
                                        "reused": list(reused), **grouped_summary(rows, surface)}
    finally:
        await client.aclose()
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print({surface: {arm: result["summary"] for arm, result in arms.items()}
           for surface, arms in report.items()})


if __name__ == "__main__":
    asyncio.run(main())
