"""Stage B1 — classify sentence units into ``sentence_discourse_state_v1`` (LLM or fixture).

Writes ``sentence_routing_stage_b1_discourse--<scenario>--<PASS|FAIL>--<UTC>.json`` under
``artifacts/runs/<YYYY-MM-DD>/`` and mirrors ``artifacts/last_sentence_routing_stage_b1_discourse.json``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.discourse_prompt import (
    DISCOURSE_PROMPT_BASE_ID,
    build_discourse_system_prompt,
    build_discourse_user_payload,
)
from evals.sentence_routing_retrieval_falsification.discourse_schema import (
    SCHEMA_SENTENCE_DISCOURSE_STATE_V1,
    DiscourseEnvelope,
    DiscourseRow,
    discourse_openai_json_schema,
    parse_discourse_envelope,
)
from evals.sentence_routing_retrieval_falsification.route_schema import (
    manifest_pc_slug_set,
    normalize_sentence_units_text_for_manifest,
)
from evals.sentence_routing_retrieval_falsification.step2_route_run import (
    build_stage_b_routing_context_dict,
    _load_sentence_units,
    _sentence_units_with_unit_routing_context,
)

_SLICE = Path(__file__).resolve().parent
_REPO_ROOT = _SLICE.parents[1]
_DEFAULT_SCENARIO = _SLICE / "gold" / "scenario_discourse_smoke.json"
_ARTIFACTS = _SLICE / "artifacts" / "runs"

_DEFAULT_MODEL = os.environ.get("DUNGEONMIND_PLANNER_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _date_folder() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _usage_tokens(usage: Any) -> tuple[int, int, int]:
    if usage is None:
        return 0, 0, 0
    inp = int(getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or 0)
    out = int(getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or 0)
    details = getattr(usage, "prompt_tokens_details", None) or getattr(usage, "input_tokens_details", None)
    cached = 0
    if details is not None:
        cached = int(getattr(details, "cached_tokens", None) or 0)
    return inp, out, cached


def _call_llm_discourse(
    *,
    model: str,
    messages: list[dict[str, str]],
    allowed_pc_slugs: list[str],
) -> tuple[dict[str, Any], float, str]:
    from openai import OpenAI

    from src.agent.planner_pricing import usage_cost_usd

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model.strip(),
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sentence_discourse_state_v1",
                "schema": discourse_openai_json_schema(allowed_pc_slugs=allowed_pc_slugs),
                "strict": True,
            },
        },
    )
    choice = resp.choices[0].message.content or "{}"
    body = json.loads(choice)
    inp_t, out_t, cached_t = _usage_tokens(resp.usage)
    pricing = usage_cost_usd(
        model_id=model.strip(),
        input_tokens=inp_t,
        output_tokens=out_t,
        cached_tokens=cached_t,
    )
    cost_usd = float(pricing.get("total_usd") or 0.0)
    return body, cost_usd, choice


def _order_discourse_rows(rows: list[DiscourseRow], units_json: list[dict[str, Any]]) -> list[DiscourseRow]:
    order = {str(u.get("unit_id")): i for i, u in enumerate(units_json) if u.get("unit_id")}
    return sorted(rows, key=lambda r: order.get(r.unit_id, 10**9))


def run_discourse_once(
    *,
    raw: dict[str, Any],
    scenario_path: Path,
    corpus_root: Path,
    units_json: list[dict[str, Any]],
    manifest_jsonable: list[dict[str, Any]],
    manifest_slugs: set[str],
    model: str,
    no_llm: bool,
    no_writes: bool,
    preflight_meta: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], float, Path | None]:
    from evals.sentence_routing_retrieval_falsification.grader import (
        collect_discourse_content_violations,
        discourse_content_unit_failure_events,
    )

    inp = dict(raw.get("input") or {})
    cost_usd = 0.0
    discourse_prompt_id = DISCOURSE_PROMPT_BASE_ID
    body: dict[str, Any] | None = None
    raw_model_output: str | None = None

    units_with_rc = _sentence_units_with_unit_routing_context(inp, list(units_json))
    units_for_llm = normalize_sentence_units_text_for_manifest(units_with_rc, manifest_slugs)
    rc = build_stage_b_routing_context_dict(inp, manifest_jsonable, corpus_root)
    allowed_pc = sorted(manifest_pc_slug_set(manifest_jsonable))

    if no_llm:
        fix = raw.get("fixture_discourse")
        if not isinstance(fix, dict):
            raise ValueError("scenario.fixture_discourse (object) is required when using --no-llm")
        body = dict(fix)
        discourse_prompt_id = DISCOURSE_PROMPT_BASE_ID
    else:
        system, discourse_prompt_id = build_discourse_system_prompt()
        user_obj = build_discourse_user_payload(
            campaign_id=inp.get("campaign_id"),
            session=inp.get("session"),
            recap_relative_path=inp.get("recap_relative_path"),
            hub_manifest=manifest_jsonable,
            sentence_units=units_for_llm,
            routing_context=rc or None,
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_obj, indent=2, ensure_ascii=False)},
        ]
        body, cost_usd, raw_model_output = _call_llm_discourse(
            model=model,
            messages=messages,
            allowed_pc_slugs=allowed_pc,
        )

    assert body is not None
    violations: list[str] = []
    envelope: DiscourseEnvelope | None = None
    try:
        envelope = parse_discourse_envelope(body)
    except Exception as exc:
        violations.append(f"B1-SHAPE: discourse JSON invalid: {exc}")

    telemetry: dict[str, Any] = {
        "stage_b1_unit_breakdown": {
            "sentence_unit_count": len(units_json),
            "discourse_row_count": len(body.get("discourse") or []) if isinstance(body.get("discourse"), list) else 0,
            "discourse_strict_parse_ok": envelope is not None,
        }
    }

    gold_discourse = raw.get("gold_discourse")
    if envelope is not None:
        ordered = _order_discourse_rows(list(envelope.discourse), units_json)
        envelope = DiscourseEnvelope(
            envelope_schema=SCHEMA_SENTENCE_DISCOURSE_STATE_V1,
            discourse=ordered,
        )
        expected_ids = {str(u.get("unit_id")) for u in units_json if u.get("unit_id")}
        got_ids = {r.unit_id for r in envelope.discourse}
        if expected_ids != got_ids:
            violations.append(
                f"B1-SHAPE: discourse unit_id set mismatch missing={sorted(expected_ids - got_ids)} "
                f"extra={sorted(got_ids - expected_ids)}"
            )
        if isinstance(gold_discourse, dict):
            violations.extend(
                collect_discourse_content_violations(envelope.discourse, gold_discourse)
            )

    telemetry["stage_b1_unit_breakdown"]["content_failure_events"] = (
        discourse_content_unit_failure_events(violations)
    )

    passed = not violations
    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)
    sidecar: dict[str, Any] = {
        "schema": raw.get("schema"),
        "pipeline": "stage_b1_discourse",
        "scenario_id": scenario_id,
        "scenario_path": str(scenario_path),
        "corpus_root": str(corpus_root),
        "pass": passed,
        "discourse_prompt_base_id": DISCOURSE_PROMPT_BASE_ID,
        "discourse_prompt_id": discourse_prompt_id,
        "scenario_estimated_cost_usd": round(cost_usd, 6),
        "routing_context": rc,
        "sentence_units": units_json,
        "hub_manifest": manifest_jsonable,
        "discourse_envelope": envelope.model_dump(by_alias=True) if envelope else body,
        "violations": {"stage_b1": violations},
        "telemetry": telemetry,
    }
    if isinstance(preflight_meta, dict) and preflight_meta:
        sidecar["preflight"] = preflight_meta
    if raw_model_output is not None and violations:
        sidecar["raw_model_output"] = raw_model_output

    written: Path | None = None
    if not no_writes:
        day = _date_folder()
        out_dir = _ARTIFACTS / day
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = _utc_stamp()
        tag = "PASS" if passed else "FAIL"
        out_path = out_dir / f"sentence_routing_stage_b1_discourse--{scenario_id}--{tag}--{stamp}.json"
        out_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        last_path = _SLICE / "artifacts" / "last_sentence_routing_stage_b1_discourse.json"
        last_path.parent.mkdir(parents=True, exist_ok=True)
        last_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written = out_path
        print(str(out_path))

    return passed, sidecar, cost_usd, written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage B1 discourse classification — sentence_discourse_state_v1.",
    )
    parser.add_argument("--scenario-json", type=Path, default=_DEFAULT_SCENARIO)
    parser.add_argument("--corpus-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--prior-json", type=Path, default=None)
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--no-writes", action="store_true")
    args = parser.parse_args()

    scenario_path = args.scenario_json.resolve()
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    inp = dict(raw.get("input") or {})
    manifest_raw = list(inp.get("hub_manifest") or [])
    corpus_root = args.corpus_root.resolve()

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
        print(json.dumps({"manifest_violations": mviol}, indent=2), file=sys.stderr)
        return 2

    manifest_objs = [HubManifestEntry.model_validate(x) for x in manifest_raw]
    manifest_jsonable = [m.model_dump(exclude_none=True) for m in manifest_objs]
    manifest_slugs = manifest_slug_set(manifest_objs)

    try:
        units_json = _load_sentence_units(raw, corpus_root, args.prior_json)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    from evals.sentence_routing_retrieval_falsification.stage_b_preflight import (
        preflight_stage_b_gold_and_capture,
    )

    _gold_norm, norm_errors, preflight_meta = preflight_stage_b_gold_and_capture(
        dict(raw.get("gold_routing") or {}),
        units_json,
        expected_capture_signature=raw.get("expected_capture_signature")
        if isinstance(raw.get("expected_capture_signature"), dict)
        else None,
    )
    if norm_errors:
        print(
            json.dumps(
                {"gold_normalize_errors": norm_errors, "preflight": preflight_meta},
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    if not args.no_llm:
        from src.agent.synthesis import _load_api_key
        from src.bootstrap_env import load_dungeonmindbuddy_dotenv

        load_dungeonmindbuddy_dotenv()
        if not (_load_api_key() or "").strip():
            print(
                "OPENAI_API_KEY missing after loading .env (see src/bootstrap_env.py). "
                "Use --no-llm for offline runs.",
                file=sys.stderr,
            )
            return 2

    try:
        passed, _, _, _ = run_discourse_once(
            raw=raw,
            scenario_path=scenario_path,
            corpus_root=corpus_root,
            units_json=units_json,
            manifest_jsonable=manifest_jsonable,
            manifest_slugs=manifest_slugs,
            model=args.model,
            no_llm=args.no_llm,
            no_writes=args.no_writes,
            preflight_meta=preflight_meta,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
