"""Offline tests for Stage A prompt-context assembly helpers."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.session_events_extraction_vertical_slice.step1_session_events_run import (
    build_user_prompt,
    discover_campaign_pc_hub_dirs,
    load_pc_identity_hints,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discover_campaign_pc_hub_dirs_prefers_same_campaign(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _write(
        corpus_root / "Longmont Campaign/Campaign 1/PCs/c1_only/README.md",
        "---\ntitle: c1 only\n---\n",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/c2_a/README.md",
        "---\ntitle: c2 a\n---\n",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/c2_b/README.md",
        "---\ntitle: c2 b\n---\n",
    )

    hubs = discover_campaign_pc_hub_dirs(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
    )
    names = [p.name for p in hubs]
    assert names == ["c2_a", "c2_b"]


def test_discover_campaign_pc_hub_dirs_falls_back_when_target_missing(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _write(
        corpus_root / "Longmont Campaign/Campaign 1/PCs/c1_only/README.md",
        "---\ntitle: c1 only\n---\n",
    )

    hubs = discover_campaign_pc_hub_dirs(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 99 - Recap.md",
    )
    assert [p.name for p in hubs] == ["c1_only"]


def test_load_pc_identity_hints_filters_to_known_character_slugs(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/caelynn/caelynn_character_dossier.md",
        """---
title: "Caelynn dossier"
campaign_id: longmont-c2
---

# Caelynn

**Caelynn** is a storm-flavored mage.

| Field | Detail |
|------|--------|
| **Species / class (corpus tokens)** | **Half Elf** **Sorcerer** |
""",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
        """---
title: "Caelynn timeline"
---

| Session | Beat (1-3 lines) | Recap / prep |
|--------|------------------|--------------|
| **Backstory** | Learned to channel storm magic in youth. | `Longmont Campaign/Campaign 2/Campaign 2 Notes.md` |
""",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/bonogo/bonogo_character_dossier.md",
        """---
title: "Bonogo dossier"
---

# Bonogo

**Bonogo** is a rogue.
""",
    )

    user_message = (
        "Extract session events.\n\n"
        "Known character slugs: caelynn, captain_lysandra_ironveil"
    )
    hints = load_pc_identity_hints(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        user_message,
    )
    assert "caelynn" in hints
    assert "Half Elf Sorcerer" in hints
    assert "Backstory: Learned to channel storm magic in youth." in hints
    assert "bonogo" not in hints


def test_load_pc_identity_hints_noop_when_hubs_absent(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    hints = load_pc_identity_hints(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        "Known character slugs: caelynn",
    )
    assert hints == ""


def test_build_user_prompt_includes_fallback_guardrails_when_hints_present() -> None:
    msg = build_user_prompt(
        "Extract events",
        "Recap body here",
        "- caelynn: species/class=Half Elf Sorcerer",
    )
    assert "PC IDENTITY HINTS (fallback anchors)" in msg
    assert "Never let hints override explicit recap facts" in msg
    assert "- caelynn: species/class=Half Elf Sorcerer" in msg


def test_build_user_prompt_omits_hint_block_when_empty() -> None:
    msg = build_user_prompt("Extract events", "Recap body here", "")
    assert "PC IDENTITY HINTS (fallback anchors)" not in msg
