"""Autonomous-writer surface for ``make_tool_dispatcher`` (one-phase loopback).

The corpus_writer's safety properties (allowlist, payload validators,
``file_state_token`` CAS) stay in place inside the loopback; only the surface
exposed to the model is one-phase. These tests verify that:

- a single ``append_timeline_row`` call commits in autonomous mode and the file
  is actually written;
- allowlist denial and payload-validator failure surface the writer's error
  JSON unchanged so the model can correct itself;
- legacy ``dry_run`` / ``confirm_token`` arguments emitted by a model are
  stripped silently (the autonomous schema doesn't expose them);
- the default ``autonomous_writes=False`` preserves the operator-driven
  two-phase contract (regression guard for the ``recap-write`` skill);
- the writer-tool schema toggles between simplified (autonomous) and
  full two-phase shapes based on the flag.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from src.agent.planner import (
    _planner_tools_responses,
    _planner_writer_tools_responses,
    make_tool_dispatcher,
)


def _seed_corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    (corpus / "Longmont Campaign/Campaign 2/Session Recaps").mkdir(parents=True)
    (corpus / "Longmont Campaign/Campaign 2/NPCs/dustwalker").mkdir(parents=True)
    (corpus / "Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md").write_text(
        textwrap.dedent(
            """\
            # Dustwalker timeline

            | Session | Beat | Recap |
            | --- | --- | --- |
            | **3** | first | `Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md` |
            """
        ),
        encoding="utf-8",
    )
    (corpus / "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md").write_text(
        "# Session 3\n", encoding="utf-8"
    )
    return corpus


def _autonomous_dispatch(corpus: Path):
    return make_tool_dispatcher(
        corpus,
        object(),
        "gpt-mock",
        allow_corpus_writes=True,
        autonomous_writes=True,
    )


def test_autonomous_append_timeline_row_commits_in_one_call(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dispatch = _autonomous_dispatch(corpus)
    out = dispatch(
        "append_timeline_row",
        json.dumps(
            {
                "npc_slug": "dustwalker",
                "session": 20,
                "beat": "Returns to the gate",
                "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
            }
        ),
    )
    payload = json.loads(out)
    assert payload["ok"] is True, payload
    assert payload["phase"] == "committed"
    assert "confirm_token" not in payload
    assert "next_call" not in payload
    body = (corpus / "Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md").read_text(
        encoding="utf-8"
    )
    assert "Returns to the gate" in body
    assert "first" in body  # prior row preserved


def test_autonomous_write_corpus_file_create_commits_in_one_call(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dispatch = _autonomous_dispatch(corpus)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - First Snow.md"
    out = dispatch(
        "write_corpus_file",
        json.dumps({"path": rel, "mode": "create", "content": "# Session 20\n"}),
    )
    payload = json.loads(out)
    assert payload["ok"] is True, payload
    assert payload["phase"] == "committed"
    assert (corpus / rel).is_file()


def test_autonomous_allowlist_denial_returns_writer_error(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dossier_rel = (
        "Longmont Campaign/Campaign 2/NPCs/dustwalker/"
        "dustwalker_character_dossier.md"
    )
    (corpus / dossier_rel).write_text("# untouched\n", encoding="utf-8")
    dispatch = _autonomous_dispatch(corpus)
    out = dispatch(
        "write_corpus_file",
        json.dumps({"path": dossier_rel, "mode": "append", "content": "rewrite\n"}),
    )
    payload = json.loads(out)
    assert payload["ok"] is False, payload
    assert "read-only" in payload["error"]
    # File untouched (no ghost commit from the hidden preview).
    assert (corpus / dossier_rel).read_text(encoding="utf-8") == "# untouched\n"


def test_autonomous_payload_validator_failure_returns_writer_error(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    prep_dir = corpus / "Longmont Campaign/Campaign 2/Session Prep"
    prep_dir.mkdir(parents=True)
    prep_rel = "Longmont Campaign/Campaign 2/Session Prep/session_4_prep.md"
    (corpus / prep_rel).write_text("# Session 4 prep\n", encoding="utf-8")
    dispatch = _autonomous_dispatch(corpus)
    # Session Prep append validator rejects payloads that aren't a blockquote
    # whose first line includes `**`.
    out = dispatch(
        "write_corpus_file",
        json.dumps(
            {
                "path": prep_rel,
                "mode": "append",
                "content": "plain text without a blockquote\n",
            }
        ),
    )
    payload = json.loads(out)
    assert payload["ok"] is False, payload
    assert "blockquote" in payload["error"]


def test_autonomous_strips_legacy_dry_run_and_confirm_token_args(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dispatch = _autonomous_dispatch(corpus)
    out = dispatch(
        "append_timeline_row",
        json.dumps(
            {
                "npc_slug": "dustwalker",
                "session": 21,
                "beat": "Holds the line",
                "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
                # Legacy / hallucinated fields the model might still emit:
                "dry_run": True,
                "confirm_token": "ignored-stale-token",
            }
        ),
    )
    payload = json.loads(out)
    assert payload["ok"] is True, payload
    assert payload["phase"] == "committed"
    body = (corpus / "Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md").read_text(
        encoding="utf-8"
    )
    assert "Holds the line" in body


def test_default_two_phase_still_required_when_autonomous_off(tmp_path: Path) -> None:
    """Regression guard: operator-driven two-phase contract unchanged for default callers."""
    corpus = _seed_corpus(tmp_path)
    dispatch = make_tool_dispatcher(
        corpus,
        object(),
        "gpt-mock",
        allow_corpus_writes=True,
        # autonomous_writes defaults to False
    )
    out = dispatch(
        "append_timeline_row",
        json.dumps(
            {
                "npc_slug": "dustwalker",
                "session": 20,
                "beat": "x",
                "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
                "dry_run": False,
            }
        ),
    )
    payload = json.loads(out)
    assert payload["ok"] is False, payload
    assert "confirm_token" in payload["error"]


def test_writer_tool_schema_simplifies_in_autonomous_mode() -> None:
    by_name_legacy = {t["name"]: t for t in _planner_writer_tools_responses()}
    by_name_auto = {
        t["name"]: t for t in _planner_writer_tools_responses(autonomous_writes=True)
    }
    legacy_write = by_name_legacy["write_corpus_file"]["parameters"]["properties"]
    auto_write = by_name_auto["write_corpus_file"]["parameters"]["properties"]
    assert "dry_run" in legacy_write and "confirm_token" in legacy_write
    assert "dry_run" not in auto_write and "confirm_token" not in auto_write

    legacy_row = by_name_legacy["append_timeline_row"]["parameters"]["properties"]
    auto_row = by_name_auto["append_timeline_row"]["parameters"]["properties"]
    assert "dry_run" in legacy_row and "confirm_token" in legacy_row
    assert "dry_run" not in auto_row and "confirm_token" not in auto_row

    # Description sanity-check: the autonomous description must not promise a
    # preview / two-phase / confirm_token surface to the model.
    auto_desc = by_name_auto["append_timeline_row"]["description"].lower()
    for forbidden in ("two-phase", "dry-run", "dry_run", "confirm_token", "preview"):
        assert forbidden not in auto_desc, (forbidden, auto_desc)


def test_planner_tools_responses_threads_autonomous_flag() -> None:
    auto_names = {
        t["name"]: t
        for t in _planner_tools_responses(
            include_write_tools=True, autonomous_writes=True
        )
    }
    legacy_names = {
        t["name"]: t for t in _planner_tools_responses(include_write_tools=True)
    }
    assert "write_corpus_file" in auto_names and "write_corpus_file" in legacy_names
    auto_props = auto_names["write_corpus_file"]["parameters"]["properties"]
    legacy_props = legacy_names["write_corpus_file"]["parameters"]["properties"]
    assert "dry_run" not in auto_props
    assert "dry_run" in legacy_props
