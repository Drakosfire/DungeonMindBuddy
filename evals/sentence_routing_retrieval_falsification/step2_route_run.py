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
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def _build_messages(
    *,
    inp: dict[str, Any],
    manifest: list[dict[str, Any]],
    units_json: list[dict[str, Any]],
) -> list[dict[str, str]]:
    system = (
        "You map recap sentence units to campaign hub slugs for continuity and retrieval.\n"
        "Rules:\n"
        "1. You receive a CLOSED LIST of hub slugs; any slug not listed is forbidden.\n"
        "2. Multi-label is allowed when a unit genuinely implicates multiple hubs.\n"
        "3. Prefer abstain (empty assigned_hubs, needs_new_hub_candidate false) over wrong "
        "attachment when unsure. Wrong hub is worse than unknown.\n"
        "4. needs_new_hub_candidate may only be true when assigned_hubs is empty and the unit "
        "implies a real entity with no fitting hub.\n"
        "5. Do not assign a hub solely because the unit's source path, recap filename, or hub "
        "anchor path mentions it. Route by semantic content in the unit text only.\n"
        "5b. When **every** hub_manifest entry has subject_class \"pc\" (PC-only list): assign a "
        "PC hub only when that PC is an **actor, object, addressee, rescuer, target, listener, or "
        "affected party** in this unit. A passing PC name in a beat centered on an NPC, location, "
        "faction, item, or event does **not** require that PC hub unless the PC has one of those "
        "roles here. If the unit is mainly about entities not represented in the manifest, "
        "abstain: assigned_hubs=[], needs_new_hub_candidate=false. Set needs_new_hub_candidate=true "
        "only when assigned_hubs is empty and the text clearly implies a **real** entity with no "
        "fitting slug in the list—never use a PC hub as a stand-in for an NPC or location.\n"
        "5b-examples (synthetic wording; follow roles, not names): "
        "\"Rook pulled the lever.\" → Rook's PC hub if Rook is a manifest slug. "
        "\"The warden questioned Rook.\" → Rook's hub (object/addressee); abstain for warden if "
        "no warden hub exists in a PC-only list. "
        "\"The party walked to the bridge.\" → every manifest PC if the PCs move **together** as "
        "the party; abstain if **the group** is only vague framing (6c). "
        "\"We brought the team together for the first fight.\" → every manifest PC slug (6c). "
        "\"The scout briefed the captain.\" → captain's PC hub if captain is a manifest slug; "
        "do not assign other PCs who are not implicated.\n"
        "6. Generic recap prose with no entity, location, faction, item, event, or world subject "
        "should abstain: assigned_hubs=[], needs_new_hub_candidate=false.\n"
        "6b. Include a PC hub when that PC has a role from rule 5b in this unit—not merely because "
        "the name appears in passing while another entity drives the beat.\n"
        "6c. Assign every manifest PC slug when the unit uses **the team** / **our team** / "
        "**teammates** in a fight or agreed job, or pairs **first combat** with **team** / "
        "**bring the team together**. Also assign every manifest PC slug when **the group** "
        "clearly denotes the PCs as the **joint subject** of movement or approach in the same "
        "beat (they advance, arrive, or are led **together**). Abstain when **the group** is "
        "only vague recap framing or the sentence center is a location/NPC with no PC in a "
        "role from rule 5b.\n"
        "7. Rationale must cite phrases from the unit text.\n"
        "8. Output only one JSON object matching the schema; no markdown fences.\n"
    )
    user_payload = {
        "campaign_id": inp.get("campaign_id"),
        "session": inp.get("session"),
        "recap_relative_path": inp.get("recap_relative_path"),
        "hub_manifest": manifest,
        "sentence_units": units_json,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, indent=2, ensure_ascii=False)},
    ]


def _routes_response_json_schema(*, allowed_hubs: set[str]) -> dict[str, Any]:
    """Strict Chat Completions JSON schema for ``sentence_hub_routes_v1``."""
    sorted_hubs = sorted(allowed_hubs)
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
) -> tuple[bool, dict[str, Any], float, Path | None]:
    """
    Grade one routing attempt. Returns ``(passed, sidecar, cost_usd, written_path)``.
    When ``no_writes`` is True, ``written_path`` is None.
    """
    from evals.sentence_routing_retrieval_falsification.grader import (
        collect_stage_b_violations,
        normalize_gold_routing_matches,
    )
    from evals.sentence_routing_retrieval_falsification.route_schema import parse_routes_envelope

    inp = dict(raw.get("input") or {})
    cost_usd = 0.0
    routes_body: dict[str, Any] | None = None
    raw_model_output: str | None = None

    if no_llm:
        fixture = raw.get("fixture_routes")
        if not isinstance(fixture, dict):
            raise ValueError("scenario.fixture_routes (object) is required when using --no-llm")
        routes_body = dict(fixture)
    else:
        messages = _build_messages(inp=inp, manifest=manifest_jsonable, units_json=units_json)
        routes_body, cost_usd, raw_model_output = _call_llm_for_routes(
            model=model,
            messages=messages,
            manifest_slugs=manifest_slugs,
        )

    assert routes_body is not None
    violations: list[str] = []
    telemetry: dict[str, Any] = {}
    routes_out: list[dict[str, Any]] = []
    expected_ids = {str(u["unit_id"]) for u in units_json if u.get("unit_id")}

    gold_norm, gold_errors = normalize_gold_routing_matches(gold_routing, units_json)
    violations.extend(gold_errors)

    try:
        envelope = parse_routes_envelope(routes_body)
    except Exception as exc:
        violations.append(f"B0: routes JSON invalid: {exc}")
        passed = False
        raw_routes = routes_body.get("routes") if isinstance(routes_body, dict) else []
        if isinstance(raw_routes, list):
            routes_out = [dict(x) for x in raw_routes if isinstance(x, dict)]
    else:
        routes_out = [r.model_dump() for r in envelope.routes]
        b_viol, telemetry = collect_stage_b_violations(
            envelope.routes,
            gold_norm,
            manifest_slugs=manifest_slugs,
            expected_unit_ids=expected_ids,
        )
        violations.extend(b_viol)
        passed = not violations

    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)
    sidecar: dict[str, object] = {
        "schema": raw.get("schema"),
        "scenario_id": scenario_id,
        "scenario_path": str(scenario_path),
        "corpus_root": str(corpus_root),
        "pass": passed,
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
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        all_pass = all_pass and passed
        vb = sidecar.get("violations", {}) if isinstance(sidecar, dict) else {}
        stage_b = vb.get("stage_b") if isinstance(vb, dict) else []
        n_v = len(stage_b) if isinstance(stage_b, list) else 0
        path_str = str(written) if written is not None else ""
        records.append(
            StageBRunRecord(
                run_index=i,
                gates_passed=passed,
                scenario_estimated_cost_usd=float(cost_usd),
                sidecar_json_path=path_str,
                stage_b_violation_count=n_v,
            )
        )

    if n > 1 and not args.no_writes:
        j_path, m_path = write_stage_b_cohort_summary(
            records,
            model_id=args.model.strip(),
            scenario_id=scenario_id,
            runs_root=_ARTIFACTS,
        )
        print(str(j_path), file=sys.stderr)
        print(str(m_path), file=sys.stderr)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
