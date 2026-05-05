"""Unit tests for Cursor-managed canvas path resolution."""

from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification import cursor_canvas_paths as ccp


def test_workspace_folder_slug_linux_style() -> None:
    root = Path("/home/alice/Projects/DungeonOverMind/DungeonMindBuddy")
    assert ccp.workspace_folder_slug(root) == "home-alice-Projects-DungeonOverMind-DungeonMindBuddy"


def test_default_cursor_canvas_path_under_cursor_projects() -> None:
    root = Path("/tmp/workspace")
    p = ccp.default_cursor_canvas_path("foo.canvas.tsx", workspace_root=root)
    slug = ccp.workspace_folder_slug(root)
    assert p == Path.home() / ".cursor" / "projects" / slug / "canvases" / "foo.canvas.tsx"
