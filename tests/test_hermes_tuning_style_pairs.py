from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_style_pairs", ROOT / "evals/hermes_tuning/run_style_pairs.py"
)
assert SPEC and SPEC.loader
style_pairs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(style_pairs)


def test_fixture_is_twelve_unique_synthetic_cases_and_prompt_parity() -> None:
    cases, voice = style_pairs.load_cases()
    fixture = json.loads(
        (ROOT / "evals/hermes_tuning/style_cases.json").read_text(encoding="utf-8")
    )
    assert "fully synthetic" in fixture["source"]
    assert len(cases) == 12
    assert len({case["case_id"] for case in cases}) == 12
    for case in cases:
        base, challenger = style_pairs.build_prompts(case, voice)
        assert challenger == base + "\n" + voice
        assert case["supported_facts"] and case["known_unknowns"]


def test_hard_gates_keep_format_and_trace_failures_separate() -> None:
    passing = style_pairs.hard_gates(
        "Check the bridge before dusk; Nera's whereabouts are unknown.",
        "ok",
        0,
        1,
    )
    assert passing["gates"]["all_pass"]
    assert not style_pairs.hard_gates("- Unknown.", "ok", 0, 1)["gates"][
        "no_heading_or_bullets"
    ]
    assert not style_pairs.hard_gates("A short answer.", "error", 0, 1)["gates"][
        "turn_status_ok"
    ]
    assert not style_pairs.hard_gates("It is clear.", "ok", 1, 1)["gates"][
        "no_tool_events"
    ]
    assert not style_pairs.hard_gates("It is unclear.", "ok", 0, 2)["gates"][
        "exactly_one_model_call"
    ]
    too_long = " ".join(["unknown"] * 101)
    assert not style_pairs.hard_gates(too_long, "ok", 0, 1)["gates"][
        "at_most_100_words"
    ]


def test_blind_packet_removes_conditions_and_measurements() -> None:
    cases, _ = style_pairs.load_cases()
    record = {
        "cases": [
            {
                "case_id": cases[0]["case_id"],
                "arms": {
                    "control": {"answer": "A grounded answer."},
                    "voice": {"answer": "A warmer answer."},
                },
                "wall_ms": 123,
                "cost": 1,
            }
        ]
    }
    packet = style_pairs.blinded_packet(record, cases, 3)
    encoded = json.dumps(packet)
    for forbidden in (
        "control",
        "voice",
        "arm_order",
        "wall_ms",
        "estimated_cost",
        "calm, practical co-GM",
    ):
        assert forbidden not in encoded
    assert packet["items"][0]["human_hard_gate_review"] == "pending"
    assert {packet["items"][0]["answer_A"], packet["items"][0]["answer_B"]} == {
        "A grounded answer.",
        "A warmer answer.",
    }


def test_locked_blind_scores_map_to_exactly_one_raw_arm_and_recompute() -> None:
    artifact = json.loads(
        (
            ROOT / "evals/hermes_tuning/artifacts/style-pairs-20261002T085003Z.json"
        ).read_text(encoding="utf-8")
    )
    raw_cases = {case["case_id"]: case for case in artifact["cases"]}
    dimensions = 4

    for result in artifact["blind_review_case_results"]:
        case_id = result["case_id"]
        raw = raw_cases[case_id]
        mapping = result["blind_label_to_arm"]
        for label in ("A", "B"):
            blind_hash = result["blind_answer_sha256"][label]
            matching_arms = [
                arm
                for arm in ("control", "voice")
                if hashlib.sha256(
                    raw["arms"][arm]["answer"].encode("utf-8")
                ).hexdigest()
                == blind_hash
            ]
            assert len(matching_arms) == 1
            assert mapping[label] == matching_arms[0]

    expected_failures = {
        "northfield-well": "control",
        "gloam-orchard": "voice",
    }
    for case_id, expected_arm in expected_failures.items():
        result = next(
            row
            for row in artifact["blind_review_case_results"]
            if row["case_id"] == case_id
        )
        for reviewer in ("PRIME", "independent_reviewer"):
            review = result["reviews"][reviewer]
            if reviewer == "PRIME":
                failed_labels = [
                    label
                    for label, gate in review["hard_gates"].items()
                    if gate == "fail_grounding"
                ]
            else:
                failed_labels = [
                    label
                    for label in ("A", "B")
                    if review[label]["gates"]["factual_grounding"] == "fail"
                ]
            assert len(failed_labels) == 1
            assert result["blind_label_to_arm"][failed_labels[0]] == expected_arm
        assert (
            artifact["human_gate_adjudication"]["results"][case_id][expected_arm]
            == "fail_grounding"
        )

    summary = artifact["blinded_review_summary"]
    for reviewer in ("PRIME", "independent_reviewer"):
        preference_by_arm = {"control": 0, "voice": 0, "tie": 0}
        scores_by_arm = {
            "control": [[] for _ in range(dimensions)],
            "voice": [[] for _ in range(dimensions)],
        }
        eligible_case_ids = []
        for result in artifact["blind_review_case_results"]:
            review = result["reviews"][reviewer]
            if reviewer == "PRIME":
                both_pass = all(
                    review["hard_gates"][label] == "pass" for label in ("A", "B")
                )
            else:
                both_pass = all(
                    all(value == "pass" for value in review[label]["gates"].values())
                    for label in ("A", "B")
                )
            if not both_pass:
                continue
            eligible_case_ids.append(result["case_id"])
            preference = review["preference"]
            preferred_arm = (
                "tie"
                if preference == "tie"
                else result["blind_label_to_arm"][preference]
            )
            preference_by_arm[preferred_arm] += 1
            for label in ("A", "B"):
                arm = result["blind_label_to_arm"][label]
                values = (
                    review["scores"][label]
                    if reviewer == "PRIME"
                    else review[label]["scores"]
                )
                assert values is not None
                for index, score in enumerate(values):
                    scores_by_arm[arm][index].append(score)

        means = {
            arm: [
                round(sum(values) / len(values), 3) if values else None
                for values in dimensions_by_arm
            ]
            for arm, dimensions_by_arm in scores_by_arm.items()
        }
        assert len(eligible_case_ids) == 10
        assert set(eligible_case_ids) == set(summary[reviewer]["eligible_case_ids"])
        assert preference_by_arm == summary[reviewer]["preference_by_arm"]
        assert means == summary[reviewer]["mean_scores_by_arm"]
