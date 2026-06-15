from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.ingestion.frontmatter import FrontmatterParseError, split_frontmatter

CORPUS_MARKDOWN_ROOT = Path("corpus") / "eldyrwild-markdown"
SCHEMA_VERSION = "dmb_statblock_corpus_index_v1"

SHEPHERDS_FLOCK_REL = (
    Path("Elderwyld")
    / "Shephards Flock"
    / "Statblocks and Tokens"
)
GENERATED_STATBLOCKS_REL = (
    Path("Longmont Campaign") / "Campaign 2" / "Statblocks" / "generated"
)

StatblockIndexSection = Literal["shepherds_flock", "generated"]

SHEPHERDS_FLOCK_ROLE_TAGS: dict[str, tuple[str, str]] = {
    "sewer_meat_creature_statblock_cr3.md": ("baseline", "pill-neutral"),
    "corrupted_meat_golem_statblock_cr3.md": ("bruiser", "pill-neutral"),
    "fleshborn_hybrid_statblock_cr3.md": ("shock troop", "pill-neutral"),
    "aberrant_meat_wing_statblock_cr1.md": ("skirmisher", "pill-neutral"),
    "meat_worm_statblock_cr_half.md": ("swarm pressure", "pill-neutral"),
    "shephards_flock_cultist_statblock_cr1.md": ("human minion", "pill-neutral"),
    "tripod_null_calf_statblock_cr5.md": ("alien scout", "pill-warn"),
    "latch_harrow_statblock_cr8.md": ("siege breaker", "pill-warn"),
}

SHEPHERDS_FLOCK_INFO_TAGS: dict[str, str] = {
    "sewer_meat_creature_statblock_cr3.md": "default herd / sewer meat thing",
    "corrupted_meat_golem_statblock_cr3.md": "anchor / hulk",
    "fleshborn_hybrid_statblock_cr3.md": "grapples / consume pressure",
    "aberrant_meat_wing_statblock_cr1.md": "flight / charm pressure",
    "meat_worm_statblock_cr_half.md": "cart wheels / civilian panic",
    "shephards_flock_cultist_statblock_cr1.md": "voice / fear / psychic pressure",
    "tripod_null_calf_statblock_cr5.md": "three-limbed geometry / mark the gate",
    "latch_harrow_statblock_cr8.md": "north-gate breach clock",
}

_CR_FILENAME_RE = re.compile(r"_statblock_cr(?P<cr>half|\d+(?:_\d+)?|\d+)", re.I)
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.M)


class StatblockCorpusIndexItem(BaseModel):
    index_id: str
    title: str
    corpus_display_path: str
    section: StatblockIndexSection
    challenge_rating: str | None = None
    creature_type: str | None = None
    role_tag: str | None = None
    role_pill_class: str | None = None
    info_tag: str | None = None
    source_type: str | None = None
    document_class: str | None = None
    campaign_id: str | None = None
    session: int | None = None
    updated_at: str | None = None


class StatblockCorpusIndexResponse(BaseModel):
    schema_version: Literal["dmb_statblock_corpus_index_v1"] = SCHEMA_VERSION
    statblocks: list[StatblockCorpusIndexItem]
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
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        if key:
            payload[key] = _parse_scalar(raw_value)
    return payload


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _cr_from_filename(name: str) -> str | None:
    match = _CR_FILENAME_RE.search(name)
    if not match:
        return None
    cr = match.group("cr").replace("_", "/")
    if cr == "half":
        return "1/2"
    return cr


def _format_cr_label(cr: str | None) -> str | None:
    if not cr:
        return None
    if cr in {"1/2", "½"}:
        return "CR 1/2"
    return f"CR {cr}"


def _title_from_body(body: str) -> str | None:
    match = _HEADING_RE.search(body)
    if not match:
        return None
    return match.group(1).strip()


def _index_id_from_path(corpus_display_path: str) -> str:
    slug = Path(corpus_display_path).stem.lower()
    return re.sub(r"[^a-z0-9]+", "-", slug).strip("-") or "statblock"


def _safe_under(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _display_path(root: Path, path: Path) -> str:
    return path.relative_to(root.resolve()).as_posix()


def _mtime_iso(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _parse_statblock_file(
    path: Path,
    *,
    repo_root: Path,
    section: StatblockIndexSection,
) -> tuple[StatblockCorpusIndexItem | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"{path.name}: could not read file ({exc})"

    frontmatter: dict[str, Any] = {}
    body = text
    try:
        block, body = split_frontmatter(text)
        if block is not None:
            frontmatter = _parse_loose_frontmatter_block(block)
    except FrontmatterParseError:
        pass

    title = (
        _text_value(frontmatter.get("title"))
        or _title_from_body(body)
        or path.stem.replace("_", " ").title()
    )
    cr = _text_value(frontmatter.get("challenge_rating")) or _cr_from_filename(path.name)
    display_path = _display_path(repo_root, path)
    role_tag, role_pill = SHEPHERDS_FLOCK_ROLE_TAGS.get(path.name, (None, None))
    info_tag = SHEPHERDS_FLOCK_INFO_TAGS.get(path.name)

    session_raw = frontmatter.get("session")
    session: int | None
    if isinstance(session_raw, int):
        session = session_raw
    elif isinstance(session_raw, str) and session_raw.isdigit():
        session = int(session_raw)
    else:
        session = None

    if section == "generated":
        role_tag = role_tag or "toolbox promote"
        role_pill = role_pill or "pill-success"
        info_tag = info_tag or "Campaign 2 generated lane"

    return (
        StatblockCorpusIndexItem(
            index_id=_index_id_from_path(display_path),
            title=title,
            corpus_display_path=display_path,
            section=section,
            challenge_rating=cr,
            creature_type=_text_value(frontmatter.get("creature_type")),
            role_tag=role_tag,
            role_pill_class=role_pill,
            info_tag=info_tag,
            source_type=_text_value(frontmatter.get("source_type")),
            document_class=_text_value(frontmatter.get("document_class")),
            campaign_id=_text_value(frontmatter.get("campaign_id")),
            session=session,
            updated_at=_mtime_iso(path),
        ),
        None,
    )


def _collect_section(
    *,
    repo_root: Path,
    corpus_root: Path,
    section_dir: Path,
    section: StatblockIndexSection,
    filename_filter,
) -> tuple[list[StatblockCorpusIndexItem], list[str]]:
    items: list[StatblockCorpusIndexItem] = []
    diagnostics: list[str] = []

    if not section_dir.is_dir():
        diagnostics.append(f"{section}: directory missing")
        return items, diagnostics

    for path in sorted(section_dir.glob("*.md")):
        if not filename_filter(path.name):
            continue
        if not _safe_under(corpus_root, path):
            diagnostics.append(f"{path.name}: path escaped allowlist root")
            continue
        item, error = _parse_statblock_file(
            path, repo_root=repo_root, section=section
        )
        if error:
            diagnostics.append(error)
            continue
        if item is not None:
            items.append(item)

    return items, diagnostics


def _sort_key(item: StatblockCorpusIndexItem) -> tuple[Any, ...]:
    if item.section == "generated":
        return (0, item.updated_at or "", item.title.lower())
    cr = item.challenge_rating or ""
    cr_sort: tuple[int, str]
    if cr == "1/2":
        cr_sort = (0, cr)
    elif cr.isdigit():
        cr_sort = (1, cr.zfill(4))
    else:
        cr_sort = (2, cr)
    return (1, cr_sort, item.title.lower())


def build_statblock_corpus_index(*, root: Path) -> StatblockCorpusIndexResponse:
    repo_root_resolved = root.resolve()
    corpus_root = (root / CORPUS_MARKDOWN_ROOT).resolve()
    diagnostics: list[str] = []
    items: list[StatblockCorpusIndexItem] = []

    generated_dir = corpus_root / GENERATED_STATBLOCKS_REL
    generated_items, generated_diag = _collect_section(
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        section_dir=generated_dir,
        section="generated",
        filename_filter=lambda name: name.lower().endswith(".md") and name != "README.md",
    )
    items.extend(generated_items)
    diagnostics.extend(generated_diag)

    flock_dir = corpus_root / SHEPHERDS_FLOCK_REL
    flock_items, flock_diag = _collect_section(
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        section_dir=flock_dir,
        section="shepherds_flock",
        filename_filter=lambda name: "_statblock_" in name.lower() and name.lower().endswith(".md"),
    )
    items.extend(flock_items)
    diagnostics.extend(flock_diag)

    generated_items_sorted = sorted(
        [item for item in items if item.section == "generated"],
        key=lambda item: (item.updated_at or "", item.title.lower()),
        reverse=True,
    )
    flock_items_sorted = sorted(
        [item for item in items if item.section == "shepherds_flock"],
        key=lambda item: _sort_key(item)[1:],
    )
    ordered = generated_items_sorted + flock_items_sorted

    return StatblockCorpusIndexResponse(statblocks=ordered, diagnostics=diagnostics)
