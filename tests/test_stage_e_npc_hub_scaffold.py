from __future__ import annotations

import json
from pathlib import Path

from evals.stage_d_entity_resolution_vertical_slice.step2_stage_e_npc_hub_scaffold import (
    run_stage_e_scaffold,
)


def _write_payload(path: Path) -> Path:
    payload = {
        "schema": "stage_d_promotion_v2",
        "campaign_id": "longmont-c1",
        "branch_scaffold_proposals": [
            {
                "slug": "kirfan",
                "display_name": "Kirfan",
                "location_slug": "upriver_river_route",
                "divergence_mode": "inherit",
                "world_parent_hub_path": "Elderwyld/Cities and Towns/Upriver River Route/NPCs/kirfan/",
                "campaign_overlay_hub_path": "Longmont Campaign/Campaign 1/NPCs/kirfan/",
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_stage_e_scaffold_preview_only(tmp_path: Path) -> None:
    promotion = _write_payload(tmp_path / "promotion.json")
    report = run_stage_e_scaffold(
        promotion_json=promotion,
        corpus_root=tmp_path / "corpus",
        commit=False,
        out_dir=tmp_path / "out",
    )
    counts = report["counts"]
    assert counts["ops_total"] == 5
    assert counts["preview_ok"] == 5
    assert counts["committed"] == 0


def test_stage_e_scaffold_commit_writes_files(tmp_path: Path) -> None:
    promotion = _write_payload(tmp_path / "promotion.json")
    corpus = tmp_path / "corpus"
    report = run_stage_e_scaffold(
        promotion_json=promotion,
        corpus_root=corpus,
        commit=True,
        out_dir=tmp_path / "out",
    )
    counts = report["counts"]
    assert counts["committed"] == 5
    assert counts["commit_error"] == 0

    campaign_readme = (
        corpus / "Longmont Campaign/Campaign 1/NPCs/kirfan/README.md"
    ).read_text(encoding="utf-8")
    assert "divergence_mode: inherit" in campaign_readme
    assert "world_hub_path: Elderwyld/Cities and Towns/Upriver River Route/NPCs/kirfan/README.md" in campaign_readme
