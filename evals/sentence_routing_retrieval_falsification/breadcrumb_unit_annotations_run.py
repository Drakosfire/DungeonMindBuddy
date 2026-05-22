#!/usr/bin/env python3
"""Run single-pass recap unit-annotation ingest and compare against manual beat gold.

Writes a default artifact under ``artifacts/runs/<date>/`` unless ``--output`` is set.

Example (Campaign 1 Session 13, with optional manual beat gold compare):

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_run \\
    --corpus-root corpus/eldyrwild-markdown \\
    --ingest-recap-md "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md" \\
    --ingest-frontmatter-seed-md "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 13 - The Meaty and the Dead.frontmatter_seed.md" \\
    --gold-md evals/sentence_routing_retrieval_falsification/manual_labels/Session\\ 13\\ -\\ The\\ Meaty\\ and\\ the\\ Dead.gold.beats.breadcrumbed.md

Example (Campaign 1 Session 1 — no manual beat gold yet; omit ``--gold-md``):

  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_run \\
    --corpus-root corpus/eldyrwild-markdown \\
    --ingest-recap-md "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md" \\
    --ingest-frontmatter-seed-md "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 01 - Stonebridge and Glowkindle Rats.breadcrumbed.md" \\
    --output /tmp/unit_annotations_c1s1.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    BreadcrumbNormalizeError,
    extract_frontmatter_route_allowlist,
    extract_meta_from_frontmatter,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_query_run import (
    _DEFAULT_BREADCRUMB_INGEST_MODEL,
    _relative_to_corpus,
    _resolve_breadcrumb_ingest_model,
    _usage_tokens,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_compile import (
    compile_unit_annotations_artifacts,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_gold import (
    compare_unit_annotations_to_gold,
    load_gold_beat_index,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_measurement import (
    evaluate_second_pass_need,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_prompt import (
    PROMPT_VARIANT_BEAT_POPULATION_V1,
    build_unit_annotations_prompt,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import (
    RecapUnitAnnotationsV1,
    validate_unit_annotations,
)
from evals.sentence_routing_retrieval_falsification.capture import (
    capture_sentence_unit_spans,
)
from src.agent.planner_pricing import usage_cost_usd
from src.agent.synthesis import _load_api_key
from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.llm.api_client import DungeonMindApiClient


def _default_output_path() -> Path:
    today = date.today().isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (
        Path(__file__).resolve().parent
        / "artifacts"
        / "runs"
        / today
        / f"unit_annotations_c1s13--{stamp}.json"
    )


def run_unit_annotations_ingest(
    *,
    recap_md: Path,
    frontmatter_seed_md: Path,
    corpus_root: Path,
    model: str,
    variant: str,
    gold_md: Path | None,
    skip_semantic: bool,
) -> dict[str, Any]:
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
            f"seed={seed_source!r} recap_rel={recap_rel!r}"
        )

    load_dungeonmindbuddy_dotenv()
    if not (_load_api_key() or "").strip():
        raise SystemExit(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py)."
        )

    spans = capture_sentence_unit_spans(recap_text=recap_body, recap_relative_path=recap_rel)
    known_unit_ids = [s.unit_id for s in spans]
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
    prompt = build_unit_annotations_prompt(
        variant=variant,
        source_recap_path=recap_rel,
        campaign_id=str(seed_meta["campaign_id"]),
        session_number=int(seed_meta["session_number"]),
        recap_body=recap_body,
        frontmatter_yaml=seed_frontmatter,
        units=units_payload,
        allowed_routes=allowed_routes,
    )

    from openai import OpenAI

    client = OpenAI()
    api = DungeonMindApiClient.wrap(client)
    api_result = api.responses_parse(
        action="breadcrumb_inline.unit_annotations_v1",
        model=model,
        input=[
            {"role": "system", "content": prompt.system_text},
            {"role": "user", "content": prompt.user_text},
        ],
        text_format=RecapUnitAnnotationsV1,
    )
    response = api_result.response
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise SystemExit("unit annotations ingest: missing output_parsed from responses.parse")
    if not isinstance(parsed, RecapUnitAnnotationsV1):
        parsed = RecapUnitAnnotationsV1.model_validate(parsed)

    usage = _usage_tokens(response)
    cost = usage_cost_usd(
        model_id=model,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
    )

    validation_error: str | None = None
    try:
        validate_unit_annotations(
            parsed,
            expected_source_recap_path=recap_rel,
            expected_campaign_id=str(seed_meta["campaign_id"]),
            expected_session_number=int(seed_meta["session_number"]),
            known_unit_ids=known_unit_ids,
            route_allowlist_normalized=seed_routes,
            run_semantic=not skip_semantic,
        )
    except BreadcrumbNormalizeError as exc:
        validation_error = str(exc)

    artifacts = compile_unit_annotations_artifacts(parsed)
    gold_compare: dict[str, Any] | None = None
    second_pass: dict[str, Any] | None = None
    if gold_md is not None:
        gold_beats = load_gold_beat_index(gold_md)
        gold_compare = compare_unit_annotations_to_gold(parsed, gold_beats)
        second_pass = evaluate_second_pass_need(
            {
                "dimension_pass_rates": gold_compare.get("dimension_pass_rates") or {},
                "failures_by_mode": {},
                "route_tag_regression_vs_baseline": False,
            }
        )

    return {
        "schema": "dmb_unit_annotations_ingest_report_v1",
        "source_recap_path": recap_rel,
        "campaign_id": seed_meta["campaign_id"],
        "session_number": seed_meta["session_number"],
        "model": model,
        "prompt_variant": variant,
        "unit_count": len(known_unit_ids),
        "validation_error": validation_error,
        "telemetry_cost": {
            "scenario_estimated_cost_usd": float(cost.get("total_usd") or 0.0),
            "usage": usage,
        },
        "parsed": parsed.model_dump(by_alias=True),
        "beat_spans": artifacts["beat_spans"],
        "location_beat_rows": artifacts["location_beat_rows"],
        "gold_compare": gold_compare,
        "second_pass": second_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--ingest-recap-md", type=Path, required=True)
    parser.add_argument("--ingest-frontmatter-seed-md", type=Path, required=True)
    parser.add_argument(
        "--gold-md",
        type=Path,
        default=None,
        help=(
            "Optional manual beat-population gold markdown for comparison "
            "(e.g. Session 13 gold). Omit for pilot sessions that do not yet "
            "have a `*.gold.beats.breadcrumbed.md` artifact."
        ),
    )
    parser.add_argument(
        "--ingest-model",
        type=str,
        default=None,
        help=(
            "Model id (else DMB_BREADCRUMB_INGEST_MODEL or "
            f"{_DEFAULT_BREADCRUMB_INGEST_MODEL})."
        ),
    )
    parser.add_argument(
        "--prompt-variant",
        default=PROMPT_VARIANT_BEAT_POPULATION_V1,
        help=f"Prompt variant (default: {PROMPT_VARIANT_BEAT_POPULATION_V1}).",
    )
    parser.add_argument(
        "--skip-semantic",
        action="store_true",
        help="Run shape validation only (skip semantic beat/population gates).",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    model = _resolve_breadcrumb_ingest_model(args.ingest_model)
    report = run_unit_annotations_ingest(
        recap_md=args.ingest_recap_md,
        frontmatter_seed_md=args.ingest_frontmatter_seed_md,
        corpus_root=args.corpus_root,
        model=model,
        variant=str(args.prompt_variant),
        gold_md=args.gold_md,
        skip_semantic=bool(args.skip_semantic),
    )
    out_path = args.output or _default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report.get("validation_error"):
        print(f"validation_error: {report['validation_error']}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
