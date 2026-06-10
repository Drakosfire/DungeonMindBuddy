from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.corpus_writer import is_writable_corpus_path, write_corpus_file

ALLOWED_GENERATED_STATBLOCK = (
    "Longmont Campaign/Campaign 2/Statblocks/generated/generated_obsidian_thornling.md"
)


def test_generated_statblock_create_allowed() -> None:
    allowed, reason = is_writable_corpus_path(ALLOWED_GENERATED_STATBLOCK, "create")
    assert allowed, reason


@pytest.mark.parametrize(
    "rel_path",
    [
        "Longmont Campaign/Campaign 2/Statblocks/generated/Nested/foo.md",
        "Longmont Campaign/Campaign 2/Statblocks/generated/Bad Slug.md",
        "Longmont Campaign/Campaign 2/Statblocks/generated/foo.txt",
        "Elderwyld/Creatures/generated_obsidian_thornling.md",
        "Longmont Campaign/Campaign 2/NPCs/foo/foo_statblock.md",
    ],
)
def test_generated_statblock_create_rejects_unsafe_paths(rel_path: str) -> None:
    allowed, reason = is_writable_corpus_path(rel_path, "create")
    assert not allowed, f"unexpectedly allowed {rel_path}: {reason}"


def test_generated_statblock_append_rejected() -> None:
    allowed, reason = is_writable_corpus_path(ALLOWED_GENERATED_STATBLOCK, "append")
    assert not allowed
    assert "append mode is not allowed" in reason


def test_generated_statblock_dry_run_and_commit(tmp_path: Path) -> None:
    body = "---\ntitle: Generated Obsidian Thornling\n---\n# Generated Obsidian Thornling\n"

    preview = write_corpus_file(
        tmp_path,
        path=ALLOWED_GENERATED_STATBLOCK,
        mode="create",
        content=body,
        dry_run=True,
    )

    assert preview["ok"] is True
    assert preview["phase"] == "preview"
    assert preview["confirm_token"]
    assert "Generated Obsidian Thornling" in preview["diff"]
    assert not (tmp_path / ALLOWED_GENERATED_STATBLOCK).exists()

    commit = write_corpus_file(
        tmp_path,
        path=ALLOWED_GENERATED_STATBLOCK,
        mode="create",
        content=body,
        dry_run=False,
        confirm_token=preview["confirm_token"],
    )

    assert commit["ok"] is True
    assert commit["phase"] == "committed"
    assert (tmp_path / ALLOWED_GENERATED_STATBLOCK).read_text(encoding="utf-8") == body
