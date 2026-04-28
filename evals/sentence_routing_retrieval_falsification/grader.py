"""Gates for ``sentence_routing_retrieval_falsification`` (legacy stage letters in function names).

- **``capture_sentence_units`` (legacy: Stage A — deterministic capture):** ``collect_stage_a_violations``.
- **``route_sentence_units_to_hubs`` (legacy: Stage B — hub routing):** ``collect_stage_b_violations``.
- **Later pipeline steps (legacy: Stages C–D):** proposal/retrieval graders still TBD; ``collect_stub_stage_bcd_telemetry`` only flags presence of gold keys for sidecars emitted from capture-only runs.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from copy import deepcopy

from evals.sentence_routing_retrieval_falsification.capture import SentenceUnit
from evals.sentence_routing_retrieval_falsification.route_schema import (
    ROUTING_DIAGNOSTIC_VALUE_SET,
    THE_PARTY_ROUTE_SENTINEL,
    RouteRow,
    normalize_route_rows_for_manifest,
)

_INVALID_DIAGNOSTIC_WITH_ASSIGNED_HUBS_ERROR = (
    "routing_diagnostic_bucket must be null when assigned_hubs is non-empty"
)


def _expected_hubs_for_must_route_row(
    g: dict[str, Any],
    party_expansion_slugs: list[str] | None,
) -> tuple[list[str] | None, str | None]:
    """
    Resolve ``expected_hubs``, expanding ``["the_party"]`` via ``party_expansion_slugs``.

    Returns ``(expanded, harness_error)``. ``harness_error`` is set when gold uses
    ``the_party`` but expansion is missing or empty.
    """
    exp = [str(x).strip() for x in (g.get("expected_hubs") or []) if str(x).strip()]
    if exp == [THE_PARTY_ROUTE_SENTINEL]:
        if not party_expansion_slugs:
            return None, (
                "Harness: gold expected_hubs [the_party] requires non-empty "
                "party_expansion_slugs (session roster)"
            )
        return list(party_expansion_slugs), None
    return exp, None


def _resolve_match_to_unit_id(
    match: dict[str, Any],
    sentence_units: list[dict[str, Any]],
    *,
    gold_row_label: str,
) -> tuple[str | None, str | None]:
    """
    DESIGN §6.5: ``line_start`` (1-based) + optional ``index_on_line`` (1-based among units on that
    line, after optional ``text_substring`` filter), sorted by ``unit_id``.
    Returns ``(unit_id, error_message)``.
    """
    if not isinstance(match, dict):
        return None, f"{gold_row_label}: match is not an object"
    line_start = match.get("line_start")
    if line_start is None:
        return None, f"{gold_row_label}: match missing line_start"
    try:
        line_no = int(line_start)
    except (TypeError, ValueError):
        return None, f"{gold_row_label}: match.line_start invalid: {line_start!r}"
    index_on_line = int(match.get("index_on_line", 1))
    if index_on_line < 1:
        return None, f"{gold_row_label}: match.index_on_line must be >= 1"
    needle = str(match.get("text_substring") or "").strip()

    candidates: list[dict[str, Any]] = []
    for u in sentence_units:
        if not isinstance(u, dict):
            continue
        try:
            ls = int(u.get("line_start", 0))
            le = int(u.get("line_end", ls))
        except (TypeError, ValueError):
            continue
        if ls <= line_no <= le:
            candidates.append(u)

    candidates.sort(key=lambda u: str(u.get("unit_id", "")))
    if needle:
        low = needle.lower()
        candidates = [u for u in candidates if low in str(u.get("text", "")).lower()]
    if len(candidates) < index_on_line:
        return (
            None,
            f"{gold_row_label}: match line_start={line_no} index_on_line={index_on_line} "
            f"only {len(candidates)} candidate(s) after filter",
        )
    uid = str(candidates[index_on_line - 1].get("unit_id") or "").strip()
    if not uid:
        return None, f"{gold_row_label}: resolved unit has empty unit_id"
    return uid, None


def normalize_gold_routing_matches(
    gold_routing: dict[str, Any],
    sentence_units: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """
    Resolve ``match`` rows to ``unit_id`` (DESIGN §6.5). Returns ``(normalized_gold_routing, errors)``.
    Errors are fatal for the harness (append to violations).
    """
    errors: list[str] = []
    out = deepcopy(gold_routing)
    for key in ("must_route", "must_abstain"):
        rows = list(out.get(key) or [])
        new_rows: list[Any] = []
        for idx, g in enumerate(rows):
            label = f"gold_routing.{key}[{idx}]"
            if not isinstance(g, dict):
                new_rows.append(g)
                continue
            row = dict(g)
            uid = str(row.get("unit_id") or "").strip()
            match = row.get("match")
            if match is not None:
                if not isinstance(match, dict):
                    errors.append(f"{label}: match must be an object")
                    new_rows.append(row)
                    continue
                resolved, err = _resolve_match_to_unit_id(
                    match, sentence_units, gold_row_label=label
                )
                if err:
                    errors.append(err)
                    new_rows.append(row)
                    continue
                if uid and uid != resolved:
                    errors.append(
                        f"{label}: unit_id {uid!r} disagrees with match resolution {resolved!r}"
                    )
                    new_rows.append(row)
                    continue
                row["unit_id"] = resolved
                row.pop("match", None)
            elif not uid:
                errors.append(f"{label}: missing both unit_id and match")
            new_rows.append(row)
        out[key] = new_rows
    return out, errors


def _violation_failure_buckets(violations: list[str]) -> dict[str, int]:
    """Stable buckets for ``violations.stage_b`` lines (B0–B2 + non-gate harness errors)."""
    c = Counter(
        {
            "b0_schema_row_integrity": 0,
            "b0_invalid_diagnostic_with_assigned_hubs": 0,
            "b0_diagnostic_null_when_assigned": 0,
            "b1_missing_expected_hub": 0,
            "b1_over_route": 0,
            "b2_over_assigned": 0,
            "b2_needs_new_hub_candidate": 0,
            "bd_diagnostic_bucket": 0,
            "non_gate": 0,
        }
    )
    for raw in violations:
        v = raw if isinstance(raw, str) else str(raw)
        if v.startswith("B0") or v.startswith("B0b") or v.startswith("B0c"):
            c["b0_schema_row_integrity"] += 1
            if _INVALID_DIAGNOSTIC_WITH_ASSIGNED_HUBS_ERROR in v:
                c["b0_invalid_diagnostic_with_assigned_hubs"] += 1
                # Legacy alias retained so older cohort summaries and reports still populate.
                c["b0_diagnostic_null_when_assigned"] += 1
        elif v.startswith("B1:") and "missing expected hubs" in v:
            c["b1_missing_expected_hub"] += 1
        elif v.startswith("B1:") and "over-route" in v:
            c["b1_over_route"] += 1
        elif v.startswith("B2:") and "hubs > max_assigned_hubs" in v:
            c["b2_over_assigned"] += 1
        elif v.startswith("B2:") and "needs_new_hub_candidate" in v:
            c["b2_needs_new_hub_candidate"] += 1
        elif v.startswith("BD:"):
            c["bd_diagnostic_bucket"] += 1
        else:
            c["non_gate"] += 1
    return dict(c)


def stage_b_violation_only_telemetry(
    violations: list[str],
    *,
    expected_unit_ids: set[str],
) -> dict[str, Any]:
    """
    Emit Stage B breakdown telemetry even when route parsing fails before grading.

    ``parse_routes_envelope`` rejects rows with schema-level contradictions before
    ``collect_stage_b_violations`` can build the normal B1/B2 breakdown. (Wire routes
    strip redundant manifest **PC** slugs when ``the_party`` is present; non-PC hubs are kept,
    and only ``npc_placeholder`` may coexist with PC assignments.) Keeping this minimal
    telemetry makes B0 sub-buckets visible in cohort summaries.
    """
    sentence_unit_count = len(expected_unit_ids)
    return {
        "stage_b_unit_breakdown": {
            "sentence_unit_count": sentence_unit_count,
            "gold_pinned_distinct_unit_count": 0,
            "unpinned_sentence_unit_count": sentence_unit_count,
            "must_route": None,
            "must_abstain": None,
            "gold_gate_checks_total": None,
            "gold_gate_checks_pass": None,
            "gold_gate_checks_fail": None,
            "violation_line_count": len(violations),
            "violation_failure_buckets": _violation_failure_buckets(violations),
            "routing_diagnostic_histogram": {},
            "diagnostic_bucket_expectations": {
                "defined": 0,
                "pass": 0,
                "fail": 0,
                "enforce": False,
            },
        }
    }


def stage_b_routes_by_id_normalized(
    routes: list[RouteRow],
    manifest_slugs: set[str],
) -> dict[str, RouteRow]:
    """Last route row wins on duplicate ``unit_id`` (matches ``collect_stage_b_violations``)."""
    routes = normalize_route_rows_for_manifest(routes, manifest_slugs)
    by_id: dict[str, RouteRow] = {}
    for r in routes:
        by_id[r.unit_id] = r
    return by_id


def _must_route_row_passes(
    by_id: dict[str, RouteRow],
    g: dict[str, Any],
    *,
    party_expansion_slugs: list[str] | None,
) -> tuple[bool, str]:
    uid = str(g.get("unit_id") or "").strip()
    if not uid:
        return False, "missing unit_id"
    row = by_id.get(uid)
    if row is None:
        return False, "missing route row"
    exp, harness_err = _expected_hubs_for_must_route_row(g, party_expansion_slugs)
    if harness_err:
        return False, harness_err
    assert exp is not None
    assigned = set(row.assigned_hubs)
    miss = [h for h in exp if h not in assigned]
    if miss:
        return (
            False,
            f"missing expected hubs {miss} (assigned={sorted(assigned)})",
        )
    max_extra = g.get("max_extra_hubs")
    if max_extra is not None:
        me = int(max_extra)
        max_allowed = len(exp) + me
        if len(row.assigned_hubs) > max_allowed:
            return (
                False,
                f"over-route: len(assigned_hubs)={len(row.assigned_hubs)} "
                f"> len(expected_hubs)+max_extra_hubs={max_allowed}",
            )
    if "expected_routing_diagnostic_bucket" in g:
        raw_diag = g["expected_routing_diagnostic_bucket"]
        want = None if raw_diag is None else str(raw_diag).strip()
        got = row.routing_diagnostic_bucket
        got_str = None if got is None else str(got).strip()
        if want != got_str:
            return (
                False,
                f"routing_diagnostic_bucket want {want!r} got {got_str!r}",
            )
    return True, ""


def _must_abstain_row_passes(by_id: dict[str, RouteRow], g: dict[str, Any]) -> tuple[bool, str]:
    uid = str(g.get("unit_id") or "").strip()
    if not uid:
        return False, "missing unit_id"
    row = by_id.get(uid)
    if row is None:
        return False, "missing route row"
    max_assigned = int(g.get("max_assigned_hubs", 0))
    if len(row.assigned_hubs) > max_assigned:
        return False, "over_assigned"
    if "needs_new_hub_candidate" in g:
        want_false = g["needs_new_hub_candidate"] is False
        if want_false and row.needs_new_hub_candidate:
            return False, "needs_new_hub_candidate"
    return True, ""


def iter_stage_b_gold_check_results(
    by_id: dict[str, RouteRow],
    gold_routing: dict[str, Any],
    *,
    party_expansion_slugs: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    One dict per gold row (same semantics as B1/B2 in ``collect_stage_b_violations``).

    Keys: ``check_key``, ``gate``, ``row_index``, ``unit_id``, ``passed``, ``fail_reason``.
    """
    out: list[dict[str, Any]] = []
    for i, g in enumerate(gold_routing.get("must_route") or []):
        ck = f"must_route[{i}]"
        if not isinstance(g, dict):
            out.append(
                {
                    "check_key": ck,
                    "gate": "must_route",
                    "row_index": i,
                    "unit_id": "",
                    "passed": False,
                    "fail_reason": "gold row not an object",
                }
            )
            continue
        uid = str(g.get("unit_id") or "").strip()
        ok, why = _must_route_row_passes(by_id, g, party_expansion_slugs=party_expansion_slugs)
        out.append(
            {
                "check_key": ck,
                "gate": "must_route",
                "row_index": i,
                "unit_id": uid,
                "passed": ok,
                "fail_reason": why,
            }
        )
    for i, g in enumerate(gold_routing.get("must_abstain") or []):
        ck = f"must_abstain[{i}]"
        if not isinstance(g, dict):
            out.append(
                {
                    "check_key": ck,
                    "gate": "must_abstain",
                    "row_index": i,
                    "unit_id": "",
                    "passed": False,
                    "fail_reason": "gold row not an object",
                }
            )
            continue
        uid = str(g.get("unit_id") or "").strip()
        ok, why = _must_abstain_row_passes(by_id, g)
        out.append(
            {
                "check_key": ck,
                "gate": "must_abstain",
                "row_index": i,
                "unit_id": uid,
                "passed": ok,
                "fail_reason": why,
            }
        )
    return out


def _gold_row_pass_fail(
    by_id: dict[str, RouteRow],
    gold_routing: dict[str, Any],
    *,
    party_expansion_slugs: list[str] | None = None,
) -> tuple[int, int, int, int, set[str]]:
    """
    Count must_route / must_abstain **checks** (one gold row = one check) that pass vs fail,
    mirroring ``collect_stage_b_violations`` logic. Returns
    ``(mr_pass, mr_fail, ma_pass, ma_fail, gold_pinned_unit_ids)``.
    """
    pinned: set[str] = set()
    mr_pass = mr_fail = ma_pass = ma_fail = 0
    for row in iter_stage_b_gold_check_results(
        by_id, gold_routing, party_expansion_slugs=party_expansion_slugs
    ):
        uid = str(row.get("unit_id") or "").strip()
        if uid:
            pinned.add(uid)
        g = row["gate"]
        ok = bool(row.get("passed"))
        if g == "must_route":
            if ok:
                mr_pass += 1
            else:
                mr_fail += 1
        elif g == "must_abstain":
            if ok:
                ma_pass += 1
            else:
                ma_fail += 1
    return mr_pass, mr_fail, ma_pass, ma_fail, pinned


def collect_stage_a_violations(
    units: list[SentenceUnit],
    gold_capture: dict[str, Any],
    *,
    corpus_root: Path,
    recap_relative_path: str,
) -> tuple[list[str], dict[str, Any]]:
    """Return (violations, telemetry) for deterministic capture."""
    violations: list[str] = []
    telemetry: dict[str, Any] = {
        "stage_a_unit_count": len(units),
        "stage_a_lines_in_recap": 0,
    }
    recap_file = corpus_root / recap_relative_path
    if not recap_file.is_file():
        violations.append(f"A0: recap not found: {recap_relative_path}")
        return violations, telemetry
    lines = recap_file.read_text(encoding="utf-8").splitlines()
    telemetry["stage_a_lines_in_recap"] = len(lines)

    min_u = int(gold_capture.get("min_units") or 0)
    max_u = int(gold_capture.get("max_units") or 9999)
    n = len(units)
    if n < min_u:
        violations.append(f"A1: unit count {n} < min_units {min_u}")
    if n > max_u:
        violations.append(f"A1: unit count {n} > max_units {max_u}")

    for i, u in enumerate(units):
        if u.line_start < 1 or u.line_end < u.line_start:
            violations.append(f"A2: unit[{i}] invalid line span {u.line_start}-{u.line_end}")
        if not (u.text or "").strip():
            violations.append(f"A2: unit[{i}] empty text")
        if not (u.path or "").strip():
            violations.append(f"A2: unit[{i}] empty path")

    must_any = list(gold_capture.get("must_contain_substrings_anywhere") or [])
    blob = "\n".join(u.text for u in units).lower()
    for needle in must_any:
        if needle.lower() not in blob:
            violations.append(f"A3: missing required substring in units: {needle!r}")

    return violations, telemetry


def collect_stage_b_violations(
    routes: list[RouteRow],
    gold_routing: dict[str, Any],
    *,
    manifest_slugs: set[str],
    expected_unit_ids: set[str],
    party_expansion_slugs: list[str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Hub-routing gates B0–B2 (hard; legacy: Stage B); B3 soft limits only in telemetry (DESIGN §6.4)."""
    violations: list[str] = []
    routes = normalize_route_rows_for_manifest(routes, manifest_slugs)
    by_id: dict[str, RouteRow] = {}
    for r in routes:
        if r.unit_id in by_id:
            violations.append(f"B0: duplicate route row for unit_id {r.unit_id!r}")
        by_id[r.unit_id] = r

    got_ids = set(by_id)
    if got_ids != expected_unit_ids:
        missing = sorted(expected_unit_ids - got_ids)
        extra = sorted(got_ids - expected_unit_ids)
        if missing:
            violations.append(f"B0: missing route rows for unit_ids: {missing}")
        if extra:
            violations.append(
                f"B0: unknown route unit_ids (not from capture_sentence_units / Stage A): {extra}"
            )

    for uid, row in by_id.items():
        for hub in row.assigned_hubs:
            if hub not in manifest_slugs:
                violations.append(f"B0b: unit {uid!r} assigns unknown hub {hub!r} (not in manifest)")

    require_diag = bool(gold_routing.get("require_routing_diagnostic_bucket"))
    if require_diag:
        for uid, row in by_id.items():
            if not row.assigned_hubs and row.routing_diagnostic_bucket is None:
                violations.append(
                    f"B0c: unit {uid!r} missing routing_diagnostic_bucket while assigned_hubs is empty"
                )

    diag_expect_raw = gold_routing.get("diagnostic_buckets")
    enforce_diag = bool(gold_routing.get("enforce_diagnostic_buckets"))
    diag_expect: dict[str, str] = {}
    if isinstance(diag_expect_raw, dict):
        for uk, ev in diag_expect_raw.items():
            uid_k = str(uk).strip()
            exp_v = str(ev).strip()
            if uid_k and exp_v:
                if exp_v not in ROUTING_DIAGNOSTIC_VALUE_SET:
                    violations.append(
                        f"Harness: diagnostic_buckets[{uid_k!r}] invalid expected bucket {exp_v!r}"
                    )
                else:
                    diag_expect[uid_k] = exp_v

    for g in gold_routing.get("must_route") or []:
        if not isinstance(g, dict):
            violations.append(f"B1: must_route entry is not an object: {g!r}")
            continue
        uid = str(g.get("unit_id") or "").strip()
        if not uid:
            violations.append(f"B1: must_route missing unit_id: {g!r}")
            continue
        ok, why = _must_route_row_passes(
            by_id, g, party_expansion_slugs=party_expansion_slugs
        )
        if not ok:
            violations.append(f"B1: must_route unit {uid!r}: {why}")

    for g in gold_routing.get("must_abstain") or []:
        if not isinstance(g, dict):
            violations.append(f"B2: must_abstain entry is not an object: {g!r}")
            continue
        uid = str(g.get("unit_id") or "").strip()
        if not uid:
            violations.append(f"B2: must_abstain missing unit_id: {g!r}")
            continue
        row = by_id.get(uid)
        if row is None:
            continue
        max_assigned = int(g.get("max_assigned_hubs", 0))
        if len(row.assigned_hubs) > max_assigned:
            violations.append(
                f"B2: must_abstain unit {uid!r} has {len(row.assigned_hubs)} hubs "
                f"> max_assigned_hubs={max_assigned}"
            )
        if "needs_new_hub_candidate" in g:
            want_false = g["needs_new_hub_candidate"] is False
            if want_false and row.needs_new_hub_candidate:
                violations.append(
                    f"B2: must_abstain unit {uid!r} must have needs_new_hub_candidate false "
                    f"(got true)"
                )

    diag_pass = 0
    diag_fail = 0
    for uid, exp in diag_expect.items():
        row = by_id.get(uid)
        if row is None:
            continue
        got = row.routing_diagnostic_bucket
        if got == exp:
            diag_pass += 1
        else:
            diag_fail += 1
            msg = f"BD: unit {uid!r} diagnostic_bucket expected {exp!r} got {got!r}"
            if enforce_diag:
                violations.append(msg)

    diag_hist: dict[str, int] = {}
    for r in routes:
        if r.assigned_hubs and r.routing_diagnostic_bucket is not None:
            dk = f"(assigned+{r.routing_diagnostic_bucket})"
        elif r.assigned_hubs:
            dk = "(assigned)"
        else:
            dk = (
                r.routing_diagnostic_bucket
                if r.routing_diagnostic_bucket is not None
                else "(unset)"
            )
        diag_hist[dk] = diag_hist.get(dk, 0) + 1

    n = len(routes)
    mean_assigned = (sum(len(r.assigned_hubs) for r in routes) / n) if n else 0.0
    unresolved = 0
    for r in routes:
        if not r.assigned_hubs and not r.needs_new_hub_candidate:
            unresolved += 1
    unresolved_fraction = (unresolved / n) if n else 0.0
    hist: dict[str, int] = {}
    for r in routes:
        k = str(len(r.assigned_hubs))
        hist[k] = hist.get(k, 0) + 1

    soft = gold_routing.get("soft_limits") or {}
    soft_warnings: list[str] = []
    max_mean = soft.get("max_mean_assigned_hubs_per_unit")
    if max_mean is not None and mean_assigned > float(max_mean):
        soft_warnings.append(
            f"mean_assigned_hubs_per_unit={mean_assigned:.3f} > soft max {max_mean}"
        )
    max_unres = soft.get("max_unresolved_fraction")
    if max_unres is not None and unresolved_fraction > float(max_unres):
        soft_warnings.append(
            f"unresolved_fraction={unresolved_fraction:.3f} > soft max {max_unres}"
        )

    mr_pass, mr_fail, ma_pass, ma_fail, gold_pinned = _gold_row_pass_fail(
        by_id, gold_routing, party_expansion_slugs=party_expansion_slugs
    )
    mr_checks = mr_pass + mr_fail
    ma_checks = ma_pass + ma_fail
    sentence_unit_count = len(expected_unit_ids)
    unpinned = max(0, sentence_unit_count - len(gold_pinned))

    telemetry: dict[str, Any] = {
        "routes_row_count": n,
        "mean_assigned_hubs": round(mean_assigned, 6),
        "unresolved_fraction": round(unresolved_fraction, 6),
        "assigned_hubs_count_histogram": hist,
        "needs_new_hub_candidate_count": sum(1 for r in routes if r.needs_new_hub_candidate),
        "stage_b_soft_warnings": soft_warnings,
        "stage_b_unit_breakdown": {
            "sentence_unit_count": sentence_unit_count,
            "gold_pinned_distinct_unit_count": len(gold_pinned),
            "unpinned_sentence_unit_count": unpinned,
            "must_route": {
                "gold_checks": mr_checks,
                "pass": mr_pass,
                "fail": mr_fail,
            },
            "must_abstain": {
                "gold_checks": ma_checks,
                "pass": ma_pass,
                "fail": ma_fail,
            },
            "gold_gate_checks_total": mr_checks + ma_checks,
            "gold_gate_checks_pass": mr_pass + ma_pass,
            "gold_gate_checks_fail": mr_fail + ma_fail,
            "violation_line_count": len(violations),
            "violation_failure_buckets": _violation_failure_buckets(violations),
            "routing_diagnostic_histogram": diag_hist,
            "diagnostic_bucket_expectations": {
                "defined": len(diag_expect),
                "pass": diag_pass,
                "fail": diag_fail,
                "enforce": enforce_diag,
            },
        },
    }
    return violations, telemetry


def collect_stub_stage_bcd_telemetry(grading: dict[str, Any]) -> dict[str, Any]:
    """Placeholder until routing/proposal/retrieval gold lands."""
    return {
        "stage_b_stub": bool(grading.get("gold_routing")),
        "stage_c_stub": bool(grading.get("gold_proposals")),
        "stage_d_stub": bool(grading.get("gold_retrieval")),
    }
