"""Unit tests for hermes_small_slice scoring (no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from evals.hermes_small_slice.score import aggregate_question_trials, score_trial

ROOT = Path(__file__).resolve().parents[2]
GOLD = json.loads(
    (ROOT / "evals/hermes_small_slice/gold/of_conks_grotesque_tree_v1.json").read_text(
        encoding="utf-8"
    )
)


def _question(qid: str) -> dict:
    return next(q for q in GOLD["questions"] if q["id"] == qid)


def test_thin_baseline_fails_source_read_requirement() -> None:
    q = _question("vague_talk")
    scored = score_trial(
        gold=GOLD,
        question=q,
        answer=(
            "The Grotesque Tree is a GM-facing threat in the garden site "
            "The Grotesque Tree (garden), located in Jove Home. It threatens Hempholm."
        ),
        tool_events=[
            {"tool_name": "expand_graph_retrieval"},
            {"tool_name": "expand_graph_retrieval"},
            {"tool_name": "expand_graph_retrieval"},
            {"tool_name": "expand_graph_retrieval"},
        ],
        result={
            "acceptance": {
                "accepted_claim_ids": [
                    "identity:threat:grotesque-tree",
                    "identity:location:grotesque-tree-site",
                    "edge:threat:grotesque-tree:threatens:location:hempholm",
                    "edge:location:grotesque-tree-site:located_in:location:jove-home",
                ],
                "source_citations_opened": 0,
            },
            "mutations": [],
        },
    )
    assert scored["source_reads"] == 0
    assert scored["source_ok"] is False
    assert scored["structural_pass"] is False
    assert scored["expands"] == 4


def test_rich_source_open_pass_structural() -> None:
    q = _question("vague_talk")
    scored = score_trial(
        gold=GOLD,
        question=q,
        answer=(
            "The Grotesque Tree grew from an enchanted conk — a Baldur's Gate mages' guild "
            "field test. In the Jove garden at Hempholm it looks stranger up close: "
            "bark like armor and thorned branches. Passive Perception 15 notices metal leaves; "
            "Passive Arcana 12 feels an aura; DC 17 Arcana finds roots under the village. "
            "It attacks within 30 feet, targets the nearest foe, and ceases when safe. "
            "Search yields about 100 gp in precious metal leaves."
        ),
        tool_events=[
            {"tool_name": "expand_graph_retrieval"},
            {"tool_name": "read_graph_source"},
        ],
        result={
            "acceptance": {
                "accepted_claim_ids": [
                    "identity:threat:grotesque-tree",
                    "identity:location:grotesque-tree-site",
                ],
                "source_citations_opened": 1,
            },
            "mutations": [],
        },
    )
    assert scored["source_ok"] is True
    assert scored["structural_pass"] is True
    assert scored["required_bucket_pass"] is True, scored["bucket_scores"]
    assert scored["expand_ready_candidate"] is True


def test_authoring_rejects_metal_leaves_read_aloud() -> None:
    q = _question("authoring_gm_note")
    scored = score_trial(
        gold=GOLD,
        question=q,
        answer="Draft note with bark, thorns, 30 feet tactics, Perception 15 leaves, 100 gp.",
        tool_events=[{"tool_name": "read_graph_source"}, {"tool_name": "propose_canvas_block"}],
        result={
            "acceptance": {
                "accepted_claim_ids": ["identity:threat:grotesque-tree", "identity:location:grotesque-tree-site"],
                "source_citations_opened": 1,
            },
            "mutations": [
                {
                    "schema": "dmb_canvas_block_proposal_v1",
                    "kind": "read-aloud",
                    "markdown": "You notice shiny metal leaves on the branches.",
                    "provenanceRefs": ["threat:grotesque-tree"],
                }
            ],
        },
    )
    assert scored["gate_hygiene_ok"] is False
    assert scored["structural_pass"] is False


def test_authoring_gm_note_proposal_passes() -> None:
    q = _question("authoring_gm_note")
    scored = score_trial(
        gold=GOLD,
        question=q,
        answer=(
            "GM note: Jove garden tree — bark like armor, thorns. Gates: Perception 15 "
            "metal leaves (do not boxed-text), Arcana 12/17 roots. Tactics 30 ft nearest. "
            "Treasure ~100 gp leaves on search. Chips: grotesque tree, site, Jove, Hempholm."
        ),
        tool_events=[
            {"tool_name": "expand_graph_retrieval"},
            {"tool_name": "read_graph_source"},
            {"tool_name": "propose_canvas_block"},
        ],
        result={
            "acceptance": {
                "accepted_claim_ids": [
                    "identity:threat:grotesque-tree",
                    "identity:location:grotesque-tree-site",
                ],
                "source_citations_opened": 1,
            },
            "mutations": [
                {
                    "schema": "dmb_canvas_block_proposal_v1",
                    "kind": "gm-note",
                    "markdown": (
                        "Closer = stranger; bark like armor; thorns. Passive Perception 15: "
                        "metal leaves. Passive Arcana 12 aura; DC 17 roots. Attacks within 30 ft. "
                        "Treasure ~100 gp metal leaves."
                    ),
                    "provenanceRefs": [
                        "threat:grotesque-tree",
                        "location:grotesque-tree-site",
                    ],
                }
            ],
        },
    )
    assert scored["canvas_ok"] is True
    assert scored["gate_hygiene_ok"] is True
    assert scored["structural_pass"] is True


def test_identity_control_does_not_require_source_read() -> None:
    q = _question("identity_only_control")
    scored = score_trial(
        gold=GOLD,
        question=q,
        answer="The Grotesque Tree threatens Hempholm.",
        tool_events=[{"tool_name": "expand_graph_retrieval"}],
        result={
            "acceptance": {
                "accepted_claim_ids": [
                    "identity:threat:grotesque-tree",
                    "edge:threat:grotesque-tree:threatens:location:hempholm",
                ],
                "source_citations_opened": 0,
            },
            "mutations": [],
        },
    )
    assert scored["source_read_required"] is False
    assert scored["source_ok"] is True


def test_aggregate_threshold() -> None:
    trials = [
        {"structural_pass": True, "required_bucket_pass": True, "expand_ready_candidate": True},
        {"structural_pass": True, "required_bucket_pass": False, "expand_ready_candidate": False},
        {"structural_pass": False, "required_bucket_pass": False, "expand_ready_candidate": False},
    ]
    agg = aggregate_question_trials(trials, threshold_pass=2)
    assert agg["structural_ok"] is True
    assert agg["expand_ready_ok"] is False
