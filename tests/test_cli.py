from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

from src.cli import DungeonBuddyCLI


def test_ask_require_campaign_fails_fast_without_campaign(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)
    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line('ask "What happened?" --require-campaign')
    output = capture.getvalue()
    assert "campaign scope is required" in output.lower()


def test_compact_command_runs(tmp_path: Path) -> None:
    store_dir = tmp_path / "store"
    cli = DungeonBuddyCLI(store_dir=store_dir, verbose=False)
    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line("compact")
    output = capture.getvalue()
    assert "compaction complete" in output.lower()
