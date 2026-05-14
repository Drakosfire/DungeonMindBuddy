"""Unit tests for Cursor-managed canvas path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.sentence_routing_retrieval_falsification import cursor_canvas_paths as ccp


def test_workspace_folder_slug_linux_style() -> None:
    root = Path("/home/alice/Projects/DungeonOverMind/DungeonMindBuddy")
    assert ccp.workspace_folder_slug(root) == "home-alice-Projects-DungeonOverMind-DungeonMindBuddy"


def test_default_cursor_canvas_path_under_cursor_projects() -> None:
    root = Path("/tmp/workspace")
    p = ccp.default_cursor_canvas_path("foo.canvas.tsx", workspace_root=root)
    slug = ccp.workspace_folder_slug(root)
    assert p == Path.home() / ".cursor" / "projects" / slug / "canvases" / "foo.canvas.tsx"


def test_ensure_canvas_file_for_patch_creates_parent_raises_when_missing(tmp_path: Path) -> None:
    dest = tmp_path / "ide" / "canvases" / "missing.canvas.tsx"
    with pytest.raises(FileNotFoundError, match="Canvas file"):
        ccp.ensure_canvas_file_for_patch(dest)


def test_ensure_canvas_file_for_patch_noop_when_exists(tmp_path: Path) -> None:
    dest = tmp_path / "ide" / "canvases" / "x.canvas.tsx"
    dest.parent.mkdir(parents=True)
    dest.write_text("local", encoding="utf-8")
    ccp.ensure_canvas_file_for_patch(dest)
    assert dest.read_text(encoding="utf-8") == "local"
