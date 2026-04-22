"""Grader for the Stage C NPC-candidate-identification vertical slice.

Stage C consumes the events JSON produced by Stage A plus the per-campaign NPC
registry (``corpus/.../<campaign>/_npc_registry.json``) and a PC negative list,
and classifies every distinct non-PC entity mentioned in any event's
``participants[]`` or ``referenced_slugs[]`` into one of three buckets:

* ``tracked_npcs_active[]``   — entities that match a registry record
* ``new_npc_candidates[]``    — named entities with no registry record yet
* ``unresolved_descriptors[]``— ambiguous descriptors awaiting human disamb

Five gates:

* **NC1** Structure validity: output JSON parses; arrays present; each record's
          required fields typed correctly; ``evidence_event_indices`` are valid
          0-indexed positions; tracked slugs match a real registry slug; all
          slugs are lowercase + non-empty + match ``^[a-z0-9_]+$``.
* **NC2** PC negative-list cleanliness (HARD GATE): no PC slug or descriptor
          leaks into any of the three buckets.
* **NC3** Registry positive-list recall (HARD GATE): every registry slug whose
          ``status`` is ``tracked`` or ``background`` AND whose slug appears in
          the events' ``participants`` ∪ ``referenced_slugs`` MUST appear in
          ``tracked_npcs_active[].slug``. Plus: every entry in the gold's
          ``expected_tracked_active_minimum`` must appear (catches alias-only
          matches like ``stacey`` → ``stacey_brambleback``).
* **NC4** New-candidate evidence discipline: every ``new_npc_candidates[]`` and
          ``unresolved_descriptors[]`` record cites at least one valid event
          index.
* **NC5** Count window: total candidates ≤ ``max_total_candidates`` (default 25).

Telemetry surfaces tracked/new/unresolved counts, registry recall ratio,
the soft-bonus ``expected_new_candidate_coverage_hit`` flag (NOT a gate
failure when missed; signals whether Stage A's referenced_slugs[] coverage
fed Stage C the entities it needed), expected-tracked-missing list, and any
PC leaks for triage.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _str_or_empty(v: Any) -> str:
    return v if isinstance(v, str) else ""


def _as_str_list(v: Any) -> list[str]:
    if not isinstance(v, list):
        return []
    return [x for x in v if isinstance(x, str)]


def _as_int_list(v: Any) -> list[int]:
    if not isinstance(v, list):
        return []
    out: list[int] = []
    for x in v:
        if isinstance(x, bool):
            continue
        if isinstance(x, int):
            out.append(x)
    return out


def _collect_event_entity_slugs(events: list[dict[str, Any]]) -> set[str]:
    """Union of all event participants[] and referenced_slugs[] (lowercased)."""
    slugs: set[str] = set()
    for ev in events:
        for p in _as_str_list(ev.get("participants")):
            slugs.add(p.strip().lower())
        for r in _as_str_list(ev.get("referenced_slugs")):
            slugs.add(r.strip().lower())
    slugs.discard("")
    return slugs


def _registry_active_slugs(registry: list[dict[str, Any]]) -> set[str]:
    """Slugs whose status is tracked or background (the positive list)."""
    out: set[str] = set()
    for rec in registry:
        status = _str_or_empty(rec.get("status"))
        if status in ("tracked", "background"):
            slug = _str_or_empty(rec.get("slug")).strip().lower()
            if slug:
                out.add(slug)
    return out


def _registry_all_slugs(registry: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for rec in registry:
        slug = _str_or_empty(rec.get("slug")).strip().lower()
        if slug:
            out.add(slug)
    return out


def _pc_match_terms(pc_roster: list[dict[str, Any]]) -> tuple[set[str], list[str]]:
    """Return (pc_slugs_lower, pc_substring_terms_lower).

    Substring terms include slug, display_name, and aliases — all lowercased
    and stripped — used for case-insensitive substring matches against
    descriptor/suggested_slug strings.
    """
    pc_slugs: set[str] = set()
    pc_terms: list[str] = []
    for pc in pc_roster:
        slug = _str_or_empty(pc.get("slug")).strip().lower()
        if slug:
            pc_slugs.add(slug)
            pc_terms.append(slug)
        dn = _str_or_empty(pc.get("display_name")).strip().lower()
        if dn:
            pc_terms.append(dn)
        for alias in _as_str_list(pc.get("aliases")):
            a = alias.strip().lower()
            if a:
                pc_terms.append(a)
    return pc_slugs, pc_terms


# ---------------------------------------------------------------------------
# NC1 — structure validity
# ---------------------------------------------------------------------------


def _grade_nc1(
    output: dict[str, Any],
    events: list[dict[str, Any]],
    registry: list[dict[str, Any]],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    n_events = len(events)
    registry_slugs = _registry_all_slugs(registry)
    telemetry: dict[str, Any] = {}

    if not isinstance(output, dict):
        return "FAIL", ["NC1: output is not a JSON object"], {"output_is_object": False}

    for key in ("tracked_npcs_active", "new_npc_candidates", "unresolved_descriptors"):
        v = output.get(key, None)
        if v is None:
            violations.append(f"NC1: missing top-level array {key!r}")
            continue
        if not isinstance(v, list):
            violations.append(f"NC1: top-level {key!r} is not a list (got {type(v).__name__})")

    tracked = output.get("tracked_npcs_active") or []
    if isinstance(tracked, list):
        for i, rec in enumerate(tracked):
            if not isinstance(rec, dict):
                violations.append(f"NC1: tracked_npcs_active[{i}] is not an object")
                continue
            slug = rec.get("slug")
            if not isinstance(slug, str) or not slug.strip():
                violations.append(f"NC1: tracked_npcs_active[{i}].slug missing or empty")
            else:
                slug_lc = slug.strip().lower()
                if not _SLUG_RE.match(slug_lc):
                    violations.append(
                        f"NC1: tracked_npcs_active[{i}].slug {slug!r} fails ^[a-z0-9_]+$"
                    )
                if slug_lc not in registry_slugs:
                    violations.append(
                        f"NC1: tracked_npcs_active[{i}].slug {slug!r} not in registry"
                    )
            evi = rec.get("evidence_event_indices")
            if not isinstance(evi, list):
                violations.append(
                    f"NC1: tracked_npcs_active[{i}].evidence_event_indices missing/not list"
                )
            else:
                for j, idx in enumerate(evi):
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        violations.append(
                            f"NC1: tracked_npcs_active[{i}].evidence_event_indices[{j}] is not int"
                        )
                    elif idx < 0 or idx >= n_events:
                        violations.append(
                            f"NC1: tracked_npcs_active[{i}].evidence_event_indices[{j}]={idx} "
                            f"out of range [0, {n_events})"
                        )
            ac = rec.get("appearance_count")
            if not isinstance(ac, int) or isinstance(ac, bool):
                violations.append(
                    f"NC1: tracked_npcs_active[{i}].appearance_count missing or not int"
                )

    new_cands = output.get("new_npc_candidates") or []
    if isinstance(new_cands, list):
        for i, rec in enumerate(new_cands):
            if not isinstance(rec, dict):
                violations.append(f"NC1: new_npc_candidates[{i}] is not an object")
                continue
            descriptor = rec.get("descriptor")
            if not isinstance(descriptor, str) or not descriptor.strip():
                violations.append(f"NC1: new_npc_candidates[{i}].descriptor missing/empty")
            sug = rec.get("suggested_slug")
            if not isinstance(sug, str) or not sug.strip():
                violations.append(f"NC1: new_npc_candidates[{i}].suggested_slug missing/empty")
            else:
                sug_lc = sug.strip().lower()
                if not _SLUG_RE.match(sug_lc):
                    violations.append(
                        f"NC1: new_npc_candidates[{i}].suggested_slug {sug!r} fails ^[a-z0-9_]+$"
                    )
            evi = rec.get("evidence_event_indices")
            if not isinstance(evi, list):
                violations.append(
                    f"NC1: new_npc_candidates[{i}].evidence_event_indices missing/not list"
                )
            else:
                for j, idx in enumerate(evi):
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        violations.append(
                            f"NC1: new_npc_candidates[{i}].evidence_event_indices[{j}] is not int"
                        )
                    elif idx < 0 or idx >= n_events:
                        violations.append(
                            f"NC1: new_npc_candidates[{i}].evidence_event_indices[{j}]={idx} "
                            f"out of range [0, {n_events})"
                        )
            rationale = rec.get("rationale")
            if not isinstance(rationale, str):
                violations.append(f"NC1: new_npc_candidates[{i}].rationale missing/not str")

    unresolved = output.get("unresolved_descriptors") or []
    if isinstance(unresolved, list):
        for i, rec in enumerate(unresolved):
            if not isinstance(rec, dict):
                violations.append(f"NC1: unresolved_descriptors[{i}] is not an object")
                continue
            descriptor = rec.get("descriptor")
            if not isinstance(descriptor, str) or not descriptor.strip():
                violations.append(f"NC1: unresolved_descriptors[{i}].descriptor missing/empty")
            evi = rec.get("evidence_event_indices")
            if not isinstance(evi, list):
                violations.append(
                    f"NC1: unresolved_descriptors[{i}].evidence_event_indices missing/not list"
                )
            else:
                for j, idx in enumerate(evi):
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        violations.append(
                            f"NC1: unresolved_descriptors[{i}].evidence_event_indices[{j}] is not int"
                        )
                    elif idx < 0 or idx >= n_events:
                        violations.append(
                            f"NC1: unresolved_descriptors[{i}].evidence_event_indices[{j}]={idx} "
                            f"out of range [0, {n_events})"
                        )
            rationale = rec.get("rationale")
            if not isinstance(rationale, str):
                violations.append(f"NC1: unresolved_descriptors[{i}].rationale missing/not str")

    telemetry["nc1_violation_count"] = len(violations)
    return ("PASS" if not violations else "FAIL"), violations, telemetry


# ---------------------------------------------------------------------------
# NC2 — PC negative-list cleanliness
# ---------------------------------------------------------------------------


def _grade_nc2(
    output: dict[str, Any],
    pc_slugs_for_check: list[str],
    pc_terms_lower: list[str],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    leaks: list[dict[str, str]] = []

    pc_slug_set = {p.strip().lower() for p in pc_slugs_for_check if isinstance(p, str)}
    pc_slug_set.discard("")
    extra_terms_lower = [t for t in pc_terms_lower if t]
    all_terms_lower = list(pc_slug_set | set(extra_terms_lower))

    tracked = output.get("tracked_npcs_active") or []
    if isinstance(tracked, list):
        for i, rec in enumerate(tracked):
            if not isinstance(rec, dict):
                continue
            slug = _str_or_empty(rec.get("slug")).strip().lower()
            if slug and slug in pc_slug_set:
                violations.append(
                    f"NC2: PC slug {slug!r} leaked into tracked_npcs_active[{i}]"
                )
                leaks.append({"bucket": "tracked_npcs_active", "field": "slug", "value": slug})

    new_cands = output.get("new_npc_candidates") or []
    if isinstance(new_cands, list):
        for i, rec in enumerate(new_cands):
            if not isinstance(rec, dict):
                continue
            descriptor = _str_or_empty(rec.get("descriptor")).strip().lower()
            sug = _str_or_empty(rec.get("suggested_slug")).strip().lower()
            for term in all_terms_lower:
                if term and descriptor and term in descriptor:
                    violations.append(
                        f"NC2: PC term {term!r} appears in new_npc_candidates[{i}].descriptor "
                        f"{rec.get('descriptor')!r}"
                    )
                    leaks.append({
                        "bucket": "new_npc_candidates",
                        "field": "descriptor",
                        "value": rec.get("descriptor"),
                    })
                    break
            for term in all_terms_lower:
                if term and sug and term in sug:
                    violations.append(
                        f"NC2: PC term {term!r} appears in new_npc_candidates[{i}].suggested_slug "
                        f"{rec.get('suggested_slug')!r}"
                    )
                    leaks.append({
                        "bucket": "new_npc_candidates",
                        "field": "suggested_slug",
                        "value": rec.get("suggested_slug"),
                    })
                    break

    unresolved = output.get("unresolved_descriptors") or []
    if isinstance(unresolved, list):
        for i, rec in enumerate(unresolved):
            if not isinstance(rec, dict):
                continue
            descriptor = _str_or_empty(rec.get("descriptor")).strip().lower()
            for term in all_terms_lower:
                if term and descriptor and term in descriptor:
                    violations.append(
                        f"NC2: PC term {term!r} appears in unresolved_descriptors[{i}].descriptor "
                        f"{rec.get('descriptor')!r}"
                    )
                    leaks.append({
                        "bucket": "unresolved_descriptors",
                        "field": "descriptor",
                        "value": rec.get("descriptor"),
                    })
                    break

    telemetry: dict[str, Any] = {"pc_leaks": leaks}
    return ("PASS" if not violations else "FAIL"), violations, telemetry


# ---------------------------------------------------------------------------
# NC3 — Registry positive-list recall
# ---------------------------------------------------------------------------


def _grade_nc3(
    output: dict[str, Any],
    events: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    expected_tracked_active_minimum: list[str],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    event_slugs = _collect_event_entity_slugs(events)
    active_slugs = _registry_active_slugs(registry)
    should_be_tracked = active_slugs & event_slugs

    tracked = output.get("tracked_npcs_active") or []
    output_tracked: set[str] = set()
    if isinstance(tracked, list):
        for rec in tracked:
            if isinstance(rec, dict):
                slug = _str_or_empty(rec.get("slug")).strip().lower()
                if slug:
                    output_tracked.add(slug)

    missing_from_event_intersection = sorted(should_be_tracked - output_tracked)
    for slug in missing_from_event_intersection:
        violations.append(
            f"NC3: registry slug {slug!r} appears in events but is missing from "
            f"tracked_npcs_active[]"
        )

    expected_minimum_lower = [
        s.strip().lower() for s in expected_tracked_active_minimum if isinstance(s, str)
    ]
    missing_from_expected = [
        s for s in expected_minimum_lower if s and s not in output_tracked
    ]
    for slug in missing_from_expected:
        violations.append(
            f"NC3: expected_tracked_active_minimum slug {slug!r} missing from "
            f"tracked_npcs_active[] (alias-aware floor; model must catch alias-only matches)"
        )

    expected_total = len(should_be_tracked) + len(set(expected_minimum_lower) - should_be_tracked)
    matched_total = len(
        (should_be_tracked & output_tracked)
        | ((set(expected_minimum_lower) - should_be_tracked) & output_tracked)
    )
    recall_ratio = (matched_total / expected_total) if expected_total else 1.0

    telemetry: dict[str, Any] = {
        "registry_active_slugs_in_events": sorted(should_be_tracked),
        "expected_tracked_active_missing": sorted(
            set(missing_from_event_intersection) | set(missing_from_expected)
        ),
        "registry_recall_ratio": round(recall_ratio, 4),
        "tracked_active_slugs_emitted": sorted(output_tracked),
    }
    return ("PASS" if not violations else "FAIL"), violations, telemetry


# ---------------------------------------------------------------------------
# NC4 — new-candidate evidence discipline
# ---------------------------------------------------------------------------


def _grade_nc4(
    output: dict[str, Any],
    events: list[dict[str, Any]],
) -> tuple[str, list[str], dict[str, Any]]:
    violations: list[str] = []
    n = len(events)

    new_cands = output.get("new_npc_candidates") or []
    if isinstance(new_cands, list):
        for i, rec in enumerate(new_cands):
            if not isinstance(rec, dict):
                continue
            evi = _as_int_list(rec.get("evidence_event_indices"))
            if len(evi) < 1:
                violations.append(
                    f"NC4: new_npc_candidates[{i}] cites zero evidence_event_indices"
                )
            for j, idx in enumerate(evi):
                if idx < 0 or idx >= n:
                    violations.append(
                        f"NC4: new_npc_candidates[{i}].evidence_event_indices[{j}]={idx} "
                        f"out of range [0, {n})"
                    )

    unresolved = output.get("unresolved_descriptors") or []
    if isinstance(unresolved, list):
        for i, rec in enumerate(unresolved):
            if not isinstance(rec, dict):
                continue
            evi = _as_int_list(rec.get("evidence_event_indices"))
            if len(evi) < 1:
                violations.append(
                    f"NC4: unresolved_descriptors[{i}] cites zero evidence_event_indices"
                )
            for j, idx in enumerate(evi):
                if idx < 0 or idx >= n:
                    violations.append(
                        f"NC4: unresolved_descriptors[{i}].evidence_event_indices[{j}]={idx} "
                        f"out of range [0, {n})"
                    )

    return ("PASS" if not violations else "FAIL"), violations, {"nc4_violation_count": len(violations)}


# ---------------------------------------------------------------------------
# NC5 — count window
# ---------------------------------------------------------------------------


def _grade_nc5(
    output: dict[str, Any],
    max_total_candidates: int,
) -> tuple[str, list[str], dict[str, Any]]:
    new_cands = output.get("new_npc_candidates") or []
    unresolved = output.get("unresolved_descriptors") or []
    n_new = len(new_cands) if isinstance(new_cands, list) else 0
    n_unresolved = len(unresolved) if isinstance(unresolved, list) else 0
    total = n_new + n_unresolved
    violations: list[str] = []
    if total > max_total_candidates:
        violations.append(
            f"NC5: total candidates ({total}) exceeds max_total_candidates "
            f"({max_total_candidates})"
        )
    return (
        "PASS" if not violations else "FAIL",
        violations,
        {"total_candidates": total, "max_total_candidates": max_total_candidates},
    )


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


def grade_stage_c(
    stage_c_output: dict[str, Any],
    gold: dict[str, Any],
    events: list[dict[str, Any]],
    registry: list[dict[str, Any]],
) -> dict[str, Any]:
    """Grade a Stage C output against gold + events fixture + registry.

    Returns a dict with keys: gates_passed, per_gate_verdict, violations,
    violation_counts, telemetry.
    """
    grading = gold.get("grading") or {}
    pc_roster = (gold.get("input") or {}).get("pc_roster") or []
    pc_slugs_for_check = list(grading.get("pc_roster_for_negative_check") or [])
    expected_tracked_active_minimum = list(grading.get("expected_tracked_active_minimum") or [])
    expected_new_should_include = list(
        grading.get("expected_new_candidates_should_include_at_least_one_of") or []
    )
    max_total = int(grading.get("max_total_candidates") or 25)

    _, pc_terms_lower = _pc_match_terms(pc_roster)

    nc1_v, nc1_violations, nc1_tel = _grade_nc1(stage_c_output, events, registry)
    nc2_v, nc2_violations, nc2_tel = _grade_nc2(
        stage_c_output, pc_slugs_for_check, pc_terms_lower
    )
    nc3_v, nc3_violations, nc3_tel = _grade_nc3(
        stage_c_output, events, registry, expected_tracked_active_minimum
    )
    nc4_v, nc4_violations, nc4_tel = _grade_nc4(stage_c_output, events)
    nc5_v, nc5_violations, nc5_tel = _grade_nc5(stage_c_output, max_total)

    per_gate_verdict = {
        "NC1": nc1_v,
        "NC2": nc2_v,
        "NC3": nc3_v,
        "NC4": nc4_v,
        "NC5": nc5_v,
    }

    all_violations = (
        nc1_violations + nc2_violations + nc3_violations + nc4_violations + nc5_violations
    )
    violation_counts = {
        "NC1": len(nc1_violations),
        "NC2": len(nc2_violations),
        "NC3": len(nc3_violations),
        "NC4": len(nc4_violations),
        "NC5": len(nc5_violations),
    }
    gates_passed_n = sum(1 for v in per_gate_verdict.values() if v == "PASS")
    gates_passed_str = f"{gates_passed_n}/5"

    tracked = stage_c_output.get("tracked_npcs_active") or []
    new_cands = stage_c_output.get("new_npc_candidates") or []
    unresolved = stage_c_output.get("unresolved_descriptors") or []

    new_slugs_lower = {
        _str_or_empty(rec.get("suggested_slug")).strip().lower()
        for rec in (new_cands if isinstance(new_cands, list) else [])
        if isinstance(rec, dict)
    }
    new_slugs_lower.discard("")
    expected_new_lower = {
        s.strip().lower() for s in expected_new_should_include if isinstance(s, str) and s.strip()
    }
    expected_new_hit = bool(new_slugs_lower & expected_new_lower)

    telemetry: dict[str, Any] = {
        "tracked_active_count": len(tracked) if isinstance(tracked, list) else 0,
        "new_candidates_count": len(new_cands) if isinstance(new_cands, list) else 0,
        "unresolved_count": len(unresolved) if isinstance(unresolved, list) else 0,
        "registry_recall_ratio": nc3_tel.get("registry_recall_ratio", 0.0),
        "registry_active_slugs_in_events": nc3_tel.get("registry_active_slugs_in_events", []),
        "tracked_active_slugs_emitted": nc3_tel.get("tracked_active_slugs_emitted", []),
        "expected_tracked_active_missing": nc3_tel.get("expected_tracked_active_missing", []),
        "expected_new_candidate_coverage_hit": expected_new_hit,
        "expected_new_candidate_coverage_terms": sorted(expected_new_lower),
        "new_candidate_slugs_emitted": sorted(new_slugs_lower),
        "pc_leaks": nc2_tel.get("pc_leaks", []),
        "total_candidates": nc5_tel.get("total_candidates", 0),
    }

    return {
        "gates_passed": gates_passed_str,
        "all_gates_passed": gates_passed_n == 5,
        "per_gate_verdict": per_gate_verdict,
        "violations": all_violations,
        "violation_counts": violation_counts,
        "telemetry": telemetry,
    }


__all__ = [
    "grade_stage_c",
    "_grade_nc1",
    "_grade_nc2",
    "_grade_nc3",
    "_grade_nc4",
    "_grade_nc5",
    "_collect_event_entity_slugs",
    "_registry_active_slugs",
    "_pc_match_terms",
]
