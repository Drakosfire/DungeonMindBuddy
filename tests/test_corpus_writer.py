"""Tests for the guarded corpus writer (allowlist + two-phase commit + timeline helper)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.agent.corpus_writer import (
    append_timeline_row,
    is_writable_corpus_path,
    write_corpus_file,
)


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel_path,mode",
    [
        ("Longmont Campaign/Campaign 2/Session Recaps/Session 20 - First Snow.md", "create"),
        ("Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md", "append"),
        ("Longmont Campaign/Campaign 2/NPCs/dustwalker/README.md", "append"),
        (
            "Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/README.md",
            "create",
        ),
        (
            "Elderwyld/Cities and Towns/Mossford/NPCs/marla_brambleback/character_seed.md",
            "create",
        ),
        ("Elderwyld/Locations/tower_mossford_stub.md", "create"),
        ("Longmont Campaign/Campaign 2/NPCs/marla_brambleback/marla_brambleback_character_dossier.md", "create"),
        (
            "Longmont Campaign/Campaign 2/Session Prep/session_20_stacey_stuart_marla_reference.md",
            "append",
        ),
    ],
)
def test_allowlist_permits_recap_create_and_npc_appends(rel_path: str, mode: str) -> None:
    allowed, reason = is_writable_corpus_path(rel_path, mode)
    assert allowed, reason


# ---------------------------------------------------------------------------
# Timeline allowlist — structural symmetry between NPCs and PCs (Stage-2 v1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel_path",
    [
        "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/timeline.md",
        "Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md",
        "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
        "Longmont Campaign/Campaign 1/PCs/some_pc/timeline.md",
    ],
)
def test_timeline_allowlist_accepts_npc_and_pc_paths(rel_path: str) -> None:
    allowed, reason = is_writable_corpus_path(rel_path, "append")
    assert allowed, reason


@pytest.mark.parametrize(
    "rel_path",
    [
        # Wrong basename under an NPC/PC hub
        "Longmont Campaign/Campaign 2/NPCs/dustwalker/random_other_file.md",
        "Longmont Campaign/Campaign 2/PCs/caelynn/notes.md",
        # PC dossier-shaped file is not the timeline (deny-basenames branch)
        "Longmont Campaign/Campaign 2/PCs/caelynn/caelynn_character_dossier.md",
        # Recap path (different allowlist branch, append mode)
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        # Sibling folder names that look-alike but aren't NPCs/PCs
        "Longmont Campaign/Campaign 2/PC/caelynn/timeline.md",
        "Longmont Campaign/Campaign 2/NPC/dustwalker/timeline.md",
    ],
)
def test_timeline_allowlist_still_rejects_forbidden_paths(rel_path: str) -> None:
    allowed, reason = is_writable_corpus_path(rel_path, "append")
    assert not allowed, f"unexpectedly allowed: {rel_path} ({reason})"


def test_path_traversal_with_timeline_tail_still_rejected_by_resolver(tmp_path: Path) -> None:
    """Even if the allowlist regex matches the tail, ``..`` traversal must be refused."""
    out = write_corpus_file(
        tmp_path,
        path="Longmont Campaign/Campaign 2/../../escaped/NPCs/x/timeline.md",
        mode="append",
        content="| **20** | x | `r.md` |\n",
        dry_run=True,
    )
    assert out["ok"] is False


@pytest.mark.parametrize(
    "rel_path,mode",
    [
        ("Longmont Campaign/Campaign 2/NPCs/dustwalker/dustwalker_character_dossier.md", "append"),
        ("Longmont Campaign/Campaign 2/NPCs/dustwalker/character_seed.md", "append"),
        ("Longmont Campaign/Campaign 2/NPCs/dustwalker/dustwalker_statblock.md", "append"),
        (
            "Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md",
            "create",
        ),
        ("Longmont Campaign/Campaign 2/NPCs/dustwalker/character_seed.md", "create"),
    ],
)
def test_allowlist_blocks_dossier_seed_statblock(rel_path: str, mode: str) -> None:
    allowed, reason = is_writable_corpus_path(rel_path, mode)
    assert not allowed
    assert "read-only" in reason


def test_allowlist_permits_campaign_dossier_create_when_path_shaped() -> None:
    rel = "Longmont Campaign/Campaign 2/NPCs/dustwalker/dustwalker_character_dossier.md"
    allowed, reason = is_writable_corpus_path(rel, "create")
    assert allowed, reason


def test_allowlist_blocks_create_outside_session_recaps() -> None:
    allowed, reason = is_writable_corpus_path(
        "Longmont Campaign/Campaign 2/random/notes.md", "create"
    )
    assert not allowed
    assert "Session Recaps" in reason


def test_allowlist_blocks_append_for_random_md() -> None:
    allowed, reason = is_writable_corpus_path(
        "Longmont Campaign/Campaign 2/Notes.md", "append"
    )
    assert not allowed
    assert "NPCs" in reason or "Session Prep" in reason


def test_allowlist_blocks_unknown_mode() -> None:
    allowed, reason = is_writable_corpus_path(
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - x.md", "overwrite"
    )
    assert not allowed
    assert "mode" in reason


# ---------------------------------------------------------------------------
# Two-phase commit: create
# ---------------------------------------------------------------------------


def _make_recap_dir(corpus: Path, *, campaign: str = "Longmont Campaign/Campaign 2") -> Path:
    recap_dir = corpus / campaign / "Session Recaps"
    recap_dir.mkdir(parents=True, exist_ok=True)
    return recap_dir


def test_create_dry_run_returns_token_and_diff(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - First Snow.md"
    body = "---\ntitle: Session 20\n---\n# Session 20\n\nfoo.\n"

    preview = write_corpus_file(tmp_path, path=rel, mode="create", content=body, dry_run=True)
    assert preview["ok"] is True
    assert preview["phase"] == "preview"
    assert preview["path"] == rel
    assert isinstance(preview["confirm_token"], str) and len(preview["confirm_token"]) >= 16
    assert "+++ b/" in preview["diff"]
    assert "Session 20" in preview["diff"]
    assert not (tmp_path / rel).exists()


def test_create_commit_with_token_writes_file(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - First Snow.md"
    body = "# Session 20\n\nThe party rides north.\n"

    preview = write_corpus_file(tmp_path, path=rel, mode="create", content=body, dry_run=True)
    token = preview["confirm_token"]

    commit = write_corpus_file(
        tmp_path,
        path=rel,
        mode="create",
        content=body,
        dry_run=False,
        confirm_token=token,
    )
    assert commit["ok"] is True
    assert commit["phase"] == "committed"
    written = (tmp_path / rel).read_text(encoding="utf-8")
    assert written.startswith("# Session 20")
    assert "fingerprint_reminder" in commit


def test_commit_without_token_errors(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - x.md"
    out = write_corpus_file(
        tmp_path, path=rel, mode="create", content="hi\n", dry_run=False
    )
    assert out["ok"] is False
    assert "confirm_token" in out["error"]


def test_commit_with_wrong_token_errors(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - x.md"
    out = write_corpus_file(
        tmp_path,
        path=rel,
        mode="create",
        content="hi\n",
        dry_run=False,
        confirm_token="deadbeef" * 4,
    )
    assert out["ok"] is False
    assert "stale" in out["error"]


def test_create_refuses_existing_file(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - x.md"
    (tmp_path / rel).write_text("already here\n", encoding="utf-8")
    out = write_corpus_file(tmp_path, path=rel, mode="create", content="new\n", dry_run=True)
    assert out["ok"] is False
    assert "already exists" in out["error"]


def test_token_invalidates_when_content_changes_between_phases(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - x.md"
    preview = write_corpus_file(
        tmp_path, path=rel, mode="create", content="first\n", dry_run=True
    )
    out = write_corpus_file(
        tmp_path,
        path=rel,
        mode="create",
        content="second\n",
        dry_run=False,
        confirm_token=preview["confirm_token"],
    )
    assert out["ok"] is False
    assert "stale" in out["error"]


# ---------------------------------------------------------------------------
# Append: timeline.md preserves prior rows + new row at end
# ---------------------------------------------------------------------------


def _make_timeline(corpus: Path, slug: str) -> Path:
    hub = corpus / "Longmont Campaign/Campaign 2/NPCs" / slug
    hub.mkdir(parents=True, exist_ok=True)
    timeline = hub / "timeline.md"
    timeline.write_text(
        textwrap.dedent(
            """\
            # Dustwalker timeline

            | Session | Beat (short) | Recap (corpus-relative path) |
            | ------- | ------------ | ---------------------------- |
            | **3** | First sighting | `Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md` |

            ## Prep notes
            - reminder
            """
        ),
        encoding="utf-8",
    )
    return timeline


def test_append_timeline_dry_run_shows_new_row(tmp_path: Path) -> None:
    _make_timeline(tmp_path, "dustwalker")
    recap_dir = _make_recap_dir(tmp_path)
    recap_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    (recap_dir / "Session 20 - Snow.md").write_text("# Session 20\n", encoding="utf-8")

    preview = append_timeline_row(
        tmp_path,
        npc_slug="dustwalker",
        session=20,
        beat="Reappears at the gate",
        recap_path=recap_rel,
        dry_run=True,
    )
    assert preview["ok"] is True
    assert preview["phase"] == "preview"
    assert "Reappears at the gate" in preview["diff"]
    assert "**20**" in preview["diff"]


def test_append_timeline_commit_preserves_existing_rows(tmp_path: Path) -> None:
    timeline = _make_timeline(tmp_path, "dustwalker")
    recap_dir = _make_recap_dir(tmp_path)
    recap_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    (recap_dir / "Session 20 - Snow.md").write_text("# Session 20\n", encoding="utf-8")

    preview = append_timeline_row(
        tmp_path,
        npc_slug="dustwalker",
        session=20,
        beat="Reappears at the gate",
        recap_path=recap_rel,
        dry_run=True,
    )
    commit = append_timeline_row(
        tmp_path,
        npc_slug="dustwalker",
        session=20,
        beat="Reappears at the gate",
        recap_path=recap_rel,
        dry_run=False,
        confirm_token=preview["confirm_token"],
    )
    assert commit["ok"] is True
    body = timeline.read_text(encoding="utf-8")
    assert "First sighting" in body  # prior row preserved
    assert "Reappears at the gate" in body  # new row present
    assert "## Prep notes" in body  # trailing prose preserved
    # Ensure the new row appears after the older row.
    assert body.index("First sighting") < body.index("Reappears at the gate")


def test_append_timeline_unknown_recap_errors(tmp_path: Path) -> None:
    _make_timeline(tmp_path, "dustwalker")
    out = append_timeline_row(
        tmp_path,
        npc_slug="dustwalker",
        session=20,
        beat="x",
        recap_path="Longmont Campaign/Campaign 2/Session Recaps/Session 99 - missing.md",
        dry_run=True,
    )
    assert out["ok"] is False
    assert "does not exist" in out["error"]


def test_append_timeline_ambiguous_slug_errors(tmp_path: Path) -> None:
    _make_timeline(tmp_path, "twin")
    other = tmp_path / "Longmont Campaign/Campaign 1/NPCs/twin"
    other.mkdir(parents=True, exist_ok=True)
    (other / "timeline.md").write_text("# other\n\n| s | b | r |\n|---|---|---|\n", encoding="utf-8")
    recap_dir = _make_recap_dir(tmp_path)
    recap_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    (recap_dir / "Session 20 - Snow.md").write_text("# x\n", encoding="utf-8")
    out = append_timeline_row(
        tmp_path,
        npc_slug="twin",
        session=20,
        beat="x",
        recap_path=recap_rel,
        dry_run=True,
    )
    assert out["ok"] is False
    assert "multiple timelines" in out["error"]


def test_append_timeline_with_explicit_path_disambiguates(tmp_path: Path) -> None:
    _make_timeline(tmp_path, "twin")
    other_hub = tmp_path / "Longmont Campaign/Campaign 1/NPCs/twin"
    other_hub.mkdir(parents=True, exist_ok=True)
    other_timeline = other_hub / "timeline.md"
    other_timeline.write_text(
        "# other\n\n| Session | Beat | Recap |\n|---|---|---|\n", encoding="utf-8"
    )
    recap_dir = _make_recap_dir(tmp_path)
    recap_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    (recap_dir / "Session 20 - Snow.md").write_text("# x\n", encoding="utf-8")
    explicit = "Longmont Campaign/Campaign 2/NPCs/twin/timeline.md"

    preview = append_timeline_row(
        tmp_path,
        npc_slug="twin",
        session=20,
        beat="explicit win",
        recap_path=recap_rel,
        timeline_path=explicit,
        dry_run=True,
    )
    assert preview["ok"] is True
    commit = append_timeline_row(
        tmp_path,
        npc_slug="twin",
        session=20,
        beat="explicit win",
        recap_path=recap_rel,
        timeline_path=explicit,
        dry_run=False,
        confirm_token=preview["confirm_token"],
    )
    assert commit["ok"] is True
    chosen = (tmp_path / explicit).read_text(encoding="utf-8")
    other = other_timeline.read_text(encoding="utf-8")
    assert "explicit win" in chosen
    assert "explicit win" not in other


def _make_pc_timeline(corpus: Path, slug: str) -> Path:
    """Mirror of ``_make_timeline`` but under the PC hub layout."""
    hub = corpus / "Longmont Campaign/Campaign 2/PCs" / slug
    hub.mkdir(parents=True, exist_ok=True)
    timeline = hub / "timeline.md"
    timeline.write_text(
        textwrap.dedent(
            """\
            # PC timeline

            | Session | Beat (short) | Recap (corpus-relative path) |
            | ------- | ------------ | ---------------------------- |
            | **3** | First arc beat | `Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md` |
            """
        ),
        encoding="utf-8",
    )
    return timeline


def test_append_timeline_falls_back_to_pc_when_no_npc_hub(tmp_path: Path) -> None:
    """Slug-only resolver should locate ``PCs/<slug>/timeline.md`` when no NPC hub exists."""
    pc_timeline = _make_pc_timeline(tmp_path, "caelynn")
    recap_dir = _make_recap_dir(tmp_path)
    recap_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    (recap_dir / "Session 20 - Snow.md").write_text("# Session 20\n", encoding="utf-8")

    preview = append_timeline_row(
        tmp_path,
        npc_slug="caelynn",
        session=20,
        beat="PC fallback resolved",
        recap_path=recap_rel,
        dry_run=True,
    )
    assert preview["ok"] is True, preview
    assert preview["path"].endswith("PCs/caelynn/timeline.md")

    commit = append_timeline_row(
        tmp_path,
        npc_slug="caelynn",
        session=20,
        beat="PC fallback resolved",
        recap_path=recap_rel,
        dry_run=False,
        confirm_token=preview["confirm_token"],
    )
    assert commit["ok"] is True, commit
    body = pc_timeline.read_text(encoding="utf-8")
    assert "PC fallback resolved" in body
    assert "First arc beat" in body  # prior row preserved


def test_append_timeline_prefers_npc_hub_over_pc_when_both_present(tmp_path: Path) -> None:
    """If a slug exists under both NPCs/ and PCs/, NPC hub wins (back-compat)."""
    npc_timeline = _make_timeline(tmp_path, "shared_slug")
    pc_timeline = _make_pc_timeline(tmp_path, "shared_slug")
    recap_dir = _make_recap_dir(tmp_path)
    recap_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    (recap_dir / "Session 20 - Snow.md").write_text("# Session 20\n", encoding="utf-8")

    preview = append_timeline_row(
        tmp_path,
        npc_slug="shared_slug",
        session=20,
        beat="goes to NPC hub",
        recap_path=recap_rel,
        dry_run=True,
    )
    assert preview["ok"] is True, preview
    assert preview["path"].endswith("NPCs/shared_slug/timeline.md")

    commit = append_timeline_row(
        tmp_path,
        npc_slug="shared_slug",
        session=20,
        beat="goes to NPC hub",
        recap_path=recap_rel,
        dry_run=False,
        confirm_token=preview["confirm_token"],
    )
    assert commit["ok"] is True
    assert "goes to NPC hub" in npc_timeline.read_text(encoding="utf-8")
    assert "goes to NPC hub" not in pc_timeline.read_text(encoding="utf-8")


def test_append_timeline_unknown_slug_mentions_both_hubs(tmp_path: Path) -> None:
    recap_dir = _make_recap_dir(tmp_path)
    recap_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    (recap_dir / "Session 20 - Snow.md").write_text("# Session 20\n", encoding="utf-8")

    out = append_timeline_row(
        tmp_path,
        npc_slug="nobody_here",
        session=20,
        beat="x",
        recap_path=recap_rel,
        dry_run=True,
    )
    assert out["ok"] is False
    assert "NPCs/nobody_here/timeline.md" in out["error"]
    assert "PCs/nobody_here/timeline.md" in out["error"]


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------


def test_session_prep_append_rejects_non_blockquote_payload(tmp_path: Path) -> None:
    hub = tmp_path / "Longmont Campaign/Campaign 2/Session Prep"
    hub.mkdir(parents=True, exist_ok=True)
    rel = "Longmont Campaign/Campaign 2/Session Prep/session_20_notes.md"
    (tmp_path / rel).write_text("# Prep\n\nDone.\n", encoding="utf-8")
    out = write_corpus_file(
        tmp_path, path=rel, mode="append", content="plain text\n", dry_run=True
    )
    assert out["ok"] is False
    assert "blockquote" in out["error"]


def test_session_prep_append_accepts_blockquote_bold_payload(tmp_path: Path) -> None:
    hub = tmp_path / "Longmont Campaign/Campaign 2/Session Prep"
    hub.mkdir(parents=True, exist_ok=True)
    rel = "Longmont Campaign/Campaign 2/Session Prep/session_20_notes.md"
    (tmp_path / rel).write_text("# Prep\n\nDone.\n", encoding="utf-8")
    out = write_corpus_file(
        tmp_path,
        path=rel,
        mode="append",
        content="> **Prep ↔ recap:** `Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`\n",
        dry_run=True,
    )
    assert out["ok"] is True


def test_path_traversal_rejected(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    out = write_corpus_file(
        tmp_path,
        path="Longmont Campaign/Campaign 2/Session Recaps/../../../etc/passwd.md",
        mode="create",
        content="x\n",
        dry_run=True,
    )
    assert out["ok"] is False


# ---------------------------------------------------------------------------
# Fingerprint reporting
# ---------------------------------------------------------------------------


def test_commit_returns_new_fingerprint(tmp_path: Path) -> None:
    _make_recap_dir(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Snow.md"
    body = "# Session 20\n"

    preview = write_corpus_file(tmp_path, path=rel, mode="create", content=body, dry_run=True)
    commit = write_corpus_file(
        tmp_path,
        path=rel,
        mode="create",
        content=body,
        dry_run=False,
        confirm_token=preview["confirm_token"],
    )
    assert commit["ok"] is True
    assert "new_corpus_fingerprint" in commit
    assert isinstance(commit["new_corpus_fingerprint"], str) and commit["new_corpus_fingerprint"]
    assert commit["new_corpus_fingerprint"] in commit["fingerprint_reminder"]


def test_update_step0_expected_fingerprint_rewrites_json(tmp_path: Path) -> None:
    import json as _json

    from src.agent.corpus_writer import update_step0_expected_fingerprint

    step0 = tmp_path / "step0.json"
    step0.write_text(
        _json.dumps(
            {
                "schema": "lysandra_vertical_slice_step0_v1",
                "expected_fingerprint": "old_value_xxxxxxxxxxxxxxxxxxxxxxx",
                "allow_fingerprint_drift": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out = update_step0_expected_fingerprint(step0, new_fingerprint="new_value_yyyyyyyyyyyyyyyy")
    assert out["ok"] is True
    assert out["old"] == "old_value_xxxxxxxxxxxxxxxxxxxxxxx"
    assert out["new"] == "new_value_yyyyyyyyyyyyyyyy"
    rewritten = _json.loads(step0.read_text(encoding="utf-8"))
    assert rewritten["expected_fingerprint"] == "new_value_yyyyyyyyyyyyyyyy"
    assert rewritten["schema"] == "lysandra_vertical_slice_step0_v1"
