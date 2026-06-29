"""Shared helpers for category graph extraction tests."""
from __future__ import annotations

from typing import Any


def minimal_category_pass_outputs(
    spref: str = "session-24:recap:paragraph:001",
    *,
    node_label: str = "Bonogo",
    node_id: str = "node:bonogo",
) -> dict[str, dict[str, Any]]:
    node = {
        "node_id": node_id,
        "label": node_label,
        "node_type": "character",
        "description": "test entity",
        "importance": "high",
        "evidence_refs": [
            {
                "source_span_ref_id": spref,
                "anchor_quotes": [node_label],
            }
        ],
    }
    empty_nodes = {"observation_nodes": []}
    return {
        "actor_pass": {"observation_nodes": [node]},
        "location_pass": empty_nodes,
        "collective_pass": empty_nodes,
        "object_pass": empty_nodes,
        "thread_pass": {
            "observation_nodes": [],
            "ignored_items": [],
            "deferred_items": [],
        },
        "beat_pass": {
            "observation_beats": [
                {
                    "beat_id": "beat:1",
                    "order": 1,
                    "title": "Scout",
                    "summary": f"{node_label} scouts the road.",
                    "involved_node_ids": [node_id],
                    "evidence_refs": [
                        {
                            "source_span_ref_id": spref,
                            "anchor_quotes": ["scouts"],
                        }
                    ],
                }
            ]
        },
        "edge_pass": {"observation_edges": []},
    }


def canonical_candidate_graph_from_passes(
    spref: str = "session-24:recap:paragraph:001",
) -> dict[str, Any]:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        FixtureCategoryGraphPassClient,
        run_category_pipeline,
    )

    span_index = {
        "spans": [
            {
                "kind": "paragraph",
                "span_id": spref,
                "source_span_ref_id": spref,
                "line_start": 1,
                "line_end": 3,
                "text": "Bonogo scouts the Mireward road and regroups at dusk.",
            }
        ]
    }
    result = run_category_pipeline(
        FixtureCategoryGraphPassClient(minimal_category_pass_outputs(spref)),
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c2",
            session_id="session-24",
            session_number=24,
            source_span_index=span_index,
            model_id="gpt-5.4-mini",
        ),
    )
    return result.candidate_graph
