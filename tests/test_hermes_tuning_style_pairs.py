from __future__ import annotations

import importlib.util
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
