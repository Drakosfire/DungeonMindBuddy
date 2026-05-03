"""Smoke-test inline recap breadcrumb artifacts.

This is deliberately deterministic: parse frontmatter boundaries and inline tags,
compare model artifacts against a manual baseline, and dry-run append timeline rows
for PC/NPC tags whose hub routes expose ``timeline.md``.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.corpus_writer import append_timeline_row

TAG_RE = re.compile(r"\[([A-Za-z]+)\]\[([^\]]+)\]")
ALLOWED_TAG_TYPES = {"PC", "NPC", "Location", "Party", "NewHubCandidate"}
TIMELINE_TAG_TYPES = {"PC", "NPC"}
SCHEMA_MARKERS = {
    "schema: dmb_recap_breadcrumbs_v1",
    'schema: "dmb_recap_breadcrumbs_v1"',
    "dmb_schema: dmb_recap_breadcrumbs_v1",
    'dmb_schema: "dmb_recap_breadcrumbs_v1"',
}


@dataclass(frozen=True)
class InlineTag:
    tag_type: str
    route: str
    line_number: int
    raw: str

    @property
    def normalized_route(self) -> str:
        return normalize_corpus_route(self.route)

    @property
    def slug(self) -> str:
        route = self.normalized_route.rstrip("/")
        if route.endswith(".md"):
            return Path(route).stem
        return route.rsplit("/", 1)[-1]


def normalize_corpus_route(route: str) -> str:
    cleaned = route.strip().replace("\\", "/")
    prefix = "corpus/eldyrwild-markdown/"
    if cleaned.startswith(prefix):
        cleaned = cleaned[len(prefix) :]
    return cleaned.lstrip("/")


def parse_frontmatter_and_body(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1 :])
    return None, text


def parse_inline_tags(text: str) -> list[InlineTag]:
    tags: list[InlineTag] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in TAG_RE.finditer(line):
            tags.append(
                InlineTag(
                    tag_type=match.group(1),
                    route=match.group(2),
                    line_number=line_no,
                    raw=match.group(0),
                )
            )
    return tags


def route_exists(corpus_root: Path, route: str) -> bool:
    rel = normalize_corpus_route(route)
    return (corpus_root / rel).exists()


def route_timeline_path(corpus_root: Path, route: str) -> str | None:
    rel = normalize_corpus_route(route).rstrip("/")
    if rel.endswith(".md"):
        return None
    if "/NPCs/" not in rel and "/PCs/" not in rel:
        return None
    timeline = corpus_root / rel / "timeline.md"
    if timeline.is_file():
        return f"{rel}/timeline.md"
    return None


def dry_run_timeline_append(
    *,
    corpus_root: Path,
    tag: InlineTag,
    session: int,
    recap_path: str,
) -> dict[str, Any]:
    timeline_path = route_timeline_path(corpus_root, tag.normalized_route)
    if timeline_path is None:
        return {
            "ok": False,
            "skipped": True,
            "reason": "no timeline.md under routed PC/NPC hub",
        }
    return append_timeline_row(
        corpus_root,
        npc_slug=tag.slug,
        session=session,
        beat=f"Breadcrumb smoke route for {tag.slug}",
        recap_path=recap_path,
        timeline_path=timeline_path,
        dry_run=True,
    )


def tag_multiset(tags: list[InlineTag]) -> Counter[tuple[str, str]]:
    return Counter((tag.tag_type, tag.normalized_route) for tag in tags)


def compare_to_baseline(tags: list[InlineTag], baseline_tags: list[InlineTag]) -> dict[str, Any]:
    got = tag_multiset(tags)
    base = tag_multiset(baseline_tags)
    overlap = got & base
    extra = got - base
    missing = base - got
    got_total = sum(got.values())
    base_total = sum(base.values())
    overlap_total = sum(overlap.values())
    return {
        "baseline_tag_total": base_total,
        "artifact_tag_total": got_total,
        "overlap_tag_total": overlap_total,
        "precision_vs_baseline": round(overlap_total / got_total, 6) if got_total else 0.0,
        "recall_vs_baseline": round(overlap_total / base_total, 6) if base_total else 0.0,
        "extra_routes": [
            {"tag_type": k[0], "route": k[1], "count": v}
            for k, v in sorted(extra.items())
        ],
        "missing_routes": [
            {"tag_type": k[0], "route": k[1], "count": v}
            for k, v in sorted(missing.items())
        ],
    }


def summarize_artifact(
    *,
    artifact_path: Path,
    corpus_root: Path,
    source_recap_path: str,
    session: int,
    baseline_tags: list[InlineTag] | None,
) -> dict[str, Any]:
    text = artifact_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter_and_body(text)
    # Inline breadcrumb tags live in the recap body. Frontmatter includes tag grammar
    # examples that intentionally look tag-shaped but are not routed spans.
    tags = parse_inline_tags(body)
    tag_counts = Counter(tag.tag_type for tag in tags)
    unknown = sorted({tag.tag_type for tag in tags if tag.tag_type not in ALLOWED_TAG_TYPES})

    route_checks: list[dict[str, Any]] = []
    append_checks: list[dict[str, Any]] = []
    seen_routes: set[tuple[str, str]] = set()
    for tag in tags:
        key = (tag.tag_type, tag.normalized_route)
        if key in seen_routes:
            continue
        seen_routes.add(key)
        exists = route_exists(corpus_root, tag.normalized_route)
        route_checks.append(
            {
                "tag_type": tag.tag_type,
                "route": tag.normalized_route,
                "exists": exists,
                "line_number": tag.line_number,
            }
        )
        if tag.tag_type in TIMELINE_TAG_TYPES:
            preview = dry_run_timeline_append(
                corpus_root=corpus_root,
                tag=tag,
                session=session,
                recap_path=source_recap_path,
            )
            append_checks.append(
                {
                    "tag_type": tag.tag_type,
                    "route": tag.normalized_route,
                    "slug": tag.slug,
                    "ok": bool(preview.get("ok")),
                    "phase": preview.get("phase"),
                    "skipped": bool(preview.get("skipped")),
                    "error": preview.get("error") or preview.get("reason"),
                    "path": preview.get("path"),
                }
            )

    missing_routes = [r for r in route_checks if not r["exists"] and r["tag_type"] != "NewHubCandidate"]
    append_failures = [
        a
        for a in append_checks
        if not a["ok"] and not (a["skipped"] and a.get("error") == "no timeline.md under routed PC/NPC hub")
    ]
    append_skips = [a for a in append_checks if a["skipped"]]
    summary: dict[str, Any] = {
        "artifact_path": str(artifact_path),
        "parse": {
            "frontmatter_present": frontmatter is not None,
            "schema_marker_present": any(marker in text for marker in SCHEMA_MARKERS),
            "counts_block_present": "counts_by_subject_type:" in text,
            "body_nonempty": bool(body.strip()),
        },
        "tag_counts": dict(sorted(tag_counts.items())),
        "tag_total": len(tags),
        "unknown_tag_types": unknown,
        "route_checks": {
            "unique_routes": len(route_checks),
            "missing_non_candidate_routes": missing_routes,
        },
        "timeline_append_dry_run": {
            "checked": len(append_checks),
            "ok": sum(1 for a in append_checks if a["ok"]),
            "skipped_no_timeline": len(append_skips),
            "failures": append_failures,
        },
    }
    if baseline_tags is not None:
        summary["baseline_comparison"] = compare_to_baseline(tags, baseline_tags)
    return summary


def default_artifact_paths(root: Path) -> list[Path]:
    base = root / "evals/sentence_routing_retrieval_falsification/manual_labels"
    paths = [base / "Session 20 - Recap.breadcrumbed.md"]
    paths.extend(sorted((base / "artifacts").glob("Session 20 - Recap.breadcrumbed.*.md")))
    return [p for p in paths if p.is_file()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test inline breadcrumb artifacts.")
    parser.add_argument("--artifact", type=Path, action="append", default=None)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--corpus-root", type=Path, default=Path("corpus/eldyrwild-markdown"))
    parser.add_argument(
        "--source-recap-path",
        default="Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
    )
    parser.add_argument("--session", type=int, default=20)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    corpus_root = (repo_root / args.corpus_root).resolve() if not args.corpus_root.is_absolute() else args.corpus_root
    artifacts = [p.resolve() for p in args.artifact] if args.artifact else default_artifact_paths(repo_root)
    baseline_path = (repo_root / args.baseline).resolve() if not args.baseline.is_absolute() else args.baseline
    baseline_tags: list[InlineTag] = []
    if baseline_path.is_file():
        _baseline_frontmatter, baseline_body = parse_frontmatter_and_body(
            baseline_path.read_text(encoding="utf-8")
        )
        baseline_tags = parse_inline_tags(baseline_body)

    payload = {
        "schema": "inline_recap_breadcrumb_smoke_v1",
        "iso_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_path": str(baseline_path),
        "corpus_root": str(corpus_root),
        "source_recap_path": args.source_recap_path,
        "artifacts": [
            summarize_artifact(
                artifact_path=p,
                corpus_root=corpus_root,
                source_recap_path=args.source_recap_path,
                session=args.session,
                baseline_tags=baseline_tags if p != baseline_path else None,
            )
            for p in artifacts
        ],
    }
    out_path = args.out
    if out_path is None:
        out_dir = repo_root / "evals/sentence_routing_retrieval_falsification/manual_labels/artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = out_dir / f"inline_breadcrumb_smoke--{stamp}.json"
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(str(out_path))
    for row in payload["artifacts"]:
        print(
            json.dumps(
                {
                    "artifact": row["artifact_path"],
                    "tags": row["tag_counts"],
                    "unknown": row["unknown_tag_types"],
                    "missing_routes": len(row["route_checks"]["missing_non_candidate_routes"]),
                    "append_ok": row["timeline_append_dry_run"]["ok"],
                    "append_checked": row["timeline_append_dry_run"]["checked"],
                    "append_skipped_no_timeline": row["timeline_append_dry_run"]["skipped_no_timeline"],
                    "baseline_precision": (row.get("baseline_comparison") or {}).get("precision_vs_baseline"),
                    "baseline_recall": (row.get("baseline_comparison") or {}).get("recall_vs_baseline"),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
