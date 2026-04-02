"""Narrative temporal tick: campaign-sourced facts must carry timeline provenance."""

from __future__ import annotations

from typing import Any


def _coerce_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _effective_evidence_session(unit: dict[str, Any]) -> int | None:
    document_session = _coerce_int(unit.get("document_session"))
    if document_session is not None:
        return document_session
    return _coerce_int(unit.get("inferred_session"))


def _is_session_specific_unit(unit: dict[str, Any]) -> bool:
    scope = unit.get("document_temporal_scope")
    if isinstance(scope, str) and scope.strip():
        return scope.strip() == "session_specific"
    source_class = str(unit.get("source_class", "")).strip()
    if source_class in {"observed_session_recap", "planning_document"}:
        return True
    if source_class in {"seed_reference", "ledger_or_dossier", "other"}:
        return False
    return True


def campaign_temporal_tick_violations(
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[str]:
    """Return human-readable errors when a fact is tied to campaign evidence but has no session/sequence tick.

    A tick is present if asserted_in_session is not None OR sequence_index_within_session is not None
    (mirrors fact_extractor inheritance from evidence.document_session / inferred_session / source_order_index).
    """
    by_id: dict[str, dict[str, Any]] = {}
    for unit in evidence_units:
        eid = unit.get("evidence_id")
        if eid is not None and str(eid).strip():
            by_id[str(eid)] = unit

    errors: list[str] = []
    for fact in facts:
        fid = str(fact.get("fact_id", "unknown_fact"))
        eids = fact.get("evidence_ids")
        if not isinstance(eids, list) or not eids:
            continue

        touches_campaign = False
        for eid in eids:
            key = str(eid)
            unit = by_id.get(key)
            if unit is None:
                errors.append(f"{fid}: evidence_id {key} not found in ingest evidence_units")
                continue
            layer = str(unit.get("canon_layer", "")).strip().lower()
            if layer == "campaign":
                touches_campaign = True

        if not touches_campaign:
            continue

        sess = fact.get("asserted_in_session")
        seq = fact.get("sequence_index_within_session")
        if sess is None and seq is None:
            errors.append(
                f"{fid}: campaign-layer evidence requires a narrative tick "
                f"(asserted_in_session and/or sequence_index_within_session); both are null"
            )

    return errors


def campaign_temporal_consistency_violations(
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[str]:
    """Return errors for campaign facts whose evidence disagrees on session provenance."""
    by_id: dict[str, dict[str, Any]] = {}
    for unit in evidence_units:
        eid = unit.get("evidence_id")
        if eid is not None and str(eid).strip():
            by_id[str(eid)] = unit

    errors: list[str] = []
    for fact in facts:
        fid = str(fact.get("fact_id", "unknown_fact"))
        eids = fact.get("evidence_ids")
        if not isinstance(eids, list) or not eids:
            continue

        campaign_units: list[dict[str, Any]] = []
        for eid in eids:
            key = str(eid)
            unit = by_id.get(key)
            if unit is None:
                continue
            layer = str(unit.get("canon_layer", "")).strip().lower()
            if layer == "campaign":
                campaign_units.append(unit)

        if not campaign_units:
            continue

        evidence_sessions = {
            session
            for session in (_effective_evidence_session(unit) for unit in campaign_units)
            if session is not None
        }
        if len(evidence_sessions) > 1:
            errors.append(
                f"{fid}: campaign evidence references conflicting sessions {sorted(evidence_sessions)}"
            )

        fact_session = _coerce_int(fact.get("asserted_in_session"))
        if fact_session is not None and evidence_sessions and fact_session not in evidence_sessions:
            errors.append(
                f"{fid}: asserted_in_session={fact_session} does not match evidence sessions "
                f"{sorted(evidence_sessions)}"
            )

    return errors


def campaign_temporal_quality_summary(
    evidence_units: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return non-blocking temporal quality metrics/warnings for campaign-linked facts."""
    by_id: dict[str, dict[str, Any]] = {}
    for unit in evidence_units:
        eid = unit.get("evidence_id")
        if eid is not None and str(eid).strip():
            by_id[str(eid)] = unit

    campaign_fact_count = 0
    session_specific_fact_count = 0
    sessionless_fact_count = 0
    asserted_session_count = 0
    sequence_only_count = 0
    missing_tick_count = 0
    sessionless_structural_only_count = 0
    sessionless_missing_tick_count = 0
    sessionless_asserted_session_count = 0
    missing_evidence_links = 0

    for fact in facts:
        eids = fact.get("evidence_ids")
        if not isinstance(eids, list) or not eids:
            continue

        campaign_units: list[dict[str, Any]] = []
        for eid in eids:
            unit = by_id.get(str(eid))
            if unit is None:
                missing_evidence_links += 1
                continue
            layer = str(unit.get("canon_layer", "")).strip().lower()
            if layer == "campaign":
                campaign_units.append(unit)

        if not campaign_units:
            continue

        campaign_fact_count += 1
        sess = _coerce_int(fact.get("asserted_in_session"))
        seq = _coerce_int(fact.get("sequence_index_within_session"))
        session_specific = any(_is_session_specific_unit(unit) for unit in campaign_units)
        if session_specific:
            session_specific_fact_count += 1
            if sess is not None:
                asserted_session_count += 1
            elif seq is not None:
                sequence_only_count += 1
            else:
                missing_tick_count += 1
        else:
            sessionless_fact_count += 1
            if sess is not None:
                sessionless_asserted_session_count += 1
            elif seq is not None:
                sessionless_structural_only_count += 1
            else:
                sessionless_missing_tick_count += 1

    sequence_only_ratio = (
        sequence_only_count / session_specific_fact_count if session_specific_fact_count else 0.0
    )
    warnings: list[str] = []
    if sequence_only_count > 0:
        warnings.append(
            "session-specific campaign facts are sequence-only (no asserted_in_session); narrative temporal anchoring is weaker"
        )
    if missing_tick_count > 0:
        warnings.append(
            "session-specific campaign facts are missing both temporal ticks; narrative temporal tick gate should fail"
        )
    if missing_evidence_links > 0:
        warnings.append("facts reference missing evidence_ids; temporal quality metrics are incomplete")

    return {
        "metrics": {
            "campaign_fact_count": campaign_fact_count,
            "session_specific_fact_count": session_specific_fact_count,
            "sessionless_fact_count": sessionless_fact_count,
            "asserted_session_count": asserted_session_count,
            "sequence_only_count": sequence_only_count,
            "missing_tick_count": missing_tick_count,
            "sessionless_structural_only_count": sessionless_structural_only_count,
            "sessionless_missing_tick_count": sessionless_missing_tick_count,
            "sessionless_asserted_session_count": sessionless_asserted_session_count,
            "missing_evidence_links": missing_evidence_links,
            "sequence_only_ratio": round(sequence_only_ratio, 4),
        },
        "warnings": warnings,
    }
