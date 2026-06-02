#!/usr/bin/env python3
"""Build a machine-readable library of ingested and prepped corpus material.

Scans committed corpus trees, ingest pipeline derivatives, hub packages, session
prep, live workspaces, and compares against the C2S23 planning activation manifest.

Example::

  uv run python scripts/build_ingested_corpus_library.py
  uv run python scripts/build_ingested_corpus_library.py --json-out Docs/data/ingested-corpus-library/ingested_corpus_library.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from src.corpus.session_recap_paths import (
    PILOT_BLESSED_SESSIONS,
    campaign_id_from_number,
    session_recaps_prefix,
)
from src.live_play.session_paths import repo_root

SCHEMA_ID = "dmb_ingested_corpus_library_v1"
DEFAULT_JSON_OUT = Path("Docs/data/ingested-corpus-library/ingested_corpus_library.json")
DEFAULT_MD_OUT = Path("Docs/data/ingested-corpus-library/ingested_corpus_library.md")
C2S23_MANIFEST = Path("evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json")
DOGFOOD_FULL_MANIFEST = Path("evals/c2_live_prep/benchmarks/c2s23_dogfood_full_manifest.json")

SESSION_RE = re.compile(r"^Session\s+(\d+)\s*-\s*(.+)\.(md|breadcrumbed\.md|frontmatter_seed\.md|records_meta\.jsonl?)$", re.I)
GENERIC_RECAP_RE = re.compile(r"^Session\s+(\d+)\s*-\s*Recap\.md$", re.I)

HUB_DOC_KINDS = ("README.md", "timeline.md", "character_seed.md")
HUB_SUFFIX_PATTERNS = (
    ("dossier", re.compile(r"_character_dossier\.md$", re.I)),
    ("statblock", re.compile(r"_statblock.*\.md$", re.I)),
    ("seed", re.compile(r"^character_seed\.md$", re.I)),
    ("timeline", re.compile(r"^timeline\.md$", re.I)),
    ("readme", re.compile(r"^README\.md$", re.I)),
)


def _utc_now_z() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _route_record(root: Path, rel: str) -> dict[str, Any]:
    p = root / rel
    return {"route": rel, "exists": p.is_file(), "size_bytes": p.stat().st_size if p.is_file() else None}


def _session_from_filename(name: str) -> int | None:
    m = re.search(r"Session\s+(\d+)", name, re.I)
    return int(m.group(1)) if m else None


def _discover_canon_recaps(recaps_dir: Path) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for path in sorted(recaps_dir.glob("Session *.md")):
        if path.parent.name.startswith("_"):
            continue
        session = _session_from_filename(path.name)
        if session is None:
            continue
        out[session] = {
            "route": path.name,
            "generic_title": bool(GENERIC_RECAP_RE.match(path.name)),
            "exists": True,
        }
    return out


def _discover_stage_dir(stage_dir: Path, *, suffix: str) -> dict[int, str]:
    if not stage_dir.is_dir():
        return {}
    out: dict[int, str] = {}
    for path in sorted(stage_dir.glob(f"Session *{suffix}")):
        session = _session_from_filename(path.name)
        if session is not None:
            out[session] = path.name
    return out


def _pipeline_tier(stages: dict[str, bool]) -> str:
    if stages.get("session_memory_jsonl") and stages.get("breadcrumbed"):
        if stages.get("ingest_staging"):
            return "full_with_staging"
        return "breadcrumb_memory"
    if stages.get("breadcrumbed"):
        return "breadcrumb_only"
    if stages.get("normalized"):
        return "normalized_only"
    if stages.get("canon_recap"):
        return "canon_only"
    return "none"


def _build_session_row(
    *,
    root: Path,
    campaign_number: int,
    session: int,
    canon: dict[str, Any] | None,
    normalized: dict[int, str],
    breadcrumbed: dict[int, str],
    frontmatter_seed: dict[int, str],
    memory_jsonl: dict[int, str],
    memory_meta: dict[int, str],
    staging: dict[int, list[str]],
) -> dict[str, Any]:
    prefix = session_recaps_prefix(campaign_number)
    campaign_id = campaign_id_from_number(campaign_number)

    def stage_route(kind: str, filename: str | None) -> dict[str, Any] | None:
        if not filename:
            return None
        rel = f"{prefix}/{kind}/{filename}" if kind != "canon" else f"{prefix}/{filename}"
        if kind == "canon":
            rel = f"{prefix}/{filename}"
        elif kind == "_normalized":
            rel = f"{prefix}/_normalized/{filename}"
        elif kind == "_breadcrumbed":
            rel = f"{prefix}/_breadcrumbed/{filename}"
        elif kind == "_session_memory":
            rel = f"{prefix}/_session_memory/{filename}"
        elif kind == "_ingest_staging":
            rel = f"Longmont Campaign/Campaign {campaign_number}/_ingest_staging/{filename}"
        return _route_record(root, rel)

    staging_files = staging.get(session) or []
    stages_present = {
        "canon_recap": bool(canon),
        "normalized": session in normalized,
        "breadcrumbed": session in breadcrumbed,
        "frontmatter_seed": session in frontmatter_seed,
        "session_memory_jsonl": session in memory_jsonl,
        "session_memory_meta": session in memory_meta,
        "ingest_staging": bool(staging_files),
    }

    row: dict[str, Any] = {
        "session": session,
        "campaign_id": campaign_id,
        "pilot_blessed": (campaign_number, session) in PILOT_BLESSED_SESSIONS,
        "pipeline_tier": _pipeline_tier(stages_present),
        "stages": {},
    }
    if canon:
        row["stages"]["canon_recap"] = _route_record(root, f"{prefix}/{canon['route']}")
        row["stages"]["canon_recap"]["generic_title"] = canon["generic_title"]
    if session in normalized:
        row["stages"]["normalized"] = _route_record(root, f"{prefix}/_normalized/{normalized[session]}")
    if session in breadcrumbed:
        row["stages"]["breadcrumbed"] = _route_record(root, f"{prefix}/_breadcrumbed/{breadcrumbed[session]}")
    if session in frontmatter_seed:
        row["stages"]["frontmatter_seed"] = _route_record(
            root, f"{prefix}/_breadcrumbed/{frontmatter_seed[session]}"
        )
    if session in memory_jsonl:
        row["stages"]["session_memory_jsonl"] = _route_record(
            root, f"{prefix}/_session_memory/{memory_jsonl[session]}"
        )
    if session in memory_meta:
        row["stages"]["session_memory_meta"] = _route_record(
            root, f"{prefix}/_session_memory/{memory_meta[session]}"
        )
    if staging_files:
        row["stages"]["ingest_staging"] = [
            _route_record(root, f"Longmont Campaign/Campaign {campaign_number}/_ingest_staging/{name}")
            for name in staging_files
        ]
    return row


def _scan_staging(campaign_dir: Path) -> dict[int, list[str]]:
    staging_dir = campaign_dir / "_ingest_staging"
    out: dict[int, list[str]] = defaultdict(list)
    if not staging_dir.is_dir():
        return out
    for path in sorted(staging_dir.glob("*.md")):
        m = re.search(r"session_(\d+)_", path.name, re.I)
        if m:
            out[int(m.group(1))].append(path.name)
    return dict(out)


def _classify_hub_file(name: str) -> str:
    for label, pattern in HUB_SUFFIX_PATTERNS:
        if pattern.search(name):
            return label
    return "other"


def _scan_hub_tree(hub_root: Path, *, root: Path, hub_kind: str) -> dict[str, Any]:
    if not hub_root.is_dir():
        return {"hub_kind": hub_kind, "entity_count": 0, "entities": []}

    entities: list[dict[str, Any]] = []
    for entity_dir in sorted(p for p in hub_root.iterdir() if p.is_dir()):
        files_by_kind: dict[str, list[str]] = defaultdict(list)
        for path in sorted(entity_dir.rglob("*.md")):
            kind = _classify_hub_file(path.name)
            files_by_kind[kind].append(_rel(root, path))
        if not files_by_kind and not (entity_dir / "README.md").exists():
            continue
        entities.append(
            {
                "slug": entity_dir.name,
                "files_by_kind": {k: v for k, v in sorted(files_by_kind.items())},
                "file_count": sum(len(v) for v in files_by_kind.values()),
            }
        )
    kind_totals: Counter[str] = Counter()
    for ent in entities:
        for kind, paths in ent["files_by_kind"].items():
            kind_totals[kind] += len(paths)
    return {
        "hub_kind": hub_kind,
        "entity_count": len(entities),
        "file_kind_totals": dict(sorted(kind_totals.items())),
        "entities": entities,
    }


def _scan_loose_campaign_md(campaign_dir: Path, *, root: Path) -> list[dict[str, Any]]:
    skip_dirs = {"Session Recaps", "Session Prep", "NPCs", "PCs", "Locations", "_ingest_staging"}
    rows: list[dict[str, Any]] = []
    for path in sorted(campaign_dir.rglob("*.md")):
        rel_parts = path.relative_to(campaign_dir).parts
        if not rel_parts or rel_parts[0] in skip_dirs:
            continue
        if rel_parts[0] in {"NPCs", "PCs", "Locations"}:
            continue
        rows.append({"route": _rel(root, path), "basename": path.name})
    return rows


def _scan_session_prep(prep_dir: Path, *, root: Path) -> list[dict[str, Any]]:
    if not prep_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(prep_dir.rglob("*.md")):
        session = _session_from_filename(path.name)
        if session is None:
            m = re.search(r"session_(\d+)_", path.name, re.I)
            session = int(m.group(1)) if m else None
        rows.append(
            {
                "session": session,
                "route": _rel(root, path),
                "basename": path.name,
            }
        )
    return rows


def _scan_elderwyld(elderwyld: Path, *, root: Path) -> dict[str, Any]:
    if not elderwyld.is_dir():
        return {"exists": False}
    top_dirs = sorted(p.name for p in elderwyld.iterdir() if p.is_dir())
    md_count = len(list(elderwyld.rglob("*.md")))
    npc_hubs = _scan_hub_tree(elderwyld / "Cities and Towns" / "Mirathorn" / "NPCs", root=root, hub_kind="elderwyld_npc")
    # Also scan other known NPC locations under Elderwyld
    extra_npc_paths = list(elderwyld.rglob("NPCs"))
    return {
        "exists": True,
        "md_file_count": md_count,
        "top_level_dirs": top_dirs,
        "mirathorn_npc_sample": npc_hubs,
        "npc_dir_count": len(extra_npc_paths),
    }


def _load_manifest_activation(root: Path, manifest_rel: Path) -> dict[str, Any]:
    manifest_path = root / manifest_rel
    if not manifest_path.is_file():
        return {"exists": False, "manifest_path": manifest_rel.as_posix()}
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    routes = {str(e.get("route") or "") for e in raw.get("entries") or []}
    return {
        "exists": True,
        "manifest_path": manifest_rel.as_posix(),
        "schema": raw.get("schema"),
        "entry_count": len(raw.get("entries") or []),
        "planning_session": raw.get("planning_session"),
        "source_sessions": raw.get("source_sessions"),
        "routes": sorted(r for r in routes if r),
    }


def _load_c2s23_activation(root: Path) -> dict[str, Any]:
    return _load_manifest_activation(root, C2S23_MANIFEST)


def _scan_live_workspaces(root: Path) -> list[dict[str, Any]]:
    live_root = root / "evals/c2_live_prep/live"
    if not live_root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for session_dir in sorted(live_root.glob("session_*")):
        m = re.search(r"session_(\d+)$", session_dir.name)
        session = int(m.group(1)) if m else None
        artifacts = []
        for name in ("live_packet.json", "recap.md", "event_log.jsonl", "current_state.json", "surface_layout.json"):
            p = session_dir / name
            if p.is_file():
                artifacts.append({"basename": name, "route": _rel(root, p)})
        rows.append({"session": session, "workspace_dir": _rel(root, session_dir), "artifacts": artifacts})
    return rows


def _scan_eval_ingest_artifacts(root: Path) -> dict[str, Any]:
    paths = {
        "merged_session_memory_s21_s22": root
        / "evals/c2_live_prep/artifacts/runs/2026-05-30/merged_session_memory_s21_s22.jsonl",
        "route_equivalence_c1": root
        / "evals/sentence_routing_retrieval_falsification/route_equivalence_longmont_c1_v1.jsonl",
        "route_equivalence_c2": root
        / "evals/sentence_routing_retrieval_falsification/route_equivalence_longmont_c2_v1.jsonl",
        "stage_d_vertical_slice": root / "evals/stage_d_entity_resolution_vertical_slice",
    }
    out: dict[str, Any] = {}
    for key, path in paths.items():
        if path.is_file():
            out[key] = {"route": _rel(root, path), "exists": True, "size_bytes": path.stat().st_size}
        elif path.is_dir():
            out[key] = {
                "route": _rel(root, path),
                "exists": True,
                "file_count": len(list(path.rglob("*"))),
            }
        else:
            out[key] = {"route": _rel(root, path), "exists": False}
    return out


def build_library(*, root: Path | None = None) -> dict[str, Any]:
    repo = root or repo_root()
    corpus = repo / "corpus/eldyrwild-markdown"
    longmont = corpus / "Longmont Campaign"

    campaigns: list[dict[str, Any]] = []
    tier_totals: Counter[str] = Counter()

    for campaign_number in (1, 2):
        campaign_dir = longmont / f"Campaign {campaign_number}"
        recaps_dir = campaign_dir / "Session Recaps"
        if not recaps_dir.is_dir():
            continue

        canon = _discover_canon_recaps(recaps_dir)
        normalized = _discover_stage_dir(recaps_dir / "_normalized", suffix=".md")
        breadcrumbed = _discover_stage_dir(recaps_dir / "_breadcrumbed", suffix=".breadcrumbed.md")
        frontmatter_seed = _discover_stage_dir(recaps_dir / "_breadcrumbed", suffix=".frontmatter_seed.md")
        memory_jsonl = _discover_stage_dir(recaps_dir / "_session_memory", suffix=".records_meta.jsonl")
        memory_meta = _discover_stage_dir(recaps_dir / "_session_memory", suffix=".records_meta.json")
        staging = _scan_staging(campaign_dir)

        all_sessions = sorted(set(canon) | set(normalized) | set(breadcrumbed) | set(memory_jsonl))
        sessions = [
            _build_session_row(
                root=corpus,
                campaign_number=campaign_number,
                session=session,
                canon=canon.get(session),
                normalized=normalized,
                breadcrumbed=breadcrumbed,
                frontmatter_seed=frontmatter_seed,
                memory_jsonl=memory_jsonl,
                memory_meta=memory_meta,
                staging=staging,
            )
            for session in all_sessions
        ]
        for row in sessions:
            tier_totals[row["pipeline_tier"]] += 1

        hub_scan: dict[str, Any] = {}
        for hub_name in ("NPCs", "PCs", "Locations", "Factions", "Plot Artifacts"):
            hub_scan[hub_name.lower()] = _scan_hub_tree(
                campaign_dir / hub_name, root=corpus, hub_kind=hub_name.lower()
            )

        prep = _scan_session_prep(campaign_dir / "Session Prep", root=corpus)
        loose_md = _scan_loose_campaign_md(campaign_dir, root=corpus)
        registries = []
        for name in ("_npc_registry.json", "_party_registry.json"):
            p = campaign_dir / name
            if p.is_file():
                registries.append(_route_record(corpus, _rel(corpus, p)))

        campaigns.append(
            {
                "campaign_id": campaign_id_from_number(campaign_number),
                "campaign_number": campaign_number,
                "session_recaps_prefix": session_recaps_prefix(campaign_number),
                "session_count": len(sessions),
                "sessions": sessions,
                "hubs": hub_scan,
                "session_prep": prep,
                "loose_markdown": loose_md,
                "registries": registries,
            }
        )

    activation = _load_c2s23_activation(repo)
    dogfood_activation = _load_manifest_activation(repo, DOGFOOD_FULL_MANIFEST)
    lib_corpus_root = "corpus/eldyrwild-markdown"

    def _repo_route(corpus_rel: str) -> str:
        return f"{lib_corpus_root}/{corpus_rel}" if not corpus_rel.startswith(lib_corpus_root) else corpus_rel

    all_ingest_routes: set[str] = set()
    for camp in campaigns:
        for sess in camp["sessions"]:
            for stage_name, stage_val in sess.get("stages", {}).items():
                if stage_name == "ingest_staging" and isinstance(stage_val, list):
                    for item in stage_val:
                        all_ingest_routes.add(_repo_route(item["route"]))
                elif isinstance(stage_val, dict) and stage_val.get("route"):
                    all_ingest_routes.add(_repo_route(stage_val["route"]))
        for prep in camp.get("session_prep") or []:
            all_ingest_routes.add(_repo_route(prep["route"]))
        for loose in camp.get("loose_markdown") or []:
            all_ingest_routes.add(_repo_route(loose["route"]))
        for hub_group in (camp.get("hubs") or {}).values():
            for ent in hub_group.get("entities") or []:
                for paths in ent.get("files_by_kind", {}).values():
                    all_ingest_routes.update(_repo_route(p) for p in paths)

    manifest_routes = set(activation.get("routes") or [])
    dogfood_routes = set(dogfood_activation.get("routes") or [])
    overlap = sorted(all_ingest_routes & manifest_routes)
    not_in_manifest = sorted(all_ingest_routes - manifest_routes)
    overlap_dogfood = sorted(all_ingest_routes & dogfood_routes)
    not_in_dogfood = sorted(all_ingest_routes - dogfood_routes)

    return {
        "schema": SCHEMA_ID,
        "generated_at": _utc_now_z(),
        "corpus_root": "corpus/eldyrwild-markdown",
        "summary": {
            "campaign_count": len(campaigns),
            "session_pipeline_tiers": dict(sorted(tier_totals.items())),
            "pilot_blessed_sessions": [
                {"campaign_id": campaign_id_from_number(c), "session": s} for c, s in PILOT_BLESSED_SESSIONS
            ],
            "total_corpus_md_files": len(list(corpus.rglob("*.md"))) if corpus.is_dir() else 0,
        },
        "campaigns": campaigns,
        "elderwyld": _scan_elderwyld(corpus / "Elderwyld", root=corpus),
        "live_workspaces": _scan_live_workspaces(repo),
        "eval_ingest_artifacts": _scan_eval_ingest_artifacts(repo),
        "retrieval_activation": {
            "c2s23_planning_manifest": activation,
            "c2s23_dogfood_full_manifest": dogfood_activation,
            "ingest_routes_on_disk": len(all_ingest_routes),
            "ingest_routes_in_c2s23_manifest": len(overlap),
            "ingest_routes_not_in_c2s23_manifest": len(not_in_manifest),
            "ingest_routes_in_dogfood_full_manifest": len(overlap_dogfood),
            "ingest_routes_not_in_dogfood_full_manifest": len(not_in_dogfood),
            "sample_routes_not_in_manifest": not_in_manifest[:25],
            "sample_routes_not_in_dogfood_manifest": not_in_dogfood[:25],
        },
    }


def _render_markdown(lib: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Ingested corpus library",
        "",
        f"- **schema:** `{lib['schema']}`",
        f"- **generated_at:** {lib['generated_at']}",
        f"- **corpus_root:** `{lib['corpus_root']}`",
        "",
        "## Summary",
        "",
    ]
    summary = lib["summary"]
    lines.append(f"- Campaigns indexed: **{summary['campaign_count']}**")
    lines.append(f"- Total corpus `.md` files: **{summary['total_corpus_md_files']}**")
    lines.append("- Session pipeline tiers:")
    for tier, count in sorted((summary.get("session_pipeline_tiers") or {}).items()):
        lines.append(f"  - `{tier}`: {count} sessions")
    lines.append("")

    act = lib["retrieval_activation"]
    man = act["c2s23_planning_manifest"]
    lines.extend(
        [
            "## Retrieval activation vs full ingest",
            "",
            f"The C2S23 planning manifest (`{man.get('manifest_path')}`) activates **{man.get('entry_count')}** routes",
            f"for planning session **{man.get('planning_session')}** with source sessions **{man.get('source_sessions')}**.",
            "",
            f"- Ingest-related routes on disk (sessions + hubs + prep): **{act['ingest_routes_on_disk']}**",
            f"- Overlap with C2S23 manifest: **{act['ingest_routes_in_c2s23_manifest']}**",
            f"- Not in C2S23 manifest: **{act['ingest_routes_not_in_c2s23_manifest']}**",
            "",
        ]
    )
    dogfood = act.get("c2s23_dogfood_full_manifest") or {}
    if dogfood.get("exists"):
        lines.extend(
            [
                f"The dogfood-full manifest (`{dogfood.get('manifest_path')}`) activates **{dogfood.get('entry_count')}** routes",
                f"with source sessions **{dogfood.get('source_sessions')}**.",
                "",
                f"- Overlap with dogfood-full manifest: **{act['ingest_routes_in_dogfood_full_manifest']}**",
                f"- Not in dogfood-full manifest: **{act['ingest_routes_not_in_dogfood_full_manifest']}**",
                "",
            ]
        )

    for camp in lib["campaigns"]:
        cid = camp["campaign_id"]
        lines.extend([f"## {cid}", ""])
        lines.append(f"Sessions: **{camp['session_count']}** | Prep docs: **{len(camp.get('session_prep') or [])}**")
        loose = camp.get("loose_markdown") or []
        if loose:
            lines.append(f"| Loose campaign markdown (Factions, Cards, etc.): **{len(loose)}**")
        lines.append("")
        lines.append("| Session | Tier | Canon | Norm | Crumb | Memory | Staging | Blessed |")
        lines.append("|---------|------|-------|------|-------|--------|---------|---------|")
        for sess in camp["sessions"]:
            stages = sess.get("stages") or {}
            lines.append(
                "| {session} | `{tier}` | {canon} | {norm} | {crumb} | {mem} | {stg} | {bless} |".format(
                    session=sess["session"],
                    tier=sess["pipeline_tier"],
                    canon="yes" if "canon_recap" in stages else "—",
                    norm="yes" if "normalized" in stages else "—",
                    crumb="yes" if "breadcrumbed" in stages else "—",
                    mem="yes" if "session_memory_jsonl" in stages else "—",
                    stg="yes" if "ingest_staging" in stages else "—",
                    bless="yes" if sess.get("pilot_blessed") else "—",
                )
            )
        lines.append("")
        for hub_name, hub in sorted((camp.get("hubs") or {}).items()):
            totals = hub.get("file_kind_totals") or {}
            if not hub.get("entity_count"):
                continue
            lines.append(
                f"### {hub_name} — {hub['entity_count']} entities "
                f"({', '.join(f'{k}:{v}' for k, v in sorted(totals.items()))})"
            )
            lines.append("")

    elder = lib.get("elderwyld") or {}
    if elder.get("exists"):
        lines.extend(
            [
                "## Elderwyld (world layer)",
                "",
                f"- Markdown files: **{elder.get('md_file_count')}**",
                f"- Top-level dirs: {', '.join(elder.get('top_level_dirs') or [])}",
                "",
            ]
        )

    live = lib.get("live_workspaces") or []
    if live:
        lines.extend(["## Live workspaces (eval)", ""])
        for row in live:
            arts = ", ".join(a["basename"] for a in row.get("artifacts") or [])
            lines.append(f"- Session **{row.get('session')}**: `{row.get('workspace_dir')}` — {arts}")
        lines.append("")

    lines.extend(
        [
            "## Regenerate",
            "",
            "```bash",
            "uv run python scripts/build_ingested_corpus_library.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--stdout", action="store_true", help="Print JSON summary to stdout")
    args = parser.parse_args()

    root = repo_root()
    library = build_library(root=root)

    json_out = (root / args.json_out).resolve()
    md_out = (root / args.markdown_out).resolve()
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(library, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(_render_markdown(library), encoding="utf-8")

    if args.stdout:
        print(
            json.dumps(
                {
                    "json_out": str(json_out),
                    "markdown_out": str(md_out),
                    "summary": library["summary"],
                    "retrieval_activation": library["retrieval_activation"],
                },
                indent=2,
            )
        )
    else:
        print(f"Wrote {json_out}")
        print(f"Wrote {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
