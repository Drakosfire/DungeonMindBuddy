"""Cache planner system instructions (corpus manifest + template) keyed by corpus fingerprint."""

from __future__ import annotations

import json
import os
from pathlib import Path

import blake3

from src.agent.planner import (
    PLANNER_MANIFEST_BUILDER_ID,
    _build_system_prompt,
    _is_managed_dungeonbuddy_storage,
    build_corpus_manifest,
)
from src.prompts.corpus_session_planner import INSTRUCTIONS_TEMPLATE_ID


def corpus_fingerprint(corpus_dir: Path) -> str:
    """Stable hash over corpus markdown paths, mtimes, and sizes (invalidates on edits)."""
    root = corpus_dir.resolve()
    lines: list[str] = []
    if not root.is_dir():
        return blake3.blake3(b"").hexdigest()[:32]
    for path in sorted(root.rglob("*.md")):
        if _is_managed_dungeonbuddy_storage(path):
            continue
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


def _env_file_stat_token(env_var: str) -> str:
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return ""
    path = Path(raw)
    if not path.is_file():
        return ""
    st = path.stat()
    return f"{st.st_mtime_ns}:{st.st_size}"


def load_or_build_planner_instructions(
    corpus_dir: Path,
    *,
    cache_root: Path | None = None,
    include_write_tools: bool = False,
) -> tuple[str, str]:
    """
    Return ``(instructions, fingerprint)`` for ``responses.create(instructions=...)``.

    Caches under ``cache_root`` (default ``out/planner_eval_cache``) so repeated eval
    sessions skip rebuilding the manifest tree. ``include_write_tools`` selects the
    instruction variant that documents the corpus-write tools; the cache uses a
    distinct file suffix so writes-on/off variants don't clobber each other.
    """
    root = Path(cache_root or Path("out/planner_eval_cache"))
    bucket = cache_dir_for_corpus(root, corpus_dir)
    bucket.mkdir(parents=True, exist_ok=True)
    fp = corpus_fingerprint(corpus_dir)
    suffix = "_writes_on" if include_write_tools else ""
    inst_path = bucket / f"instructions{suffix}.txt"
    meta_path = bucket / f"meta{suffix}.json"

    session_memory_fp = _env_file_stat_token("DUNGEONMIND_SESSION_MEMORY_RECORDS_JSONL")
    memory_capsule_fp = _env_file_stat_token("DUNGEONMIND_PLANNER_MEMORY_CAPSULE_PATH")

    if inst_path.is_file() and meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if (
                str(meta.get("fingerprint")) == fp
                and str(meta.get("corpus_root")) == str(corpus_dir.resolve())
                and str(meta.get("instructions_template_id", "")) == INSTRUCTIONS_TEMPLATE_ID
                and str(meta.get("manifest_builder_id", "")) == PLANNER_MANIFEST_BUILDER_ID
                and bool(meta.get("include_write_tools", False)) == bool(include_write_tools)
                and str(meta.get("session_memory_records_fp", "")) == session_memory_fp
                and str(meta.get("memory_capsule_fp", "")) == memory_capsule_fp
            ):
                return inst_path.read_text(encoding="utf-8"), fp
        except (OSError, json.JSONDecodeError):
            pass

    manifest = build_corpus_manifest(corpus_dir)
    instructions = _build_system_prompt(manifest, include_write_tools=include_write_tools)
    inst_path.write_text(instructions, encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "fingerprint": fp,
                "corpus_root": str(corpus_dir.resolve()),
                "format": "planner_instructions_v1",
                "instructions_template_id": INSTRUCTIONS_TEMPLATE_ID,
                "manifest_builder_id": PLANNER_MANIFEST_BUILDER_ID,
                "include_write_tools": bool(include_write_tools),
                "session_memory_records_fp": session_memory_fp,
                "memory_capsule_fp": memory_capsule_fp,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return instructions, fp


def session_cache_key(scenario_id: str, corpus_fp: str) -> str:
    """Key for eval session artifacts (scenario + corpus fingerprint)."""
    return f"{scenario_id}__{corpus_fp}"
