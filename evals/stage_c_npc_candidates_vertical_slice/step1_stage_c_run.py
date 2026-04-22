"""Stage C vertical slice: classify event-mention entities into 3 buckets.

Stage C consumes Stage A's events JSON (frozen as a fixture for deterministic
testing) plus the per-campaign NPC registry and a PC negative list, and emits
``StageCOutput``: tracked_npcs_active[], new_npc_candidates[],
unresolved_descriptors[]. No corpus reads, no recap re-reads — all input is
JSON (matching the discipline Stage B established).

Run (from repo root)::

    uv run python -m evals.stage_c_npc_candidates_vertical_slice.step1_stage_c_run \\
        --n 5 --model gpt-5.4-mini

Options::

    --n N               Number of runs in the cohort (default: 1)
    --model MODEL       Model ID (default: resolved via DUNGEONMIND_PLANNER_MODEL or gpt-5.4-mini)
    --scenario-json     Path to gold scenario JSON (default: gold/stage_c_session20.json)
    --runs-root         Override artifact runs root directory
    --no-writes         Skip writing run reports to disk
    -q / --quiet        Suppress progress lines on stderr
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pydantic import BaseModel, Field  # noqa: E402

from src.agent.planner_pricing import usage_cost_usd  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from src.contracts.npc_registry import load_npc_registry  # noqa: E402
from src.ingestion.entity_extractor import _usage_dict_from_openai_response  # noqa: E402
from src.llm.api_client import DungeonMindApiClient  # noqa: E402

from evals.stage_c_npc_candidates_vertical_slice.grader import grade_stage_c  # noqa: E402
from evals.stage_c_npc_candidates_vertical_slice.stage_c_run_report import (  # noqa: E402
    StageCRunSummary,
    write_stage_c_multi_summary,
    write_stage_c_run_report,
)


_SLICE_DIR = Path(__file__).resolve().parent
_GOLD_SCENARIO = _SLICE_DIR / "gold" / "stage_c_session20.json"
_DEFAULT_MODEL = "gpt-5.4-mini"


# ---------------------------------------------------------------------------
# Pydantic structured output
# ---------------------------------------------------------------------------


class TrackedNpcActive(BaseModel):
    slug: str
    evidence_event_indices: list[int] = Field(default_factory=list)
    appearance_count: int = 0


class NewNpcCandidate(BaseModel):
    descriptor: str
    suggested_slug: str
    evidence_event_indices: list[int] = Field(default_factory=list)
    rationale: str = ""


class UnresolvedDescriptor(BaseModel):
    descriptor: str
    evidence_event_indices: list[int] = Field(default_factory=list)
    rationale: str = ""


class StageCOutput(BaseModel):
    tracked_npcs_active: list[TrackedNpcActive] = Field(default_factory=list)
    new_npc_candidates: list[NewNpcCandidate] = Field(default_factory=list)
    unresolved_descriptors: list[UnresolvedDescriptor] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


def load_scenario(path: Path | None = None) -> dict[str, Any]:
    p = (path or _GOLD_SCENARIO).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"missing scenario JSON: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _resolve_relative(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()


def load_events_fixture(path_str: str) -> list[dict[str, Any]]:
    path = _resolve_relative(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Stage A events fixture not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"events fixture {path} is not a top-level JSON array")
    return data


def load_registry_records(path_str: str) -> list[dict[str, Any]]:
    """Load registry as list[dict] (the grader and prompt builder use plain dicts)."""
    path = _resolve_relative(path_str)
    records = load_npc_registry(path)
    return [r.model_dump(mode="json") for r in records]


def resolve_model(model_arg: str | None) -> str:
    if model_arg and model_arg.strip():
        return model_arg.strip()
    env = os.environ.get("DUNGEONMIND_PLANNER_MODEL", "").strip()
    if env:
        return env
    return _DEFAULT_MODEL


# ---------------------------------------------------------------------------
# System prompt (the contract)
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = """\
You are a tabletop-RPG entity classifier. Your task is to classify entities mentioned in \
session events into three buckets so a downstream entity-resolution stage knows which \
existing NPCs to update, which new NPCs the GM should review, and which descriptors need \
human disambiguation.

## THREE-BUCKET CONTRACT

You MUST emit exactly three arrays in your JSON output:

1. **`tracked_npcs_active[]`** — entities in the **registry positive-list** who appear in \
at least one event. The registry is supplied in the user message as `tracked_npc_registry`. \
Match an event entity to a registry record by **any** of: (a) exact slug match against the \
record's `slug`, (b) case-insensitive match against `display_name`, (c) case-insensitive \
substring match against any item in `aliases[]`. Always emit the registry's canonical \
`slug` (NEVER the alias or display name) in this bucket. `evidence_event_indices[]` MUST \
list every 0-indexed event position where the NPC appears (in `participants[]` OR \
`referenced_slugs[]`). `appearance_count` MUST equal `len(evidence_event_indices)`.

2. **`new_npc_candidates[]`** — entities that appear in events but have **no match** in \
the registry (by slug, display_name, or any alias). Emit:
   - `descriptor`: how the recap named this entity (use the most descriptive form)
   - `suggested_slug`: lowercase snake_case derived from the most distinctive part of the \
descriptor (no `npc_` prefix; e.g. "Professor Tealeaf" → `professor_tealeaf`, "Kirfan" → \
`kirfan`, "the elderly fisherman" → `the_elderly_fisherman`)
   - `evidence_event_indices`: at least one 0-indexed event position
   - `rationale`: ONE sentence explaining why this is a new NPC candidate

3. **`unresolved_descriptors[]`** — descriptors that COULD be a known NPC or COULD be new \
but cannot be confidently classified (e.g. "the masked figure" with no other naming \
evidence). Use SPARINGLY: if the descriptor is at least named, default to \
`new_npc_candidates[]` instead. Emit `descriptor`, `evidence_event_indices` (≥1), and \
`rationale` (one sentence why classification is ambiguous).

## PC NEGATIVE LIST — HARD RULE

PCs are NEVER NPCs. The user message supplies a `pc_roster`. If a slug or descriptor \
matches the PC roster (by slug, display_name, or any alias — case-insensitive substring), \
**DO NOT include it in any output bucket**. Drop it silently. PCs leaking into Stage C \
output corrupts every downstream stage; this is the single most damaging mistake you can \
make.

## EVIDENCE DISCIPLINE — HARD RULE

Every record in every bucket MUST cite at least one valid `evidence_event_indices[]` \
entry (0-indexed positions in the input `events` array). For `tracked_npcs_active[]`, \
list **all** events where the NPC appears, not just one. Do NOT cite event indices that \
do not actually mention the entity.

## NO HALLUCINATION

Only classify entities that actually appear in the events' `participants[]` or \
`referenced_slugs[]` fields. Do NOT invent NPCs that aren't there. Do NOT include \
registry entries who don't appear in events (the registry is large; only \
active-in-this-session ones go in `tracked_npcs_active[]`).

## SUGGESTED-SLUG CONVENTION

Lowercase, snake_case, derived from the most distinctive part of the descriptor. \
"the elderly fisherman" → `the_elderly_fisherman`. "Professor Tealeaf" → \
`professor_tealeaf`. "Kirfan" → `kirfan`. Do NOT add prefixes like `npc_`.

## EXAMPLES (drawn from the C2 corpus)

- Event has `participants: [bonogo, stafl]`, `referenced_slugs: [kirfan]`. PC roster \
includes `bonogo, stafl`. `kirfan` is not in the registry → \
`new_npc_candidates: [{descriptor: "Kirfan", suggested_slug: "kirfan", \
evidence_event_indices: [N], rationale: "Named NPC referenced in event but not in \
registry"}]`. `bonogo` and `stafl` are PCs — drop them silently.

- Event has `participants: [thrin_branchborn]`. Registry has `thrin_branchborn` \
(status=tracked) → `tracked_npcs_active: [{slug: "thrin_branchborn", \
evidence_event_indices: [N], appearance_count: 1}]`.

- Event has `participants: [stacey]`. Registry has `stacey_brambleback` (status=tracked) \
with alias `Stacey`. The event slug `stacey` matches the alias `Stacey` (case-insensitive \
substring) → emit the canonical registry slug: \
`tracked_npcs_active: [{slug: "stacey_brambleback", evidence_event_indices: [N], \
appearance_count: 1}]`.

- Event has `referenced_slugs: ["the_masked_figure"]` with no other naming → \
`unresolved_descriptors: [{descriptor: "the masked figure", \
evidence_event_indices: [N], rationale: "Descriptor without identifying name"}]`.
"""


def build_user_message(
    *,
    pc_roster: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    events: list[dict[str, Any]],
    session_label: str,
    campaign_id: str,
) -> str:
    pc_json = json.dumps(pc_roster, indent=2, ensure_ascii=False)
    reg_json = json.dumps(registry, indent=2, ensure_ascii=False)
    events_json = json.dumps(events, indent=2, ensure_ascii=False)

    parts = [
        f"Classify the entities mentioned in the events from {session_label} of campaign "
        f"`{campaign_id}` into the three buckets defined in the system prompt.",
        "",
        "## PC Roster (negative list — these are PLAYER CHARACTERS, never classify them as NPCs)",
        "",
        "```json",
        pc_json,
        "```",
        "",
        "## Tracked NPC Registry (positive list — known canonical NPCs in this campaign)",
        "",
        "```json",
        reg_json,
        "```",
        "",
        "## Session Events (extracted from the recap; 0-indexed)",
        "",
        "```json",
        events_json,
        "```",
        "",
        "Now classify every distinct non-PC entity mentioned in any event's `participants[]` "
        "or `referenced_slugs[]` into one of three buckets. Emit `StageCOutput` JSON.",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------


def run_stage_c(
    *,
    client: Any,
    model_id: str,
    scenario: dict[str, Any],
    events: list[dict[str, Any]],
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    inp = scenario.get("input") or {}
    pc_roster = list(inp.get("pc_roster") or [])
    session_label = str(inp.get("session_label") or "")
    campaign_id = str(inp.get("campaign_id") or "")

    user_message = build_user_message(
        pc_roster=pc_roster,
        registry=registry,
        events=events,
        session_label=session_label,
        campaign_id=campaign_id,
    )

    api_client = DungeonMindApiClient.wrap(client)
    try:
        api_result = api_client.responses_parse(
            action="stage_c_npc_candidate_id.classify",
            model=model_id,
            input=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            text_format=StageCOutput,
        )
    except Exception as exc:
        return _error_result(f"API call failed: {exc}")

    response = api_result.response
    parsed: StageCOutput | None = getattr(response, "output_parsed", None)
    if parsed is None:
        return _error_result("API response missing output_parsed (structured output failed)")
    if not isinstance(parsed, StageCOutput):
        try:
            parsed = StageCOutput.model_validate(parsed)
        except Exception as exc:
            return _error_result(f"Failed to validate output as StageCOutput: {exc}")

    output_dict = parsed.model_dump()
    grade = grade_stage_c(output_dict, scenario, events, registry)

    usage = _usage_dict_from_openai_response(response)
    cost_info = usage_cost_usd(
        model_id=model_id,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
    )
    cost_usd = float(cost_info["total_usd"])
    raw_response_id = str(getattr(response, "id", "") or "")

    return {
        "stage_c_output": output_dict,
        "violations": grade["violations"],
        "violation_counts": grade["violation_counts"],
        "telemetry": grade["telemetry"],
        "per_gate_verdict": grade["per_gate_verdict"],
        "all_gates_passed": grade["all_gates_passed"],
        "gates_passed_str": grade["gates_passed"],
        "cost_usd": cost_usd,
        "usage": usage,
        "cost_info": cost_info,
        "raw_response_id": raw_response_id,
        "error": None,
    }


def _error_result(msg: str) -> dict[str, Any]:
    return {
        "stage_c_output": {
            "tracked_npcs_active": [],
            "new_npc_candidates": [],
            "unresolved_descriptors": [],
        },
        "violations": [msg],
        "violation_counts": {"NC1": 1, "NC2": 0, "NC3": 0, "NC4": 0, "NC5": 0},
        "telemetry": {
            "tracked_active_count": 0,
            "new_candidates_count": 0,
            "unresolved_count": 0,
            "registry_recall_ratio": 0.0,
            "expected_tracked_active_missing": [],
            "expected_new_candidate_coverage_hit": False,
            "pc_leaks": [],
        },
        "per_gate_verdict": {"NC1": "FAIL", "NC2": "FAIL", "NC3": "FAIL", "NC4": "FAIL", "NC5": "FAIL"},
        "all_gates_passed": False,
        "gates_passed_str": "0/5",
        "cost_usd": 0.0,
        "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
        "cost_info": {},
        "raw_response_id": "",
        "error": msg,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage C: NPC candidate identification benchmark"
    )
    parser.add_argument("--n", type=int, default=1, help="Cohort size (default: 1)")
    parser.add_argument("--model", type=str, default="", help="Model ID")
    parser.add_argument("--scenario-json", type=Path, default=None)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--no-writes", action="store_true", help="Skip writing artifacts")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    load_dungeonmindbuddy_dotenv()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print(
            "OPENAI_API_KEY missing after loading .env / .env.development "
            "(see src/bootstrap_env.py).",
            file=sys.stderr,
        )
        sys.exit(2)

    from openai import OpenAI

    client = OpenAI()
    model_id = resolve_model(args.model.strip() or None)
    scenario = load_scenario(args.scenario_json)
    scenario_id = str(scenario.get("scenario_id") or "stage_c_session20")
    n = max(1, int(args.n))

    inp = scenario.get("input") or {}
    events_path = str(inp.get("stage_a_events_path") or "")
    registry_path = str(inp.get("npc_registry_path") or "")
    if not events_path:
        print("scenario missing input.stage_a_events_path", file=sys.stderr)
        sys.exit(2)
    if not registry_path:
        print("scenario missing input.npc_registry_path", file=sys.stderr)
        sys.exit(2)

    events = load_events_fixture(events_path)
    registry = load_registry_records(registry_path)

    if not args.quiet:
        print(
            f"[stage-c] n={n} model={model_id} events={len(events)} "
            f"registry_records={len(registry)}",
            file=sys.stderr,
        )

    summaries: list[StageCRunSummary] = []
    total_cost = 0.0
    pass_count = 0

    for i in range(n):
        if not args.quiet:
            print(f"[stage-c] run {i + 1}/{n} starting…", file=sys.stderr)
        t0 = time.monotonic()
        result = run_stage_c(
            client=client,
            model_id=model_id,
            scenario=scenario,
            events=events,
            registry=registry,
        )
        elapsed_s = round(time.monotonic() - t0, 2)
        cost = float(result["cost_usd"])
        total_cost += cost
        gates_passed = bool(result["all_gates_passed"])
        if gates_passed:
            pass_count += 1
        verdict = result["per_gate_verdict"]
        telemetry = result["telemetry"]
        verdict_str = " ".join(f"{k}={v}" for k, v in sorted(verdict.items()))
        print(
            f"[stage-c] run {i + 1}/{n} | "
            f"{'PASS' if gates_passed else 'FAIL'} | "
            f"tracked={telemetry.get('tracked_active_count', 0)} "
            f"new={telemetry.get('new_candidates_count', 0)} "
            f"unresolved={telemetry.get('unresolved_count', 0)} | "
            f"tealeaf_hit={telemetry.get('expected_new_candidate_coverage_hit', False)} | "
            f"cost_usd={cost:.4f} | "
            f"elapsed={elapsed_s}s | "
            f"{verdict_str}"
        )

        if result.get("error"):
            print(f"[stage-c] run {i + 1} error: {result['error']}", file=sys.stderr)

        if not args.no_writes:
            paths, summary = write_stage_c_run_report(
                scenario_id=scenario_id,
                model_id=model_id,
                gates_passed=gates_passed,
                per_gate_verdict=verdict,
                violations=result["violations"],
                violation_counts=result["violation_counts"],
                grader_telemetry=telemetry,
                stage_c_output=result["stage_c_output"],
                cost_usd=cost,
                usage=result["usage"],
                scenario=scenario,
                runs_root=args.runs_root,
                run_index=i if n > 1 else None,
                cohort_size=n if n > 1 else None,
            )
            summaries.append(summary)
            if not args.quiet:
                print(f"[stage-c] report: {paths.primary_md}", file=sys.stderr)
                print(f"[stage-c] sidecar: {paths.sidecar_json}", file=sys.stderr)
        else:
            from datetime import datetime, timezone
            summaries.append(
                StageCRunSummary(
                    run_index=i,
                    iso_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    gates_passed=gates_passed,
                    scenario_estimated_cost_usd=round(cost, 6),
                    tracked_active_count=int(telemetry.get("tracked_active_count", 0)),
                    new_candidates_count=int(telemetry.get("new_candidates_count", 0)),
                    unresolved_count=int(telemetry.get("unresolved_count", 0)),
                    violation_counts=dict(result["violation_counts"]),
                    per_gate_verdict=dict(verdict),
                    primary_md_path="",
                    sidecar_json_path="",
                    extras={"grader_telemetry": dict(telemetry)},
                )
            )

        if total_cost > 1.0 and pass_count == 0 and i >= 1 and i + 1 < n:
            print(
                f"[stage-c] STOP: cumulative cost ${total_cost:.2f} with 0 passes; "
                "skipping remaining cohort runs per budget guard.",
                file=sys.stderr,
            )
            break

    if total_cost > 2.0:
        print(
            f"[stage-c] WARNING: cumulative cost ${total_cost:.2f} exceeded $2.00 cap.",
            file=sys.stderr,
        )

    if n > 1 and summaries and not args.no_writes:
        md_s, json_s = write_stage_c_multi_summary(
            summaries,
            model_id=model_id,
            scenario_id=scenario_id,
            runs_root=args.runs_root,
        )
        print(f"[stage-c] cohort summary: {md_s}", file=sys.stderr)
        print(f"[stage-c] cohort sidecar: {json_s}", file=sys.stderr)

    print(
        f"[stage-c] cohort done | pass_rate={pass_count}/{n} | "
        f"total_cost_usd=${total_cost:.4f}"
    )

    if summaries and not all(s.gates_passed for s in summaries):
        sys.exit(1)


if __name__ == "__main__":
    main()
