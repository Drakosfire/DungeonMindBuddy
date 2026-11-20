from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import sys

import pytest

from evals.npc_corpus_recall_audit.npc_corpus_recall_audit import (
    build_npc_corpus_recall_audit_report,
)


def _row(report: dict, npc_id: str) -> dict:
    for row in report.get("rows") or []:
        if str(row.get("npc_id") or "") == npc_id:
            return row
    raise AssertionError(f"npc_id not found in report rows: {npc_id}")


def _isolated_cli(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[1] / "evals/npc_corpus_recall_audit/npc_corpus_recall_audit.py"
    script = tmp_path / "checkout/evals/npc_corpus_recall_audit/npc_corpus_recall_audit.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(source, script)
    return script


@pytest.mark.parametrize("no_update", [False, True])
def test_cli_external_output_controls_existing_mirror(tmp_path: Path, no_update: bool) -> None:
    script = _isolated_cli(tmp_path)
    mirror = script.parent / "artifacts/last_npc_corpus_recall_audit.json"
    mirror.parent.mkdir()
    mirror.write_text("retained historical bytes", encoding="utf-8")
    before = (mirror.read_bytes(), mirror.stat().st_mtime_ns)
    output = tmp_path / "external/report.json"
    command = [sys.executable, str(script), "--output", str(output)]
    if no_update:
        command.append("--no-update-latest")
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    receipt = json.loads(result.stdout)
    assert json.loads(output.read_text())["schema"] == "dmb_npc_corpus_recall_audit_v2"
    if no_update:
        assert (mirror.read_bytes(), mirror.stat().st_mtime_ns) == before
        assert receipt["mirror"] is None
    else:
        assert mirror.read_bytes() == output.read_bytes()
        assert receipt["mirror"] == str(mirror)
    assert list(mirror.parent.iterdir()) == [mirror]


def test_cli_no_update_does_not_create_checkout_artifacts(tmp_path: Path) -> None:
    script = _isolated_cli(tmp_path)
    output = tmp_path / "external/report.json"
    result = subprocess.run(
        [sys.executable, str(script), "--output", str(output), "--no-update-latest"],
        capture_output=True, text=True, check=True,
    )
    assert output.is_file()
    assert json.loads(result.stdout)["mirror"] is None
    assert not (script.parent / "artifacts").exists()


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
