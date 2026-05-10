#!/usr/bin/env python3
"""Run session-memory query grading (JSONL records + gold scenarios).

Gold schema ``dmb_breadcrumb_query_natural_gold_v1`` can run either:
- retrieval+LLM synthesis (default), or
- retrieval-only gates (``--retrieval-only``).

Writes a default artifact under ``artifacts/runs/<date>/`` unless ``--output`` is set.

Examples:

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --breadcrumb-md evals/sentence_routing_retrieval_falsification/manual_labels/Session\\ 20\\ -\\ Recap.breadcrumbed.md \\
    --corpus-root corpus/eldyrwild-markdown

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --records-jsonl /tmp/session20.jsonl \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_closed_loop_v1.json

  # C1S1 natural gold: also refreshes c1s1-breadcrumb-query-benchmark-review.canvas.tsx (see README).
  # C1S2 natural gold: also refreshes c1s2-breadcrumb-query-benchmark-review.canvas.tsx (see README).
  # C1S3 natural gold: also refreshes c1s3-breadcrumb-query-benchmark-review.canvas.tsx (see README).

  # Ingestion loop: normalize → optional repair adjudication → JSONL → query grade + sentinel score

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \\
    --breadcrumb-md evals/sentence_routing_retrieval_falsification/manual_labels/Session\\ 20\\ -\\ Recap.breadcrumbed.md \\
    --corpus-root corpus/eldyrwild-markdown \\
    --repair-adjudicate \\
    --tagging-sentinel-json evals/sentence_routing_retrieval_falsification/gold/breadcrumb_tagging_sentinels_session20.json \\
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import blake3

from evals.sentence_routing_retrieval_falsification.c1s1_benchmark_canvas_emit import (
    c1s1_canvas_refresh_auto_enabled,
    refresh_c1s1_benchmark_canvases,
)
from evals.sentence_routing_retrieval_falsification.c1s2_benchmark_canvas_emit import (
    c1s2_canvas_refresh_auto_enabled,
    refresh_c1s2_benchmark_canvases,
)
from evals.sentence_routing_retrieval_falsification.c1s3_benchmark_canvas_emit import (
    c1s3_canvas_refresh_auto_enabled,
    refresh_c1s3_benchmark_canvases,
)
from evals.sentence_routing_retrieval_falsification.c1s13_benchmark_canvas_emit import (
    c1s13_canvas_refresh_auto_enabled,
    refresh_c1s13_benchmark_canvases,
)
from evals.sentence_routing_retrieval_falsification.cursor_canvas_paths import (
    default_cursor_canvas_path,
    ensure_canvas_file_for_patch,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    BreadcrumbNormalizeError,
    NormalizedRecord,
    extract_frontmatter_route_allowlist,
    extract_meta_from_frontmatter,
    normalize_for_alignment,
    normalize_breadcrumb_artifact,
    strip_leading_heading_lines,
    write_records_jsonl,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_prompt import (
    ALLOWED_VARIANTS as BREADCRUMB_PROMPT_VARIANTS,
    PROMPT_VARIANT_CONTROL,
    PROMPT_VARIANT_CONTINUATION,
    build_breadcrumb_prompt,
    build_breadcrumb_route_prompt,
    extract_breadcrumb_markdown,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_render import (
    render_routing_only_breadcrumb_markdown,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_schema import (
    BreadcrumbRouteAssignmentsV1,
    validate_route_assignments,
)
from evals.sentence_routing_retrieval_falsification.capture import (
    capture_sentence_unit_spans,
    capture_sentence_units,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    TAG_RE,
    parse_inline_tags,
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload import (
    build_payload as build_canvas_payload,
    render_generated_block as render_canvas_block,
    update_canvas_text as update_canvas_text_block,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    aggregate_context_evidence_metrics,
    grade_natural_scenario,
    grade_scenario,
    load_gold,
    merge_natural_benchmark_scenario,
    natural_retrieval_bundle,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_natural_scoring import (
    build_hit_context_text,
    index_records_by_unit_id,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_llm import (
    format_synthesis_user_message,
    resolve_breadcrumb_query_llm_model,
    synthesize_answer_from_hit_context,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_semantic_similarity import (
    EMBEDDING_MODEL_DEFAULT,
    compare_expected_to_output_with_embeddings,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_repair import (
    adjudicate_repairs_with_llm,
    apply_repair_patches,
    find_repair_candidates,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_scorer import (
    read_tagging_sentinels,
    score_normalized_records,
)
from evals.sentence_routing_retrieval_falsification.route_equivalence_shadow import (
    ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
    build_route_equivalence_shadow_payload,
    load_route_equivalence_shadow_records,
)
from evals.sentence_routing_retrieval_falsification.token_resolver_shadow import (
    build_campaign_lexicon,
    compute_shadow_diff,
    get_benchmark_lexicon_seeds,
)
from src.agent.synthesis import _load_api_key
from src.agent.planner_pricing import usage_cost_usd
from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.llm.api_client import DungeonMindApiClient

_PROMOTED_CONTEXT_MAX_LEXICAL_UNITS_DEFAULT = 8
_PROMOTED_CONTEXT_MAX_CHARS_DEFAULT = 2400
_DEFAULT_BREADCRUMB_INGEST_MODEL = "gpt-5.3-codex"


def _resolve_repair_model(cli_model: str | None) -> str:
    return (
        (cli_model or "").strip()
        or os.environ.get("DMB_BREADCRUMB_REPAIR_MODEL", "").strip()
        or "gpt-5.4-mini"
    )


def _resolve_breadcrumb_ingest_model(cli_model: str | None) -> str:
    return (
        (cli_model or "").strip()
        or os.environ.get("DMB_BREADCRUMB_INGEST_MODEL", "").strip()
        or _DEFAULT_BREADCRUMB_INGEST_MODEL
    )


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


def _count_non_meta_routed_records(records: list[NormalizedRecord]) -> int:
    count = 0
    for rec in records:
        uid = str(rec.unit_id or "")
        if uid.startswith("meta-"):
            continue
        if rec.routes:
            count += 1
    return count


def _first_mismatch_details(*, expected: str, actual: str, window: int = 160) -> dict[str, Any]:
    idx = 0
    max_idx = min(len(expected), len(actual))
    while idx < max_idx and expected[idx] == actual[idx]:
        idx += 1
    start = max(0, idx - window // 2)
    end_expected = min(len(expected), idx + window // 2)
    end_actual = min(len(actual), idx + window // 2)
    return {
        "first_mismatch_index": idx,
        "expected_len": len(expected),
        "actual_len": len(actual),
        "expected_excerpt": expected[start:end_expected],
        "actual_excerpt": actual[start:end_actual],
    }


def _ingest_attempt_diagnostics(*, candidate_md: str, recap_body: str) -> dict[str, Any]:
    _fm, body = parse_frontmatter_and_body(candidate_md)
    body_plain = TAG_RE.sub("", strip_leading_heading_lines(body or candidate_md))
    units = capture_sentence_units(recap_text=recap_body, recap_relative_path="__ingest_diag__")
    expected_joint = normalize_for_alignment("".join(normalize_for_alignment(u.text) for u in units))
    actual_plain = normalize_for_alignment(body_plain)
    drift = _first_mismatch_details(expected=expected_joint, actual=actual_plain)
    return {
        "expected_joint_blake3": blake3.blake3(expected_joint.encode("utf-8")).hexdigest(),
        "actual_plain_blake3": blake3.blake3(actual_plain.encode("utf-8")).hexdigest(),
        "plain_equal_after_normalization": expected_joint == actual_plain,
        "inline_tag_count": len(parse_inline_tags(candidate_md)),
        "mismatch": drift,
    }


def _relative_to_corpus(*, corpus_root: Path, recap_path: Path) -> str:
    try:
        return str(recap_path.resolve().relative_to(corpus_root.resolve()))
    except ValueError as exc:
        raise SystemExit(
            f"--ingest-recap-md must live under --corpus-root. recap={recap_path} corpus_root={corpus_root}"
        ) from exc


def _normalize_recap_body_for_prompt(recap_body: str) -> str:
    """Prompt-facing recap normalization to reduce heading-echo drift.

    C2S20-style recaps are mostly plain narrative paragraphs; some sessions include
    intermediate markdown headings (e.g., "## Major Beats"). We strip markdown
    heading lines before prompting so the model focuses on source prose rather than
    reproducing editorial section markers.
    """
    lines = str(recap_body or "").splitlines()
    kept: list[str] = []
    for line in lines:
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _generate_breadcrumb_artifact(
    *,
    recap_md: Path,
    frontmatter_seed_md: Path,
    corpus_root: Path,
    variant: str,
    model: str,
    out_path: Path,
    min_routed_records: int,
) -> dict[str, Any]:
    recap_text = recap_md.read_text(encoding="utf-8")
    _recap_fm, recap_body = parse_frontmatter_and_body(recap_text)
    if not recap_body.strip():
        raise SystemExit(f"recap markdown has no body content: {recap_md}")
    recap_body_for_prompt = _normalize_recap_body_for_prompt(recap_body)
    if not recap_body_for_prompt.strip():
        raise SystemExit(
            f"recap body empty after heading normalization: {recap_md}"
        )
    seed_text = frontmatter_seed_md.read_text(encoding="utf-8")
    seed_frontmatter, _seed_body = parse_frontmatter_and_body(seed_text)
    if seed_frontmatter is None:
        raise SystemExit(f"frontmatter seed missing YAML frontmatter: {frontmatter_seed_md}")
    try:
        seed_meta = extract_meta_from_frontmatter(seed_frontmatter)
    except BreadcrumbNormalizeError as exc:
        raise SystemExit(f"invalid frontmatter seed metadata: {exc}") from exc
    seed_routes = extract_frontmatter_route_allowlist(seed_frontmatter)
    if not seed_routes:
        raise SystemExit(
            f"frontmatter seed has no route/proposed_route allowlist entries: {frontmatter_seed_md}"
        )
    recap_rel = _relative_to_corpus(corpus_root=corpus_root, recap_path=recap_md)
    seed_source = str(seed_meta.get("source_recap_path") or "").strip()
    if seed_source != recap_rel:
        raise SystemExit(
            "frontmatter seed source_recap_path mismatch: "
            f"seed={seed_source!r} recap_rel={recap_rel!r}. "
            "Use a seed aligned to this recap."
        )

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        raise SystemExit(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Required for --ingest-recap-md prompt generation."
        )
    from openai import OpenAI

    client = OpenAI()
    variants: list[str] = [variant]
    if variant != PROMPT_VARIANT_CONTROL:
        variants.append(PROMPT_VARIANT_CONTROL)
    attempt_reports: list[dict[str, Any]] = []
    total_cost_usd = 0.0
    chosen_variant = variant
    breadcrumb_md = ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt_idx, attempt_variant in enumerate(variants, start=1):
        routed_records = 0
        prompt = build_breadcrumb_prompt(
            variant=attempt_variant,
            recap_body=recap_body_for_prompt,
            frontmatter_yaml=seed_frontmatter,
        )
        response = client.responses.create(
            model=model,
            instructions=prompt.system_text,
            input=[{"type": "message", "role": "user", "content": prompt.user_text}],
        )
        raw_text = (getattr(response, "output_text", None) or "").strip()
        candidate_md = extract_breadcrumb_markdown(raw_text)
        attempt_artifact_path = out_path.parent / (
            f"{out_path.stem}.attempt{attempt_idx}.{attempt_variant}.failed.md"
        )
        attempt_artifact_path.write_text(candidate_md, encoding="utf-8")
        usage = _usage_tokens(response)
        cost = usage_cost_usd(
            model_id=model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
        )
        total_cost_usd += float(cost.get("total_usd") or 0.0)
        try:
            # Readiness gate: only accept an artifact that normalizes cleanly.
            rec_objs, _meta = normalize_breadcrumb_artifact(
                artifact_text=candidate_md,
                corpus_root=corpus_root,
            )
            routed_records = _count_non_meta_routed_records(rec_objs)
            if routed_records < int(min_routed_records):
                raise BreadcrumbNormalizeError(
                    "generated breadcrumb has insufficient inline routed records "
                    f"(required>={int(min_routed_records)}, found={routed_records})"
                )
        except BreadcrumbNormalizeError as exc:
            attempt_diag = _ingest_attempt_diagnostics(candidate_md=candidate_md, recap_body=recap_body)
            attempt_reports.append(
                {
                    "attempt": attempt_idx,
                    "variant": attempt_variant,
                    "ok": False,
                    "error": str(exc),
                    "cost_usd": float(cost.get("total_usd") or 0.0),
                    "usage": usage,
                    "non_meta_routed_record_count": int(routed_records),
                    "attempt_artifact_path": str(attempt_artifact_path.resolve()),
                    "text_diagnostics": attempt_diag,
                }
            )
            continue
        if attempt_artifact_path.exists():
            attempt_artifact_path.unlink()
        breadcrumb_md = candidate_md
        chosen_variant = attempt_variant
        attempt_reports.append(
            {
                "attempt": attempt_idx,
                "variant": attempt_variant,
                "ok": True,
                "cost_usd": float(cost.get("total_usd") or 0.0),
                "usage": usage,
                "non_meta_routed_record_count": int(routed_records),
            }
        )
        break
    if not breadcrumb_md:
        diag_path = out_path.parent / f"{out_path.stem}.ingest_diagnostics.json"
        diag_payload = {
            "schema": "dmb_breadcrumb_ingest_diagnostics_v1",
            "recap_md": str(recap_md.resolve()),
            "frontmatter_seed_md": str(frontmatter_seed_md.resolve()),
            "output_path_requested": str(out_path.resolve()),
            "model": model,
            "variant_requested": variant,
            "attempts": attempt_reports,
            "cost_usd": float(total_cost_usd),
        }
        diag_path.write_text(json.dumps(diag_payload, indent=2), encoding="utf-8")
        compact = "; ".join(
            f"{a['variant']} (${float(a.get('cost_usd') or 0.0):.4f}): {a.get('error', 'unknown')}"
            for a in attempt_reports
        )
        raise SystemExit(
            "breadcrumb prompt ingestion failed readiness gate after variant retries. "
            f"attempts={compact}; diagnostics={diag_path}"
        )
    out_path.write_text(breadcrumb_md, encoding="utf-8")

    return {
        "artifact_path": str(out_path.resolve()),
        "model": model,
        "variant_requested": variant,
        "variant_selected": chosen_variant,
        "frontmatter_seed": str(frontmatter_seed_md.resolve()),
        "source_recap": recap_rel,
        "prompt_input_normalization": "strip_markdown_headings_c2s20_style",
        "attempts": attempt_reports,
        "cost_usd": float(total_cost_usd),
    }


def _generate_breadcrumb_artifact_routing_only(
    *,
    recap_md: Path,
    frontmatter_seed_md: Path,
    corpus_root: Path,
    variant: str,
    model: str,
    out_path: Path,
    min_routed_records: int,
) -> dict[str, Any]:
    """Structured route assignment + deterministic injection (no recap prose from the model)."""
    recap_text = recap_md.read_text(encoding="utf-8")
    _recap_fm, recap_body = parse_frontmatter_and_body(recap_text)
    if not recap_body.strip():
        raise SystemExit(f"recap markdown has no body content: {recap_md}")
    seed_text = frontmatter_seed_md.read_text(encoding="utf-8")
    seed_frontmatter, _seed_body = parse_frontmatter_and_body(seed_text)
    if seed_frontmatter is None:
        raise SystemExit(f"frontmatter seed missing YAML frontmatter: {frontmatter_seed_md}")
    try:
        seed_meta = extract_meta_from_frontmatter(seed_frontmatter)
    except BreadcrumbNormalizeError as exc:
        raise SystemExit(f"invalid frontmatter seed metadata: {exc}") from exc
    seed_routes = extract_frontmatter_route_allowlist(seed_frontmatter)
    if not seed_routes:
        raise SystemExit(
            f"frontmatter seed has no route/proposed_route allowlist entries: {frontmatter_seed_md}"
        )
    recap_rel = _relative_to_corpus(corpus_root=corpus_root, recap_path=recap_md)
    seed_source = str(seed_meta.get("source_recap_path") or "").strip()
    if seed_source != recap_rel:
        raise SystemExit(
            "frontmatter seed source_recap_path mismatch: "
            f"seed={seed_source!r} recap_rel={recap_rel!r}. "
            "Use a seed aligned to this recap."
        )

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        raise SystemExit(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py). Required for --ingest-routing-only."
        )

    spans = capture_sentence_unit_spans(recap_text=recap_body, recap_relative_path=recap_rel)
    units_payload: list[dict[str, object]] = [
        {
            "unit_id": s.unit_id,
            "line_start": s.line_start,
            "line_end": s.line_end,
            "text": s.text,
        }
        for s in spans
    ]
    allowed_routes = sorted(seed_routes)
    prompt = build_breadcrumb_route_prompt(
        variant=variant,
        source_recap_path=recap_rel,
        recap_body=recap_body,
        frontmatter_yaml=seed_frontmatter,
        units=units_payload,
        allowed_routes=allowed_routes,
    )

    from openai import OpenAI

    client = OpenAI()
    api = DungeonMindApiClient.wrap(client)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        api_result = api.responses_parse(
            action="breadcrumb_inline.route_assignments_v1",
            model=model,
            input=[
                {"role": "system", "content": prompt.system_text},
                {"role": "user", "content": prompt.user_text},
            ],
            text_format=BreadcrumbRouteAssignmentsV1,
        )
    except Exception as exc:
        raise SystemExit(f"routing-only ingest: OpenAI responses.parse failed: {exc}") from exc

    response = api_result.response
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise SystemExit(
            "routing-only ingest: missing output_parsed from responses.parse "
            "(structured output failed)"
        )
    if not isinstance(parsed, BreadcrumbRouteAssignmentsV1):
        parsed = BreadcrumbRouteAssignmentsV1.model_validate(parsed)

    usage = _usage_tokens(response)
    cost = usage_cost_usd(
        model_id=model,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
    )
    total_cost_usd = float(cost.get("total_usd") or 0.0)

    try:
        validate_route_assignments(
            parsed,
            expected_source_recap_path=recap_rel,
            known_unit_ids={s.unit_id for s in spans},
            route_allowlist_normalized=seed_routes,
        )
        breadcrumb_md = render_routing_only_breadcrumb_markdown(
            seed_frontmatter_yaml=seed_frontmatter,
            recap_body=recap_body,
            spans=spans,
            assignments=parsed,
        )
        rec_objs, _meta = normalize_breadcrumb_artifact(
            artifact_text=breadcrumb_md,
            corpus_root=corpus_root,
        )
        routed_records = _count_non_meta_routed_records(rec_objs)
        if routed_records < int(min_routed_records):
            raise BreadcrumbNormalizeError(
                "routing-only breadcrumb has insufficient inline routed records "
                f"(required>={int(min_routed_records)}, found={routed_records})"
            )
    except BreadcrumbNormalizeError as exc:
        diag_path = out_path.parent / f"{out_path.stem}.routing_only_ingest_diagnostics.json"
        diag_payload = {
            "schema": "dmb_breadcrumb_routing_only_ingest_diagnostics_v1",
            "recap_md": str(recap_md.resolve()),
            "frontmatter_seed_md": str(frontmatter_seed_md.resolve()),
            "output_path_requested": str(out_path.resolve()),
            "model": model,
            "variant": variant,
            "error": str(exc),
            "cost_usd": total_cost_usd,
            "usage": usage,
            "assignments": parsed.model_dump(by_alias=True),
        }
        diag_path.write_text(json.dumps(diag_payload, indent=2), encoding="utf-8")
        raise SystemExit(
            f"routing-only ingest failed readiness gate: {exc}; diagnostics={diag_path}"
        ) from exc

    out_path.write_text(breadcrumb_md, encoding="utf-8")

    return {
        "artifact_path": str(out_path.resolve()),
        "model": model,
        "variant_requested": variant,
        "variant_selected": variant,
        "frontmatter_seed": str(frontmatter_seed_md.resolve()),
        "source_recap": recap_rel,
        "ingest_mode": "routing_only_structured",
        "prompt_input_normalization": "none_full_recap_body_for_units",
        "attempts": [
            {
                "attempt": 1,
                "variant": variant,
                "ok": True,
                "cost_usd": total_cost_usd,
                "usage": usage,
                "non_meta_routed_record_count": int(routed_records),
            }
        ],
        "cost_usd": float(total_cost_usd),
    }


_DEFAULT_BREADCRUMB_QUERY_SEMANTIC_CANVAS = default_cursor_canvas_path("breadcrumb-query-semantic-review.canvas.tsx")
_DEFAULT_C1S1_BENCHMARK_CANVAS = default_cursor_canvas_path("c1s1-breadcrumb-query-benchmark-review.canvas.tsx")
_DEFAULT_C1S2_BENCHMARK_CANVAS = default_cursor_canvas_path("c1s2-breadcrumb-query-benchmark-review.canvas.tsx")
_DEFAULT_C1S3_BENCHMARK_CANVAS = default_cursor_canvas_path("c1s3-breadcrumb-query-benchmark-review.canvas.tsx")
_DEFAULT_C1S13_BENCHMARK_CANVAS = default_cursor_canvas_path("c1s13-breadcrumb-query-benchmark-review.canvas.tsx")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--breadcrumb-md", type=Path, help="Breadcrumb markdown artifact")
    parser.add_argument(
        "--ingest-recap-md",
        type=Path,
        default=None,
        help=(
            "Generate breadcrumb markdown from this recap via breadcrumb prompt, "
            "then continue normalize->records->retrieval in the same run."
        ),
    )
    parser.add_argument(
        "--ingest-routing-only",
        action="store_true",
        help=(
            "With --ingest-recap-md: use structured route assignment (responses.parse) "
            "and a deterministic renderer instead of full markdown generation."
        ),
    )
    parser.add_argument(
        "--ingest-frontmatter-seed-md",
        type=Path,
        default=None,
        help=(
            "Frontmatter seed markdown (with route/proposed_route index) used for "
            "--ingest-recap-md prompt generation."
        ),
    )
    parser.add_argument(
        "--ingest-breadcrumb-variant",
        choices=sorted(BREADCRUMB_PROMPT_VARIANTS),
        default=PROMPT_VARIANT_CONTINUATION,
        help=(
            "Prompt variant for --ingest-recap-md generation "
            f"(default: {PROMPT_VARIANT_CONTINUATION})."
        ),
    )
    parser.add_argument(
        "--ingest-breadcrumb-model",
        type=str,
        default=None,
        help=(
            "Model id for --ingest-recap-md generation "
            f"(else DMB_BREADCRUMB_INGEST_MODEL or {_DEFAULT_BREADCRUMB_INGEST_MODEL})."
        ),
    )
    parser.add_argument(
        "--ingest-breadcrumb-out",
        type=Path,
        default=None,
        help="Optional output path for generated breadcrumb markdown.",
    )
    parser.add_argument(
        "--ingest-min-routed-records",
        type=int,
        default=1,
        help=(
            "When using --ingest-recap-md, require at least this many non-meta "
            "records with inline routes after normalization (default: 1). "
            "Set 0 to disable."
        ),
    )
    parser.add_argument("--corpus-root", type=Path, help="Corpus root (required with --breadcrumb-md)")
    parser.add_argument("--records-jsonl", type=Path, help="Pre-built JSONL records")
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_closed_loop_v1.json"),
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="Natural gold only: OpenAI model id (else DMB_BREADCRUMB_QUERY_LLM_MODEL or MODEL_POLICY ruleslawyer_response_synthesis).",
    )
    parser.add_argument(
        "--semantic-similarity",
        action="store_true",
        help="Natural gold only: embed expected_answer vs synthesized answer and record cosine similarity.",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help=(
            "Natural gold only: skip LLM answer synthesis and run retrieval-only gates "
            "(route/unit/query-mode/context evidence + deterministic semantic-on-context)."
        ),
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=EMBEDDING_MODEL_DEFAULT,
        help="Embedding model for --semantic-similarity (default: text-embedding-3-large).",
    )
    parser.add_argument("--output", type=Path, help="Write report JSON here")
    parser.add_argument(
        "--canvas-tsx",
        nargs="?",
        const=_DEFAULT_BREADCRUMB_QUERY_SEMANTIC_CANVAS,
        default=None,
        type=Path,
        help=(
            "After the report is written, regenerate the breadcrumb query semantic review canvas "
            "(breadcrumb_query_canvas_payload). Pass a path, or pass the flag alone to use the default "
            f"Cursor-managed file: {_DEFAULT_BREADCRUMB_QUERY_SEMANTIC_CANVAS} "
            "(override canvases parent with DMB_CURSOR_CANVAS_DIR). Omit the flag to skip."
        ),
    )
    parser.add_argument(
        "--canvas-baseline-report",
        type=Path,
        default=None,
        help="Baseline report JSON to compare against when refreshing the canvas (optional).",
    )
    parser.add_argument(
        "--canvas-deterministic-report",
        type=Path,
        default=None,
        help="Deterministic-only report JSON paired with the canvas refresh (optional).",
    )
    parser.add_argument(
        "--c1s1-canvas-tsx",
        type=Path,
        action="append",
        default=None,
        dest="c1s1_canvas_tsx",
        metavar="PATH",
        help=(
            "C1S1 benchmark review canvas (.canvas.tsx). Repeat to patch multiple files. "
            "When omitted, auto C1S1 runs use the Cursor-managed default "
            f"(override parent with DMB_CURSOR_CANVAS_DIR): {_DEFAULT_C1S1_BENCHMARK_CANVAS}. "
            "Passing this flag once or more also forces C1S1 canvas refresh for non-C1S1 gold."
        ),
    )
    parser.add_argument(
        "--skip-c1s1-canvas-refresh",
        action="store_true",
        help="Do not patch the C1S1 benchmark review canvas (overrides auto refresh for C1S1 gold).",
    )
    parser.add_argument(
        "--c1s2-canvas-tsx",
        type=Path,
        action="append",
        default=None,
        dest="c1s2_canvas_tsx",
        metavar="PATH",
        help=(
            "C1S2 benchmark review canvas (.canvas.tsx). Repeat to patch multiple files. "
            "When omitted, auto C1S2 runs use the Cursor-managed default "
            f"(override parent with DMB_CURSOR_CANVAS_DIR): {_DEFAULT_C1S2_BENCHMARK_CANVAS}. "
            "Passing this flag once or more also forces C1S2 canvas refresh for non-C1S2 gold."
        ),
    )
    parser.add_argument(
        "--skip-c1s2-canvas-refresh",
        action="store_true",
        help="Do not patch the C1S2 benchmark review canvas (overrides auto refresh for C1S2 gold).",
    )
    parser.add_argument(
        "--c1s3-canvas-tsx",
        type=Path,
        action="append",
        default=None,
        dest="c1s3_canvas_tsx",
        metavar="PATH",
        help=(
            "C1S3 benchmark review canvas (.canvas.tsx). Repeat to patch multiple files. "
            "When omitted, auto C1S3 runs use the Cursor-managed default "
            f"(override parent with DMB_CURSOR_CANVAS_DIR): {_DEFAULT_C1S3_BENCHMARK_CANVAS}. "
            "Passing this flag once or more also forces C1S3 canvas refresh for non-C1S3 gold."
        ),
    )
    parser.add_argument(
        "--skip-c1s3-canvas-refresh",
        action="store_true",
        help="Do not patch the C1S3 benchmark review canvas (overrides auto refresh for C1S3 gold).",
    )
    parser.add_argument(
        "--c1s13-canvas-tsx",
        type=Path,
        action="append",
        default=None,
        dest="c1s13_canvas_tsx",
        metavar="PATH",
        help=(
            "C1S13 benchmark review canvas (.canvas.tsx). Repeat to patch multiple files. "
            "When omitted, auto C1S13 runs use the Cursor-managed default "
            f"(override parent with DMB_CURSOR_CANVAS_DIR): {_DEFAULT_C1S13_BENCHMARK_CANVAS}. "
            "Passing this flag once or more also forces C1S13 canvas refresh for non-C1S13 gold."
        ),
    )
    parser.add_argument(
        "--skip-c1s13-canvas-refresh",
        action="store_true",
        help="Do not patch the C1S13 benchmark review canvas (overrides auto refresh for C1S13 gold).",
    )
    parser.add_argument(
        "--repair-adjudicate",
        action="store_true",
        help=(
            "After normalizing --breadcrumb-md, run deterministic repair candidates + "
            "one OpenAI Responses adjudication pass, then merge allowed patches into records."
        ),
    )
    parser.add_argument(
        "--pronoun-route-handles",
        action="store_true",
        help=(
            "When normalizing --breadcrumb-md, enrich pronoun-bearing records with "
            "route-derived lexical handles from their own breadcrumbs."
        ),
    )
    parser.add_argument(
        "--repair-model",
        type=str,
        default=None,
        help="Model for --repair-adjudicate (else DMB_BREADCRUMB_REPAIR_MODEL or gpt-5.4-mini).",
    )
    parser.add_argument(
        "--tagging-sentinel-json",
        type=Path,
        default=None,
        help=(
            "Optional sentinel gold (schema dmb_breadcrumb_tagging_sentinels_v1). "
            "Requires --breadcrumb-md. Adds tagging_score to the report."
        ),
    )
    parser.add_argument(
        "--route-equivalence-jsonl",
        type=Path,
        action="append",
        default=None,
        help=(
            "Path to a committed route_equivalence_*_v1.jsonl artifact. May be "
            "passed multiple times to combine campaigns (e.g. C1 + C2). "
            "Shadow-only: when set, each natural-gold scenario row gains a "
            "'shadow_route_equivalences' diagnostic field. Legacy lexicon "
            "seeds remain the active source; no retrieval or grading change."
        ),
    )
    parser.add_argument(
        "--tagging-baseline-md",
        type=Path,
        default=Path(
            "evals/sentence_routing_retrieval_falsification/manual_labels/"
            "Session 20 - Recap.breadcrumbed.md"
        ),
        help=(
            "Baseline breadcrumb markdown for precision/recall vs tagged markup "
            "(default: Session 20 manual baseline). Omitted after repair adds routes "
            "(markdown body was not rewritten)."
        ),
    )
    args = parser.parse_args()

    if bool(getattr(args, "ingest_routing_only", False)) and args.ingest_recap_md is None:
        raise SystemExit("--ingest-routing-only requires --ingest-recap-md")

    suite_dir = Path(__file__).resolve().parent
    default_out = suite_dir / "artifacts" / "runs" / str(date.today()) / "breadcrumb_query_run_report.json"

    rec_objs: list[NormalizedRecord] | None = None
    breadcrumb_art_text: str | None = None
    meta: dict[str, Any] = {}
    repair_report_json: dict[str, Any] | None = None
    repair_cost_usd = 0.0
    ingest_cost_usd = 0.0
    breadcrumb_ingest_report: dict[str, Any] | None = None
    corpus_root_resolved: Path | None = None

    if args.ingest_recap_md is not None:
        if args.records_jsonl is not None:
            raise SystemExit("--ingest-recap-md cannot be combined with --records-jsonl")
        if args.breadcrumb_md is not None:
            raise SystemExit("--ingest-recap-md cannot be combined with --breadcrumb-md")
        if args.ingest_frontmatter_seed_md is None:
            raise SystemExit("--ingest-frontmatter-seed-md is required with --ingest-recap-md")
        if not args.corpus_root:
            raise SystemExit("--corpus-root is required with --ingest-recap-md")
        corpus_root_resolved = Path(args.corpus_root).resolve()
        recap_path = Path(args.ingest_recap_md).resolve()
        seed_path = Path(args.ingest_frontmatter_seed_md).resolve()
        if args.ingest_breadcrumb_out is not None:
            ingest_out = Path(args.ingest_breadcrumb_out).resolve()
        else:
            stem = recap_path.stem.replace(" ", "_")
            ingest_out = (
                suite_dir
                / "artifacts"
                / "runs"
                / str(date.today())
                / f"{stem}.breadcrumbed.generated.md"
            )
        ingest_model = _resolve_breadcrumb_ingest_model(args.ingest_breadcrumb_model)
        if bool(args.ingest_routing_only):
            breadcrumb_ingest_report = _generate_breadcrumb_artifact_routing_only(
                recap_md=recap_path,
                frontmatter_seed_md=seed_path,
                corpus_root=corpus_root_resolved,
                variant=str(args.ingest_breadcrumb_variant),
                model=ingest_model,
                out_path=ingest_out,
                min_routed_records=max(0, int(args.ingest_min_routed_records)),
            )
        else:
            breadcrumb_ingest_report = _generate_breadcrumb_artifact(
                recap_md=recap_path,
                frontmatter_seed_md=seed_path,
                corpus_root=corpus_root_resolved,
                variant=str(args.ingest_breadcrumb_variant),
                model=ingest_model,
                out_path=ingest_out,
                min_routed_records=max(0, int(args.ingest_min_routed_records)),
            )
        ingest_cost_usd = float(breadcrumb_ingest_report.get("cost_usd") or 0.0)
        args.breadcrumb_md = Path(str(breadcrumb_ingest_report["artifact_path"]))

    if args.records_jsonl:
        if args.repair_adjudicate:
            raise SystemExit("--repair-adjudicate requires --breadcrumb-md")
        if args.tagging_sentinel_json is not None:
            raise SystemExit("--tagging-sentinel-json requires --breadcrumb-md")
        records_path = args.records_jsonl
        lines = records_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
    elif args.breadcrumb_md:
        if not args.corpus_root:
            raise SystemExit("--corpus-root is required with --breadcrumb-md")
        art = args.breadcrumb_md.read_text(encoding="utf-8")
        breadcrumb_art_text = art
        corpus_root_resolved = Path(args.corpus_root).resolve()
        rec_objs, meta = normalize_breadcrumb_artifact(
            artifact_text=art,
            corpus_root=corpus_root_resolved,
            enrich_pronoun_route_handles=bool(args.pronoun_route_handles),
        )

        if args.repair_adjudicate:
            load_dungeonmindbuddy_dotenv()
            if not (_load_api_key() or "").strip():
                raise SystemExit(
                    "OPENAI_API_KEY missing after loading .env / .env.development "
                    "(see src/bootstrap_env.py). Required for --repair-adjudicate."
                )
            from openai import OpenAI

            candidates = find_repair_candidates(rec_objs)
            repair_model = _resolve_repair_model(args.repair_model)
            if not candidates:
                repair_report_json = {
                    "enabled": True,
                    "skipped": "no_candidates",
                    "candidate_count": 0,
                    "cost_usd": 0.0,
                    "model": repair_model,
                }
            else:
                recap_path = corpus_root_resolved / rec_objs[0].source_recap_path
                recap_full = recap_path.read_text(encoding="utf-8")
                _rfm, recap_body = parse_frontmatter_and_body(recap_full)
                client = OpenAI()
                try:
                    patches, repair_cost_usd, telemetry, raw_text = adjudicate_repairs_with_llm(
                        client=client,
                        model=repair_model,
                        recap_body=recap_body,
                        candidates=candidates,
                    )
                except (json.JSONDecodeError, ValueError) as exc:
                    repair_report_json = {
                        "enabled": True,
                        "error": f"repair_parse_failed: {exc}",
                        "candidate_count": len(candidates),
                        "cost_usd": 0.0,
                        "model": repair_model,
                    }
                    patches = []
                    raw_text = ""
                    telemetry = {}
                else:
                    candidate_ids = {c.unit_id for c in candidates}
                    allowed_routes = {c.unit_id: set(c.nearby_subject_routes) for c in candidates}
                    apply_rep = apply_repair_patches(
                        rec_objs,
                        patches,
                        candidate_unit_ids=candidate_ids,
                        allowed_routes_by_unit=allowed_routes,
                    )
                    repair_report_json = {
                        "enabled": True,
                        "model": repair_model,
                        "candidate_count": len(candidates),
                        "cost_usd": repair_cost_usd,
                        "telemetry": telemetry,
                        "raw_response_preview": raw_text[:2000],
                        "apply_report": apply_rep.to_json_dict(),
                    }

        records = [r.to_json_dict() for r in rec_objs]
        meta_path = default_out.with_name(default_out.stem + "_records_meta.json")
        if args.output:
            meta_path = args.output.with_suffix(".records_meta.json")
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        records_path = meta_path.with_suffix(".jsonl")
        write_records_jsonl(rec_objs, records_path)
    else:
        raise SystemExit("Provide --records-jsonl or (--breadcrumb-md and --corpus-root)")

    gold = load_gold(args.gold)
    sch = str(gold.get("schema") or "")
    results: list[dict[str, Any]] = []
    llm_model: str | None = None
    aggregate_llm_cost_usd = 0.0
    aggregate_embedding_cost_usd = 0.0

    shadow_lexicon: Any | None = None
    shadow_build_error = ""
    legacy_route_stopwords_snapshot: list[str] = []
    legacy_module_equivalences: dict[str, list[str]] = {}

    if args.semantic_similarity and sch != "dmb_breadcrumb_query_natural_gold_v1":
        raise SystemExit(
            "--semantic-similarity requires gold schema dmb_breadcrumb_query_natural_gold_v1 "
            "(compares expected_answer to synthesized LLM output)."
        )
    if args.semantic_similarity and args.retrieval_only:
        raise SystemExit("--semantic-similarity cannot be combined with --retrieval-only")

    if sch == "dmb_breadcrumb_query_natural_gold_v1":
        if not args.retrieval_only:
            load_dungeonmindbuddy_dotenv()
            if not (_load_api_key() or "").strip():
                raise SystemExit(
                    "OPENAI_API_KEY missing after loading .env / .env.development "
                    "(see src/bootstrap_env.py). Required for natural gold runs (LLM synthesis)."
                )
            llm_model = (args.llm_model or "").strip() or resolve_breadcrumb_query_llm_model()
        default_campaign = str(gold.get("campaign_id") or "")
        default_spec = gold.get("default_query_spec") or {}

        # Shadow-mode token resolution: run the new layered resolver alongside
        # the legacy expansion/scoring inputs and emit a diff per scenario.
        # This stays read-only — the legacy code path remains authoritative.
        try:
            _bench_seeds = get_benchmark_lexicon_seeds()
            legacy_route_stopwords_snapshot = sorted(_bench_seeds.legacy_route_stopwords_for_shadow_diff)
            legacy_module_equivalences = {
                str(k): list(v) for k, v in _bench_seeds.equivalences.items()
            }
            # Always pass normalized ``records`` (dict rows). When ingesting from
            # ``--records-jsonl``, ``rec_objs`` is None but ``records`` is loaded;
            # using ``rec_objs or []`` would incorrectly build an empty lexicon.
            shadow_lexicon = build_campaign_lexicon(
                breadcrumb_artifact_text=breadcrumb_art_text or "",
                records=records,
                breadcrumb_md_path=args.breadcrumb_md if args.breadcrumb_md else None,
                campaign_id=default_campaign,
            )
        except Exception as exc:  # noqa: BLE001 - shadow mode must never break the run
            shadow_lexicon = None
            legacy_route_stopwords_snapshot = []
            legacy_module_equivalences = {}
            shadow_build_error = f"{type(exc).__name__}: {exc}"
        else:
            shadow_build_error = ""

        route_equivalence_records = None
        route_equivalence_paths_resolved: list[Path] = []
        _HARNESS_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
        route_equivalence_load_error = ""
        if args.route_equivalence_jsonl:
            try:
                route_equivalence_paths_resolved = [
                    Path(p).resolve() for p in args.route_equivalence_jsonl
                ]
                route_equivalence_records = load_route_equivalence_shadow_records(
                    route_equivalence_paths_resolved
                )
            except (OSError, ValueError) as exc:
                route_equivalence_records = None
                route_equivalence_load_error = f"{type(exc).__name__}: {exc}"

        for scenario in gold.get("scenarios") or []:
            scen = merge_natural_benchmark_scenario(dict(scenario), gold)
            bundle = natural_retrieval_bundle(records=records, scenario=scen)
            result, hit_ctx = bundle
            by_unit = index_records_by_unit_id(records)
            hit_ctx_full = build_hit_context_text(
                result.hits,
                by_unit,
                include_normalized_route_lines=True,
            )
            hit_ctx_llm = build_hit_context_text(
                result.hits,
                by_unit,
                include_normalized_route_lines=False,
                exclude_path_like_lexical_units=True,
                query_tokens=[str(x) for x in (result.trace.get("query_tokens") or [])],
                max_lexical_units=int(
                    scen.get("llm_promoted_context_max_units")
                    or _PROMOTED_CONTEXT_MAX_LEXICAL_UNITS_DEFAULT
                ),
                max_chars=int(
                    scen.get("llm_promoted_context_max_chars")
                    or _PROMOTED_CONTEXT_MAX_CHARS_DEFAULT
                ),
                order_mode=str(scen.get("llm_promoted_context_order") or "ranked"),
            )
            llm_user_message = format_synthesis_user_message(
                question=str(scen["question"]),
                hit_context=hit_ctx_llm,
            )
            llm_text = ""
            llm_cost = 0.0
            llm_usage: dict[str, Any] = {}
            if not args.retrieval_only:
                llm_text, llm_cost, llm_usage = synthesize_answer_from_hit_context(
                    question=str(scen["question"]),
                    hit_context=hit_ctx_llm,
                    model=llm_model,
                )
                aggregate_llm_cost_usd += llm_cost
            row = grade_natural_scenario(
                records=records,
                scenario=scen,
                llm_answer=None if args.retrieval_only else llm_text,
                cached_retrieval=bundle,
                breadcrumb_artifact_text=breadcrumb_art_text or "",
                lexicon=shadow_lexicon,
            )
            # Lexical-only context for synthesis + report mirror (route coverage still uses hit objects).
            row["retrieved_context"] = hit_ctx_llm
            # Full deterministic hit-context string (units + normalized route lines) for forensics.
            row["retrieval_hit_context_full"] = hit_ctx_full
            if args.retrieval_only:
                row["llm_skipped"] = True
            else:
                preview_n = int(scen.get("llm_answer_preview_chars", 1200))
                row["llm_answer_preview"] = llm_text[:preview_n]
                # Exact user message sent to the synthesis chat completion (question + promoted context).
                row["llm_user_message"] = llm_user_message
                row["llm_cost_usd"] = llm_cost
                row["llm_usage"] = llm_usage
                row["llm_model"] = llm_model
            if args.semantic_similarity:
                expected_answer = str(scen.get("expected_answer") or "").strip()
                if not expected_answer:
                    row["embedding_similarity_error"] = "scenario_missing_expected_answer"
                else:
                    sim = compare_expected_to_output_with_embeddings(
                        expected_answer=expected_answer,
                        output_answer=llm_text,
                        model=str(args.embedding_model),
                    )
                    aggregate_embedding_cost_usd += float(sim.get("cost_usd") or 0.0)
                    row["expected_answer"] = expected_answer
                    row["embedding_similarity"] = sim
            if shadow_lexicon is not None:
                row["shadow_token_resolution"] = compute_shadow_diff(
                    scenario=scen,
                    lexicon=shadow_lexicon,
                    legacy_route_stopwords=legacy_route_stopwords_snapshot,
                    legacy_equivalences=legacy_module_equivalences,
                )
            else:
                row["shadow_token_resolution"] = {
                    "schema": "dmb_token_resolver_shadow_v1",
                    "error": shadow_build_error or "lexicon_unavailable",
                }
            if route_equivalence_records is not None:
                row["shadow_route_equivalences"] = build_route_equivalence_shadow_payload(
                    scenario_campaign_id=str(scen.get("campaign_id") or default_campaign),
                    records=route_equivalence_records,
                    source_paths=route_equivalence_paths_resolved,
                    workspace_root=_HARNESS_WORKSPACE_ROOT,
                )
            elif args.route_equivalence_jsonl:
                row["shadow_route_equivalences"] = {
                    "schema": ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
                    "error": route_equivalence_load_error or "load_failed",
                }
            results.append(row)
    else:
        for scenario in gold.get("scenarios") or []:
            results.append(grade_scenario(records=records, scenario=scenario))

    tagging_score: dict[str, Any] | None = None
    if args.tagging_sentinel_json is not None:
        if rec_objs is None or corpus_root_resolved is None:
            raise SystemExit("--tagging-sentinel-json requires --breadcrumb-md")
        sentinels_data = read_tagging_sentinels(Path(args.tagging_sentinel_json).resolve())
        baseline_file = Path(args.tagging_baseline_md).resolve()
        baseline_for_score = baseline_file if baseline_file.is_file() else None
        skip_baseline_body = bool(
            repair_report_json
            and repair_report_json.get("apply_report")
            and int(repair_report_json["apply_report"].get("routes_added") or 0) > 0
        )
        tagging_score = score_normalized_records(
            records=rec_objs,
            corpus_root=corpus_root_resolved,
            artifact_path=str(Path(args.breadcrumb_md).resolve()),
            meta=meta,
            normalize_error=None,
            sentinels=sentinels_data,
            baseline_artifact_path=baseline_for_score,
            breadcrumb_full_text=None if skip_baseline_body else breadcrumb_art_text,
        )

    report: dict[str, Any] = {
        "records_source": str(records_path.resolve()),
        "gold": str(args.gold.resolve()),
        "gold_schema": sch,
        "all_ok": all(r["ok"] for r in results),
        "results": results,
        "context_evidence_aggregate": aggregate_context_evidence_metrics(results),
    }
    if breadcrumb_ingest_report is not None:
        report["breadcrumb_ingestion"] = breadcrumb_ingest_report
    if repair_report_json is not None:
        report["repair_adjudication"] = repair_report_json
    if tagging_score is not None:
        report["tagging_score"] = tagging_score
    total_sidecar_cost_usd = (
        float(ingest_cost_usd)
        + float(repair_cost_usd)
        + aggregate_llm_cost_usd
        + aggregate_embedding_cost_usd
    )
    if sch == "dmb_breadcrumb_query_natural_gold_v1":
        report["llm_enabled"] = not args.retrieval_only
        report["llm_model"] = llm_model
        report["aggregate_llm_cost_usd"] = aggregate_llm_cost_usd
        report["retrieval_only"] = bool(args.retrieval_only)
        report["shadow_token_resolution_build"] = {
            "ok": shadow_lexicon is not None,
            "error": shadow_build_error or None,
            "lexicon": shadow_lexicon.to_json_dict() if shadow_lexicon is not None else None,
        }
    if args.semantic_similarity:
        report["embedding_similarity_enabled"] = True
        report["embedding_model"] = str(args.embedding_model)
        report["aggregate_embedding_cost_usd"] = aggregate_embedding_cost_usd
    if repair_cost_usd > 0 and "repair_adjudication" in report:
        report["repair_adjudication_cost_usd"] = float(repair_cost_usd)
    if ingest_cost_usd > 0 and "breadcrumb_ingestion" in report:
        report["breadcrumb_ingestion_cost_usd"] = float(ingest_cost_usd)
    if total_sidecar_cost_usd > 0:
        report["scenario_estimated_cost_usd"] = total_sidecar_cost_usd

    out = args.output or default_out
    out.parent.mkdir(parents=True, exist_ok=True)

    gold_path = Path(args.gold).resolve()
    auto_c1s1 = c1s1_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold)
    forced_c1s1 = bool(args.c1s1_canvas_tsx)
    would_c1s1 = (not args.skip_c1s1_canvas_refresh) and (auto_c1s1 or forced_c1s1)
    if args.skip_c1s1_canvas_refresh and (auto_c1s1 or forced_c1s1):
        report["c1s1_canvas_refresh"] = {
            "enabled": False,
            "reason": "skipped_by_flag",
            "targets": [],
            "updated": [],
            "unchanged": [],
            "errors": [],
        }
    elif would_c1s1:
        c1_paths = list(args.c1s1_canvas_tsx) if args.c1s1_canvas_tsx else [_DEFAULT_C1S1_BENCHMARK_CANVAS]
        report["c1s1_canvas_refresh"] = refresh_c1s1_benchmark_canvases(
            report=report,
            gold=gold,
            report_path=out,
            canvas_paths=c1_paths,
        )

    auto_c1s2 = c1s2_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold)
    forced_c1s2 = bool(args.c1s2_canvas_tsx)
    would_c1s2 = (not args.skip_c1s2_canvas_refresh) and (auto_c1s2 or forced_c1s2)
    if args.skip_c1s2_canvas_refresh and (auto_c1s2 or forced_c1s2):
        report["c1s2_canvas_refresh"] = {
            "enabled": False,
            "reason": "skipped_by_flag",
            "targets": [],
            "updated": [],
            "unchanged": [],
            "errors": [],
        }
    elif would_c1s2:
        c2_paths = list(args.c1s2_canvas_tsx) if args.c1s2_canvas_tsx else [_DEFAULT_C1S2_BENCHMARK_CANVAS]
        report["c1s2_canvas_refresh"] = refresh_c1s2_benchmark_canvases(
            report=report,
            gold=gold,
            report_path=out,
            canvas_paths=c2_paths,
        )

    auto_c1s3 = c1s3_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold)
    forced_c1s3 = bool(args.c1s3_canvas_tsx)
    would_c1s3 = (not args.skip_c1s3_canvas_refresh) and (auto_c1s3 or forced_c1s3)
    if args.skip_c1s3_canvas_refresh and (auto_c1s3 or forced_c1s3):
        report["c1s3_canvas_refresh"] = {
            "enabled": False,
            "reason": "skipped_by_flag",
            "targets": [],
            "updated": [],
            "unchanged": [],
            "errors": [],
        }
    elif would_c1s3:
        c3_paths = list(args.c1s3_canvas_tsx) if args.c1s3_canvas_tsx else [_DEFAULT_C1S3_BENCHMARK_CANVAS]
        report["c1s3_canvas_refresh"] = refresh_c1s3_benchmark_canvases(
            report=report,
            gold=gold,
            report_path=out,
            canvas_paths=c3_paths,
        )

    auto_c1s13 = c1s13_canvas_refresh_auto_enabled(gold_path=gold_path, gold=gold)
    forced_c1s13 = bool(args.c1s13_canvas_tsx)
    would_c1s13 = (not args.skip_c1s13_canvas_refresh) and (auto_c1s13 or forced_c1s13)
    if args.skip_c1s13_canvas_refresh and (auto_c1s13 or forced_c1s13):
        report["c1s13_canvas_refresh"] = {
            "enabled": False,
            "reason": "skipped_by_flag",
            "targets": [],
            "updated": [],
            "unchanged": [],
            "errors": [],
        }
    elif would_c1s13:
        c13_paths = (
            list(args.c1s13_canvas_tsx)
            if args.c1s13_canvas_tsx
            else [_DEFAULT_C1S13_BENCHMARK_CANVAS]
        )
        report["c1s13_canvas_refresh"] = refresh_c1s13_benchmark_canvases(
            report=report,
            gold=gold,
            report_path=out,
            canvas_paths=c13_paths,
        )

    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary: dict[str, Any] = {
        "wrote": str(out),
        "all_ok": report["all_ok"],
        "c1s1_canvas_refresh": report.get("c1s1_canvas_refresh"),
        "c1s2_canvas_refresh": report.get("c1s2_canvas_refresh"),
        "c1s3_canvas_refresh": report.get("c1s3_canvas_refresh"),
        "c1s13_canvas_refresh": report.get("c1s13_canvas_refresh"),
    }
    if args.canvas_tsx is not None:
        summary["semantic_canvas"] = _refresh_canvas(
            canvas_path=args.canvas_tsx,
            report=report,
            gold=gold,
            report_path=out,
            baseline_report_path=args.canvas_baseline_report,
            deterministic_report_path=args.canvas_deterministic_report,
            records_jsonl=records_path,
        )
    print(json.dumps(summary, indent=2))

    c1_errs = (report.get("c1s1_canvas_refresh") or {}).get("errors") or []
    c2_errs = (report.get("c1s2_canvas_refresh") or {}).get("errors") or []
    c3_errs = (report.get("c1s3_canvas_refresh") or {}).get("errors") or []
    if c1_errs or c2_errs or c3_errs:
        sys.exit(1)


def _refresh_canvas(
    *,
    canvas_path: Path,
    report: dict[str, Any],
    gold: dict[str, Any],
    report_path: Path,
    baseline_report_path: Path | None,
    deterministic_report_path: Path | None,
    records_jsonl: Path,
) -> dict[str, Any]:
    """Regenerate the breadcrumb query semantic review canvas block from the report just written."""
    from evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload import (
        _load_records_text,
    )

    baseline = (
        json.loads(baseline_report_path.read_text(encoding="utf-8"))
        if baseline_report_path is not None
        else None
    )
    deterministic = (
        json.loads(deterministic_report_path.read_text(encoding="utf-8"))
        if deterministic_report_path is not None
        else None
    )
    report_for_records = dict(report)
    report_for_records.setdefault("records_source", str(records_jsonl.resolve()))
    records_text = _load_records_text(report_for_records, records_jsonl)
    payload = build_canvas_payload(
        report=report,
        gold=gold,
        baseline=baseline,
        deterministic=deterministic,
        records_text=records_text,
        report_path=str(report_path.resolve()),
        gold_path=str(report.get("gold") or ""),
        baseline_path=(str(baseline_report_path.resolve()) if baseline_report_path else None),
        deterministic_path=(
            str(deterministic_report_path.resolve()) if deterministic_report_path else None
        ),
    )
    block = render_canvas_block(payload)
    ensure_canvas_file_for_patch(canvas_path)
    canvas_text = canvas_path.read_text(encoding="utf-8")
    new_text = update_canvas_text_block(canvas_text, block)
    if new_text != canvas_text:
        canvas_path.write_text(new_text, encoding="utf-8")
        return {"canvas_updated": str(canvas_path)}
    return {"canvas_unchanged": str(canvas_path)}

if __name__ == "__main__":
    main()
