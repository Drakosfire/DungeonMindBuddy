from __future__ import annotations

from pathlib import Path

from evals.npc_corpus_recall_audit.npc_corpus_recall_audit import (
    build_npc_corpus_recall_audit_report,
)


def _row(report: dict, npc_id: str) -> dict:
    for row in report.get("rows") or []:
        if str(row.get("npc_id") or "") == npc_id:
            return row
    raise AssertionError(f"npc_id not found in report rows: {npc_id}")


def test_npc_corpus_recall_audit_baseline_shape() -> None:
    repo = Path(__file__).resolve().parents[1]
    report = build_npc_corpus_recall_audit_report(repo_root=repo)
    assert report["schema"] == "dmb_npc_corpus_recall_audit_v2"
    assert report["offline_stub"] is True
    assert report["scenario_estimated_cost_usd"] == 0.0
    agg = report.get("aggregates") or {}
    assert agg.get("targets_total") == 13
    assert agg.get("targets_with_any_hub", 0) >= 1
    assert agg.get("targets_with_mentions_in_scope") == 13
    assert isinstance(agg.get("contract_violation_counts"), dict)


def test_key_rows_capture_world_campaign_gap() -> None:
    repo = Path(__file__).resolve().parents[1]
    report = build_npc_corpus_recall_audit_report(repo_root=repo)

    kirfan = _row(report, "kirfan")
    assert kirfan["has_any_hub"] is True
    assert kirfan["has_world_hub"] is True
    assert kirfan["has_campaign_hub"] is True
    assert kirfan["has_divergence_mode"] is True
    # Registry parent-link wiring remains incomplete; scaffolded hubs are discoverable.
    assert kirfan["has_world_parent_link"] is False
    assert kirfan["readiness_tier"] == "campaign_hub_no_world_link"

    lysandra = _row(report, "captain_lysandra_ironveil")
    assert lysandra["has_any_hub"] is True
    assert lysandra["has_world_hub"] is True
    assert lysandra["has_campaign_hub"] is True
    assert lysandra["has_world_parent_link"] is True
    assert lysandra["has_statblock"] is True

    pippa = _row(report, "pippa")
    assert pippa["has_campaign_hub"] is True
    assert pippa["has_world_parent_link"] is False
    assert pippa["has_statblock"] is False
    assert "campaign_hub_missing_world_parent_link" in (pippa.get("contract_violations") or [])
    assert "campaign_hub_missing_divergence_mode" in (pippa.get("contract_violations") or [])
