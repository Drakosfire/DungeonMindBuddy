"""Stage D — GM promotion CLI (propose-only).

Aggregates Stage D proposals across cohort sidecars + per-run sidecars and
flags registry collisions. Default mode is **deterministic-only**: the
deterministic flags (slug_collision, display_name_overlap, pc_collision)
plus raw evidence (descriptors, sessions, event indices) carry every signal
the GM needs for the easy-case promotion review. Pair the JSON sidecar
output with the browser viewer at
``evals/stage_d_entity_resolution_vertical_slice/promotions/viewer.html``.

Pass ``--with-llm`` to additionally call ``gpt-5.4-mini`` for an
accept / reject / defer / merge_into_existing recommendation per proposal.
Useful for hard cases (Kirfan-class coreference, alias-add semantics, or
when the model's judgment is wanted as a sanity check against the GM's).

This script is **propose-only**: it never mutates
``corpus/eldyrwild-markdown/<campaign>/_npc_registry.json``. Output is a
``promotions/<campaign_id>_stage_d_promotion_<ts>.{json,md}`` sidecar that the
GM reviews before any registry edit. Mirrors the propose-only contract of
Stage D itself (``evals/stage_d_entity_resolution_vertical_slice/proposals/``).

Run::

    uv run python -m scripts.promote_stage_d_proposals \\
        --campaign-id longmont-c1 \\
        --proposals "evals/stage_d_entity_resolution_vertical_slice/proposals/longmont-c1_stage_d_proposals_*.json" \\
        --per-run "evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--*c1*--PASS--*.json" \\
        --registry "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json"

Add ``--with-llm`` to enable the model recommendation pass. Final cost is
printed; cost guard warns above $0.50 and aborts above $2.00 per invocation.
The legacy ``--no-llm`` flag is accepted for back-compat (it is now the
default and a no-op).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pydantic import BaseModel, Field  # noqa: E402

from src.contracts.npc_registry import NpcRegistryRecord, load_npc_registry  # noqa: E402

PROMOTION_SCHEMA_VERSION = "stage_d_promotion_v2"
_DEFAULT_OUT_DIR = (
    _REPO_ROOT / "evals" / "stage_d_entity_resolution_vertical_slice" / "promotions"
)
_PROMOTION_ACTION = "stage_d_promotion_judgment"

# Defensive PC slug net (mirrors Stage D ER2). Stage D's ER2 gate already
# blocks PC-name leaks; this set only fires the ``pc_collision`` flag if the
# upstream gate ever regresses. Unioned across the Longmont C1/C2 gold rosters
# checked in at ``evals/stage_d_entity_resolution_vertical_slice/gold/``.
_LONGMONT_PC_SLUGS: set[str] = {
    "bonogo",
    "caelynn",
    "ephanna",
    "karsemine",
    "stafl",
    "baergrom",
}


def _resolve_promotion_model(model: str | None) -> str:
    """Resolve the judgment model id from MODEL_POLICY.json (action ``corpus_session_planner``).

    Falls back to ``gpt-5.4-mini`` if the policy file is missing or malformed,
    matching ``src/agent/planner._resolve_planner_model``.
    """
    if model and str(model).strip():
        return str(model).strip()
    candidates = [
        _REPO_ROOT / "MODEL_POLICY.json",
        _REPO_ROOT.parent / "MODEL_POLICY.json",
    ]
    for policy_path in candidates:
        if not policy_path.is_file():
            continue
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        role = policy.get("actions", {}).get("corpus_session_planner")
        if not role:
            continue
        mid = policy.get("models", {}).get(str(role))
        if isinstance(mid, str) and mid.strip():
            return mid.strip()
    return "gpt-5.4-mini"


# --------------------------------------------------------------------------- #
# Pydantic structured-output shapes for the LLM judgment turn
# --------------------------------------------------------------------------- #


class PromotePayload(BaseModel):
    """Final NpcRegistryRecord-shaped payload for an accepted new candidate.

    Mirrors :class:`src.contracts.npc_registry.NpcRegistryRecord` but with
    every field required so OpenAI structured outputs (strict JSON Schema)
    accepts it. Status MUST be ``candidate`` and hub_path MUST be null per
    Stage D's propose-only contract.
    """

    slug: str
    display_name: str
    aliases: list[str]
    status: str = Field(description="Must equal 'candidate' (Stage D contract).")
    first_session: int
    last_session: int
    hub_path: Optional[str] = Field(
        default=None,
        description="Must be null for status='candidate'.",
    )
    setting_hub_path: Optional[str] = None
    notes: str


class ModelPromotionRecommendation(BaseModel):
    """LLM judgment for one ``proposed_new_records[]`` entry."""

    recommendation: str = Field(
        description=(
            "One of: accept, reject, defer_to_gm, merge_into_existing."
        )
    )
    confidence: str = Field(description="One of: high, medium, low.")
    rationale: str = Field(description="1-3 sentence justification.")
    promote_payload: Optional[PromotePayload] = None
    merge_target_slug: Optional[str] = None


class ModelAliasRecommendation(BaseModel):
    """LLM judgment for one ``proposed_aliases[]`` entry."""

    recommendation: str = Field(description="One of: accept, reject, defer_to_gm.")
    confidence: str = Field(description="One of: high, medium, low.")
    rationale: str


class ModelUnresolvableRecommendation(BaseModel):
    """LLM judgment for one ``unresolvable[]`` entry (advisory)."""

    recommendation: str = Field(
        description=(
            "One of: leave_unresolvable, propose_canonical, defer_to_gm."
        )
    )
    confidence: str = Field(description="One of: high, medium, low.")
    rationale: str
    proposed_canonical_slug: Optional[str] = None


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


@dataclass
class EvidenceRow:
    scenario_id: str
    session_number: Optional[int]
    descriptors_seen: list[str]
    evidence_event_indices: list[int]
    source_file: str
    # Resolved event records for the indices above, when the cohort proposals
    # file embedded `source_events`. Empty when reading legacy proposals or
    # per-run sidecars that don't carry events through.
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AggregatedNewRecord:
    slug: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    first_session: Optional[int] = None
    last_session: Optional[int] = None
    proposed_campaign_hub_path: Optional[str] = None
    proposed_setting_hub_path: Optional[str] = None
    proposed_location_slug: Optional[str] = None
    proposed_divergence_mode: Optional[str] = None
    evidence: list[EvidenceRow] = field(default_factory=list)
    appearance_runs: int = 0
    session_appearances: list[int] = field(default_factory=list)


@dataclass
class AggregatedAlias:
    target_slug: str
    alias_text: str
    evidence: list[EvidenceRow] = field(default_factory=list)
    appearance_runs: int = 0


@dataclass
class AggregatedUnresolvable:
    descriptor: str
    evidence: list[EvidenceRow] = field(default_factory=list)
    appearance_runs: int = 0
    sample_reason: str = ""


@dataclass
class AggregationResult:
    new_records: dict[str, AggregatedNewRecord]
    aliases: dict[tuple[str, str], AggregatedAlias]
    unresolvables: dict[str, AggregatedUnresolvable]
    sources_seen: list[str]


def _expand_glob(pattern: str | None, repo_root: Path) -> list[Path]:
    """Resolve ``pattern`` via ``Path.glob`` rooted at the repo root.

    Empty / absent patterns return an empty list so either ``--proposals`` or
    ``--per-run`` may be omitted without erroring.
    """
    if not pattern or not str(pattern).strip():
        return []
    p = str(pattern).strip()
    if "*" in p or "?" in p or "[" in p:
        return sorted(repo_root.glob(p))
    candidate = (repo_root / p).resolve()
    if not candidate.exists():
        return []
    return [candidate]


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_descriptors_from_notes(notes: Any) -> list[str]:
    """Pull the descriptor text out of Stage D's note string when present.

    Stage D notes look like:
        "Proposed by Stage D deterministic v0; descriptor 'Foo'; evidence event indices [1, 2]."
    """
    if not isinstance(notes, str):
        return []
    descriptors: list[str] = []
    marker = "descriptor '"
    cursor = 0
    while True:
        idx = notes.find(marker, cursor)
        if idx == -1:
            break
        start = idx + len(marker)
        end = notes.find("'", start)
        if end == -1:
            break
        descriptors.append(notes[start:end])
        cursor = end + 1
    return descriptors


def _extract_event_indices_from_notes(notes: Any) -> list[int]:
    if not isinstance(notes, str):
        return []
    marker = "evidence event indices ["
    idx = notes.find(marker)
    if idx == -1:
        return []
    start = idx + len(marker)
    end = notes.find("]", start)
    if end == -1:
        return []
    raw = notes[start:end]
    out: list[int] = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(int(tok))
        except ValueError:
            continue
    return out


def _resolve_events(
    indices: list[int],
    event_lookup: dict[int, dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Look up event records for `indices` against an event lookup map.

    Returns an empty list when the cohort/per-run source did not embed
    `source_events`, so legacy artefacts gracefully degrade to indices-only.
    """
    if not indices or not event_lookup:
        return []
    out: list[dict[str, Any]] = []
    for i in indices:
        ev = event_lookup.get(int(i))
        if isinstance(ev, dict):
            out.append({"event_index": int(i), **ev})
    return out


def _ingest_record(
    *,
    rec: dict[str, Any],
    scenario_id: str,
    session_number: Optional[int],
    source_file: str,
    aggregated: dict[str, AggregatedNewRecord],
    event_lookup: dict[int, dict[str, Any]] | None = None,
) -> None:
    slug = str(rec.get("slug") or "").strip().lower()
    if not slug:
        return
    existing = aggregated.get(slug)
    descriptors = _extract_descriptors_from_notes(rec.get("notes"))
    evidence_indices = _extract_event_indices_from_notes(rec.get("notes"))
    first = _safe_int(rec.get("first_session"))
    last = _safe_int(rec.get("last_session"))
    display = str(rec.get("display_name") or "").strip()
    aliases_in = [a for a in (rec.get("aliases") or []) if isinstance(a, str) and a]
    proposed_campaign_hub_path = rec.get("proposed_campaign_hub_path")
    proposed_setting_hub_path = rec.get("proposed_setting_hub_path")
    proposed_location_slug = rec.get("proposed_location_slug")
    proposed_divergence_mode = rec.get("proposed_divergence_mode")
    if existing is None:
        existing = AggregatedNewRecord(
            slug=slug,
            display_name=display,
            aliases=list(aliases_in),
            first_session=first,
            last_session=last,
            proposed_campaign_hub_path=(
                str(proposed_campaign_hub_path)
                if isinstance(proposed_campaign_hub_path, str) and proposed_campaign_hub_path.strip()
                else None
            ),
            proposed_setting_hub_path=(
                str(proposed_setting_hub_path)
                if isinstance(proposed_setting_hub_path, str) and proposed_setting_hub_path.strip()
                else None
            ),
            proposed_location_slug=(
                str(proposed_location_slug)
                if isinstance(proposed_location_slug, str) and proposed_location_slug.strip()
                else None
            ),
            proposed_divergence_mode=(
                str(proposed_divergence_mode)
                if isinstance(proposed_divergence_mode, str) and proposed_divergence_mode.strip()
                else None
            ),
            session_appearances=[session_number] if session_number is not None else [],
        )
        aggregated[slug] = existing
    else:
        if not existing.display_name and display:
            existing.display_name = display
        for a in aliases_in:
            if a not in existing.aliases:
                existing.aliases.append(a)
        if first is not None:
            existing.first_session = (
                first if existing.first_session is None else min(existing.first_session, first)
            )
        if last is not None:
            existing.last_session = (
                last if existing.last_session is None else max(existing.last_session, last)
            )
        if session_number is not None and session_number not in existing.session_appearances:
            existing.session_appearances.append(session_number)
        if (
            existing.proposed_campaign_hub_path is None
            and isinstance(proposed_campaign_hub_path, str)
            and proposed_campaign_hub_path.strip()
        ):
            existing.proposed_campaign_hub_path = proposed_campaign_hub_path
        if (
            existing.proposed_setting_hub_path is None
            and isinstance(proposed_setting_hub_path, str)
            and proposed_setting_hub_path.strip()
        ):
            existing.proposed_setting_hub_path = proposed_setting_hub_path
        if (
            existing.proposed_location_slug is None
            and isinstance(proposed_location_slug, str)
            and proposed_location_slug.strip()
        ):
            existing.proposed_location_slug = proposed_location_slug
        if (
            existing.proposed_divergence_mode is None
            and isinstance(proposed_divergence_mode, str)
            and proposed_divergence_mode.strip()
        ):
            existing.proposed_divergence_mode = proposed_divergence_mode
    existing.evidence.append(
        EvidenceRow(
            scenario_id=scenario_id,
            session_number=session_number,
            descriptors_seen=descriptors,
            evidence_event_indices=evidence_indices,
            source_file=source_file,
            events=_resolve_events(evidence_indices, event_lookup),
        )
    )
    existing.appearance_runs += 1


def _ingest_alias(
    *,
    rec: dict[str, Any],
    scenario_id: str,
    session_number: Optional[int],
    source_file: str,
    aggregated: dict[tuple[str, str], AggregatedAlias],
    event_lookup: dict[int, dict[str, Any]] | None = None,
) -> None:
    target = str(rec.get("target_slug") or "").strip().lower()
    text = str(rec.get("alias_text") or "").strip()
    if not target or not text:
        return
    key = (target, text.lower())
    existing = aggregated.get(key)
    if existing is None:
        existing = AggregatedAlias(target_slug=target, alias_text=text)
        aggregated[key] = existing
    existing.evidence.append(
        EvidenceRow(
            scenario_id=scenario_id,
            session_number=session_number,
            descriptors_seen=[],
            evidence_event_indices=[],
            source_file=source_file,
            events=[],
        )
    )
    existing.appearance_runs += 1


def _ingest_unresolvable(
    *,
    rec: dict[str, Any],
    scenario_id: str,
    session_number: Optional[int],
    source_file: str,
    aggregated: dict[str, AggregatedUnresolvable],
    event_lookup: dict[int, dict[str, Any]] | None = None,
) -> None:
    desc = str(rec.get("descriptor") or "").strip()
    if not desc:
        return
    key = desc.lower()
    existing = aggregated.get(key)
    if existing is None:
        existing = AggregatedUnresolvable(
            descriptor=desc,
            sample_reason=str(rec.get("reason") or rec.get("sample_reason") or "").strip(),
        )
        aggregated[key] = existing
    # Unresolvables track the descriptor itself, but Stage D's deterministic
    # output also encodes the originating event indices in the unresolvable's
    # `reason` text on some paths. We extract them when present so the GM can
    # still see the source events.
    indices = _extract_event_indices_from_notes(rec.get("reason"))
    existing.evidence.append(
        EvidenceRow(
            scenario_id=scenario_id,
            session_number=session_number,
            descriptors_seen=[],
            evidence_event_indices=indices,
            source_file=source_file,
            events=_resolve_events(indices, event_lookup),
        )
    )
    existing.appearance_runs += 1


def _session_number_from_scenario(scenario_id: str) -> Optional[int]:
    """Best-effort extraction of session number from a scenario_id string.

    Stage D scenario ids look like ``stage_d_live_from_c_session3_c1`` or
    ``stage_d_session20``. Pulls the int after ``session``.
    """
    if not scenario_id:
        return None
    s = scenario_id.lower()
    marker = "session"
    idx = s.find(marker)
    if idx == -1:
        return None
    cursor = idx + len(marker)
    digits: list[str] = []
    while cursor < len(s) and s[cursor].isdigit():
        digits.append(s[cursor])
        cursor += 1
    if not digits:
        return None
    try:
        return int("".join(digits))
    except ValueError:
        return None


def aggregate_sources(
    *,
    cohort_paths: list[Path],
    per_run_paths: list[Path],
) -> AggregationResult:
    """Walk cohort proposals files + per-run sidecars and aggregate by slug."""
    new_records: dict[str, AggregatedNewRecord] = {}
    aliases: dict[tuple[str, str], AggregatedAlias] = {}
    unresolvables: dict[str, AggregatedUnresolvable] = {}
    sources_seen: list[str] = []

    for path in cohort_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sources_seen.append(str(path))
        scenario_id = str(payload.get("scenario_id") or "")
        session_number = _session_number_from_scenario(scenario_id)
        # Build the index → event lookup for this cohort. Cohort proposals
        # written by stage_d_run_report >= v0.2 embed `source_events` for
        # exactly this purpose; older files still aggregate fine.
        source_events = payload.get("source_events") or []
        event_lookup: dict[int, dict[str, Any]] = {}
        if isinstance(source_events, list):
            for i, ev in enumerate(source_events):
                if isinstance(ev, dict):
                    event_lookup[i] = ev
        for rec in payload.get("proposed_records") or []:
            if isinstance(rec, dict):
                _ingest_record(
                    rec=rec,
                    scenario_id=scenario_id,
                    session_number=session_number,
                    source_file=str(path),
                    aggregated=new_records,
                    event_lookup=event_lookup,
                )
        for rec in payload.get("proposed_aliases") or []:
            if isinstance(rec, dict):
                _ingest_alias(
                    rec=rec,
                    scenario_id=scenario_id,
                    session_number=session_number,
                    source_file=str(path),
                    aggregated=aliases,
                    event_lookup=event_lookup,
                )
        for rec in payload.get("unresolvable") or []:
            if isinstance(rec, dict):
                _ingest_unresolvable(
                    rec=rec,
                    scenario_id=scenario_id,
                    session_number=session_number,
                    source_file=str(path),
                    aggregated=unresolvables,
                    event_lookup=event_lookup,
                )

    for path in per_run_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sources_seen.append(str(path))
        scenario_id = str(payload.get("scenario_id") or "")
        session_number = _session_number_from_scenario(scenario_id)
        out = payload.get("stage_d_output") or {}
        # Per-run sidecars don't currently embed events; legacy degrade.
        event_lookup = {}
        for rec in out.get("proposed_new_records") or []:
            if isinstance(rec, dict):
                _ingest_record(
                    rec=rec,
                    scenario_id=scenario_id,
                    session_number=session_number,
                    source_file=str(path),
                    aggregated=new_records,
                    event_lookup=event_lookup,
                )
        for rec in out.get("proposed_aliases") or []:
            if isinstance(rec, dict):
                _ingest_alias(
                    rec=rec,
                    scenario_id=scenario_id,
                    session_number=session_number,
                    source_file=str(path),
                    aggregated=aliases,
                    event_lookup=event_lookup,
                )
        for rec in out.get("unresolvable") or []:
            if isinstance(rec, dict):
                _ingest_unresolvable(
                    rec=rec,
                    scenario_id=scenario_id,
                    session_number=session_number,
                    source_file=str(path),
                    aggregated=unresolvables,
                    event_lookup=event_lookup,
                )

    return AggregationResult(
        new_records=new_records,
        aliases=aliases,
        unresolvables=unresolvables,
        sources_seen=sources_seen,
    )


# --------------------------------------------------------------------------- #
# Registry collision check
# --------------------------------------------------------------------------- #


def collision_flags_for_slug(
    *,
    slug: str,
    display_name: str,
    aliases: list[str],
    registry: list[NpcRegistryRecord],
    pc_slugs: set[str],
) -> dict[str, Any]:
    """Compute slug_collision / display_name_overlap / pc_collision flags."""
    flags: dict[str, Any] = {
        "slug_collision": False,
        "display_name_overlap": None,
        "pc_collision": False,
    }
    s_lc = slug.lower()
    if s_lc in pc_slugs:
        flags["pc_collision"] = True
    for rec in registry:
        if rec.slug.lower() == s_lc:
            flags["slug_collision"] = True
            break
    cand_terms = [display_name.lower()] if display_name else []
    cand_terms.extend(a.lower() for a in aliases if a)
    for rec in registry:
        haystack = [rec.display_name.lower()] + [a.lower() for a in rec.aliases]
        for needle in cand_terms:
            if not needle:
                continue
            for hay in haystack:
                if hay and (needle in hay or hay in needle):
                    flags["display_name_overlap"] = rec.slug
                    return flags
    return flags


def collision_flags_for_alias(
    *,
    target_slug: str,
    alias_text: str,
    registry: list[NpcRegistryRecord],
) -> dict[str, Any]:
    flags: dict[str, Any] = {
        "target_exists": False,
        "alias_already_present": False,
    }
    tgt_lc = target_slug.lower()
    a_lc = alias_text.lower().strip()
    for rec in registry:
        if rec.slug.lower() == tgt_lc:
            flags["target_exists"] = True
            present = {x.lower() for x in rec.aliases}
            if a_lc in present or a_lc == rec.display_name.lower():
                flags["alias_already_present"] = True
            break
    return flags


# --------------------------------------------------------------------------- #
# LLM judgment turn
# --------------------------------------------------------------------------- #


_PROMOTION_SYSTEM_PROMPT = """You are an editorial assistant helping a tabletop RPG GM
review NPC entity-resolution proposals before they are promoted into a curated
campaign registry. The pipeline (Stage D) already routed each item via
deterministic heuristics; your job is to give a per-slug recommendation the GM
can act on.

CONSTRAINTS (these are HARD rules — never violate):
- Status of any accepted proposal MUST be exactly the string "candidate".
- hub_path of any accepted proposal MUST be null. The GM authors hubs by hand later.
- Never propose a slug that collides with an existing registry slug. If a
  proposal's slug already exists, recommend "merge_into_existing" with the
  colliding slug as merge_target_slug, OR "defer_to_gm".
- Never propose a slug that matches a PC roster slug.
- Be conservative. When in doubt, prefer "defer_to_gm" over "accept".

RECOMMENDATION VOCABULARY:
- accept: clear, single-entity, no collision, evidence sufficient.
- reject: looks like noise (fragment, generic descriptor, mis-extracted).
- defer_to_gm: ambiguous, partial evidence, name shape unclear, or unsure
  whether it duplicates an existing entity by a different slug.
- merge_into_existing: this slug is a variant of an existing registry slug;
  give the merge target.

CONFIDENCE: high / medium / low — your subjective certainty in the recommendation.

RATIONALE: 1-3 sentences. Cite the evidence (sessions seen, descriptors,
event indices) when relevant.
""".strip()


_ALIAS_SYSTEM_PROMPT = """You are an editorial assistant reviewing proposed alias
additions to existing NPC registry records. Each item proposes attaching an
alias string to a target slug. The GM will accept, reject, or defer.

Recommend "accept" only if the alias is clearly a real-world reference to the
target NPC (not a generic descriptor that could match many entities). Prefer
"defer_to_gm" when uncertain. Use 1-3 sentences for rationale.
""".strip()


_UNRESOLVABLE_SYSTEM_PROMPT = """You are an editorial assistant reviewing
descriptors Stage D's deterministic v0 declined to resolve. These are usually
generic creature descriptions ("the elderly fisherman", "flaming spider
monstrosity") that the GM may either leave alone or canonicalize into a
specific slug. Your recommendation is ADVISORY — Stage D v0 punted on these
and the GM gets the final call.

Use "propose_canonical" only when there is strong evidence (the descriptor
references a specific named entity already in the registry). Otherwise prefer
"leave_unresolvable" or "defer_to_gm". Use 1-3 sentences for rationale.
""".strip()


def _registry_siblings_for_prompt(
    registry: list[NpcRegistryRecord], cap: int = 30
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rec in registry[:cap]:
        out.append(
            {
                "slug": rec.slug,
                "display_name": rec.display_name,
                "aliases": list(rec.aliases),
                "status": rec.status,
            }
        )
    return out


def _evidence_for_prompt(rows: list[EvidenceRow]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "scenario_id": row.scenario_id,
                "session_number": row.session_number,
                "descriptors_seen": list(row.descriptors_seen),
                "evidence_event_indices": list(row.evidence_event_indices),
            }
        )
    return out


def _usage_dict_from_response(response: Any) -> dict[str, int]:
    usage_raw = getattr(response, "usage", None)
    if not usage_raw:
        return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    details = getattr(usage_raw, "input_tokens_details", None)
    cached = 0
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    return {
        "input_tokens": int(getattr(usage_raw, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage_raw, "output_tokens", 0) or 0),
        "cached_tokens": cached,
    }


@dataclass
class CostTally:
    total_usd: float = 0.0
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


def _add_usage(
    tally: CostTally,
    *,
    model: str,
    usage: dict[str, int],
) -> None:
    from src.agent.planner_pricing import usage_cost_usd

    cost = usage_cost_usd(
        model_id=model,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
    )
    tally.total_usd += float(cost["total_usd"])
    tally.calls += 1
    tally.input_tokens += usage["input_tokens"]
    tally.output_tokens += usage["output_tokens"]
    tally.cached_tokens += usage["cached_tokens"]


def _judge_new_record(
    *,
    api_client: Any,
    model: str,
    record: AggregatedNewRecord,
    flags: dict[str, Any],
    registry_siblings: list[dict[str, Any]],
    pc_slugs: list[str],
    tally: CostTally,
) -> tuple[ModelPromotionRecommendation, dict[str, int]]:
    payload = {
        "slug": record.slug,
        "display_name": record.display_name,
        "aliases": record.aliases,
        "first_session": record.first_session,
        "last_session": record.last_session,
        "appearance_runs": record.appearance_runs,
        "session_appearances": record.session_appearances,
        "evidence": _evidence_for_prompt(record.evidence),
        "registry_collision_flags": flags,
        "registry_siblings_sample": registry_siblings,
        "pc_roster_slugs": sorted(pc_slugs),
    }
    user_prompt = (
        "Review this Stage D proposed_new_record and emit a structured "
        "recommendation.\n\n"
        f"Proposal:\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n"
    )
    result = api_client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": _PROMOTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        text_format=ModelPromotionRecommendation,
    )
    parsed = getattr(result, "output_parsed", None)
    if parsed is None:
        raise ValueError("OpenAI response did not return output_parsed (new_record judgment).")
    if not isinstance(parsed, ModelPromotionRecommendation):
        parsed = ModelPromotionRecommendation.model_validate(parsed)
    usage = _usage_dict_from_response(result)
    _add_usage(tally, model=model, usage=usage)
    return parsed, usage


def _judge_alias(
    *,
    api_client: Any,
    model: str,
    alias: AggregatedAlias,
    flags: dict[str, Any],
    registry_siblings: list[dict[str, Any]],
    tally: CostTally,
) -> tuple[ModelAliasRecommendation, dict[str, int]]:
    payload = {
        "target_slug": alias.target_slug,
        "alias_text": alias.alias_text,
        "appearance_runs": alias.appearance_runs,
        "evidence": _evidence_for_prompt(alias.evidence),
        "registry_flags": flags,
        "registry_siblings_sample": registry_siblings,
    }
    user_prompt = (
        "Review this Stage D proposed_alias and emit a structured recommendation.\n\n"
        f"Proposal:\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n"
    )
    result = api_client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": _ALIAS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        text_format=ModelAliasRecommendation,
    )
    parsed = getattr(result, "output_parsed", None)
    if parsed is None:
        raise ValueError("OpenAI response did not return output_parsed (alias judgment).")
    if not isinstance(parsed, ModelAliasRecommendation):
        parsed = ModelAliasRecommendation.model_validate(parsed)
    usage = _usage_dict_from_response(result)
    _add_usage(tally, model=model, usage=usage)
    return parsed, usage


def _judge_unresolvable(
    *,
    api_client: Any,
    model: str,
    item: AggregatedUnresolvable,
    registry_siblings: list[dict[str, Any]],
    tally: CostTally,
) -> tuple[ModelUnresolvableRecommendation, dict[str, int]]:
    payload = {
        "descriptor": item.descriptor,
        "sample_reason": item.sample_reason,
        "appearance_runs": item.appearance_runs,
        "evidence": _evidence_for_prompt(item.evidence),
        "registry_siblings_sample": registry_siblings,
    }
    user_prompt = (
        "Review this Stage D unresolvable item and emit a structured recommendation.\n\n"
        f"Item:\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n"
    )
    result = api_client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": _UNRESOLVABLE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        text_format=ModelUnresolvableRecommendation,
    )
    parsed = getattr(result, "output_parsed", None)
    if parsed is None:
        raise ValueError(
            "OpenAI response did not return output_parsed (unresolvable judgment)."
        )
    if not isinstance(parsed, ModelUnresolvableRecommendation):
        parsed = ModelUnresolvableRecommendation.model_validate(parsed)
    usage = _usage_dict_from_response(result)
    _add_usage(tally, model=model, usage=usage)
    return parsed, usage


# --------------------------------------------------------------------------- #
# Sidecar serialisation
# --------------------------------------------------------------------------- #


def _serialise_evidence(rows: list[EvidenceRow]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "scenario_id": row.scenario_id,
                "session_number": row.session_number,
                "descriptors_seen": list(row.descriptors_seen),
                "evidence_event_indices": list(row.evidence_event_indices),
                "source_file": row.source_file,
                # Resolved event records, when the cohort proposals file
                # carried `source_events`. Empty for legacy/per-run sources.
                "events": [dict(e) for e in (row.events or [])],
            }
        )
    return out


def _build_promotion_payload(
    *,
    campaign_id: str,
    aggregated: AggregationResult,
    registry: list[NpcRegistryRecord],
    pc_slugs: set[str],
    new_record_recs: dict[str, dict[str, Any]],
    alias_recs: dict[tuple[str, str], dict[str, Any]],
    unresolvable_recs: dict[str, dict[str, Any]],
    model_id: str,
    use_llm: bool,
    cost_tally: CostTally,
    when: datetime,
) -> dict[str, Any]:
    new_rows: list[dict[str, Any]] = []
    for slug, rec in sorted(aggregated.new_records.items(), key=lambda kv: kv[0]):
        flags = collision_flags_for_slug(
            slug=rec.slug,
            display_name=rec.display_name,
            aliases=rec.aliases,
            registry=registry,
            pc_slugs=pc_slugs,
        )
        row = {
            "slug": rec.slug,
            "display_name": rec.display_name,
            "aliases": list(rec.aliases),
            "first_session": rec.first_session,
            "last_session": rec.last_session,
            "proposed_campaign_hub_path": rec.proposed_campaign_hub_path,
            "proposed_setting_hub_path": rec.proposed_setting_hub_path,
            "proposed_location_slug": rec.proposed_location_slug,
            "proposed_divergence_mode": rec.proposed_divergence_mode,
            "appearance_runs": rec.appearance_runs,
            "session_appearances": sorted(rec.session_appearances),
            "registry_collision_flags": flags,
            "evidence": _serialise_evidence(rec.evidence),
            "recommendation_source": (
                "llm" if use_llm and slug in new_record_recs else "deterministic_only"
            ),
        }
        if use_llm and slug in new_record_recs:
            row.update(new_record_recs[slug])
        else:
            row["recommendation"] = None
            row["confidence"] = None
            row["rationale"] = None
        new_rows.append(row)

    alias_rows: list[dict[str, Any]] = []
    for key in sorted(aggregated.aliases.keys()):
        alias = aggregated.aliases[key]
        flags = collision_flags_for_alias(
            target_slug=alias.target_slug,
            alias_text=alias.alias_text,
            registry=registry,
        )
        row = {
            "target_slug": alias.target_slug,
            "alias_text": alias.alias_text,
            "appearance_runs": alias.appearance_runs,
            "registry_flags": flags,
            "evidence": _serialise_evidence(alias.evidence),
            "recommendation_source": (
                "llm" if use_llm and key in alias_recs else "deterministic_only"
            ),
        }
        if use_llm and key in alias_recs:
            row.update(alias_recs[key])
        else:
            row["recommendation"] = None
            row["confidence"] = None
            row["rationale"] = None
        alias_rows.append(row)

    unresolvable_rows: list[dict[str, Any]] = []
    for desc_key in sorted(aggregated.unresolvables.keys()):
        item = aggregated.unresolvables[desc_key]
        row = {
            "descriptor": item.descriptor,
            "sample_reason": item.sample_reason,
            "appearance_runs": item.appearance_runs,
            "evidence": _serialise_evidence(item.evidence),
            "recommendation_source": (
                "llm" if use_llm and desc_key in unresolvable_recs else "deterministic_only"
            ),
        }
        if use_llm and desc_key in unresolvable_recs:
            row.update(unresolvable_recs[desc_key])
        else:
            row["recommendation"] = None
            row["confidence"] = None
            row["rationale"] = None
            row["proposed_canonical_slug"] = None
        unresolvable_rows.append(row)

    branch_scaffold_proposals: list[dict[str, Any]] = []
    for row in new_rows:
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        campaign_hub = row.get("proposed_campaign_hub_path")
        setting_hub = row.get("proposed_setting_hub_path")
        location_slug = row.get("proposed_location_slug")
        divergence = row.get("proposed_divergence_mode")
        branch_scaffold_proposals.append(
            {
                "slug": slug,
                "display_name": row.get("display_name"),
                "location_slug": location_slug,
                "divergence_mode": divergence,
                "world_parent_hub_path": setting_hub,
                "campaign_overlay_hub_path": campaign_hub,
                "recommended_files": [
                    p
                    for p in [
                        f"{campaign_hub}README.md" if isinstance(campaign_hub, str) and campaign_hub else None,
                        f"{campaign_hub}timeline.md" if isinstance(campaign_hub, str) and campaign_hub else None,
                        f"{campaign_hub}{slug}_character_dossier.md"
                        if isinstance(campaign_hub, str) and campaign_hub
                        else None,
                    ]
                    if p is not None
                ],
            }
        )

    return {
        "schema": PROMOTION_SCHEMA_VERSION,
        "generated_at": when.isoformat(),
        "campaign_id": campaign_id,
        "model_id": model_id if use_llm else None,
        "llm_enabled": bool(use_llm),
        "cost": {
            "total_usd": round(cost_tally.total_usd, 6),
            "calls": cost_tally.calls,
            "input_tokens": cost_tally.input_tokens,
            "output_tokens": cost_tally.output_tokens,
            "cached_tokens": cost_tally.cached_tokens,
        },
        "sources": list(aggregated.sources_seen),
        "registry_size": len(registry),
        "proposed_new_records": new_rows,
        "proposed_aliases": alias_rows,
        "unresolvable": unresolvable_rows,
        "branch_scaffold_proposals": branch_scaffold_proposals,
    }


def _flag_summary_for_md(flags: dict[str, Any]) -> str:
    parts: list[str] = []
    if flags.get("slug_collision"):
        parts.append("slug_collision")
    if flags.get("display_name_overlap"):
        parts.append(f"name_overlap→{flags['display_name_overlap']}")
    if flags.get("pc_collision"):
        parts.append("pc_collision")
    return ", ".join(parts) if parts else "none"


def _alias_flag_summary_for_md(flags: dict[str, Any]) -> str:
    parts: list[str] = []
    if not flags.get("target_exists"):
        parts.append("target_missing")
    if flags.get("alias_already_present"):
        parts.append("already_present")
    return ", ".join(parts) if parts else "ok"


def _evidence_summary(rows: list[dict[str, Any]] | list[EvidenceRow]) -> str:
    """One-line evidence summary for a markdown table cell."""
    sessions: list[Any] = []
    descriptors: list[str] = []
    for row in rows:
        if isinstance(row, EvidenceRow):
            if row.session_number is not None:
                sessions.append(row.session_number)
            descriptors.extend(row.descriptors_seen)
        else:
            sn = row.get("session_number")
            if sn is not None:
                sessions.append(sn)
            descriptors.extend(row.get("descriptors_seen") or [])
    uniq_sessions = sorted({s for s in sessions if s is not None})
    uniq_desc = []
    seen: set[str] = set()
    for d in descriptors:
        if d not in seen:
            seen.add(d)
            uniq_desc.append(d)
    parts: list[str] = []
    if uniq_sessions:
        parts.append(f"sessions={uniq_sessions}")
    if uniq_desc:
        parts.append(f"descriptors={uniq_desc}")
    return "; ".join(parts) if parts else "(none)"


def _md_escape(text: Any) -> str:
    s = "" if text is None else str(text)
    return s.replace("\n", " ").replace("|", "\\|").strip()


def _build_promotion_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    iso = payload.get("generated_at", "")
    campaign = payload.get("campaign_id", "")
    model = payload.get("model_id") or "(deterministic_only)"
    cost = payload.get("cost", {})
    lines.append(
        f"<!-- benchmark_artifact: {payload.get('schema')} | iso_utc: {iso} "
        f"| campaign: {campaign} | model: {model} "
        f"| cost_usd: {cost.get('total_usd', 0)} -->"
    )
    lines.append("")
    lines.append(f"# Stage D promotion review — {campaign}")
    lines.append("")
    lines.append(f"- **generated_at:** `{iso}`")
    lines.append(f"- **model:** `{model}`")
    lines.append(f"- **llm_enabled:** {payload.get('llm_enabled')}")
    lines.append(
        f"- **cost:** ${cost.get('total_usd', 0):.4f} USD over "
        f"{cost.get('calls', 0)} call(s)"
    )
    lines.append(f"- **sources:** {len(payload.get('sources') or [])} file(s)")
    lines.append(f"- **registry size at review:** {payload.get('registry_size', 0)}")
    lines.append("")

    new_rows = payload.get("proposed_new_records") or []
    lines.append(f"## proposed_new_records ({len(new_rows)})")
    lines.append("")
    if new_rows:
        lines.append(
            "| slug | recommendation | confidence | rationale | evidence | flags |"
        )
        lines.append("|---|---|---|---|---|---|")
        for row in new_rows:
            lines.append(
                "| `{slug}` | {rec} | {conf} | {rat} | {ev} | {fl} |".format(
                    slug=_md_escape(row.get("slug")),
                    rec=_md_escape(row.get("recommendation") or "(none)"),
                    conf=_md_escape(row.get("confidence") or "—"),
                    rat=_md_escape(row.get("rationale") or "—"),
                    ev=_md_escape(_evidence_summary(row.get("evidence") or [])),
                    fl=_md_escape(
                        _flag_summary_for_md(row.get("registry_collision_flags") or {})
                    ),
                )
            )
    else:
        lines.append("(none)")
    lines.append("")

    scaffold_rows = payload.get("branch_scaffold_proposals") or []
    lines.append(f"## branch_scaffold_proposals ({len(scaffold_rows)})")
    lines.append("")
    if scaffold_rows:
        lines.append("| slug | divergence_mode | world_parent_hub_path | campaign_overlay_hub_path | location_slug |")
        lines.append("|---|---|---|---|---|")
        for row in scaffold_rows:
            lines.append(
                "| `{slug}` | {div} | {world} | {camp} | {loc} |".format(
                    slug=_md_escape(row.get("slug")),
                    div=_md_escape(row.get("divergence_mode") or "—"),
                    world=_md_escape(row.get("world_parent_hub_path") or "—"),
                    camp=_md_escape(row.get("campaign_overlay_hub_path") or "—"),
                    loc=_md_escape(row.get("location_slug") or "—"),
                )
            )
    else:
        lines.append("(none)")
    lines.append("")

    alias_rows = payload.get("proposed_aliases") or []
    lines.append(f"## proposed_aliases ({len(alias_rows)})")
    lines.append("")
    if alias_rows:
        lines.append(
            "| target_slug | alias_text | recommendation | confidence | rationale | flags |"
        )
        lines.append("|---|---|---|---|---|---|")
        for row in alias_rows:
            lines.append(
                "| `{tgt}` | {a} | {rec} | {conf} | {rat} | {fl} |".format(
                    tgt=_md_escape(row.get("target_slug")),
                    a=_md_escape(row.get("alias_text")),
                    rec=_md_escape(row.get("recommendation") or "(none)"),
                    conf=_md_escape(row.get("confidence") or "—"),
                    rat=_md_escape(row.get("rationale") or "—"),
                    fl=_md_escape(_alias_flag_summary_for_md(row.get("registry_flags") or {})),
                )
            )
    else:
        lines.append("(none)")
    lines.append("")

    unres_rows = payload.get("unresolvable") or []
    lines.append(f"## unresolvable ({len(unres_rows)}) — advisory")
    lines.append("")
    if unres_rows:
        lines.append(
            "| descriptor | recommendation | confidence | rationale | proposed_canonical |"
        )
        lines.append("|---|---|---|---|---|")
        for row in unres_rows:
            lines.append(
                "| {d} | {rec} | {conf} | {rat} | {can} |".format(
                    d=_md_escape(row.get("descriptor")),
                    rec=_md_escape(row.get("recommendation") or "(none)"),
                    conf=_md_escape(row.get("confidence") or "—"),
                    rat=_md_escape(row.get("rationale") or "—"),
                    can=_md_escape(row.get("proposed_canonical_slug") or "—"),
                )
            )
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("## sources")
    lines.append("")
    for src in payload.get("sources") or []:
        lines.append(f"- `{src}`")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Top-level orchestration
# --------------------------------------------------------------------------- #


def _build_openai_client() -> Any:
    """Build a sync OpenAI client wrapper for the judgment turn.

    Loads ``.env`` via ``src.bootstrap_env.load_dungeonmindbuddy_dotenv`` so
    ``OPENAI_API_KEY`` matches CLI / pytest behavior. Returns the raw
    ``OpenAI`` SDK client (we use ``responses.parse`` directly, mirroring
    ``src/ingestion/entity_extractor.py``).
    """
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for --with-llm mode."
        )
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "openai SDK is required for --with-llm mode (install via uv add openai)."
        ) from exc
    return OpenAI(api_key=api_key)


def run_promotion(
    *,
    campaign_id: str,
    proposals_pattern: str | None,
    per_run_pattern: str | None,
    registry_path: Path,
    out_dir: Path | None = None,
    use_llm: bool = False,
    quiet: bool = False,
    api_client: Any | None = None,
    model_override: str | None = None,
    when: datetime | None = None,
    cost_warn_usd: float = 0.50,
    cost_abort_usd: float = 2.00,
    pc_slugs: set[str] | None = None,
) -> dict[str, Any]:
    """Programmatic entry point. Returns a dict with sidecar paths + payload + cost."""
    when = when or datetime.now(timezone.utc)
    out_dir = out_dir or _DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    cohort_paths = _expand_glob(proposals_pattern, _REPO_ROOT)
    per_run_paths = _expand_glob(per_run_pattern, _REPO_ROOT)
    if not cohort_paths and not per_run_paths:
        raise ValueError(
            "no proposals or per-run sidecars matched the provided patterns; "
            "check --proposals / --per-run globs (rooted at repo root)."
        )

    if not quiet:
        print(
            f"[promote] campaign={campaign_id} cohort_files={len(cohort_paths)} "
            f"per_run_files={len(per_run_paths)} registry={registry_path}",
            flush=True,
        )

    aggregated = aggregate_sources(
        cohort_paths=cohort_paths,
        per_run_paths=per_run_paths,
    )
    registry = load_npc_registry(registry_path)
    pc_set = set(pc_slugs) if pc_slugs is not None else set(_LONGMONT_PC_SLUGS)

    model_id = _resolve_promotion_model(model_override) if use_llm else "(none)"
    cost_tally = CostTally()
    new_record_recs: dict[str, dict[str, Any]] = {}
    alias_recs: dict[tuple[str, str], dict[str, Any]] = {}
    unresolvable_recs: dict[str, dict[str, Any]] = {}

    if use_llm:
        if api_client is None:
            api_client = _build_openai_client()
        registry_siblings = _registry_siblings_for_prompt(registry)
        for slug, rec in sorted(aggregated.new_records.items()):
            flags = collision_flags_for_slug(
                slug=rec.slug,
                display_name=rec.display_name,
                aliases=rec.aliases,
                registry=registry,
                pc_slugs=pc_set,
            )
            try:
                parsed, _usage = _judge_new_record(
                    api_client=api_client,
                    model=model_id,
                    record=rec,
                    flags=flags,
                    registry_siblings=registry_siblings,
                    pc_slugs=list(pc_set),
                    tally=cost_tally,
                )
                new_record_recs[slug] = {
                    "recommendation": parsed.recommendation,
                    "confidence": parsed.confidence,
                    "rationale": parsed.rationale,
                    "promote_payload": (
                        parsed.promote_payload.model_dump(mode="json")
                        if parsed.promote_payload is not None
                        else None
                    ),
                    "merge_target_slug": parsed.merge_target_slug,
                }
            except Exception as exc:  # noqa: BLE001
                if not quiet:
                    print(
                        f"[promote] WARN new_record judgment failed for {slug!r}: {exc}",
                        flush=True,
                    )
                new_record_recs[slug] = {
                    "recommendation": "defer_to_gm",
                    "confidence": "low",
                    "rationale": f"LLM judgment failed: {exc}",
                    "promote_payload": None,
                    "merge_target_slug": None,
                }
            _enforce_cost_guard(
                cost_tally, warn_usd=cost_warn_usd, abort_usd=cost_abort_usd, quiet=quiet
            )

        for key, alias in sorted(aggregated.aliases.items()):
            flags = collision_flags_for_alias(
                target_slug=alias.target_slug,
                alias_text=alias.alias_text,
                registry=registry,
            )
            try:
                parsed_a, _usage = _judge_alias(
                    api_client=api_client,
                    model=model_id,
                    alias=alias,
                    flags=flags,
                    registry_siblings=registry_siblings,
                    tally=cost_tally,
                )
                alias_recs[key] = {
                    "recommendation": parsed_a.recommendation,
                    "confidence": parsed_a.confidence,
                    "rationale": parsed_a.rationale,
                }
            except Exception as exc:  # noqa: BLE001
                if not quiet:
                    print(
                        f"[promote] WARN alias judgment failed for {key!r}: {exc}",
                        flush=True,
                    )
                alias_recs[key] = {
                    "recommendation": "defer_to_gm",
                    "confidence": "low",
                    "rationale": f"LLM judgment failed: {exc}",
                }
            _enforce_cost_guard(
                cost_tally, warn_usd=cost_warn_usd, abort_usd=cost_abort_usd, quiet=quiet
            )

        for desc_key, item in sorted(aggregated.unresolvables.items()):
            try:
                parsed_u, _usage = _judge_unresolvable(
                    api_client=api_client,
                    model=model_id,
                    item=item,
                    registry_siblings=registry_siblings,
                    tally=cost_tally,
                )
                unresolvable_recs[desc_key] = {
                    "recommendation": parsed_u.recommendation,
                    "confidence": parsed_u.confidence,
                    "rationale": parsed_u.rationale,
                    "proposed_canonical_slug": parsed_u.proposed_canonical_slug,
                }
            except Exception as exc:  # noqa: BLE001
                if not quiet:
                    print(
                        f"[promote] WARN unresolvable judgment failed for "
                        f"{item.descriptor!r}: {exc}",
                        flush=True,
                    )
                unresolvable_recs[desc_key] = {
                    "recommendation": "defer_to_gm",
                    "confidence": "low",
                    "rationale": f"LLM judgment failed: {exc}",
                    "proposed_canonical_slug": None,
                }
            _enforce_cost_guard(
                cost_tally, warn_usd=cost_warn_usd, abort_usd=cost_abort_usd, quiet=quiet
            )

    payload = _build_promotion_payload(
        campaign_id=campaign_id,
        aggregated=aggregated,
        registry=registry,
        pc_slugs=pc_set,
        new_record_recs=new_record_recs,
        alias_recs=alias_recs,
        unresolvable_recs=unresolvable_recs,
        model_id=model_id,
        use_llm=use_llm,
        cost_tally=cost_tally,
        when=when,
    )

    iso_compact = when.strftime("%Y%m%dT%H%M%S") + "Z"
    base = f"{campaign_id}_stage_d_promotion_{iso_compact}"
    json_path = out_dir / f"{base}.json"
    md_path = out_dir / f"{base}.md"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    md_path.write_text(_build_promotion_markdown(payload), encoding="utf-8")

    if not quiet:
        print(f"[promote] wrote {json_path}", flush=True)
        print(f"[promote] wrote {md_path}", flush=True)
        print(
            f"[promote] cost: ${cost_tally.total_usd:.4f} USD over "
            f"{cost_tally.calls} call(s)",
            flush=True,
        )

    return {
        "json_path": json_path,
        "md_path": md_path,
        "payload": payload,
        "cost": cost_tally,
    }


def _enforce_cost_guard(
    tally: CostTally,
    *,
    warn_usd: float,
    abort_usd: float,
    quiet: bool,
) -> None:
    if tally.total_usd > abort_usd:
        raise RuntimeError(
            f"cost guard tripped: ${tally.total_usd:.4f} USD > abort threshold "
            f"${abort_usd:.2f}; aborting."
        )
    if tally.total_usd > warn_usd and not quiet:
        print(
            f"[promote] WARN cost ${tally.total_usd:.4f} USD exceeds warn threshold "
            f"${warn_usd:.2f}",
            flush=True,
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="promote_stage_d_proposals",
        description=(
            "Aggregate Stage D propose-only sidecars + per-run reports for a "
            "campaign and produce a GM review surface (JSON + Markdown). "
            "Optionally calls gpt-5.4-mini for an accept/reject/defer "
            "recommendation per slug. NEVER mutates _npc_registry.json."
        ),
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument(
        "--proposals",
        default="",
        help="glob pattern for cohort proposals files (rooted at repo root).",
    )
    parser.add_argument(
        "--per-run",
        default="",
        help="glob pattern for per-run sidecar files (rooted at repo root).",
    )
    parser.add_argument(
        "--registry", required=True, help="path to _npc_registry.json (READ-ONLY)."
    )
    parser.add_argument(
        "--out-dir",
        default=str(_DEFAULT_OUT_DIR),
        help="directory to write the promotion sidecars to.",
    )
    llm_group = parser.add_mutually_exclusive_group()
    llm_group.add_argument(
        "--with-llm",
        action="store_true",
        help=(
            "Enable the model recommendation pass (gpt-5.4-mini via "
            "MODEL_POLICY.json). Default is deterministic-only — the "
            "deterministic flags + raw evidence carry every signal the GM "
            "needs for easy-case promotions. Use --with-llm for hard cases "
            "(coreference, alias semantics) or to sanity-check GM judgment."
        ),
    )
    llm_group.add_argument(
        "--no-llm",
        action="store_true",
        help=(
            "DEPRECATED — deterministic-only is now the default; this flag "
            "is accepted for back-compat and is a no-op. Drop it from new "
            "scripts; pass --with-llm if you want the model pass."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help="override model id (else MODEL_POLICY.json corpus_session_planner action).",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.no_llm and not args.quiet:
        print(
            "[promote_stage_d_proposals] --no-llm is deprecated and a no-op; "
            "deterministic-only is now the default. Pass --with-llm to "
            "enable the model recommendation pass.",
            file=sys.stderr,
        )
    registry_path = (Path(args.registry)
                     if Path(args.registry).is_absolute()
                     else _REPO_ROOT / args.registry).resolve()
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (_REPO_ROOT / out_dir).resolve()
    try:
        run_promotion(
            campaign_id=args.campaign_id,
            proposals_pattern=args.proposals,
            per_run_pattern=args.per_run,
            registry_path=registry_path,
            out_dir=out_dir,
            use_llm=bool(args.with_llm),
            quiet=args.quiet,
            model_override=args.model,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[promote] ERROR: {exc}", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
