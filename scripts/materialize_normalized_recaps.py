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

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.agent.corpus_writer import write_corpus_file  # noqa: E402

_CORPUS = _REPO_ROOT / "corpus" / "eldyrwild-markdown"
_NORMALIZED_ON = "2026-05-08"
_SCHEMA = "dmb_recap_normalized_v1"

# (campaign_id, session) -> Title Case slug (filename + title tail)
_SLUGS: dict[tuple[str, int], str] = {
    ("longmont-c1", 1): "Stonebridge and Glowkindle Rats",
    ("longmont-c1", 9): "Battle with the Meat Monsters",
    ("longmont-c1", 10): "Thraxx and the Last Warehouse",
    ("longmont-c1", 12): "The Persistent Bugbear",
    ("longmont-c1", 15): "Cult Tunnels and Captain Idris",
    ("longmont-c1", 16): "Peacemaker Fiddle Meat Pile",
    ("longmont-c1", 17): "Festival Aftermath Loose Ends",
    ("longmont-c2", 2): "Steel Fangs Colosseum",
    ("longmont-c2", 3): "Storms Torbin and Shepherd",
    ("longmont-c2", 4): "Wolf Manor Mage Duel",
    ("longmont-c2", 5): "Lysandra Tea Guardhouse",
    ("longmont-c2", 6): "Barn Fleshborn Shepherd Wake",
    ("longmont-c2", 7): "Portals Tentacles Barn",
    ("longmont-c2", 8): "Dustwalker Cellar Barin Party",
    ("longmont-c2", 9): "Costume Contest Temple Aspitome",
    ("longmont-c2", 10): "Festival Crafting Elementals",
    ("longmont-c2", 11): "Coliseum Finals Tealeaf Tea",
    ("longmont-c2", 12): "Dustwalker Globe Duel",
    ("longmont-c2", 13): "Council Curfew Swamp March",
    ("longmont-c2", 14): "Supplies Wolf Crypt Letter",
    ("longmont-c2", 15): "Ride Out Mossford Ale",
    ("longmont-c2", 16): "Thinking Tree Sneaking Forest",
    ("longmont-c2", 18): "Wyvern Mother Fallen Spine",
    ("longmont-c2", 19): "Mossford Plans Stuart Inn",
    ("longmont-c2", 20): "Gnat Swarm Marla Lysandra",
}

_RECAP_LINE_RE = re.compile(
    r"^("
    r"\s{0,3}#{1,6}\s*Recap\s*:?\s*"
    r"|\s*Recap\s*:\s*"
    r"|\s*\*\*Recap\*\*\s*:?\s*"
    r"|\s*\*\*Recap:\s*"
    r")$",
    re.IGNORECASE,
)
_SESSION_TITLE_ONLY_RE = re.compile(
    r"^#{1,6}\s*Session\s+\d+.*$", re.IGNORECASE
)


def _parse_minimal_frontmatter(text: str) -> tuple[dict[str, str | int | None], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return {}, text
    payload: dict[str, str | int | None] = {}
    for raw in lines[1:end_idx]:
        s = raw.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        key, _, value = s.partition(":")
        key = key.strip()
        value = value.strip()
        if value in {"", "null", "NULL", "None", "none", "~"}:
            payload[key] = None
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        elif value.lstrip("-").isdigit():
            try:
                payload[key] = int(value)
                continue
            except ValueError:
                pass
        payload[key] = value
    body = "\n".join(lines[end_idx + 1 :])
    return payload, body


def _slug_from_title(title: str, campaign_id: str, session: int) -> str:
    key = (campaign_id, session)
    if key in _SLUGS:
        return str(_SLUGS[key])
    t = str(title or "").strip()
    m = re.match(r"^Session\s+\d+\s*-\s*(.+)$", t, re.I)
    if m:
        t = m.group(1).strip()
    t = re.sub(r":+\s*$", "", t).strip()
    if re.match(r"^Recap:?$", t, re.I):
        raise ValueError(f"Generic recap title for {campaign_id} S{session}; add _SLUGS entry")
    if not t:
        raise ValueError(f"Unresolved slug for {campaign_id} S{session}")
    return t


def _extract_recap_raw(body: str) -> tuple[str, bool]:
    """Return recap text (no outer H1 title-only line) and whether **-prefix strip needed."""
    lines = body.split("\n")
    start = 0
    found_marker = False
    strip_bold_prefix = False
    for idx, line in enumerate(lines):
        s = line.strip()
        if _RECAP_LINE_RE.match(s) or s == "**Recap:":
            start = idx + 1
            found_marker = True
            if "**Recap" in line and ":**" not in line and not line.strip().endswith("**"):
                strip_bold_prefix = True
            break
    if not found_marker:
        # Whole body; drop leading # Session … line if present
        chunk_lines = lines[:]
        i = 0
        while i < len(chunk_lines) and not chunk_lines[i].strip():
            i += 1
        if i < len(chunk_lines) and _SESSION_TITLE_ONLY_RE.match(chunk_lines[i].strip()):
            i += 1
        while i < len(chunk_lines) and not chunk_lines[i].strip():
            i += 1
        chunk = "\n".join(chunk_lines[i:])
    else:
        chunk = "\n".join(lines[start:])
    if strip_bold_prefix:
        ls = chunk.split("\n")
        for j, ln in enumerate(ls):
            if ln.strip():
                if ln.lstrip().startswith("**"):
                    ls[j] = re.sub(r"^\s*\*\*", "", ln, count=1)
                break
        chunk = "\n".join(ls)
    return chunk.strip("\n"), strip_bold_prefix


def _strip_md_headings(text: str) -> str:
    out_lines: list[str] = []
    for line in text.split("\n"):
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _clean_body(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = _strip_md_headings(text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _yaml_scalar(key: str, v: str | int | None) -> str:
    if v is None:
        return f"{key}: null"
    if isinstance(v, int):
        return f"{key}: {v}"
    s = str(v)
    if "\n" in s:
        raise ValueError(f"multiline frontmatter value for {key}")
    if re.search(r'[:#"\'\[\]{}]', s) or s.strip() != s:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'{key}: "{escaped}"'
    return f"{key}: {s}"


def _format_frontmatter_merged(
    fm: dict[str, str | int | None],
    *,
    title: str,
    normalized_from: str,
) -> str:
    merged: dict[str, str | int | None] = dict(fm)
    merged["title"] = title
    merged["subject_class"] = None
    merged["subject_doc_kind"] = "recap"
    merged["normalized_from"] = normalized_from
    merged["normalized_on"] = _NORMALIZED_ON
    merged["normalization_schema"] = _SCHEMA

    priority = [
        "title",
        "document_class",
        "canon_layer",
        "campaign_id",
        "temporal_scope",
        "session",
        "origin_session",
        "last_updated_session",
        "source_class",
        "subject_class",
        "subject_doc_kind",
        "normalized_from",
        "normalized_on",
        "normalization_schema",
    ]
    lines_out = ["---"]
    seen: set[str] = set()
    for k in priority:
        if k not in merged:
            continue
        lines_out.append(_yaml_scalar(k, merged[k]))
        seen.add(k)
    for k in sorted(merged.keys()):
        if k in seen:
            continue
        lines_out.append(_yaml_scalar(k, merged[k]))
    lines_out.append("---")
    return "\n".join(lines_out) + "\n"


def _build_normalized_content(
    *,
    fm: dict[str, str | int | None],
    body_clean: str,
    session: int,
    normalized_from: str,
    title: str,
) -> str:
    h1 = f"# Session {session} Recap"
    narrative = body_clean.strip()
    body = f"{h1}\n\n{narrative}\n"
    return _format_frontmatter_merged(fm, title=title, normalized_from=normalized_from) + body


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
