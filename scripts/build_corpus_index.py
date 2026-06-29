#!/usr/bin/env python3
"""Build corpus directory index for Eldyrwild / Longmont markdown.

Writes:
  - corpus/CORPUS-INDEX.json   (machine-readable tree + file lists)
  - Docs/Anchors/CORPUS-ANCHOR.md (human re-anchor hierarchy)

Regenerate after adding session recaps or worldbuilding hubs:

  PYTHONPATH=. python scripts/build_corpus_index.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PRIMARY_CORPUS = REPO_ROOT / "corpus" / "eldyrwild-markdown"
UNPROCESSED_CORPUS = REPO_ROOT / "corpus" / "Eldyrwild and Campaign Unprocessed"
DRAFTS_CORPUS = REPO_ROOT / "corpus" / "_drafts"
JSON_OUT = REPO_ROOT / "corpus" / "CORPUS-INDEX.json"
MARKDOWN_OUT = REPO_ROOT / "Docs" / "Anchors" / "CORPUS-ANCHOR.md"

SCHEMA = "dmb_corpus_index_v1"
INDEX_VERSION = "1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(primary: Path, path: Path) -> str:
    return path.relative_to(primary).as_posix()


def _dir_tree(primary: Path, rel_root: str, *, max_depth: int) -> dict[str, Any]:
    base = primary / rel_root
    if not base.is_dir():
        return {"path": rel_root, "exists": False, "directories": [], "markdown_files": []}

    directories: list[dict[str, Any]] = []
    markdown_files: list[str] = []

    for p in sorted(base.rglob("*")):
        rel = _rel(primary, p)
        depth = len(Path(rel_root).parts) + len(p.relative_to(base).parts)
        if depth > max_depth:
            continue
        if p.is_file() and p.suffix.lower() == ".md":
            if p.parent == base:
                markdown_files.append(rel)
        elif p.is_dir() and p != base:
            child_rel = _rel(primary, p)
            if len(Path(child_rel).parts) - len(Path(rel_root).parts) <= max_depth:
                md_here = sorted(
                    _rel(primary, f)
                    for f in p.glob("*.md")
                )
                subdirs = sorted(
                    d.name
                    for d in p.iterdir()
                    if d.is_dir() and not d.name.startswith(".")
                )
                directories.append(
                    {
                        "path": child_rel,
                        "markdown_at_level": md_here,
                        "subdirectories": subdirs,
                        "markdown_file_count_recursive": len(list(p.rglob("*.md"))),
                    }
                )

    return {
        "path": rel_root,
        "exists": True,
        "markdown_at_level": markdown_files,
        "directories": directories,
    }


def _session_recap_inventory(primary: Path, campaign: str) -> dict[str, Any]:
    base = primary / "Longmont Campaign" / campaign / "Session Recaps"
    buckets: dict[str, list[str]] = defaultdict(list)
    if not base.is_dir():
        return {"campaign": campaign, "exists": False, "buckets": {}}

    for p in sorted(base.rglob("*.md")):
        rel = _rel(primary, p)
        parts = p.relative_to(base).parts
        if len(parts) == 1:
            bucket = "canonical"
        elif parts[0].startswith("_"):
            bucket = parts[0]
        else:
            bucket = "other"
        buckets[bucket].append(rel)

    return {
        "campaign": campaign,
        "path": f"Longmont Campaign/{campaign}/Session Recaps",
        "exists": True,
        "buckets": {k: buckets[k] for k in sorted(buckets)},
        "counts": {k: len(v) for k, v in buckets.items()},
    }


def _campaign_directories(primary: Path, campaign: str) -> dict[str, Any]:
    base = primary / "Longmont Campaign" / campaign
    out: dict[str, Any] = {"campaign": campaign, "path": f"Longmont Campaign/{campaign}", "directories": {}}
    if not base.is_dir():
        out["exists"] = False
        return out
    out["exists"] = True
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        out["directories"][d.name] = {
            "path": _rel(primary, d),
            "markdown_file_count": len(list(d.rglob("*.md"))),
        }
    return out


def build_index() -> dict[str, Any]:
    primary = PRIMARY_CORPUS
    markdown_total = len(list(primary.rglob("*.md"))) if primary.is_dir() else 0
    return {
        "schema": SCHEMA,
        "version": INDEX_VERSION,
        "generated_at": _utc_now(),
        "repo_root": str(REPO_ROOT),
        "corpus_roots": {
            "primary_markdown": {
                "path": "corpus/eldyrwild-markdown",
                "exists": primary.is_dir(),
                "markdown_file_count": markdown_total,
                "role": "Canonical Eldyrwild + Longmont markdown corpus (read/write target for recap ingest and worldbuilding).",
            },
            "unprocessed_pipeline": {
                "path": "corpus/Eldyrwild and Campaign Unprocessed",
                "exists": UNPROCESSED_CORPUS.is_dir(),
                "role": "Pipeline stage artifacts (Stage A/B surfaces, evaluation reports). Not primary markdown source.",
            },
            "drafts": {
                "path": "corpus/_drafts",
                "exists": DRAFTS_CORPUS.is_dir(),
                "role": "Scratch / in-progress corpus drafts.",
            },
        },
        "session_recaps": {
            "campaign_1": _session_recap_inventory(primary, "Campaign 1"),
            "campaign_2": _session_recap_inventory(primary, "Campaign 2"),
        },
        "longmont_campaigns": {
            "campaign_1": _campaign_directories(primary, "Campaign 1"),
            "campaign_2": _campaign_directories(primary, "Campaign 2"),
            "shared": _longmont_shared(primary),
        },
        "worldbuilding": {
            "elderwyld_root": "Elderwyld",
            "tree": _dir_tree(primary, "Elderwyld", max_depth=3),
            "top_level_markdown": sorted(
                _rel(primary, p) for p in (primary / "Elderwyld").glob("*.md")
            )
            if (primary / "Elderwyld").is_dir()
            else [],
        },
        "related_modules": {
            "session_recap_paths": "src/corpus/session_recap_paths.py",
            "planning_corpus_manifest": "src/live_play/planning_corpus_manifest.py",
            "batch_ingest": "tools/batch_ingest_corpus.py",
        },
    }


def _longmont_shared(primary: Path) -> dict[str, Any]:
    base = primary / "Longmont Campaign"
    out: dict[str, Any] = {"path": "Longmont Campaign", "directories": {}}
    if not base.is_dir():
        out["exists"] = False
        return out
    out["exists"] = True
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name.startswith("Campaign"):
            continue
        out["directories"][d.name] = {
            "path": _rel(primary, d),
            "markdown_file_count": len(list(d.rglob("*.md"))),
        }
    return out


def _md_list(title: str, paths: list[str]) -> list[str]:
    lines = [f"### {title} ({len(paths)})", ""]
    if not paths:
        lines.append("_None._")
        lines.append("")
        return lines
    for p in paths:
        lines.append(f"- `{p}`")
    lines.append("")
    return lines


def render_markdown(index: dict[str, Any]) -> str:
    roots = index["corpus_roots"]
    c1 = index["session_recaps"]["campaign_1"]
    c2 = index["session_recaps"]["campaign_2"]
    wb = index["worldbuilding"]
    lc1 = index["longmont_campaigns"]["campaign_1"]
    lc2 = index["longmont_campaigns"]["campaign_2"]
    shared = index["longmont_campaigns"]["shared"]

    lines = [
        "# Corpus Anchor — Eldyrwild / Longmont Markdown",
        "",
        f"Generated: `{index['generated_at']}` · schema `{index['schema']}` v{index['version']}",
        "",
        "Regenerate:",
        "",
        "```bash",
        "PYTHONPATH=. python scripts/build_corpus_index.py",
        "```",
        "",
        "Machine-readable companion: [`corpus/CORPUS-INDEX.json`](../../corpus/CORPUS-INDEX.json)",
        "",
        "## Purpose",
        "",
        "Re-anchor source for **where campaign recaps and worldbuilding markdown live** in this repo.",
        "Use before graph-memory vocabulary work, recap ingest, planning manifests, or corpus-grounded extraction.",
        "",
        "Paths below are **repo-relative** from the DungeonMindBuddy root.",
        "",
        "## Corpus roots",
        "",
        "| Root | Path | Role |",
        "|------|------|------|",
        f"| Primary markdown | `{roots['primary_markdown']['path']}` | {roots['primary_markdown']['role']} ({roots['primary_markdown']['markdown_file_count']} `.md` files) |",
        f"| Unprocessed pipeline | `{roots['unprocessed_pipeline']['path']}` | {roots['unprocessed_pipeline']['role']} |",
        f"| Drafts | `{roots['drafts']['path']}` | {roots['drafts']['role']} |",
        "",
        "**Read rule:** prefer `corpus/eldyrwild-markdown/` for canonical prose. Treat `_normalized`, `_breadcrumbed`, `_session_memory`, and `_archive` as **derived** ingest artifacts unless a task explicitly targets them.",
        "",
        "## Session recaps — authority buckets",
        "",
        "| Bucket | Meaning |",
        "|--------|---------|",
        "| `canonical` | GM-authored recap files at `Session Recaps/` root |",
        "| `_normalized` | Mechanical normalized recap (graph ingest input) |",
        "| `_breadcrumbed` | Legacy breadcrumb derivatives |",
        "| `_archive` | Timestamped archive copies |",
        "| `_session_memory` | Derived session-memory JSONL companions (when present) |",
        "",
        "Path helpers: `src/corpus/session_recap_paths.py`",
        "",
        "## Campaign 1 — Session Recaps",
        "",
        f"Base: `corpus/eldyrwild-markdown/{c1['path']}`",
        "",
    ]
    for bucket, paths in c1.get("buckets", {}).items():
        lines.extend(_md_list(bucket, paths))

    lines.extend(
        [
            "## Campaign 2 — Session Recaps",
            "",
            f"Base: `corpus/eldyrwild-markdown/{c2['path']}`",
            "",
        ]
    )
    for bucket, paths in c2.get("buckets", {}).items():
        lines.extend(_md_list(bucket, paths))

    lines.extend(["## Longmont Campaign directories", ""])
    for camp_label, camp in [("Campaign 1", lc1), ("Campaign 2", lc2)]:
        lines.append(f"### {camp_label}")
        lines.append("")
        for name, meta in sorted(camp.get("directories", {}).items()):
            lines.append(f"- `{meta['path']}/` — {meta['markdown_file_count']} markdown files")
        lines.append("")

    lines.extend(["### Shared (outside Campaign 1/2 folders)", ""])
    for name, meta in sorted(shared.get("directories", {}).items()):
        lines.append(f"- `{meta['path']}/` — {meta['markdown_file_count']} markdown files")
    lines.append("")

    lines.extend(["## Worldbuilding — Elderwyld", ""])
    lines.append(f"Root: `corpus/eldyrwild-markdown/{wb['elderwyld_root']}/`")
    lines.append("")
    lines.extend(_md_list("Top-level markdown", wb.get("top_level_markdown", [])))

    lines.extend(["### Directory tree (depth ≤ 3)", ""])
    tree = wb.get("tree", {})
    for entry in tree.get("directories", []):
        count = entry.get("markdown_file_count_recursive", 0)
        subs = ", ".join(entry.get("subdirectories") or []) or "—"
        lines.append(f"- `{entry['path']}/` — {count} `.md` (recursive); subdirs: {subs}")
    lines.append("")

    lines.extend(
        [
            "## Related tooling",
            "",
            "| Module | Path |",
            "|--------|------|",
            "| Session recap path helpers | `src/corpus/session_recap_paths.py` |",
            "| C2 planning corpus manifest | `src/live_play/planning_corpus_manifest.py` |",
            "| Batch corpus ingest | `tools/batch_ingest_corpus.py` |",
            "",
            "## Re-anchor checklist (corpus scope)",
            "",
            "1. Confirm you are reading from `corpus/eldyrwild-markdown/`, not unprocessed pipeline output.",
            "2. For play facts, prefer canonical recaps or `_normalized` (ingest input), not `_breadcrumbed`.",
            "3. For setting vocabulary, start at Elderwyld location hubs (`README.md` indexes under `Elderwyld/Cities and Towns/`).",
            "4. Re-run `scripts/build_corpus_index.py` after adding sessions or major worldbuilding hubs.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    index = build_index()
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_OUT.write_text(render_markdown(index), encoding="utf-8")
    print(f"Wrote {JSON_OUT.relative_to(REPO_ROOT)}")
    print(f"Wrote {MARKDOWN_OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
