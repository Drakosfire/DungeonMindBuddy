"""Recap-to-events extraction slice: structured event records from a recap.

This runner calls the model once per run with the session recap text and a typed
Pydantic schema, then grades the resulting event records against the gold scenario.
No planner machinery, no corpus writes — pure structured-output extraction.

Pydantic models are defined in this module (do not modify fact_extractor.py).
``EventRecordModel`` matches the stored ``event_record`` enums/fields and adds a required
``recap_evidence_span`` (path + 1-based recap line range). The runner normalizes that span into
``source_anchors`` (hash + ``commit_sha``) before ``event_record.schema.json`` validation.

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

from pydantic import BaseModel, Field, model_validator  # noqa: E402

from src.agent.planner_pricing import usage_cost_usd  # noqa: E402
from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from src.contracts.schema_validation import validate_many  # noqa: E402
from src.ingestion.entity_extractor import _usage_dict_from_openai_response  # noqa: E402
from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha  # noqa: E402
from src.llm.api_client import DungeonMindApiClient  # noqa: E402

from evals.session_events_extraction_vertical_slice.grader import (  # noqa: E402
    RECAP_EVIDENCE_SPAN_MAX_LINES,
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

# Anchor repair: keep user prompt under this size (chars); split weak-event batches if needed.
_ANCHOR_REPAIR_USER_CHAR_BUDGET = 120_000

# Anchor repair: applying model-provided `revised_event_name` / `revised_outcomes` is off by
# default. Span-local len>=4 token-subset checks are necessary but not sufficient: a span can
# mention all tokens while attributing the wrong action to the wrong participant (see
# `tests/test_step1_session_events_run.py` — lexical subset can pass for role/action swaps).
_ANCHOR_REPAIR_APPLY_TEXT_REWRITES = False

# ---------------------------------------------------------------------------
# Pydantic schema — event_record fields + required ``recap_evidence_span``
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


class RecapEvidenceSpan(BaseModel):
    """Inclusive 1-based line span into the numbered **RECAP TEXT** block in the user message."""

    path: str = Field(
        ...,
        min_length=1,
        description="Corpus-relative recap path copied verbatim from the extraction task.",
    )
    line_start: int = Field(..., ge=1)
    line_end: int = Field(..., ge=1)

    @model_validator(mode="after")
    def _ordered_and_bounded(self) -> RecapEvidenceSpan:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be >= line_start")
        if self.line_end - self.line_start + 1 > RECAP_EVIDENCE_SPAN_MAX_LINES:
            raise ValueError(
                f"recap_evidence_span must cover at most {RECAP_EVIDENCE_SPAN_MAX_LINES} lines"
            )
        return self


class EventRecordModel(BaseModel):
    event_name: Optional[str] = None
    event_class: _EventClass
    time_scope: _TimeScope
    certainty: _Certainty
    recap_evidence_span: RecapEvidenceSpan
    participants: list[str] = Field(default_factory=list)
    referenced_slugs: list[str] = Field(default_factory=list)
    location: Optional[str] = None
    outcomes: list[str] = Field(default_factory=list)
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

_SYSTEM_PROMPT = f"""\
You extract **session recap → structured event records** for a tabletop RPG campaign. Your \
north star is **citation-grounded capture**: every event must be **defensible from the recap \
prose** the operator can re-open and verify (path + line span), not from free-floating \
paraphrase. Downstream tooling hashes the **literal bytes** of that line window; your job is to \
choose **inclusive 1-based line numbers** from the **RECAP TEXT** block so the window contains \
the **full sentence or sentences** that express the beat — the same natural idea-units readers \
see in the corpus. **Rich, sentence-complete context beats minimal line count.** Long sentences \
and occasional run-ons are normal: include them whole rather than clipping mid-sentence to save \
lines.

## 1) `recap_evidence_span` — do this first for every event

For **each** event, you MUST emit `recap_evidence_span` with:
- `path`: the **exact** corpus-relative recap path string repeated in the user task (same \
characters as given — copy/paste discipline).
- `line_start`, `line_end`: **inclusive** 1-based indices taken **only** from the **left column** \
of the numbered recap (format `NNNN: body`). These integers are the contract: they must refer \
to real lines in that block.

Hard rules for the span:
- **At most {RECAP_EVIDENCE_SPAN_MAX_LINES} lines** total (`line_end - line_start + 1 <= {RECAP_EVIDENCE_SPAN_MAX_LINES}`).
- **Never** set a span that covers **all** numbered lines when there is more than one line in \
the recap (whole-file spans are rejected).
- **Sentence boundaries:** every sentence you rely on for this event must appear **in full** \
inside the span. Do not set `line_end` so the window cuts off mid-sentence. If a sentence wraps \
across numbered lines, include each of those lines. If one numbered line holds several sentences \
and only one belongs to this event, include at least that full sentence (often the entire line \
is the right choice).
- When several sentences jointly establish one beat, include all of them (still within the line \
cap). Split into separate events if the cap would force a mid-sentence clip.
- The span must **support** the event: concatenate lines `line_start`…`line_end` and treat that \
text as the **only** evidence you are allowed to rely on for who acted and what changed. Every \
slug in `participants[]` must appear in that concatenation via a recognizable surface form \
(slug with underscores as spaces, a distinctive ≥4-letter slug segment, or the recap's own \
spelling if it differs slightly). If you cannot find such a span, **shrink the beat**, **move \
participants to a different event**, or **split** the beat — do not attach actors to prose they \
do not appear in.

You do **not** emit `content_hash` or `commit_sha`; the harness derives them from your lines.

## 2) `participants[]` — slug contract (no exceptions)

When a person in the recap maps to a slug under **Known character slugs** in the user message, \
use that slug **verbatim** in `participants[]`. Never substitute a display name or title.

Wrong vs right shape (generic pattern):
- WRONG: `"participants": ["Mirei"]`  →  RIGHT: `"participants": ["mirei_blackraven"]` \
when that slug is listed.

If no listed slug matches, omit that person from `participants[]` rather than guessing a slug.

## 3) `referenced_slugs[]` — named but non-acting entities

When the recap **names** an entity in connection with a beat but that entity **does not act** \
in the prose you are encoding, put the canonical slug (from the known list when available) in \
`referenced_slugs[]`, not in `participants[]`. Keep `referenced_slugs[]` empty when there is no \
such case. Never duplicate pure actors: acting characters belong in `participants[]` only.

## 4) Referenced-name echo (timeline visibility)

Every slug in `referenced_slugs[]` must also have its **recap surface proper name** appear \
verbatim in at least one `outcomes[]` string for that same event (downstream stages read \
outcomes, not the slug array). Example pattern: if `referenced_slugs` includes `norvik`, an \
outcome must contain `Norvik`, not a paraphrase that drops the name.

## 5) MULTI-PARTICIPANT ROSTER COMPLETENESS (hard rule)

When the recap describes **one** joint action whose subject is an explicit comma-separated list \
of named characters, **every** named character from that list belongs in `participants[]` for \
that event — every named character in that list belongs in `participants[]`. Count names in the \
recap sentence before you emit; do not collapse the roster to "the party" without enumerating \
each slug the recap named.

## 6) `outcomes[]` — searchable vocabulary (secondary to the span)

`outcomes[]` is still the GM-searchable surface. When the recap uses a **specific** class, race, \
weapon, spell, ability, item, place, or proper name inside the span you chose, carry that token \
**verbatim** into at least one outcome for an overlapping-participant event. A `must_preserve`-style \
OR is expressed downstream as `tokenA|tokenB` in grading metadata — you implement the intent by \
preserving whichever recap token actually appears in **your** span.

Each outcome is one concrete sentence; prefer 2–5 per event (more for dense combat or social \
beats). "Concrete" means who did what, with which named tool or effect, and what changed — all \
traceable to the span.

## 7) Taxonomy and hygiene

- `event_class`, `time_scope`, `certainty`: required; use `scene` + `observed` for events told \
as table fact in this session's prose.
- `evidence_id`: set to the same recap path string the task provides.
- Do **not** merge distinct recap beats into one event; do **not** invent beats absent from the \
recap.
- Aim for **10–20** events across combat, social conflict, conversation, discovery, travel, \
ritual, and investigation as the recap warrants.
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


def _format_numbered_recap(recap_text: str) -> str:
    """Prefix each recap line with a 4-digit 1-based line number (same convention as anchor repair)."""
    lines = recap_text.splitlines()
    return "\n".join(f"{i:04d}: {line}" for i, line in enumerate(lines, 1))


def _merge_recap_evidence_span_into_source_anchors(
    d: dict[str, Any],
    *,
    recap_relative_path: str,
    recap_lines: list[str],
    commit_sha: str,
) -> None:
    """Pop ``recap_evidence_span`` from *d* and set ``source_anchors`` when the span is usable.

    Invalid spans are ignored so the runner can fall back to default anchors + repair.
    """
    span = d.pop("recap_evidence_span", None)
    total = len(recap_lines)
    if not isinstance(span, dict):
        return
    try:
        ls = int(span["line_start"])
        le = int(span["line_end"])
    except (KeyError, TypeError, ValueError):
        return
    if ls < 1 or le < ls or le > total:
        return
    if le - ls + 1 > RECAP_EVIDENCE_SPAN_MAX_LINES:
        return
    if total > 1 and ls == 1 and le >= total:
        return
    _, anchor = build_recap_extracted_anchor(
        corpus_source_path=recap_relative_path,
        full_file_lines=recap_lines,
        line_start_1=ls,
        line_end_1=le,
        commit_sha=commit_sha,
    )
    d["source_anchors"] = [anchor.to_json_dict()]


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
    numbered = _format_numbered_recap(recap_text)
    return (
        f"{user_message}{hint_block}\n\n---\n\n"
        "**RECAP TEXT (1-based line numbers in the left column — use only these integers in "
        "each event's ``recap_evidence_span``):**\n\n"
        f"{numbered}"
    )


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


def _distinctive_tokens_subset_of_span(text: str, span_tokens: set[str]) -> bool:
    """True when every len>=4 alphanumeric token in *text* appears in *span_tokens*.

    Used to block anchor-repair rewrites that introduce recap terms absent from the
    model-selected line span. Vacuously true when *text* has no such tokens.
    """
    proposed = _tokenize_for_overlap(text)
    if not proposed:
        return True
    return proposed <= span_tokens


def _apply_revised_event_text_if_supported(
    *,
    item: AnchorRepairItem,
    span_tokens: set[str],
) -> tuple[bool, bool, str | None, list[str]]:
    """Return (apply_name, apply_outcomes, name_or_none, outcomes_or_empty).

    **Not sufficient for trust when used alone:** every len>=4 token in the proposed text
    may still appear in the same span as a *different* actor performing that action. Callers
    that enable `_ANCHOR_REPAIR_APPLY_TEXT_REWRITES` should treat this as a lexical gate only.

    Conservative policy when applied: `revised_event_name` applies only if supported;
    `revised_outcomes` apply only as a full list when *every* non-empty outcome string is
    supported.
    """
    name: str | None = None
    if item.revised_event_name and str(item.revised_event_name).strip():
        name = str(item.revised_event_name).strip()
    revised_outcomes = [str(x).strip() for x in (item.revised_outcomes or []) if str(x).strip()]

    apply_name = bool(name and _distinctive_tokens_subset_of_span(name, span_tokens))
    apply_outcomes = bool(
        revised_outcomes
        and all(_distinctive_tokens_subset_of_span(o, span_tokens) for o in revised_outcomes)
    )
    return apply_name, apply_outcomes, name, revised_outcomes


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


# Slug segments this common are weak evidence on their own (too many false positives in prose).
_GENERIC_SLUG_PARTS = frozenset(
    {
        "captain",
        "lord",
        "lady",
        "general",
        "doctor",
        "sergeant",
        "commander",
        "private",
        "guard",
        "sir",
        "king",
        "queen",
        "prince",
        "princess",
        "the",
    }
)

# Recap prose sometimes spells a PC differently than the canonical hub slug. Anchor repair
# must still tie `participants[]` to the selected line span without reading benchmark gold.
_SLUG_RECAP_SURFACE_ALIASES: dict[str, frozenset[str]] = {
    # Session 20 recap uses "Karesmine" while the slug is `karsemine`.
    "karsemine": frozenset({"karesmine"}),
}


def _participant_slug_surface_forms(slug: str) -> list[str]:
    """Lowercase substrings that may tie a corpus participant slug to recap prose."""
    s = str(slug).strip().lower()
    if not s:
        return []
    forms: list[str] = []
    for candidate in (s, s.replace("_", " ")):
        if candidate and candidate not in forms:
            forms.append(candidate)
    parts = s.split("_")
    if len(parts) >= 2:
        for part in parts:
            if len(part) >= 4 and part not in _GENERIC_SLUG_PARTS and part not in forms:
                forms.append(part)
    for alias in _SLUG_RECAP_SURFACE_ALIASES.get(s, frozenset()):
        if alias and alias not in forms:
            forms.append(alias)
    return forms


def _participant_evidence_in_span(participants: list[str], span_lower: str) -> bool:
    """Fail-closed: every participant slug must have at least one surface form in the span."""
    slugs = [str(p).strip() for p in participants if str(p).strip()]
    if not slugs:
        return True
    for slug in slugs:
        if not any(form in span_lower for form in _participant_slug_surface_forms(slug)):
            return False
    return True


def partition_weak_events_for_anchor_repair_prompt(
    weak_events: list[dict[str, Any]],
    *,
    recap_relative_path: str,
    recap_lines: list[str],
    char_budget: int,
) -> list[list[dict[str, Any]]]:
    """Greedy partition so each batch's full user prompt stays within char_budget."""
    if not weak_events:
        return []
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    def _prompt_for(batch: list[dict[str, Any]]) -> str:
        return _build_anchor_repair_user_prompt(
            recap_relative_path=recap_relative_path,
            recap_lines=recap_lines,
            weak_events=batch,
        )

    for w in weak_events:
        if not current:
            one = _prompt_for([w])
            if len(one) > char_budget:
                chunks.append([w])
                continue
            current = [w]
            continue
        trial = current + [w]
        if len(_prompt_for(trial)) <= char_budget:
            current = trial
        else:
            chunks.append(current)
            one = _prompt_for([w])
            if len(one) > char_budget:
                chunks.append([w])
                current = []
            else:
                current = [w]
    if current:
        chunks.append(current)
    return chunks


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
    chunks = partition_weak_events_for_anchor_repair_prompt(
        weak,
        recap_relative_path=recap_relative_path,
        recap_lines=recap_lines,
        char_budget=_ANCHOR_REPAIR_USER_CHAR_BUDGET,
    )

    repairs_by_index: dict[int, AnchorRepairItem] = {}
    total_in_tokens = 0
    total_out_tokens = 0
    total_cached_tokens = 0
    chunks_failed = 0

    for batch in chunks:
        prompt = _build_anchor_repair_user_prompt(
            recap_relative_path=recap_relative_path,
            recap_lines=recap_lines,
            weak_events=batch,
        )
        api_result = None
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
            chunks_failed += 1
            continue

        parsed: AnchorRepairOutput | None = getattr(api_result.response, "output_parsed", None)
        if parsed is None:
            chunks_failed += 1
            continue

        u = _usage_dict_from_openai_response(api_result.response)
        total_in_tokens += int(u["input_tokens"])
        total_out_tokens += int(u["output_tokens"])
        total_cached_tokens += int(u["cached_tokens"])

        for item in parsed.repairs:
            repairs_by_index[int(item.event_index)] = item

    repaired = 0
    unresolved = 0
    for item in sorted(repairs_by_index.values(), key=lambda x: int(x.event_index)):
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
        # Strictness: never accept whole-file replacements in repair (multi-line recaps only).
        if len(recap_lines) > 1 and line_start == 1 and line_end == len(recap_lines):
            unresolved += 1
            continue
        span_len = line_end - line_start + 1
        if span_len > RECAP_EVIDENCE_SPAN_MAX_LINES:
            unresolved += 1
            continue

        ev = events_raw[idx]
        original_tokens = _tokenize_for_overlap(_event_text_blob(ev))
        span_text = _lines_window_text(recap_lines, line_start, line_end)
        span_lower = span_text.lower()
        span_tokens = _tokenize_for_overlap(span_text)
        if original_tokens and len(original_tokens & span_tokens) == 0:
            unresolved += 1
            continue
        if not _participant_evidence_in_span(list(ev.get("participants") or []), span_lower):
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
        if _ANCHOR_REPAIR_APPLY_TEXT_REWRITES:
            apply_name, apply_outcomes, name, revised_outcomes = (
                _apply_revised_event_text_if_supported(
                    item=item,
                    span_tokens=span_tokens,
                )
            )
            if apply_name and name:
                ev["event_name"] = name
            if apply_outcomes and revised_outcomes:
                ev["outcomes"] = list(revised_outcomes)
        repaired += 1

    # Weak events with no repair row from model count as unresolved.
    weak_indices = {int(w["event_index"]) for w in weak}
    answered = set(repairs_by_index.keys())
    unresolved += len(weak_indices - answered)

    repair_stats: dict[str, int] = {
        "repaired": repaired,
        "unresolved": unresolved,
        "skipped": 0,
    }
    if chunks_failed:
        repair_stats["repair_chunks_failed"] = int(chunks_failed)
    return events_raw, repair_stats, {
        "input_tokens": total_in_tokens,
        "output_tokens": total_out_tokens,
        "cached_tokens": total_cached_tokens,
    }


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
    recap_lines = recap_text.splitlines()
    commit_sha = resolve_git_commit_sha(cwd=_REPO_ROOT)
    events_raw: list[dict[str, Any]] = []
    for ev in parsed.events:
        d = ev.model_dump()
        # Remove evidence_id if empty string (schema allows it to be absent)
        if d.get("evidence_id") == "":
            del d["evidence_id"]
        _merge_recap_evidence_span_into_source_anchors(
            d,
            recap_relative_path=recap_relative_path,
            recap_lines=recap_lines,
            commit_sha=commit_sha,
        )
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

    violations, telemetry = collect_session_events_violations(
        events_raw,
        grading,
        corpus_root=corpus_root,
        recap_relative_path=recap_relative_path,
    )
    telemetry["anchor_repair"] = repair_stats
    verdict = per_gate_verdict(violations)
    if grading.get("expected_anchored_spans") is not None:
        verdict.setdefault("SE6", "FAIL" if violations.get("se6") else "PASS")
    if grading.get("require_verified_event_anchors"):
        verdict.setdefault("SE7", "FAIL" if violations.get("se7") else "PASS")
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
