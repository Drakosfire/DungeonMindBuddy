"""Resolve Cursor IDE-managed canvas file paths (``~/.cursor/projects/<slug>/canvases/``).

Cursor stores workspace-local canvases under a directory derived from the absolute
workspace root. This matches the layout described in ``.cursor/skills-cursor/canvas/SKILL.md``.

Override the **canvases directory** (not a single file) with env ``DMB_CURSOR_CANVAS_DIR``
if your Cursor install uses a different layout.

Emitters default to :func:`default_cursor_canvas_path` (IDE-managed ``.../canvases/``). Before patching,
:func:`ensure_canvas_file_for_patch` creates the parent directory if missing. The target file must
already exist (create it once in Cursor from the canvas template, or pass ``--canvas-tsx`` to an
existing path); there is **no** repo-local ``canvases/`` bootstrap copy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


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


def ensure_canvas_file_for_patch(canvas_path: Path) -> Path:
    """Prepare ``canvas_path`` for marker-based patching.

    - Creates the parent directory (typically ``.../canvases/``) if missing.
    - If the file does not exist, raises ``FileNotFoundError`` with guidance to create the canvas
      in Cursor or pass an explicit ``--canvas-tsx`` path.

    Returns the resolved path.
    """
    path = canvas_path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return path
    raise FileNotFoundError(
        f"Canvas file {path} does not exist. Create it in Cursor (canvas view) or pass "
        f"--canvas-tsx to an existing .canvas.tsx. Default directory: {path.parent} "
        f"(override parent with DMB_CURSOR_CANVAS_DIR)."
    )



def replace_generated_block(
    text: str, block: str, *, begin: str, end: str
) -> str:
    """Replace one ordered marker pair, preserving all surrounding text."""
    if begin not in text or end not in text:
        raise ValueError(f"canvas is missing the generated-block markers ({begin!r} / {end!r})")
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(f"Expected one generated block marker pair ({begin!r} / {end!r})")
    start = text.index(begin)
    stop = text.index(end)
    if stop < start:
        raise ValueError("Generated block end marker precedes its begin marker")
    return text[:start] + block + text[stop + len(end):]


def patch_candidate_canvas_paths(
    block: str, paths: list[Path], *, begin: str, end: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for canvas_path in paths:
        p = canvas_path.expanduser().resolve()
        try:
            ensure_canvas_file_for_patch(p)
            text = p.read_text(encoding="utf-8")
        except OSError as exc:
            out.append({"path": str(p), "error": f"{type(exc).__name__}: {exc}"})
            continue
        if begin not in text or end not in text:
            out.append(
                {
                    "path": str(p),
                    "error": f"ValueError: Canvas must contain {begin!r} and {end!r}",
                }
            )
            continue
        pre, rest = text.split(begin, 1)
        _mid, post = rest.split(end, 1)
        if post.startswith("\n\n"):
            post = post[1:]
        new_text = pre + block + post
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            out.append({"canvas_updated": str(p)})
        else:
            out.append({"canvas_unchanged": str(p)})
    return out
