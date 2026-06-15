from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.ingestion.frontmatter import FrontmatterParseError, split_frontmatter

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

_HEADING_RE = re.compile(r"^#\s+(.+)$", re.M)
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


def _parse_scalar(raw: str) -> str | int | None:
    value = raw.strip()
    if value in {"", "null", "NULL", "None", "none", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def _parse_loose_frontmatter_block(block: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") and ":" not in stripped:
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip().lstrip("#").strip()
        if key:
            payload[key] = _parse_scalar(raw_value)
    return payload


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _title_from_body(body: str) -> str | None:
    match = _HEADING_RE.search(body)
    if not match:
        return None
    return match.group(1).strip()


def _dice_from_text(*values: str | None) -> str | None:
    for value in values:
        if not value:
            continue
        match = _DICE_RE.search(value)
        if match:
            return match.group("dice").lower()
    return None


def _display_path(root: Path, path: Path) -> str:
    return path.relative_to(root.resolve()).as_posix()


def _safe_under(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _mtime_iso(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


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
            frontmatter = _parse_loose_frontmatter_block(block)
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
