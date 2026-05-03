"""Split Stage B cohort runner: B1 discourse state + deterministic B2 hub routing.

This is the benchmark entrypoint for the sibling proving slice. It writes normal B1/B2
per-run sidecars plus a split-pipeline cohort summary that carries combined cost,
pass/fail, and failure-relocation telemetry.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.step2_route_run import _load_sentence_units
from evals.sentence_routing_retrieval_falsification.step2a_discourse_run import run_discourse_once
from evals.sentence_routing_retrieval_falsification.grader import cohort_aggregate_unit_failure_events
from evals.sentence_routing_retrieval_falsification.step2b_route_from_discourse_run import (
    run_route_from_discourse_once,
)

_SLICE = Path(__file__).resolve().parent
_REPO_ROOT = _SLICE.parents[1]
_DEFAULT_SCENARIO = _SLICE / "gold" / "scenario_discourse_smoke.json"
_ARTIFACTS = _SLICE / "artifacts" / "runs"
_DEFAULT_MODEL = os.environ.get("DUNGEONMIND_PLANNER_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"

SUMMARY_SCHEMA = "sentence_routing_stage_b_discourse_pipeline_cohort_summary_v1"


def _b2_failure_partition_vs_npc_context(record: dict[str, Any], ctx_unit_ids: set[str]) -> dict[str, Any]:
    b2 = record.get("b2") if isinstance(record.get("b2"), dict) else {}
    bd = b2.get("stage_b_unit_breakdown") if isinstance(b2.get("stage_b_unit_breakdown"), dict) else {}
    ufe = bd.get("unit_failure_events") if isinstance(bd.get("unit_failure_events"), dict) else {}
    failed = {str(x) for x in (ufe.get("distinct_failure_unit_ids") or [])}
    return {
        "b2_fail_unit_ids_with_npc_context": sorted(failed & ctx_unit_ids),
        "b2_fail_unit_ids_without_npc_context": sorted(failed - ctx_unit_ids),
    }


def _cohort_npc_first_context_aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    with_ctx: set[str] = set()
    without_ctx: set[str] = set()
    for r in records:
        nf = r.get("npc_first_context")
        if not isinstance(nf, dict) or not nf.get("enabled"):
            continue
        with_ctx.update(str(x) for x in (nf.get("b2_fail_unit_ids_with_npc_context") or []))
        without_ctx.update(str(x) for x in (nf.get("b2_fail_unit_ids_without_npc_context") or []))
    return {
        "distinct_b2_failures_with_npc_context": sorted(with_ctx),
        "distinct_b2_failures_without_npc_context": sorted(without_ctx),
    }


def _write_npc_attachment_context_artifact(
    sidecar: dict[str, Any],
    *,
    scenario_id: str,
    no_writes: bool,
) -> Path | None:
    if no_writes:
        return None
    day_dir = _ARTIFACTS / _date_folder()
    day_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    safe = _sanitize_filename_segment(scenario_id, max_len=56)
    out_path = day_dir / f"npc_attachment_context_v1--{safe}--{stamp}.json"
    out_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _date_folder() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _sanitize_filename_segment(raw: str, *, max_len: int = 48) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", (raw or "").strip())
    s = s.strip("._-") or "model"
    return s[:max_len]


def _cost_summary(costs: list[float]) -> dict[str, float]:
    return {
        "min": round(min(costs), 6) if costs else 0.0,
        "max": round(max(costs), 6) if costs else 0.0,
        "mean": round(statistics.mean(costs), 6) if costs else 0.0,
        "sum": round(sum(costs), 6),
    }


def _write_split_pipeline_summary(
    *,
    records: list[dict[str, Any]],
    model_id: str,
    scenario_id: str,
    no_writes: bool,
    preflight_meta: dict[str, Any] | None = None,
    npc_first_context_build_cost_usd: float = 0.0,
) -> tuple[Path | None, Path | None]:
    if no_writes:
        return None, None
    day_dir = _ARTIFACTS / _date_folder()
    day_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    model_seg = _sanitize_filename_segment(model_id)
    base = f"sentence_routing_stage_b_discourse_pipeline_summary--{scenario_id}--{model_seg}--N{len(records)}--{stamp}"
    json_path = day_dir / f"{base}.json"
    md_path = day_dir / f"{base}.md"

    costs = [float(r.get("cost_usd") or 0.0) for r in records]
    passed = sum(1 for r in records if r.get("pipeline_passed"))
    payload = {
        "schema": SUMMARY_SCHEMA,
        "pipeline": "stage_b_discourse_v1",
        "iso_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_id": scenario_id,
        "model_id": model_id,
        "n": len(records),
        "passed": passed,
        "pass_rate": round(passed / len(records), 6) if records else 0.0,
        "cost_usd": _cost_summary(costs),
        "cost_baseline_note": (
            "Split Stage B first cohort; compare against monolithic Stage B cohorts for the same "
            "scenario/model. Flag regression at >=1.5x cohort sum or any single run >=1.5x prior mean."
        ),
        "runs": records,
    }
    if npc_first_context_build_cost_usd > 0.0:
        payload["npc_first_context_build_cost_usd"] = round(float(npc_first_context_build_cost_usd), 6)
        payload["npc_first_context_cost_note"] = (
            "Stage A extraction cost for --build-npc-first-context (once per invocation); "
            "not included in runs[].cost_usd (B1 discourse only)."
        )
    agg_nf = _cohort_npc_first_context_aggregate(records)
    if any(isinstance(r.get("npc_first_context"), dict) and r["npc_first_context"].get("enabled") for r in records):
        payload["cohort_npc_first_context"] = agg_nf
    if isinstance(preflight_meta, dict) and preflight_meta:
        payload["preflight"] = preflight_meta
    ufe_list: list[dict[str, Any] | None] = []
    b1_ufe_list: list[dict[str, Any] | None] = []
    for r in records:
        b1 = r.get("b1") if isinstance(r.get("b1"), dict) else {}
        b1_bd = (
            b1.get("stage_b1_unit_breakdown")
            if isinstance(b1.get("stage_b1_unit_breakdown"), dict)
            else {}
        )
        raw_b1_ufe = b1_bd.get("content_failure_events") if isinstance(b1_bd, dict) else None
        b1_ufe_list.append(raw_b1_ufe if isinstance(raw_b1_ufe, dict) else None)
        b2 = r.get("b2") if isinstance(r.get("b2"), dict) else {}
        bd = b2.get("stage_b_unit_breakdown") if isinstance(b2.get("stage_b_unit_breakdown"), dict) else {}
        raw_ufe = bd.get("unit_failure_events")
        ufe_list.append(raw_ufe if isinstance(raw_ufe, dict) else None)
    payload["cohort_b1_content_failure_events"] = cohort_aggregate_unit_failure_events(
        b1_ufe_list
    )
    payload["cohort_unit_failure_events"] = cohort_aggregate_unit_failure_events(ufe_list)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    costs_obj = payload["cost_usd"]
    md_lines = [
        "# Split Stage B — discourse pipeline cohort",
        "",
        f"- **scenario:** `{scenario_id}`",
        f"- **model:** `{model_id}`",
        f"- **pass rate:** {passed}/{len(records)}",
        f"- **Cost:** sum ${costs_obj['sum']:.4f} | mean ${costs_obj['mean']:.4f} | min ${costs_obj['min']:.4f} | max ${costs_obj['max']:.4f}",
        "",
    ]
    pf = payload.get("preflight")
    if isinstance(pf, dict) and pf:
        md_lines.extend(
            [
                "## Preflight",
                "",
                f"- **capture_signature:** `{json.dumps(pf.get('capture_signature'), sort_keys=True)}`",
                f"- **gold_routing_normalized_fingerprint_sha16:** `{pf.get('gold_routing_normalized_fingerprint_sha16', '')}`",
                f"- **must_route_rows:** {pf.get('must_route_rows', '?')}",
                f"- **must_abstain_rows:** {pf.get('must_abstain_rows', '?')}",
                "",
            ]
        )
    md_lines.extend(
        [
            "## Cohort — B1 content failure buckets (union across runs)",
            "",
            "Distinct `unit_id` values that failed B1 content expectations in **any** run.",
            "",
        ]
    )
    b1_cufe = payload.get("cohort_b1_content_failure_events") or {}
    b1_c_buckets = b1_cufe.get("by_bucket") if isinstance(b1_cufe, dict) else None
    if not isinstance(b1_cufe, dict) or "by_bucket" not in b1_cufe:
        md_lines.append("- *(no `cohort_b1_content_failure_events` in payload)*")
    elif isinstance(b1_c_buckets, dict) and len(b1_c_buckets) > 0:
        for bname, bobj in sorted(b1_c_buckets.items()):
            if not isinstance(bobj, dict):
                continue
            uids = bobj.get("unit_ids") or []
            cnt = bobj.get("count", len(uids) if isinstance(uids, list) else 0)
            if isinstance(uids, list) and uids:
                md_lines.append(
                    f"- **{bname}** — {cnt} unit(s): " + ", ".join(f"`{u}`" for u in uids)
                )
            else:
                md_lines.append(f"- **{bname}** — {cnt} unit(s)")
        dist = (
            b1_cufe.get("distinct_failure_unit_ids")
            if isinstance(b1_cufe, dict)
            else None
        )
        if isinstance(dist, list) and dist:
            md_lines.append(
                "- **distinct_failure_unit_ids (any B1 content bucket):** "
                + ", ".join(f"`{u}`" for u in dist)
            )
    else:
        md_lines.append(
            "- **Cohort B1 content failure buckets:** none (no B1 content failing `unit_id` in any run)."
        )
    md_lines.extend(
        [
            "",
        "## Cohort — B2 unit failure buckets (union across runs)",
        "",
        "Distinct `unit_id` values that failed B2 gates in **any** run. See each run’s "
        "`b2.stage_b_unit_breakdown.unit_failure_events`.",
        "",
        ]
    )
    cufe = payload.get("cohort_unit_failure_events") or {}
    c_buckets = cufe.get("by_bucket") if isinstance(cufe, dict) else None
    if not isinstance(cufe, dict) or "by_bucket" not in cufe:
        md_lines.append("- *(no `cohort_unit_failure_events` in payload)*")
    elif isinstance(c_buckets, dict) and len(c_buckets) > 0:
        for bname, bobj in sorted(c_buckets.items()):
            if not isinstance(bobj, dict):
                continue
            uids = bobj.get("unit_ids") or []
            cnt = bobj.get("count", len(uids) if isinstance(uids, list) else 0)
            if isinstance(uids, list) and uids:
                md_lines.append(
                    f"- **{bname}** — {cnt} unit(s): " + ", ".join(f"`{u}`" for u in uids)
                )
            else:
                md_lines.append(f"- **{bname}** — {cnt} unit(s)")
        dist = cufe.get("distinct_failure_unit_ids") if isinstance(cufe, dict) else None
        if isinstance(dist, list) and dist:
            md_lines.append(
                "- **distinct_failure_unit_ids (any bucket):** "
                + ", ".join(f"`{u}`" for u in dist)
            )
    else:
        md_lines.append(
            "- **Cohort failure buckets:** none (no B2 failing `unit_id` in any run)."
        )
    if npc_first_context_build_cost_usd > 0.0:
        md_lines.extend(
            [
                "",
                "## NPC-first context (experiment)",
                "",
                f"- **context_build_cost_usd (Stage A, once):** ${npc_first_context_build_cost_usd:.4f}",
                "- **B1 route cost:** still `runs[].cost_usd` (discourse only).",
                "",
            ]
        )
    cnf = payload.get("cohort_npc_first_context")
    if isinstance(cnf, dict) and cnf:
        md_lines.extend(
            [
                "### Cohort — B2 failures vs NPC-first-enriched units",
                "",
                "Distinct `unit_id` values across runs:",
                "",
            ]
        )
        w = cnf.get("distinct_b2_failures_with_npc_context") or []
        wo = cnf.get("distinct_b2_failures_without_npc_context") or []
        md_lines.append(
            "- **with_npc_first_context:** "
            + (", ".join(f"`{u}`" for u in w) if isinstance(w, list) and w else "*(none)*")
        )
        md_lines.append(
            "- **without_npc_first_context:** "
            + (", ".join(f"`{u}`" for u in wo) if isinstance(wo, list) and wo else "*(none)*")
        )
        md_lines.append("")
    md_lines.extend(["", "## Runs", ""])
    for r in records:
        b1 = r.get("b1") if isinstance(r.get("b1"), dict) else {}
        b1_bd = (
            b1.get("stage_b1_unit_breakdown")
            if isinstance(b1.get("stage_b1_unit_breakdown"), dict)
            else {}
        )
        b2 = r.get("b2") if isinstance(r.get("b2"), dict) else {}
        bd = b2.get("stage_b_unit_breakdown") if isinstance(b2.get("stage_b_unit_breakdown"), dict) else {}
        delta = bd.get("b2_delta") if isinstance(bd.get("b2_delta"), dict) else {}
        counts = delta.get("gold_failure_attribution_counts") if isinstance(delta, dict) else {}
        md_lines.append(
            f"- run {int(r.get('run_index', 0)) + 1}: "
            f"{'PASS' if r.get('pipeline_passed') else 'FAIL'} | "
            f"B1={'PASS' if r.get('b1_passed') else 'FAIL'} | "
            f"B2={'PASS' if r.get('b2_passed') else 'FAIL'} | "
            f"${float(r.get('cost_usd') or 0.0):.4f}"
        )
        md_lines.append(f"  - B1 sidecar: `{r.get('b1_sidecar_json')}`")
        md_lines.append(f"  - B2 sidecar: `{r.get('b2_sidecar_json')}`")
        nf = r.get("npc_first_context")
        if isinstance(nf, dict) and nf.get("enabled"):
            md_lines.append(
                "  - NPC-first: enriched units="
                f"{nf.get('units_enriched', '?')}; "
                f"B2 fail w/ ctx={nf.get('b2_fail_unit_ids_with_npc_context')}; "
                f"w/o ctx={nf.get('b2_fail_unit_ids_without_npc_context')}"
            )
        b1_ufe = b1_bd.get("content_failure_events") if isinstance(b1_bd, dict) else {}
        b1_ufeb = b1_ufe.get("by_bucket") if isinstance(b1_ufe, dict) else {}
        if isinstance(b1_ufeb, dict) and b1_ufeb:
            md_lines.append("  - B1 content failure buckets:")
            for bn, bobj in sorted(b1_ufeb.items()):
                if not isinstance(bobj, dict):
                    continue
                uids = bobj.get("unit_ids") or []
                if isinstance(uids, list) and uids:
                    md_lines.append(
                        f"    - `{bn}`: " + ", ".join(f"`{x}`" for x in uids)
                    )
        if isinstance(counts, dict):
            md_lines.append(f"  - B2 delta attribution: `{json.dumps(counts, sort_keys=True)}`")
        ufe = bd.get("unit_failure_events") if isinstance(bd, dict) else {}
        ufeb = ufe.get("by_bucket") if isinstance(ufe, dict) else {}
        if isinstance(ufeb, dict) and ufeb:
            md_lines.append("  - B2 unit failure buckets:")
            for bn, bobj in sorted(ufeb.items()):
                if not isinstance(bobj, dict):
                    continue
                uids = bobj.get("unit_ids") or []
                if isinstance(uids, list) and uids:
                    md_lines.append(
                        f"    - `{bn}`: " + ", ".join(f"`{x}`" for x in uids)
                    )
        ug = bd.get("unit_gate_events") if isinstance(bd, dict) else {}
        if isinstance(ug, dict) and ug.get("must_route"):
            mr = ug.get("must_route") or {}
            ma = ug.get("must_abstain") or {}
            md_lines.append(
                "  - B2 unit gate events: "
                f"must_route pass {mr.get('pass_unit_ids', [])}; fail {mr.get('fail_unit_ids', [])}; "
                f"must_abstain pass {ma.get('pass_unit_ids', [])}; fail {ma.get('fail_unit_ids', [])}."
            )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _load_scenario_inputs_from_raw(
    raw: dict[str, Any],
    corpus_root: Path,
    prior_json: Path | None,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[str],
    dict[str, Any],
    dict[str, Any],
]:
    raw = dict(raw)
    inp = dict(raw.get("input") or {})
    manifest_raw = list(inp.get("hub_manifest") or [])
    gold_routing = dict(raw.get("gold_routing") or {})

    from evals.sentence_routing_retrieval_falsification.route_schema import (
        HubManifestEntry,
        manifest_slug_set,
        validate_hub_manifest,
    )

    max_entries = int(inp.get("max_manifest_entries") or 64)
    validate_paths = bool(inp.get("validate_manifest_paths", True))
    mviol = validate_hub_manifest(
        manifest_raw,
        corpus_root=corpus_root,
        validate_paths=validate_paths,
        max_manifest_entries=max_entries,
    )
    if mviol:
        raise ValueError(json.dumps({"manifest_violations": mviol}, indent=2))
    manifest_objs = [HubManifestEntry.model_validate(x) for x in manifest_raw]
    manifest_jsonable = [m.model_dump(exclude_none=True) for m in manifest_objs]
    manifest_slugs = manifest_slug_set(manifest_objs)
    units_json = _load_sentence_units(raw, corpus_root, prior_json)

    from evals.sentence_routing_retrieval_falsification.stage_b_preflight import (
        preflight_stage_b_gold_and_capture,
    )

    gold_norm, norm_errors, preflight_meta = preflight_stage_b_gold_and_capture(
        gold_routing,
        units_json,
        expected_capture_signature=raw.get("expected_capture_signature")
        if isinstance(raw.get("expected_capture_signature"), dict)
        else None,
    )
    if norm_errors:
        raise ValueError(
            json.dumps(
                {"gold_normalize_errors": norm_errors, "preflight": preflight_meta},
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
    return raw, units_json, manifest_jsonable, manifest_slugs, gold_norm, preflight_meta


def _load_scenario_inputs(scenario_path: Path, corpus_root: Path, prior_json: Path | None) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[str],
    dict[str, Any],
    dict[str, Any],
]:
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    return _load_scenario_inputs_from_raw(raw, corpus_root, prior_json)


def _merge_session_entity_candidates_blob(inp: dict[str, Any], blob: dict[str, Any]) -> None:
    """Shallow-merge ``blob`` into ``inp['session_entity_candidates']`` (list fields concatenate)."""
    prev = inp.get("session_entity_candidates")
    if not isinstance(prev, dict):
        inp["session_entity_candidates"] = dict(blob)
        return
    merged = dict(prev)
    for k, v in blob.items():
        if k in merged and isinstance(merged[k], list) and isinstance(v, list):
            merged[k] = list(merged[k]) + list(v)
        else:
            merged[k] = v
    inp["session_entity_candidates"] = merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Split Stage B cohort: B1 discourse -> B2 route.")
    parser.add_argument("--scenario-json", type=Path, default=_DEFAULT_SCENARIO)
    parser.add_argument("--corpus-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--prior-json", type=Path, default=None)
    parser.add_argument(
        "--session-entity-candidates-json",
        type=Path,
        default=None,
        help="Merge JSON {npc_names, location_names, ...} into scenario input session_entity_candidates "
        "(ablation; does not change on-disk gold).",
    )
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL)
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--no-writes", action="store_true")
    parser.add_argument(
        "--prompt-variant",
        type=str,
        default=None,
        help="B1 discourse prompt append (e.g. npc_first_context_v1).",
    )
    parser.add_argument(
        "--npc-first-context-json",
        type=Path,
        default=None,
        help="Load npc_attachment_context_v1 sidecar (mutually exclusive with --build-npc-first-context).",
    )
    parser.add_argument(
        "--build-npc-first-context",
        action="store_true",
        help="Run Stage A session-events extraction once, build npc_attachment_context_v1, enrich units.",
    )
    parser.add_argument(
        "--npc-first-timeline-gold",
        type=Path,
        default=None,
        help="Optional timeline-pass JSON (grading.expected_appends/skips) for NPC append vs skip alignment.",
    )
    args = parser.parse_args()

    n = max(1, int(args.n))
    scenario_path = args.scenario_json.resolve()
    corpus_root = args.corpus_root.resolve()
    prior_json = args.prior_json.resolve() if args.prior_json else None
    model = str(args.model).strip()
    prompt_variant = str(args.prompt_variant).strip() if args.prompt_variant else None

    try:
        raw = json.loads(scenario_path.read_text(encoding="utf-8"))
        if args.session_entity_candidates_json is not None:
            cand_path = args.session_entity_candidates_json.resolve()
            blob = json.loads(cand_path.read_text(encoding="utf-8"))
            if not isinstance(blob, dict):
                raise ValueError("session_entity_candidates_json must be a JSON object")
            inp = dict(raw.get("input") or {})
            _merge_session_entity_candidates_blob(inp, blob)
            raw["input"] = inp
        raw, units_json, manifest_jsonable, manifest_slugs, gold_routing, preflight_meta = (
            _load_scenario_inputs_from_raw(raw, corpus_root, prior_json)
        )
        if bool(args.build_npc_first_context) and args.npc_first_context_json is not None:
            raise ValueError("Use either --build-npc-first-context or --npc-first-context-json, not both.")
        if bool(args.build_npc_first_context) and bool(args.no_llm):
            raise ValueError("--build-npc-first-context requires live Stage A (omit --no-llm).")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not args.no_llm:
        from src.agent.synthesis import _load_api_key
        from src.bootstrap_env import load_dungeonmindbuddy_dotenv

        load_dungeonmindbuddy_dotenv()
        if not (_load_api_key() or "").strip():
            print(
                "OPENAI_API_KEY missing after loading .env (see src/bootstrap_env.py). "
                "Use --no-llm for offline fixture runs.",
                file=sys.stderr,
            )
            return 2

    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)
    records: list[dict[str, Any]] = []
    all_pass = True

    ctx_sidecar: dict[str, Any] | None = None
    context_build_cost_usd = 0.0
    npc_ctx_disk_path: Path | None = None
    enrich_stats: dict[str, int] = {"units_enriched": 0, "units_with_npc_slugs": 0}
    built_from_stage_a = False

    if args.npc_first_context_json is not None:
        from evals.sentence_routing_retrieval_falsification.npc_first_context import (
            load_npc_attachment_context_sidecar,
        )

        ctx_sidecar = load_npc_attachment_context_sidecar(args.npc_first_context_json.resolve())
        npc_ctx_disk_path = args.npc_first_context_json.resolve()
    elif args.build_npc_first_context:
        from openai import OpenAI

        from evals.session_events_extraction_vertical_slice.step1_session_events_run import (
            run_session_events_extraction,
        )
        from evals.sentence_routing_retrieval_falsification.npc_first_context import (
            build_minimal_session_events_scenario,
            build_npc_attachment_context_sidecar,
            default_eldyrwild_corpus_root,
        )

        from src.bootstrap_env import load_dungeonmindbuddy_dotenv

        load_dungeonmindbuddy_dotenv()
        minimal = build_minimal_session_events_scenario(raw)
        eldyr_root = default_eldyrwild_corpus_root(corpus_root)
        client = OpenAI()
        result = run_session_events_extraction(
            client=client,
            model_id=model,
            scenario=minimal,
            corpus_root=eldyr_root,
        )
        err = result.get("error")
        if err:
            print(json.dumps({"npc_first_context_build_error": err}, indent=2), file=sys.stderr)
            return 2
        events = list(result.get("parsed_events") or [])
        context_build_cost_usd = float(result.get("cost_usd") or 0.0)
        timeline_grading = None
        if args.npc_first_timeline_gold is not None:
            tg_path = args.npc_first_timeline_gold.resolve()
            tg_raw = json.loads(tg_path.read_text(encoding="utf-8"))
            if isinstance(tg_raw, dict):
                timeline_grading = tg_raw.get("grading") if isinstance(tg_raw.get("grading"), dict) else tg_raw
        ctx_sidecar = build_npc_attachment_context_sidecar(
            scenario_id=scenario_id,
            units_json=units_json,
            parsed_events=events,
            manifest_jsonable=manifest_jsonable,
            timeline_grading=timeline_grading,
        )
        written = _write_npc_attachment_context_artifact(
            ctx_sidecar,
            scenario_id=scenario_id,
            no_writes=args.no_writes,
        )
        if written is not None:
            npc_ctx_disk_path = written
            print(str(written), file=sys.stderr)
        built_from_stage_a = True

    units_for_pipeline = units_json
    ctx_unit_ids: set[str] = set()
    if ctx_sidecar is not None:
        from evals.sentence_routing_retrieval_falsification.npc_first_context import (
            enrich_sentence_units_with_npc_attachment_context,
        )

        units_for_pipeline, enrich_stats = enrich_sentence_units_with_npc_attachment_context(
            units_json, ctx_sidecar
        )
        bu = ctx_sidecar.get("by_unit_id")
        if isinstance(bu, dict):
            ctx_unit_ids = {str(k) for k in bu.keys()}

    for i in range(n):
        try:
            b1_passed, b1_sidecar, b1_cost, b1_path = run_discourse_once(
                raw=raw,
                scenario_path=scenario_path,
                corpus_root=corpus_root,
                units_json=units_for_pipeline,
                manifest_jsonable=manifest_jsonable,
                manifest_slugs=manifest_slugs,
                model=model,
                no_llm=args.no_llm,
                no_writes=args.no_writes,
                preflight_meta=preflight_meta,
                prompt_variant=prompt_variant,
            )
            b2_discourse_path = b1_path if b1_path is not None else None
            b2_passed, b2_sidecar, b2_path = run_route_from_discourse_once(
                raw=raw,
                scenario_path=scenario_path,
                corpus_root=corpus_root,
                units_json=units_for_pipeline,
                manifest_jsonable=manifest_jsonable,
                manifest_slugs=manifest_slugs,
                gold_routing=gold_routing,
                discourse_path=b2_discourse_path,
                no_writes=args.no_writes,
                preflight_meta=preflight_meta,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

        pipeline_passed = b1_passed and b2_passed
        all_pass = all_pass and pipeline_passed
        b2_telem = b2_sidecar.get("telemetry") if isinstance(b2_sidecar, dict) else {}
        b2_breakdown = (
            b2_telem.get("stage_b_unit_breakdown")
            if isinstance(b2_telem, dict)
            else None
        )
        rec: dict[str, Any] = {
            "run_index": i,
            "pipeline_passed": pipeline_passed,
            "b1_passed": b1_passed,
            "b2_passed": b2_passed,
            "cost_usd": round(float(b1_cost), 6),
            "b1_sidecar_json": str(b1_path) if b1_path is not None else "",
            "b2_sidecar_json": str(b2_path) if b2_path is not None else "",
            "b1": {
                "violations": b1_sidecar.get("violations", {}).get("stage_b1", []),
                "stage_b1_unit_breakdown": b1_sidecar.get("telemetry", {}).get(
                    "stage_b1_unit_breakdown",
                    {},
                ),
            },
            "b2": {
                "violations": b2_sidecar.get("violations", {}).get("stage_b", []),
                "stage_b_unit_breakdown": b2_breakdown or {},
            },
        }
        rec["npc_first_context"] = {
            "enabled": ctx_sidecar is not None,
            "schema": ctx_sidecar.get("schema") if isinstance(ctx_sidecar, dict) else None,
            "sidecar_path": str(npc_ctx_disk_path) if npc_ctx_disk_path is not None else "",
            "built_from_stage_a": built_from_stage_a,
            "units_enriched": int(enrich_stats.get("units_enriched") or 0),
            "units_with_npc_slugs": int(enrich_stats.get("units_with_npc_slugs") or 0),
            "unit_ids_with_context": sorted(ctx_unit_ids),
            "context_build_cost_usd": round(context_build_cost_usd, 6) if i == 0 else 0.0,
        }
        rec["npc_first_context"].update(_b2_failure_partition_vs_npc_context(rec, ctx_unit_ids))
        records.append(rec)

    j_path, m_path = _write_split_pipeline_summary(
        records=records,
        model_id=model,
        scenario_id=scenario_id,
        no_writes=args.no_writes,
        preflight_meta=preflight_meta,
        npc_first_context_build_cost_usd=context_build_cost_usd,
    )
    if j_path is not None:
        print(str(j_path), file=sys.stderr)
    if m_path is not None:
        print(str(m_path), file=sys.stderr)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
