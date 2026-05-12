"""Single-pass unit-annotation ingest prompt (``dmb_recap_unit_annotations_v1``)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from evals.sentence_routing_retrieval_falsification.breadcrumb_prompt import (
    PROMPT_VARIANT_CONTINUATION,
    PROMPT_VARIANT_CONTROL,
    PROMPT_VARIANT_PRONOUN_RESOLUTION,
    _CONTINUATION_ADDENDUM,
    _PRONOUN_RESOLUTION_ADDENDUM,
)

PROMPT_VARIANT_BEAT_POPULATION_V1 = "beat_population_v1"

# C1S13 beat-boundary ablation variants (one isolated change each, then combined).
PROMPT_VARIANT_BEAT_EXP_V1_NO_LARGEST = "beat_exp_v1_no_largest"
PROMPT_VARIANT_BEAT_EXP_V2_LOC_MENTIONS_NO_MERGE = "beat_exp_v2_loc_mentions_no_merge"
PROMPT_VARIANT_BEAT_EXP_V3_BEAT_ROW_SELF_CHECK = "beat_exp_v3_beat_row_self_check"
PROMPT_VARIANT_BEAT_EXP_V4_PARTY_SPLIT_HARD = "beat_exp_v4_party_split_hard"
PROMPT_VARIANT_BEAT_EXP_V5_EVENT_MODE = "beat_exp_v5_event_mode"
PROMPT_VARIANT_BEAT_EXP_V_ALL = "beat_exp_v_all"

BEAT_BOUNDARY_EXPERIMENT_VARIANTS = (
    PROMPT_VARIANT_BEAT_POPULATION_V1,
    PROMPT_VARIANT_BEAT_EXP_V1_NO_LARGEST,
    PROMPT_VARIANT_BEAT_EXP_V2_LOC_MENTIONS_NO_MERGE,
    PROMPT_VARIANT_BEAT_EXP_V3_BEAT_ROW_SELF_CHECK,
    PROMPT_VARIANT_BEAT_EXP_V4_PARTY_SPLIT_HARD,
    PROMPT_VARIANT_BEAT_EXP_V5_EVENT_MODE,
    PROMPT_VARIANT_BEAT_EXP_V_ALL,
)

ALLOWED_UNIT_ANNOTATION_VARIANTS = {
    PROMPT_VARIANT_CONTROL,
    PROMPT_VARIANT_CONTINUATION,
    PROMPT_VARIANT_PRONOUN_RESOLUTION,
    *BEAT_BOUNDARY_EXPERIMENT_VARIANTS,
}

_BEAT_SPAN_LARGEST = (
    "- A beat is a retrieval-stable segment, not a story chapter: it is the largest\n"
    "  contiguous unit span where one location/population row can answer recall without\n"
    "  mixing different places, active rosters, or event modes."
)
_BEAT_SPAN_SMALLEST = (
    "- A beat is a retrieval-stable segment, not a story chapter: use the smallest\n"
    "  contiguous unit span that still yields one location/population row without\n"
    "  mixing different places, active rosters, or event modes."
)

_BEAT_ASSIGNMENT_TAIL = """\
- Start a new beat when scene goal, location, roster, combat state, ritual state, or travel leg
  materially changes.
- Treat sublocation changes as location changes when they change the recall answer
  (e.g. desk area vs infirmary vs study room vs morgue doorway).
- Start a new beat when the party splits, rejoins, or the narration follows only one subgroup.
- Start a new beat when the event mode changes, especially briefing/decision → rest/prep,
  ritual/questioning → ambush reveal, ambush reveal → combat exchange, or combat exchange → retreat/report.
- Keep adjacent units in the same beat only when they are one continuous scene with stable
  location, roster, and event mode.
- If a broader narrative scene contains multiple plausible location/population answers,
  prefer smaller beats over a mixed population row.
- Do not reopen a beat after a different beat begins.
- Beat IDs: ``c{campaign_number}s{session_number}-b{ordinal:03d}-{short_slug}`` (lowercase slug).
- Emit each used ``beat_id`` once in ``beat_index`` with a short summary.
"""

_BEAT_POPULATION_ADDENDUM = """\

BEAT / POPULATION EMPHASIS (this variant):
- Assign ``beat_id`` on every narrative unit; use null only for non-story units.
- Every beat with a location change must carry at least one ``location_mentions`` row on
  units that establish the place.
- Do not merge same-building or same-combat units when sublocation, active roster, or tactical
  phase changes would make one population row ambiguous.
- For ``location_entity_list``-style recall, ensure ``population_mentions`` cover explicit
  and carried present entities per beat/location, and ``mentioned_only`` for entities
  referenced but absent.
"""

_EXP_V2_LOC_MENTIONS_NO_MERGE = """\

LOCATION MENTIONS DO NOT LICENSE MERGING (isolated experiment):
- ``location_mentions`` record unit-level location facts; they do not permit one beat to
  contain multiple active locations or sublocations.
- If the active place changes, start a new beat unless the prior place is only
  ``mentioned_only`` in that unit.
"""

_EXP_V3_BEAT_ROW_SELF_CHECK = """\

BEAT ROW SELF-CHECK (isolated experiment):
- Before finalizing each beat, ask whether one compiled ``location_beat_population`` row
  could answer recall without mixing active locations, active rosters, or event modes.
- If not, split the beat.
"""

_EXP_V4_PARTY_SPLIT_HARD = """\

PARTY SPLIT / REJOIN HARD BOUNDARY (isolated experiment):
- Party split, subgroup focus, and regroup are hard beat boundaries.
- Do not keep split subgroups in one beat because the broader academy or building scene
  continues, unless the unit is only planning or mentioning the split.
"""

_EXP_V5_EVENT_MODE = """\

EVENT MODE OVER LOCATION (isolated experiment):
- When event mode changes, split even if the parent location route stays the same.
- Examples: briefing/options → decision/split; subgroup action in a sublocation;
  rest/prep → regroup/problem discovery.
"""

_EXPERIMENT_ADDENDA: dict[str, tuple[str, ...]] = {
    PROMPT_VARIANT_BEAT_EXP_V2_LOC_MENTIONS_NO_MERGE: (_EXP_V2_LOC_MENTIONS_NO_MERGE,),
    PROMPT_VARIANT_BEAT_EXP_V3_BEAT_ROW_SELF_CHECK: (_EXP_V3_BEAT_ROW_SELF_CHECK,),
    PROMPT_VARIANT_BEAT_EXP_V4_PARTY_SPLIT_HARD: (_EXP_V4_PARTY_SPLIT_HARD,),
    PROMPT_VARIANT_BEAT_EXP_V5_EVENT_MODE: (_EXP_V5_EVENT_MODE,),
    PROMPT_VARIANT_BEAT_EXP_V_ALL: (
        _EXP_V2_LOC_MENTIONS_NO_MERGE,
        _EXP_V3_BEAT_ROW_SELF_CHECK,
        _EXP_V4_PARTY_SPLIT_HARD,
        _EXP_V5_EVENT_MODE,
    ),
}


def _unit_annotations_system_header(*, beat_span_line: str) -> str:
    return f"""\
You annotate fixed recap ``units`` with beat membership, route tags, location context,
and population mentions. Downstream tooling injects inline breadcrumb tags and compiles
location-beat population rows — you MUST NOT output recap prose or markdown.

Structured output (JSON only — no fences, no commentary):
- Emit one object matching ``dmb_recap_unit_annotations_v1``:
  * ``schema``: literal ``dmb_recap_unit_annotations_v1``
  * ``source_recap_path``, ``campaign_id``, ``session_number``: repeat from the user message
  * ``beat_index``: stable beat IDs with one-line summaries (no unit lists here)
  * ``unit_annotations``: exactly one row per supplied unit, in the same order
- Each unit row includes ``unit_id``, nullable ``beat_id``, ``tags``, ``location_mentions``,
  and ``population_mentions``.

Route tags (``tags``):
- Allowed tag types: ``PC``, ``NPC``, ``Location``, ``Party``, ``NewHubCandidate``.
- Each ``route`` must be copied EXACTLY from the allowlist JSON (slashes matter).
- Tag only durable retrieval spans; do not tag every mention.

Beat assignment:
{beat_span_line}
{_BEAT_ASSIGNMENT_TAIL}
Location mentions (``location_mentions``):
- Record where the unit happens or what location it materially references.
- Use ``location_route`` when an allowlisted route exists; otherwise ``location_label``.
- Exactly one of ``location_route`` or ``location_label`` per mention (the other is null).
- ``presence_kind`` is ``explicit``, ``carried``, or ``mentioned_only``.

Population mentions (``population_mentions``):
- Record entities relevant to beat/location population (present or mentioned-only).
- Use ``entity_route`` for routed PCs/NPCs/Party/NewHubCandidate; ``entity_label`` only for
  unrouted collectives (e.g. ``alerted guards``).
- Exactly one of ``entity_route`` or ``entity_label`` per mention (the other is null).
- ``presence_kind``: ``explicit`` = named/acting/placed in scene; ``carried`` = still present
  from same-beat context without contradiction; ``mentioned_only`` = discussed but not present.
- ``support_unit_ids``: unit IDs justifying the mention; for ``carried``, include the current
  unit and a prior same-beat unit when available.
- Optional ``entity_state`` for non-roster facts (e.g. ``dead_body_or_head``).
- Separate route tags from population: a character may be present without a durable tag, and
  mentioned without being present.

Party policy:
- When prose says ``the party``, prefer a ``Party`` route tag when allowlisted; expand to
  individual PCs in ``population_mentions`` only when the local roster is clear.
"""


@dataclass(frozen=True)
class UnitAnnotationsPrompt:
    variant: str
    system_text: str
    user_text: str


def _beat_span_line_for_variant(variant: str) -> str:
    if variant in {
        PROMPT_VARIANT_BEAT_POPULATION_V1,
        PROMPT_VARIANT_BEAT_EXP_V1_NO_LARGEST,
        PROMPT_VARIANT_BEAT_EXP_V_ALL,
    }:
        return _BEAT_SPAN_SMALLEST
    return _BEAT_SPAN_LARGEST


def _build_unit_annotations_system_text(*, variant: str) -> str:
    if variant not in ALLOWED_UNIT_ANNOTATION_VARIANTS:
        raise ValueError(
            f"variant must be one of {sorted(ALLOWED_UNIT_ANNOTATION_VARIANTS)}; got {variant!r}"
        )
    text = _unit_annotations_system_header(beat_span_line=_beat_span_line_for_variant(variant))
    if variant in {PROMPT_VARIANT_CONTINUATION, PROMPT_VARIANT_PRONOUN_RESOLUTION}:
        text += _CONTINUATION_ADDENDUM
    if variant == PROMPT_VARIANT_PRONOUN_RESOLUTION:
        text += _PRONOUN_RESOLUTION_ADDENDUM
    if variant in BEAT_BOUNDARY_EXPERIMENT_VARIANTS or variant == PROMPT_VARIANT_PRONOUN_RESOLUTION:
        text += _BEAT_POPULATION_ADDENDUM
    for addendum in _EXPERIMENT_ADDENDA.get(variant, ()):
        text += addendum
    return text


def build_unit_annotations_prompt(
    *,
    variant: str,
    source_recap_path: str,
    campaign_id: str,
    session_number: int,
    recap_body: str,
    frontmatter_yaml: str,
    units: list[dict[str, object]],
    allowed_routes: list[str],
) -> UnitAnnotationsPrompt:
    """Structured single-pass prompt: model returns ``RecapUnitAnnotationsV1`` JSON."""
    routes_json = json.dumps(allowed_routes, indent=2, ensure_ascii=False)
    units_json = json.dumps(units, indent=2, ensure_ascii=False)
    user_text = (
        f"source_recap_path (repeat verbatim in output JSON): {source_recap_path!r}\n"
        f"campaign_id: {campaign_id!r}\n"
        f"session_number: {session_number}\n\n"
        "Allowlisted routes (EXACT strings for route fields):\n```json\n"
        f"{routes_json}\n```\n\n"
        "Recap body (context only — do not echo or paraphrase):\n```recap\n"
        f"{recap_body}\n```\n\n"
        "Units to annotate (JSON — emit one ``unit_annotations`` row per unit, same order):\n"
        f"```json\n{units_json}\n```\n\n"
        "Frontmatter entity index (context only):\n```yaml\n"
        f"{frontmatter_yaml.strip()}\n```\n"
    )
    return UnitAnnotationsPrompt(
        variant=variant,
        system_text=_build_unit_annotations_system_text(variant=variant),
        user_text=user_text,
    )
