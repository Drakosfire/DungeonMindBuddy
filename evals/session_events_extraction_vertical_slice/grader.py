"""Grader for the session-events-extraction vertical slice.

Gates:
* SE1 — schema validity: every parsed event validates against event_record.schema.json
* SE2 — count window: min_event_count <= len(events) <= max_event_count
* SE3 — participant coverage: every slug in must_cover_participants appears in at least one event
* SE4 — event-class coverage: every class in must_cover_event_classes appears in at least one event
* SE5 — anchor coverage (soft, 0.5 threshold): for each expected_event, score whether a matching
         model event exists (same event_class + participant overlap + text overlap on name/outcomes)

Telemetry keys: event_count, participants_seen, event_classes_seen,
                expected_event_coverage_ratio, unmatched_expected_event_indices.
"""

from __future__ import annotations

from typing import Any

from src.contracts.schema_validation import list_validation_failures

_SCHEMA_FILENAME = "event_record.schema.json"
_SE5_PASS_THRESHOLD = 0.5  # gate fails when coverage ratio < this


# ---------------------------------------------------------------------------
# SE1 — schema validity
# ---------------------------------------------------------------------------


def collect_se1_violations(events: list[dict[str, Any]]) -> list[str]:
    """Each event must validate against event_record.schema.json."""
    bad: list[str] = []
    failures = list_validation_failures(events, _SCHEMA_FILENAME)
    for i, _instance, err_msg in failures:
        bad.append(f"SE1: event[{i}] schema validation failed: {err_msg}")
    return bad


# ---------------------------------------------------------------------------
# SE2 — count window
# ---------------------------------------------------------------------------


def collect_se2_violations(
    events: list[dict[str, Any]],
    *,
    min_count: int,
    max_count: int,
) -> list[str]:
    n = len(events)
    if n < min_count:
        return [f"SE2: event count {n} is below min_event_count {min_count}"]
    if n > max_count:
        return [f"SE2: event count {n} exceeds max_event_count {max_count}"]
    return []


# ---------------------------------------------------------------------------
# SE3 — participant coverage
# ---------------------------------------------------------------------------


def collect_se3_violations(
    events: list[dict[str, Any]],
    must_cover: list[str],
) -> list[str]:
    """Every required slug must appear in participants[] of at least one event."""
    seen: set[str] = set()
    for ev in events:
        for p in ev.get("participants") or []:
            seen.add(str(p).strip())
    bad: list[str] = []
    for slug in must_cover:
        if str(slug).strip() not in seen:
            bad.append(f"SE3: required participant {slug!r} not found in any event's participants[]")
    return bad


# ---------------------------------------------------------------------------
# SE4 — event-class coverage
# ---------------------------------------------------------------------------


def collect_se4_violations(
    events: list[dict[str, Any]],
    must_cover: list[str],
) -> list[str]:
    """Every required event_class must appear at least once."""
    seen: set[str] = {str(ev.get("event_class", "")).strip() for ev in events}
    bad: list[str] = []
    for cls in must_cover:
        if str(cls).strip() not in seen:
            bad.append(f"SE4: required event_class {cls!r} not found in any event")
    return bad


# ---------------------------------------------------------------------------
# SE5 — anchor coverage (soft gate, 0.5 threshold)
# ---------------------------------------------------------------------------


def _text_overlap(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """True when expected and actual share a meaningful word in name or outcomes text."""
    def _words(ev: dict[str, Any]) -> set[str]:
        tokens: set[str] = set()
        name = str(ev.get("event_name") or "").lower()
        tokens.update(t for t in name.split() if len(t) > 3)
        for outcome in ev.get("outcomes") or []:
            for t in str(outcome).lower().split():
                if len(t) > 3:
                    tokens.add(t)
        return tokens

    exp_words = _words(expected)
    if not exp_words:
        return False
    act_words = _words(actual)
    return bool(exp_words & act_words)


def _participant_overlap(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    exp_p = {str(p).strip() for p in (expected.get("participants") or [])}
    act_p = {str(p).strip() for p in (actual.get("participants") or [])}
    return bool(exp_p & act_p)


def _events_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Loose match: same event_class + at least one shared participant + text overlap."""
    if str(expected.get("event_class", "")).strip() != str(actual.get("event_class", "")).strip():
        return False
    if not _participant_overlap(expected, actual):
        return False
    return _text_overlap(expected, actual)


def collect_se5_violations(
    events: list[dict[str, Any]],
    expected_events: list[dict[str, Any]],
) -> tuple[list[str], float, list[int]]:
    """SE5: anchor coverage soft gate.

    Returns:
      (violations, coverage_ratio, unmatched_indices)

    A violation is emitted only when coverage_ratio < _SE5_PASS_THRESHOLD.
    """
    if not expected_events:
        return [], 1.0, []

    matched_count = 0
    unmatched: list[int] = []
    for i, exp in enumerate(expected_events):
        found = any(_events_match(exp, act) for act in events)
        if found:
            matched_count += 1
        else:
            unmatched.append(i)

    ratio = matched_count / len(expected_events)
    bad: list[str] = []
    if ratio < _SE5_PASS_THRESHOLD:
        bad.append(
            f"SE5: anchor coverage ratio {ratio:.2f} < threshold {_SE5_PASS_THRESHOLD:.2f} "
            f"({matched_count}/{len(expected_events)} expected events matched); "
            f"unmatched indices: {unmatched}"
        )
    return bad, ratio, unmatched


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def collect_session_events_violations(
    events: list[dict[str, Any]],
    grading: dict[str, Any],
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Return (violations_dict, telemetry_dict).

    violations_dict buckets: se1, se2, se3, se4, se5
    """
    min_count = int(grading.get("min_event_count") or 0)
    max_count = int(grading.get("max_event_count") or 9999)
    must_cover_participants = list(grading.get("must_cover_participants") or [])
    must_cover_classes = list(grading.get("must_cover_event_classes") or [])
    expected_events = list(grading.get("expected_events") or [])

    out: dict[str, list[str]] = {}

    se1 = collect_se1_violations(events)
    if se1:
        out["se1"] = se1

    se2 = collect_se2_violations(events, min_count=min_count, max_count=max_count)
    if se2:
        out["se2"] = se2

    se3 = collect_se3_violations(events, must_cover_participants)
    if se3:
        out["se3"] = se3

    se4 = collect_se4_violations(events, must_cover_classes)
    if se4:
        out["se4"] = se4

    se5, ratio, unmatched = collect_se5_violations(events, expected_events)
    if se5:
        out["se5"] = se5

    participants_seen: list[str] = sorted(
        {str(p).strip() for ev in events for p in (ev.get("participants") or [])}
    )
    event_classes_seen: list[str] = sorted(
        {str(ev.get("event_class", "")).strip() for ev in events}
    )

    telemetry: dict[str, Any] = {
        "event_count": len(events),
        "participants_seen": participants_seen,
        "event_classes_seen": event_classes_seen,
        "expected_event_coverage_ratio": round(ratio, 4),
        "unmatched_expected_event_indices": unmatched,
    }
    return out, telemetry


# ---------------------------------------------------------------------------
# Per-gate verdict
# ---------------------------------------------------------------------------


def per_gate_verdict(violations: dict[str, list[str]]) -> dict[str, str]:
    return {
        "SE1": "FAIL" if violations.get("se1") else "PASS",
        "SE2": "FAIL" if violations.get("se2") else "PASS",
        "SE3": "FAIL" if violations.get("se3") else "PASS",
        "SE4": "FAIL" if violations.get("se4") else "PASS",
        "SE5": "FAIL" if violations.get("se5") else "PASS",
    }


__all__ = [
    "collect_session_events_violations",
    "collect_se1_violations",
    "collect_se2_violations",
    "collect_se3_violations",
    "collect_se4_violations",
    "collect_se5_violations",
    "per_gate_verdict",
]
