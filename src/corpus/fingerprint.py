"""Fingerprint corpus Markdown for cache invalidation."""

from pathlib import Path

import blake3


def is_managed_dungeonbuddy_storage(path: Path) -> bool:
    return "_dungeonbuddy" in path.parts


def corpus_fingerprint(corpus_dir: Path) -> str:
    """Stable hash over corpus markdown paths, mtimes, and sizes (invalidates on edits)."""
    root = corpus_dir.resolve()
    lines: list[str] = []
    if not root.is_dir():
        return blake3.blake3(b"").hexdigest()[:32]
    for path in sorted(root.rglob("*.md")):
        if is_managed_dungeonbuddy_storage(path):
            continue
        try:
            rel = path.relative_to(root).as_posix()
            st = path.stat()
            lines.append(f"{rel}\t{st.st_mtime_ns}\t{st.st_size}")
        except OSError:
            continue
    payload = "\n".join(lines).encode("utf-8")
    return blake3.blake3(payload).hexdigest()[:32]
