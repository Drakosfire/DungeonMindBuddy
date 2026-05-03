"""Run a focused breadcrumb tagging cohort with one model + variant prompt.

This is the experiment surface for the Breadcrumb Tagging Experiment plan: drive a
small cohort (default ``n=3``) of generations through ``responses.create`` for a
single model (default ``gpt-5.3-codex``) and a single prompt variant, normalize
each artifact, score it against the sentinel set, and write a costed cohort
summary plus per-run artifacts to disk.

Run from repo root::

    uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_variant_runner \\
        --variant under_tagged_continuation_v1 --n 3

Outputs (default paths under ``evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/``):

* ``breadcrumb_tagging_variant--<variant>--<stamp>.cohort.json`` — cohort summary.
* ``breadcrumb_tagging_variant--<variant>--<stamp>.cohort.md`` — markdown summary.
* ``breadcrumb_tagging_variant--<variant>--<run_idx>.md`` — generated artifact.
* ``breadcrumb_tagging_variant--<variant>--<run_idx>.json`` — per-run sidecar
  (usage, cost, sentinel verdict, normalize status).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (  # noqa: E402
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_prompt import (  # noqa: E402
    ALLOWED_VARIANTS,
    PROMPT_VARIANT_CONTINUATION,
    PROMPT_VARIANT_CONTROL,
    build_breadcrumb_prompt,
    extract_breadcrumb_markdown,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_scorer import (  # noqa: E402
    score_artifact,
)
from src.agent.planner_pricing import usage_cost_usd  # noqa: E402
from src.agent.synthesis import _load_api_key  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402

DEFAULT_MODEL = "gpt-5.3-codex"
DEFAULT_RECAP_REL = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"
DEFAULT_FRONTMATTER_SOURCE = (
    "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md"
)
DEFAULT_SENTINELS = (
    "evals/sentence_routing_retrieval_falsification/gold/breadcrumb_tagging_sentinels_session20.json"
)


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _slugify_variant(variant: str) -> str:
    return variant.replace("/", "_").replace(" ", "_")


def _usage_tokens(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    cached = 0
    details = getattr(usage, "input_tokens_details", None)
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "cached_tokens": cached,
    }


def _read_recap_body(repo_root: Path, recap_rel: str, corpus_root: Path) -> str:
    recap_path = corpus_root / recap_rel
    text = recap_path.read_text(encoding="utf-8")
    _frontmatter, body = parse_frontmatter_and_body(text)
    return body


def _read_frontmatter(repo_root: Path, frontmatter_source: str) -> str:
    artifact = repo_root / frontmatter_source
    fm, _body = parse_frontmatter_and_body(artifact.read_text(encoding="utf-8"))
    if fm is None:
        raise RuntimeError(
            f"frontmatter source {frontmatter_source!r} has no YAML frontmatter"
        )
    return fm


def _call_responses_create(
    *,
    client: Any,
    model: str,
    instructions: str,
    user_text: str,
) -> tuple[Any, float]:
    t0 = time.perf_counter()
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=[{"type": "message", "role": "user", "content": user_text}],
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return response, elapsed_ms


def _run_one(
    *,
    client: Any,
    model: str,
    variant: str,
    recap_body: str,
    frontmatter_yaml: str,
    run_index: int,
    artifact_md_path: Path,
    artifact_json_path: Path,
    corpus_root: Path,
    sentinels: dict[str, Any],
) -> dict[str, Any]:
    prompt = build_breadcrumb_prompt(
        variant=variant,
        recap_body=recap_body,
        frontmatter_yaml=frontmatter_yaml,
    )
    response, elapsed_ms = _call_responses_create(
        client=client,
        model=model,
        instructions=prompt.system_text,
        user_text=prompt.user_text,
    )
    raw_text = (getattr(response, "output_text", None) or "").strip()
    breadcrumb_md = extract_breadcrumb_markdown(raw_text)

    artifact_md_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_md_path.write_text(breadcrumb_md, encoding="utf-8")

    usage = _usage_tokens(response)
    cost = usage_cost_usd(
        model_id=model,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
    )

    score = score_artifact(
        artifact_path=artifact_md_path,
        corpus_root=corpus_root,
        sentinels=sentinels,
        baseline_artifact_path=None,
    )

    sidecar = {
        "schema": "dmb_breadcrumb_tagging_variant_run_v1",
        "run_index": run_index,
        "model": model,
        "variant": variant,
        "elapsed_ms": round(elapsed_ms, 2),
        "response_id": str(getattr(response, "id", "")),
        "usage": usage,
        "cost_info": cost,
        "cost_usd": float(cost.get("total_usd") or 0.0),
        "raw_response_chars": len(raw_text),
        "artifact_md_path": str(artifact_md_path),
        "score": {
            "normalize_ok": score["normalize"]["ok"],
            "normalize_error": score["normalize"]["error"],
            "unit_count": score["normalize"]["unit_count"],
            "units_with_routes": score["normalize"]["units_with_routes"],
            "tag_class_counts": score["normalize"]["tag_class_counts"],
            "sentinels_summary": score["sentinels"]["summary"],
            "positive_units": score["sentinels"]["positive_units"],
            "negative_units": score["sentinels"]["negative_units"],
            "protected_units": score["sentinels"]["protected_units"],
        },
    }
    artifact_json_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_json_path.write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return sidecar


def _aggregate_cohort(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "cost_usd": {"sum": 0.0, "min": 0.0, "max": 0.0, "mean": 0.0},
            "sentinels": {"all_passed_count": 0, "positive_passed_count": 0,
                          "negative_passed_count": 0, "protected_passed_count": 0},
            "normalize_ok_count": 0,
        }
    costs = [float(r.get("cost_usd") or 0.0) for r in rows]
    pos_pass = sum(
        1
        for r in rows
        if r["score"]["sentinels_summary"].get("positive_passed", 0)
        == r["score"]["sentinels_summary"].get("positive_total", 0)
    )
    neg_pass = sum(
        1
        for r in rows
        if r["score"]["sentinels_summary"].get("negative_passed", 0)
        == r["score"]["sentinels_summary"].get("negative_total", 0)
    )
    prot_pass = sum(
        1
        for r in rows
        if r["score"]["sentinels_summary"].get("protected_passed", 0)
        == r["score"]["sentinels_summary"].get("protected_total", 0)
    )
    all_pass = sum(1 for r in rows if r["score"]["sentinels_summary"].get("all_passed"))
    return {
        "n": len(rows),
        "cost_usd": {
            "sum": round(sum(costs), 6),
            "min": round(min(costs), 6),
            "max": round(max(costs), 6),
            "mean": round(sum(costs) / len(costs), 6),
        },
        "sentinels": {
            "all_passed_count": all_pass,
            "positive_passed_count": pos_pass,
            "negative_passed_count": neg_pass,
            "protected_passed_count": prot_pass,
        },
        "normalize_ok_count": sum(1 for r in rows if r["score"]["normalize_ok"]),
    }


def _render_cohort_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Breadcrumb Tagging Variant Cohort — {report['variant']}")
    lines.append("")
    lines.append(f"- iso_utc: `{report['iso_utc']}`")
    lines.append(f"- model: `{report['model']}`")
    lines.append(f"- variant: `{report['variant']}`")
    lines.append(f"- n: {report['n']}")
    lines.append(f"- recap: `{report['recap_relative_path']}`")
    lines.append(f"- frontmatter source: `{report['frontmatter_source']}`")
    lines.append(f"- sentinels: `{report['sentinels_path']}`")
    agg = report["aggregate"]
    lines.append("")
    lines.append("## Cost")
    lines.append("")
    lines.append(
        f"- sum: ${agg['cost_usd']['sum']:.6f} | mean: ${agg['cost_usd']['mean']:.6f} | "
        f"min: ${agg['cost_usd']['min']:.6f} | max: ${agg['cost_usd']['max']:.6f}"
    )
    lines.append("")
    lines.append("## Sentinels")
    lines.append("")
    s = agg["sentinels"]
    lines.append(
        f"- all_passed: {s['all_passed_count']}/{report['n']}"
        f"  positive_passed: {s['positive_passed_count']}/{report['n']}"
        f"  negative_passed: {s['negative_passed_count']}/{report['n']}"
        f"  protected_passed: {s['protected_passed_count']}/{report['n']}"
    )
    lines.append(f"- normalize_ok_count: {agg['normalize_ok_count']}/{report['n']}")
    lines.append("")
    lines.append("## Per-run")
    lines.append("")
    lines.append("| run | normalize | pos | neg | prot | all | usd | output toks |")
    lines.append("| ---: | :---: | :---: | :---: | :---: | :---: | ---: | ---: |")
    for r in report["runs"]:
        s = r["score"]["sentinels_summary"]
        lines.append(
            f"| {r['run_index']} | "
            f"{'OK' if r['score']['normalize_ok'] else 'BAD'} | "
            f"{s.get('positive_passed')}/{s.get('positive_total')} | "
            f"{s.get('negative_passed')}/{s.get('negative_total')} | "
            f"{s.get('protected_passed')}/{s.get('protected_total')} | "
            f"{'PASS' if s.get('all_passed') else 'FAIL'} | "
            f"{r.get('cost_usd', 0):.6f} | "
            f"{r['usage']['output_tokens']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(ALLOWED_VARIANTS), required=True)
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--corpus-root", type=Path, default=Path("corpus/eldyrwild-markdown"))
    parser.add_argument("--recap-relative-path", default=DEFAULT_RECAP_REL)
    parser.add_argument("--frontmatter-source", default=DEFAULT_FRONTMATTER_SOURCE)
    parser.add_argument("--sentinels", type=Path, default=Path(DEFAULT_SENTINELS))
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=None,
        help="Override artifact runs root; defaults to evals/.../artifacts/runs/<date>/",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    corpus_root = (
        (repo_root / args.corpus_root).resolve()
        if not args.corpus_root.is_absolute()
        else args.corpus_root
    )
    sentinels_path = (
        args.sentinels.resolve()
        if args.sentinels.is_absolute()
        else (repo_root / args.sentinels).resolve()
    )
    sentinels = json.loads(sentinels_path.read_text(encoding="utf-8"))

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Add the key to repo .env or export it for CI.",
            file=sys.stderr,
        )
        return 2

    from openai import OpenAI

    client = OpenAI()

    recap_body = _read_recap_body(repo_root, args.recap_relative_path, corpus_root)
    frontmatter_yaml = _read_frontmatter(repo_root, args.frontmatter_source)

    runs_root = args.runs_root or (
        repo_root
        / "evals/sentence_routing_retrieval_falsification/artifacts/runs"
        / _now_date()
    )
    runs_root.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    variant_slug = _slugify_variant(args.variant)

    runs: list[dict[str, Any]] = []
    for idx in range(1, args.n + 1):
        artifact_md = runs_root / f"breadcrumb_tagging_variant--{variant_slug}--run{idx:02d}.md"
        artifact_json = runs_root / f"breadcrumb_tagging_variant--{variant_slug}--run{idx:02d}.json"
        sidecar = _run_one(
            client=client,
            model=args.model,
            variant=args.variant,
            recap_body=recap_body,
            frontmatter_yaml=frontmatter_yaml,
            run_index=idx,
            artifact_md_path=artifact_md,
            artifact_json_path=artifact_json,
            corpus_root=corpus_root,
            sentinels=sentinels,
        )
        runs.append(sidecar)
        s = sidecar["score"]["sentinels_summary"]
        print(
            json.dumps(
                {
                    "run": idx,
                    "normalize_ok": sidecar["score"]["normalize_ok"],
                    "positive": f"{s.get('positive_passed')}/{s.get('positive_total')}",
                    "negative": f"{s.get('negative_passed')}/{s.get('negative_total')}",
                    "protected": f"{s.get('protected_passed')}/{s.get('protected_total')}",
                    "all_pass": s.get("all_passed"),
                    "cost_usd": sidecar["cost_usd"],
                    "elapsed_ms": sidecar["elapsed_ms"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    cohort_report = {
        "schema": "dmb_breadcrumb_tagging_variant_cohort_v1",
        "iso_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": args.model,
        "variant": args.variant,
        "n": args.n,
        "recap_relative_path": args.recap_relative_path,
        "frontmatter_source": args.frontmatter_source,
        "sentinels_path": str(sentinels_path),
        "corpus_root": str(corpus_root),
        "aggregate": _aggregate_cohort(runs),
        "runs": runs,
    }

    cohort_json = runs_root / f"breadcrumb_tagging_variant--{variant_slug}--{stamp}.cohort.json"
    cohort_md = runs_root / f"breadcrumb_tagging_variant--{variant_slug}--{stamp}.cohort.md"
    cohort_json.write_text(
        json.dumps(cohort_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    cohort_md.write_text(_render_cohort_markdown(cohort_report), encoding="utf-8")

    print(json.dumps({
        "cohort_json": str(cohort_json),
        "cohort_md": str(cohort_md),
        "aggregate": cohort_report["aggregate"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
