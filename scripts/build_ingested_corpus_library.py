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
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_play.ingested_corpus_library import build_library
from live_play.session_paths import repo_root

DEFAULT_JSON_OUT = Path("Docs/data/ingested-corpus-library/ingested_corpus_library.json")
DEFAULT_MD_OUT = Path("Docs/data/ingested-corpus-library/ingested_corpus_library.md")


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
