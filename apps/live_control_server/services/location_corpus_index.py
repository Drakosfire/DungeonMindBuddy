from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.ingestion.frontmatter import FrontmatterParseError, split_frontmatter

CORPUS_MARKDOWN_ROOT = Path("corpus") / "eldyrwild-markdown"
SCHEMA_VERSION = "dmb_location_corpus_index_v1"

MIREWARD_REL = Path("Elderwyld/Cities and Towns/Mireward")
MIREWARD_SCAFFOLD_REL = MIREWARD_REL / "Mireward_PLACE_BUILD_SCAFFOLD.md"
MIREWARD_GAZETTEER_REL = MIREWARD_REL / "Mireward_Map_Key_and_Gazetteer.md"
MIREWARD_DOSSIERS_REL = MIREWARD_REL / "Mireward_Location_Dossiers"
JOURNEY_REL = Path("Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md")
REACH_ROAD_REL = Path("Elderwyld/Roads/mireward_reach_road_d100_encounter_table.md")
MOSSFORD_REL = Path("Elderwyld/Cities and Towns/Mossford")
MOSSFORD_DOSSIERS_REL = MOSSFORD_REL / "Mossford_Location_Dossiers"
EDGE_REL = Path("Elderwyld/Cities and Towns/Edge of the World")

LocationIndexSection = Literal[
    "mireward",
    "reach_travel",
    "mossford_reference",
    "related_hubs",
]

_HEADING_RE = re.compile(r"^#\s+(.+)$", re.M)


class LocationCorpusIndexItem(BaseModel):
    index_id: str
    title: str
    section: LocationIndexSection
    corpus_display_path: str
    subject_doc_kind: str | None = None
    document_class: str | None = None
    canon_layer: str | None = None
    table_note: str | None = None
    hub_path: str | None = None
    embed_start: str | None = None
    embed_end: str | None = None
    updated_at: str | None = None


class LocationCorpusIndexResponse(BaseModel):
    schema_version: Literal["dmb_location_corpus_index_v1"] = SCHEMA_VERSION
    locations: list[LocationCorpusIndexItem]
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
        if not stripped or (stripped.startswith("#") and ":" not in stripped):
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


def _parse_location_file(
    path: Path,
    *,
    repo_root: Path,
    corpus_root: Path,
    section: LocationIndexSection,
    index_id: str,
    title_override: str | None = None,
    table_note_override: str | None = None,
    embed_start: str | None = None,
    embed_end: str | None = None,
    hub_path: Path | None = None,
) -> tuple[LocationCorpusIndexItem | None, str | None]:
    if not path.is_file():
        return None, f"{index_id}: file missing"
    if not _safe_under(corpus_root, path):
        return None, f"{index_id}: path escaped corpus root"

    frontmatter, body, error = _read_markdown_with_frontmatter(path)
    if error:
        return None, error

    title = (
        title_override
        or _text_value(frontmatter.get("title"))
        or _title_from_body(body)
        or path.stem.replace("_", " ")
    )
    table_note = table_note_override or _text_value(frontmatter.get("table_note"))

    return (
        LocationCorpusIndexItem(
            index_id=index_id,
            title=title,
            section=section,
            corpus_display_path=_display_path(repo_root, path),
            subject_doc_kind=_text_value(frontmatter.get("subject_doc_kind")),
            document_class=_text_value(frontmatter.get("document_class")),
            canon_layer=_text_value(frontmatter.get("canon_layer")),
            table_note=table_note,
            hub_path=_display_path(repo_root, hub_path) if hub_path else None,
            embed_start=embed_start,
            embed_end=embed_end,
            updated_at=_mtime_iso(path),
        ),
        None,
    )


def _collect_dossiers(
    *,
    repo_root: Path,
    corpus_root: Path,
    dossiers_dir: Path,
    section: LocationIndexSection,
    id_prefix: str,
    hub_path: Path | None = None,
) -> tuple[list[LocationCorpusIndexItem], list[str]]:
    items: list[LocationCorpusIndexItem] = []
    diagnostics: list[str] = []
    if not dossiers_dir.is_dir():
        diagnostics.append(f"{id_prefix}: dossier directory missing")
        return items, diagnostics

    for path in sorted(dossiers_dir.glob("*.md")):
        slug = path.stem.lower().replace(" ", "_")
        item, error = _parse_location_file(
            path,
            repo_root=repo_root,
            corpus_root=corpus_root,
            section=section,
            index_id=f"{id_prefix}-dossier-{slug}",
            hub_path=hub_path,
        )
        if error:
            diagnostics.append(error)
            continue
        if item is not None:
            items.append(item)
    return items, diagnostics


def _build_mireward_f4_excerpt(
    *,
    repo_root: Path,
    corpus_root: Path,
) -> tuple[LocationCorpusIndexItem | None, str | None]:
    path = corpus_root / MIREWARD_SCAFFOLD_REL
    return _parse_location_file(
        path,
        repo_root=repo_root,
        corpus_root=corpus_root,
        section="mireward",
        index_id="mireward-scaffold-f4-north-gate",
        title_override="North-gate refugee wave (S23)",
        table_note_override=(
            "Excerpt from place scaffold §F4 — locked S23 north-apron sketch until dossier promotion."
        ),
        embed_start="## F4. Edge support refugee wave",
        embed_end="## F2. Anchor NPC",
    )


def _section_sort_key(item: LocationCorpusIndexItem) -> tuple[str, str]:
    return (item.title.lower(), item.index_id)


def build_location_corpus_index(*, root: Path) -> LocationCorpusIndexResponse:
    repo_root_resolved = root.resolve()
    corpus_root = (root / CORPUS_MARKDOWN_ROOT).resolve()
    items: list[LocationCorpusIndexItem] = []
    diagnostics: list[str] = []

    mireward_hub = corpus_root / MIREWARD_REL / "README.md"
    item, error = _parse_location_file(
        mireward_hub,
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        section="mireward",
        index_id="mireward-hub-readme",
        hub_path=mireward_hub,
    )
    if error:
        diagnostics.append(error)
    elif item is not None:
        items.append(item)

    item, error = _parse_location_file(
        corpus_root / MIREWARD_SCAFFOLD_REL,
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        section="mireward",
        index_id="mireward-place-scaffold",
        hub_path=mireward_hub if mireward_hub.is_file() else None,
    )
    if error:
        diagnostics.append(error)
    elif item is not None:
        items.append(item)

    f4_item, f4_error = _build_mireward_f4_excerpt(
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
    )
    if f4_error:
        diagnostics.append(f4_error)
    elif f4_item is not None:
        items.append(f4_item)

    gazetteer_path = corpus_root / MIREWARD_GAZETTEER_REL
    if gazetteer_path.is_file():
        item, error = _parse_location_file(
            gazetteer_path,
            repo_root=repo_root_resolved,
            corpus_root=corpus_root,
            section="mireward",
            index_id="mireward-gazetteer",
            hub_path=mireward_hub if mireward_hub.is_file() else None,
        )
        if error:
            diagnostics.append(error)
        elif item is not None:
            items.append(item)

    dossier_items, dossier_diagnostics = _collect_dossiers(
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        dossiers_dir=corpus_root / MIREWARD_DOSSIERS_REL,
        section="mireward",
        id_prefix="mireward",
        hub_path=mireward_hub if mireward_hub.is_file() else None,
    )
    items.extend(dossier_items)
    diagnostics.extend(dossier_diagnostics)

    for rel_path, index_id, table_note in (
        (
            JOURNEY_REL,
            "reach-journey-tracker",
            "Travel bookkeeping for the Mireward Reach march — distances and camp state.",
        ),
        (
            REACH_ROAD_REL,
            "reach-road-encounters",
            "Road encounter table for the Reach; also indexed on Roll tables.",
        ),
    ):
        item, error = _parse_location_file(
            corpus_root / rel_path,
            repo_root=repo_root_resolved,
            corpus_root=corpus_root,
            section="reach_travel",
            index_id=index_id,
            table_note_override=table_note,
        )
        if error:
            diagnostics.append(error)
        elif item is not None:
            items.append(item)

    mossford_hub = corpus_root / MOSSFORD_REL / "README.md"
    item, error = _parse_location_file(
        mossford_hub,
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        section="mossford_reference",
        index_id="mossford-hub-readme",
        table_note_override="Reference hub shape Mireward is targeting for promotion.",
        hub_path=mossford_hub if mossford_hub.is_file() else None,
    )
    if error:
        diagnostics.append(error)
    elif item is not None:
        items.append(item)

    mossford_items, mossford_diagnostics = _collect_dossiers(
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        dossiers_dir=corpus_root / MOSSFORD_DOSSIERS_REL,
        section="mossford_reference",
        id_prefix="mossford",
        hub_path=mossford_hub if mossford_hub.is_file() else None,
    )
    items.extend(mossford_items)
    diagnostics.extend(mossford_diagnostics)

    edge_hub = corpus_root / EDGE_REL / "README.md"
    item, error = _parse_location_file(
        edge_hub,
        repo_root=repo_root_resolved,
        corpus_root=corpus_root,
        section="related_hubs",
        index_id="edge-of-the-world-hub",
        hub_path=edge_hub if edge_hub.is_file() else None,
    )
    if error:
        diagnostics.append(error)
    elif item is not None:
        items.append(item)

    mireward_items = sorted(
        [entry for entry in items if entry.section == "mireward"],
        key=_section_sort_key,
    )
    reach_items = sorted(
        [entry for entry in items if entry.section == "reach_travel"],
        key=_section_sort_key,
    )
    mossford_items_sorted = sorted(
        [entry for entry in items if entry.section == "mossford_reference"],
        key=_section_sort_key,
    )
    related_items = sorted(
        [entry for entry in items if entry.section == "related_hubs"],
        key=_section_sort_key,
    )

    return LocationCorpusIndexResponse(
        locations=mireward_items + reach_items + mossford_items_sorted + related_items,
        diagnostics=diagnostics,
    )
