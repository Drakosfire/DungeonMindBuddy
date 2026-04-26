"""Unit tests for H1 violation taxonomy (no LLM)."""

from __future__ import annotations

from collections import Counter

import pytest

from evals.sentence_routing_retrieval_falsification.h1_routing_evidence import (
    classify_sidecar_violations,
    classify_stage_b_violation,
    compute_directional_scorecard,
    h1_decision_from_counts,
)


@pytest.mark.parametrize(
    ("viol", "text", "expected"),
    [
        ("B0: missing route rows for unit_ids: ['u-1']", "", "schema_row_integrity"),
        (
            "B1: must_route unit 'u-X' missing expected hubs ['a'] (assigned=[])",
            "Bonogo swings.",
            "named_pc_omission",
        ),
        (
            "B1: must_route unit 'u-X' missing expected hubs ['a', 'b'] (assigned=[])",
            "The team agreed to clear the rats.",
            "party_reference_boundary",
        ),
        (
            "B1: must_route unit 'u-X' missing expected hubs ['bonogo'] (assigned=[])",
            "He quite enjoyed the hike.",
            "pronoun_carryover",
        ),
        (
            "B2: must_abstain unit 'u-X' has 6 hubs > max_assigned_hubs=0",
            "As the group approached it resolved into a statue.",
            "party_reference_boundary",
        ),
        (
            "B2: must_abstain unit 'u-X' must have needs_new_hub_candidate false (got true)",
            "Glowkindle posted a notice.",
            "out_of_manifest_candidate",
        ),
    ],
)
def test_classify_stage_b_violation(viol: str, text: str, expected: str) -> None:
    assert classify_stage_b_violation(viol, unit_text=text) == expected


def test_classify_sidecar_uses_unit_text() -> None:
    side = {
        "sentence_units": [
            {"unit_id": "u-L0026-01", "text": "A fine first combat to bring the team together!"},
        ],
        "violations": {
            "stage_b": [
                "B1: must_route unit 'u-L0026-01' missing expected hubs ['a'] (assigned=[])",
            ],
        },
    }
    pairs = classify_sidecar_violations(side)
    assert pairs[0][1] == "party_reference_boundary"


def test_h1_decision_accept() -> None:
    v, _ = h1_decision_from_counts(
        Counter({"party_reference_boundary": 10, "named_pc_omission": 3})
    )
    assert v == "ACCEPT_H1"


def test_h1_decision_reject_named() -> None:
    v, _ = h1_decision_from_counts(
        Counter({"party_reference_boundary": 2, "named_pc_omission": 12})
    )
    assert v == "REJECT_H1"


def test_h1_decision_reject_schema() -> None:
    v, _ = h1_decision_from_counts(
        Counter({"schema_row_integrity": 8, "party_reference_boundary": 3, "named_pc_omission": 2})
    )
    assert v == "REJECT_H1"


def test_directional_scorecard_plan_aligned_keys() -> None:
    scenario = {
        "input": {
            "hub_manifest": [
                {
                    "slug": "npc_a",
                    "path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/PCs/bonogo/README.md",
                    "subject_class": "pc",
                    "campaign_id": "longmont-c1",
                    "label": "test",
                }
            ]
        },
        "gold_routing": {
            "must_route": [
                {"unit_id": "u1", "expected_hubs": ["npc_a"], "max_extra_hubs": 0},
            ],
            "must_abstain": [
                {
                    "unit_id": "u2",
                    "max_assigned_hubs": 0,
                    "needs_new_hub_candidate": False,
                },
            ],
        },
    }
    sidecar = {
        "sentence_units": [
            {"unit_id": "u1", "line_start": 1, "line_end": 1, "text": "npc_a strikes."},
            {"unit_id": "u2", "line_start": 2, "line_end": 2, "text": "As the group walked north."},
        ],
        "routes": [
            {
                "unit_id": "u1",
                "assigned_hubs": ["npc_a"],
                "confidence": "high",
                "rationale": "Names npc_a.",
                "needs_new_hub_candidate": False,
            },
            {
                "unit_id": "u2",
                "assigned_hubs": [],
                "confidence": "low",
                "rationale": "Travel beat.",
                "needs_new_hub_candidate": False,
            },
        ],
    }
    sc = compute_directional_scorecard(scenario=scenario, sidecar=sidecar)
    assert sc["named_pc_recall"] == 1.0
    assert sc["party_boundary_precision"] == 1.0
    assert sc["candidate_sanity"] == 1.0
