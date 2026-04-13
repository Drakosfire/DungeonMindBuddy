"""Step 2 — canonical statblock selection + marker checks + intent classification (Lysandra vertical slice).

Implements draft gates:

- **G2.1** Selected canonical statblock path matches ``corpus_policy.canonical_statblock_relpath``.
- **G2.2** Statblock markdown contains required marker substrings from gold.
- **G2.2b** Parsed challenge rating from statblock text matches ``gold.expected_challenge_rating``.
- **G2.3** Single canonical path (policy must not list ties; we only read one file).
- **G2.4.1–G2.4.4** Deterministic heuristic classifier vs gold fixtures (no LLM).

See ``gold/step2_canonical_and_intent.json`` and ``Docs/Plans/DESIGN-lysandra-statblock-vertical-slice-benchmark.md`` §6.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_SLICE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = str(_SLICE_DIR.parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evals.lysandra_vertical_slice.step0_corpus_environment import load_step0_gold, resolve_corpus_dir
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy


IntentMode = Literal["factual_lookup", "upgrade_request", "comparison_request"]
PowerAxis = Literal["challenge_rating", "class_level", "hybrid", "unknown"]


def step2_gold_path() -> Path:
    return _SLICE_DIR / "gold" / "step2_canonical_and_intent.json"


def load_step2_gold() -> dict[str, Any]:
    return json.loads(step2_gold_path().read_text(encoding="utf-8"))


def _norm_rel(p: str) -> str:
    return p.strip().replace("\\", "/")


def select_canonical_statblock_relpath(policy: dict[str, Any]) -> str | None:
    raw = policy.get("canonical_statblock_relpath")
    if isinstance(raw, str) and raw.strip():
        return _norm_rel(raw)
    return None


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
    Deterministic heuristic (v1). Tuned for Lysandra slice prompts; not a general NLU.

    Priority:
    1. Explicit numeric CR targets -> upgrade + challenge_rating
    2. Explicit class / level-up phrasing with class context -> upgrade + class_level
    3. Comparison language -> comparison + hybrid (unless only CR is mentioned and no table contrast)
    4. Upgrade phrasing without axis -> upgrade + unknown + clarifier
    5. Else factual; axis defaults to challenge_rating when CR is asked, else unknown without clarifier
    """
    text = user_line.strip()
    low = text.lower()

    # --- explicit targets ---
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
        # Table vs sheet contrast usually mixes mechanical + played canon.
        return IntentClassification(
            intent_mode="comparison_request",
            power_axis="hybrid",
            clarifier_required=False,
            clarifier_question="",
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

    # --- factual ---
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
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    Returns ``(detail, ok, violations)``.

    ``detail`` includes: ``canonical_path``, ``parsed_challenge_rating``, marker checks.
    """
    policy = corpus_policy or load_corpus_policy()
    g2 = step2_gold or load_step2_gold()
    violations: list[str] = []

    canon = select_canonical_statblock_relpath(policy)
    if not canon:
        violations.append("G2.1 FAIL: corpus_policy.canonical_statblock_relpath is missing or empty")
        return {"canonical_path": None}, False, violations

    root = corpus_dir.resolve()
    abs_path = (root / canon).resolve()
    try:
        abs_path.relative_to(root)
    except ValueError:
        violations.append(f"G2.1 FAIL: canonical path escapes corpus root: {canon}")
        return {"canonical_path": canon}, False, violations

    if not abs_path.is_file():
        violations.append(f"G2.1 FAIL: canonical statblock file missing on disk: {canon}")
        return {"canonical_path": canon}, False, violations

    try:
        body = abs_path.read_text(encoding="utf-8")
    except OSError as e:
        violations.append(f"G2.1 FAIL: could not read canonical statblock ({canon}): {e}")
        return {"canonical_path": canon}, False, violations

    markers = [str(m) for m in (g2.get("required_statblock_markers") or []) if str(m).strip()]
    for m in markers:
        if m not in body:
            violations.append(f"G2.2 FAIL: required statblock marker not found in canonical file: {m!r}")

    exp_cr = g2.get("expected_challenge_rating")
    parsed = parse_challenge_rating_from_statblock(body)
    detail: dict[str, Any] = {
        "canonical_path": canon,
        "parsed_challenge_rating": parsed,
        "expected_challenge_rating": exp_cr,
        "markers_required": markers,
        "markers_found": {m: (m in body) for m in markers},
    }

    if parsed is None:
        violations.append("G2.2b FAIL: could not parse Challenge Rating from canonical statblock")
    elif exp_cr is not None and int(exp_cr) != parsed:
        violations.append(f"G2.2b FAIL: parsed CR {parsed} != gold expected_challenge_rating {exp_cr}")

    return detail, len(violations) == 0, violations


def run_step2_intent_fixture_gates(
    *,
    step2_gold: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Evaluate G2.4.* expectations for each gold fixture (deterministic)."""
    g2 = step2_gold or load_step2_gold()
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
    corpus_dir: Path | None = None,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """Canonical gates + intent fixture gates."""
    root = corpus_dir or resolve_corpus_dir(load_step0_gold())
    policy = corpus_policy or load_corpus_policy()
    g2 = step2_gold or load_step2_gold()
    all_v: list[str] = []
    detail, ok_c, v_c = run_step2_canonical_gates(root, corpus_policy=policy, step2_gold=g2)
    all_v.extend(v_c)
    ok_i, v_i = run_step2_intent_fixture_gates(step2_gold=g2)
    all_v.extend(v_i)
    out = {"canonical_detail": detail, "intent_fixtures_ok": ok_i}
    return out, ok_c and ok_i, all_v


def main() -> None:
    root = resolve_corpus_dir(load_step0_gold())
    detail, ok, viol = run_step2_all(root)
    print(json.dumps({"corpus_dir": str(root), "ok": ok, "detail": detail}, indent=2, ensure_ascii=False))
    if viol:
        print("--- violations ---", file=sys.stderr)
        for line in viol:
            print(line, file=sys.stderr)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
