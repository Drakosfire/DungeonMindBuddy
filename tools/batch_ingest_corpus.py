#!/usr/bin/env python3
"""Batch-ingest every markdown file under corpus/eldyrwild-markdown into one store.

Uses the same pipeline as the interactive CLI (frontmatter, gates, MODEL_POLICY).

Usage (from DungeonMindBuddy repo root):
  uv run python tools/batch_ingest_corpus.py --store out/stores/dungeonbuddy_store_batch

Optional:
  --corpus-root PATH   default: corpus/eldyrwild-markdown
  --paths-file PATH    one repo-relative or corpus-root-relative .md path per line (# comments ok); overrides rglob
  --limit N            ingest only first N files (sorted paths, or first N from --paths-file)
  --force              re-ingest even when store already has this file's fingerprint/scope
  --resume             skip paths listed in <store>/logs/batch_progress.json (crash recovery)
  --use-batch-api      per-file ingest uses OpenAI Batch API (adds --use-openai-batch-api to each ingest)
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cli import DungeonBuddyCLI, compute_ingest_key_for_path  # noqa: E402


class Tee:
    def __init__(self, *files: object) -> None:
        self.files = files

    def write(self, data: str) -> None:
        for f in self.files:
            f.write(data)
            f.flush()

    def flush(self) -> None:
        for f in self.files:
            f.flush()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_batch_progress(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"completed": [], "started_at": None}


def _save_batch_progress(path: Path, progress: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _is_managed_dungeonbuddy_storage(path: Path) -> bool:
    # corpus/<worldId>-markdown/_dungeonbuddy/ is managed product storage, not legacy corpus.
    return "_dungeonbuddy" in path.parts


def collect_legacy_corpus_markdown_paths(
    corpus_root: Path,
    *,
    paths_file: Path | None = None,
    limit: int = 0,
) -> list[Path]:
    """Collect markdown paths for legacy whole-tree ingest; excludes managed _dungeonbuddy storage."""
    if paths_file:
        raw_lines = paths_file.read_text(encoding="utf-8").splitlines()
        rels: list[str] = []
        for line in raw_lines:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            rels.append(s)
        paths: list[Path] = []
        for rel in rels:
            p = Path(rel)
            path = p.resolve() if p.is_absolute() else (corpus_root / rel).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"path from --paths-file not found: {path}")
            if _is_managed_dungeonbuddy_storage(path):
                print(
                    f"Warning: skipping managed _dungeonbuddy path from --paths-file: {path}",
                    file=sys.stderr,
                )
                continue
            paths.append(path)
    else:
        paths = sorted(
            p for p in corpus_root.rglob("*.md") if not _is_managed_dungeonbuddy_storage(p)
        )

    if limit > 0:
        paths = paths[:limit]
    return paths


def _load_model_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_model_policy(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _set_structured_generation_role(policy_path: Path, role: str) -> None:
    payload = _load_model_policy(policy_path)
    payload.setdefault("actions", {})
    payload["actions"]["structured_generation"] = role
    _save_model_policy(policy_path, payload)


def _latest_completed_run_for_path(store_dir: Path, source_path: Path) -> dict[str, Any] | None:
    log_path = store_dir / "logs" / "ingest_runs.jsonl"
    runs = _read_jsonl(log_path)
    source_str = str(source_path)
    for row in reversed(runs):
        if row.get("status") != "completed":
            continue
        if row.get("source_path") == source_str:
            return row
    return None


def _compute_escalation_metrics(run_row: dict[str, Any]) -> dict[str, Any]:
    artifact_dir = Path(str(run_row["artifact_dir"]))
    entities = json.loads((artifact_dir / "stage_entities.json").read_text(encoding="utf-8"))
    facts = json.loads((artifact_dir / "stage_facts.json").read_text(encoding="utf-8"))
    chunks = json.loads((artifact_dir / "stage_chunks.json").read_text(encoding="utf-8"))

    entity_count = len(entities)
    fact_count = len(facts)
    chunk_count = len(chunks)
    other_count = 0
    for e in entities:
        raw = e.get("entity_class")
        cls = str(raw) if raw is not None and str(raw).strip() else "missing"
        if cls in ("other", "unknown"):
            other_count += 1
    unknown_kind_count = sum(1 for e in entities if str(e.get("entity_kind") or "unknown") == "unknown")
    other_missing_facets = sum(
        1
        for e in entities
        if str(e.get("entity_class") or "") == "other" and not (e.get("semantic_facets") or [])
    )

    return {
        "entity_count": entity_count,
        "fact_count": fact_count,
        "chunk_count": chunk_count,
        "other_count": other_count,
        "other_rate": (other_count / entity_count) if entity_count else 0.0,
        "unknown_kind_count": unknown_kind_count,
        "unknown_kind_rate": (unknown_kind_count / entity_count) if entity_count else 0.0,
        "other_missing_facets_count": other_missing_facets,
        "other_missing_facets_rate": (other_missing_facets / other_count) if other_count else 0.0,
        "entities_per_chunk": (entity_count / chunk_count) if chunk_count else 0.0,
        "facts_per_chunk": (fact_count / chunk_count) if chunk_count else 0.0,
    }


def _build_escalation_decision(
    *,
    source_path: Path,
    run_row: dict[str, Any],
    metrics: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    reasons: list[str] = []
    if metrics["other_rate"] > args.escalate_other_rate:
        reasons.append(f"other_rate>{args.escalate_other_rate:.2f}")
    if metrics["unknown_kind_rate"] > args.escalate_unknown_kind_rate:
        reasons.append(f"unknown_kind_rate>{args.escalate_unknown_kind_rate:.2f}")
    if metrics["other_missing_facets_rate"] > args.escalate_other_missing_facets_rate:
        reasons.append(f"other_missing_facets_rate>{args.escalate_other_missing_facets_rate:.2f}")
    if metrics["entities_per_chunk"] < args.escalate_min_entities_per_chunk:
        reasons.append(f"entities_per_chunk<{args.escalate_min_entities_per_chunk:.2f}")
    if metrics["facts_per_chunk"] < args.escalate_min_facts_per_chunk:
        reasons.append(f"facts_per_chunk<{args.escalate_min_facts_per_chunk:.2f}")
    if args.escalate_world and str(run_row.get("layer")) == "world":
        reasons.append("world_layer_priority")

    return {
        "source_path": str(source_path),
        "run_id": run_row.get("run_id"),
        "layer": run_row.get("layer"),
        "artifact_dir": run_row.get("artifact_dir"),
        "metrics": metrics,
        "escalate": bool(reasons),
        "reasons": reasons,
    }


# Per-1M-token USD (fallback when model not in OpenAI public pricing table).
# Keep aligned with ``src/agent/planner_pricing._PRICING_PER_1M``.
_PRICING_PER_1M: dict[str, dict[str, float]] = {
    "gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "output": 1.20},
    "gpt-5.6-terra": {"input": 2.00, "cached_input": 0.20, "output": 12.00},
    "gpt-5.6-sol": {"input": 5.00, "cached_input": 0.50, "output": 30.00},
    "gpt-5.4-nano": {"input": 0.20, "cached_input": 0.02, "output": 1.25},
    "gpt-5.4-mini": {"input": 0.75, "cached_input": 0.075, "output": 4.50},
    "gpt-5.4-pro": {"input": 30.00, "cached_input": 30.00, "output": 180.00},
    "gpt-5.4": {"input": 2.50, "cached_input": 0.25, "output": 15.00},
    "gpt-5.3-codex": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.3-chat": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.2": {"input": 1.75, "cached_input": 0.175, "output": 14.00},
    "gpt-5.1": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-5-nano": {"input": 0.05, "cached_input": 0.005, "output": 0.40},
    "gpt-5-mini": {"input": 0.25, "cached_input": 0.025, "output": 2.00},
    "gpt-5": {"input": 1.25, "cached_input": 0.125, "output": 10.00},
    "gpt-4.1-nano": {"input": 0.10, "cached_input": 0.025, "output": 0.40},
    "gpt-4.1-mini": {"input": 0.40, "cached_input": 0.10, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "cached_input": 0.50, "output": 8.00},
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "o4-mini": {"input": 1.10, "cached_input": 0.275, "output": 4.40},
    "o3-mini": {"input": 1.10, "cached_input": 0.55, "output": 4.40},
    "o3": {"input": 2.00, "cached_input": 0.50, "output": 8.00},
}


def _pricing_rates_for_model(model_name: str) -> dict[str, float]:
    if not model_name or not str(model_name).strip():
        return {"input": 0.0, "cached_input": 0.0, "output": 0.0}
    mn = str(model_name).lower().strip()
    best: dict[str, float] | None = None
    best_len = 0
    for prefix, rates in _PRICING_PER_1M.items():
        if mn.startswith(prefix.lower()) and len(prefix) > best_len:
            best = dict(rates)
            best_len = len(prefix)
    return best if best is not None else {"input": 0.0, "cached_input": 0.0, "output": 0.0}


def _usage_int(mc: dict[str, Any], key: str) -> int:
    u = mc.get("usage")
    if not isinstance(u, dict):
        return 0
    return int(u.get(key, 0) or 0)


def _elapsed_seconds(started: str, ended: str) -> float:
    a = datetime.fromisoformat(started.replace("Z", "+00:00"))
    b = datetime.fromisoformat(ended.replace("Z", "+00:00"))
    return max(0.0, (b - a).total_seconds())


def _fmt_tokens_short(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _dominant_model_name(llm_rows: list[dict[str, Any]]) -> str:
    names = [str(r.get("model_name", "")).strip() for r in llm_rows if str(r.get("model_name", "")).strip()]
    if not names:
        return ""
    counts = Counter(names)
    top = counts.most_common(1)[0][0]
    return top


def _aggregate_batch_report(
    store_dir: Path,
    summary: dict[str, Any],
    started: str,
    ended: str,
    escalation_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    run_ids: set[str] = set()
    for r in summary.get("results", []):
        rid = r.get("run_id")
        if isinstance(rid, str) and rid:
            run_ids.add(rid)
    for er in escalation_runs:
        rid = er.get("escalated_run_id")
        if isinstance(rid, str) and rid:
            run_ids.add(rid)

    model_calls = _read_jsonl(store_dir / "logs" / "model_calls.jsonl")
    relevant = [mc for mc in model_calls if mc.get("run_id") in run_ids]
    entity_calls = [mc for mc in relevant if mc.get("stage") == "entity_extraction"]
    fact_calls = [mc for mc in relevant if mc.get("stage") == "fact_extraction"]
    llm_rows = entity_calls + fact_calls
    uses_openai_batch = any(bool(mc.get("openai_batch")) for mc in llm_rows)

    total_input = sum(_usage_int(mc, "input_tokens") for mc in llm_rows)
    total_output = sum(_usage_int(mc, "output_tokens") for mc in llm_rows)
    total_cached = sum(_usage_int(mc, "cached_tokens") for mc in llm_rows)
    uncached_input = sum(
        max(0, _usage_int(mc, "input_tokens") - _usage_int(mc, "cached_tokens")) for mc in llm_rows
    )
    api_entity = sum(_usage_int(mc, "api_calls") for mc in entity_calls)
    api_fact = sum(_usage_int(mc, "api_calls") for mc in fact_calls)
    api_total = api_entity + api_fact

    cache_rate = (total_cached / total_input) if total_input > 0 else 0.0

    entity_hits = sum(int(mc.get("cache_hits", 0) or 0) for mc in entity_calls)
    entity_misses = sum(int(mc.get("cache_misses", 0) or 0) for mc in entity_calls)
    fact_hits = sum(int(mc.get("cache_hits", 0) or 0) for mc in fact_calls)
    fact_misses = sum(int(mc.get("cache_misses", 0) or 0) for mc in fact_calls)
    local_total = entity_hits + entity_misses + fact_hits + fact_misses
    local_hit_rate = (
        (entity_hits + fact_hits) / local_total if local_total > 0 else 0.0
    )

    entity_ms = sum(int(mc.get("duration_ms", 0) or 0) for mc in entity_calls)
    fact_ms = sum(int(mc.get("duration_ms", 0) or 0) for mc in fact_calls)
    total_model_ms = entity_ms + fact_ms
    elapsed_sec = _elapsed_seconds(started, summary.get("ended_at") or ended)
    overhead_ms = max(0, int(round(elapsed_sec * 1000)) - total_model_ms)

    event_records_total = sum(int(mc.get("event_records_count", 0) or 0) for mc in entity_calls)
    claims_total = sum(int(mc.get("claims_count", 0) or 0) for mc in entity_calls)

    class_dist: Counter[str] = Counter()
    for r in summary.get("results", []):
        if not r.get("run_id"):
            continue
        p = r.get("path")
        if not p:
            continue
        run_row = _latest_completed_run_for_path(store_dir, Path(str(p)))
        if not run_row:
            continue
        ad = run_row.get("artifact_dir")
        if not ad:
            continue
        ent_path = Path(str(ad)) / "stage_entities.json"
        if not ent_path.is_file():
            continue
        try:
            ents = json.loads(ent_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(ents, list):
            continue
        for e in ents:
            if not isinstance(e, dict):
                continue
            raw = e.get("entity_class")
            cls = str(raw) if raw is not None and str(raw).strip() else "missing"
            class_dist[cls] += 1

    results = summary.get("results", [])
    file_total = len(results)
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    succeeded = sum(1 for r in results if r.get("run_id"))
    failed = max(0, file_total - succeeded - skipped)
    zero_output = sum(
        1
        for r in results
        if r.get("run_id")
        and r.get("facts_delta", -1) == 0
        and r.get("entities_delta", -1) == 0
        and r.get("evidence_delta", -1) == 0
    )

    model_name = _dominant_model_name(llm_rows)
    rates = _pricing_rates_for_model(model_name)
    est_cost = (
        uncached_input * rates["input"] + total_cached * rates["cached_input"] + total_output * rates["output"]
    ) / 1_000_000
    est_cost_before_openai_batch = est_cost
    if uses_openai_batch:
        est_cost = est_cost * 0.5
    without_cache_cost = (total_input * rates["input"] + total_output * rates["output"]) / 1_000_000
    savings_usd = max(0.0, without_cache_cost - est_cost)
    savings_pct = (100.0 * savings_usd / without_cache_cost) if without_cache_cost > 0 else 0.0

    ended_at = str(summary.get("ended_at") or ended)

    return {
        "generated_at": _utc_now_iso(),
        "run_window": {
            "started_at": started,
            "ended_at": ended_at,
            "elapsed_seconds": round(elapsed_sec, 3),
        },
        "files": {
            "total": file_total,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "zero_output": zero_output,
        },
        "api_calls": {
            "total": api_total,
            "entity_extraction": api_entity,
            "fact_extraction": api_fact,
        },
        "tokens": {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cached_tokens": total_cached,
            "cache_rate": round(cache_rate, 6),
        },
        "cost_estimate": {
            "model_name": model_name or "(unknown)",
            "input_cost_per_1m": rates["input"],
            "cached_input_cost_per_1m": rates["cached_input"],
            "output_cost_per_1m": rates["output"],
            "estimated_cost_usd": round(est_cost, 4),
            "without_caching_cost_usd": round(without_cache_cost, 4),
            "savings_pct": round(savings_pct, 2),
            "openai_batch_discount_applied": uses_openai_batch,
            "openai_batch_pricing_multiplier": 0.5 if uses_openai_batch else 1.0,
            "estimated_cost_before_openai_batch_usd": round(est_cost_before_openai_batch, 4),
        },
        "local_cache": {
            "entity_hits": entity_hits,
            "entity_misses": entity_misses,
            "fact_hits": fact_hits,
            "fact_misses": fact_misses,
            "overall_hit_rate": round(local_hit_rate, 6),
        },
        "timing": {
            "entity_extraction_ms": entity_ms,
            "fact_extraction_ms": fact_ms,
            "total_model_ms": total_model_ms,
            "overhead_ms": overhead_ms,
        },
        "entity_class_distribution": dict(sorted(class_dist.items(), key=lambda x: (-x[1], x[0]))),
        "recap": {
            "event_records_total": event_records_total,
            "claims_total": claims_total,
        },
    }


def _print_batch_report_table(report: dict[str, Any]) -> None:
    files = report["files"]
    api = report["api_calls"]
    tok = report["tokens"]
    loc = report["local_cache"]
    cost = report["cost_estimate"]
    timing = report["timing"]
    savings_usd = max(
        0.0,
        float(cost["without_caching_cost_usd"]) - float(cost["estimated_cost_usd"]),
    )

    file_line = (
        f"{files['total']} total, {files['succeeded']} ok, {files['failed']} failed, "
        f"{files['skipped']} skipped"
    )
    api_line = f"{api['total']:,} ({api['entity_extraction']} entity + {api['fact_extraction']} fact)"
    tok_line = (
        f"{_fmt_tokens_short(tok['input_tokens'])} input, "
        f"{_fmt_tokens_short(tok['output_tokens'])} output, "
        f"{_fmt_tokens_short(tok['cached_tokens'])} cached"
    )
    cache_pct = 100.0 * float(tok["cache_rate"])
    batch_note = ""
    if cost.get("openai_batch_discount_applied"):
        batch_note = " (×0.5 OpenAI Batch pricing)"
    cost_line = f"${float(cost['estimated_cost_usd']):.2f} (saved ${savings_usd:.2f} via caching){batch_note}"
    model_s = timing["total_model_ms"] / 1000.0

    lines = [
        "╔══════════════════════════════════════════════════╗",
        "║              BATCH INGEST REPORT                 ║",
        "╠══════════════════════════════════════════════════╣",
        f"║ Files:    {file_line:<38} ║",
        f"║ API Calls: {api_line:<36} ║",
        f"║ Tokens:   {tok_line:<38} ║",
        f"║ Cache Rate: {cache_pct:.1f}% (OpenAI prefix)              ║",
        f"║ Local Cache: {100.0 * float(loc['overall_hit_rate']):.1f}% hit rate                   ║",
        f"║ Est. Cost: {cost_line:<36} ║",
        f"║ Duration:  {model_s:.1f}s model time                      ║",
        "╚══════════════════════════════════════════════════╝",
    ]
    print("\n" + "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch corpus ingest")
    parser.add_argument(
        "--store",
        type=Path,
        default=Path("out/stores/dungeonbuddy_store_batch"),
        help="Fact store directory (created if missing; default under out/stores/)",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path("corpus/eldyrwild-markdown"),
        help="Root directory to scan for *.md",
    )
    parser.add_argument(
        "--paths-file",
        type=Path,
        default=None,
        help="Text file: one markdown path per line, relative to --corpus-root (or absolute). "
        "Lines starting with # are ignored. When set, only these files are ingested (then --limit trims).",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max files (0 = all)")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Evidence units per LLM call during ingest (passed to each ingest; default 5)",
    )
    parser.add_argument(
        "--enforce-cheap-pass",
        action="store_true",
        help="Temporarily force structured_generation=cheapest during base pass.",
    )
    parser.add_argument(
        "--base-role",
        type=str,
        default="cheapest",
        help="MODEL_POLICY role for base pass when --enforce-cheap-pass is used.",
    )
    parser.add_argument(
        "--escalation-role",
        type=str,
        default="fast_smart",
        help="MODEL_POLICY role for escalated re-runs.",
    )
    parser.add_argument(
        "--auto-escalate",
        action="store_true",
        help="Re-run flagged files with structured_generation=fast_smart and --force.",
    )
    parser.add_argument(
        "--escalate-world",
        action="store_true",
        help="Always escalate world-layer files.",
    )
    parser.add_argument("--escalate-other-rate", type=float, default=0.30)
    parser.add_argument("--escalate-unknown-kind-rate", type=float, default=0.08)
    parser.add_argument("--escalate-other-missing-facets-rate", type=float, default=0.40)
    parser.add_argument("--escalate-min-entities-per-chunk", type=float, default=0.80)
    parser.add_argument("--escalate-min-facts-per-chunk", type=float, default=2.00)
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Append full transcript here (default: <store>/logs/batch_ingest.log)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingest even if store already has this source fingerprint/scope",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted batch using logs/batch_progress.json (completed paths skipped)",
    )
    parser.add_argument(
        "--use-batch-api",
        action="store_true",
        help="Use OpenAI Batch API for each ingest (~50%% cost vs realtime; async, up to 24h per batch job)",
    )
    args = parser.parse_args()

    corpus_root = args.corpus_root.resolve()
    if not corpus_root.is_dir():
        print(f"Error: corpus root not found: {corpus_root}", file=sys.stderr)
        return 1

    store_dir = args.store.resolve()
    store_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.log or (store_dir / "logs" / "batch_ingest.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        paths = collect_legacy_corpus_markdown_paths(
            corpus_root,
            paths_file=args.paths_file,
            limit=args.limit,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    started = datetime.now(timezone.utc).isoformat()
    progress_path = store_dir / "logs" / "batch_progress.json"
    if args.resume:
        progress = _load_batch_progress(progress_path)
    else:
        progress = {"completed": [], "started_at": started}
        if progress_path.exists():
            progress_path.unlink()
    completed_set = {str(p) for p in progress.get("completed", []) if p}

    summary: dict[str, object] = {
        "started_at": started,
        "store": str(store_dir),
        "corpus_root": str(corpus_root),
        "file_count": len(paths),
        "use_openai_batch_api": bool(args.use_batch_api),
        "results": [],
    }
    decisions: list[dict[str, Any]] = []
    escalation_runs: list[dict[str, Any]] = []

    policy_path = ROOT.parent / "MODEL_POLICY.json"
    original_policy: dict[str, Any] | None = None
    policy_restored = False

    with log_path.open("a", encoding="utf-8") as logf:
        logf.write(f"\n=== batch_ingest start {started} files={len(paths)} ===\n")
        tee = Tee(sys.__stdout__, logf)
        old_stdout = sys.stdout
        sys.stdout = tee  # type: ignore[assignment]

        try:
            if policy_path.exists():
                original_policy = _load_model_policy(policy_path)
            if args.enforce_cheap_pass and policy_path.exists():
                print(
                    f"Forcing structured_generation={args.base_role} for base pass",
                    flush=True,
                )
                _set_structured_generation_role(policy_path, args.base_role)

            cli = DungeonBuddyCLI(store_dir=store_dir, verbose=True)
            for i, path in enumerate(paths, start=1):
                rel = path.relative_to(corpus_root) if path.is_relative_to(corpus_root) else path
                path_key = str(path.resolve())
                if args.resume and path_key in completed_set:
                    print(f"\n[{i}/{len(paths)}] skipped (already done this run): {rel}", flush=True)
                    summary["results"].append(
                        {
                            "path": str(path),
                            "status": "skipped",
                            "reason": "resume",
                            "facts_delta": 0,
                            "entities_delta": 0,
                            "evidence_delta": 0,
                        }
                    )
                    continue

                ingest_key = compute_ingest_key_for_path(path)
                if (
                    ingest_key
                    and cli.store.has_ingest_fingerprint(ingest_key)
                    and not args.force
                ):
                    print(f"\n[{i}/{len(paths)}] skipped (unchanged): {rel}", flush=True)
                    summary["results"].append(
                        {
                            "path": str(path),
                            "status": "skipped",
                            "reason": "unchanged",
                            "facts_delta": 0,
                            "entities_delta": 0,
                            "evidence_delta": 0,
                        }
                    )
                    continue

                print(f"\n[{i}/{len(paths)}] ingest {rel}", flush=True)
                facts_before = len(cli.store.facts)
                entities_before = len(cli.store.entities)
                evidence_before = len(cli.store.evidence_units)
                line = f"ingest {shlex.quote(str(path))} --batch-size {args.batch_size}"
                if args.force:
                    line += " --force"
                if args.use_batch_api:
                    line += " --use-openai-batch-api"
                cli.handle_line(line)
                run_row = _latest_completed_run_for_path(store_dir, path)
                entry: dict[str, Any] = {
                    "path": str(path),
                    "facts_delta": len(cli.store.facts) - facts_before,
                    "entities_delta": len(cli.store.entities) - entities_before,
                    "evidence_delta": len(cli.store.evidence_units) - evidence_before,
                }
                if run_row:
                    entry["run_id"] = run_row.get("run_id")
                    entry["artifact_dir"] = run_row.get("artifact_dir")
                    metrics = _compute_escalation_metrics(run_row)
                    decision = _build_escalation_decision(
                        source_path=path,
                        run_row=run_row,
                        metrics=metrics,
                        args=args,
                    )
                    decisions.append(decision)
                    entry["escalation_decision"] = {
                        "escalate": decision["escalate"],
                        "reasons": decision["reasons"],
                    }
                    progress.setdefault("completed", []).append(path_key)
                    _save_batch_progress(progress_path, progress)
                summary["results"].append(entry)

            failed_main = sum(
                1
                for r in summary["results"]
                if r.get("status") != "skipped" and not r.get("run_id")
            )
            if failed_main == 0 and progress_path.exists():
                progress_path.unlink()

            flagged = [d for d in decisions if d["escalate"]]
            if args.auto_escalate and flagged:
                if not policy_path.exists():
                    print("Warning: MODEL_POLICY.json not found; skipping auto escalation.")
                else:
                    print(
                        f"\nAuto-escalating {len(flagged)} files with structured_generation={args.escalation_role}",
                        flush=True,
                    )
                    _set_structured_generation_role(policy_path, args.escalation_role)
                    for i, decision in enumerate(flagged, start=1):
                        path = Path(str(decision["source_path"]))
                        rel = path.relative_to(corpus_root) if path.is_relative_to(corpus_root) else path
                        print(
                            f"[escalate {i}/{len(flagged)}] ingest --force {rel} | reasons={decision['reasons']}",
                            flush=True,
                        )
                        line = (
                            f"ingest {shlex.quote(str(path))} --force --batch-size {args.batch_size}"
                        )
                        if args.use_batch_api:
                            line += " --use-openai-batch-api"
                        before = _latest_completed_run_for_path(store_dir, path)
                        cli.handle_line(line)
                        after = _latest_completed_run_for_path(store_dir, path)
                        if after and (not before or after.get("run_id") != before.get("run_id")):
                            after_metrics = _compute_escalation_metrics(after)
                            escalation_runs.append(
                                {
                                    "source_path": str(path),
                                    "base_run_id": decision.get("run_id"),
                                    "escalated_run_id": after.get("run_id"),
                                    "reasons": decision.get("reasons"),
                                    "base_metrics": decision.get("metrics"),
                                    "escalated_metrics": after_metrics,
                                }
                            )
            elif args.auto_escalate:
                print("\nAuto escalation enabled but no files were flagged.", flush=True)
        finally:
            if original_policy is not None and policy_path.exists():
                _save_model_policy(policy_path, original_policy)
                policy_restored = True
            sys.stdout = old_stdout

        ended = datetime.now(timezone.utc).isoformat()
        logf.write(f"=== batch_ingest end {ended} ===\n")

    summary["ended_at"] = ended
    _results = summary["results"]
    summary["skipped_count"] = (
        sum(1 for r in _results if isinstance(r, dict) and r.get("status") == "skipped")
        if isinstance(_results, list)
        else 0
    )
    summary["policy_restore"] = {"restored": policy_restored, "policy_path": str(policy_path)}
    summary["escalation"] = {
        "generated_at": _utc_now_iso(),
        "thresholds": {
            "other_rate": args.escalate_other_rate,
            "unknown_kind_rate": args.escalate_unknown_kind_rate,
            "other_missing_facets_rate": args.escalate_other_missing_facets_rate,
            "min_entities_per_chunk": args.escalate_min_entities_per_chunk,
            "min_facts_per_chunk": args.escalate_min_facts_per_chunk,
            "escalate_world": args.escalate_world,
        },
        "decisions_count": len(decisions),
        "flagged_count": sum(1 for d in decisions if d.get("escalate")),
        "auto_escalate": bool(args.auto_escalate),
        "base_role": args.base_role,
        "escalation_role": args.escalation_role,
        "escalation_runs_count": len(escalation_runs),
    }

    summary_path = store_dir / "logs" / "batch_ingest_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = _aggregate_batch_report(store_dir, summary, started, ended, escalation_runs)
    report_path = store_dir / "logs" / "batch_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    decisions_path = store_dir / "logs" / "escalation_decisions.json"
    decisions_path.write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    if escalation_runs:
        escalation_runs_path = store_dir / "logs" / "escalation_runs.json"
        escalation_runs_path.write_text(json.dumps(escalation_runs, indent=2), encoding="utf-8")

    print(f"\nWrote summary: {summary_path}")
    print(f"Wrote batch report: {report_path}")
    _print_batch_report_table(report)
    print(f"Wrote escalation decisions: {decisions_path}")
    if escalation_runs:
        print(f"Wrote escalation runs: {store_dir / 'logs' / 'escalation_runs.json'}")
    print(f"Transcript: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
