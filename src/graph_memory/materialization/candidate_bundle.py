"""Deterministic candidate bundle construction and validation (PR006)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from graph_memory.materialization.acceptance_manifest import (
    AcceptanceManifestError,
    SourceItem,
    build_inventory,
    load_acceptance_manifest,
    sha256_bytes,
    sha256_file,
)

BUNDLE_SCHEMA = "dmb_world_materialization_candidate_bundle_v1"

PC_SLUGS = ("baergrom", "bonogo", "caelynn", "ephanna", "karsemine", "stafl")

PC_ALIAS_OVERRIDES: dict[str, list[str]] = {
    "baergrom": ["Baergorm", "Baergrom"],
    "karsemine": ["Karsemine", "Kasemine", "Karsemine"],
}

FIXED_ENTITIES: list[tuple[str, str, str, str, list[str]]] = [
    ("loc_mirathorn", "Mirathorn", "location", "location", ["Mirathorn"]),
    ("loc_mireward", "Mireward", "location", "location", ["Mireward", "Mireward Reach"]),
    ("loc_edge", "Edge of the World", "location", "location", ["Edge of the World", "Edge"]),
    (
        "npc_lysandra_ironveil",
        "Captain Lysandra Ironveil",
        "npc",
        "npc",
        ["Lysandra", "Lysandra Ironveil", "Captain Lysandra Ironveil"],
    ),
    ("npc_lysandro", "Lysandro", "npc", "npc", ["Lysandro"]),
    ("npc_thrin_branchborn", "Thrin", "npc", "npc", ["Thrin", "Thrin Branchborn"]),
    ("npc_orik_tane", "Orik Tane", "npc", "npc", ["Orik Tane"]),
    ("npc_brin_holloway", "Brin Holloway", "npc", "npc", ["Brin Holloway"]),
    (
        "creature_tripod_null_calf",
        "Tripod Null Calf",
        "creature",
        "creature",
        ["Tripod Null Calf", "Tripod Null-Calf", "tripod"],
    ),
    (
        "creature_latch_harrow",
        "Latch Harrow",
        "creature",
        "creature",
        ["Latch Harrow"],
    ),
    (
        "event_journey_mireward_reach",
        "Journey to Mireward Reach",
        "event",
        "event",
        ["Journey to Mireward Reach"],
    ),
]

MECHANICAL_ID_BY_STEM: dict[str, str] = {
    "tripod_null_calf_statblock_cr5": "creature_tripod_null_calf",
    "latch_harrow_statblock_cr8": "creature_latch_harrow",
}

GENERIC_HEADINGS = frozenset(
    {
        "sub-locations",
        "suggested reads",
        "read order",
        "related corpus",
        "authority",
        "conventions",
        "terrain",
        "geography",
        "current state",
        "build status",
        "table role",
        "stat summary",
        "overview",
        "mechanical sheets",
        "session recaps",
        "anchor npcs",
        "world primer",
        "origin and history",
        "conventions (optional — fill in if you want strict tracking)",
    }
)

_REQUIRED_FAIL_DOMAINS = frozenset({"recap", "pc_hub", "campaign_hub", "mechanical"})


@dataclass(frozen=True)
class LexiconEntry:
    node_id: str
    label: str
    kind: str
    role: str
    aliases: tuple[str, ...]


def _artifact_id(domain: str, repo_rel_path: str) -> str:
    digest = sha256_bytes(repo_rel_path.encode("utf-8"))[7:23]
    return f"artifact:{domain}:longmont-c2:{digest}"


def _evidence_ref(
    source_path: str,
    *,
    session_id: str | None = None,
    heading: str | None = None,
) -> dict[str, Any]:
    locator = source_path
    if heading:
        locator = f"{source_path}#{heading}"
    ref: dict[str, Any] = {
        "evidence_ref_id": f"evidence:{sha256_bytes(source_path.encode('utf-8'))[7:23]}",
        "locator": locator,
    }
    if session_id:
        ref["session_id"] = session_id
    return ref


def _node(
    node_id: str,
    *,
    label: str,
    kind: str,
    role: str,
    aliases: list[str] | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    alias_list = list(aliases or [label])
    payload: dict[str, Any] = {
        "node_id": node_id,
        "label": label,
        "kind": kind,
        "role": role,
        "aliases": alias_list,
    }
    if summary:
        payload["summary"] = summary
    return payload


def _edge(source: str, target: str, predicate: str, label: str) -> dict[str, Any]:
    return {
        "source_node_id": source,
        "target_node_id": target,
        "predicate": predicate,
        "label": label,
    }


def _empty_candidate_graph() -> dict[str, Any]:
    return {
        "nodes": [],
        "edges": [],
        "evidence_refs": [],
        "unresolved_mentions": [],
    }


def _parse_frontmatter_and_body(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    block = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    frontmatter: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        value = raw.strip().strip('"').strip("'")
        frontmatter[key.strip()] = value
    return frontmatter, body


def _extract_h1(body: str) -> str | None:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return None


def _strip_display_name(title: str) -> str:
    primary = re.split(r"\s+[—–-]\s+", title, maxsplit=1)[0].strip()
    primary = re.sub(r"\s*\([^)]*\)\s*$", "", primary).strip()
    return primary or title.strip()


def _slugify_token(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unnamed"


def _is_distinct_entity_title(title: str) -> bool:
    norm = _strip_display_name(title).strip().lower()
    if not norm or norm in GENERIC_HEADINGS:
        return False
    if len(norm) < 3:
        return False
    return True


def _is_location_hub_readme(path: str) -> str | None:
    if path.endswith("/Mirathorn/README.md") or path.endswith("/Mirathorn.md"):
        return "loc_mirathorn"
    if path.endswith("/Mireward/README.md") or path.endswith("/Mireward.md"):
        return "loc_mireward"
    return None


def _build_lexicon(repo_root: Path, manifest: dict[str, Any]) -> dict[str, LexiconEntry]:
    entries: dict[str, LexiconEntry] = {}
    for node_id, label, kind, role, aliases in FIXED_ENTITIES:
        entries[node_id] = LexiconEntry(
            node_id=node_id,
            label=label,
            kind=kind,
            role=role,
            aliases=tuple(dict.fromkeys([label, *aliases])),
        )

    party = manifest.get("party") or {}
    registry_path = repo_root / party.get("registry", "")
    corpus_root = repo_root / manifest["corpus_root"]
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for slug in party.get("required_pc_slugs") or []:
            hub_rel = party["hub_template"].format(slug=slug)
            hub_path = corpus_root / hub_rel
            if not hub_path.is_file():
                continue
            text = hub_path.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter_and_body(text)
            title = frontmatter.get("title") or _extract_h1(body) or slug.title()
            display = _strip_display_name(title)
            aliases = [display, slug, slug.replace("_", " ")]
            aliases.extend(PC_ALIAS_OVERRIDES.get(slug, []))
            node_id = f"pc_{slug}"
            entries[node_id] = LexiconEntry(
                node_id=node_id,
                label=display,
                kind="pc",
                role="pc",
                aliases=tuple(dict.fromkeys(aliases)),
            )
    return entries


def _mention_patterns(entry: LexiconEntry) -> list[tuple[re.Pattern[str], str]]:
    patterns: list[tuple[re.Pattern[str], str]] = []
    seen: set[str] = set()
    for alias in sorted(entry.aliases, key=len, reverse=True):
        norm = alias.strip()
        if not norm or norm.lower() in seen:
            continue
        seen.add(norm.lower())
        if norm.lower() == "edge":
            patterns.append((re.compile(r"\bEdge of the World\b", re.IGNORECASE), entry.node_id))
            continue
        if norm.lower() == "tripod":
            patterns.append((re.compile(r"\btripod\b", re.IGNORECASE), entry.node_id))
            continue
        escaped = re.escape(norm)
        patterns.append((re.compile(rf"\b{escaped}\b", re.IGNORECASE), entry.node_id))
    return patterns


def _find_mentioned_node_ids(text: str, lexicon: dict[str, LexiconEntry]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for entry in lexicon.values():
        for pattern, node_id in _mention_patterns(entry):
            if pattern.search(text):
                if node_id not in seen:
                    seen.add(node_id)
                    found.append(node_id)
                break
    return found


def _add_node_once(
    graph: dict[str, Any],
    entry: LexiconEntry,
    *,
    summary: str | None = None,
) -> None:
    if any(node["node_id"] == entry.node_id for node in graph["nodes"]):
        return
    graph["nodes"].append(
        _node(
            entry.node_id,
            label=entry.label,
            kind=entry.kind,
            role=entry.role,
            aliases=list(entry.aliases),
            summary=summary,
        )
    )


def _creature_id_from_title(title: str, *, stem: str | None = None) -> str:
    if stem and stem in MECHANICAL_ID_BY_STEM:
        return MECHANICAL_ID_BY_STEM[stem]
    norm = _slugify_token(_strip_display_name(title))
    if "tripod" in norm:
        return "creature_tripod_null_calf"
    if "latch_harrow" in norm or ("latch" in norm and "harrow" in norm):
        return "creature_latch_harrow"
    return f"creature_{norm}"


def _recap_participating_pcs(
    session: int,
    body: str,
    lexicon: dict[str, LexiconEntry],
    party_registry: dict[str, Any],
) -> list[str]:
    mentioned = [
        node_id
        for node_id in _find_mentioned_node_ids(body, lexicon)
        if node_id.startswith("pc_")
    ]
    roster_key = str(session)
    roster = party_registry.get("session_pc_rosters", {}).get(roster_key)
    if roster:
        roster_ids = {f"pc_{slug}" for slug in roster}
        return sorted(roster_ids & set(mentioned))
    return sorted(mentioned)


def _graph_is_meaningful(graph: dict[str, Any], *, domain: str) -> bool:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    evidence = graph.get("evidence_refs") or []
    if not nodes or not evidence:
        return False
    if domain == "recap":
        non_event = [node for node in nodes if node.get("kind") != "event"]
        return bool(edges) or bool(non_event)
    return True


def _must_fail_if_empty(item: SourceItem) -> bool:
    if item.domain in _REQUIRED_FAIL_DOMAINS:
        return True
    if item.domain == "worldbuilding" and _is_location_hub_readme(item.path):
        return True
    return False


def _candidate_graph_for_item(
    item: SourceItem,
    *,
    repo_root: Path,
    lexicon: dict[str, LexiconEntry],
    party_registry: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    graph = _empty_candidate_graph()
    path = item.path
    full_path = repo_root / path
    if not full_path.is_file():
        if _must_fail_if_empty(item):
            return graph, "missing_source_file"
        return graph, "no_extractable_entity_from_content"

    text = full_path.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter_and_body(text)
    title = frontmatter.get("title") or _extract_h1(body) or Path(path).stem
    h1 = _extract_h1(body) or title
    evidence = _evidence_ref(path, heading=_strip_display_name(h1))

    if item.domain == "pc_hub":
        slug_match = re.search(r"/PCs/([^/]+)/README\.md$", path)
        slug = slug_match.group(1) if slug_match else path.split("/")[-2]
        node_id = f"pc_{slug}"
        entry = lexicon.get(node_id)
        if entry is None:
            display = _strip_display_name(title)
            entry = LexiconEntry(
                node_id=node_id,
                label=display,
                kind="pc",
                role="pc",
                aliases=(display,),
            )
        _add_node_once(graph, entry, summary=f"PC hub: {entry.label}")
        graph["evidence_refs"].append(evidence)

    elif item.domain == "mechanical":
        stem = Path(path).stem
        creature_id = _creature_id_from_title(title, stem=stem)
        display = _strip_display_name(title)
        graph["nodes"].append(
            _node(
                creature_id,
                label=display,
                kind="creature",
                role="creature",
                aliases=[display, h1],
                summary=f"Mechanical: {stem}",
            )
        )
        graph["evidence_refs"].append(evidence)

    elif item.domain == "campaign_hub":
        if "Journey" in Path(path).name:
            journey = lexicon["event_journey_mireward_reach"]
            _add_node_once(graph, journey, summary="Journey tracker event")
            mentioned = _find_mentioned_node_ids(body + "\n" + title, lexicon)
            if "loc_mireward" in mentioned or "Mireward" in body or "mireward" in body.lower():
                _add_node_once(graph, lexicon["loc_mireward"])
                graph["edges"].append(
                    _edge(
                        journey.node_id,
                        "loc_mireward",
                        "leads_to",
                        "leads to Mireward",
                    )
                )
            for node_id in mentioned:
                if node_id in {journey.node_id, "loc_mireward"}:
                    continue
                _add_node_once(graph, lexicon[node_id])
            graph["evidence_refs"].append(evidence)
        elif "lysandra" in path.lower():
            _add_node_once(graph, lexicon["npc_lysandra_ironveil"])
            mentioned = _find_mentioned_node_ids(body + "\n" + title, lexicon)
            if "loc_mireward" in mentioned:
                _add_node_once(graph, lexicon["loc_mireward"])
                graph["edges"].append(
                    _edge(
                        "npc_lysandra_ironveil",
                        "loc_mireward",
                        "associated_with",
                        "associated with Mireward",
                    )
                )
            for node_id in mentioned:
                if node_id.startswith("npc_") and node_id != "npc_lysandra_ironveil":
                    _add_node_once(graph, lexicon[node_id])
            graph["evidence_refs"].append(evidence)

    elif item.domain == "worldbuilding":
        hub_id = _is_location_hub_readme(path)
        if hub_id:
            entry = lexicon[hub_id]
            _add_node_once(graph, entry, summary=f"Location hub: {entry.label}")
            graph["evidence_refs"].append(evidence)
        else:
            combined = f"{title}\n{h1}\n{body}"
            mentioned = _find_mentioned_node_ids(combined, lexicon)
            for node_id in mentioned:
                # Location nodes only when this file's content mentions them
                # (or the path is under that location tree AND the name appears).
                if node_id == "loc_mirathorn" and "mirathorn" not in combined.lower():
                    continue
                if node_id == "loc_mireward" and "mireward" not in combined.lower():
                    continue
                _add_node_once(graph, lexicon[node_id])

            doc_kind = str(frontmatter.get("subject_doc_kind") or "").strip().lower()
            typed_kinds = {
                "statblock",
                "dossier",
                "seed",
                "location_dossier",
                "character_dossier",
            }
            path_l = path.lower()
            is_typed = doc_kind in typed_kinds or "statblock" in path_l or "_dossier" in path_l
            if is_typed and (_is_distinct_entity_title(h1) or _is_distinct_entity_title(title)):
                entity_title = _strip_display_name(
                    h1 if _is_distinct_entity_title(h1) else title
                )
                if doc_kind == "statblock" or "statblock" in path_l:
                    note_id = _creature_id_from_title(entity_title, stem=Path(path).stem)
                    kind = "creature"
                    role = "creature"
                else:
                    note_id = f"note_{_slugify_token(entity_title)}"
                    kind = "object"
                    role = "note"
                if not any(node["node_id"] == note_id for node in graph["nodes"]):
                    graph["nodes"].append(
                        _node(
                            note_id,
                            label=entity_title,
                            kind=kind,
                            role=role,
                            aliases=[entity_title],
                            summary=f"Worldbuilding {doc_kind or 'typed'}: {Path(path).name}",
                        )
                    )
            if graph["nodes"]:
                graph["evidence_refs"].append(evidence)

    elif item.domain == "recap":
        session = item.session_number
        if session is None:
            return graph, "missing_session_number"
        event_id = f"event_session_{session}"
        session_id = f"session-{session}"
        event_label = _strip_display_name(title) if title else f"Session {session}"
        graph["nodes"].append(
            _node(
                event_id,
                label=event_label,
                kind="event",
                role="event",
                aliases=[event_label, f"Session {session}"],
                summary=f"Recap session {session}",
            )
        )
        graph["evidence_refs"].append(_evidence_ref(path, session_id=session_id, heading=event_label))
        participating = _recap_participating_pcs(session, body, lexicon, party_registry)
        for pc_id in participating:
            _add_node_once(graph, lexicon[pc_id])
            graph["edges"].append(
                _edge(pc_id, event_id, "participated_in", "participated in")
            )
        for node_id in _find_mentioned_node_ids(body, lexicon):
            if node_id.startswith("pc_"):
                continue
            entry = lexicon[node_id]
            _add_node_once(graph, entry)
            if entry.kind == "location":
                graph["edges"].append(
                    _edge(event_id, node_id, "occurred_at", f"occurred at {entry.label}")
                )
            elif entry.kind in {"npc", "creature"}:
                graph["edges"].append(
                    _edge(node_id, event_id, "participated_in", "participated in")
                )

    if not _graph_is_meaningful(graph, domain=item.domain):
        if _must_fail_if_empty(item):
            return graph, "required_source_empty_graph"
        return graph, "no_extractable_entity_from_content"
    return graph, None


def build_deterministic_acceptance_bundle(
    repo_root: Path,
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
) -> dict[str, Any]:
    """Build candidate bundle from manifest inventory (no LLM)."""
    inventory = build_inventory(manifest, repo_root=repo_root, manifest_path=manifest_path)
    lexicon = _build_lexicon(repo_root, manifest)
    party_registry: dict[str, Any] = {}
    registry_path = repo_root / manifest["party"]["registry"]
    if registry_path.is_file():
        party_registry = json.loads(registry_path.read_text(encoding="utf-8"))

    sources: list[dict[str, Any]] = []
    failed_required: list[dict[str, Any]] = []

    for item_dict in inventory["source_items"]:
        item = SourceItem(
            path=item_dict["path"],
            domain=item_dict["domain"],
            required=item_dict["required"],
            sha256=item_dict["sha256"],
            session_number=item_dict.get("session_number"),
        )
        domain = item.domain
        artifact = _artifact_id(domain, item.path)
        graph, skip_reason = _candidate_graph_for_item(
            item,
            repo_root=repo_root,
            lexicon=lexicon,
            party_registry=party_registry,
        )
        if skip_reason:
            if item.required and _must_fail_if_empty(item):
                failed_required.append(
                    {
                        "kind": "required_source_empty_graph",
                        "path": item.path,
                        "domain": domain,
                        "skip_reason": skip_reason,
                    }
                )
            sources.append(
                {
                    "source_artifact_id": artifact,
                    "source_uri": item.path,
                    "source_revision_id": item.sha256,
                    "source_domain": domain,
                    "required": item.required,
                    "status": "skipped",
                    "skip_reason": skip_reason,
                    "candidate_graph": _empty_candidate_graph(),
                }
            )
        else:
            sources.append(
                {
                    "source_artifact_id": artifact,
                    "source_uri": item.path,
                    "source_revision_id": item.sha256,
                    "source_domain": domain,
                    "required": item.required,
                    "status": "accepted",
                    "skip_reason": None,
                    "candidate_graph": graph,
                }
            )

    if failed_required:
        raise AcceptanceManifestError(
            f"candidate bundle failed {len(failed_required)} required source(s)",
            errors=failed_required,
        )

    manifest_bytes = manifest_path.read_bytes()
    return {
        "schema": BUNDLE_SCHEMA,
        "version": "1.0",
        "world_id": manifest["world_id"],
        "campaign_scope": manifest["campaign_scope"],
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "sources": sources,
    }


def load_candidate_bundle(bundle_path: Path) -> dict[str, Any]:
    return json.loads(bundle_path.read_text(encoding="utf-8"))


def _inventory_lookup(
    inventory: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if inventory is None:
        return {}
    if isinstance(inventory, dict):
        items = inventory.get("source_items") or inventory.get("requested") or []
    else:
        items = inventory
    return {
        str(item["path"]): {
            "sha256": item.get("sha256"),
            "required": item.get("required"),
            "domain": item.get("domain"),
        }
        for item in items
        if item.get("path")
    }


def validate_candidate_bundle(
    bundle: dict[str, Any],
    *,
    manifest_sha256: str | None = None,
    inventory_paths: set[str] | None = None,
    inventory: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> list[str]:
    """Return validation error strings (empty when valid)."""
    errors: list[str] = []
    if bundle.get("schema") != BUNDLE_SCHEMA:
        errors.append(f"unsupported bundle schema: {bundle.get('schema')!r}")
    if manifest_sha256 and bundle.get("manifest_sha256") != manifest_sha256:
        errors.append("manifest_sha256 mismatch")
    sources = bundle.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        return errors

    inv_by_path = _inventory_lookup(inventory)
    if inventory_paths is not None and not inv_by_path:
        inv_by_path = {path: {} for path in inventory_paths}

    seen_paths: set[str] = set()
    for index, entry in enumerate(sources):
        uri = entry.get("source_uri")
        if not uri:
            errors.append(f"sources[{index}] missing source_uri")
            continue
        if uri in seen_paths:
            errors.append(f"duplicate source_uri: {uri}")
        seen_paths.add(uri)

        inv_item = inv_by_path.get(uri)
        if inv_by_path and inv_item is None:
            errors.append(f"sources[{index}] source_uri not in inventory: {uri}")
        elif inv_item is not None:
            expected_sha = inv_item.get("sha256")
            if expected_sha and entry.get("source_revision_id") != expected_sha:
                errors.append(
                    f"sources[{index}] stale source_revision_id for {uri}"
                )
            expected_required = inv_item.get("required")
            if expected_required is not None and entry.get("required") != expected_required:
                errors.append(f"sources[{index}] required flag mismatch for {uri}")

        status = entry.get("status")
        cg = entry.get("candidate_graph")
        if not isinstance(cg, dict):
            errors.append(f"sources[{index}] missing candidate_graph")
            continue
        for key in ("nodes", "edges", "evidence_refs", "unresolved_mentions"):
            if key not in cg:
                errors.append(f"sources[{index}].candidate_graph missing {key}")

        domain = entry.get("source_domain", "")
        if status == "accepted":
            if not _graph_is_meaningful(cg, domain=domain):
                errors.append(f"sources[{index}] accepted source lacks meaningful graph")
        elif status == "skipped":
            if not entry.get("skip_reason"):
                errors.append(f"sources[{index}] skipped source missing skip_reason")
        else:
            errors.append(f"sources[{index}] invalid status: {status!r}")

    if inv_by_path:
        missing = set(inv_by_path) - seen_paths
        extra = seen_paths - set(inv_by_path)
        if missing:
            errors.append(f"bundle missing inventory paths: {sorted(missing)[:5]}")
        if extra:
            errors.append(f"bundle has extra paths: {sorted(extra)[:5]}")
    elif inventory_paths is not None:
        missing = inventory_paths - seen_paths
        extra = seen_paths - inventory_paths
        if missing:
            errors.append(f"bundle missing inventory paths: {sorted(missing)[:5]}")
        if extra:
            errors.append(f"bundle has extra paths: {sorted(extra)[:5]}")

    return errors


def build_ambiguous_mention_fixture_candidate() -> dict[str, Any]:
    """Intentional ambiguous mention for unit tests (not used in real bundle)."""
    return {
        "nodes": [],
        "edges": [],
        "evidence_refs": [],
        "unresolved_mentions": [
            {
                "mention_text": "the captain",
                "candidate_node_ids": ["npc_lysandra_ironveil", "npc_captain_idris"],
                "reason": "ambiguous_title_reference",
            }
        ],
    }
