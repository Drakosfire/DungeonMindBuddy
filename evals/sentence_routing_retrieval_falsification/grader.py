"""Gates for ``sentence_routing_retrieval_falsification`` (legacy stage letters in function names).

- **``capture_sentence_units`` (legacy: Stage A — deterministic capture):** ``collect_stage_a_violations``.
- **``route_sentence_units_to_hubs`` (legacy: Stage B — hub routing):** ``collect_stage_b_violations``.
- **Later pipeline steps (legacy: Stages C–D):** proposal/retrieval graders still TBD; ``collect_stub_stage_bcd_telemetry`` only flags presence of gold keys for sidecars emitted from capture-only runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from copy import deepcopy

from evals.sentence_routing_retrieval_falsification.capture import SentenceUnit
from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow


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
) -> tuple[list[str], dict[str, Any]]:
    """Hub-routing gates B0–B2 (hard; legacy: Stage B); B3 soft limits only in telemetry (DESIGN §6.4)."""
    violations: list[str] = []
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

    for g in gold_routing.get("must_route") or []:
        if not isinstance(g, dict):
            violations.append(f"B1: must_route entry is not an object: {g!r}")
            continue
        uid = str(g.get("unit_id") or "").strip()
        if not uid:
            violations.append(f"B1: must_route missing unit_id: {g!r}")
            continue
        row = by_id.get(uid)
        if row is None:
            continue
        exp = [str(x).strip() for x in (g.get("expected_hubs") or []) if str(x).strip()]
        assigned = set(row.assigned_hubs)
        miss = [h for h in exp if h not in assigned]
        if miss:
            violations.append(
                f"B1: must_route unit {uid!r} missing expected hubs {miss} "
                f"(assigned={sorted(assigned)})"
            )
        max_extra = g.get("max_extra_hubs")
        if max_extra is not None:
            me = int(max_extra)
            max_allowed = len(exp) + me
            if len(row.assigned_hubs) > max_allowed:
                violations.append(
                    f"B1: must_route unit {uid!r} over-route: len(assigned_hubs)={len(row.assigned_hubs)} "
                    f"> len(expected_hubs)+max_extra_hubs={max_allowed}"
                )

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

    telemetry: dict[str, Any] = {
        "routes_row_count": n,
        "mean_assigned_hubs": round(mean_assigned, 6),
        "unresolved_fraction": round(unresolved_fraction, 6),
        "assigned_hubs_count_histogram": hist,
        "needs_new_hub_candidate_count": sum(1 for r in routes if r.needs_new_hub_candidate),
        "stage_b_soft_warnings": soft_warnings,
    }
    return violations, telemetry


def collect_stub_stage_bcd_telemetry(grading: dict[str, Any]) -> dict[str, Any]:
    """Placeholder until routing/proposal/retrieval gold lands."""
    return {
        "stage_b_stub": bool(grading.get("gold_routing")),
        "stage_c_stub": bool(grading.get("gold_proposals")),
        "stage_d_stub": bool(grading.get("gold_retrieval")),
    }
