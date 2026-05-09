"""Dispatch tests for list_npc_hubs / list_pc_hubs (read-only corpus discovery)."""

from __future__ import annotations

import json
from pathlib import Path

from src.agent.planner import build_corpus_path_ref_index, make_tool_dispatcher


def test_list_npc_hubs_returns_child_slugs(tmp_path: Path) -> None:
    npc = tmp_path / "Longmont Campaign" / "Campaign 2" / "NPCs"
    (npc / "alpha_slug").mkdir(parents=True)
    (npc / "alpha_slug" / "timeline.md").write_text("# t\n", encoding="utf-8")
    (npc / "beta_slug" / "README.md").parent.mkdir(parents=True)
    (npc / "beta_slug" / "README.md").write_text("# r\n", encoding="utf-8")

    idx = build_corpus_path_ref_index(tmp_path)
    dispatch = make_tool_dispatcher(tmp_path, object(), "gpt-mock", corpus_path_ref_index=idx)
    raw = dispatch(
        "list_npc_hubs",
        json.dumps({"npcs_root": "Longmont Campaign/Campaign 2/NPCs"}),
    )
    data = json.loads(raw)
    assert data.get("ok") is True
    assert data.get("subject_class") == "npc"
    assert data.get("hub_count") == 2
    slugs = {h["slug"] for h in data.get("hubs", [])}
    assert slugs == {"alpha_slug", "beta_slug"}
    by = {h["slug"]: h for h in data["hubs"]}
    assert by["alpha_slug"]["has_timeline_md"] is True
    assert by["beta_slug"]["has_timeline_md"] is False


def test_list_pc_hubs_requires_pc_suffix(tmp_path: Path) -> None:
    npc = tmp_path / "Longmont Campaign" / "Campaign 2" / "NPCs"
    npc.mkdir(parents=True)
    idx = build_corpus_path_ref_index(tmp_path)
    dispatch = make_tool_dispatcher(tmp_path, object(), "gpt-mock", corpus_path_ref_index=idx)
    raw = dispatch(
        "list_pc_hubs",
        json.dumps({"pcs_root": "Longmont Campaign/Campaign 2/NPCs"}),
    )
    data = json.loads(raw)
    assert data.get("ok") is False


def test_list_npc_hubs_rejects_dotdot(tmp_path: Path) -> None:
    idx = build_corpus_path_ref_index(tmp_path)
    dispatch = make_tool_dispatcher(tmp_path, object(), "gpt-mock", corpus_path_ref_index=idx)
    raw = dispatch("list_npc_hubs", json.dumps({"npcs_root": "../Longmont Campaign/Campaign 2/NPCs"}))
    data = json.loads(raw)
    assert data.get("ok") is False


def test_recall_npc_context_returns_hub_bundle(tmp_path: Path) -> None:
    c1 = tmp_path / "Longmont Campaign" / "Campaign 1"
    hub = c1 / "NPCs" / "bubbles_the_float_goat"
    hub.mkdir(parents=True)
    (c1 / "_npc_registry.json").write_text(
        json.dumps(
            [
                {
                    "slug": "bubbles_the_float_goat",
                    "display_name": "Bubbles the Float Goat",
                    "aliases": ["Bubbles"],
                    "status": "tracked",
                    "hub_path": "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/",
                }
            ]
        ),
        encoding="utf-8",
    )
    (hub / "README.md").write_text("# Bubbles\n", encoding="utf-8")
    (hub / "bubbles_the_float_goat_character_dossier.md").write_text(
        "water-walking pack goat\n", encoding="utf-8"
    )
    (hub / "timeline.md").write_text("flood rescue\n", encoding="utf-8")
    idx = build_corpus_path_ref_index(tmp_path)
    dispatch = make_tool_dispatcher(tmp_path, object(), "gpt-mock", corpus_path_ref_index=idx)

    raw = dispatch(
        "recall_npc_context",
        json.dumps({"campaign_id": "longmont-c1", "npc": "Bubbles"}),
    )
    data = json.loads(raw)

    assert data["ok"] is True
    assert data["record"]["slug"] == "bubbles_the_float_goat"
    assert data["hub_path"] == "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat"
    assert [f["path"] for f in data["context_files"]] == [
        "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/README.md",
        "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/bubbles_the_float_goat_character_dossier.md",
        "Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/timeline.md",
    ]


def test_recall_npc_context_reports_missing_registry_match(tmp_path: Path) -> None:
    c1 = tmp_path / "Longmont Campaign" / "Campaign 1"
    c1.mkdir(parents=True)
    (c1 / "_npc_registry.json").write_text("[]", encoding="utf-8")
    dispatch = make_tool_dispatcher(tmp_path, object(), "gpt-mock", corpus_path_ref_index={})

    raw = dispatch("recall_npc_context", json.dumps({"campaign_id": "longmont-c1", "npc": "Pippa"}))
    data = json.loads(raw)

    assert data["ok"] is False
    assert "no matching NPC registry record" in data["error"]
