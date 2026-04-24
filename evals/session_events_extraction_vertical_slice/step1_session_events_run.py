"""Recap-to-events extraction slice: structured event records from a recap.

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
import re
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
from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha  # noqa: E402
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
_MAX_PC_HINTS = 10
_MAX_PC_HINT_CHARS_PER_ENTRY = 320
_MAX_PC_HINT_CHARS_TOTAL = 2400

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


class AnchorRepairItem(BaseModel):
    event_index: int
    status: Literal["anchored", "unresolved"]
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    revised_event_name: Optional[str] = None
    revised_outcomes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: Optional[str] = None
    unresolved_reason: Optional[str] = None


class AnchorRepairOutput(BaseModel):
    repairs: list[AnchorRepairItem]


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

**REFERENCED-NAME ECHO (hard rule):** Every entity you place in `referenced_slugs[]` MUST also \
have its **canonical proper name** appear verbatim in at least one of that event's `outcomes[]` \
strings — not just a generic descriptor. The slug list and the outcomes are read by separate \
downstream stages: the timeline-pass stage only sees `outcomes[]` text and cannot search the \
slug list, so a name that lives only in `referenced_slugs[]` is invisible to the timeline beat. \
Use the canonical surface name from the recap (e.g. "Kirfan", not "kirfan"; "Tomas", not \
"tomas") in the outcome sentence; you may add a generic gloss after it ("the elderly fisherman \
Kirfan", "Tomas the merchant"), but the proper name itself must be there verbatim.

Concrete example: if you emit `referenced_slugs: ["kirfan"]` for a stuck-net beat, at least one \
outcome must read like `"The party helps the elderly fisherman Kirfan recover his stuck net"` \
or `"Kirfan's stuck net turns out to be roof beams"` — NOT `"The group meets an elderly \
fisherman whose net is stuck"` (which loses the name).

**MULTI-PARTICIPANT ROSTER COMPLETENESS (hard rule):** When the recap describes a single action whose subject is a comma-separated list of named characters (e.g. "A, B, C, and D accepted the offer", or "X, Y, and Z entered the room together", or "all five PCs heard the noise"), every named character in that list belongs in `participants[]` for the corresponding event. Do not omit any name from the comma list. Before emitting the event, count the named characters in the recap's listing sentence and confirm `len(participants)` is at least that count plus any non-PC participants the same sentence introduces (e.g. an NPC offering the ride). If you find yourself summarizing the roster as "the party" or "the group" without enumerating, expand the enumeration into `participants[]`.

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

_ANCHOR_REPAIR_SYSTEM_PROMPT = """\
You repair weak event provenance for a tabletop recap extraction benchmark.

Input contains:
- recap text with numbered lines
- events that currently have weak anchors

For each event:
1) Select a precise line span that best supports the event (usually 1-8 lines).
2) Improve event fidelity: keep only facts grounded in that span.
3) Preserve distinctive named terms when present (NPC names, places, spells, items).
4) If uncertain, return unresolved.

Hard rules:
- NEVER return whole-file spans.
- DO NOT invent details absent from the selected lines.
- Keep participant slugs unchanged (not returned here, but event identity depends on it).
- Prefer concise, concrete outcomes.

Return strictly the requested schema.
"""


def _campaign_id_from_recap_relative_path(recap_relative_path: str) -> str | None:
    """Infer campaign ID from recap path when possible.

    Example:
      Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md -> longmont-c2
    """
    m = re.search(r"Longmont Campaign/Campaign\s+(\d+)", recap_relative_path)
    if not m:
        return None
    return f"longmont-c{m.group(1)}"


def _extract_known_character_slugs(user_message: str) -> set[str]:
    """Parse a known-character-slugs list from the scenario user message when present."""
    marker = "Known character slugs:"
    idx = user_message.find(marker)
    if idx < 0:
        return set()
    tail = user_message[idx + len(marker):]
    first_line = tail.splitlines()[0] if tail else ""
    raw = [s.strip() for s in first_line.split(",")]
    return {slug for slug in raw if slug}


def _campaign_number_from_campaign_id(campaign_id: str | None) -> str | None:
    if not campaign_id:
        return None
    m = re.fullmatch(r"longmont-c(\d+)", campaign_id.strip())
    if not m:
        return None
    return m.group(1)


def discover_campaign_pc_hub_dirs(corpus_root: Path, recap_relative_path: str) -> list[Path]:
    """Return campaign-relevant PC hub directories.

    Prefer the recap's campaign when recognizable. If that campaign has no PC hubs,
    fall back to all other Longmont campaign PC hubs so the flow can still provide
    minimal hints when available.
    """
    campaign_id = _campaign_id_from_recap_relative_path(recap_relative_path)
    campaign_num = _campaign_number_from_campaign_id(campaign_id)
    longmont_root = corpus_root / "Longmont Campaign"
    if not longmont_root.is_dir():
        return []

    preferred_base: Path | None = None
    if campaign_num:
        candidate = longmont_root / f"Campaign {campaign_num}" / "PCs"
        if candidate.is_dir():
            preferred_base = candidate

    def _hub_dirs(pcs_dir: Path) -> list[Path]:
        return sorted([p for p in pcs_dir.iterdir() if p.is_dir() and p.name.strip()])

    if preferred_base is not None:
        preferred_hubs = _hub_dirs(preferred_base)
        if preferred_hubs:
            return preferred_hubs

    fallback_hubs: list[Path] = []
    for campaign_dir in sorted(longmont_root.glob("Campaign */PCs")):
        if not campaign_dir.is_dir():
            continue
        fallback_hubs.extend(_hub_dirs(campaign_dir))
    return fallback_hubs


def _split_frontmatter_and_body(text: str) -> tuple[dict[str, str], str]:
    text = text.strip()
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, text
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}, text

    frontmatter: dict[str, str] = {}
    for line in lines[1:end_idx]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        k = key.strip()
        v = value.strip().strip('"').strip("'")
        if k:
            frontmatter[k] = v
    body = "\n".join(lines[end_idx + 1:]).strip()
    return frontmatter, body


def _clean_hint_fragment(text: str) -> str:
    t = re.sub(r"`([^`]*)`", r"\1", text)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _first_nonempty_paragraph(body: str) -> str:
    chunks = [c.strip() for c in body.split("\n\n")]
    for chunk in chunks:
        if not chunk:
            continue
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        if lines[0].startswith("#"):
            continue
        joined = " ".join(lines)
        if joined.startswith("|") and joined.endswith("|"):
            continue
        if joined.startswith("- "):
            continue
        return _clean_hint_fragment(joined)
    return ""


def _extract_species_class_line(body: str) -> str:
    for raw in body.splitlines():
        line = raw.strip()
        if not line.startswith("|") or "Species / class" not in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 2:
            return _clean_hint_fragment(parts[1])
    return ""


def _extract_timeline_intro_row(timeline_text: str) -> str:
    for raw in timeline_text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        if "Session" in line and "Beat" in line:
            continue
        if re.match(r"^\|\s*-+\s*\|", line):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue
        session_token = _clean_hint_fragment(parts[0])
        beat = _clean_hint_fragment(parts[1])
        if not beat:
            continue
        if session_token:
            return f"{session_token}: {beat}"
        return beat
    return ""


def _read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _build_pc_hint_entry(hub_dir: Path) -> str:
    slug = hub_dir.name.strip()
    if not slug:
        return ""

    dossier_candidates = sorted(hub_dir.glob("*_character_dossier*.md"))
    dossier_text = _read_text_if_exists(dossier_candidates[0]) if dossier_candidates else ""
    timeline_text = _read_text_if_exists(hub_dir / "timeline.md")

    fragments: list[str] = []
    if dossier_text:
        fm, body = _split_frontmatter_and_body(dossier_text)
        title = _clean_hint_fragment(fm.get("title", ""))
        if title:
            fragments.append(f"title={title}")
        species_class = _extract_species_class_line(body)
        if species_class:
            fragments.append(f"species/class={species_class}")
        para = _first_nonempty_paragraph(body)
        if para:
            fragments.append(para)

    if timeline_text:
        _, timeline_body = _split_frontmatter_and_body(timeline_text)
        intro = _extract_timeline_intro_row(timeline_body)
        if intro:
            fragments.append(f"timeline={intro}")

    if not fragments:
        return ""

    entry = f"- {slug}: " + " | ".join(fragments)
    if len(entry) > _MAX_PC_HINT_CHARS_PER_ENTRY:
        entry = entry[: _MAX_PC_HINT_CHARS_PER_ENTRY - 1].rstrip() + "…"
    return entry


def load_pc_identity_hints(
    corpus_root: Path,
    recap_relative_path: str,
    user_message: str,
) -> str:
    """Load bounded PC identity hints for the recap's campaign context."""
    hubs = discover_campaign_pc_hub_dirs(corpus_root, recap_relative_path)
    if not hubs:
        return ""

    known_slugs = _extract_known_character_slugs(user_message)
    entries: list[str] = []
    total_chars = 0

    for hub in hubs:
        slug = hub.name.strip()
        if known_slugs and slug not in known_slugs:
            continue
        entry = _build_pc_hint_entry(hub)
        if not entry:
            continue
        projected = total_chars + len(entry) + (1 if entries else 0)
        if projected > _MAX_PC_HINT_CHARS_TOTAL:
            break
        entries.append(entry)
        total_chars = projected
        if len(entries) >= _MAX_PC_HINTS:
            break

    return "\n".join(entries)


def build_user_prompt(user_message: str, recap_text: str, pc_identity_hints: str = "") -> str:
    hint_block = ""
    if pc_identity_hints.strip():
        hint_block = (
            "\n\n---\n\n"
            "**PC IDENTITY HINTS (fallback anchors):**\n"
            "- Use these hints only when recap phrasing is terse or ambiguous.\n"
            "- Never let hints override explicit recap facts.\n"
            "- If recap text conflicts with a hint, trust the recap text.\n\n"
            f"{pc_identity_hints.strip()}"
        )
    return f"{user_message}{hint_block}\n\n---\n\n**RECAP TEXT:**\n\n{recap_text}"


def _default_event_source_anchors(recap_relative_path: str, recap_text: str) -> list[dict[str, Any]]:
    lines = recap_text.splitlines()
    if not lines:
        return []
    _, anchor = build_recap_extracted_anchor(
        corpus_source_path=recap_relative_path,
        full_file_lines=lines,
        line_start_1=1,
        line_end_1=len(lines),
        commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
    )
    return [anchor.to_json_dict()]


def _tokenize_for_overlap(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9']+", text.lower()) if len(t) >= 4}


def _event_text_blob(event: dict[str, Any]) -> str:
    return " ".join(
        [
            str(event.get("event_name") or ""),
            " ".join(str(x) for x in (event.get("outcomes") or [])),
        ]
    ).strip()


def _lines_window_text(lines: list[str], line_start: int, line_end: int) -> str:
    return "\n".join(lines[max(0, line_start - 1): line_end])


def _is_weak_anchor(anchor: dict[str, Any], total_lines: int) -> bool:
    source_type = str(anchor.get("source_type", "") or "").strip()
    if source_type == "legacy_unanchored":
        return True
    try:
        line_start = int(anchor.get("line_start"))
        line_end = int(anchor.get("line_end"))
    except (TypeError, ValueError):
        return True
    if line_start == 1 and line_end >= total_lines:
        return True
    return False


def _build_anchor_repair_user_prompt(
    *,
    recap_relative_path: str,
    recap_lines: list[str],
    weak_events: list[dict[str, Any]],
) -> str:
    numbered = "\n".join(f"{i:04d}: {line}" for i, line in enumerate(recap_lines, 1))
    payload = {
        "recap_relative_path": recap_relative_path,
        "events_to_repair": weak_events,
    }
    return (
        "Repair event anchors for the recap below.\n\n"
        "Return one repair row per input event using the same event_index.\n"
        "If you cannot confidently anchor an event, set status=unresolved.\n\n"
        f"INPUT EVENTS JSON:\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n\n"
        f"RECAP LINES:\n```text\n{numbered}\n```"
    )


def _repair_weak_event_anchors(
    *,
    client: Any,
    model_id: str,
    recap_relative_path: str,
    recap_text: str,
    events_raw: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    recap_lines = recap_text.splitlines()
    if not recap_lines:
        return events_raw, {"repaired": 0, "unresolved": 0, "skipped": len(events_raw)}, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }

    weak: list[dict[str, Any]] = []
    for idx, ev in enumerate(events_raw):
        anchors = [a for a in (ev.get("source_anchors") or []) if isinstance(a, dict)]
        if not anchors or any(_is_weak_anchor(a, len(recap_lines)) for a in anchors):
            weak.append(
                {
                    "event_index": idx,
                    "event_name": ev.get("event_name"),
                    "event_class": ev.get("event_class"),
                    "participants": ev.get("participants") or [],
                    "outcomes": ev.get("outcomes") or [],
                }
            )
    if not weak:
        return events_raw, {"repaired": 0, "unresolved": 0, "skipped": 0}, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }

    api_client = DungeonMindApiClient.wrap(client)
    prompt = _build_anchor_repair_user_prompt(
        recap_relative_path=recap_relative_path,
        recap_lines=recap_lines,
        weak_events=weak,
    )
    try:
        api_result = api_client.responses_parse(
            action="session_events_extraction.repair_anchors",
            model=model_id,
            input=[
                {"role": "system", "content": _ANCHOR_REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            text_format=AnchorRepairOutput,
        )
    except Exception:
        return events_raw, {"repaired": 0, "unresolved": len(weak), "skipped": 0}, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }

    parsed: AnchorRepairOutput | None = getattr(api_result.response, "output_parsed", None)
    if parsed is None:
        return events_raw, {"repaired": 0, "unresolved": len(weak), "skipped": 0}, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }

    repaired = 0
    unresolved = 0
    for item in parsed.repairs:
        idx = int(item.event_index)
        if idx < 0 or idx >= len(events_raw):
            unresolved += 1
            continue
        if item.status != "anchored":
            unresolved += 1
            continue
        if item.line_start is None or item.line_end is None:
            unresolved += 1
            continue
        line_start = int(item.line_start)
        line_end = int(item.line_end)
        if line_start < 1 or line_end < line_start or line_end > len(recap_lines):
            unresolved += 1
            continue
        # Strictness: never accept whole-file replacements in repair.
        if line_start == 1 and line_end == len(recap_lines):
            unresolved += 1
            continue
        span_len = line_end - line_start + 1
        if span_len > 12:
            unresolved += 1
            continue

        ev = events_raw[idx]
        original_tokens = _tokenize_for_overlap(_event_text_blob(ev))
        span_tokens = _tokenize_for_overlap(_lines_window_text(recap_lines, line_start, line_end))
        if original_tokens and len(original_tokens & span_tokens) == 0:
            unresolved += 1
            continue

        _, anchor = build_recap_extracted_anchor(
            corpus_source_path=recap_relative_path,
            full_file_lines=recap_lines,
            line_start_1=line_start,
            line_end_1=line_end,
            commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
        )
        ev["source_anchors"] = [anchor.to_json_dict()]
        if item.revised_event_name and item.revised_event_name.strip():
            ev["event_name"] = item.revised_event_name.strip()
        revised_outcomes = [str(x).strip() for x in (item.revised_outcomes or []) if str(x).strip()]
        if revised_outcomes:
            ev["outcomes"] = revised_outcomes
        repaired += 1

    repair_usage = _usage_dict_from_openai_response(api_result.response)
    return events_raw, {"repaired": repaired, "unresolved": unresolved, "skipped": 0}, repair_usage


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------


def run_session_events_extraction(
    *,
    client: Any,
    model_id: str,
    scenario: dict[str, Any],
    corpus_root: Path,
    enable_anchor_repair: bool = True,
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

    pc_identity_hints = load_pc_identity_hints(corpus_root, recap_relative_path, user_message)
    user_prompt = build_user_prompt(user_message, recap_text, pc_identity_hints)
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

    default_anchors = _default_event_source_anchors(recap_relative_path, recap_text)
    events_raw: list[dict[str, Any]] = []
    for ev in parsed.events:
        d = ev.model_dump()
        # Remove evidence_id if empty string (schema allows it to be absent)
        if d.get("evidence_id") == "":
            del d["evidence_id"]
        if not d.get("source_anchors") and default_anchors:
            d["source_anchors"] = list(default_anchors)
        events_raw.append(d)

    repair_stats = {"repaired": 0, "unresolved": 0, "skipped": len(events_raw)}
    repair_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    if enable_anchor_repair:
        events_raw, repair_stats, repair_usage = _repair_weak_event_anchors(
            client=client,
            model_id=model_id,
            recap_relative_path=recap_relative_path,
            recap_text=recap_text,
            events_raw=events_raw,
        )

    usage_first = _usage_dict_from_openai_response(response)
    usage = {
        "input_tokens": int(usage_first["input_tokens"]) + int(repair_usage["input_tokens"]),
        "output_tokens": int(usage_first["output_tokens"]) + int(repair_usage["output_tokens"]),
        "cached_tokens": int(usage_first["cached_tokens"]) + int(repair_usage["cached_tokens"]),
    }
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
    telemetry["anchor_repair"] = repair_stats
    verdict = per_gate_verdict(violations)
    if grading.get("expected_anchored_spans") is not None:
        verdict.setdefault("SE6", "FAIL" if violations.get("se6") else "PASS")
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
        description="Recap-to-events extraction benchmark"
    )
    parser.add_argument("--n", type=int, default=1, help="Cohort size (default: 1)")
    parser.add_argument("--model", type=str, default="", help="Model ID")
    parser.add_argument("--scenario-json", type=Path, default=None)
    parser.add_argument("--runs-root", type=Path, default=None)
    parser.add_argument("--no-writes", action="store_true", help="Skip writing artifacts")
    parser.add_argument(
        "--disable-anchor-repair",
        action="store_true",
        help="Skip LLM re-anchoring pass for weak/default anchors.",
    )
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
            enable_anchor_repair=not bool(args.disable_anchor_repair),
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
