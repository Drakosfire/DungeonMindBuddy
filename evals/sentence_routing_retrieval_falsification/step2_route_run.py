"""``route_sentence_units_to_hubs`` harness (legacy: Stage B) — hub routing (sentence units → manifest hub slugs), LLM or ``--no-llm`` fixture.

Writes ``sentence_routing_stage_b_hub_routes--<scenario>--<PASS|FAIL>--<UTC>.json`` under
``artifacts/runs/<YYYY-MM-DD>/`` and mirrors ``artifacts/last_sentence_routing_stage_b_hub_routes.json``.

Cohort (``--n`` > 1): repeats the run and writes
``sentence_routing_stage_b_cohort_summary--<model>--N<n>--<UTC>.{json,md}``.

Run (repo root)::

    uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --no-llm

    uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \\
        --prior-json evals/sentence_routing_retrieval_falsification/artifacts/last_sentence_routing_stage_a_capture.json

    uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --n 3 --no-llm

When a scenario JSON includes a non-empty top-level ``sentence_units`` array, it overrides
recap capture and ``--prior-json`` (useful for narrow gold slices without editing the recap file).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.routing_prompt import (
    PROMPT_VARIANT_APPENDS,
    ROUTING_PROMPT_BASE_ID,
    build_routing_system_prompt,
)
from evals.sentence_routing_retrieval_falsification.session_roster import (
    resolve_session_pc_roster_slugs,
)
from evals.sentence_routing_retrieval_falsification.route_schema import (
    ROUTING_DIAGNOSTIC_ENUM,
    THE_PARTY_ROUTE_SENTINEL,
    expand_the_party_sentinel,
)

_SLICE = Path(__file__).resolve().parent
_REPO_ROOT = _SLICE.parents[1]
_DEFAULT_SCENARIO = _SLICE / "gold" / "scenario_mini.json"
_ARTIFACTS = _SLICE / "artifacts" / "runs"

_DEFAULT_MODEL = os.environ.get("DUNGEONMIND_PLANNER_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"


def _utc_stamp() -> str:
    """UTC timestamp for filenames (microsecond resolution avoids cohort collisions)."""
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


def _pc_party_names_from_input(inp: dict[str, Any]) -> list[str]:
    """Optional ``input.pc_party_names`` — in-world adventuring-band labels for this run (not gold)."""
    raw = inp.get("pc_party_names")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _dedupe_party_names(names: list[str]) -> list[str]:
    """Stable de-dupe (case-insensitive keys), first occurrence wins."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in names:
        s = str(raw).strip()
        if not s:
            continue
        key = s.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _party_registry_json_path(*, corpus_root: Path, recap_relative_path: str) -> Path | None:
    """``<campaign>/Session Recaps/<recap>.md`` → ``<campaign>/_party_registry.json`` if that file exists."""
    rel = (recap_relative_path or "").strip()
    if not rel:
        return None
    try:
        recap = (corpus_root / rel).resolve()
        recap.relative_to(corpus_root.resolve())
    except ValueError:
        return None
    if recap.parent.name != "Session Recaps":
        return None
    candidate = recap.parent.parent / "_party_registry.json"
    return candidate if candidate.is_file() else None


def _pc_party_names_from_party_registry_file(
    *,
    corpus_root: Path,
    recap_relative_path: str,
    campaign_id: str | None,
) -> list[str]:
    """
    Load ``pc_party_names`` from the campaign-level ``_party_registry.json`` next to ``Session Recaps/``.

    When ``campaign_id`` is non-empty, it must match the registry's ``campaign_id`` (if present) or the
    registry is ignored (wrong-campaign safety).
    """
    path = _party_registry_json_path(corpus_root=corpus_root, recap_relative_path=recap_relative_path)
    if path is None:
        return []
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(blob, dict):
        return []
    reg_schema = str(blob.get("schema") or "").strip()
    if reg_schema and reg_schema != "party_registry_v1":
        return []
    reg_cid = blob.get("campaign_id")
    if campaign_id and reg_cid is not None and str(reg_cid).strip() != str(campaign_id).strip():
        return []
    raw = blob.get("pc_party_names")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _merged_pc_party_names(inp: dict[str, Any], corpus_root: Path | None) -> list[str]:
    """Registry (campaign folder) first, then optional ``input.pc_party_names`` overrides/extras."""
    merged: list[str] = []
    if corpus_root is not None:
        rel = str(inp.get("recap_relative_path") or "").strip()
        cid_raw = inp.get("campaign_id")
        cid = str(cid_raw).strip() if cid_raw is not None else ""
        merged.extend(
            _pc_party_names_from_party_registry_file(
                corpus_root=corpus_root,
                recap_relative_path=rel,
                campaign_id=cid or None,
            )
        )
    merged.extend(_pc_party_names_from_input(inp))
    return _dedupe_party_names(merged)


def _pc_roster_slugs_from_manifest(manifest: list[dict[str, Any]]) -> list[str]:
    """Manifest-order PC roster slugs when the routing surface is PC-only."""
    if not manifest:
        return []
    out: list[str] = []
    for entry in manifest:
        if str(entry.get("subject_class") or "").strip() != "pc":
            return []
        slug = str(entry.get("slug") or "").strip()
        if slug:
            out.append(slug)
    return out


def _string_list_from_context(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for x in value:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _sentence_units_with_unit_routing_context(
    inp: dict[str, Any],
    units_json: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge optional ``input.unit_routing_context`` keyed by ``unit_id`` onto each sentence_unit."""
    raw = inp.get("unit_routing_context")
    if not isinstance(raw, dict) or not raw:
        return units_json
    out: list[dict[str, Any]] = []
    for unit in units_json:
        if not isinstance(unit, dict):
            continue
        uid = str(unit.get("unit_id") or "").strip()
        patch = raw.get(uid) if uid else None
        if isinstance(patch, dict) and patch:
            merged = dict(unit)
            base_rc = merged.get("routing_context")
            if isinstance(base_rc, dict):
                merged["routing_context"] = {**base_rc, **patch}
            else:
                merged["routing_context"] = dict(patch)
            out.append(merged)
        else:
            out.append(unit)
    return out


def build_stage_b_routing_context_dict(
    inp: dict[str, Any],
    manifest: list[dict[str, Any]],
    corpus_root: Path | None,
) -> dict[str, Any]:
    """Shared top-level ``routing_context`` for Stage B user payloads (hub routing + discourse B1)."""
    party_names = _merged_pc_party_names(inp, corpus_root)
    pc_roster_slugs = _pc_roster_slugs_from_manifest(manifest)
    session_pc_roster_slugs: list[str] = []
    if corpus_root is not None and pc_roster_slugs:
        session_pc_roster_slugs = resolve_session_pc_roster_slugs(
            inp=inp, corpus_root=corpus_root, manifest_jsonable=manifest
        )
    routing_context: dict[str, Any] = {}
    raw_routing_context = inp.get("routing_context")
    if isinstance(raw_routing_context, dict):
        active_scene_owner_hubs = _string_list_from_context(
            raw_routing_context.get("active_scene_owner_hubs")
        )
        if active_scene_owner_hubs:
            routing_context["active_scene_owner_hubs"] = active_scene_owner_hubs
        active_collective_actor = str(
            raw_routing_context.get("active_collective_actor") or ""
        ).strip()
        if active_collective_actor:
            routing_context["active_collective_actor"] = active_collective_actor
        previous_unit_assignments = raw_routing_context.get("previous_unit_assignments")
        if isinstance(previous_unit_assignments, dict) and previous_unit_assignments:
            routing_context["previous_unit_assignments"] = previous_unit_assignments
    for key in ("active_scene_owner_hubs", "active_collective_actor", "previous_unit_assignments"):
        if key in inp and key not in routing_context:
            if key == "active_scene_owner_hubs":
                active_scene_owner_hubs = _string_list_from_context(inp.get(key))
                if active_scene_owner_hubs:
                    routing_context[key] = active_scene_owner_hubs
            elif key == "active_collective_actor":
                active_collective_actor = str(inp.get(key) or "").strip()
                if active_collective_actor:
                    routing_context[key] = active_collective_actor
            elif isinstance(inp.get(key), dict) and inp.get(key):
                routing_context[key] = inp[key]
    if party_names:
        routing_context["pc_party_names"] = party_names
    if pc_roster_slugs:
        routing_context["pc_roster_slugs"] = pc_roster_slugs
    if session_pc_roster_slugs:
        routing_context["session_pc_roster_slugs"] = session_pc_roster_slugs
    return routing_context


def _build_messages(
    *,
    inp: dict[str, Any],
    manifest: list[dict[str, Any]],
    units_json: list[dict[str, Any]],
    corpus_root: Path | None = None,
    prompt_variant: str | None = None,
) -> tuple[list[dict[str, str]], str]:
    """Returns ``(messages, routing_prompt_id)`` — full prompt digest includes variant append."""
    system, routing_prompt_id = build_routing_system_prompt(prompt_variant)
    sentence_units_payload = _sentence_units_with_unit_routing_context(inp, units_json)
    user_payload: dict[str, Any] = {
        "campaign_id": inp.get("campaign_id"),
        "session": inp.get("session"),
        "recap_relative_path": inp.get("recap_relative_path"),
        "hub_manifest": manifest,
        "sentence_units": sentence_units_payload,
    }
    routing_context = build_stage_b_routing_context_dict(inp, manifest, corpus_root)
    if routing_context:
        user_payload["routing_context"] = routing_context
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, indent=2, ensure_ascii=False)},
    ], routing_prompt_id


def _routes_response_json_schema(*, allowed_hubs: set[str]) -> dict[str, Any]:
    """Strict Chat Completions JSON schema for ``sentence_hub_routes_v1``."""
    sorted_hubs = sorted(allowed_hubs | {THE_PARTY_ROUTE_SENTINEL})
    diag_any_of: list[dict[str, Any]] = [{"type": "null"}]
    diag_any_of.append({"type": "string", "enum": list(ROUTING_DIAGNOSTIC_ENUM)})
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema", "routes"],
        "properties": {
            "schema": {"type": "string", "enum": ["sentence_hub_routes_v1"]},
            "routes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "unit_id",
                        "assigned_hubs",
                        "confidence",
                        "rationale",
                        "needs_new_hub_candidate",
                        "routing_diagnostic_bucket",
                    ],
                    "properties": {
                        "unit_id": {"type": "string"},
                        "assigned_hubs": {
                            "type": "array",
                            "items": {"type": "string", "enum": sorted_hubs},
                        },
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        "rationale": {"type": "string"},
                        "needs_new_hub_candidate": {"type": "boolean"},
                        "routing_diagnostic_bucket": {"anyOf": diag_any_of},
                    },
                },
            },
        },
    }


def _load_sentence_units(
    scenario: dict[str, Any],
    corpus_root: Path,
    prior_path: Path | None,
) -> list[dict[str, Any]]:
    embedded = scenario.get("sentence_units")
    if isinstance(embedded, list) and embedded:
        return [dict(x) for x in embedded if isinstance(x, dict)]
    if prior_path is not None:
        side = json.loads(Path(prior_path).read_text(encoding="utf-8"))
        raw = side.get("sentence_units")
        if isinstance(raw, list) and raw:
            return [dict(x) for x in raw if isinstance(x, dict)]
    inp = scenario.get("input") or {}
    rel = str(inp.get("recap_relative_path") or "").strip()
    if not rel:
        raise ValueError("scenario input.recap_relative_path is required when no prior-json units")
    from evals.sentence_routing_retrieval_falsification.capture import (
        capture_sentence_units_from_file,
        units_to_jsonable,
    )

    units = capture_sentence_units_from_file(corpus_root=corpus_root, recap_relative_path=rel)
    return units_to_jsonable(units)


def _call_llm_for_routes(
    *,
    model: str,
    messages: list[dict[str, str]],
    manifest_slugs: set[str],
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
                "name": "sentence_hub_routes_v1",
                "schema": _routes_response_json_schema(allowed_hubs=manifest_slugs),
                "strict": True,
            },
        },
    )
    choice = resp.choices[0].message.content or "{}"
    routes_body = json.loads(choice)
    inp_t, out_t, cached_t = _usage_tokens(resp.usage)
    pricing = usage_cost_usd(
        model_id=model.strip(),
        input_tokens=inp_t,
        output_tokens=out_t,
        cached_tokens=cached_t,
    )
    cost_usd = float(pricing.get("total_usd") or 0.0)
    return routes_body, cost_usd, choice


def grade_sentence_hub_routes_payload(
    *,
    routes_body: dict[str, Any],
    raw: dict[str, Any],
    scenario_path: Path,
    corpus_root: Path,
    units_json: list[dict[str, Any]],
    manifest_jsonable: list[dict[str, Any]],
    manifest_slugs: set[str],
    gold_routing: dict[str, Any],
    routing_prompt_id: str,
) -> tuple[bool, list[str], dict[str, Any], list[dict[str, Any]]]:
    """
    Shared Stage B2 grading: parse ``sentence_hub_routes_v1``, expand ``the_party``, run B1/B2 gates.

    Returns ``(passed, violations, telemetry, routes_out)``.
    """
    from evals.sentence_routing_retrieval_falsification.grader import (
        collect_stage_b_violations,
        normalize_gold_routing_matches,
        stage_b_violation_only_telemetry,
    )
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        coerce_wire_routes_payload_for_grading,
        normalize_route_rows_for_manifest,
        parse_routes_envelope,
    )

    inp = dict(raw.get("input") or {})
    session_pc = resolve_session_pc_roster_slugs(
        inp=inp, corpus_root=corpus_root, manifest_jsonable=manifest_jsonable
    )
    manifest_pc_fallback = _pc_roster_slugs_from_manifest(manifest_jsonable)
    party_expansion_for_grade = session_pc if session_pc else manifest_pc_fallback

    violations: list[str] = []
    telemetry: dict[str, Any] = {}
    routes_out: list[dict[str, Any]] = []
    expected_ids = {str(u["unit_id"]) for u in units_json if u.get("unit_id")}

    gold_norm, gold_errors = normalize_gold_routing_matches(gold_routing, units_json)
    violations.extend(gold_errors)

    envelope = None
    strict_parse_failed = False
    graded_after_wire_coercion = False
    try:
        envelope = parse_routes_envelope(routes_body, manifest_jsonable=manifest_jsonable)
    except Exception as exc:
        strict_parse_failed = True
        violations.append(f"B0: routes JSON invalid: {exc}")
        try:
            coerced = coerce_wire_routes_payload_for_grading(
                dict(routes_body), manifest_jsonable=manifest_jsonable
            )
            envelope = parse_routes_envelope(coerced, manifest_jsonable=manifest_jsonable)
            graded_after_wire_coercion = True
        except Exception:
            envelope = None

    if envelope is not None:
        has_party = any(
            THE_PARTY_ROUTE_SENTINEL in (r.assigned_hubs or []) for r in envelope.routes
        )
        if has_party:
            exp_target = session_pc if session_pc else manifest_pc_fallback
            if not exp_target:
                violations.append(
                    "B0: the_party assigned but session_pc_roster_slugs could not be resolved "
                    "(no PC entries in hub_manifest)"
                )
            else:
                envelope.routes = expand_the_party_sentinel(envelope.routes, exp_target)
        envelope.routes = normalize_route_rows_for_manifest(envelope.routes, manifest_slugs)
        routes_out = [r.model_dump() for r in envelope.routes]
        b_viol, telemetry = collect_stage_b_violations(
            envelope.routes,
            gold_norm,
            manifest_slugs=manifest_slugs,
            expected_unit_ids=expected_ids,
            party_expansion_slugs=party_expansion_for_grade,
        )
        violations.extend(b_viol)
        sb = telemetry.setdefault("stage_b_unit_breakdown", {})
        sb["routing_prompt_id"] = routing_prompt_id
        sb["wire_strict_parse_ok"] = not strict_parse_failed
        if strict_parse_failed:
            sb["graded_after_wire_coercion"] = graded_after_wire_coercion
        passed = not violations
    else:
        telemetry = stage_b_violation_only_telemetry(
            violations,
            expected_unit_ids=expected_ids,
            gold_routing=gold_norm,
            party_expansion_slugs=party_expansion_for_grade,
        )
        passed = False
        raw_routes = routes_body.get("routes") if isinstance(routes_body, dict) else []
        if isinstance(raw_routes, list):
            routes_out = [dict(x) for x in raw_routes if isinstance(x, dict)]

    return passed, violations, telemetry, routes_out


def run_stage_b_once(
    *,
    raw: dict[str, Any],
    scenario_path: Path,
    corpus_root: Path,
    units_json: list[dict[str, Any]],
    manifest_jsonable: list[dict[str, Any]],
    manifest_slugs: set[str],
    gold_routing: dict[str, Any],
    model: str,
    no_llm: bool,
    no_writes: bool,
    prompt_variant: str | None = None,
) -> tuple[bool, dict[str, Any], float, Path | None]:
    """
    Grade one routing attempt. Returns ``(passed, sidecar, cost_usd, written_path)``.
    When ``no_writes`` is True, ``written_path`` is None.
    """
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        normalize_sentence_units_text_for_manifest,
    )

    inp = dict(raw.get("input") or {})
    cost_usd = 0.0
    routes_body: dict[str, Any] | None = None
    raw_model_output: str | None = None
    _, routing_prompt_id = build_routing_system_prompt(prompt_variant)

    if no_llm:
        fixture = raw.get("fixture_routes")
        if not isinstance(fixture, dict):
            raise ValueError("scenario.fixture_routes (object) is required when using --no-llm")
        routes_body = dict(fixture)
    else:
        units_for_llm = normalize_sentence_units_text_for_manifest(
            units_json, manifest_slugs
        )
        messages, routing_prompt_id = _build_messages(
            inp=inp,
            manifest=manifest_jsonable,
            units_json=units_for_llm,
            corpus_root=corpus_root,
            prompt_variant=prompt_variant,
        )
        routes_body, cost_usd, raw_model_output = _call_llm_for_routes(
            model=model,
            messages=messages,
            manifest_slugs=manifest_slugs,
        )

    assert routes_body is not None
    passed, violations, telemetry, routes_out = grade_sentence_hub_routes_payload(
        routes_body=routes_body,
        raw=raw,
        scenario_path=scenario_path,
        corpus_root=corpus_root,
        units_json=units_json,
        manifest_jsonable=manifest_jsonable,
        manifest_slugs=manifest_slugs,
        gold_routing=gold_routing,
        routing_prompt_id=routing_prompt_id,
    )

    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)
    sidecar: dict[str, object] = {
        "schema": raw.get("schema"),
        "scenario_id": scenario_id,
        "scenario_path": str(scenario_path),
        "corpus_root": str(corpus_root),
        "pass": passed,
        "prompt_variant": None
        if prompt_variant is None
        else (str(prompt_variant).strip() or None),
        "routing_prompt_base_id": ROUTING_PROMPT_BASE_ID,
        "routing_prompt_id": routing_prompt_id,
        "scenario_estimated_cost_usd": round(cost_usd, 6),
        "violations": {"stage_b": violations},
        "telemetry": telemetry,
        "sentence_units": units_json,
        "hub_manifest": manifest_jsonable,
        "routes": routes_out,
    }
    if raw_model_output is not None and violations:
        sidecar["raw_model_output"] = raw_model_output

    written: Path | None = None
    if not no_writes:
        day = _date_folder()
        out_dir = _ARTIFACTS / day
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = _utc_stamp()
        tag = "PASS" if passed else "FAIL"
        out_path = out_dir / f"sentence_routing_stage_b_hub_routes--{scenario_id}--{tag}--{stamp}.json"
        out_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        last_path = _SLICE / "artifacts" / "last_sentence_routing_stage_b_hub_routes.json"
        last_path.parent.mkdir(parents=True, exist_ok=True)
        last_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written = out_path
        print(str(out_path))

    return passed, sidecar, cost_usd, written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="route_sentence_units_to_hubs (legacy: Stage B) — map sentence units to hub slugs (sentence routing falsification harness).",
    )
    parser.add_argument("--scenario-json", type=Path, default=_DEFAULT_SCENARIO)
    parser.add_argument("--corpus-root", type=Path, default=_REPO_ROOT)
    parser.add_argument(
        "--prior-json",
        type=Path,
        default=None,
        help="capture_sentence_units sidecar JSON (legacy: Stage A capture; sentence_units); e.g. last_sentence_routing_stage_a_capture.json",
    )
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL)
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="Cohort size: repeat hub-routing run N times (default 1). When N>1, writes cohort summary JSON+MD.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use scenario fixture_routes JSON only (CI / grader smoke).",
    )
    parser.add_argument("--no-writes", action="store_true")
    parser.add_argument(
        "--prompt-variant",
        type=str,
        default="",
        metavar="NAME",
        help=(
            "Append experimental system text for A/B prompt tests. "
            f"Known: {', '.join(sorted(PROMPT_VARIANT_APPENDS))}."
        ),
    )
    args = parser.parse_args()

    n = max(1, int(args.n))
    scenario_path = args.scenario_json.resolve()
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    inp = dict(raw.get("input") or {})
    manifest_raw = list(inp.get("hub_manifest") or [])
    gold_routing = dict(raw.get("gold_routing") or {})
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

    if not args.no_llm and n >= 1:
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

    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)
    from evals.sentence_routing_retrieval_falsification.sentence_routing_stage_b_cohort_report import (
        StageBRunRecord,
        write_stage_b_cohort_summary,
    )

    records: list[StageBRunRecord] = []
    all_pass = True
    prompt_variant_arg = str(args.prompt_variant or "").strip() or None

    for i in range(n):
        try:
            passed, sidecar, cost_usd, written = run_stage_b_once(
                raw=raw,
                scenario_path=scenario_path,
                corpus_root=corpus_root,
                units_json=units_json,
                manifest_jsonable=manifest_jsonable,
                manifest_slugs=manifest_slugs,
                gold_routing=gold_routing,
                model=args.model,
                no_llm=args.no_llm,
                no_writes=args.no_writes,
                prompt_variant=prompt_variant_arg,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        all_pass = all_pass and passed
        vb = sidecar.get("violations", {}) if isinstance(sidecar, dict) else {}
        stage_b = vb.get("stage_b") if isinstance(vb, dict) else []
        n_v = len(stage_b) if isinstance(stage_b, list) else 0
        path_str = str(written) if written is not None else ""
        telem = sidecar.get("telemetry") if isinstance(sidecar, dict) else None
        unit_bd = None
        if isinstance(telem, dict):
            raw_bd = telem.get("stage_b_unit_breakdown")
            unit_bd = raw_bd if isinstance(raw_bd, dict) else None
        records.append(
            StageBRunRecord(
                run_index=i,
                gates_passed=passed,
                scenario_estimated_cost_usd=float(cost_usd),
                sidecar_json_path=path_str,
                stage_b_violation_count=n_v,
                routing_prompt_base_id=(
                    str(sidecar.get("routing_prompt_base_id") or "").strip() or None
                ),
                routing_prompt_id=str(sidecar.get("routing_prompt_id") or "").strip()
                or None,
                stage_b_unit_breakdown=unit_bd,
            )
        )

    if n > 1 and not args.no_writes:
        j_path, m_path = write_stage_b_cohort_summary(
            records,
            model_id=args.model.strip(),
            scenario_id=scenario_id,
            runs_root=_ARTIFACTS,
            prompt_variant=prompt_variant_arg,
        )
        print(str(j_path), file=sys.stderr)
        print(str(m_path), file=sys.stderr)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
