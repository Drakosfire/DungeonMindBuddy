"""Build a tmpdir corpus snapshot with Session 20 post-ingest artifacts removed."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

_SLICE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SLICE_DIR.parents[1]


def pre_state_manifest_path() -> Path:
    return _SLICE_DIR / "gold" / "step0_pre_state_manifest.json"


def load_pre_state_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or pre_state_manifest_path()
    return json.loads(p.read_text(encoding="utf-8"))


def strip_trailing_blockquote_section(text: str) -> str:
    """Remove a contiguous trailing blockquote region (lines starting with ``>``)."""
    ends_nl = text.endswith("\n")
    lines = text.splitlines()
    i = len(lines) - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0:
        return text
    if not lines[i].lstrip().startswith(">"):
        return text
    start_remove = i
    while start_remove >= 0:
        ln = lines[start_remove]
        if not ln.strip():
            start_remove -= 1
            continue
        if ln.lstrip().startswith(">"):
            start_remove -= 1
            continue
        break
    kept = lines[: start_remove + 1]
    out = "\n".join(kept)
    if ends_nl or kept:
        out += "\n"
    return out


def remove_timeline_session_row(text: str, session: int) -> str:
    pattern = re.compile(rf"^\| \*\*{session}\*\* \|[^\n]*\n?", re.MULTILINE)
    return pattern.sub("", text)


def apply_pre_state_manifest(corpus_root: Path, manifest: dict[str, Any]) -> None:
    for rel in manifest.get("delete", []):
        target = corpus_root / str(rel).strip("/")
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.is_file():
            target.unlink(missing_ok=True)

    for rel in manifest.get("remove_trailing_blockquote_in", []):
        path = corpus_root / str(rel).strip("/")
        if path.is_file():
            path.write_text(
                strip_trailing_blockquote_section(path.read_text(encoding="utf-8")),
                encoding="utf-8",
            )

    for spec in manifest.get("remove_table_row_session_in", []):
        path = corpus_root / str(spec["path"]).strip("/")
        if path.is_file():
            sess = int(spec["session"])
            path.write_text(
                remove_timeline_session_row(path.read_text(encoding="utf-8"), sess),
                encoding="utf-8",
            )


def build_pre_state_corpus(
    *,
    repo_root: Path | None = None,
    manifest: dict[str, Any] | None = None,
    tmp_dir: Path | None = None,
) -> Path:
    """Copy ``corpus/eldyrwild-markdown`` to a temp dir and apply the manifest.

    Returns the new corpus root (the copy root, same layout as the live corpus).
    """
    repo = repo_root or _REPO_ROOT
    src = (repo / "corpus" / "eldyrwild-markdown").resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"corpus source missing: {src}")

    man = manifest or load_pre_state_manifest()
    if tmp_dir is not None:
        dst = tmp_dir
        dst.mkdir(parents=True, exist_ok=True)
        # copytree requires dst not exist or empty - use a subdir
        root = dst / "eldyrwild-markdown"
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(src, root)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="session_recap_pre_state_"))
        root = tmp / "eldyrwild-markdown"
        shutil.copytree(src, root)

    apply_pre_state_manifest(root, man)
    return root.resolve()
