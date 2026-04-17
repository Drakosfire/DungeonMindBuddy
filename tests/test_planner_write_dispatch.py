"""Planner write-tool registration and dispatcher routing (gated by allow_corpus_writes)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from src.agent.planner import (
    _planner_tools_responses,
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


def test_writer_tools_absent_by_default() -> None:
    names = {t["name"] for t in _planner_tools_responses()}
    assert "write_corpus_file" not in names
    assert "append_timeline_row" not in names


def test_writer_tools_present_when_enabled() -> None:
    names = {t["name"] for t in _planner_tools_responses(include_write_tools=True)}
    assert "write_corpus_file" in names
    assert "append_timeline_row" in names


def test_writer_tool_schemas_have_required_fields() -> None:
    by_name = {t["name"]: t for t in _planner_tools_responses(include_write_tools=True)}
    write_schema = by_name["write_corpus_file"]["parameters"]
    assert write_schema["required"] == ["path", "mode", "content"]
    assert write_schema["properties"]["mode"]["enum"] == ["create", "append"]
    timeline_schema = by_name["append_timeline_row"]["parameters"]
    assert timeline_schema["required"] == ["npc_slug", "session", "beat", "recap_path"]


def test_dispatcher_blocks_writes_when_disabled(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dispatch = make_tool_dispatcher(corpus, object(), "gpt-mock")
    out = dispatch(
        "write_corpus_file",
        json.dumps(
            {
                "path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - x.md",
                "mode": "create",
                "content": "# x\n",
                "dry_run": True,
            }
        ),
    )
    assert out.startswith("Error:")
    assert "disabled" in out
    out2 = dispatch(
        "append_timeline_row",
        json.dumps(
            {
                "npc_slug": "dustwalker",
                "session": 20,
                "beat": "x",
                "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
            }
        ),
    )
    assert out2.startswith("Error:")
    assert "disabled" in out2


def test_dispatcher_routes_write_corpus_file_dry_run(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dispatch = make_tool_dispatcher(corpus, object(), "gpt-mock", allow_corpus_writes=True)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - First Snow.md"
    out = dispatch(
        "write_corpus_file",
        json.dumps({"path": rel, "mode": "create", "content": "# Session 20\n", "dry_run": True}),
    )
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["phase"] == "preview"
    assert payload["path"] == rel
    assert isinstance(payload["confirm_token"], str) and payload["confirm_token"]
    assert not (corpus / rel).exists()


def test_dispatcher_routes_append_timeline_row_round_trip(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dispatch = make_tool_dispatcher(corpus, object(), "gpt-mock", allow_corpus_writes=True)
    base_args = {
        "npc_slug": "dustwalker",
        "session": 20,
        "beat": "Returns to the gate",
        "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
    }
    preview = json.loads(
        dispatch("append_timeline_row", json.dumps({**base_args, "dry_run": True}))
    )
    assert preview["ok"] is True
    commit = json.loads(
        dispatch(
            "append_timeline_row",
            json.dumps({**base_args, "dry_run": False, "confirm_token": preview["confirm_token"]}),
        )
    )
    assert commit["ok"] is True
    body = (corpus / "Longmont Campaign/Campaign 2/NPCs/dustwalker/timeline.md").read_text(
        encoding="utf-8"
    )
    assert "Returns to the gate" in body
    assert "first" in body  # prior row preserved


def test_dispatcher_rejects_non_integer_session(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dispatch = make_tool_dispatcher(corpus, object(), "gpt-mock", allow_corpus_writes=True)
    out = dispatch(
        "append_timeline_row",
        json.dumps(
            {
                "npc_slug": "dustwalker",
                "session": "not-a-number",
                "beat": "x",
                "recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
                "dry_run": True,
            }
        ),
    )
    assert out.startswith("Error:")
    assert "session" in out


def test_dispatcher_blocks_dossier_write_even_when_writes_enabled(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    dossier = corpus / "Longmont Campaign/Campaign 2/NPCs/dustwalker/dustwalker_character_dossier.md"
    dossier.write_text("# untouched\n", encoding="utf-8")
    dispatch = make_tool_dispatcher(corpus, object(), "gpt-mock", allow_corpus_writes=True)
    out = dispatch(
        "write_corpus_file",
        json.dumps(
            {
                "path": "Longmont Campaign/Campaign 2/NPCs/dustwalker/"
                "dustwalker_character_dossier.md",
                "mode": "append",
                "content": "rewrite\n",
                "dry_run": True,
            }
        ),
    )
    payload = json.loads(out)
    assert payload["ok"] is False
    assert "read-only" in payload["error"]
    assert dossier.read_text(encoding="utf-8") == "# untouched\n"
