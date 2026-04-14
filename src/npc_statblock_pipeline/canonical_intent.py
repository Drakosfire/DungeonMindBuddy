"""Canonical statblock selection, marker checks, intent classification, planner bridge.

Policy-driven: ``corpus_policy`` supplies ``canonical_statblock_relpath`` and optional
``mechanical_statblock_trace_path_filters`` for tool-trace matching (no hardcoded NPC).
Gold JSON supplies markers, expected CR, planner_bridge intent expectations, etc.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

IntentMode = Literal["factual_lookup", "upgrade_request", "comparison_request"]


def read_paths_from_tool_trace(tool_trace: list[dict[str, Any]]) -> list[str]:
    """``path`` arguments from executed ``read_corpus_file`` calls in order (same semantics as planner live_eval)."""
    paths: list[str] = []
    for row in tool_trace:
        if str(row.get("tool", "")) != "read_corpus_file":
            continue
        args = row.get("arguments") or {}
        p = str(args.get("path", "")).strip()
        if p:
            paths.append(p)
    return paths
PowerAxis = Literal["challenge_rating", "class_level", "hybrid", "unknown"]

SELECTION_RULE_POLICY_CANONICAL = "corpus_policy.canonical_statblock_relpath"


def _norm_rel(p: str) -> str:
    return p.strip().replace("\\", "/")


def select_canonical_statblock_relpath(policy: dict[str, Any]) -> str | None:
    raw = policy.get("canonical_statblock_relpath")
    if isinstance(raw, str) and raw.strip():
        return _norm_rel(raw)
    return None


def build_selection_reason(
    policy: dict[str, Any],
    *,
    outcome: str,
    canon: str | None = None,
) -> dict[str, Any]:
    """Machine-readable trace for why Step 2 picked (or failed to pick) a canonical statblock."""
    out: dict[str, Any] = {
        "rule_id": SELECTION_RULE_POLICY_CANONICAL,
        "outcome": outcome,
        "corpus_policy_schema": policy.get("schema"),
    }
    if policy.get("entity_canonical_name"):
        out["entity_canonical_name"] = policy.get("entity_canonical_name")
    if canon is not None:
        out["canonical_statblock_relpath"] = canon
    return out


def detail_for_cli_stdout(canonical_detail: dict[str, Any], max_extract_chars: int = 80_000) -> dict[str, Any]:
    """Replace huge ``extracted_markdown`` in a copy for terminal JSON."""
    d = copy.deepcopy(canonical_detail)
    em = d.get("extracted_markdown")
    if isinstance(em, str) and len(em) > max_extract_chars:
        d["extracted_markdown"] = (
            f"[{len(em)} characters omitted from CLI stdout; use run_step2_canonical_gates / run_step2_all in Python for full text]"
        )
        d["extracted_markdown_cli_truncated"] = True
    return d


def build_extracted_section_span(corpus_rel: str, extracted: str) -> dict[str, Any]:
    """
    Char offsets into the file as read (UTF-8 decoded ``str``). ``end_char`` is **exclusive**
    (Python slice ``extracted == full_body[start_char:end_char]`` when ``start_char == 0``).
    """
    n = len(extracted)
    return {
        "corpus_relative_path": _norm_rel(corpus_rel),
        "start_char": 0,
        "end_char": n,
        "end_char_exclusive": True,
        "length_chars": n,
    }


def parse_challenge_rating_from_statblock(text: str) -> int | None:
    m = re.search(r"Challenge\s+Rating\s*:\s*(\d+)", text, flags=re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


@dataclass(frozen=True)
class IntentClassification:
    intent_mode: IntentMode
    power_axis: PowerAxis
    clarifier_required: bool
    clarifier_question: str

    def matches_expect(self, expect: dict[str, Any]) -> tuple[bool, list[str]]:
        diffs: list[str] = []
        for key in ("intent_mode", "power_axis", "clarifier_required"):
            if key not in expect:
                continue
            a = getattr(self, key)
            b = expect[key]
            if a != b:
                diffs.append(f"{key}: got {a!r}, expected {b!r}")
        return len(diffs) == 0, diffs


def classify_intent(user_line: str) -> IntentClassification:
    """
    Deterministic heuristic (v1). Tuned for NPC upgrade / prep prompts; not a general NLU.
    """
    text = user_line.strip()
    low = text.lower()

    if re.search(r"\bcr\s*\d+", low) or re.search(r"\bchallenge\s+rating\b", low):
        if re.search(r"\b(to|at)\s+cr\s*\d+", low) or re.search(
            r"\b(bump|raise|increase|set)\b[^.\n]{0,40}\bcr\b", low
        ):
            return IntentClassification(
                intent_mode="upgrade_request",
                power_axis="challenge_rating",
                clarifier_required=False,
                clarifier_question="",
            )

    class_tokens = (
        "fighter",
        "wizard",
        "rogue",
        "cleric",
        "ranger",
        "paladin",
        "bard",
        "monk",
        "barbarian",
        "sorcerer",
        "warlock",
        "druid",
        "artificer",
        "multiclass",
        "class level",
        "character level",
        "player level",
    )
    if any(tok in low for tok in class_tokens) and re.search(
        r"\b(level|levels|level-up|level up)\b", low
    ):
        return IntentClassification(
            intent_mode="upgrade_request",
            power_axis="class_level",
            clarifier_required=False,
            clarifier_question="",
        )

    if "compare" in low or " vs " in low or " versus " in low:
        return IntentClassification(
            intent_mode="comparison_request",
            power_axis="hybrid",
            clarifier_required=False,
            clarifier_question="",
        )

    if "regenerate" in low and "dossier" in low and (
        "statblock" in low or "creature sheet" in low
    ):
        if "only" in low or "do not" in low or "not copy" in low or "ignore" in low:
            return IntentClassification(
                intent_mode="upgrade_request",
                power_axis="unknown",
                clarifier_required=True,
                clarifier_question=(
                    "You asked to rebuild from the dossier without the old mechanical sheet. "
                    "Should the new block follow **CR-based NPC math**, **class-style levels**, "
                    "or a **fresh monster template**?"
                ),
            )

    upgrade_markers = (
        "level up",
        "level-up",
        "level her up",
        "level him up",
        "level them up",
        "new statblock",
        "regenerate her statblock",
        "regenerate his statblock",
        "upgrade her statblock",
        "upgrade his statblock",
        "make her stronger",
        "make him stronger",
        "more powerful",
        "increase her cr",
        "increase his cr",
        "raise her cr",
        "raise his cr",
        "bump her cr",
        "bump his cr",
    )
    if any(m in low for m in upgrade_markers):
        explicit_cr = bool(re.search(r"\bcr\s*\d+", low))
        explicit_class = any(tok in low for tok in class_tokens)
        if explicit_cr and not explicit_class:
            return IntentClassification(
                intent_mode="upgrade_request",
                power_axis="challenge_rating",
                clarifier_required=False,
                clarifier_question="",
            )
        if explicit_class and not explicit_cr:
            return IntentClassification(
                intent_mode="upgrade_request",
                power_axis="class_level",
                clarifier_required=False,
                clarifier_question="",
            )
        if explicit_cr and explicit_class:
            return IntentClassification(
                intent_mode="upgrade_request",
                power_axis="hybrid",
                clarifier_required=True,
                clarifier_question=(
                    "Do you want this upgrade expressed as a CR change, as class levels, "
                    "or both (and which should drive combat stats)?"
                ),
            )
        return IntentClassification(
            intent_mode="upgrade_request",
            power_axis="unknown",
            clarifier_required=True,
            clarifier_question=(
                "When you say “level up,” should I treat this as a **CR increase** for the NPC statblock, "
                "or are you asking for **class-style levels** (PC-style progression)?"
            ),
        )

    statblock_ctx = "statblock" in low or "stat block" in low
    if statblock_ctx and (
        "armor class" in low
        or re.search(r"\bac\b", low)
        or "hit point" in low
        or re.search(r"\bhp\b", low)
        or "saving throw" in low
    ):
        return IntentClassification(
            intent_mode="factual_lookup",
            power_axis="challenge_rating",
            clarifier_required=False,
            clarifier_question="",
        )

    if "challenge rating" in low or re.search(r"\bcr\b", low):
        return IntentClassification(
            intent_mode="factual_lookup",
            power_axis="challenge_rating",
            clarifier_required=False,
            clarifier_question="",
        )

    if "what level" in low or "which level" in low or "how many levels" in low:
        return IntentClassification(
            intent_mode="factual_lookup",
            power_axis="unknown",
            clarifier_required=False,
            clarifier_question="",
        )

    return IntentClassification(
        intent_mode="factual_lookup",
        power_axis="unknown",
        clarifier_required=False,
        clarifier_question="",
    )


def run_step2_canonical_gates(
    corpus_dir: Path,
    *,
    corpus_policy: dict[str, Any],
    step2_gold: dict[str, Any],
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    Returns ``(detail, ok, violations)``.

    ``corpus_policy`` and ``step2_gold`` must be provided (benchmark loads JSON).
    """
    g2 = step2_gold
    violations: list[str] = []

    canon = select_canonical_statblock_relpath(corpus_policy)
    if not canon:
        violations.append("G2.1 FAIL: corpus_policy.canonical_statblock_relpath is missing or empty")
        return {
            "canonical_path": None,
            "selection_reason": build_selection_reason(corpus_policy, outcome="policy_field_missing_or_empty"),
        }, False, violations

    root = corpus_dir.resolve()
    abs_path = (root / canon).resolve()
    try:
        abs_path.relative_to(root)
    except ValueError:
        violations.append(f"G2.1 FAIL: canonical path escapes corpus root: {canon}")
        return {
            "canonical_path": canon,
            "selection_reason": build_selection_reason(
                corpus_policy, outcome="path_escapes_corpus_root", canon=canon
            ),
        }, False, violations

    if not abs_path.is_file():
        violations.append(f"G2.1 FAIL: canonical statblock file missing on disk: {canon}")
        return {
            "canonical_path": canon,
            "selection_reason": build_selection_reason(corpus_policy, outcome="file_not_found", canon=canon),
        }, False, violations

    try:
        body = abs_path.read_text(encoding="utf-8")
    except OSError as e:
        violations.append(f"G2.1 FAIL: could not read canonical statblock ({canon}): {e}")
        return {
            "canonical_path": canon,
            "selection_reason": build_selection_reason(corpus_policy, outcome="read_error", canon=canon),
        }, False, violations

    max_c = g2.get("detail_max_extracted_markdown_chars")
    truncated = False
    if max_c is not None:
        try:
            lim = int(max_c)
        except (TypeError, ValueError):
            lim = 0
        if lim > 0 and len(body) > lim:
            extracted = body[:lim]
            truncated = True
        else:
            extracted = body
    else:
        extracted = body

    markers = [str(m) for m in (g2.get("required_statblock_markers") or []) if str(m).strip()]
    for m in markers:
        if m not in body:
            violations.append(f"G2.2 FAIL: required statblock marker not found in canonical file: {m!r}")

    exp_cr = g2.get("expected_challenge_rating")
    parsed = parse_challenge_rating_from_statblock(body)
    detail: dict[str, Any] = {
        "canonical_path": canon,
        "selection_reason": build_selection_reason(corpus_policy, outcome="selected", canon=canon),
        "extracted_markdown": extracted,
        "extracted_section_span": build_extracted_section_span(canon, extracted),
        "parsed_challenge_rating": parsed,
        "expected_challenge_rating": exp_cr,
        "markers_required": markers,
        "markers_found": {m: (m in body) for m in markers},
    }
    if truncated:
        detail["extracted_markdown_truncated"] = True
        detail["extracted_markdown_full_file_chars"] = len(body)

    if parsed is None:
        violations.append("G2.2b FAIL: could not parse Challenge Rating from canonical statblock")
    elif exp_cr is not None and int(exp_cr) != parsed:
        violations.append(f"G2.2b FAIL: parsed CR {parsed} != gold expected_challenge_rating {exp_cr}")

    return detail, len(violations) == 0, violations


def run_step2_intent_fixture_gates(
    *,
    step2_gold: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Evaluate G2.4.* expectations for each gold fixture (deterministic)."""
    g2 = step2_gold
    violations: list[str] = []
    for fx in g2.get("fixtures") or []:
        fid = str(fx.get("id", "?"))
        ul = str(fx.get("user_line", "")).strip()
        expect = fx.get("expect") or {}
        if not ul:
            violations.append(f"G2.4 FAIL [{fid}]: empty user_line")
            continue
        got = classify_intent(ul)
        ok, diffs = got.matches_expect(expect)
        if not ok:
            for d in diffs:
                violations.append(f"G2.4 FAIL [{fid}]: {d}")
        if bool(expect.get("clarifier_required")) and not got.clarifier_required:
            violations.append(f"G2.4.3 FAIL [{fid}]: expected clarifier_required True, got False")
        if bool(expect.get("clarifier_required")) and not str(got.clarifier_question).strip():
            violations.append(f"G2.4.3 FAIL [{fid}]: clarifier_required but clarifier_question empty")
        if not bool(expect.get("clarifier_required")) and got.clarifier_required:
            violations.append(f"G2.4.3 FAIL [{fid}]: expected clarifier_required False, got True")

    return len(violations) == 0, violations


def run_step2_all(
    corpus_dir: Path,
    *,
    corpus_policy: dict[str, Any],
    step2_gold: dict[str, Any],
) -> tuple[dict[str, Any], bool, list[str]]:
    """Canonical gates + intent fixture gates."""
    all_v: list[str] = []
    detail, ok_c, v_c = run_step2_canonical_gates(
        corpus_dir, corpus_policy=corpus_policy, step2_gold=step2_gold
    )
    all_v.extend(v_c)
    ok_i, v_i = run_step2_intent_fixture_gates(step2_gold=step2_gold)
    all_v.extend(v_i)
    out = {"canonical_detail": detail, "intent_fixtures_ok": ok_i}
    return out, ok_c and ok_i, all_v


def statblock_trace_reads_matching_policy(read_paths: list[str], policy: dict[str, Any]) -> list[str]:
    """
    ``read_corpus_file`` paths that count as “this entity’s mechanical statblock” for the planner bridge.

    Controlled by ``corpus_policy.mechanical_statblock_trace_path_filters``:

    - ``all_substrings_ignore_case`` (list[str]): every entry must appear as a substring of the path
      (case-insensitive).
    - ``path_suffix_ignore_case`` (str, optional): if set, path must end with this suffix (default ``.md``).

    If filters are missing or ``all_substrings_ignore_case`` is empty, returns ``[]`` (bridge does not
    infer entity statblock reads from the trace).
    """
    raw = policy.get("mechanical_statblock_trace_path_filters")
    if not isinstance(raw, dict):
        return []
    subs = [str(x).strip() for x in (raw.get("all_substrings_ignore_case") or []) if str(x).strip()]
    if not subs:
        return []
    sfx_raw = raw.get("path_suffix_ignore_case")
    sfx = ".md" if sfx_raw is None else str(sfx_raw).strip().lower()
    if not sfx:
        sfx = ".md"
    out: list[str] = []
    for p in read_paths:
        n = _norm_rel(p).lower()
        if not all(s.lower() in n for s in subs):
            continue
        if not n.endswith(sfx):
            continue
        out.append(_norm_rel(p))
    return out


def run_step2_planner_bridge(
    *,
    user_message: str,
    tool_trace: list[dict[str, Any]],
    planner_scenario_key: str,
    corpus_policy: dict[str, Any],
    step2_gold: dict[str, Any],
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    After a planner turn: classify ``user_message``, and optionally assert statblock reads
    in ``tool_trace`` include ``corpus_policy.canonical_statblock_relpath`` when policy filters
    matched any read path.

    ``step2_gold`` → ``planner_bridge`` (optional). If absent or empty, returns ``({}, True, [])``.
    """
    g2 = step2_gold
    cfg = g2.get("planner_bridge")
    if not isinstance(cfg, dict) or not cfg:
        return {}, True, []

    violations: list[str] = []
    detail: dict[str, Any] = {"planner_scenario_key": planner_scenario_key}

    expect_map = cfg.get("intent_expectations_by_planner_scenario_key") or {}
    expect = expect_map.get(planner_scenario_key) if isinstance(expect_map, dict) else None
    got = classify_intent(user_message)
    detail["intent_from_planner_user_message"] = {
        "intent_mode": got.intent_mode,
        "power_axis": got.power_axis,
        "clarifier_required": got.clarifier_required,
    }

    if isinstance(expect, dict) and expect:
        ok_m, diffs = got.matches_expect(expect)
        if not ok_m:
            for d in diffs:
                violations.append(f"BRIDGE intent [{planner_scenario_key}]: {d}")
        if bool(expect.get("clarifier_required")) and not got.clarifier_required:
            violations.append(
                f"BRIDGE intent [{planner_scenario_key}]: expected clarifier_required True, got False"
            )
        if bool(expect.get("clarifier_required")) and not str(got.clarifier_question).strip():
            violations.append(
                f"BRIDGE intent [{planner_scenario_key}]: clarifier_required but clarifier_question empty"
            )
        if not bool(expect.get("clarifier_required")) and got.clarifier_required:
            violations.append(
                f"BRIDGE intent [{planner_scenario_key}]: expected clarifier_required False, got True"
            )

    if cfg.get("assert_statblock_read_matches_canonical_when_present"):
        canon = select_canonical_statblock_relpath(corpus_policy)
        trace_paths = read_paths_from_tool_trace(tool_trace)
        reads = statblock_trace_reads_matching_policy(trace_paths, corpus_policy)
        detail["mechanical_statblock_reads_in_trace"] = reads
        detail["canonical_statblock_relpath"] = canon
        if reads and canon:
            cn = _norm_rel(canon).lower()
            read_lower = {_norm_rel(p).lower() for p in reads}
            if cn not in read_lower:
                violations.append(
                    "BRIDGE trace: mechanical statblock read(s) "
                    f"{reads!r} but corpus_policy.canonical_statblock_relpath "
                    f"{_norm_rel(canon)!r} was never opened."
                )

    return detail, len(violations) == 0, violations
