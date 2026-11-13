from __future__ import annotations

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
from src.ingestion.frontmatter import FrontmatterParseError, split_frontmatter

CORPUS_MARKDOWN_ROOT = Path("corpus") / "eldyrwild-markdown"
SCHEMA_VERSION = "dmb_npc_corpus_index_v1"

MIREWARD_NPCS_REL = Path("Elderwyld/Cities and Towns/Mireward/NPCs")
CAMPAIGN_2_NPCS_REL = Path("Longmont Campaign/Campaign 2/NPCs")

NpcIndexSection = Literal["mireward_setting", "campaign_2"]



class NpcCorpusIndexItem(BaseModel):
    index_id: str
    title: str
    slug: str
    section: NpcIndexSection
    hub_path: str
    primary_doc_path: str | None = None
    seed_path: str | None = None
    dossier_path: str | None = None
    timeline_path: str | None = None
    table_note: str | None = None
    document_class: str | None = None
    canon_layer: str | None = None
    campaign_id: str | None = None
    temporal_scope: str | None = None
    updated_at: str | None = None


class NpcCorpusIndexResponse(BaseModel):
    schema_version: Literal["dmb_npc_corpus_index_v1"] = SCHEMA_VERSION
    npcs: list[NpcCorpusIndexItem]
    diagnostics: list[str] = Field(default_factory=list)


def _first_existing(hub_dir: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(hub_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _primary_doc_for_hub(
    *,
    hub_dir: Path,
    seed_path: Path | None,
    dossier_path: Path | None,
    timeline_path: Path | None,
) -> Path | None:
    if dossier_path is not None:
        return dossier_path
    if seed_path is not None:
        return seed_path
    for path in sorted(hub_dir.glob("*.md")):
        if path.name == "README.md" or path == timeline_path:
            continue
        return path
    return None


def _parse_npc_hub(
    readme_path: Path,
    *,
    repo_root: Path,
    corpus_root: Path,
    section: NpcIndexSection,
) -> tuple[NpcCorpusIndexItem | None, str | None]:
    if not _safe_under(corpus_root, readme_path):
        return None, f"{readme_path.name}: path escaped corpus root"

    try:
        text = readme_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"{readme_path.name}: could not read file ({exc})"

    frontmatter: dict[str, Any] = {}
    body = text
    try:
        block, body = split_frontmatter(text)
        if block is not None:
            frontmatter = parse_loose_frontmatter(block, allow_commented_fields=False)
    except FrontmatterParseError:
        pass

    hub_dir = readme_path.parent
    seed_path = hub_dir / "character_seed.md"
    if not seed_path.is_file():
        seed_path = None
    dossier_path = _first_existing(
        hub_dir,
        ["*_character_dossier.md", "*_character_dossier_*.md", "*_dossier.md"],
    )
    timeline_path = hub_dir / "timeline.md"
    if not timeline_path.is_file():
        timeline_path = None
    primary_doc_path = _primary_doc_for_hub(
        hub_dir=hub_dir,
        seed_path=seed_path,
        dossier_path=dossier_path,
        timeline_path=timeline_path,
    )

    title = (
        _text_value(frontmatter.get("title"))
        or _title_from_body(body)
        or hub_dir.name.replace("_", " ").title()
    )

    doc_paths = [
        path
        for path in (readme_path, seed_path, dossier_path, timeline_path, primary_doc_path)
        if path is not None
    ]
    updated_at = max((_mtime_iso(path) for path in doc_paths), default=None)

    def display(path: Path | None) -> str | None:
        if path is None:
            return None
        return _display_path(repo_root, path)

    return (
        NpcCorpusIndexItem(
            index_id=f"{section}-{hub_dir.name}",
            title=title,
            slug=hub_dir.name,
            section=section,
            hub_path=display(readme_path) or "",
            primary_doc_path=display(primary_doc_path),
            seed_path=display(seed_path),
            dossier_path=display(dossier_path),
            timeline_path=display(timeline_path),
            table_note=_text_value(frontmatter.get("table_note")),
            document_class=_text_value(frontmatter.get("document_class")),
            canon_layer=_text_value(frontmatter.get("canon_layer")),
            campaign_id=_text_value(frontmatter.get("campaign_id")),
            temporal_scope=_text_value(frontmatter.get("temporal_scope")),
            updated_at=updated_at,
        ),
        None,
    )


def _collect_section(
    *,
    repo_root: Path,
    corpus_root: Path,
    section_dir: Path,
    section: NpcIndexSection,
) -> tuple[list[NpcCorpusIndexItem], list[str]]:
    items: list[NpcCorpusIndexItem] = []
    diagnostics: list[str] = []
    if not section_dir.is_dir():
        diagnostics.append(f"{section}: directory missing")
        return items, diagnostics

    for readme_path in sorted(section_dir.glob("*/README.md")):
        item, error = _parse_npc_hub(
            readme_path,
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


def build_npc_corpus_index(*, root: Path) -> NpcCorpusIndexResponse:
    repo_root_resolved = root.resolve()
    corpus_root = (root / CORPUS_MARKDOWN_ROOT).resolve()
    items: list[NpcCorpusIndexItem] = []
    diagnostics: list[str] = []

    for section, rel_path in (
        ("mireward_setting", MIREWARD_NPCS_REL),
        ("campaign_2", CAMPAIGN_2_NPCS_REL),
    ):
        section_items, section_diagnostics = _collect_section(
            repo_root=repo_root_resolved,
            corpus_root=corpus_root,
            section_dir=corpus_root / rel_path,
            section=section,
        )
        items.extend(section_items)
        diagnostics.extend(section_diagnostics)

    mireward_items = sorted(
        [item for item in items if item.section == "mireward_setting"],
        key=lambda item: item.title.lower(),
    )
    campaign_items = sorted(
        [item for item in items if item.section == "campaign_2"],
        key=lambda item: item.title.lower(),
    )
    return NpcCorpusIndexResponse(
        npcs=mireward_items + campaign_items,
        diagnostics=diagnostics,
    )
