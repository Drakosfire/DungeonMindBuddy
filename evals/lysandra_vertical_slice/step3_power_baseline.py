"""Step 3 — ``power_baseline`` + evidence spans (Lysandra vertical slice).

Gates (see ``gold/step3_power_baseline.json`` and ``GATES.md``):

- **G3.1** ``challenge_rating_current`` matches gold when CR parses from canonical body.
- **G3.2** Each evidence span slices to **verbatim** text in the same UTF-8 body used for extraction.
- **G3.3** ``class_level_current`` may be ``null`` (v1: always null from statblock).
- **G3.4** If CR line is absent, apply ``fallback_when_cr_absent`` from gold.

Inputs: Step 2 ``canonical_detail`` (preferred) or run ``run_step2_canonical_gates`` first.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_SLICE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = str(_SLICE_DIR.parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from evals.lysandra_vertical_slice.step0_corpus_environment import load_step0_gold, resolve_corpus_dir
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy
from evals.lysandra_vertical_slice.step2_canonical_intent import (
    build_step2_intent_fixture_sequence_client,
    load_step2_gold,
    parse_challenge_rating_from_statblock,
    run_step2_canonical_gates,
    run_step2_intent_fixture_gates,
)
from src.agent.synthesis import _load_api_key


def _norm_rel(p: str) -> str:
    return p.strip().replace("\\", "/")


def step3_gold_path() -> Path:
    return _SLICE_DIR / "gold" / "step3_power_baseline.json"


def load_step3_gold() -> dict[str, Any]:
    return json.loads(step3_gold_path().read_text(encoding="utf-8"))


# One logical line each (RulesIngestion / markdown statblock surface).
_SPAN_PATTERNS: dict[str, re.Pattern[str]] = {
    "challenge_rating": re.compile(r"^[ \t]*Challenge\s+Rating\s*:.*$", re.MULTILINE | re.IGNORECASE),
    "armor_class": re.compile(r"^[ \t]*Armor\s+Class\s*:.*$", re.MULTILINE | re.IGNORECASE),
    "hit_points": re.compile(r"^[ \t]*Hit\s+Points.*$", re.MULTILINE | re.IGNORECASE),
}


def extract_evidence_spans_for_fields(
    body: str,
    corpus_relative_path: str,
    fields: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Build ``evidence_spans`` entries with ``start_char`` / ``end_char`` (**end_char** exclusive,
    i.e. ``body[start:end]``) and ``verbatim`` equal to that slice.
    """
    violations: list[str] = []
    spans: list[dict[str, Any]] = []
    path_n = _norm_rel(corpus_relative_path)
    for field in fields:
        pat = _SPAN_PATTERNS.get(field)
        if not pat:
            violations.append(f"G3.2 FAIL: unknown evidence_span_field {field!r}")
            continue
        m = pat.search(body)
        if not m:
            violations.append(f"G3.2 FAIL: no line match for field {field!r} in {path_n!r}")
            continue
        start, end = m.start(), m.end()
        verbatim = body[start:end]
        if body[start:end] != verbatim:
            violations.append(f"G3.2 FAIL: internal span mismatch for field {field!r}")
            continue
        spans.append(
            {
                "field": field,
                "corpus_relative_path": path_n,
                "start_char": start,
                "end_char": end,
                "end_char_exclusive": True,
                "verbatim": verbatim,
            }
        )
    return spans, violations


def _load_statblock_body(
    corpus_dir: Path,
    canonical_path: str,
    step2_canonical_detail: dict[str, Any],
) -> str:
    """Prefer Step 2 extract when it is the full file; otherwise read from disk."""
    if step2_canonical_detail.get("extracted_markdown_truncated"):
        return (corpus_dir / canonical_path).read_text(encoding="utf-8", errors="replace")
    em = step2_canonical_detail.get("extracted_markdown")
    if isinstance(em, str) and em.strip():
        return em
    return (corpus_dir / canonical_path).read_text(encoding="utf-8", errors="replace")


def run_step3_power_baseline_gates(
    corpus_dir: Path,
    *,
    step2_canonical_detail: dict[str, Any] | None = None,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
    step3_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    Returns ``(detail, ok, violations)``.

    If ``step2_canonical_detail`` is omitted, runs ``run_step2_canonical_gates`` first; if Step 2
    fails, Step 3 does not run (violations reference Step 2).
    """
    root = corpus_dir.resolve()
    policy = corpus_policy or load_corpus_policy()
    s2g = step2_gold or load_step2_gold()
    s3g = step3_gold or load_step3_gold()
    violations: list[str] = []

    if step2_canonical_detail is None:
        d2, ok2, v2 = run_step2_canonical_gates(root, corpus_policy=policy, step2_gold=s2g)
        if not ok2:
            violations.append(f"STEP3 blocked: Step 2 canonical gates failed: {v2}")
            return {"step2_canonical_detail": d2, "step2_violations": v2}, False, violations
        step2_canonical_detail = d2

    sr = step2_canonical_detail.get("selection_reason") or {}
    if sr.get("outcome") != "selected":
        violations.append(f"STEP3 blocked: Step 2 selection_reason.outcome is not 'selected': {sr!r}")
        return {"step2_canonical_detail": step2_canonical_detail}, False, violations

    canon = step2_canonical_detail.get("canonical_path")
    if not isinstance(canon, str) or not canon.strip():
        violations.append("STEP3 blocked: missing canonical_path in Step 2 detail")
        return {"step2_canonical_detail": step2_canonical_detail}, False, violations

    body = _load_statblock_body(root, canon, step2_canonical_detail)
    cr = parse_challenge_rating_from_statblock(body)
    exp_pb = s3g.get("expected_power_baseline") or {}

    if cr is None:
        fb = s3g.get("fallback_when_cr_absent")
        if not isinstance(fb, dict):
            violations.append("G3.4 FAIL: CR absent in canonical statblock and no fallback_when_cr_absent in gold")
            return {"step2_canonical_detail": step2_canonical_detail}, False, violations
        pb = dict(fb.get("power_baseline") or {})
        spans = list(fb.get("evidence_spans") or [])
        detail: dict[str, Any] = {
            "canonical_path": _norm_rel(canon),
            "power_baseline": pb,
            "evidence_spans": spans,
            "challenge_rating_parse_failed": True,
            "step2_canonical_detail": step2_canonical_detail,
        }
        return detail, len(violations) == 0, violations

    power_baseline: dict[str, Any] = {
        "challenge_rating_current": cr,
        "class_level_current": None,
        "class_level_source": None,
        "axis_source": str(exp_pb.get("axis_source") or "canonical_statblock"),
        "extraction_method": str(exp_pb.get("extraction_method") or "statblock_marker_parse"),
    }

    exp_cr = exp_pb.get("challenge_rating_current")
    if exp_cr is not None and int(exp_cr) != int(cr):
        violations.append(f"G3.1 FAIL: challenge_rating_current {cr} != gold expected {exp_cr}")

    exp_cl = exp_pb.get("class_level_current")
    if exp_cl is not None and power_baseline.get("class_level_current") != exp_cl:
        violations.append(f"G3.3 FAIL: class_level_current {power_baseline.get('class_level_current')!r} != gold {exp_cl!r}")
    if exp_pb.get("class_level_current") is None and power_baseline.get("class_level_current") is not None:
        violations.append("G3.3 FAIL: gold expects class_level_current null but baseline is non-null")

    fields = [str(x) for x in (s3g.get("evidence_span_fields") or []) if str(x).strip()]
    spans, span_v = extract_evidence_spans_for_fields(body, canon, fields)
    violations.extend(span_v)

    for sp in spans:
        s, e = int(sp["start_char"]), int(sp["end_char"])
        if s < 0 or e > len(body) or s > e:
            violations.append(f"G3.2 FAIL: span out of range for field={sp.get('field')!r} [{s},{e}) len={len(body)}")
            continue
        if body[s:e] != sp.get("verbatim"):
            violations.append(f"G3.2 FAIL: verbatim mismatch field={sp.get('field')!r}")

    detail = {
        "canonical_path": _norm_rel(canon),
        "power_baseline": power_baseline,
        "evidence_spans": spans,
        "step2_canonical_detail": step2_canonical_detail,
    }
    return detail, len(violations) == 0, violations


def run_step2_and_step3(
    corpus_dir: Path | None = None,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
    step3_gold: dict[str, Any] | None = None,
    intent_client: Any | None = None,
    intent_model: str | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """Run Step 2 canonical + intent fixtures, then Step 3 (aggregate for harness / CLI)."""
    root = corpus_dir or resolve_corpus_dir(load_step0_gold())
    policy = corpus_policy or load_corpus_policy()
    s2g = step2_gold or load_step2_gold()
    s3g = step3_gold or load_step3_gold()
    all_v: list[str] = []

    d2, ok2, v2 = run_step2_canonical_gates(root, corpus_policy=policy, step2_gold=s2g)
    all_v.extend(v2)
    ok_i, v_i = run_step2_intent_fixture_gates(
        step2_gold=s2g, client=intent_client, model=intent_model
    )
    all_v.extend(v_i)
    out: dict[str, Any] = {"canonical_detail": d2, "intent_fixtures_ok": ok_i}
    if not ok2 or not ok_i:
        return out, False, all_v

    d3, ok3, v3 = run_step3_power_baseline_gates(
        root, step2_canonical_detail=d2, corpus_policy=policy, step2_gold=s2g, step3_gold=s3g
    )
    all_v.extend(v3)
    out["power_baseline_detail"] = d3
    return out, ok3, all_v


def main() -> None:
    root = resolve_corpus_dir(load_step0_gold())
    s2g = load_step2_gold()
    intent_client = None
    if _load_api_key() is None:
        intent_client = build_step2_intent_fixture_sequence_client(s2g)
    out, ok, viol = run_step2_and_step3(root, step2_gold=s2g, intent_client=intent_client)
    print(json.dumps({"corpus_dir": str(root), "ok": ok, "detail": out}, indent=2, ensure_ascii=False))
    if viol:
        print("--- violations ---", file=sys.stderr)
        for line in viol:
            print(line, file=sys.stderr)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
