"""Deterministic B1/B2 coherence normalization (split Stage B2 path).

Runs on parsed discourse rows **before** :func:`discourse_reducer.routes_from_discourse_rows`.
Emits ``b2_coherence_corrections`` so fixes are visible in sidecars (contract hardening; not gold-aware).
"""

from __future__ import annotations

from typing import Any

from evals.sentence_routing_retrieval_falsification.discourse_schema import DiscourseRow
from evals.sentence_routing_retrieval_falsification.route_schema import (
    THE_PARTY_ROUTE_SENTINEL,
)

# Missing-entity buckets that contradict explicit PC state. ``npc_placeholder`` is allowed as an
# additive cue ("PC plus out-of-manifest NPC"), matching the route-schema exception.
_INCOMPATIBLE_MISSING_BUCKET_WHEN_PC_STATE = frozenset(
    {
        "location_placeholder",
        "event_or_object_placeholder",
        "true_empty",
        "new_hub_candidate",
    }
)


def normalize_discourse_rows_for_b2_coherence(
    rows: list[DiscourseRow],
    *,
    session_pc_roster_slugs: list[str] | None = None,
) -> tuple[list[DiscourseRow], list[dict[str, Any]]]:
    """
    Return ``(normalized_rows, b2_coherence_corrections)``.

    Rules (deterministic, not gold-aware):

    1. **PC state wins over non-NPC placeholders** — if a discourse row already carries explicit
       PC slugs, clear contradictory missing-entity buckets (but keep ``npc_placeholder``).

    2. **Narrow-PC-only vs party expansion** — if ``narrow_pc_only`` is true, clear party-band
       expansion flags so reducer output cannot depend on a contradictory collective actor.

    3. **Missing roster vs party expansion** — if party expansion is requested without a session PC
       roster, clear the expansion flags and make the unresolved state explicit via ``true_empty``.
    """
    events: list[dict[str, Any]] = []
    out: list[DiscourseRow] = []
    has_roster = bool(session_pc_roster_slugs)

    for row in rows:
        fixed = row
        pc_slugs = (
            list(row.direct_pc_slugs)
            + list(row.topic_pc_slugs)
            + list(row.scene_owner_pc_slugs)
            + list(row.perceiver_pc_slugs)
        )
        if pc_slugs and row.missing_entity_bucket in _INCOMPATIBLE_MISSING_BUCKET_WHEN_PC_STATE:
            fixed = fixed.model_copy(update={"missing_entity_bucket": None})
            events.append(
                {
                    "unit_id": row.unit_id,
                    "rule": "clear_missing_bucket_when_pc_state_present",
                    "from": row.missing_entity_bucket,
                    "to": None,
                }
            )

        if fixed.narrow_pc_only and (
            fixed.collective_actor == THE_PARTY_ROUTE_SENTINEL or fixed.party_expansion_allowed
        ):
            before = {
                "collective_actor": fixed.collective_actor,
                "party_expansion_allowed": fixed.party_expansion_allowed,
            }
            fixed = fixed.model_copy(
                update={"collective_actor": None, "party_expansion_allowed": False}
            )
            events.append(
                {
                    "unit_id": row.unit_id,
                    "rule": "clear_party_expansion_under_narrow_pc_only",
                    "from": before,
                    "to": {"collective_actor": None, "party_expansion_allowed": False},
                }
            )

        if (
            fixed.collective_actor == THE_PARTY_ROUTE_SENTINEL
            and fixed.party_expansion_allowed
            and not has_roster
        ):
            fixed = fixed.model_copy(
                update={
                    "collective_actor": None,
                    "party_expansion_allowed": False,
                    "missing_entity_bucket": fixed.missing_entity_bucket or "true_empty",
                }
            )
            events.append(
                {
                    "unit_id": row.unit_id,
                    "rule": "clear_party_expansion_without_session_roster",
                    "from": {"collective_actor": THE_PARTY_ROUTE_SENTINEL, "party_expansion_allowed": True},
                    "to": {
                        "collective_actor": None,
                        "party_expansion_allowed": False,
                        "missing_entity_bucket": fixed.missing_entity_bucket,
                    },
                }
            )

        out.append(fixed)

    return out, events
