#!/usr/bin/env python3
"""Deterministic NPC corpus recall audit for C1S1-3 + C2S20.

This benchmark inspects what the corpus currently knows about the NPCs named in:
  - Campaign 1 Session 1
  - Campaign 1 Session 2
  - Campaign 1 Session 3
  - Campaign 2 Session 20

It is intentionally offline and deterministic (no LLM calls, no writes to corpus).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_ROOT_REL = Path("corpus/eldyrwild-markdown")

_RECAPS: dict[str, str] = {
    "c1s1": "Longmont Campaign/Campaign 1/Session Recaps/Session 1 - Recap 3-27-24.md",
    "c1s2": "Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Finishing the Job.md",
    "c1s3": "Longmont Campaign/Campaign 1/Session Recaps/Session 3 - The Stone Bridge Flood.md",
    "c2s20": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
}

_REGISTRIES: dict[str, str] = {
    "longmont-c1": "Longmont Campaign/Campaign 1/_npc_registry.json",
    "longmont-c2": "Longmont Campaign/Campaign 2/_npc_registry.json",
}


@dataclass(frozen=True)
class TargetNpc:
    id: str
    display_name: str
    aliases: tuple[str, ...]


_TARGETS: tuple[TargetNpc, ...] = (
    TargetNpc("grishna", "Grishna", ("Grishna",)),
    TargetNpc("glowkindle", "Glowkindle", ("Glowkindle",)),
    TargetNpc("pippa", "Pippa", ("Pippa", "Pippa Goldwhistle")),
    TargetNpc("bubbles_the_float_goat", "Bubbles the Float Goat", ("Bubbles", "Bubbles the Float Goat")),
    TargetNpc("kirfan", "Kirfan", ("Kirfan",)),
    TargetNpc("stuart", "Stuart", ("Stuart",)),
    TargetNpc("stacey_brambleback", "Stacey Brambleback", ("Stacey", "Stacey Brambleback")),
    TargetNpc("marla_brambleback", "Marla Brambleback", ("Marla", "Marla Brambleback")),
    TargetNpc("sheriff_roderic_marr", "Sheriff Roderic Marr", ("Sheriff", "Sheriff Marr", "Roderic Marr")),
    TargetNpc("mayor", "Mayor", ("Mayor",)),
    TargetNpc("captain_lysandra_ironveil", "Captain Lysandra Ironveil", ("Lysandra", "Captain Lysandra Ironveil")),
    TargetNpc("sara_mirathorn_operator", "Sara", ("Sara", "Sara Mirathorn Operator")),
    TargetNpc("professor_tealeaf", "Professor Tealeaf", ("Professor Tealeaf", "Tealeaf")),
)


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _mention_hits(target: TargetNpc, recap_texts: dict[str, str]) -> list[str]:
    aliases = [a for a in target.aliases if a.strip()]
    hits: list[str] = []
    for recap_id, text in recap_texts.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", text, flags=re.IGNORECASE):
                hits.append(recap_id)
                break
    return hits


def _frontmatter_kv(readme_text: str) -> dict[str, str]:
    m = re.match(r"(?s)^---\n(.*?)\n---\n", readme_text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def _extract_location_fields(frontmatter: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in frontmatter.items() if "location" in k.lower()}


def _extract_divergence_mode(frontmatter: dict[str, str]) -> str | None:
    val = str(frontmatter.get("divergence_mode") or "").strip().lower()
    if not val:
        return None
    if val in {"inherit", "override", "campaign_only"}:
        return val
    return f"invalid:{val}"


def _location_from_path(hub_rel: str) -> str | None:
    normalized = hub_rel.replace("\\", "/")
    m_world = re.search(r"/Cities and Towns/([^/]+)/NPCs/", normalized)
    if m_world:
        return _slugify(m_world.group(1))
    m_campaign = re.search(r"/Locations/([^/]+)/NPCs/", normalized)
    if m_campaign:
        return _slugify(m_campaign.group(1))
    return None


def _hub_inventory(corpus_root: Path, hub_rel: str) -> dict[str, Any]:
    hub_dir = corpus_root / hub_rel
    readme = hub_dir / "README.md"
    files = list(hub_dir.glob("*")) if hub_dir.is_dir() else []
    has_dossier = any(p.name.endswith("_character_dossier.md") for p in files)
    has_timeline = (hub_dir / "timeline.md").is_file()
    has_seed = (hub_dir / "character_seed.md").is_file()
    has_statblock = any("statblock" in p.name.lower() for p in files if p.is_file())
    fm = _frontmatter_kv(_read_text(readme))
    loc_fields = _extract_location_fields(fm)
    divergence_mode = _extract_divergence_mode(fm)
    return {
        "hub_path": hub_rel,
        "exists": hub_dir.is_dir(),
        "has_readme": readme.is_file(),
        "has_dossier": has_dossier,
        "has_timeline": has_timeline,
        "has_seed": has_seed,
        "has_statblock": has_statblock,
        "frontmatter_location_fields": loc_fields,
        "divergence_mode": divergence_mode,
        "path_location_slug": _location_from_path(hub_rel),
        "world_hub": "/Elderwyld/" in f"/{hub_rel.replace('\\', '/')}",
        "campaign_hub": "/Longmont Campaign/" in f"/{hub_rel.replace('\\', '/')}",
    }


def _load_registry_records(corpus_root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for campaign_id, rel in _REGISTRIES.items():
        path = corpus_root / rel
        if not path.is_file():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                row2 = dict(row)
                row2["_registry_campaign_id"] = campaign_id
                row2["_registry_path"] = rel
                out.append(row2)
    return out


def _registry_matches(target: TargetNpc, registry_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases_norm = {_slugify(a) for a in target.aliases}
    aliases_norm.add(_slugify(target.id))
    aliases_norm.discard("")
    matches: list[dict[str, Any]] = []
    for row in registry_rows:
        slug = _slugify(str(row.get("slug") or ""))
        display = _slugify(str(row.get("display_name") or ""))
        row_aliases = {_slugify(str(x)) for x in (row.get("aliases") or []) if isinstance(x, str)}
        if slug in aliases_norm or display in aliases_norm or bool(row_aliases & aliases_norm):
            matches.append(row)
    return matches


def _direct_hub_matches(corpus_root: Path, target: TargetNpc) -> list[str]:
    npc_roots = [
        corpus_root / "Longmont Campaign",
        corpus_root / "Elderwyld",
    ]
    alias_slugs = {_slugify(a) for a in target.aliases}
    alias_slugs.add(_slugify(target.id))
    alias_slugs.discard("")
    found: set[str] = set()
    for root in npc_roots:
        if not root.is_dir():
            continue
        for readme in root.rglob("NPCs/*/README.md"):
            slug = _slugify(readme.parent.name)
            if slug in alias_slugs or any(a and a in slug for a in alias_slugs):
                rel = str(readme.parent.relative_to(corpus_root)).replace("\\", "/")
                found.add(rel)
    return sorted(found)


def _classify_tier(row: dict[str, Any]) -> str:
    if not row.get("has_any_hub"):
        return "no_hub"
    if row.get("has_campaign_hub") and not row.get("has_world_parent_link"):
        return "campaign_hub_no_world_link"
    if not row.get("has_location_link"):
        return "hub_no_location_link"
    if not row.get("has_timeline") or not row.get("has_dossier_or_seed"):
        return "hub_thin"
    return "linked_ready_baseline"


def _score(row: dict[str, Any]) -> int:
    score = 0
    if row.get("has_any_hub"):
        score += 1
    if row.get("has_campaign_hub"):
        score += 1
    if row.get("has_world_hub"):
        score += 1
    if row.get("has_world_parent_link"):
        score += 1
    if row.get("has_location_link"):
        score += 1
    if row.get("has_statblock"):
        score += 1
    if row.get("has_divergence_mode"):
        score += 1
    return score


def _contract_violations(row: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if not row.get("has_any_hub"):
        violations.append("missing_hub")
        return violations
    if row.get("has_campaign_hub") and not row.get("has_world_parent_link"):
        violations.append("campaign_hub_missing_world_parent_link")
    if not row.get("has_location_link"):
        violations.append("missing_location_link")
    if row.get("has_campaign_hub") and not row.get("has_divergence_mode"):
        violations.append("campaign_hub_missing_divergence_mode")
    if row.get("has_invalid_divergence_mode"):
        violations.append("campaign_hub_invalid_divergence_mode")
    if not row.get("has_timeline"):
        violations.append("missing_timeline")
    if not row.get("has_dossier_or_seed"):
        violations.append("missing_dossier_or_seed")
    return violations


def build_npc_corpus_recall_audit_report(*, repo_root: Path | None = None) -> dict[str, Any]:
    repo = (repo_root or _REPO_ROOT).resolve()
    corpus_root = repo / _CORPUS_ROOT_REL

    recap_texts: dict[str, str] = {}
    for recap_id, rel in _RECAPS.items():
        recap_texts[recap_id] = _read_text(corpus_root / rel)

    registry_rows = _load_registry_records(corpus_root)
    npc_rows: list[dict[str, Any]] = []

    for target in _TARGETS:
        mention_sessions = _mention_hits(target, recap_texts)
        reg_hits = _registry_matches(target, registry_rows)
        hub_candidates: set[str] = set()
        for hit in reg_hits:
            for k in ("hub_path", "setting_hub_path"):
                val = str(hit.get(k) or "").strip()
                if val:
                    hub_candidates.add(val.rstrip("/"))
        for rel in _direct_hub_matches(corpus_root, target):
            hub_candidates.add(rel.rstrip("/"))

        hubs = [_hub_inventory(corpus_root, rel) for rel in sorted(hub_candidates)]
        has_any_hub = any(h.get("exists") for h in hubs)
        has_campaign_hub = any(bool(h.get("campaign_hub")) for h in hubs)
        has_world_hub = any(bool(h.get("world_hub")) for h in hubs)
        has_timeline = any(bool(h.get("has_timeline")) for h in hubs)
        has_dossier_or_seed = any(bool(h.get("has_dossier") or h.get("has_seed")) for h in hubs)
        has_statblock = any(bool(h.get("has_statblock")) for h in hubs)
        campaign_hubs = [h for h in hubs if bool(h.get("campaign_hub"))]
        campaign_divergence_modes = [
            str(h.get("divergence_mode") or "")
            for h in campaign_hubs
            if str(h.get("divergence_mode") or "").strip() != ""
        ]
        has_invalid_divergence_mode = any(m.startswith("invalid:") for m in campaign_divergence_modes)
        has_divergence_mode = any(
            m in {"inherit", "override", "campaign_only"}
            for m in campaign_divergence_modes
        )
        has_location_link = any(
            bool(h.get("path_location_slug")) or bool(h.get("frontmatter_location_fields"))
            for h in hubs
        )
        has_world_parent_link = any(
            str(hit.get("setting_hub_path") or "").strip() != ""
            for hit in reg_hits
        )

        row = {
            "npc_id": target.id,
            "display_name": target.display_name,
            "aliases": list(target.aliases),
            "mentioned_in_sessions": mention_sessions,
            "registry_matches": [
                {
                    "campaign_id": hit.get("_registry_campaign_id"),
                    "registry_path": hit.get("_registry_path"),
                    "slug": hit.get("slug"),
                    "status": hit.get("status"),
                    "hub_path": hit.get("hub_path"),
                    "setting_hub_path": hit.get("setting_hub_path"),
                }
                for hit in reg_hits
            ],
            "hubs": hubs,
            "has_any_hub": has_any_hub,
            "has_campaign_hub": has_campaign_hub,
            "has_world_hub": has_world_hub,
            "has_world_parent_link": has_world_parent_link,
            "has_location_link": has_location_link,
            "has_timeline": has_timeline,
            "has_dossier_or_seed": has_dossier_or_seed,
            "has_statblock": has_statblock,
            "campaign_divergence_modes": campaign_divergence_modes,
            "has_divergence_mode": has_divergence_mode,
            "has_invalid_divergence_mode": has_invalid_divergence_mode,
        }
        row["readiness_tier"] = _classify_tier(row)
        row["readiness_score"] = _score(row)
        row["contract_violations"] = _contract_violations(row)
        npc_rows.append(row)

    tier_counts: dict[str, int] = {}
    for row in npc_rows:
        tier = str(row.get("readiness_tier") or "unknown")
        tier_counts[tier] = int(tier_counts.get(tier, 0)) + 1

    total = len(npc_rows)
    aggregates = {
        "targets_total": total,
        "targets_with_mentions_in_scope": sum(1 for r in npc_rows if r.get("mentioned_in_sessions")),
        "targets_with_any_hub": sum(1 for r in npc_rows if r.get("has_any_hub")),
        "targets_with_campaign_hub": sum(1 for r in npc_rows if r.get("has_campaign_hub")),
        "targets_with_world_hub": sum(1 for r in npc_rows if r.get("has_world_hub")),
        "targets_with_world_parent_link": sum(1 for r in npc_rows if r.get("has_world_parent_link")),
        "targets_with_location_link": sum(1 for r in npc_rows if r.get("has_location_link")),
        "targets_with_statblock": sum(1 for r in npc_rows if r.get("has_statblock")),
        "targets_with_divergence_mode": sum(1 for r in npc_rows if r.get("has_divergence_mode")),
        "tier_counts": tier_counts,
    }
    violation_counts: dict[str, int] = {}
    for row in npc_rows:
        for v in row.get("contract_violations") or []:
            k = str(v)
            violation_counts[k] = int(violation_counts.get(k, 0)) + 1
    aggregates["contract_violation_counts"] = violation_counts

    all_ok = not any((row.get("contract_violations") or []) for row in npc_rows)

    return {
        "schema": "dmb_npc_corpus_recall_audit_v2",
        "offline_stub": True,
        "objective": (
            "Audit world-vs-campaign NPC hub readiness and explicit location linkage "
            "for NPCs named in C1S1-3 and C2S20."
        ),
        "scope_sessions": list(_RECAPS.keys()),
        "scope_recaps": _RECAPS,
        "world_campaign_contract": {
            "world_as_main": True,
            "campaign_as_overlay_branch": True,
            "expected_campaign_world_link_field": "setting_hub_path",
            "expected_location_link": "path_location_slug or explicit frontmatter location fields",
            "expected_divergence_mode_field": "divergence_mode in {inherit, override, campaign_only}",
        },
        "all_ok": bool(all_ok),
        "aggregates": aggregates,
        "rows": npc_rows,
        "next_contract_checks": [
            "Every campaign NPC hub should carry a world parent link when a world hub exists.",
            "Every NPC should have at least one location link (path-derived or explicit field).",
            "Campaign hubs should encode divergence explicitly (inherit/override/campaign_only).",
        ],
        "aggregate_llm_cost_usd": 0.0,
        "scenario_estimated_cost_usd": 0.0,
    }


def _default_output_path(suite_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = suite_dir / "artifacts" / "runs" / str(date.today())
    return run_dir / f"npc_corpus_recall_audit--{stamp}.json"


def main() -> None:
    suite = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    out = args.output or _default_output_path(suite)
    report = build_npc_corpus_recall_audit_report(repo_root=_REPO_ROOT)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    mirror = suite / "artifacts" / "last_npc_corpus_recall_audit.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote": str(out),
                "mirror": str(mirror),
                "all_ok": bool(report.get("all_ok")),
                "targets_total": report.get("aggregates", {}).get("targets_total"),
                "targets_with_any_hub": report.get("aggregates", {}).get("targets_with_any_hub"),
                "targets_with_location_link": report.get("aggregates", {}).get("targets_with_location_link"),
                "targets_with_world_parent_link": report.get("aggregates", {}).get("targets_with_world_parent_link"),
                "targets_with_divergence_mode": report.get("aggregates", {}).get("targets_with_divergence_mode"),
                "contract_violation_counts": report.get("aggregates", {}).get("contract_violation_counts"),
                "cost_usd": 0.0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
