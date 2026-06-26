from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.corpus.session_recap_paths import (
    campaign_id_from_number,
    frontmatter_seed_relpath,
    normalized_recap_relpath,
    session_recaps_prefix,
)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
_TITLE_RE = re.compile(r"^\s*title:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)
_SUBJECT_CLASS_RE = re.compile(r"^\s*subject_class:\s*[\"']?([A-Za-z_]+)[\"']?\s*$", re.MULTILINE)
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


@dataclass(frozen=True)
class SeedEntity:
    slug: str
    display_name: str
    route: str
    aliases: tuple[str, ...] = ()


def _strip_frontmatter(text: str) -> str:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return text
    return text[match.end() :]


def _frontmatter(text: str) -> str:
    match = _FRONTMATTER_RE.match(text)
    return match.group(1) if match else ""


def _frontmatter_value(pattern: re.Pattern[str], frontmatter: str) -> str | None:
    match = pattern.search(frontmatter)
    return match.group(1).strip().strip('"').strip("'") if match else None


def _slug_to_display(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("_") if part)


def _route_for_readme(corpus_root: Path, readme: Path) -> str:
    rel = readme.parent.relative_to(corpus_root).as_posix()
    return f"{rel}/"


def _token_set(text: str) -> set[str]:
    return {token.lower() for token in _WORD_RE.findall(text)}


def _mentions_entity(text: str, entity: SeedEntity) -> bool:
    lower_text = text.lower()
    if entity.display_name and entity.display_name.lower() in lower_text:
        return True
    for alias in entity.aliases:
        if alias and alias.lower() in lower_text:
            return True
    tokens = _token_set(text)
    slug_parts = {part for part in entity.slug.lower().split("_") if len(part) >= 4}
    return bool(slug_parts & tokens)


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_party_roster(campaign_dir: Path, *, session: int) -> tuple[str, ...]:
    registry = _load_json(campaign_dir / "_party_registry.json") or {}
    raw_rosters = registry.get("session_pc_rosters") or {}
    best_session = -1
    best_roster: list[str] = []
    for key, value in raw_rosters.items():
        try:
            roster_session = int(key)
        except (TypeError, ValueError):
            continue
        if roster_session <= session and roster_session > best_session and isinstance(value, list):
            best_session = roster_session
            best_roster = [str(item).strip() for item in value if str(item).strip()]
    return tuple(best_roster)


def _load_pc_entities(corpus_root: Path, campaign_dir: Path, roster: tuple[str, ...]) -> list[SeedEntity]:
    pc_dir = campaign_dir / "PCs"
    entities: list[SeedEntity] = []
    slugs = roster or tuple(sorted(path.name for path in pc_dir.iterdir() if path.is_dir())) if pc_dir.is_dir() else ()
    for slug in slugs:
        readme = pc_dir / slug / "README.md"
        title = None
        if readme.is_file():
            title = _frontmatter_value(_TITLE_RE, _frontmatter(readme.read_text(encoding="utf-8")))
        entities.append(
            SeedEntity(
                slug=slug,
                display_name=(title or _slug_to_display(slug)).split("—", 1)[0].strip(),
                route=f"{pc_dir.relative_to(corpus_root).as_posix()}/{slug}/",
            )
        )
    return entities


def _load_npc_registry_entities(campaign_dir: Path) -> list[SeedEntity]:
    raw = _load_json(campaign_dir / "_npc_registry.json") or []
    entities: list[SeedEntity] = []
    if not isinstance(raw, list):
        return entities
    for row in raw:
        if not isinstance(row, dict):
            continue
        route = row.get("hub_path") or row.get("setting_hub_path")
        slug = str(row.get("slug") or "").strip()
        if not slug or not route:
            continue
        aliases = tuple(str(alias).strip() for alias in row.get("aliases") or [] if str(alias).strip())
        entities.append(
            SeedEntity(
                slug=slug,
                display_name=str(row.get("display_name") or _slug_to_display(slug)).strip(),
                route=str(route).strip(),
                aliases=aliases,
            )
        )
    return entities


def _scan_hub_readmes(
    corpus_root: Path, *, campaign_number: int, subject_class: str
) -> list[SeedEntity]:
    entities: list[SeedEntity] = []
    for readme in sorted(corpus_root.rglob("README.md")):
        rel_parts = readme.relative_to(corpus_root).parts
        if len(rel_parts) >= 3 and rel_parts[0] == "Longmont Campaign":
            if rel_parts[1] != f"Campaign {campaign_number}":
                continue
        text = readme.read_text(encoding="utf-8")
        fm = _frontmatter(text)
        if _frontmatter_value(_SUBJECT_CLASS_RE, fm) != subject_class:
            continue
        slug = readme.parent.name
        title = _frontmatter_value(_TITLE_RE, fm) or _slug_to_display(slug)
        entities.append(
            SeedEntity(
                slug=slug,
                display_name=title.split("—", 1)[0].strip(),
                route=_route_for_readme(corpus_root, readme),
            )
        )
    return entities


def _dedupe_entities(entities: list[SeedEntity]) -> list[SeedEntity]:
    seen: set[str] = set()
    out: list[SeedEntity] = []
    for entity in entities:
        if entity.slug in seen:
            continue
        seen.add(entity.slug)
        out.append(entity)
    return out


def _yaml_string_list(values: tuple[str, ...], *, indent: int) -> list[str]:
    pad = " " * indent
    return [f'{pad}- "{value}"' for value in values]


def build_frontmatter_seed(
    *,
    corpus_root: Path,
    campaign_number: int,
    session: int,
) -> str:
    corpus_root = corpus_root.resolve()
    campaign_id = campaign_id_from_number(campaign_number)
    campaign_dir = corpus_root / f"Longmont Campaign/Campaign {campaign_number}"
    recap_rel = normalized_recap_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    recap_path = corpus_root / recap_rel
    recap_text = recap_path.read_text(encoding="utf-8")
    recap_body = _strip_frontmatter(recap_text)
    basename = recap_path.stem
    roster = _load_party_roster(campaign_dir, session=session)
    pcs = _load_pc_entities(corpus_root, campaign_dir, roster)
    npc_candidates = _dedupe_entities(
        _load_npc_registry_entities(campaign_dir)
        + _scan_hub_readmes(corpus_root, campaign_number=campaign_number, subject_class="npc")
    )
    location_candidates = _scan_hub_readmes(
        corpus_root, campaign_number=campaign_number, subject_class="location"
    )
    npcs = [entity for entity in npc_candidates if _mentions_entity(recap_body, entity)]
    locations = [entity for entity in location_candidates if _mentions_entity(recap_body, entity)]

    lines: list[str] = [
        "---",
        "schema: dmb_recap_breadcrumbs_v1",
        f'source_recap_path: "{recap_rel}"',
        "campaign:",
        '  title: "Longmont Campaign"',
        f"  campaign_number: {campaign_number}",
        f"  campaign_id: {campaign_id}",
        "session:",
        f"  number: {session}",
        f'  title: "{basename}"',
        "  document_class: play",
        "  canon_layer: campaign",
        "  temporal_scope: session_specific",
        f"  origin_session: {session}",
        f"  last_updated_session: {session}",
        "  source_class: observed_session_recap",
        "breadcrumb_semantics:",
        '  purpose: "Machine-facing session memory index over normalized recap prose."',
        '  placement_rule: "Place tags immediately after the source-derived span that should route to that hub."',
        '  selectivity_rule: "Tag durable actions, discoveries, relationships, location-state changes, collective decisions, and unresolved durable entities; do not tag every mere mention."',
        '  source_boundary: "The canonical source recap remains the prose source of truth and is not edited by this file."',
        "inline_tag_grammar:",
        '  pc: "[PC][corpus-relative hub route]"',
        '  npc: "[NPC][corpus-relative hub route]"',
        '  location: "[Location][corpus-relative hub route]"',
        '  party: "[Party][corpus-relative or proposed party hub route]"',
        '  new_hub_candidate: "[NewHubCandidate][proposed corpus-relative route]"',
        "entity_index:",
        "  parties:",
        "    questionable_company:",
        "      slug: questionable_company",
        '      display_name: "Questionable Company"',
        "      hub_status: proposed",
        f'      proposed_route: "Longmont Campaign/Campaign {campaign_number}/Parties/questionable_company/"',
        f"      default_members: [{', '.join(roster)}]",
        "      aliases_in_recap:",
        '        - "the group"',
        '        - "the party"',
        '        - "the team"',
        '      routing_policy: "Tag party spans only for collective decisions, travel beats, or end-of-session forks."',
        "  pcs:",
    ]
    for entity in pcs:
        lines.extend(
            [
                f"    - slug: {entity.slug}",
                f'      route: "{entity.route}"',
            ]
        )
    if not pcs:
        lines.append("    []")
    lines.append("  npcs:")
    for entity in npcs:
        lines.extend(
            [
                f"    - slug: {entity.slug}",
                f'      route: "{entity.route}"',
            ]
        )
        if entity.aliases:
            lines.append("      aliases_in_recap:")
            lines.extend(_yaml_string_list(entity.aliases, indent=8))
    if not npcs:
        lines.append("    []")
    lines.append("  locations:")
    for entity in locations:
        lines.extend(
            [
                f"    - slug: {entity.slug}",
                f'      route: "{entity.route}"',
            ]
        )
    if not locations:
        lines.append("    []")
    lines.extend(
        [
            "  new_hub_candidates: []",
            "unresolved_open_questions: []",
            "counts_by_subject_type:",
            "  indexed_entities:",
            "    parties: 1",
            f"    pcs: {len(pcs)}",
            f"    npcs: {len(npcs)}",
            f"    locations: {len(locations)}",
            "    new_hub_candidates: 0",
            "  inline_tags:",
            "    PC: 0",
            "    NPC: 0",
            "    Location: 0",
            "    Party: 0",
            "    NewHubCandidate: 0",
            "  unresolved_open_questions: 0",
            "---",
            "",
            f"### {basename} — frontmatter seed only",
            "",
        ]
    )
    return "\n".join(lines)


def default_frontmatter_seed_path(
    *, corpus_root: Path, campaign_number: int, session: int
) -> Path:
    rel = frontmatter_seed_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    return corpus_root / rel
