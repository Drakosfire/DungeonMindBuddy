"""Stage A vertical slice: extract structured event records from a session recap.

This runner calls the model once per run with the session recap text and a typed
Pydantic schema, then grades the resulting event records against the gold scenario.
No planner machinery, no corpus writes — pure structured-output extraction.

Pydantic models are defined in this module (do not modify fact_extractor.py).
The EventRecordModel mirrors event_record.schema.json exactly (same enums, same fields).

Path strategy: recap is read from the canonical corpus root
``corpus/eldyrwild-markdown/<recap_relative_path>``. The CORPUS_ROOT env var or the
default ``corpus/eldyrwild-markdown`` path relative to the repo root is used.

Run (from repo root)::

    uv run python -m evals.session_events_extraction_vertical_slice.step1_session_events_run --n 2 --model gpt-5.4-mini

Options::

    --n N               Number of runs in the cohort (default: 1)
    --model MODEL       Model ID (default: resolved via DUNGEONMIND_PLANNER_MODEL env or gpt-5.4-mini)
    --scenario-json     Path to gold scenario JSON (default: gold/session_events_session20.json)
    --runs-root         Override artifact runs root directory
    --no-writes         Skip writing run reports to disk
    -q / --quiet        Suppress progress lines on stderr
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Literal, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pydantic import BaseModel, Field  # noqa: E402

from src.agent.planner_pricing import usage_cost_usd  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from src.contracts.schema_validation import validate_many  # noqa: E402
from src.ingestion.entity_extractor import _usage_dict_from_openai_response  # noqa: E402
from src.llm.api_client import DungeonMindApiClient  # noqa: E402

from evals.session_events_extraction_vertical_slice.grader import (  # noqa: E402
    collect_session_events_violations,
    per_gate_verdict,
)
from evals.session_events_extraction_vertical_slice.session_events_run_report import (  # noqa: E402
    SessionEventsRunSummary,
    write_session_events_multi_summary,
    write_session_events_run_report,
)

_SLICE_DIR = Path(__file__).resolve().parent
_GOLD_SCENARIO = _SLICE_DIR / "gold" / "session_events_session20.json"
_DEFAULT_CORPUS_ROOT = _REPO_ROOT / "corpus" / "eldyrwild-markdown"

_DEFAULT_MODEL = "gpt-5.4-mini"

# ---------------------------------------------------------------------------
# Pydantic schema — mirrors event_record.schema.json exactly
# ---------------------------------------------------------------------------

_EventClass = Literal[
    "conversation",
    "travel",
    "combat",
    "discovery",
    "transfer",
    "ritual",
    "betrayal",
    "disaster",
    "investigation",
    "social_conflict",
]
_TimeScope = Literal["scene", "session", "historical_reference"]
_Certainty = Literal["observed", "inferred", "uncertain"]


class EventRecordModel(BaseModel):
    event_name: Optional[str] = None
    event_class: _EventClass
    participants: list[str] = Field(default_factory=list)
    referenced_slugs: list[str] = Field(default_factory=list)
    location: Optional[str] = None
    outcomes: list[str] = Field(default_factory=list)
    time_scope: _TimeScope
    certainty: _Certainty
    evidence_id: str = ""


class EventExtractionOutput(BaseModel):
    events: list[EventRecordModel]


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


def load_scenario(path: Path | None = None) -> dict[str, Any]:
    p = (path or _GOLD_SCENARIO).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"missing scenario JSON: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_corpus_root() -> Path:
    import os
    env = os.environ.get("DUNGEONMIND_CORPUS_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_CORPUS_ROOT


def read_recap(corpus_root: Path, recap_relative_path: str) -> str:
    path = corpus_root / recap_relative_path
    if not path.is_file():
        raise FileNotFoundError(
            f"Recap file not found: {path}\n"
            f"Corpus root: {corpus_root}\n"
            f"Relative path: {recap_relative_path}"
        )
    return path.read_text(encoding="utf-8")


def resolve_model(model_arg: str | None) -> str:
    import os
    if model_arg and model_arg.strip():
        return model_arg.strip()
    env = os.environ.get("DUNGEONMIND_PLANNER_MODEL", "").strip()
    if env:
        return env
    return _DEFAULT_MODEL


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert game-master event analyst for a tabletop RPG campaign. \
Your task is to extract all meaningful narrative events from a session recap as structured event records.

**SLUG CONTRACT (hard rule — no exceptions):** When a person, place, or thing in the recap has a \
canonical slug listed in the user message under "Known character slugs", you MUST use that slug \
verbatim in `participants[]`. NEVER use a display name, title, or surface form — only the \
exact slug string.

Concrete failure examples (DO NOT do these):
- WRONG: `"participants": ["Lysandra"]`   RIGHT: `"participants": ["captain_lysandra_ironveil"]`
- WRONG: `"participants": ["Stacey"]`     RIGHT: `"participants": ["stacey"]`
- WRONG: `"participants": ["Sara"]`       RIGHT: `"participants": ["sara_mirathorn_operator"]`

If you are unsure which slug maps to a character, pick the slug from the "Known character slugs" \
list that best matches — do not write a display name. If a character has no slug in the list, \
omit them from `participants[]` entirely.

**REFERENCED SLUGS CONTRACT (preserve named entities — hard rule):** When the recap names an \
entity (NPC, faction, character, or significant figure) **in connection with an event** but the \
entity is **not an actor** in that event — for example, when a "Big beats" header names someone \
the prose re-describes generically (e.g. "Kirfan" in the header, "the elderly fisherman" in the \
narrative), or when an event mentions a person who is referenced but not acting — emit the \
entity's slug in that event's `referenced_slugs[]` array. The same entity MAY appear in \
`participants[]` (if they also acted) AND `referenced_slugs[]` (if they were also referenced) \
across different events. Use the canonical slug from the "Known character slugs" list whenever \
one exists; if the referenced entity has no canonical slug, emit a stable lowercase-snake_case \
form derived from the recap's first naming (e.g. `kirfan`, `the_elderly_fisherman`) and a \
downstream entity-resolution stage will reconcile it. Do NOT invent slugs for entities that \
already have a canonical one — use the canonical slug verbatim.

The point of this field is to preserve naming evidence so a future stage can merge "the elderly \
fisherman" with "Kirfan" — without this slot, that merge is impossible.

Concrete examples of `referenced_slugs[]`:
- Recap header says `Helped Kirfan pull up debris from the broken structure from upriver`. Prose \
narrative re-describes the same beat as "the party helped an elderly fisherman drag wreckage \
from the river." The fisherman event has `participants: ["bonogo", "stafl", "baergrom"]` (the \
PCs who acted) and `referenced_slugs: ["kirfan"]` (the named NPC who was the subject but did \
not act in the prose beat).
- An event describes the party discussing what to do about a missing merchant. The merchant is \
named "Tomas" but does not appear in the scene. `participants: ["caelynn", "ephanna"]`, \
`referenced_slugs: ["tomas"]`.
- An event has the party fighting bandits while bystanders cheer. If a bystander has a name \
("Marla shouts encouragement from the doorway") but is not part of the action, put the \
bystander's slug in `referenced_slugs[]`, not `participants[]`.

`referenced_slugs[]` is OPTIONAL — emit an empty list (or omit entirely) when an event has no \
referenced-but-not-acting entities. Do NOT pad it with the same entries already in \
`participants[]`; an entity who actively did something belongs in `participants[]` only.

**OUTCOMES CONTRACT (preserve searchable vocabulary — hard rule):** The `outcomes[]` field is \
the durable, searchable record of what happened in each event. A future game-master will search \
the campaign archive by specific named terms — character names, character classes, character \
races, weapon names, spell names, ability names, item names, and place names. **When the recap \
uses a specific named term for a character class, character race, weapon, spell, ability, item, \
place, or NPC inside an event, that exact term MUST appear verbatim in at least one outcome \
string for that event.** Paraphrasing away these named terms destroys the archive's \
searchability and is the single most damaging mistake you can make.

Concrete examples of right vs wrong outcomes:
- WRONG: `"Karsemine attacks the swarm with her weapons"`
  RIGHT: `"Karsemine lands 4 scimitar and short-sword hits using Zephyr Strike, then dashes away"`
- WRONG: `"Ephanna casts an attack spell that hits the swarm"`
  RIGHT: `"Ephanna's second Eldritch Blast hits and removes a cluster from the swarm"`
- WRONG: `"Caelynn casts a wave spell that pushes the swarm back"`
  RIGHT: `"Caelynn casts Thunderwave, splits the swarm, and pushes it back 10 feet"`
- WRONG: `"Stuart confronts a girl about stolen money"`
  RIGHT: `"Stuart demands his gold back from Stacey and threatens her with a dart"`
- WRONG (PC introduction collapsed): single travel event with `outcomes: ["The party of \
six adventurers arrive at Stonebridge"]`
  RIGHT (PC introduction preserved per actor): emit one outcome per named PC carrying the \
class/race tokens the recap uses, e.g. `outcomes: ["Karsemine the Tiefling Ranger arrives at \
Stonebridge with the party", "Stafl the Human Bard arrives at Stonebridge with the party", \
"Caelynn the Half Elf Sorcerer arrives at Stonebridge with the party", ...]`. When a recap's \
opening paragraph names every PC by class+race, treat that as the canonical introduction event \
for those tokens; downstream stages rely on these outcome strings to recover per-PC identity.

Outcome shape rules:
- Each outcome is one concrete sentence.
- Prefer 2–5 outcomes per event; combat and social-conflict events usually need 3–5.
- If the recap names a character class, character race, weapon, spell, ability, item, place, \
or NPC inside an event, that name MUST appear verbatim in at least one of that event's outcomes.
- "Concrete" means: who did what to whom, with which named tool/spell/ability, and what changed.

Additional rules:
- Set evidence_id to the recap path provided in the user message.
- Use time_scope "scene" for specific events in this session.
- Use certainty "observed" for events directly described in the recap.
- Do not merge multiple distinct beats into a single event.
- Do not invent events not described in the recap.
- Aim for completeness: capture 10–20 events covering combat, social conflicts, conversations, \
discoveries, travel, rituals, and investigations.\
"""


def build_user_prompt(user_message: str, recap_text: str) -> str:
    return f"{user_message}\n\n---\n\n**RECAP TEXT:**\n\n{recap_text}"


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------


def run_session_events_extraction(
    *,
    client: Any,
    model_id: str,
    scenario: dict[str, Any],
    corpus_root: Path,
) -> dict[str, Any]:
    """Run one extraction, validate, grade, and return a result dict.

    Returns a dict with keys:
      parsed_events, violations, telemetry, per_gate, cost_usd, usage,
      raw_response_id, gates_passed, error (if any)
    """
    inp = scenario.get("input") or {}
    recap_relative_path = str(inp.get("recap_relative_path") or "")
    user_message = str(inp.get("user_message") or "")
    grading = scenario.get("grading") or {}

    if not recap_relative_path:
        return _error_result("scenario missing input.recap_relative_path")
    if not user_message:
        return _error_result("scenario missing input.user_message")

    try:
        recap_text = read_recap(corpus_root, recap_relative_path)
    except FileNotFoundError as exc:
        return _error_result(str(exc))

    user_prompt = build_user_prompt(user_message, recap_text)
    api_client = DungeonMindApiClient.wrap(client)

    try:
        api_result = api_client.responses_parse(
            action="session_events_extraction.extract",
            model=model_id,
            input=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            text_format=EventExtractionOutput,
        )
    except Exception as exc:
        return _error_result(f"API call failed: {exc}")

    response = api_result.response
    parsed: EventExtractionOutput | None = getattr(response, "output_parsed", None)
    if parsed is None:
        return _error_result("API response missing output_parsed (structured output failed)")

    if not isinstance(parsed, EventExtractionOutput):
        try:
            parsed = EventExtractionOutput.model_validate(parsed)
        except Exception as exc:
            return _error_result(f"Failed to validate output as EventExtractionOutput: {exc}")

    events_raw: list[dict[str, Any]] = []
    for ev in parsed.events:
        d = ev.model_dump()
        # Remove evidence_id if empty string (schema allows it to be absent)
        if d.get("evidence_id") == "":
            del d["evidence_id"]
        events_raw.append(d)

    usage = _usage_dict_from_openai_response(response)
    cost_info = usage_cost_usd(
        model_id=model_id,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
    )
    cost_usd = float(cost_info["total_usd"])
    raw_response_id = str(getattr(response, "id", "") or "")

    # SE1: validate each event against JSON schema (fail-loud if malformed)
    from jsonschema.exceptions import ValidationError
    from src.contracts.schema_validation import list_validation_failures

    schema_failures = list_validation_failures(events_raw, "event_record.schema.json")
    if schema_failures:
        # Fail-loud: report schema errors but continue so grader can record SE1 failures
        bad_indices = [i for i, _, _ in schema_failures]
        print(
            f"[session-events] WARNING: {len(schema_failures)} event(s) failed schema validation "
            f"(indices: {bad_indices}). Grader will record SE1 FAILs.",
            file=sys.stderr,
        )

    violations, telemetry = collect_session_events_violations(events_raw, grading)
    verdict = per_gate_verdict(violations)
    gates_passed = not violations

    return {
        "parsed_events": events_raw,
        "violations": violations,
        "telemetry": telemetry,
        "per_gate": verdict,
        "cost_usd": cost_usd,
        "usage": usage,
        "cost_info": cost_info,
        "raw_response_id": raw_response_id,
        "gates_passed": gates_passed,
        "error": None,
    }


def _error_result(msg: str) -> dict[str, Any]:
    return {
        "parsed_events": [],
        "violations": {"input": [msg]},
        "telemetry": {"event_count": 0, "participants_seen": [], "event_classes_seen": [],
                      "expected_event_coverage_ratio": 0.0, "unmatched_expected_event_indices": []},
        "per_gate": {"SE1": "FAIL", "SE2": "FAIL", "SE3": "FAIL", "SE4": "FAIL", "SE5": "FAIL"},
        "cost_usd": 0.0,
        "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
        "cost_info": {},
        "raw_response_id": "",
        "gates_passed": False,
        "error": msg,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage A: session events extraction benchmark"
    )
    parser.add_argument("--n", type=int, default=1, help="Cohort size (default: 1)")
    parser.add_argument("--model", type=str, default="", help="Model ID")
    parser.add_argument("--scenario-json", type=Path, default=None)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--no-writes", action="store_true", help="Skip writing artifacts")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    load_dungeonmindbuddy_dotenv()

    import os
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY missing after loading .env / .env.development.", file=sys.stderr)
        sys.exit(2)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model_id = resolve_model(args.model.strip() or None)
    gold = load_scenario(args.scenario_json)
    scenario_id = str(gold.get("scenario_id") or "session_events_session20")
    n = max(1, int(args.n))
    corpus_root = resolve_corpus_root()

    if not args.quiet:
        print(
            f"[session-events] n={n} model={model_id} corpus_root={corpus_root}",
            file=sys.stderr,
        )

    summaries: list[SessionEventsRunSummary] = []
    total_cost = 0.0
    pass_count = 0

    for i in range(n):
        if not args.quiet:
            print(f"[session-events] run {i + 1}/{n} starting…", file=sys.stderr)
        t0 = time.monotonic()

        result = run_session_events_extraction(
            client=client,
            model_id=model_id,
            scenario=gold,
            corpus_root=corpus_root,
        )
        elapsed_s = round(time.monotonic() - t0, 2)
        cost = float(result["cost_usd"])
        total_cost += cost
        gates_passed = bool(result["gates_passed"])
        if gates_passed:
            pass_count += 1
        verdict = result["per_gate"]
        telemetry = result["telemetry"]
        event_count = int(telemetry.get("event_count", 0))

        verdict_str = " ".join(f"{k}={v}" for k, v in sorted(verdict.items()))
        print(
            f"[session-events] run {i + 1}/{n} | "
            f"{'PASS' if gates_passed else 'FAIL'} | "
            f"events={event_count} | "
            f"cost_usd={cost:.4f} | "
            f"elapsed={elapsed_s}s | "
            f"{verdict_str}"
        )

        if result.get("error"):
            print(f"[session-events] run {i + 1} error: {result['error']}", file=sys.stderr)

        if not args.no_writes:
            paths, summary = write_session_events_run_report(
                scenario_id=scenario_id,
                model_id=model_id,
                gates_passed=gates_passed,
                per_gate_verdict=verdict,
                violations=result["violations"],
                grader_telemetry=telemetry,
                parsed_events=result["parsed_events"],
                cost_usd=cost,
                usage=result["usage"],
                scenario=gold,
                runs_root=args.runs_root,
                run_index=i if n > 1 else None,
                cohort_size=n if n > 1 else None,
            )
            summaries.append(summary)
            if not args.quiet:
                print(f"[session-events] report: {paths.primary_md}", file=sys.stderr)
                print(f"[session-events] sidecar: {paths.sidecar_json}", file=sys.stderr)
        else:
            from datetime import datetime, timezone
            summaries.append(
                SessionEventsRunSummary(
                    run_index=i,
                    iso_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    gates_passed=gates_passed,
                    scenario_estimated_cost_usd=round(cost, 6),
                    event_count=event_count,
                    violation_counts={k: len(v) for k, v in result["violations"].items()},
                    per_gate_verdict=verdict,
                    primary_md_path="",
                    sidecar_json_path="",
                )
            )

        # Budget guard: stop if cost > $1.00 with no passes after 2+ runs
        if total_cost > 1.0 and pass_count == 0 and i >= 1 and i + 1 < n:
            print(
                f"[session-events] STOP: cumulative cost ${total_cost:.2f} with 0 passes; "
                "skipping remaining cohort runs per budget guard.",
                file=sys.stderr,
            )
            break

    if total_cost > 2.0:
        print(
            f"[session-events] WARNING: cumulative cost ${total_cost:.2f} exceeded $2.00 cap.",
            file=sys.stderr,
        )

    if n > 1 and summaries and not args.no_writes:
        md_s, json_s = write_session_events_multi_summary(
            summaries,
            model_id=model_id,
            scenario_id=scenario_id,
            runs_root=args.runs_root,
        )
        print(f"[session-events] cohort summary: {md_s}", file=sys.stderr)
        print(f"[session-events] cohort sidecar: {json_s}", file=sys.stderr)

    print(
        f"[session-events] cohort done | pass_rate={pass_count}/{n} | "
        f"total_cost_usd=${total_cost:.4f}"
    )

    if summaries and not all(s.gates_passed for s in summaries):
        sys.exit(1)


if __name__ == "__main__":
    main()
