from __future__ import annotations

from src.contracts.temporal_tick_gate import (
    campaign_temporal_quality_summary,
    campaign_temporal_consistency_violations,
    campaign_temporal_tick_violations,
)


def _unit(eid: str, *, layer: str, campaign_id: str | None = None) -> dict:
    return {
        "evidence_id": eid,
        "canon_layer": layer,
        "campaign_id": campaign_id,
    }


def _fact(fid: str, eid: str, *, sess: int | None, seq: int | None) -> dict:
    return {
        "fact_id": fid,
        "evidence_ids": [eid],
        "asserted_in_session": sess,
        "sequence_index_within_session": seq,
    }


def test_world_sourced_fact_may_have_null_tick() -> None:
    ev = [_unit("e1", layer="world")]
    facts = [_fact("f1", "e1", sess=None, seq=None)]
    assert campaign_temporal_tick_violations(ev, facts) == []


def test_campaign_fact_requires_session_or_sequence() -> None:
    ev = [_unit("e1", layer="campaign", campaign_id="c1")]
    facts = [_fact("f1", "e1", sess=None, seq=None)]
    errs = campaign_temporal_tick_violations(ev, facts)
    assert len(errs) == 1
    assert "f1" in errs[0]
    assert "narrative tick" in errs[0]


def test_campaign_fact_passes_with_session_only() -> None:
    ev = [_unit("e1", layer="campaign", campaign_id="c1")]
    facts = [_fact("f1", "e1", sess=6, seq=None)]
    assert campaign_temporal_tick_violations(ev, facts) == []


def test_campaign_fact_passes_with_sequence_only() -> None:
    ev = [_unit("e1", layer="campaign", campaign_id="c1")]
    facts = [_fact("f1", "e1", sess=None, seq=3)]
    assert campaign_temporal_tick_violations(ev, facts) == []


def test_missing_evidence_id_surfaces_error() -> None:
    ev = [_unit("e1", layer="campaign", campaign_id="c1")]
    facts = [_fact("f1", "missing", sess=None, seq=None)]
    errs = campaign_temporal_tick_violations(ev, facts)
    assert any("not found" in e for e in errs)


def test_campaign_temporal_consistency_allows_single_evidence_session() -> None:
    ev = [
        {
            "evidence_id": "e1",
            "canon_layer": "campaign",
            "campaign_id": "c1",
            "document_session": 6,
            "inferred_session": None,
        }
    ]
    facts = [_fact("f1", "e1", sess=6, seq=1)]
    assert campaign_temporal_consistency_violations(ev, facts) == []


def test_campaign_temporal_consistency_rejects_mixed_evidence_sessions() -> None:
    ev = [
        {
            "evidence_id": "e1",
            "canon_layer": "campaign",
            "campaign_id": "c1",
            "document_session": 6,
            "inferred_session": None,
        },
        {
            "evidence_id": "e2",
            "canon_layer": "campaign",
            "campaign_id": "c1",
            "document_session": 7,
            "inferred_session": None,
        },
    ]
    facts = [
        {
            "fact_id": "f1",
            "evidence_ids": ["e1", "e2"],
            "asserted_in_session": 6,
            "sequence_index_within_session": 10,
        }
    ]
    errs = campaign_temporal_consistency_violations(ev, facts)
    assert any("conflicting sessions" in e for e in errs)


def test_campaign_temporal_consistency_rejects_asserted_session_mismatch() -> None:
    ev = [
        {
            "evidence_id": "e1",
            "canon_layer": "campaign",
            "campaign_id": "c1",
            "document_session": 8,
            "inferred_session": None,
        }
    ]
    facts = [_fact("f1", "e1", sess=3, seq=1)]
    errs = campaign_temporal_consistency_violations(ev, facts)
    assert any("does not match evidence sessions" in e for e in errs)


def test_campaign_temporal_quality_summary_flags_sequence_only() -> None:
    ev = [
        {
            "evidence_id": "e1",
            "canon_layer": "campaign",
            "campaign_id": "c1",
            "document_session": None,
            "inferred_session": None,
        }
    ]
    facts = [_fact("f1", "e1", sess=None, seq=2)]
    summary = campaign_temporal_quality_summary(ev, facts)
    assert summary["metrics"]["campaign_fact_count"] == 1
    assert summary["metrics"]["sequence_only_count"] == 1
    assert summary["metrics"]["sequence_only_ratio"] == 1.0
    assert summary["warnings"]
