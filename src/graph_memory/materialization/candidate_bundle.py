"""Deterministic candidate bundle construction and validation (PR006)."""

from __future__ import annotations

import json
import re
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

STABLE_NODE_IDS = {
    **{f"pc_{slug}": {"label": slug.title(), "kind": "pc", "role": "pc"} for slug in PC_SLUGS},
    "loc_mirathorn": {"label": "Mirathorn", "kind": "location", "role": "location"},
    "loc_mireward": {"label": "Mireward", "kind": "location", "role": "location"},
    "npc_lysandra_ironveil": {
        "label": "Captain Lysandra Ironveil",
        "kind": "npc",
        "role": "npc",
    },
    "creature_tripod_null_calf": {
        "label": "Tripod Null Calf",
        "kind": "creature",
        "role": "creature",
    },
    "creature_latch_harrow": {
        "label": "Latch Harrow",
        "kind": "creature",
        "role": "creature",
    },
    "event_journey_mireward_reach": {
        "label": "Journey to Mireward Reach",
        "kind": "event",
        "role": "event",
    },
    **{
        f"event_session_{n}": {
            "label": f"Session {n} Event",
            "kind": "event",
            "role": "event",
        }
        for n in range(1, 24)
    },
}

MECHANICAL_NODE_BY_BASENAME = {
    "tripod_null_calf_statblock_cr5": "creature_tripod_null_calf",
    "latch_harrow_statblock_cr8": "creature_latch_harrow",
}


def _artifact_id(domain: str, repo_rel_path: str) -> str:
    digest = sha256_bytes(repo_rel_path.encode("utf-8"))[7:23]
    return f"artifact:{domain}:longmont-c2:{digest}"


def _evidence_ref(source_path: str, *, session_id: str | None = None) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "evidence_ref_id": f"evidence:{sha256_bytes(source_path.encode('utf-8'))[7:23]}",
        "locator": source_path,
    }
    if session_id:
        ref["session_id"] = session_id
    return ref


def _node(
    node_id: str,
    *,
    summary: str | None = None,
) -> dict[str, Any]:
    meta = STABLE_NODE_IDS[node_id]
    payload: dict[str, Any] = {
        "node_id": node_id,
        "label": meta["label"],
        "kind": meta["kind"],
        "role": meta["role"],
        "aliases": [meta["label"]],
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


def _location_for_worldbuilding_path(path: str) -> str | None:
    if "/Mirathorn/" in path or path.endswith("/Mirathorn/README.md"):
        return "loc_mirathorn"
    if "/Mireward/" in path or path.endswith("/Mireward/README.md"):
        return "loc_mireward"
    return None


def _candidate_graph_for_item(item: SourceItem) -> dict[str, Any]:
    graph = _empty_candidate_graph()
    path = item.path
    evidence = _evidence_ref(path)

    if item.domain == "pc_hub":
        slug_match = re.search(r"/PCs/([^/]+)/README\.md$", path)
        slug = slug_match.group(1) if slug_match else path.split("/")[-2]
        node_id = f"pc_{slug}"
        graph["nodes"].append(_node(node_id, summary=f"PC hub: {slug}"))
        graph["evidence_refs"].append(evidence)

    elif item.domain == "worldbuilding":
        loc_id = _location_for_worldbuilding_path(path)
        if loc_id:
            graph["nodes"].append(_node(loc_id, summary=f"Worldbuilding: {Path(path).name}"))
            graph["evidence_refs"].append(evidence)

    elif item.domain == "campaign_hub":
        if "Journey" in Path(path).name:
            graph["nodes"].append(
                _node("event_journey_mireward_reach", summary="Journey to Mireward Reach")
            )
            graph["nodes"].append(_node("loc_mireward", summary="Journey destination hub"))
            graph["edges"].append(
                _edge(
                    "event_journey_mireward_reach",
                    "loc_mireward",
                    "leads_to",
                    "leads to Mireward",
                )
            )
            graph["evidence_refs"].append(evidence)
        elif "lysandra" in path.lower():
            graph["nodes"].append(_node("npc_lysandra_ironveil"))
            graph["nodes"].append(_node("loc_mireward"))
            graph["edges"].append(
                _edge("npc_lysandra_ironveil", "loc_mireward", "associated_with", "associated with Mireward")
            )
            graph["evidence_refs"].append(evidence)

    elif item.domain == "mechanical":
        stem = Path(path).stem
        node_id = MECHANICAL_NODE_BY_BASENAME.get(stem)
        if node_id:
            graph["nodes"].append(_node(node_id, summary=f"Mechanical: {stem}"))
            graph["evidence_refs"].append(evidence)

    elif item.domain == "recap":
        session = item.session_number
        if session is None:
            return graph
        event_id = f"event_session_{session}"
        session_id = f"session-{session}"
        graph["nodes"].append(_node(event_id, summary=f"Recap session {session}"))
        graph["evidence_refs"].append(_evidence_ref(path, session_id=session_id))
        for slug in PC_SLUGS:
            graph["edges"].append(
                _edge(f"pc_{slug}", event_id, "participated_in", "participated in")
            )
        if session == 23:
            graph["nodes"].append(
                _node("loc_mireward", summary="Mireward gate battle (Session 23)")
            )
            graph["edges"].append(
                _edge(event_id, "loc_mireward", "occurred_at", "gate battle at Mireward")
            )

    return graph


def build_deterministic_acceptance_bundle(
    repo_root: Path,
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
) -> dict[str, Any]:
    """Build candidate bundle from manifest inventory (no LLM)."""
    inventory = build_inventory(manifest, repo_root=repo_root, manifest_path=manifest_path)
    sources: list[dict[str, Any]] = []

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
        sources.append(
            {
                "source_artifact_id": artifact,
                "source_uri": item.path,
                "source_revision_id": item.sha256,
                "source_domain": domain,
                "required": item.required,
                "status": "accepted",
                "skip_reason": None,
                "candidate_graph": _candidate_graph_for_item(item),
            }
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


def validate_candidate_bundle(
    bundle: dict[str, Any],
    *,
    manifest_sha256: str | None = None,
    inventory_paths: set[str] | None = None,
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

    seen_paths: set[str] = set()
    for index, entry in enumerate(sources):
        uri = entry.get("source_uri")
        if not uri:
            errors.append(f"sources[{index}] missing source_uri")
            continue
        if uri in seen_paths:
            errors.append(f"duplicate source_uri: {uri}")
        seen_paths.add(uri)
        cg = entry.get("candidate_graph")
        if not isinstance(cg, dict):
            errors.append(f"sources[{index}] missing candidate_graph")
            continue
        for key in ("nodes", "edges", "evidence_refs", "unresolved_mentions"):
            if key not in cg:
                errors.append(f"sources[{index}].candidate_graph missing {key}")

    if inventory_paths is not None:
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
