"""Tests for the deterministic recap-context resolver."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.agent.recap_context import (
    RECENT_RECAP_K,
    RecapContextError,
    resolve_recap_context,
)


def _write_recap(
    corpus_root: Path,
    *,
    campaign_hub: str,
    filename: str,
    session: int,
    campaign_id: str,
    title: str | None = None,
) -> Path:
    if title is None:
        title = f"Session {session} - Recap"
    body = textwrap.dedent(
        f"""\
        ---
        title: "{title}"
        document_class: play
        canon_layer: campaign
        campaign_id: {campaign_id}
        temporal_scope: session_specific
        session: {session}
        origin_session: {session}
        last_updated_session: {session}
        source_class: observed_session_recap
        ---
        # {title}

        Body of session {session}.
        """
    )
    recaps_dir = corpus_root / campaign_hub / "Session Recaps"
    recaps_dir.mkdir(parents=True, exist_ok=True)
    path = recaps_dir / filename
    path.write_text(body, encoding="utf-8")
    return path


def _write_prep(
    corpus_root: Path, *, campaign_hub: str, filename: str, body: str = "prep notes"
) -> Path:
    prep_dir = corpus_root / campaign_hub / "Session Prep"
    prep_dir.mkdir(parents=True, exist_ok=True)
    path = prep_dir / filename
    path.write_text(body, encoding="utf-8")
    return path


def _seed_campaign_2(root: Path) -> None:
    """Five recaps in Campaign 2 (sessions 15–19), no Session 20 (pre-state)."""
    hub = "Longmont Campaign/Campaign 2"
    for n in (15, 16, 17, 18, 19):
        _write_recap(
            root,
            campaign_hub=hub,
            filename=f"Session {n} - Recap.md",
            session=n,
            campaign_id="longmont-c2",
        )


def test_target_session_defaults_to_max_plus_one_for_active_campaign(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    ctx = resolve_recap_context(tmp_path)
    assert ctx.campaign_id == "longmont-c2"
    assert ctx.target_session == 20
    assert ctx.next_session_after_target == 21


def test_recent_recaps_capped_at_K_and_sorted_desc_by_session(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    ctx = resolve_recap_context(tmp_path)
    assert len(ctx.recent_recaps) == RECENT_RECAP_K
    assert [e.session for e in ctx.recent_recaps] == [19, 18, 17]


def test_recent_recaps_excludes_target_and_above(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_recap(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="Session 22 - Recap.md",
        session=22,
        campaign_id="longmont-c2",
    )
    ctx = resolve_recap_context(tmp_path, target_session=20)
    assert all(e.session < 20 for e in ctx.recent_recaps)
    assert [e.session for e in ctx.recent_recaps] == [19, 18, 17]


def test_recent_recaps_uses_frontmatter_not_filename(tmp_path: Path) -> None:
    """Filename ``Session 9 - Recap`` collates **after** ``Session 19`` lexicographically;
    we must sort by frontmatter ``session: N``, not filename."""
    hub = "Longmont Campaign/Campaign 2"
    _write_recap(
        tmp_path,
        campaign_hub=hub,
        filename="Session 19 - Recap.md",
        session=19,
        campaign_id="longmont-c2",
    )
    _write_recap(
        tmp_path,
        campaign_hub=hub,
        filename="Session 9 - Recap.md",
        session=9,
        campaign_id="longmont-c2",
    )
    ctx = resolve_recap_context(tmp_path)
    assert [e.session for e in ctx.recent_recaps] == [19, 9]


def test_explicit_target_session_overrides_default(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    ctx = resolve_recap_context(tmp_path, target_session=18)
    assert ctx.target_session == 18
    assert [e.session for e in ctx.recent_recaps] == [17, 16, 15]


def test_target_session_already_present_surfaces_note(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    ctx = resolve_recap_context(tmp_path, target_session=18)
    assert any("already exists" in n for n in ctx.notes)


def test_fewer_than_K_priors_surfaces_note(tmp_path: Path) -> None:
    hub = "Longmont Campaign/Campaign 2"
    for n in (1, 2):
        _write_recap(
            tmp_path,
            campaign_hub=hub,
            filename=f"Session {n} - Recap.md",
            session=n,
            campaign_id="longmont-c2",
        )
    ctx = resolve_recap_context(tmp_path)
    assert ctx.target_session == 3
    assert len(ctx.recent_recaps) == 2
    assert any("Only 2 prior" in n for n in ctx.notes)


def test_prep_doc_resolves_unique_match(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_stacey_stuart_marla_reference.md",
    )
    ctx = resolve_recap_context(tmp_path)
    assert ctx.prep_doc_path is not None
    assert ctx.prep_doc_path.endswith("session_20_stacey_stuart_marla_reference.md")
    assert ctx.session_prep_dir is not None
    assert ctx.session_prep_dir.endswith("Session Prep")


def test_prep_doc_zero_matches_returns_none(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    (tmp_path / "Longmont Campaign/Campaign 2/Session Prep").mkdir(parents=True, exist_ok=True)
    ctx = resolve_recap_context(tmp_path)
    assert ctx.prep_doc_path is None
    assert ctx.session_prep_dir is not None
    assert any("No prep doc matched" in n for n in ctx.notes)


def test_prep_doc_missing_dir_surfaces_note(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    ctx = resolve_recap_context(tmp_path)
    assert ctx.prep_doc_path is None
    assert ctx.session_prep_dir is None
    assert any("no 'Session Prep/' folder" in n for n in ctx.notes)


def test_prep_doc_duplicate_raises(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    hub = "Longmont Campaign/Campaign 2"
    _write_prep(tmp_path, campaign_hub=hub, filename="session_20_part_one.md")
    _write_prep(tmp_path, campaign_hub=hub, filename="session_20_part_two.md")
    with pytest.raises(RecapContextError, match="Multiple prep docs"):
        resolve_recap_context(tmp_path)


def test_prep_doc_bare_form_accepted(tmp_path: Path) -> None:
    """``session_20.md`` (no underscore-suffix) is the rare single-file form and is OK."""
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path, campaign_hub="Longmont Campaign/Campaign 2", filename="session_20.md"
    )
    ctx = resolve_recap_context(tmp_path)
    assert ctx.prep_doc_path is not None
    assert ctx.prep_doc_path.endswith("session_20.md")


def test_prep_doc_for_other_session_is_ignored(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_2_something.md",
    )
    ctx = resolve_recap_context(tmp_path)
    assert ctx.prep_doc_path is None


def test_multi_campaign_auto_detect_picks_highest_max_session(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_recap(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 1",
        filename="Session 12 - Recap.md",
        session=12,
        campaign_id="longmont-c1",
    )
    ctx = resolve_recap_context(tmp_path)
    assert ctx.campaign_id == "longmont-c2"
    assert ctx.target_session == 20


def test_multi_campaign_explicit_campaign_id_pins_choice(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_recap(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 1",
        filename="Session 12 - Recap.md",
        session=12,
        campaign_id="longmont-c1",
    )
    ctx = resolve_recap_context(tmp_path, campaign_id="longmont-c1")
    assert ctx.campaign_id == "longmont-c1"
    assert ctx.target_session == 13
    assert [e.session for e in ctx.recent_recaps] == [12]


def test_unknown_campaign_id_raises(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    with pytest.raises(RecapContextError, match="has no recaps"):
        resolve_recap_context(tmp_path, campaign_id="nonexistent")


def test_no_recaps_anywhere_raises(tmp_path: Path) -> None:
    with pytest.raises(RecapContextError, match="No recap files"):
        resolve_recap_context(tmp_path)


def test_files_without_required_frontmatter_are_skipped(tmp_path: Path) -> None:
    """An index file (``document_class: reference``, no ``session``) must be ignored."""
    hub = "Longmont Campaign/Campaign 2"
    _seed_campaign_2(tmp_path)
    index = tmp_path / hub / "Session Recaps" / "Session Recaps (index).md"
    index.write_text(
        textwrap.dedent(
            """\
            ---
            title: "Campaign 2 Session Recaps (index)"
            document_class: reference
            canon_layer: campaign
            campaign_id: longmont-c2
            temporal_scope: campaign_stateful
            source_class: index
            ---
            # Index

            Per-session play documents live here.
            """
        ),
        encoding="utf-8",
    )
    ctx = resolve_recap_context(tmp_path)
    assert ctx.target_session == 20
    paths = [e.path for e in ctx.recent_recaps]
    assert all("(index)" not in p for p in paths)


def test_to_dict_round_trips_for_tool_wire_format(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    _write_prep(
        tmp_path,
        campaign_hub="Longmont Campaign/Campaign 2",
        filename="session_20_x.md",
    )
    ctx = resolve_recap_context(tmp_path)
    d = ctx.to_dict()
    assert d["campaign_id"] == "longmont-c2"
    assert d["target_session"] == 20
    assert isinstance(d["recent_recaps"], list)
    assert d["recent_recaps"][0]["session"] == 19
    assert d["prep_doc_path"].endswith("session_20_x.md")
    assert d["session_recaps_dir"].endswith("Session Recaps")
    assert d["next_session_after_target"] == 21


def test_relative_paths_use_posix_separators(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    ctx = resolve_recap_context(tmp_path)
    for e in ctx.recent_recaps:
        assert "\\" not in e.path
    assert "\\" not in ctx.session_recaps_dir
    assert "\\" not in ctx.campaign_hub


def test_npcs_dir_resolved_when_present(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    npcs = tmp_path / "Longmont Campaign/Campaign 2/NPCs/marla_brambleback"
    npcs.mkdir(parents=True)
    (npcs / "README.md").write_text("# Marla\n", encoding="utf-8")
    ctx = resolve_recap_context(tmp_path)
    assert ctx.npcs_dir is not None
    assert ctx.npcs_dir.endswith("NPCs")


def test_npcs_dir_none_when_absent(tmp_path: Path) -> None:
    _seed_campaign_2(tmp_path)
    ctx = resolve_recap_context(tmp_path)
    assert ctx.npcs_dir is None
