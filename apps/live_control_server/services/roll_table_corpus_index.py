from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.live_control_server.services.corpus_index_helpers import (
    _display_path,
    _mtime_iso,
    _safe_under,
    _text_value,
    _title_from_body,
    parse_loose_frontmatter,
)
from ingestion.frontmatter import FrontmatterParseError, split_frontmatter

CORPUS_MARKDOWN_ROOT = Path("corpus") / "eldyrwild-markdown"
SCHEMA_VERSION = "dmb_roll_table_corpus_index_v1"

SESSION_22_PREP_REL = Path("Longmont Campaign/Campaign 2/Session Prep/session_22")
ROADS_REL = Path("Elderwyld/Roads")
WILDERNESS_REL = Path("Elderwyld/Wilderness")
MIREWARD_SCAFFOLD_REL = Path(
    "Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md"
)

RollTableIndexSection = Literal[
    "session_22",
    "mireward_scaffold",
    "roads",
    "wilderness",
]

_DICE_RE = re.compile(r"(?<![a-z0-9])(?P<dice>d(?:4|6|8|10|12|20|100))(?![a-z0-9])", re.I)


class RollTableCorpusIndexItem(BaseModel):
    index_id: str
    title: str
    section: RollTableIndexSection
    corpus_display_path: str
    table_id: str | None = None
    dice: str | None = None
    table_note: str | None = None
    document_class: str | None = None
    source_class: str | None = None
    campaign_id: str | None = None
    session: int | None = None
    embed_start: str | None = None
    embed_end: str | None = None
    updated_at: str | None = None


class RollTableCorpusIndexResponse(BaseModel):
    schema_version: Literal["dmb_roll_table_corpus_index_v1"] = SCHEMA_VERSION
    roll_tables: list[RollTableCorpusIndexItem]
    diagnostics: list[str] = Field(default_factory=list)


def _dice_from_text(*values: str | None) -> str | None:
    for value in values:
        if not value:
            continue
        match = _DICE_RE.search(value)
        if match:
            return match.group("dice").lower()
    return None


def _index_id_from_path(section: RollTableIndexSection, corpus_display_path: str) -> str:
    slug = Path(corpus_display_path).stem.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", slug).strip("-") or "roll-table"
    return f"{section}-{cleaned}"


def _read_markdown_with_frontmatter(
    path: Path,
) -> tuple[dict[str, Any], str, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, "", f"{path.name}: could not read file ({exc})"

    frontmatter: dict[str, Any] = {}
    body = text
    try:
        block, body = split_frontmatter(text)
        if block is not None:
            frontmatter = parse_loose_frontmatter(block, allow_commented_fields=True)
    except FrontmatterParseError:
        pass
    return frontmatter, body, None


def _parse_roll_table_file(
    path: Path,
    *,
    repo_root: Path,
    corpus_root: Path,
    section: RollTableIndexSection,
) -> tuple[RollTableCorpusIndexItem | None, str | None]:
    if not _safe_under(corpus_root, path):
        return None, f"{path.name}: path escaped corpus root"

    frontmatter, body, error = _read_markdown_with_frontmatter(path)
    if error:
        return None, error

    title = (
        _text_value(frontmatter.get("title"))
        or _title_from_body(body)
        or path.stem.replace("_", " ").title()
    )
    dice = _text_value(frontmatter.get("dice")) or _dice_from_text(path.name, title, body[:500])
    display_path = _display_path(repo_root, path)

    session_raw = frontmatter.get("session")
    session: int | None
    if isinstance(session_raw, int):
        session = session_raw
    elif isinstance(session_raw, str) and session_raw.isdigit():
        session = int(session_raw)
    else:
        session = None

    return (
        RollTableCorpusIndexItem(
            index_id=_index_id_from_path(section, display_path),
            title=title,
            section=section,
            corpus_display_path=display_path,
            table_id=_text_value(frontmatter.get("table_id")),
            dice=dice,
            table_note=_text_value(frontmatter.get("table_note")),
            document_class=_text_value(frontmatter.get("document_class")),
            source_class=_text_value(frontmatter.get("source_class")),
            campaign_id=_text_value(frontmatter.get("campaign_id")),
            session=session,
            updated_at=_mtime_iso(path),
        ),
        None,
    )


def _is_roll_table_candidate(path: Path) -> bool:
    name = path.name.lower()
    if name == "readme.md":
        return False
    return bool(_DICE_RE.search(name) or "table" in name)


def _collect_directory(
    *,
    repo_root: Path,
    corpus_root: Path,
    section_dir: Path,
    section: RollTableIndexSection,
) -> tuple[list[RollTableCorpusIndexItem], list[str]]:
    items: list[RollTableCorpusIndexItem] = []
    diagnostics: list[str] = []
    if not section_dir.is_dir():
        diagnostics.append(f"{section}: directory missing")
        return items, diagnostics

    for path in sorted(section_dir.glob("*.md")):
        if not _is_roll_table_candidate(path):
            continue
        item, error = _parse_roll_table_file(
            path,
            repo_root=repo_root,
            corpus_root=corpus_root,
            section=section,
        )
        if error:
            diagnostics.append(error)
            continue
        if item is not None:
            items.append(item)
    return items, diagnostics


def _build_mireward_scaffold_entry(
    *,
    repo_root: Path,
    corpus_root: Path,
) -> tuple[RollTableCorpusIndexItem | None, str | None]:
    path = corpus_root / MIREWARD_SCAFFOLD_REL
    if not path.is_file():
        return None, "mireward_scaffold: file missing"
    if not _safe_under(corpus_root, path):
        return None, "mireward_scaffold: path escaped corpus root"

    frontmatter, body, error = _read_markdown_with_frontmatter(path)
    if error:
        return None, error
    display_path = _display_path(repo_root, path)
    return (
        RollTableCorpusIndexItem(
            index_id="mireward-scaffold-on-the-fly-marcher-kit",
            title="North-Gate Refugee Improvisation Kit",
            section="mireward_scaffold",
            corpus_display_path=display_path,
            dice="mixed",
            table_note="Excerpt: roll or pick marcher role, eyes, hook, need, voice, and name.",
            document_class=_text_value(frontmatter.get("document_class")),
            source_class=_text_value(frontmatter.get("source_class")),
            campaign_id=_text_value(frontmatter.get("campaign_id")),
            embed_start="### On-the-fly marcher kit",
            embed_end="### Scene affordances",
            updated_at=_mtime_iso(path),
        ),
        None,
    )


def _section_sort_key(item: RollTableCorpusIndexItem) -> tuple[str, str]:
    return (item.title.lower(), item.dice or "")


def build_roll_table_corpus_index(*, root: Path) -> RollTableCorpusIndexResponse:
    repo_root_resolved = root.resolve()
    corpus_root = (root / CORPUS_MARKDOWN_ROOT).resolve()
    items: list[RollTableCorpusIndexItem] = []
    diagnostics: list[str] = []

    for section, rel_path in (
        ("session_22", SESSION_22_PREP_REL),
        ("roads", ROADS_REL),
        ("wilderness", WILDERNESS_REL),
    ):
        section_items, section_diagnostics = _collect_directory(
            repo_root=repo_root_resolved,
            corpus_root=corpus_root,
            section_dir=corpus_root / rel_path,
            section=section,
        )
        items.extend(section_items)
        diagnostics.extend(section_diagnostics)

    scaffold_item, scaffold_error = _build_mireward_scaffold_entry(
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
    )
    if scaffold_error:
        diagnostics.append(scaffold_error)
    if scaffold_item is not None:
        items.append(scaffold_item)

    ordered: list[RollTableCorpusIndexItem] = []
    for section in ("session_22", "mireward_scaffold", "roads", "wilderness"):
        ordered.extend(
            sorted(
                [item for item in items if item.section == section],
                key=_section_sort_key,
            )
        )

    return RollTableCorpusIndexResponse(
        roll_tables=ordered,
        diagnostics=diagnostics,
    )
