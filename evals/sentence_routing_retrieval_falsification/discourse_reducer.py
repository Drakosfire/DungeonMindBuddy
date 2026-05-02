"""Deterministic Stage B2: discourse rows → hub route rows (``sentence_hub_routes_v1`` shape).

Discourse-row **coherence normalization** and ``b2_coherence_corrections`` telemetry live in
:mod:`stage_b2_coherence` / ``step2b_route_from_discourse_run`` (split pipeline), before this
module's pure row→routes transform.
"""

from __future__ import annotations

from typing import Any

from evals.sentence_routing_retrieval_falsification.discourse_schema import DiscourseRow
from evals.sentence_routing_retrieval_falsification.route_schema import (
    SCHEMA_SENTENCE_HUB_ROUTES_V1,
    THE_PARTY_ROUTE_SENTINEL,
    RouteRow,
    manifest_pc_slug_set,
    strip_pc_slugs_when_the_party_present,
)


def _filter_manifest_pcs(slugs: list[str], manifest_pc: set[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for s in slugs:
        if s in manifest_pc and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def discourse_row_to_route_row(
    row: DiscourseRow,
    *,
    manifest_pc_slugs: set[str],
    session_pc_roster_slugs: list[str] | None = None,
) -> RouteRow:
    """
    Map one discourse row to one route row.

    Expansion policy:
    - Union explicit PC slug lists (direct, topic, scene owner, perceiver), intersect manifest PCs.
    - If ``collective_actor == the_party``, ``party_expansion_allowed``, a session PC roster exists,
      not ``narrow_pc_only``, and discourse mode supports joint-band routing → assigned_hubs =
      [the_party] unless contradicted by explicit narrow multi-PC roles (handled via narrow_pc_only /
      slug lists).
    - ``narrow_pc_only`` suppresses emitting ``the_party`` from collective_actor (use explicit slug lists only).
    """
    pcs = _filter_manifest_pcs(
        list(row.direct_pc_slugs)
        + list(row.topic_pc_slugs)
        + list(row.scene_owner_pc_slugs)
        + list(row.perceiver_pc_slugs),
        manifest_pc_slugs,
    )

    wants_party = (
        row.collective_actor == THE_PARTY_ROUTE_SENTINEL
        and row.party_expansion_allowed
        and bool(session_pc_roster_slugs)
        and not row.narrow_pc_only
        and row.discourse_mode in ("explicit_party", "implicit_party")
    )

    assigned: list[str] = []
    if wants_party:
        hub_seed = [THE_PARTY_ROUTE_SENTINEL] + pcs
        assigned = strip_pc_slugs_when_the_party_present(hub_seed, manifest_pc_slugs)
    else:
        assigned = list(pcs)

    diag: str | None = None
    needs_new = False

    if not assigned:
        me = row.missing_entity_bucket
        if me == "new_hub_candidate":
            needs_new = True
        if me in ("npc_placeholder", "location_placeholder", "event_or_object_placeholder", "true_empty"):
            diag = me
        elif row.discourse_mode == "true_empty":
            diag = "true_empty"
        elif me:
            diag = me
    else:
        # Non-empty hubs: diagnostic only for npc_placeholder + PC assignment (matches RouteRow rules).
        if row.missing_entity_bucket == "npc_placeholder" and (
            THE_PARTY_ROUTE_SENTINEL in assigned or any(h in manifest_pc_slugs for h in assigned)
        ):
            diag = "npc_placeholder"
        else:
            diag = None

    rationale = (
        f"[discourse_reducer] mode={row.discourse_mode!r}; "
        f"from B1 rationale: {row.rationale}"
    ).strip()

    return RouteRow(
        unit_id=row.unit_id,
        assigned_hubs=assigned,
        confidence="high",
        rationale=rationale[:8000] if len(rationale) > 8000 else rationale,
        needs_new_hub_candidate=needs_new,
        routing_diagnostic_bucket=diag,
    )


def routes_from_discourse_rows(
    rows: list[DiscourseRow],
    *,
    manifest_jsonable: list[dict[str, Any]],
    session_pc_roster_slugs: list[str] | None = None,
) -> dict[str, Any]:
    """Build ``sentence_hub_routes_v1`` envelope dict from discourse rows."""
    manifest_pc = manifest_pc_slug_set(manifest_jsonable)
    routes = [
        discourse_row_to_route_row(
            r,
            manifest_pc_slugs=manifest_pc,
            session_pc_roster_slugs=session_pc_roster_slugs,
        ).model_dump()
        for r in rows
    ]
    return {"schema": SCHEMA_SENTENCE_HUB_ROUTES_V1, "routes": routes}
