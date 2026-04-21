"""Build a tmpdir corpus snapshot: Stage-1 recap pinned from gold; Lysandra timeline without Session 20 row."""

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


def remove_timeline_session_row(text: str, session: int) -> str:
    pattern = re.compile(rf"^\| \*\*{session}\*\* \|[^\n]*\n?", re.MULTILINE)
    return pattern.sub("", text)


def apply_pre_state_manifest(corpus_root: Path, manifest: dict[str, Any]) -> None:
    for spec in manifest.get("remove_table_row_session_in", []):
        path = corpus_root / str(spec["path"]).strip("/")
        if path.is_file():
            sess = int(spec["session"])
            path.write_text(
                remove_timeline_session_row(path.read_text(encoding="utf-8"), sess),
                encoding="utf-8",
            )

    for spec in manifest.get("copy_into_corpus", []):
        src_rel = str(spec["src_relative_to_slice"]).strip()
        dst_rel = str(spec["dst_relative_to_corpus"]).strip("/")
        src = (_SLICE_DIR / src_rel).resolve()
        dst = corpus_root / dst_rel
        if not src.is_file():
            raise FileNotFoundError(f"pre-state copy source missing: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def build_pre_state_corpus(
    *,
    repo_root: Path | None = None,
    manifest: dict[str, Any] | None = None,
    tmp_dir: Path | None = None,
) -> Path:
    """Copy ``corpus/eldyrwild-markdown`` to a temp dir and apply the Stage-2 manifest.

    Order: full corpus copy → strip Session 20 timeline row (if present) → copy gold recap
    into place (pins Stage-1 artifact bytes).
    """
    repo = repo_root or _REPO_ROOT
    src = (repo / "corpus" / "eldyrwild-markdown").resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"corpus source missing: {src}")

    man = manifest or load_pre_state_manifest()
    if tmp_dir is not None:
        dst = tmp_dir
        dst.mkdir(parents=True, exist_ok=True)
        root = dst / "eldyrwild-markdown"
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(src, root)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="session_timeline_append_pre_state_"))
        root = tmp / "eldyrwild-markdown"
        shutil.copytree(src, root)

    apply_pre_state_manifest(root, man)
    return root.resolve()
