"""Reconciliation tests for anchor-quote contract on live candidate graphs."""

from __future__ import annotations

import pytest

from evals.graph_memory_layer.category_graph_model_study import (
    assemble_envelope,
    consolidate_category_outputs,
    ensure_s22_run_bundle,
    s22_run_bundle_dir,
)
from evals.graph_memory_layer.reconcile_live_candidate import (
    ReconcileError,
    validate_live_candidate_output,
)


def _minimal_consolidated(actor_nodes=None, thread_nodes=None):
    base = {
        "actor_pass": {"observation_nodes": actor_nodes or []},
        "location_pass": {"observation_nodes": []},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": thread_nodes or [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {"observation_beats": []},
        "edge_pass": {"observation_edges": []},
    }
    return consolidate_category_outputs(base, session=22)


@pytest.fixture(scope="module")
def s22_bundle():
    ensure_s22_run_bundle(allow_overwrite=True)
    return s22_run_bundle_dir()


def test_valid_anchor_quote_resolves_to_matches(s22_bundle):
    consolidated = _minimal_consolidated(
        thread_nodes=[
            {
                "node_id": "clue:puddles",
                "label": "Delayed puddle reflections",
                "node_type": "clue",
                "description": "odd water",
                "importance": "high",
                "evidence_refs": [
                    {
                        "source_span_ref_id": "spref:session-22:p004",
                        "anchor_quotes": ["the reflections are somewhat delayed"],
                    }
                ],
            }
        ],
    )
    envelope = assemble_envelope(consolidated)
    report = validate_live_candidate_output(
        envelope,
        run_bundle=s22_bundle,
        allowed_span_refs={"spref:session-22:p004"},
    )
    node = report["reconciled_candidate_graph"]["nodes"][0]
    ev = node["evidence_refs"][0]
    assert ev["source_span_ref_id"] == "spref:session-22:p004"
    assert ev["anchor_quotes"] == ["the reflections are somewhat delayed"]
    assert ev["anchor_quote_matches"]
    assert ev["anchor_quote_matches"][0]["match_text"]


def test_invalid_anchor_quote_fails_reconciliation(s22_bundle):
    consolidated = _minimal_consolidated(
        thread_nodes=[
            {
                "node_id": "clue:bad",
                "label": "bogus",
                "node_type": "clue",
                "description": "x",
                "importance": "low",
                "evidence_refs": [
                    {
                        "source_span_ref_id": "spref:session-22:p007",
                        "anchor_quotes": ["this phrase is not in the paragraph at all"],
                    }
                ],
            }
        ],
    )
    envelope = assemble_envelope(consolidated)
    with pytest.raises(ReconcileError, match="invalid_anchor_quote:not_in_paragraph"):
        validate_live_candidate_output(
            envelope,
            run_bundle=s22_bundle,
            allowed_span_refs={"spref:session-22:p007"},
        )


def test_label_fallback_when_anchor_quotes_omitted(s22_bundle):
    consolidated = _minimal_consolidated(
        actor_nodes=[
            {
                "node_id": "npc:grobnok",
                "label": "Grobnok",
                "node_type": "character",
                "description": "operator",
                "importance": "high",
                "evidence_refs": [{"source_span_ref_id": "spref:session-22:p012"}],
            }
        ],
    )
    envelope = assemble_envelope(consolidated)
    report = validate_live_candidate_output(
        envelope,
        run_bundle=s22_bundle,
        allowed_span_refs={"spref:session-22:p012"},
    )
    node = report["reconciled_candidate_graph"]["nodes"][0]
    ev = node["evidence_refs"][0]
    assert "anchor_quotes" not in ev or not ev.get("anchor_quotes")
    assert ev.get("anchor_quote_matches")
    assert "Grobnok" in ev["anchor_quote_matches"][0]["match_text"]


def test_quote_in_wrong_paragraph_fails_even_if_elsewhere_in_recap(s22_bundle):
    consolidated = _minimal_consolidated(
        thread_nodes=[
            {
                "node_id": "clue:cross",
                "label": "cross paragraph",
                "node_type": "clue",
                "description": "x",
                "importance": "low",
                "evidence_refs": [
                    {
                        "source_span_ref_id": "spref:session-22:p001",
                        "anchor_quotes": ["the reflections are somewhat delayed"],
                    }
                ],
            }
        ],
    )
    envelope = assemble_envelope(consolidated)
    with pytest.raises(ReconcileError, match="invalid_anchor_quote:not_in_paragraph"):
        validate_live_candidate_output(
            envelope,
            run_bundle=s22_bundle,
            allowed_span_refs={"spref:session-22:p001"},
        )
