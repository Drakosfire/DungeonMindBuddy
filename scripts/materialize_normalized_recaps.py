"""One-shot: build `Session Recaps/_normalized/` prepared recaps from originals.

See Docs/CONVENTION-Session-Recap-Normalization.md and
Docs/Plans/INDEX-Recap-Normalization.md.

Prepared bodies intentionally exclude everything before the recap span (e.g.
## Major Beats, ## Next Beats, ## Loot, ## Into the Sewer, Looking Ahead).
That omission is policy—see CONVENTION section 6 (*Intentionally dropped
pre-recap chrome*).

Usage (from repo root):
  uv run python scripts/materialize_normalized_recaps.py

Writes via ``write_corpus_file`` (two-phase) after allowlist includes _normalized/.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from corpus.corpus_writer import write_corpus_file  # noqa: E402

from live_play.normalized_recaps import (  # noqa: E402
    _build_normalized_content,
    _clean_body,
    _extract_recap_raw,
    _parse_minimal_frontmatter,
    _slug_from_title,
)

_CORPUS = _REPO_ROOT / "corpus" / "eldyrwild-markdown"


def main() -> int:
    if not _CORPUS.is_dir():
        print(f"Missing corpus: {_CORPUS}", file=sys.stderr)
        return 2

    recaps: list[Path] = []
    for p in sorted(_CORPUS.rglob("*.md")):
        parts = p.parts
        if "Session Recaps" not in parts:
            continue
        if "_normalized" in parts:
            continue
        if p.parent.name != "Session Recaps":
            continue
        recaps.append(p)

    for src in recaps:
        text = src.read_text(encoding="utf-8")
        fm, body = _parse_minimal_frontmatter(text)
        cid = str(fm.get("campaign_id") or "").strip()
        sess = fm.get("session")
        if not cid or not isinstance(sess, int):
            print(f"skip (no campaign_id/session): {src.relative_to(_CORPUS)}")
            continue
        slug = _slug_from_title(str(fm.get("title") or ""), cid, sess)
        recap_raw, _ = _extract_recap_raw(body)
        body_clean = _clean_body(recap_raw)
        rel = src.resolve().relative_to(_CORPUS.resolve()).as_posix()
        nn = f"{sess:02d}"
        title = f"Session {sess} - {slug}"
        out_rel = (
            src.parent / "_normalized" / f"Session {nn} - {slug}.md"
        ).resolve().relative_to(_CORPUS.resolve()).as_posix()

        content = _build_normalized_content(
            fm=fm,
            body_clean=body_clean,
            session=sess,
            normalized_from=rel,
            title=title,
        )

        prev = write_corpus_file(_CORPUS, path=out_rel, mode="create", content=content, dry_run=True)
        if not prev.get("ok"):
            print(f"FAIL preview {out_rel}: {prev.get('error')}", file=sys.stderr)
            return 1
        tok = prev["confirm_token"]
        commit = write_corpus_file(
            _CORPUS,
            path=out_rel,
            mode="create",
            content=content,
            dry_run=False,
            confirm_token=tok,
        )
        if not commit.get("ok"):
            print(f"FAIL commit {out_rel}: {commit.get('error')}", file=sys.stderr)
            return 1
        print(f"OK {out_rel}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
