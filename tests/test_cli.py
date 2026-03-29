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


def test_ingest_without_frontmatter_and_no_layer_fails_fast(tmp_path: Path) -> None:
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nNo metadata.\n", encoding="utf-8")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}" --no-frontmatter')
    output = capture.getvalue().lower()
    assert "--layer is required" in output


def test_ingest_frontmatter_makes_layer_optional(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "battle.md"
    source.write_text(
        (
            "---\n"
            'title: "Battle with The Wolf and Aftermath"\n'
            "document_class: play\n"
            "canon_layer: campaign\n"
            "campaign_id: longmont-c1\n"
            "session: 8\n"
            "source_class: observed_session_recap\n"
            "---\n\n"
            "# Encounter\n\n"
            "The wolf receives a killing blow.\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}"')
    output = capture.getvalue().lower()
    assert "openai_api_key is required for ingest" in output
    assert "--layer is required" not in output


def test_ingest_frontmatter_conflict_with_cli_flags_fails(tmp_path: Path) -> None:
    source = tmp_path / "battle.md"
    source.write_text(
        (
            "---\n"
            'title: "Battle with The Wolf and Aftermath"\n'
            "document_class: play\n"
            "canon_layer: campaign\n"
            "campaign_id: longmont-c1\n"
            "session: 8\n"
            "source_class: observed_session_recap\n"
            "---\n\n"
            "# Encounter\n\n"
            "The wolf receives a killing blow.\n"
        ),
        encoding="utf-8",
    )
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}" --layer world')
    output = capture.getvalue().lower()
    assert "frontmatter conflicts with cli arguments" in output


def test_ingest_missing_frontmatter_runs_inference_loop(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "no_meta.md"
    source.write_text("# Session 2 Recap\n\nThe council reconvenes.\n", encoding="utf-8")
    cli = DungeonBuddyCLI(store_dir=tmp_path / "store", verbose=False)

    monkeypatch.setattr("src.cli.infer_frontmatter_metadata", lambda **_: None)

    def _fake_confirm(self, source_path, text):  # noqa: ANN001
        _ = text
        source_path.write_text(
            (
                "---\n"
                'title: "Session 2 Recap"\n'
                "document_class: play\n"
                "canon_layer: campaign\n"
                "campaign_id: longmont-c1\n"
                "session: 2\n"
                "source_class: observed_session_recap\n"
                "---\n\n"
                "# Session 2 Recap\n\nThe council reconvenes.\n"
            ),
            encoding="utf-8",
        )
        return True

    monkeypatch.setattr(DungeonBuddyCLI, "_confirm_inferred_frontmatter", _fake_confirm)
    monkeypatch.setattr("src.cli._load_env", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    capture = io.StringIO()
    with redirect_stdout(capture):
        cli.handle_line(f'ingest "{source}"')
    output = capture.getvalue().lower()
    assert "openai_api_key is required for ingest" in output
