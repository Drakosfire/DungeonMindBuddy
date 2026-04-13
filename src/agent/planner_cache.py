"""Cache planner system instructions (corpus manifest + template) keyed by corpus fingerprint."""

from __future__ import annotations

import json
from pathlib import Path
import blake3

from src.agent.planner import _build_system_prompt, build_corpus_manifest


def corpus_fingerprint(corpus_dir: Path) -> str:
    """Stable hash over corpus markdown paths, mtimes, and sizes (invalidates on edits)."""
    root = corpus_dir.resolve()
    lines: list[str] = []
    if not root.is_dir():
        return blake3.blake3(b"").hexdigest()[:32]
    for path in sorted(root.rglob("*.md")):
        try:
            rel = path.relative_to(root).as_posix()
            st = path.stat()
            lines.append(f"{rel}\t{st.st_mtime_ns}\t{st.st_size}")
        except OSError:
            continue
    payload = "\n".join(lines).encode("utf-8")
    return blake3.blake3(payload).hexdigest()[:32]


def cache_dir_for_corpus(cache_root: Path, corpus_dir: Path) -> Path:
    fp = corpus_fingerprint(corpus_dir)
    return (cache_root / fp).resolve()


def load_or_build_planner_instructions(
    corpus_dir: Path,
    *,
    cache_root: Path | None = None,
) -> tuple[str, str]:
    """
    Return ``(instructions, fingerprint)`` for ``responses.create(instructions=...)``.

    Caches under ``cache_root`` (default ``out/planner_eval_cache``) so repeated eval
    sessions skip rebuilding the manifest tree.
    """
    root = Path(cache_root or Path("out/planner_eval_cache"))
    bucket = cache_dir_for_corpus(root, corpus_dir)
    bucket.mkdir(parents=True, exist_ok=True)
    fp = corpus_fingerprint(corpus_dir)
    inst_path = bucket / "instructions.txt"
    meta_path = bucket / "meta.json"

    if inst_path.is_file() and meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if str(meta.get("fingerprint")) == fp and str(meta.get("corpus_root")) == str(
                corpus_dir.resolve()
            ):
                return inst_path.read_text(encoding="utf-8"), fp
        except (OSError, json.JSONDecodeError):
            pass

    manifest = build_corpus_manifest(corpus_dir)
    instructions = _build_system_prompt(manifest)
    inst_path.write_text(instructions, encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "fingerprint": fp,
                "corpus_root": str(corpus_dir.resolve()),
                "format": "planner_instructions_v1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return instructions, fp


def session_cache_key(scenario_id: str, corpus_fp: str) -> str:
    """Key for eval session artifacts (scenario + corpus fingerprint)."""
    return f"{scenario_id}__{corpus_fp}"
