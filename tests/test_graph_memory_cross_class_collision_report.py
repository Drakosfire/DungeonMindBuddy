from __future__ import annotations

from src.graph_memory.diagnostics.cross_class_collision_report import (
    render_blocked_collision_markdown,
    summarize_blocked_collision_records,
)


def _direct_payload():
    return {
        "consolidation_diagnostics": {
            "cross_class_blocked_nodes": [
                {
                    "label": "stone bridge",
                    "node_ids": ["node:place:stone-bridge", "node:object:stone-bridge"],
                    "classes": ["object", "place"],
                    "reason": "unsafe_cross_class_exact_label",
                }
            ]
        },
        "nodes": [
            {"node_id": "node:place:stone-bridge", "label": "Stone Bridge", "node_type": "location"},
            {"node_id": "node:object:stone-bridge", "label": "Stone Bridge", "node_type": "item"},
        ],
    }


def test_extracts_direct_blocked_diagnostics():
    records = summarize_blocked_collision_records(bed_id="bed", variant="baseline", extraction_payload=_direct_payload())

    assert len(records) == 1
    record = records[0]
    assert record.label == "stone bridge"
    assert record.classes == ("object", "place")
    assert set(record.node_ids) == {"node:place:stone-bridge", "node:object:stone-bridge"}
    assert len(record.nodes) == 2


def test_extracts_nested_ablation_diagnostics():
    payload = {
        "extraction_run_diagnostics": {
            "consolidation_diagnostics": {
                "cross_class_blocked_nodes": [
                    {
                        "label": "river s edge pub",
                        "node_ids": ["loc_pub", "item_pub"],
                        "classes": ["object", "place"],
                        "reason": "unsafe_cross_class_exact_label",
                    }
                ]
            }
        },
        "extracted_nodes": [
            {"node_id": "loc_pub", "label": "River's Edge Pub", "node_type": "location"},
            {"node_id": "item_pub", "label": "River's Edge Pub", "node_type": "item"},
        ],
    }

    records = summarize_blocked_collision_records(bed_id="bed", variant="edge_packet", extraction_payload=payload)

    assert len(records) == 1
    assert records[0].label == "river s edge pub"
    assert len(records[0].nodes) == 2


def test_no_blocked_diagnostics_returns_empty_list():
    assert summarize_blocked_collision_records(bed_id="bed", variant="baseline", extraction_payload={"nodes": []}) == []


def test_markdown_renderer_is_deterministic():
    records = summarize_blocked_collision_records(bed_id="bed", variant="baseline", extraction_payload=_direct_payload())

    first = render_blocked_collision_markdown(records, generated_date="2026-07-01")
    second = render_blocked_collision_markdown(records, generated_date="2026-07-01")

    assert first == second


def test_report_includes_human_review_columns():
    markdown = render_blocked_collision_markdown([], generated_date="2026-07-01")

    assert "| Bed | Variant | Label | Classes | Node IDs | Suggested review action | Human decision | Notes |" in markdown


def test_actor_collisions_are_conservative():
    payload = {
        "cross_class_blocked_nodes": [
            {
                "label": "troupe of gnomes",
                "node_ids": ["npc_gnomes", "group_gnomes"],
                "classes": ["actor", "collective"],
                "reason": "unsafe_cross_class_exact_label",
            }
        ],
        "nodes": [
            {"node_id": "npc_gnomes", "label": "Troupe of Gnomes", "node_type": "npc"},
            {"node_id": "group_gnomes", "label": "Troupe of Gnomes", "node_type": "group"},
        ],
    }

    records = summarize_blocked_collision_records(bed_id="bed", variant="node_packet", extraction_payload=payload)

    assert records[0].suggested_review_action == "candidate_keep_blocked"


def test_missing_node_details_do_not_crash():
    payload = {
        "cross_class_blocked_nodes": [
            {
                "label": "stone bridge",
                "node_ids": ["missing-a", "missing-b"],
                "classes": ["object", "place"],
                "reason": "unsafe_cross_class_exact_label",
            }
        ]
    }

    records = summarize_blocked_collision_records(bed_id="bed", variant="baseline", extraction_payload=payload)
    markdown = render_blocked_collision_markdown(records, generated_date="2026-07-01")

    assert len(records) == 1
    assert records[0].nodes == ()
    assert "stone bridge" in markdown


def test_no_source_quotes_leak():
    payload = _direct_payload()
    payload["nodes"][0]["description"] = "A long raw source quote that should not appear in the markdown review table."
    payload["nodes"][0]["evidence_refs"] = [{"quote": "verbatim quote should not leak"}]

    records = summarize_blocked_collision_records(bed_id="bed", variant="baseline", extraction_payload=payload)
    markdown = render_blocked_collision_markdown(records, generated_date="2026-07-01")

    assert "verbatim quote should not leak" not in markdown
    assert "A long raw source quote" not in markdown
