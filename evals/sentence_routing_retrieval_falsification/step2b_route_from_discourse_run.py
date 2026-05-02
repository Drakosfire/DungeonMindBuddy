"""Stage B2 — deterministic routes from ``sentence_discourse_state_v1`` (discourse reducer + Stage B gates).

Reads a Stage B1 sidecar (``--discourse-json``) or ``scenario.fixture_discourse``, runs
:func:`discourse_reducer.routes_from_discourse_rows`, then reuses
:func:`step2_route_run.grade_sentence_hub_routes_payload`.

Writes ``sentence_routing_stage_b2_from_discourse--<scenario>--<PASS|FAIL>--<UTC>.json`` under
``artifacts/runs/<YYYY-MM-DD>/`` and mirrors ``artifacts/last_sentence_routing_stage_b2_from_discourse.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.discourse_reducer import routes_from_discourse_rows
from evals.sentence_routing_retrieval_falsification.stage_b2_coherence import (
    normalize_discourse_rows_for_b2_coherence,
)
from evals.sentence_routing_retrieval_falsification.discourse_schema import DiscourseRow
from evals.sentence_routing_retrieval_falsification.discourse_schema import parse_discourse_envelope
from evals.sentence_routing_retrieval_falsification.discourse_prompt import DISCOURSE_PROMPT_BASE_ID
from evals.sentence_routing_retrieval_falsification.step2_route_run import (
    ROUTING_PROMPT_BASE_ID,
    build_stage_b_routing_context_dict,
    grade_sentence_hub_routes_payload,
    _load_sentence_units,
)

_SLICE = Path(__file__).resolve().parent
_REPO_ROOT = _SLICE.parents[1]
_DEFAULT_SCENARIO = _SLICE / "gold" / "scenario_discourse_smoke.json"
_ARTIFACTS = _SLICE / "artifacts" / "runs"


def _utc_stamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _date_folder() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for x in value:
        s = str(x).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _load_discourse_sidecar(
    *,
    raw: dict[str, Any],
    discourse_path: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if discourse_path is not None:
        side = json.loads(Path(discourse_path).read_text(encoding="utf-8"))
        env = side.get("discourse_envelope")
        if isinstance(env, dict):
            rc = side.get("routing_context")
            return dict(env), dict(rc) if isinstance(rc, dict) else {}
        raise ValueError("discourse sidecar missing discourse_envelope object")
    fix = raw.get("fixture_discourse")
    if not isinstance(fix, dict):
        raise ValueError("Provide --discourse-json or scenario.fixture_discourse (object)")
    return dict(fix), {}


def _route_expected_hubs_from_state(
    row: DiscourseRow,
    *,
    manifest_pc_slugs: set[str],
    session_pc_roster_slugs: list[str],
) -> list[str]:
    hubs: list[str] = []
    seen: set[str] = set()
    for slug in (
        list(row.direct_pc_slugs)
        + list(row.topic_pc_slugs)
        + list(row.scene_owner_pc_slugs)
        + list(row.perceiver_pc_slugs)
    ):
        if slug in manifest_pc_slugs and slug not in seen:
            seen.add(slug)
            hubs.append(slug)
    if (
        row.collective_actor == "the_party"
        and row.party_expansion_allowed
        and session_pc_roster_slugs
        and not row.narrow_pc_only
        and row.discourse_mode in ("explicit_party", "implicit_party")
    ):
        hubs = list(session_pc_roster_slugs)
    return hubs


def _gold_expected_hubs(gold_row: dict[str, Any], *, session_pc_roster_slugs: list[str]) -> list[str]:
    raw = [str(x).strip() for x in gold_row.get("expected_hubs") or [] if str(x).strip()]
    if raw == ["the_party"] and session_pc_roster_slugs:
        return list(session_pc_roster_slugs)
    return raw


def build_b2_delta_telemetry(
    *,
    discourse_rows: list[DiscourseRow],
    routes_out: list[dict[str, Any]],
    manifest_pc_slugs: set[str],
    session_pc_roster_slugs: list[str],
    gold_routing: dict[str, Any],
) -> dict[str, Any]:
    """Compare B1-derived route expectations with final B2 routes and gold failures."""
    expected_by_id = {
        r.unit_id: _route_expected_hubs_from_state(
            r,
            manifest_pc_slugs=manifest_pc_slugs,
            session_pc_roster_slugs=session_pc_roster_slugs,
        )
        for r in discourse_rows
    }
    actual_by_id = {
        str(r.get("unit_id") or ""): [
            str(h).strip() for h in r.get("assigned_hubs") or [] if str(h).strip()
        ]
        for r in routes_out
        if isinstance(r, dict)
    }
    route_mismatches: list[dict[str, Any]] = []
    for uid, expected in sorted(expected_by_id.items()):
        actual = actual_by_id.get(uid, [])
        if sorted(expected) != sorted(actual):
            route_mismatches.append(
                {"unit_id": uid, "b1_expected_hubs": expected, "b2_assigned_hubs": actual}
            )

    gold_attribution: list[dict[str, Any]] = []
    counts = {
        "b1_state_missing_expected_hub": 0,
        "b2_reducer_missing_expected_hub": 0,
        "b1_state_over_routed": 0,
        "b2_reducer_over_routed": 0,
    }
    for g in gold_routing.get("must_route") or []:
        if not isinstance(g, dict):
            continue
        uid = str(g.get("unit_id") or "").strip()
        if not uid:
            continue
        expected_gold = _gold_expected_hubs(g, session_pc_roster_slugs=session_pc_roster_slugs)
        actual = actual_by_id.get(uid, [])
        missing = sorted(set(expected_gold) - set(actual))
        if not missing:
            continue
        b1_expected = set(expected_by_id.get(uid, []))
        missing_from_state = sorted(set(missing) - b1_expected)
        missing_from_reducer = sorted(set(missing) & b1_expected)
        if missing_from_state:
            counts["b1_state_missing_expected_hub"] += 1
        if missing_from_reducer:
            counts["b2_reducer_missing_expected_hub"] += 1
        gold_attribution.append(
            {
                "gate": "must_route",
                "unit_id": uid,
                "missing_hubs": missing,
                "missing_from_b1_state": missing_from_state,
                "missing_from_b2_reducer": missing_from_reducer,
            }
        )
    for g in gold_routing.get("must_abstain") or []:
        if not isinstance(g, dict):
            continue
        uid = str(g.get("unit_id") or "").strip()
        if not uid:
            continue
        max_assigned = int(g.get("max_assigned_hubs", 0))
        actual = actual_by_id.get(uid, [])
        if len(actual) <= max_assigned:
            continue
        b1_expected = expected_by_id.get(uid, [])
        if b1_expected:
            counts["b1_state_over_routed"] += 1
            source = "b1_state"
        else:
            counts["b2_reducer_over_routed"] += 1
            source = "b2_reducer"
        gold_attribution.append(
            {
                "gate": "must_abstain",
                "unit_id": uid,
                "assigned_hubs": actual,
                "max_assigned_hubs": max_assigned,
                "attributed_to": source,
            }
        )

    return {
        "route_mismatch_count": len(route_mismatches),
        "route_mismatches": route_mismatches,
        "gold_failure_attribution_counts": counts,
        "gold_failure_attribution": gold_attribution,
    }


def run_route_from_discourse_once(
    *,
    raw: dict[str, Any],
    scenario_path: Path,
    corpus_root: Path,
    units_json: list[dict[str, Any]],
    manifest_jsonable: list[dict[str, Any]],
    manifest_slugs: set[str],
    gold_routing: dict[str, Any],
    discourse_path: Path | None,
    no_writes: bool,
    preflight_meta: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any], Path | None]:
    discourse_dict, sidecar_routing_context = _load_discourse_sidecar(
        raw=raw,
        discourse_path=discourse_path,
    )
    envelope = parse_discourse_envelope(discourse_dict)
    routing_context = build_stage_b_routing_context_dict(
        dict(raw.get("input") or {}),
        manifest_jsonable,
        corpus_root,
    )
    if sidecar_routing_context:
        routing_context = {**routing_context, **sidecar_routing_context}
    session_pc_roster_slugs = _string_list(routing_context.get("session_pc_roster_slugs"))
    discourse_rows, b2_coherence_corrections = normalize_discourse_rows_for_b2_coherence(
        list(envelope.discourse),
        session_pc_roster_slugs=session_pc_roster_slugs,
    )
    routes_body = routes_from_discourse_rows(
        discourse_rows,
        manifest_jsonable=manifest_jsonable,
        session_pc_roster_slugs=session_pc_roster_slugs,
    )

    passed, violations, telemetry, routes_out = grade_sentence_hub_routes_payload(
        routes_body=routes_body,
        raw=raw,
        scenario_path=scenario_path,
        corpus_root=corpus_root,
        units_json=units_json,
        manifest_jsonable=manifest_jsonable,
        manifest_slugs=manifest_slugs,
        gold_routing=gold_routing,
        routing_prompt_id=ROUTING_PROMPT_BASE_ID,
    )
    from evals.sentence_routing_retrieval_falsification.grader import normalize_gold_routing_matches

    gold_norm, _ = normalize_gold_routing_matches(gold_routing, units_json)
    sb = telemetry.setdefault("stage_b_unit_breakdown", {})
    sb["pipeline"] = "stage_b2_from_discourse"
    sb["discourse_prompt_base_id"] = DISCOURSE_PROMPT_BASE_ID
    sb["b2_coherence_corrections"] = b2_coherence_corrections
    sb["b2_delta"] = build_b2_delta_telemetry(
        discourse_rows=discourse_rows,
        routes_out=routes_out,
        manifest_pc_slugs={str(e.get("slug") or "").strip() for e in manifest_jsonable if str(e.get("subject_class") or "").strip() == "pc"},
        session_pc_roster_slugs=session_pc_roster_slugs,
        gold_routing=gold_norm,
    )

    scenario_id = str(raw.get("scenario_id") or scenario_path.stem)
    sidecar: dict[str, Any] = {
        "schema": raw.get("schema"),
        "pipeline": "stage_b2_from_discourse",
        "scenario_id": scenario_id,
        "scenario_path": str(scenario_path),
        "corpus_root": str(corpus_root),
        "pass": passed,
        "routing_prompt_base_id": ROUTING_PROMPT_BASE_ID,
        "routing_prompt_id": ROUTING_PROMPT_BASE_ID,
        "discourse_prompt_base_id": DISCOURSE_PROMPT_BASE_ID,
        "scenario_estimated_cost_usd": 0.0,
        "violations": {"stage_b": violations},
        "telemetry": telemetry,
        "routing_context": routing_context,
        "sentence_units": units_json,
        "hub_manifest": manifest_jsonable,
        "discourse_envelope": discourse_dict,
        "routes": routes_out,
    }
    if isinstance(preflight_meta, dict) and preflight_meta:
        sidecar["preflight"] = preflight_meta

    written: Path | None = None
    if not no_writes:
        day = _date_folder()
        out_dir = _ARTIFACTS / day
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = _utc_stamp()
        tag = "PASS" if passed else "FAIL"
        out_path = out_dir / f"sentence_routing_stage_b2_from_discourse--{scenario_id}--{tag}--{stamp}.json"
        out_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        last_path = _SLICE / "artifacts" / "last_sentence_routing_stage_b2_from_discourse.json"
        last_path.parent.mkdir(parents=True, exist_ok=True)
        last_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written = out_path
        print(str(out_path))

    return passed, sidecar, written


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage B2 — route from discourse state (deterministic).")
    parser.add_argument("--scenario-json", type=Path, default=_DEFAULT_SCENARIO)
    parser.add_argument("--corpus-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--prior-json", type=Path, default=None)
    parser.add_argument("--discourse-json", type=Path, default=None, help="Stage B1 sidecar path.")
    parser.add_argument("--no-writes", action="store_true")
    args = parser.parse_args()

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
        print(
            json.dumps(
                {"gold_normalize_errors": norm_errors, "preflight": preflight_meta},
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    gold_routing = gold_norm

    dp = args.discourse_json.resolve() if args.discourse_json else None

    try:
        passed, _, _ = run_route_from_discourse_once(
            raw=raw,
            scenario_path=scenario_path,
            corpus_root=corpus_root,
            units_json=units_json,
            manifest_jsonable=manifest_jsonable,
            manifest_slugs=manifest_slugs,
            gold_routing=gold_routing,
            discourse_path=dp,
            no_writes=args.no_writes,
            preflight_meta=preflight_meta,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
