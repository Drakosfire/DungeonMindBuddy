#!/usr/bin/env python3
"""Split multi-session recap markdown and apply document_metadata frontmatter across corpus."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingestion.frontmatter import (  # noqa: E402
    DocumentMetadata,
    FrontmatterError,
    parse_document_frontmatter,
    split_frontmatter,
    write_document_with_frontmatter,
)


CORPUS = ROOT / "corpus" / "eldyrwild-markdown"


def safe_slug(s: str, max_len: int = 80) -> str:
    s = s.replace("/", "-")
    for c in '<>:"\\|?*':
        s = s.replace(c, "")
    s = re.sub(r"\s+", " ", s).strip(" .")
    return (s[:max_len]).rstrip(".")


def write_play(path: Path, *, session: int, title: str, body: str, campaign_id: str) -> None:
    meta = DocumentMetadata(
        title=title,
        document_class="play",
        canon_layer="campaign",
        campaign_id=campaign_id,
        session=session,
        source_class="observed_session_recap",
    )
    b = body.strip()
    if not b.endswith("\n"):
        b += "\n"
    write_document_with_frontmatter(path, metadata=meta, body=b)


def write_reference(path: Path, *, title: str, body: str, campaign_id: str) -> None:
    meta = DocumentMetadata(
        title=title,
        document_class="reference",
        canon_layer="campaign",
        campaign_id=campaign_id,
        session=None,
        source_class="ledger_or_dossier",
    )
    b = body.strip()
    if not b.endswith("\n"):
        b += "\n"
    write_document_with_frontmatter(path, metadata=meta, body=b)


def write_world(path: Path, *, title: str, body: str) -> None:
    meta = DocumentMetadata(
        title=title,
        document_class="world",
        canon_layer="world",
        campaign_id=None,
        session=None,
        source_class="seed_reference",
    )
    b = body.strip()
    if not b.endswith("\n"):
        b += "\n"
    write_document_with_frontmatter(path, metadata=meta, body=b)


def write_planning(path: Path, *, title: str, body: str, campaign_id: str, session: int | None) -> None:
    meta = DocumentMetadata(
        title=title,
        document_class="planning",
        canon_layer="campaign",
        campaign_id=campaign_id,
        session=session,
        source_class="planning_document",
    )
    b = body.strip()
    if not b.endswith("\n"):
        b += "\n"
    write_document_with_frontmatter(path, metadata=meta, body=b)


def write_reference_other(path: Path, *, title: str, body: str, campaign_id: str) -> None:
    meta = DocumentMetadata(
        title=title,
        document_class="reference",
        canon_layer="campaign",
        campaign_id=campaign_id,
        session=None,
        source_class="other",
    )
    b = body.strip()
    if not b.endswith("\n"):
        b += "\n"
    write_document_with_frontmatter(path, metadata=meta, body=b)


# --- Campaign 2 split ---

C2_HEADER = re.compile(r"(?m)^# Session (\d+)([^\n]*)$")


def split_campaign_2_recaps() -> list[Path]:
    src = CORPUS / "Longmont Campaign" / "Campaign 2" / "Campaign 2 Session Recaps.md"
    out_dir = CORPUS / "Longmont Campaign" / "Campaign 2" / "Session Recaps"
    out_dir.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    m2 = re.search(r"(?m)^# Session 2\b", text)
    if not m2:
        raise RuntimeError("Campaign 2: expected '# Session 2' heading")

    pre = text[: m2.start()]
    rest = text[m2.start() :]
    created: list[Path] = []

    # Session 1 (preamble before first # Session)
    s1_body = pre.strip()
    # Title from "Session 1: ..." first line of substance
    title_suffix = "Recap"
    for line in s1_body.splitlines():
        m = re.match(r"Session\s+1\s*:\s*(.+)", line.strip())
        if m:
            raw = m.group(1).strip()
            words = raw.split()
            head = " ".join(words[:6]) if len(words) > 6 else raw[:55]
            title_suffix = safe_slug(head, 60) or "Let the Games Begin"
            break
    p1 = out_dir / f"Session 1 - {safe_slug(title_suffix)}.md"
    write_play(p1, session=1, title=f"Session 1 - {title_suffix}", body=s1_body, campaign_id="longmont-c2")
    created.append(p1)

    matches = list(C2_HEADER.finditer(rest))
    for i, m in enumerate(matches):
        num = int(m.group(1))
        tail = (m.group(2) or "").strip().lstrip(":").strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(rest)
        chunk = rest[start:end].strip()

        # Split Session 16 / Session 17 (17 introduced by plain "Session 17 Recap:")
        if num == 16:
            split_m = re.search(r"(?m)^Session 17 Recap:\s*$", chunk)
            if split_m:
                chunk_16 = chunk[: split_m.start()].strip()
                chunk_17 = chunk[split_m.start() :].strip()
                t16 = tail or "Recap"
                p16 = out_dir / f"Session 16 - {safe_slug(t16)}.md"
                write_play(
                    p16,
                    session=16,
                    title=f"Session 16 - {t16}".strip(),
                    body=chunk_16,
                    campaign_id="longmont-c2",
                )
                created.append(p16)
                # Session 17 body includes the "Session 17 Recap:" line as heading — keep in body
                p17 = out_dir / "Session 17 - Migrating Forest and Thrin.md"
                write_play(
                    p17,
                    session=17,
                    title="Session 17 - Migrating Forest and Thrin",
                    body=chunk_17,
                    campaign_id="longmont-c2",
                )
                created.append(p17)
                continue

        if num == 17:
            # Already emitted from 16-split
            continue

        short = safe_slug(tail, 50) if tail else "Recap"
        title = f"Session {num} - {tail}".strip() if tail else f"Session {num} - Recap"
        outp = out_dir / f"Session {num} - {short}.md"
        write_play(outp, session=num, title=title, body=chunk, campaign_id="longmont-c2")
        created.append(outp)

    index_body = (
        "# Campaign 2 session recaps (index)\n\n"
        "Per-session play documents live in this folder as `Session N - *.md`. "
        "This file replaces the former combined `Campaign 2 Session Recaps.md` for ingestion.\n"
    )
    write_reference(
        src,
        title="Campaign 2 Session Recaps (index)",
        body=index_body,
        campaign_id="longmont-c2",
    )
    return created


# --- Campaign 1 General Notes split ---

SESSION_MARKERS = [
    re.compile(r"^### Session (\d+)\s*(.*)$"),
    re.compile(r"^## Session (\d+):\s*(.*)$"),
    re.compile(r"^## Session (\d+)\s*$"),
    re.compile(r"^Session (\d+):\s*(.*)$"),
]


def parse_c1_marker(line: str) -> tuple[int, str, str] | None:
    for cre in SESSION_MARKERS:
        m = cre.match(line)
        if not m:
            continue
        sn = int(m.group(1))
        tail = ""
        if m.lastindex is not None and m.lastindex >= 2:
            tail = (m.group(2) or "").strip().lstrip(":").strip()
        return sn, tail, line
    return None


def split_campaign_1_general_notes() -> list[Path]:
    src = CORPUS / "Longmont Campaign" / "Campaign 1" / "Longmont Campaign General Notes.md"
    raw = src.read_text(encoding="utf-8")
    meta, body = parse_document_frontmatter(raw)
    if meta is None:
        raise RuntimeError("General Notes: expected YAML frontmatter")
    lines = body.splitlines(keepends=True)
    markers: list[tuple[int, int, int, str, str]] = []
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        parsed = parse_c1_marker(stripped)
        if parsed:
            sn, tail, full = parsed
            markers.append((i, sn, tail, full))

    out_dir = CORPUS / "Longmont Campaign" / "Campaign 1" / "Session Recaps"
    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    i = 0
    while i < len(markers):
        start_line, sess, tail, full = markers[i]
        if sess == 8:
            j = i + 1
            while j < len(markers) and markers[j][1] < 9:
                j += 1
            i = j
            continue
        end_line = len(lines)
        if i + 1 < len(markers):
            end_line = markers[i + 1][0]
        chunk = "".join(lines[start_line:end_line]).strip()
        short = safe_slug(tail, 50) if tail else "Recap"
        title = f"Session {sess} - {tail}".strip() if tail else f"Session {sess} - Recap"
        outp = out_dir / f"Session {sess} - {short}.md"
        if sess != 8:
            write_play(outp, session=sess, title=title, body=chunk, campaign_id="longmont-c1")
            created.append(outp)
        i += 1

    # Trim General Notes: keep content before first session marker
    first_session = markers[0][0] if markers else len(lines)
    kept = "".join(lines[:first_session]).rstrip() + "\n"
    index_tail = (
        "\n## Session recap documents\n\n"
        "Session play recaps are stored under `Session Recaps/` as one file per session. "
        "Session 8 player recap: `Session Recaps/Session 8 - Captain Lysandra Quest.md`.\n"
    )
    new_body = kept + index_tail
    write_reference(
        src,
        title="Longmont Campaign General Notes",
        body=new_body,
        campaign_id="longmont-c1",
    )
    return created


def infer_metadata(path: Path, body: str) -> DocumentMetadata:
    p = str(path)
    lower = p.lower()
    stem = path.stem.replace("_", " ").strip() or "Untitled"

    if "longmont campaign" not in lower:
        title = stem
        if body.strip().startswith("#"):
            first = body.strip().splitlines()[0].lstrip("#").strip()
            if first:
                title = first[:200]
        return DocumentMetadata(
            title=title,
            document_class="world",
            canon_layer="world",
            campaign_id=None,
            session=None,
            source_class="seed_reference",
        )

    campaign_id = "longmont-c1" if "campaign 1" in lower else "longmont-c2"
    bdir = path.parent.name.lower()

    if "session prep" in lower or bdir == "session prep":
        sess = None
        m = re.search(r"session\s+(\d+)", stem, re.I) or re.search(
            r"session\s+(\d+)", body[:800], re.I
        )
        if m:
            sess = int(m.group(1))
        return DocumentMetadata(
            title=stem,
            document_class="planning",
            canon_layer="campaign",
            campaign_id=campaign_id,
            session=sess,
            source_class="planning_document",
        )

    if "session recaps" in lower or "session recaps" in str(path.parent).lower():
        m = re.search(r"session\s+(\d+)", stem, re.I) or re.search(
            r"session\s+(\d+)", body[:1200], re.I
        )
        sess = int(m.group(1)) if m else None
        if sess is not None:
            return DocumentMetadata(
                title=stem,
                document_class="play",
                canon_layer="campaign",
                campaign_id=campaign_id,
                session=sess,
                source_class="observed_session_recap",
            )

    if re.search(r"session\s+\d+", stem, re.I) and (
        "recap" in stem.lower() or "session" in stem.lower()
    ):
        m = re.search(r"session\s+(\d+)", stem, re.I)
        if m:
            return DocumentMetadata(
                title=stem,
                document_class="play",
                canon_layer="campaign",
                campaign_id=campaign_id,
                session=int(m.group(1)),
                source_class="observed_session_recap",
            )

    if "npc" in lower and "dossier" in lower:
        return DocumentMetadata(
            title=stem,
            document_class="reference",
            canon_layer="campaign",
            campaign_id=campaign_id,
            session=None,
            source_class="other",
        )

    if "homebrew" in lower or "item" in lower or "trinket" in lower or "cards" in lower:
        src_cls = "other" if "player copy" in lower or "layout" in lower else "ledger_or_dossier"
        return DocumentMetadata(
            title=stem,
            document_class="reference",
            canon_layer="campaign",
            campaign_id=campaign_id,
            session=None,
            source_class=src_cls,
        )

    if "character" in lower and "docs" in lower:
        return DocumentMetadata(
            title=stem,
            document_class="reference",
            canon_layer="campaign",
            campaign_id=campaign_id,
            session=None,
            source_class="other",
        )

    if "mirathorn" in lower and "battle" in lower and "wolf" in lower:
        return DocumentMetadata(
            title=stem,
            document_class="play",
            canon_layer="campaign",
            campaign_id=campaign_id,
            session=8,
            source_class="observed_session_recap",
        )

    return DocumentMetadata(
        title=stem,
        document_class="reference",
        canon_layer="campaign",
        campaign_id=campaign_id,
        session=None,
        source_class="ledger_or_dossier",
    )


def frontmatter_pass_all() -> tuple[int, int, list[Path]]:
    updated = 0
    skipped = 0
    paths: list[Path] = []
    for md in sorted(CORPUS.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        try:
            meta, body = parse_document_frontmatter(text)
        except FrontmatterError:
            block, rest = split_frontmatter(text)
            body = rest if block is not None else text
            meta = None
        if meta is not None:
            skipped += 1
            continue
        inferred = infer_metadata(md, body)
        write_document_with_frontmatter(md, metadata=inferred, body=body)
        updated += 1
        paths.append(md)
    return updated, skipped, paths


def patch_narrative_ledgers() -> None:
    campaign_id = "longmont-c2"
    for name, title in (
        ("Elderwyld_Narrative_Ledger_2.md", "Elderwyld Narrative Ledger — Campaign 2 Living Record"),
        ("Elderwyld_Narrative_Ledger_Campaign2.md", "Elderwyld Narrative Ledger (Campaign 2)"),
    ):
        p = CORPUS / "Longmont Campaign" / "Campaign 2" / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        try:
            meta, body = parse_document_frontmatter(text)
        except FrontmatterError:
            block, rest = split_frontmatter(text)
            body = rest if block is not None else text
            meta = None
        if meta is not None:
            continue
        write_reference(
            p,
            title=title,
            body=body,
            campaign_id=campaign_id,
        )


def main() -> None:
    split_campaign_2_recaps()
    split_campaign_1_general_notes()
    dup = CORPUS / "Longmont Campaign" / "Campaign 2" / "Elderwyld_Narrative_Ledger_Campaign2.md(1).md"
    if dup.exists():
        dup.unlink()
    patch_narrative_ledgers()
    u, s, _ = frontmatter_pass_all()
    print(f"frontmatter_pass: updated={u} already_valid={s}")


if __name__ == "__main__":
    main()
