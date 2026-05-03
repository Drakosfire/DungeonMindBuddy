"""Tests for NPC-first attachment context (Stage B experiment scaffolding)."""

from __future__ import annotations

import pytest

from evals.sentence_routing_retrieval_falsification.discourse_prompt import (
    DISCOURSE_PROMPT_BASE_ID,
    build_discourse_system_prompt,
)
from evals.sentence_routing_retrieval_falsification.npc_first_context import (
    SCHEMA_NPC_ATTACHMENT_CONTEXT_V1,
    build_npc_attachment_context_sidecar,
    enrich_sentence_units_with_npc_attachment_context,
    load_npc_timeline_alignment_sets,
    normalize_eldyrwild_recap_suffix,
    ranges_overlap_1based,
)


def test_normalize_eldyrwild_recap_suffix_strips_prefix() -> None:
    long_p = "corpus/eldyrwild-markdown/Longmont Campaign/x.md"
    short_p = "Longmont Campaign/x.md"
    assert normalize_eldyrwild_recap_suffix(long_p) == short_p
    assert normalize_eldyrwild_recap_suffix(short_p) == short_p


def test_ranges_overlap_1based() -> None:
    assert ranges_overlap_1based(1, 3, 3, 5)
    assert not ranges_overlap_1based(1, 2, 3, 4)


def test_build_sidecar_maps_event_span_to_units_excluding_manifest_pcs() -> None:
    units = [
        {"unit_id": "u-hit", "path": "Longmont Campaign/Recap.md", "line_start": 5, "line_end": 5},
        {"unit_id": "u-miss", "path": "Longmont Campaign/Recap.md", "line_start": 99, "line_end": 99},
    ]
    events = [
        {
            "participants": ["npc_mayor", "pc_alice"],
            "referenced_slugs": ["npc_ref"],
            "source_anchors": [
                {"path": "Longmont Campaign/Recap.md", "line_start": 4, "line_end": 6},
            ],
        }
    ]
    manifest = [
        {"slug": "pc_alice", "subject_class": "pc", "path": "a.md"},
    ]
    gold = {
        "expected_appends": [
            {
                "npc_slug": "npc_mayor",
                "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/npc_mayor/timeline.md",
            }
        ],
        "expected_skips": [
            {
                "npc_slug": "npc_ref",
                "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/npc_ref/timeline.md",
            }
        ],
    }
    sidecar = build_npc_attachment_context_sidecar(
        scenario_id="t",
        units_json=units,
        parsed_events=events,
        manifest_jsonable=manifest,
        timeline_grading=gold,
    )
    assert sidecar["schema"] == SCHEMA_NPC_ATTACHMENT_CONTEXT_V1
    assert set(sidecar["by_unit_id"].keys()) == {"u-hit"}
    row = sidecar["by_unit_id"]["u-hit"]
    assert set(row["npc_slugs"]) == {"npc_mayor", "npc_ref"}
    assert row["per_npc_attachment"]["npc_mayor"] == "append"
    assert row["per_npc_attachment"]["npc_ref"] == "skip_incidental"


def test_path_prefix_mismatch_resolved_by_normalize() -> None:
    units = [
        {
            "unit_id": "u1",
            "path": "corpus/eldyrwild-markdown/Longmont Campaign/Recap.md",
            "line_start": 2,
            "line_end": 2,
        }
    ]
    events = [
        {
            "participants": ["ghost_npc"],
            "source_anchors": [{"path": "Longmont Campaign/Recap.md", "line_start": 2, "line_end": 2}],
        }
    ]
    sidecar = build_npc_attachment_context_sidecar(
        scenario_id="t",
        units_json=units,
        parsed_events=events,
        manifest_jsonable=[],
        timeline_grading=None,
    )
    assert "u1" in sidecar["by_unit_id"]


def test_enrich_merges_only_units_present_in_by_unit_id() -> None:
    units = [
        {"unit_id": "a", "path": "x.md", "line_start": 1, "line_end": 1},
        {"unit_id": "b", "path": "x.md", "line_start": 2, "line_end": 2},
    ]
    sidecar = {
        "schema": SCHEMA_NPC_ATTACHMENT_CONTEXT_V1,
        "scenario_id": "t",
        "by_unit_id": {
            "a": {
                "npc_slugs": ["z"],
                "per_npc_attachment": {"z": "unknown"},
                "npc_attachment_summary": "npc_timeline_disposition_partial_or_unknown",
                "pc_routing_instruction": "test",
            }
        },
    }
    out, stats = enrich_sentence_units_with_npc_attachment_context(units, sidecar)
    assert stats["units_enriched"] == 1
    assert out[0]["routing_context"]["npc_first_context"]["npc_slugs"] == ["z"]
    assert "routing_context" not in out[1]


def test_discourse_prompt_variant_npc_first() -> None:
    base_text, base_id = build_discourse_system_prompt(None)
    assert base_id == DISCOURSE_PROMPT_BASE_ID
    v_text, v_id = build_discourse_system_prompt("npc_first_context_v1")
    assert "npc_first_context_v1" in v_text
    assert "annotated, not erased" in v_text
    assert v_id != base_id


def test_discourse_prompt_unknown_variant_raises() -> None:
    with pytest.raises(ValueError, match="unknown discourse prompt_variant"):
        build_discourse_system_prompt("not_a_real_variant")


def test_load_npc_timeline_alignment_filters_pc_paths() -> None:
    g = {
        "expected_appends": [
            {
                "npc_slug": "caelynn",
                "timeline_relative_path": "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
            },
            {
                "npc_slug": "dustwalker",
                "timeline_relative_path": "Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md",
            },
        ],
        "expected_skips": [],
    }
    app, skip = load_npc_timeline_alignment_sets(g)
    assert app == {"dustwalker"}
    assert skip == set()
