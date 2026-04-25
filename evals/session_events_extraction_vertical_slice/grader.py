"""Grader for the session-events-extraction vertical slice.

Gates:
* SE1 — schema validity: every parsed event validates against event_record.schema.json
* SE2 — count window: min_event_count <= len(events) <= max_event_count
* SE3 — participant coverage: every slug in must_cover_participants appears in at least one event
* SE4 — event-class coverage: every class in must_cover_event_classes appears in at least one event
* SE5 — anchor coverage + outcome-vocabulary preservation:
        Lenient coverage ratio mirrors prior behavior: for each ``expected_events[i]`` we look
        for a loose-match candidate (same event_class + participant overlap + name/outcomes text
        overlap). The matched_count / total ratio is the lenient coverage figure.

        Additionally, each expected event may declare ``must_preserve_terms: list[str]`` —
        distinctive named terms (weapon names, spell names, ability names, item names, place
        names, NPC names) that must appear *verbatim* (case-insensitive substring) in the
        model's output for an event involving the same participants. A term containing
        ``|`` is an **OR group** (e.g. ``drawing|blueprint``): any single alternative may
        satisfy the slot.

        Term-check is **per-term, across all participant-overlapping actuals**: for each
        required term ``t``, the term is considered preserved iff some actual sharing ≥1
        participant with the expected event contains ``t`` (case-insensitive substring) in
        its ``name + outcomes`` text. This decouples the outcome-vocabulary sub-gate from
        two sources of false positives:

        1. **Event-class drift** — the model often classifies the same beat under a related
           class (e.g. ``ritual`` instead of ``social_conflict`` for Caelynn's bracelet
           de-escalation). The strict ``_events_match`` matcher would exclude the right
           candidate; participant overlap alone keeps it in the pool.
        2. **Beat-splitting** — the model legitimately splits a gold-curated beat into two
           or three events (e.g. "Karsemine rounds up horses; observes magical storm" is
           often split into a wagon-discovery event with the horses and a separate
           camp-setup event with the storm + shimmering rain). As long as each distinctive
           term appears verbatim somewhere in participant-overlapping actuals, the OUTCOMES
           CONTRACT we are policing — vocabulary preservation for retrievability — holds.

        The OUTCOMES CONTRACT regressions this gate IS designed to catch are
        **paraphrasing** ("Eldritch Blast" → "attack spell", "antidote" silently dropped,
        "Questionable Company" → "the party") and **silent omission** of distinctive named
        terms anywhere in the model's output for the relevant participants.

        If any required term is absent from every participant-overlapping actual, the
        expected event counts as **vocabulary-incomplete** for SE5: it does not lower the
        lenient coverage ratio, but it does emit a ``missing_outcome_terms`` violation and
        trips the gate.

* SE6 (optional) — gold ``expected_anchored_spans``: each span covered by a participant-matched
  event anchor whose line range contains the span.
* SE7 (optional) — when ``grading["require_verified_event_anchors"]`` is true: every event's
  ``source_anchors`` must hash-match the recap file on disk under ``corpus_root`` and must not
  be a whole-file placeholder on multi-line recaps (capture-layer provenance; see design doc).

Telemetry keys: event_count, participants_seen, event_classes_seen,
                expected_event_coverage_ratio, unmatched_expected_event_indices,
                expected_events_with_missing_terms, missing_terms_total,
                expected_anchor_span_coverage_ratio, se7_* when SE7 runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.contracts.schema_validation import list_validation_failures
from src.ingestion.source_anchor import anchor_bytes_verify_at_head

_SCHEMA_FILENAME = "event_record.schema.json"
_SE5_PASS_THRESHOLD = 0.5  # gate fails when coverage ratio < this

# Max inclusive recap lines per event ``recap_evidence_span`` / ``source_anchors`` (step1).
# Sentence-bounded evidence may span multiple lines; must stay below whole-file spans.
RECAP_EVIDENCE_SPAN_MAX_LINES = 32

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
# SE5 — anchor coverage + outcome vocabulary preservation
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


def _actual_haystack(actual: dict[str, Any]) -> str:
    """Combined lowercase text used for case-insensitive substring checks."""
    name = str(actual.get("event_name") or "")
    outcomes = " ".join(str(o) for o in (actual.get("outcomes") or []))
    return f"{name} {outcomes}".lower()


def _se5_term_alternatives(term: str) -> list[str]:
    """Return alternative substrings for one SE5 slot (``a|b`` → OR; else single term)."""
    raw = str(term).strip()
    if not raw:
        return []
    if "|" in raw:
        return [p.strip() for p in raw.split("|") if p.strip()]
    return [raw]


def _se5_term_satisfied_in_haystack(haystack: str, term: str) -> bool:
    """True if any alternative for ``term`` is a case-insensitive substring of ``haystack``."""
    h = haystack.lower()
    return any(alt.lower() in h for alt in _se5_term_alternatives(term))


def _missing_terms(actual: dict[str, Any], required_terms: list[str]) -> list[str]:
    """Return required terms that are NOT case-insensitive substrings of the actual event text."""
    if not required_terms:
        return []
    haystack = _actual_haystack(actual)
    missing: list[str] = []
    for term in required_terms:
        s = str(term).strip()
        if not s:
            continue
        if not _se5_term_satisfied_in_haystack(haystack, s):
            missing.append(s)
    return missing


def _collect_se5_full(
    events: list[dict[str, Any]],
    expected_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Internal SE5 computation that returns the full result including the
    sibling-fallback telemetry. ``collect_se5_violations`` is a 4-tuple shim
    over this so existing call sites keep working unchanged.

    Returned dict keys:
      * ``violations`` (list[str]): human-readable SE5 strings (lenient-coverage
        failure + per missing-terms violation).
      * ``ratio`` (float), ``unmatched`` (list[int]): lenient-match telemetry
        (unchanged semantics).
      * ``term_violations`` (list[dict]): same payload shape as before; only
        emitted for terms that are missing both from the matched actual event
        AND from every other participant-overlapping actual event in the run.
      * ``terms_preserved_via_sibling`` (list[dict]): NEW soft-pass telemetry.
        Each entry is ``{expected_event_index: int, term: str,
        actual_event_index: int}`` — emitted when a term was missing from the
        matched actual event but present (case-insensitive substring on
        ``event_name + " " + " ".join(outcomes)`` — identical to the matched-
        event check) in another participant-overlapping actual event in the run.
        These do NOT trip the SE5 gate and are NOT counted in ``missing_terms_total``.
    """
    if not expected_events:
        return {
            "violations": [],
            "ratio": 1.0,
            "unmatched": [],
            "term_violations": [],
            "terms_preserved_via_sibling": [],
        }

    matched_count = 0
    unmatched: list[int] = []
    term_violations: list[dict[str, Any]] = []
    terms_preserved_via_sibling: list[dict[str, Any]] = []

    for i, exp in enumerate(expected_events):
        # Lenient coverage: strict event_class + participant + text-overlap match.
        strict_matches = [a for a in events if _events_match(exp, a)]
        if strict_matches:
            matched_count += 1
        else:
            unmatched.append(i)

        required_terms = list(exp.get("must_preserve_terms") or [])
        required_terms = [str(t).strip() for t in required_terms if str(t).strip()]
        if not required_terms:
            continue

        # Identify the "matched actual event" for this expected: the participant-
        # overlapping candidate that preserved the most required terms (tie-break:
        # first occurrence in the events list). This is the same heuristic the
        # previous implementation used to surface a representative actual in the
        # term_violations payload, now promoted to the primary term-check target.
        candidates_with_idx = [
            (idx, a) for idx, a in enumerate(events) if _participant_overlap(exp, a)
        ]
        if not candidates_with_idx:
            # No participant overlap anywhere — handled by lenient gate as unmatched.
            continue

        matched_actual: dict[str, Any] | None = None
        matched_actual_index = -1
        best_preserved = -1
        for idx, a in candidates_with_idx:
            hay_a = _actual_haystack(a)
            preserved_count = sum(
                1 for t in required_terms if _se5_term_satisfied_in_haystack(hay_a, t)
            )
            if preserved_count > best_preserved:
                best_preserved = preserved_count
                matched_actual = a
                matched_actual_index = idx

        missing: list[str] = []
        for term in required_terms:
            hay_matched = (
                _actual_haystack(matched_actual) if matched_actual is not None else ""
            )
            # 1) Matched actual event check (existing happy path).
            if matched_actual is not None and _se5_term_satisfied_in_haystack(
                hay_matched, term
            ):
                continue

            # 2) Sibling-event fallback: another participant-overlapping actual.
            #    Same case-insensitive substring check against
            #    `event_name + " " + " ".join(outcomes)` as the matched-event
            #    check. If found → soft-pass (telemetry only, no violation).
            #    Events with no participant overlap do not satisfy this contract;
            #    otherwise a required term dumped elsewhere in the run could hide
            #    a missing term on the relevant beat.
            sibling_idx: int | None = None
            for j, a in candidates_with_idx:
                if j == matched_actual_index:
                    continue
                if _se5_term_satisfied_in_haystack(_actual_haystack(a), term):
                    sibling_idx = j
                    break
            if sibling_idx is not None:
                terms_preserved_via_sibling.append(
                    {
                        "expected_event_index": i,
                        "term": term,
                        "actual_event_index": sibling_idx,
                    }
                )
                continue

            # 3) Term not in matched, not in any sibling → hard miss.
            missing.append(term)

        if missing:
            term_violations.append(
                {
                    "kind": "missing_outcome_terms",
                    "expected_event_index": i,
                    "expected_event_name": str(exp.get("event_name") or ""),
                    "missing_terms": list(missing),
                    "actual_event_name": str((matched_actual or {}).get("event_name") or ""),
                    "actual_event_outcomes": list((matched_actual or {}).get("outcomes") or []),
                }
            )

    ratio = matched_count / len(expected_events)
    bad: list[str] = []
    if ratio < _SE5_PASS_THRESHOLD:
        bad.append(
            f"SE5: anchor coverage ratio {ratio:.2f} < threshold {_SE5_PASS_THRESHOLD:.2f} "
            f"({matched_count}/{len(expected_events)} expected events matched); "
            f"unmatched indices: {unmatched}"
        )
    for tv in term_violations:
        bad.append(
            f"SE5: missing_outcome_terms — expected_events[{tv['expected_event_index']}] "
            f"({tv['expected_event_name']!r}): matched actual {tv['actual_event_name']!r} "
            f"is missing required term(s) {tv['missing_terms']}"
        )
    return {
        "violations": bad,
        "ratio": ratio,
        "unmatched": unmatched,
        "term_violations": term_violations,
        "terms_preserved_via_sibling": terms_preserved_via_sibling,
    }


def collect_se5_violations(
    events: list[dict[str, Any]],
    expected_events: list[dict[str, Any]],
) -> tuple[list[str], float, list[int], list[dict[str, Any]]]:
    """SE5: anchor coverage + outcome-vocabulary preservation (4-tuple shim).

    Returns ``(violations, coverage_ratio, unmatched_indices, term_violations)``.

    The new ``terms_preserved_via_sibling`` soft-pass telemetry is exposed on the
    orchestrator's telemetry dict (``collect_session_events_violations``); see
    ``_collect_se5_full`` for the full result shape.
    """
    r = _collect_se5_full(events, expected_events)
    return r["violations"], r["ratio"], r["unmatched"], r["term_violations"]


# ---------------------------------------------------------------------------
# SE6 — capture-layer anchor coverage (optional)
# ---------------------------------------------------------------------------


def collect_se6_violations(
    events: list[dict[str, Any]],
    expected_anchored_spans: list[dict[str, Any]],
    *,
    max_anchor_span_lines: int = RECAP_EVIDENCE_SPAN_MAX_LINES,
) -> tuple[list[str], float, list[int]]:
    """
    Optional capture-layer gate:
    each expected span must be covered by at least one event with participant slug + source_anchor.
    """
    if not expected_anchored_spans:
        return [], 1.0, []

    unmatched: list[int] = []
    for i, exp in enumerate(expected_anchored_spans):
        slug = str(exp.get("npc_slug", "")).strip()
        path = str(exp.get("path", "")).strip()
        lr = exp.get("line_range") or []
        if not slug or not path or not isinstance(lr, list) or len(lr) != 2:
            unmatched.append(i)
            continue
        try:
            want_start = int(lr[0])
            want_end = int(lr[1])
        except (TypeError, ValueError):
            unmatched.append(i)
            continue
        if want_start < 1 or want_end < want_start:
            unmatched.append(i)
            continue

        matched = False
        for ev in events:
            participants = {str(p).strip() for p in (ev.get("participants") or [])}
            if slug not in participants:
                continue
            for anchor in ev.get("source_anchors") or []:
                if not isinstance(anchor, dict):
                    continue
                a_path = str(anchor.get("path", "")).strip()
                if a_path != path:
                    continue
                try:
                    a_start = int(anchor.get("line_start"))
                    a_end = int(anchor.get("line_end"))
                except (TypeError, ValueError):
                    continue
                if (a_end - a_start + 1) > max_anchor_span_lines:
                    continue
                if a_start <= want_start and a_end >= want_end:
                    matched = True
                    break
            if matched:
                break
        if not matched:
            unmatched.append(i)

    ratio = (len(expected_anchored_spans) - len(unmatched)) / len(expected_anchored_spans)
    if unmatched:
        return (
            [
                f"SE6: anchored-span coverage {ratio:.2f} < 1.00 "
                f"({len(expected_anchored_spans) - len(unmatched)}/{len(expected_anchored_spans)}); "
                f"unmatched indices: {unmatched}"
            ],
            ratio,
            unmatched,
        )
    return [], ratio, unmatched


# ---------------------------------------------------------------------------
# SE7 — every event anchor verifies against on-disk recap bytes (optional)
# ---------------------------------------------------------------------------


def collect_se7_violations(
    events: list[dict[str, Any]],
    *,
    corpus_root: Path,
    recap_relative_path: str,
) -> tuple[list[str], dict[str, Any]]:
    """
    Capture-layer gate: each event must carry ``source_anchors`` that (1) point at the
    scenario recap path, (2) hash-match the current corpus bytes at the declared line span,
    and (3) are not a whole-file placeholder when the recap has multiple lines.

    Lexical survival on beats is intentionally out of scope here; see SE5 / timeline TP1.
    """
    recap_norm = Path(recap_relative_path.strip()).as_posix()
    recap_file = corpus_root / recap_relative_path
    telemetry: dict[str, Any] = {
        "se7_recap_lines": 0,
        "se7_events_checked": 0,
        "se7_anchors_checked": 0,
        "se7_whole_file_placeholder_count": 0,
    }
    if not recap_file.is_file():
        return (
            [f"SE7: recap not found under corpus_root: {recap_relative_path!r}"],
            telemetry,
        )
    lines = recap_file.read_text(encoding="utf-8").splitlines()
    nlines = len(lines)
    telemetry["se7_recap_lines"] = nlines
    bad: list[str] = []
    for i, ev in enumerate(events):
        telemetry["se7_events_checked"] += 1
        anchors_raw = ev.get("source_anchors")
        if not isinstance(anchors_raw, list) or not anchors_raw:
            bad.append(f"SE7: event[{i}] has no source_anchors")
            continue
        for j, raw in enumerate(anchors_raw):
            if not isinstance(raw, dict):
                bad.append(f"SE7: event[{i}] anchor[{j}] is not an object")
                continue
            telemetry["se7_anchors_checked"] += 1
            apath = Path(str(raw.get("path", "")).strip()).as_posix()
            if apath != recap_norm:
                bad.append(
                    f"SE7: event[{i}] anchor[{j}] path {apath!r} != scenario recap {recap_norm!r}"
                )
                continue
            issue = anchor_bytes_verify_at_head(corpus_root=corpus_root, raw=raw)
            if issue:
                bad.append(f"SE7: event[{i}] anchor[{j}] {issue}")
            try:
                ls = int(raw["line_start"])
                le = int(raw["line_end"])
            except (KeyError, TypeError, ValueError):
                continue
            if nlines > 1 and ls == 1 and le >= nlines:
                telemetry["se7_whole_file_placeholder_count"] += 1
                bad.append(
                    f"SE7: event[{i}] anchor[{j}] spans whole recap ({ls}-{le}); "
                    "use a bounded sentence-level line range when the recap has multiple lines"
                )
    return bad, telemetry


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def collect_session_events_violations(
    events: list[dict[str, Any]],
    grading: dict[str, Any],
    *,
    corpus_root: Path | None = None,
    recap_relative_path: str | None = None,
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Return (violations_dict, telemetry_dict).

    violations_dict buckets: se1, se2, se3, se4, se5, se6 (optional), se7 (optional)
    """
    min_count = int(grading.get("min_event_count") or 0)
    max_count = int(grading.get("max_event_count") or 9999)
    must_cover_participants = list(grading.get("must_cover_participants") or [])
    must_cover_classes = list(grading.get("must_cover_event_classes") or [])
    expected_events = list(grading.get("expected_events") or [])
    expected_anchored_spans = list(grading.get("expected_anchored_spans") or [])
    se6_max_anchor_span_lines = int(
        grading.get("se6_max_anchor_span_lines") or RECAP_EVIDENCE_SPAN_MAX_LINES
    )

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

    se5_full = _collect_se5_full(events, expected_events)
    se5 = se5_full["violations"]
    ratio = se5_full["ratio"]
    unmatched = se5_full["unmatched"]
    term_violations = se5_full["term_violations"]
    terms_preserved_via_sibling = se5_full["terms_preserved_via_sibling"]
    if se5:
        out["se5"] = se5

    se6_ratio = 1.0
    se6_unmatched: list[int] = []
    if expected_anchored_spans:
        se6, se6_ratio, se6_unmatched = collect_se6_violations(
            events,
            expected_anchored_spans,
            max_anchor_span_lines=max(1, se6_max_anchor_span_lines),
        )
        if se6:
            out["se6"] = se6

    se7_telemetry: dict[str, Any] = {}
    if grading.get("require_verified_event_anchors"):
        if corpus_root is None or not recap_relative_path:
            out.setdefault("se7", []).append(
                "SE7: require_verified_event_anchors is set but corpus_root or "
                "recap_relative_path was not passed to collect_session_events_violations"
            )
        else:
            se7, se7_telemetry = collect_se7_violations(
                events,
                corpus_root=corpus_root,
                recap_relative_path=recap_relative_path,
            )
            if se7:
                out["se7"] = se7

    participants_seen: list[str] = sorted(
        {str(p).strip() for ev in events for p in (ev.get("participants") or [])}
    )
    event_classes_seen: list[str] = sorted(
        {str(ev.get("event_class", "")).strip() for ev in events}
    )

    expected_events_with_missing_terms: list[int] = [
        int(tv["expected_event_index"]) for tv in term_violations
    ]
    missing_terms_total: int = sum(len(tv.get("missing_terms") or []) for tv in term_violations)

    telemetry: dict[str, Any] = {
        "event_count": len(events),
        "participants_seen": participants_seen,
        "event_classes_seen": event_classes_seen,
        "expected_event_coverage_ratio": round(ratio, 4),
        "unmatched_expected_event_indices": unmatched,
        "expected_events_with_missing_terms": expected_events_with_missing_terms,
        "missing_terms_total": missing_terms_total,
        "se5_term_violations": term_violations,
        "terms_preserved_via_sibling": terms_preserved_via_sibling,
        "expected_anchor_span_coverage_ratio": round(se6_ratio, 4),
        "unmatched_expected_anchor_span_indices": se6_unmatched,
    }
    telemetry.update(se7_telemetry)
    return out, telemetry


# ---------------------------------------------------------------------------
# Per-gate verdict
# ---------------------------------------------------------------------------


def per_gate_verdict(violations: dict[str, list[str]]) -> dict[str, str]:
    verdict = {
        "SE1": "FAIL" if violations.get("se1") else "PASS",
        "SE2": "FAIL" if violations.get("se2") else "PASS",
        "SE3": "FAIL" if violations.get("se3") else "PASS",
        "SE4": "FAIL" if violations.get("se4") else "PASS",
        "SE5": "FAIL" if violations.get("se5") else "PASS",
    }
    if "se6" in violations:
        verdict["SE6"] = "FAIL" if violations.get("se6") else "PASS"
    return verdict


__all__ = [
    "collect_session_events_violations",
    "collect_se1_violations",
    "collect_se2_violations",
    "collect_se3_violations",
    "collect_se4_violations",
    "collect_se5_violations",
    "collect_se6_violations",
    "collect_se7_violations",
    "per_gate_verdict",
]
