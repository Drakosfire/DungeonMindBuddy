"""Unit-level breadcrumb route scorer.

Reads a breadcrumb markdown artifact, normalizes it to ``dmb_session_memory_record_v1``
records, and applies sentinel positive/negative checks plus protected-set precision
metrics so we can measure whether a prompt or repair-stage variant closes specific
under-tagged scenes without sliding into NER-style over-routing.

The scorer is deterministic: it does not call any LLM. The optional ``baseline``
artifact is used only for tag-multiset precision/recall context, mirroring
``breadcrumb_smoke.compare_to_baseline``.

Sentinel rules
==============

A "sentinel" is a list of ``unit_id``s plus a list of route substrings the unit must
have. We support:

* ``positive_units`` — every listed unit MUST contain every listed route substring on
  at least one route normalized via ``normalize_corpus_route``. Missing-on-unit is a
  failure.
* ``negative_units`` — every listed unit MUST NOT contain any listed route substring
  on any of its routes. Hit is a failure (over-routing).
* ``protected_units`` — every listed unit must keep AT LEAST the listed route
  substrings (no regression of already-good routes). Missing-on-unit is a failure.

Sentinels are JSON in the shape::

    {
      "schema": "dmb_breadcrumb_tagging_sentinels_v1",
      "session_number": 20,
      "positive_units": [
        {"unit_id": "u-L0019-09", "must_contain": ["captain_lysandra_ironveil", "Voices Tower"]}
      ],
      "negative_units": [
        {"unit_id": "u-L0019-02", "must_not_contain": ["captain_lysandra_ironveil"]}
      ],
      "protected_units": [
        {"unit_id": "u-L0019-06", "must_contain": ["captain_lysandra_ironveil"]}
      ]
    }

Output schema: ``dmb_breadcrumb_tagging_score_v1``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    BreadcrumbNormalizeError,
    NormalizedRecord,
    normalize_breadcrumb_artifact,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    compare_to_baseline,
    parse_frontmatter_and_body,
    parse_inline_tags,
)

SCHEMA_OUT = "dmb_breadcrumb_tagging_score_v1"
SENTINELS_SCHEMA = "dmb_breadcrumb_tagging_sentinels_v1"


@dataclass(frozen=True)
class SentinelCheck:
    unit_id: str
    must_contain: tuple[str, ...] = ()
    must_not_contain: tuple[str, ...] = ()


def _read_sentinels(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SENTINELS_SCHEMA:
        raise ValueError(
            f"sentinels file must declare schema {SENTINELS_SCHEMA}; got {data.get('schema')!r}"
        )
    return data


def _records_by_unit(records: list[NormalizedRecord]) -> dict[str, NormalizedRecord]:
    return {r.unit_id: r for r in records}


def _routes_for_unit(record: NormalizedRecord | None) -> list[str]:
    if record is None:
        return []
    return [att.normalized_route for att in record.routes]


def _eval_positive(
    *,
    unit_id: str,
    must_contain: tuple[str, ...],
    record: NormalizedRecord | None,
) -> dict[str, Any]:
    routes = _routes_for_unit(record)
    missing: list[str] = []
    for needle in must_contain:
        n = needle.lower()
        if not any(n in r.lower() for r in routes):
            missing.append(needle)
    return {
        "unit_id": unit_id,
        "expected_substrings": list(must_contain),
        "found_routes": routes,
        "missing_substrings": missing,
        "passed": not missing,
        "unit_present": record is not None,
    }


def _eval_negative(
    *,
    unit_id: str,
    must_not_contain: tuple[str, ...],
    record: NormalizedRecord | None,
) -> dict[str, Any]:
    routes = _routes_for_unit(record)
    over_hits: list[str] = []
    for needle in must_not_contain:
        n = needle.lower()
        for r in routes:
            if n in r.lower():
                over_hits.append(needle)
                break
    return {
        "unit_id": unit_id,
        "forbidden_substrings": list(must_not_contain),
        "found_routes": routes,
        "over_routed_substrings": over_hits,
        "passed": not over_hits,
        "unit_present": record is not None,
    }


def score_artifact(
    *,
    artifact_path: Path,
    corpus_root: Path,
    sentinels: dict[str, Any] | None,
    baseline_artifact_path: Path | None,
) -> dict[str, Any]:
    text = artifact_path.read_text(encoding="utf-8")
    try:
        records, meta = normalize_breadcrumb_artifact(
            artifact_text=text, corpus_root=corpus_root
        )
        normalize_error: str | None = None
    except BreadcrumbNormalizeError as exc:
        records = []
        meta = {}
        normalize_error = str(exc)

    by_unit = _records_by_unit(records)
    total_route_attachments = sum(len(r.routes) for r in records)
    units_with_routes = sum(1 for r in records if r.routes)
    tag_class_counter: Counter[str] = Counter()
    for r in records:
        for att in r.routes:
            tag_class_counter[att.subject_class] += 1

    positive_results: list[dict[str, Any]] = []
    negative_results: list[dict[str, Any]] = []
    protected_results: list[dict[str, Any]] = []

    if sentinels is not None:
        for entry in sentinels.get("positive_units", []) or []:
            uid = str(entry["unit_id"])
            positive_results.append(
                _eval_positive(
                    unit_id=uid,
                    must_contain=tuple(entry.get("must_contain", []) or []),
                    record=by_unit.get(uid),
                )
            )
        for entry in sentinels.get("negative_units", []) or []:
            uid = str(entry["unit_id"])
            negative_results.append(
                _eval_negative(
                    unit_id=uid,
                    must_not_contain=tuple(entry.get("must_not_contain", []) or []),
                    record=by_unit.get(uid),
                )
            )
        for entry in sentinels.get("protected_units", []) or []:
            uid = str(entry["unit_id"])
            protected_results.append(
                _eval_positive(
                    unit_id=uid,
                    must_contain=tuple(entry.get("must_contain", []) or []),
                    record=by_unit.get(uid),
                )
            )

    sentinel_summary = {
        "positive_total": len(positive_results),
        "positive_passed": sum(1 for r in positive_results if r["passed"]),
        "negative_total": len(negative_results),
        "negative_passed": sum(1 for r in negative_results if r["passed"]),
        "protected_total": len(protected_results),
        "protected_passed": sum(1 for r in protected_results if r["passed"]),
    }
    sentinel_summary["all_passed"] = all(
        sentinel_summary[k + "_total"] == sentinel_summary[k + "_passed"]
        for k in ("positive", "negative", "protected")
    )

    baseline_block: dict[str, Any] | None = None
    if baseline_artifact_path is not None and baseline_artifact_path.is_file():
        _baseline_fm, baseline_body = parse_frontmatter_and_body(
            baseline_artifact_path.read_text(encoding="utf-8")
        )
        baseline_tags = parse_inline_tags(baseline_body)
        _fm, body = parse_frontmatter_and_body(text)
        artifact_tags = parse_inline_tags(body)
        baseline_block = {
            "baseline_path": str(baseline_artifact_path),
            **compare_to_baseline(artifact_tags, baseline_tags),
        }

    return {
        "schema": SCHEMA_OUT,
        "artifact_path": str(artifact_path),
        "corpus_root": str(corpus_root),
        "normalize": {
            "ok": normalize_error is None,
            "error": normalize_error,
            "meta": meta,
            "unit_count": len(records),
            "units_with_routes": units_with_routes,
            "total_route_attachments": total_route_attachments,
            "tag_class_counts": dict(sorted(tag_class_counter.items())),
        },
        "sentinels": {
            "summary": sentinel_summary,
            "positive_units": positive_results,
            "negative_units": negative_results,
            "protected_units": protected_results,
        },
        "baseline_comparison": baseline_block,
    }


def score_cohort(
    *,
    artifact_paths: list[Path],
    corpus_root: Path,
    sentinels: dict[str, Any] | None,
    baseline_artifact_path: Path | None,
) -> dict[str, Any]:
    rows = [
        score_artifact(
            artifact_path=p,
            corpus_root=corpus_root,
            sentinels=sentinels,
            baseline_artifact_path=baseline_artifact_path
            if baseline_artifact_path != p
            else None,
        )
        for p in artifact_paths
    ]
    sentinel_pass_count = sum(1 for r in rows if r["sentinels"]["summary"].get("all_passed"))
    return {
        "schema": "dmb_breadcrumb_tagging_score_cohort_v1",
        "iso_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corpus_root": str(corpus_root),
        "sentinels_path": None,
        "baseline_artifact_path": str(baseline_artifact_path) if baseline_artifact_path else None,
        "artifacts": rows,
        "aggregate": {
            "artifact_count": len(rows),
            "sentinels_all_passed_count": sentinel_pass_count,
        },
    }


def render_markdown_summary(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Breadcrumb Tagging Scorer")
    lines.append("")
    lines.append(f"- iso_utc: `{report['iso_utc']}`")
    lines.append(f"- corpus_root: `{report['corpus_root']}`")
    if report.get("sentinels_path"):
        lines.append(f"- sentinels: `{report['sentinels_path']}`")
    lines.append(f"- baseline: `{report.get('baseline_artifact_path')}`")
    lines.append("")
    lines.append("| Artifact | Units | Routed | All sentinels | Pos | Neg | Prot | Recall vs baseline |")
    lines.append("| --- | ---: | ---: | :---: | :---: | :---: | :---: | ---: |")
    for row in report["artifacts"]:
        sentinel = row["sentinels"]["summary"]
        baseline = row.get("baseline_comparison") or {}
        recall = baseline.get("recall_vs_baseline")
        recall_s = f"{recall:.3f}" if isinstance(recall, (int, float)) else "—"
        lines.append(
            f"| `{Path(row['artifact_path']).name}` | "
            f"{row['normalize']['unit_count']} | "
            f"{row['normalize']['units_with_routes']} | "
            f"{'PASS' if sentinel.get('all_passed') else 'FAIL'} | "
            f"{sentinel.get('positive_passed')}/{sentinel.get('positive_total')} | "
            f"{sentinel.get('negative_passed')}/{sentinel.get('negative_total')} | "
            f"{sentinel.get('protected_passed')}/{sentinel.get('protected_total')} | "
            f"{recall_s} |"
        )
    lines.append("")
    for row in report["artifacts"]:
        if row["normalize"]["error"]:
            lines.append(
                f"- `{Path(row['artifact_path']).name}` normalize error: "
                f"`{row['normalize']['error']}`"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score breadcrumb artifacts vs sentinels.")
    parser.add_argument("--artifact", type=Path, action="append", required=True)
    parser.add_argument("--sentinels", type=Path, default=None)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(
            "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--corpus-root", type=Path, default=Path("corpus/eldyrwild-markdown"))
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    corpus_root = (
        (repo_root / args.corpus_root).resolve()
        if not args.corpus_root.is_absolute()
        else args.corpus_root
    )
    baseline_path = (
        (repo_root / args.baseline).resolve()
        if args.baseline is not None and not args.baseline.is_absolute()
        else args.baseline
    )
    sentinels = _read_sentinels(args.sentinels) if args.sentinels else None
    artifact_paths = [
        p.resolve() if p.is_absolute() else (repo_root / p).resolve() for p in args.artifact
    ]

    report = score_cohort(
        artifact_paths=artifact_paths,
        corpus_root=corpus_root,
        sentinels=sentinels,
        baseline_artifact_path=baseline_path,
    )
    if args.sentinels:
        report["sentinels_path"] = str(args.sentinels.resolve())

    out_json = args.out_json
    if out_json is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = (
            repo_root
            / "evals/sentence_routing_retrieval_falsification/artifacts/runs"
            / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_json = out_dir / f"breadcrumb_tagging_score--{stamp}.json"
    out_json = out_json.resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(str(out_json))

    out_md = args.out_md
    if out_md is None:
        out_md = out_json.with_suffix(".md")
    out_md.write_text(render_markdown_summary(report), encoding="utf-8")
    print(str(out_md))

    for row in report["artifacts"]:
        sentinel = row["sentinels"]["summary"]
        baseline = row.get("baseline_comparison") or {}
        print(
            json.dumps(
                {
                    "artifact": Path(row["artifact_path"]).name,
                    "normalize_ok": row["normalize"]["ok"],
                    "units": row["normalize"]["unit_count"],
                    "routed_units": row["normalize"]["units_with_routes"],
                    "positive": f"{sentinel.get('positive_passed')}/{sentinel.get('positive_total')}",
                    "negative": f"{sentinel.get('negative_passed')}/{sentinel.get('negative_total')}",
                    "protected": f"{sentinel.get('protected_passed')}/{sentinel.get('protected_total')}",
                    "all_pass": sentinel.get("all_passed"),
                    "baseline_recall": baseline.get("recall_vs_baseline"),
                    "baseline_precision": baseline.get("precision_vs_baseline"),
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
