"""Resolve Cursor IDE-managed canvas file paths (``~/.cursor/projects/<slug>/canvases/``).

Cursor stores workspace-local canvases under a directory derived from the absolute
workspace root. This matches the layout described in ``.cursor/skills-cursor/canvas/SKILL.md``.

Override the **canvases directory** (not a single file) with env ``DMB_CURSOR_CANVAS_DIR``
if your Cursor install uses a different layout.

Emitters default to :func:`default_cursor_canvas_path` (IDE-managed ``.../canvases/``). Before patching,
:func:`ensure_canvas_file_for_patch` creates that directory and, if the file is missing, copies the
committed template from :func:`repo_canvases_dir` (``<repo>/canvases/<same basename>``).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _repo_root_from_eval_file() -> Path:
    """DungeonMindBuddy repo root (parent of ``evals/``)."""
    return Path(__file__).resolve().parents[2]


def workspace_folder_slug(workspace_root: Path) -> str:
    """Slug used under ``~/.cursor/projects/<slug>/`` for this workspace."""
    s = workspace_root.resolve().as_posix()
    if len(s) >= 2 and s[1] == ":":
        s = s[2:].lstrip("/")
    else:
        s = s.lstrip("/")
    return s.replace("/", "-")


def cursor_canvases_dir(workspace_root: Path | None = None) -> Path:
    """Directory where Cursor expects ``*.canvas.tsx`` for this repo."""
    override = (os.environ.get("DMB_CURSOR_CANVAS_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    root = workspace_root if workspace_root is not None else _repo_root_from_eval_file()
    slug = workspace_folder_slug(root)
    return Path.home() / ".cursor" / "projects" / slug / "canvases"


def default_cursor_canvas_path(filename: str, *, workspace_root: Path | None = None) -> Path:
    """Full path to one canvas file in the IDE-managed canvases directory."""
    return cursor_canvases_dir(workspace_root) / filename


def repo_canvases_dir(workspace_root: Path | None = None) -> Path:
    """Committed canvas templates under ``<repo>/canvases/`` (source-of-truth for structure/markers)."""
    root = workspace_root if workspace_root is not None else _repo_root_from_eval_file()
    return root / "canvases"


def ensure_canvas_file_for_patch(canvas_path: Path, *, workspace_root: Path | None = None) -> Path:
    """Prepare ``canvas_path`` for marker-based patching.

    - Creates the parent directory (typically ``.../canvases/``) if missing.
    - If the file does not exist yet, copies from ``repo_canvases_dir()/canvas_path.name``
      when that template exists (keeps IDE-managed path in sync with repo canvases).

    Returns the resolved path. Raises ``FileNotFoundError`` if the file is missing and
    no repo template exists.
    """
    path = canvas_path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return path
    src = repo_canvases_dir(workspace_root) / path.name
    if not src.is_file():
        raise FileNotFoundError(
            f"Canvas file {path} does not exist and no repo template at {src}. "
            "Add the .canvas.tsx under canvases/ in the repo, or create the file at the target path."
        )
    shutil.copy2(src, path)
    return path
