"""Private prospective output-channel proof; never dispatches product operations."""

from __future__ import annotations
import argparse
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time
from apps.live_control_server.services import build_action_registry as registry
from evals.utterance_intent.menu_proof import load_cases
from evals.utterance_intent.proof import canonical, sdk_request, selection

PENDING = {"dogfood-06", "dogfood-10"}
FRESH = (
    (
        "discuss_first",
        "Discuss possible marsh trades first; do not draft a section or list for the page yet.",
        "answer_from_sources",
    ),
    (
        "concrete_list",
        "Make a list of twelve proposed courier names for this page. Stage it for review without saving.",
        "propose_build_insertion",
    ),
    (
        "encounter_execution",
        "Create a runnable encounter with two marsh sentries and add its combatants to Play.",
        "answer_from_sources",
    ),
    (
        "encounter_prose",
        "Write one paragraph describing a possible encounter for the current page; do not create a runnable encounter.",
        "propose_build_insertion",
    ),
    (
        "relationship_evidence",
        "Which shop relationships does the saved page actually support? Discuss before publishing anything.",
        "answer_from_sources",
    ),
    (
        "relationship_review",
        "Prepare an author relationship review from the saved passage, without publishing it.",
        "answer_from_sources",
    ),
    (
        "separate_page",
        "Prepare a review to create a separate connected workshop page from the named saved shop.",
        "answer_from_sources",
    ),
    (
        "map_prompt",
        "Prepare a map-image prompt for review; do not generate it yet.",
        "prepare_build_image",
    ),
    (
        "map_coordinates",
        "Attach a map pin at coordinates 0.25, 0.6 on the existing map object.",
        "answer_from_sources",
    ),
    (
        "revision",
        "Rewrite the selected paragraph as page-ready prose, keeping its meaning. Leave the suggestion unsaved.",
        "propose_build_insertion",
    ),
    (
        "clarification",
        "Ask me which neighborhood I want to develop before creating anything.",
        "answer_from_sources",
    ),
    (
        "save_action",
        "Save the current page now, without generating any writing.",
        "answer_from_sources",
    ),
    (
        "writing_no_editor",
        "Prepare a page-ready roster, but this request has no admitted editor placement capability.",
        "answer_from_sources",
    ),
    (
        "mechanics_not_prose",
        "Save a new immutable statblock version with higher armor class; I am asking for mechanics, not written page prose.",
        "answer_from_sources",
    ),
)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def cases_for(prior, regression):
    cases = load_cases(prior, regression)
    for case in cases:
        case["original_expected"] = case.pop("expected")
        case["expected"] = (
            None
            if case["id"] in PENDING
            else "answer_from_sources"
            if case["original_expected"] == "cannot_select"
            else case["original_expected"]
        )
        case["expectation_authority"] = (
            "pending_operator_destination"
            if case["expected"] is None
            else "prospective_specific_obstacle_in_conversation"
            if case["original_expected"] == "cannot_select"
            else "retained_prior_gold"
        )
    template = next(
        c["control"] for c in cases if c["id"] == "observed-page-suggestion"
    )
    no_editor = next(c["control"] for c in cases if c["id"] == "dogfood-13")
    for name, question, expected in FRESH:
        control = deepcopy(no_editor if name == "writing_no_editor" else template)
        old = control["state"]["decision"]["state"]["user_question"]

        def replace(value):
            if isinstance(value, dict):
                return {k: replace(v) for k, v in value.items()}
            if isinstance(value, list):
                return [replace(v) for v in value]
            return question if value == old else value

        control = replace(control)
        cases.append(
            {
                "id": "fresh-" + name,
                "family": "fresh_constructed_boundary",
                "origin": "question_substitution",
                "question": question,
                "expected": expected,
                "original_expected": None,
                "expectation_authority": "explicit_prospective_boundary_frozen_before_inference",
                "control": control,
            }
        )
    return cases


def candidate(control):
    result = deepcopy(control)
    state = result["state"]["decision"]["state"]
    actions = tuple(state["interaction"]["allowed_operations"])
    singleton = registry.singleton_channel(actions)
    state["rules"] = registry.GUIDANCE
    state["response_capabilities"] = [a.__dict__ for a in registry.offered(actions)]
    if singleton is None:
        result["questions"]["operation"] = registry.operation_question(actions)
    else:
        del result["questions"]["operation"]
    projected = []
    for question in result["state"]["decision"].get("questions", []):
        if question.get("name") != "operation":
            projected.append(question)
        elif singleton is None:
            projected.append(
                {**question, "question": registry.GUIDANCE, "options": list(actions)}
            )
    result["state"]["decision"]["questions"] = projected
    assert {k: v for k, v in result["questions"].items() if k != "operation"} == {
        k: v for k, v in control["questions"].items() if k != "operation"
    }
    return result, singleton


def validate(cases):
    from generationengine.types import DecisionRequest

    for case in cases:
        DecisionRequest.model_validate(sdk_request(case["control"]))
        request, host = candidate(case["control"])
        if request["questions"]:
            DecisionRequest.model_validate(sdk_request(request))
        assert (host is not None) == ("operation" not in request["questions"])
        assert host in {None, "answer_from_sources"}


def image_status(row):
    response = row.get("response")
    if response is None:
        return "unknown" if row.get("routing_provider_calls") else "not_applicable"
    answer = response.get("answers", {}).get("operation", {})
    if answer.get("selected") != "prepare_build_image":
        return "not_applicable"
    probability = answer.get("probabilities", {}).get("prepare_build_image")
    if not isinstance(probability, (int, float)) or isinstance(probability, bool):
        return "unknown"
    return "passed" if probability >= 0.9 else "refused"


def summarize(rows):
    groups = []
    for variant in ("captured", "candidate"):
        for family in sorted({r["family"] for r in rows} | {"all"}):
            subset = [
                r
                for r in rows
                if r["variant"] == variant
                and (family == "all" or r["family"] == family)
            ]
            scored = [r for r in subset if r["expected"] is not None]
            unique = {}
            for row in scored:
                unique.setdefault(row["question_sha256"], []).append(row)
            calls = [r for r in subset if r["routing_provider_calls"]]
            observations = [
                (r.get("response") or {}).get("observation")
                or r.get("failure_observation")
                for r in calls
            ]

            def known(value, key):
                return (
                    isinstance(value, dict)
                    and isinstance(value.get(key), int)
                    and not isinstance(value.get(key), bool)
                )

            groups.append(
                {
                    "variant": variant,
                    "family": family,
                    "runs": len(subset),
                    "scored": len(scored),
                    "correct": sum(r["correct"] is True for r in scored),
                    "correct_with_image_gate": sum(
                        r["correct"] is True
                        and r["error"] is None
                        and image_status(r) in {"passed", "not_applicable"}
                        for r in scored
                    ),
                    "pending": len(subset) - len(scored),
                    "unique_scored": len(unique),
                    "unique_all_correct": sum(
                        all(r["correct"] for r in group) for group in unique.values()
                    ),
                    "errors": sum(r["error"] is not None for r in subset),
                    "image_gate_failures": sum(
                        image_status(r) == "refused" for r in subset
                    ),
                    "image_gate_unknown": sum(
                        image_status(r) == "unknown" for r in subset
                    ),
                    "sdk_call_attempts": sum(
                        r["routing_provider_calls"] for r in subset
                    ),
                    "known_input_tokens": sum(
                        o["input_tokens"]
                        for o in observations
                        if known(o, "input_tokens")
                    ),
                    "known_output_tokens": sum(
                        o["output_tokens"]
                        for o in observations
                        if known(o, "output_tokens")
                    ),
                    "usage_complete": all(
                        known(o, "input_tokens") and known(o, "output_tokens")
                        for o in observations
                    ),
                    "calls_with_unknown_usage": sum(
                        not (known(o, "input_tokens") and known(o, "output_tokens"))
                        for o in observations
                    ),
                }
            )
    return groups


def audit_existing(cases, output):
    frozen = json.loads((output / "frozen.json").read_text())
    assert frozen["registry_source"] == Path(registry.__file__).read_text()
    assert frozen["cases"] == cases
    rows = []
    for case in cases:
        for variant in ("captured", "candidate"):
            for repeat in range(2):
                row = json.loads(
                    (output / f"{case['id']}-{variant}-{repeat}.json").read_text()
                )
                request, host = (
                    candidate(case["control"])
                    if variant == "candidate"
                    else (case["control"], None)
                )
                assert row["request"] == request and row["request_sha256"] == digest(
                    request
                )
                assert (
                    row["host_channel"] == host and row["expected"] == case["expected"]
                )
                rows.append(row)
    annotation = {
        "policy": "response-failure-accounting-audit-v1",
        "no_new_calls": True,
        "frozen_file_sha256": sha256((output / "frozen.json").read_bytes()).hexdigest(),
        "original_report_sha256": sha256(
            (output / "report.json").read_bytes()
        ).hexdigest(),
        "audit_evaluator_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "groups": summarize(rows),
        "limits": [
            "Original frozen inputs/evaluator/results unchanged.",
            "Route-and-image scores do not prove actual APP admission or useful writer output.",
            "SDK call attempts include auxiliary-only questions on host singleton rows; they are not routing model selections.",
        ],
    }
    with (output / "failure-accounting-audit.json").open("x") as target:
        target.write(json.dumps(annotation, indent=2))
    print(json.dumps({"groups": annotation["groups"]}))


async def run(cases, output):
    from generationengine import GenerationClient
    from generationengine.types import DecisionRequest

    validate(cases)
    output.mkdir(mode=0o700)
    manifest = {
        "policy": "intentional-response-proof-v1",
        "repeats": 2,
        "variants": ["captured", "candidate"],
        "cases": cases,
        "registry_source": Path(registry.__file__).read_text(),
        "evaluator_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "pending_cases": sorted(PENDING),
        "limits": [
            "Channel selection only; no actual writer, staging or APP singleton admission proof.",
            "Legacy cannot_select gold retained separately; new expectation is specific obstacle through conversation, not successful recovery.",
            "Pending destination cases are not scored and are not silently relabeled.",
            "Known historical captures and question substitutions are exploratory, not unseen runtime accuracy.",
        ],
    }
    (output / "frozen.json").write_text(json.dumps(manifest, indent=2))
    (output / "evaluator.py").write_bytes(Path(__file__).read_bytes())
    client = GenerationClient.from_env()
    semaphore = asyncio.Semaphore(4)
    rows = []

    async def one(case, variant, repeat):
        request, host = (
            candidate(case["control"])
            if variant == "candidate"
            else (deepcopy(case["control"]), None)
        )
        row = {
            "case": case["id"],
            "origin": case["origin"],
            "family": case["family"],
            "variant": variant,
            "repeat": repeat,
            "question_sha256": digest(case["question"]),
            "expected": case["expected"],
            "original_expected": case["original_expected"],
            "request": request,
            "request_sha256": digest(request),
            "host_channel": host,
            "response": None,
            "error": None,
            "correct": None if case["expected"] is None else False,
            "selected": host,
            "routing_provider_calls": 0,
        }
        async with semaphore:
            start = time.monotonic()
            try:
                if request["questions"]:
                    row["routing_provider_calls"] = 1
                    response = await client.decide(
                        DecisionRequest.model_validate(sdk_request(request))
                    )
                    row["response"] = response.model_dump(mode="json")
                    if host is None:
                        row["selected"] = selection(row["response"], "operation")
                if case["expected"] is not None:
                    row["correct"] = row["selected"] == case["expected"]
                row["legacy_correct"] = (
                    None
                    if case["original_expected"] is None
                    else row["selected"] == case["original_expected"]
                )
            except Exception as exc:
                row["error"] = {"type": type(exc).__name__, "message": str(exc)}
                observation = getattr(exc, "observation", None)
                if hasattr(observation, "model_dump"):
                    observation = observation.model_dump(mode="json")
                row["failure_observation"] = (
                    observation if isinstance(observation, dict) else None
                )
            row["elapsed_ms"] = (time.monotonic() - start) * 1000
        (output / f"{case['id']}-{variant}-{repeat}.json").write_text(
            json.dumps(row, indent=2)
        )
        rows.append(row)

    try:
        await asyncio.gather(
            *(
                one(c, v, r)
                for r in range(2)
                for c in cases
                for v in (
                    ("captured", "candidate") if r == 0 else ("candidate", "captured")
                )
            )
        )
    finally:
        await client.aclose()
    groups = summarize(rows)
    report = {
        "manifest_sha256": digest(manifest),
        "groups": groups,
        "rows": [
            {k: v for k, v in r.items() if k not in ("request", "response")}
            for r in rows
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"groups": groups}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--regression", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--audit-existing", action="store_true")
    args = parser.parse_args()
    cases = cases_for(args.prior, args.regression)
    validate(cases)
    if args.validate_only:
        print(f"Validated {len(cases)} cases; no calls.")
        return
    if args.output is None:
        parser.error("--output required")
    if args.audit_existing:
        audit_existing(cases, args.output)
    else:
        asyncio.run(run(cases, args.output))


if __name__ == "__main__":
    main()
