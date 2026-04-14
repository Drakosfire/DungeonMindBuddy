"""Step 4 — deterministic **level-up context bundle** (Lysandra vertical slice).

Assembles a **structured bundle** for gates, regression, and tooling: ``power_baseline``,
``target_challenge_rating``, statblock + dossier + **timeline** excerpts (``timeline_relpath``),
optional ``session_anchor`` excerpt, and **keyword-ranked** recap snippets.

Bundle JSON is for **gates and humans only**. Nothing here is assembled for an agent.
Context discovery is the agent's job, not the harness's.

**Not in v1:** validating free-form model prose, ``level_up_request`` JSON schema, or
``G2.4`` clarifier simulation (bundle assumes upgrade-to-gold-target-CR path).
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
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy, score_text_for_aliases
from evals.lysandra_vertical_slice.step2_canonical_intent import (
    load_step2_gold,
    run_step2_canonical_gates,
)
from evals.lysandra_vertical_slice.step3_power_baseline import (
    load_step3_gold,
    run_step2_and_step3,
    run_step3_power_baseline_gates,
)

_CAMPAIGN_RE = re.compile(r"Campaign\s+(\d+)", re.IGNORECASE)
_SESSION_RE = re.compile(r"Session\s+(\d+)", re.IGNORECASE)


def _norm_rel(p: str) -> str:
    return p.strip().replace("\\", "/")


def step4_gold_path() -> Path:
    return _SLICE_DIR / "gold" / "step4_levelup_context.json"


def load_step4_gold() -> dict[str, Any]:
    return json.loads(step4_gold_path().read_text(encoding="utf-8"))


def _recap_sort_key(rel: str, score: int) -> tuple[int, int, int, str]:
    c_m = _CAMPAIGN_RE.search(rel)
    s_m = _SESSION_RE.search(rel)
    camp = int(c_m.group(1)) if c_m else 0
    sess = int(s_m.group(1)) if s_m else 0
    return (-score, -camp, -sess, rel)


def _path_allowed(rel: str, allowed_prefixes: list[str]) -> bool:
    return any(rel.startswith(pref) for pref in allowed_prefixes)


def _theme_boost_score(text: str, keywords: list[str], per_hit: int) -> int:
    if per_hit <= 0 or not keywords:
        return 0
    low = text.lower()
    total = 0
    for kw in keywords:
        k = str(kw).strip().lower()
        if not k:
            continue
        total += per_hit * low.count(k)
    return total


def _path_bonus(rel: str, bonuses: dict[str, int]) -> int:
    extra = 0
    for frag, pts in (bonuses or {}).items():
        f = str(frag).strip()
        if f and f in rel:
            extra += int(pts)
    return extra


def _first_alias_anchor_span(text: str, aliases: list[str]) -> tuple[int, int] | None:
    low = text.lower()
    ordered = sorted((str(a).strip() for a in aliases if str(a).strip()), key=len, reverse=True)
    for a in ordered:
        pos = low.find(a.lower())
        if pos >= 0:
            return pos, pos + len(a)
    return None


def _snippet_around_anchor(
    text: str,
    aliases: list[str],
    before: int,
    after: int,
) -> tuple[int, int, str]:
    span = _first_alias_anchor_span(text, aliases)
    if span is None:
        e = min(len(text), 400)
        return 0, e, text[:e]
    lo, hi = span
    s = max(0, lo - max(0, before))
    e = min(len(text), hi + max(0, after))
    return s, e, text[s:e]


def _iter_paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Blank-line paragraph boundaries as ``(start, end)`` indices in ``text``."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in re.finditer(r"\n\s*\n+", text):
        if m.start() > start:
            spans.append((start, m.start()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _best_paragraph_snippet(
    text: str,
    aliases: list[str],
    theme_words: list[str],
    theme_boost: int,
    max_para_chars: int,
) -> tuple[int, int, str] | None:
    """Pick the paragraph block with highest alias + theme score."""
    best: tuple[int, int, int] | None = None  # lo, hi, score
    for lo, hi in _iter_paragraph_spans(text):
        raw = text[lo:hi]
        if not raw.strip():
            continue
        alias_hits = score_text_for_aliases(raw, aliases)
        if alias_hits <= 0:
            continue
        sc = alias_hits + _theme_boost_score(raw, theme_words, theme_boost)
        if sc <= 0:
            continue
        if best is None or sc > best[2]:
            best = (lo, hi, sc)
    if best is None:
        return None
    lo, hi, _ = best
    cap = max(200, int(max_para_chars))
    raw = text[lo:hi]
    if len(raw) > cap:
        raw = raw[:cap]
        hi = lo + len(raw)
    return lo, hi, raw


def _recap_snippet_for_file(
    full_text: str,
    *,
    aliases: list[str],
    g4: dict[str, Any],
) -> tuple[int, int, str]:
    mode = str(g4.get("recap_snippet_mode") or "best_scoring_paragraph").strip().lower()
    themes = [str(x) for x in (g4.get("theme_boost_keywords") or []) if str(x).strip()]
    t_boost = int(g4.get("theme_boost_score_per_occurrence") or 0)
    max_para = int(g4.get("max_chars_per_recap_paragraph") or 2400)
    if mode in ("best_scoring_paragraph", "best_paragraph_by_score"):
        got = _best_paragraph_snippet(full_text, aliases, themes, t_boost, max_para)
        if got is not None:
            return got
    before = int(g4.get("snippet_chars_before_anchor") or 400)
    after = int(g4.get("snippet_chars_after_anchor") or 400)
    return _snippet_around_anchor(full_text, aliases, before, after)


def _scan_recap_scores(
    corpus_dir: Path,
    *,
    corpus_policy: dict[str, Any],
    step4_gold: dict[str, Any],
) -> list[tuple[str, int, str]]:
    """Return list of (rel_posix, score, raw_text) for markdown under recap dirs."""
    aliases = [str(x) for x in (corpus_policy.get("aliases") or []) if str(x).strip()]
    allowed = [str(p) for p in (corpus_policy.get("corpus_roots_allowed_prefixes") or []) if str(p).strip()]
    dirs = [str(d).strip().rstrip("/") for d in (step4_gold.get("recap_scan_relative_dirs") or []) if str(d).strip()]
    cap = max(1000, int(step4_gold.get("max_chars_per_recap_read") or 500_000))
    themes = [str(x) for x in (step4_gold.get("theme_boost_keywords") or []) if str(x).strip()]
    t_boost = int(step4_gold.get("theme_boost_score_per_occurrence") or 0)
    bonuses = step4_gold.get("path_substring_score_bonus") or {}
    if isinstance(bonuses, dict):
        pb = {str(k): int(v) for k, v in bonuses.items() if str(k).strip()}
    else:
        pb = {}

    out: list[tuple[str, int, str]] = []
    for d in dirs:
        root = corpus_dir / d
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if not path.is_file():
                continue
            try:
                rel = _norm_rel(path.relative_to(corpus_dir).as_posix())
            except ValueError:
                continue
            if not _path_allowed(rel, allowed):
                continue
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError:
                continue
            body = raw[:cap]
            score = score_text_for_aliases(body, aliases)
            score += _theme_boost_score(body, themes, t_boost)
            score += _path_bonus(rel, pb)
            if score <= 0:
                continue
            out.append((rel, score, raw))

    out.sort(key=lambda t: _recap_sort_key(t[0], t[1]))
    return out


def _load_statblock_excerpt(
    corpus_dir: Path,
    step2_detail: dict[str, Any],
    max_chars: int,
) -> tuple[str, str]:
    """Return (path, excerpt) from Step 2 canonical extract or disk."""
    canon = step2_detail.get("canonical_path")
    if not isinstance(canon, str) or not canon.strip():
        return "", ""
    path = _norm_rel(canon)
    if step2_detail.get("extracted_markdown_truncated"):
        body = (corpus_dir / path).read_text(encoding="utf-8", errors="replace")
    else:
        em = step2_detail.get("extracted_markdown")
        body = em if isinstance(em, str) and em.strip() else (corpus_dir / path).read_text(
            encoding="utf-8", errors="replace"
        )
    mc = max(0, int(max_chars))
    return path, body[:mc] if mc else body


def _load_dossier_excerpt(corpus_dir: Path, policy: dict[str, Any], max_chars: int) -> tuple[str, str]:
    rel = policy.get("primary_reference_relpath")
    if not isinstance(rel, str) or not rel.strip():
        return "", ""
    p = _norm_rel(rel)
    path = corpus_dir / p
    if not path.is_file():
        return p, ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    mc = max(0, int(max_chars))
    return p, raw[:mc] if mc else raw


def _load_anchor_excerpt(corpus_dir: Path, policy: dict[str, Any], max_chars: int) -> tuple[str, str]:
    rel = policy.get("session_anchor_relpath")
    if not isinstance(rel, str) or not rel.strip():
        return "", ""
    p = _norm_rel(rel)
    path = corpus_dir / p
    if not path.is_file():
        return p, ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    mc = max(0, int(max_chars))
    return p, raw[:mc] if mc else raw


def _load_timeline_excerpt(corpus_dir: Path, policy: dict[str, Any], max_chars: int) -> tuple[str, str]:
    """``corpus_policy.timeline_relpath`` — benchmark / bundle tools only; not a planner instruction leak."""
    rel = policy.get("timeline_relpath")
    if not isinstance(rel, str) or not rel.strip():
        return "", ""
    p = _norm_rel(rel)
    path = corpus_dir / p
    if not path.is_file():
        return p, ""
    raw = path.read_text(encoding="utf-8", errors="replace")
    mc = max(0, int(max_chars))
    return p, raw[:mc] if mc else raw


def build_levelup_context_bundle(
    corpus_dir: Path,
    *,
    step3_detail: dict[str, Any],
    corpus_policy: dict[str, Any] | None = None,
    step4_gold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure builder (no gate violations). Requires successful Step 3 ``detail`` shape."""
    root = corpus_dir.resolve()
    policy = corpus_policy or load_corpus_policy()
    g4 = step4_gold or load_step4_gold()
    step2 = step3_detail.get("step2_canonical_detail") or {}
    pb = dict(step3_detail.get("power_baseline") or {})
    target_cr = int(g4["target_challenge_rating"])

    stat_path, stat_excerpt = _load_statblock_excerpt(
        root, step2, int(g4.get("max_statblock_chars_for_bundle") or 28_000)
    )
    dos_path, dos_excerpt = _load_dossier_excerpt(
        root, policy, int(g4.get("max_dossier_chars") or 12_000)
    )
    tl_path, tl_excerpt = _load_timeline_excerpt(
        root, policy, int(g4.get("max_timeline_chars") or 16_000)
    )

    anchor: dict[str, Any] = {}
    if g4.get("include_session_anchor_excerpt", True):
        ap, atxt = _load_anchor_excerpt(root, policy, int(g4.get("session_anchor_max_chars") or 12_000))
        if ap:
            anchor = {"corpus_relative_path": ap, "text": atxt}

    aliases = [str(x) for x in (policy.get("aliases") or []) if str(x).strip()]
    ranked = _scan_recap_scores(root, corpus_policy=policy, step4_gold=g4)
    n_take = max(1, int(g4.get("max_recap_files_to_snippetize") or 4))

    snippets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel, score, raw in ranked:
        if len(snippets) >= n_take:
            break
        if rel in seen:
            continue
        seen.add(rel)
        s, e, verb = _recap_snippet_for_file(raw, aliases=aliases, g4=g4)
        snippets.append(
            {
                "corpus_relative_path": rel,
                "keyword_score": score,
                "start_char": s,
                "end_char": e,
                "end_char_exclusive": True,
                "verbatim": verb,
            }
        )

    cur = pb.get("challenge_rating_current")
    cur_s = str(cur) if cur is not None else "unknown"
    instr = (
        f"Raise this NPC from CR {cur_s} to CR {target_cr} for the next mechanical export. "
        "Use recap tone (fatigue, command pressure, recent hazards) only when supported by recap "
        "files actually read from the corpus; do not invent sessions."
    )

    bundle: dict[str, Any] = {
        "entity_canonical_name": policy.get("entity_canonical_name"),
        "power_baseline": pb,
        "power_target": {"target_challenge_rating": target_cr, "axis": "challenge_rating"},
        "evidence_spans_from_step3": step3_detail.get("evidence_spans") or [],
        "statblock_excerpt": {"corpus_relative_path": stat_path, "text": stat_excerpt},
        "dossier_excerpt": {"corpus_relative_path": dos_path, "text": dos_excerpt},
        "timeline_excerpt": {"corpus_relative_path": tl_path, "text": tl_excerpt},
        "session_anchor_excerpt": anchor,
        "session_recap_snippets": snippets,
        "recap_ranking_meta": {
            "scored_files_considered": len(ranked),
            "recap_snippet_mode": g4.get("recap_snippet_mode") or "best_scoring_paragraph",
            "theme_boost_keywords": g4.get("theme_boost_keywords") or [],
        },
        "upgrade_instrumentation": instr,
    }
    return bundle


def run_step4_levelup_context_gates(
    corpus_dir: Path,
    *,
    step3_detail: dict[str, Any] | None = None,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
    step3_gold: dict[str, Any] | None = None,
    step4_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """
    If ``step3_detail`` is omitted, runs Step 2 canonical + Step 3 first (intent fixtures not run).

    For the full eval aggregate including intent fixtures, use ``run_step2_through_step4``.
    """
    root = corpus_dir.resolve()
    policy = corpus_policy or load_corpus_policy()
    s2g = step2_gold or load_step2_gold()
    s3g = step3_gold or load_step3_gold()
    g4 = step4_gold or load_step4_gold()
    violations: list[str] = []

    if step3_detail is None:
        d2, ok2, v2 = run_step2_canonical_gates(root, corpus_policy=policy, step2_gold=s2g)
        if not ok2:
            violations.append(f"STEP4 blocked: Step 2 canonical failed: {v2}")
            return {"step2_canonical_detail": d2, "step2_violations": v2}, False, violations
        d3, ok3, v3 = run_step3_power_baseline_gates(
            root, step2_canonical_detail=d2, corpus_policy=policy, step2_gold=s2g, step3_gold=s3g
        )
        if not ok3:
            violations.extend(v3)
            violations.append("STEP4 blocked: Step 3 failed")
            return {"step3_detail": d3, "step3_violations": v3}, False, violations
        step3_detail = d3

    pb = step3_detail.get("power_baseline") or {}
    cur = pb.get("challenge_rating_current")
    target_cr = int(g4["target_challenge_rating"])

    if cur is None:
        violations.append("G4.1 FAIL: challenge_rating_current is null; cannot assert monotonic CR upgrade")
    else:
        try:
            cur_i = int(cur)
            if target_cr <= cur_i:
                violations.append(f"G4.1 FAIL: target_challenge_rating {target_cr} must exceed baseline {cur_i}")
        except (TypeError, ValueError):
            violations.append(f"G4.1 FAIL: non-numeric challenge_rating_current: {cur!r}")

    bundle = build_levelup_context_bundle(root, step3_detail=step3_detail, corpus_policy=policy, step4_gold=g4)

    min_snip = max(0, int(g4.get("min_recap_snippets") or 0))
    snips = bundle.get("session_recap_snippets") or []
    if len(snips) < min_snip:
        violations.append(f"G4_RECAP FAIL: expected at least {min_snip} recap snippets, got {len(snips)}")

    union = "\n".join(str(s.get("verbatim") or "") for s in snips)
    for sub in [str(x) for x in (g4.get("assert_snippets_union_contains_substrings") or []) if str(x).strip()]:
        if sub not in union:
            violations.append(f"G4_RECAP FAIL: snippets union missing required substring {sub!r}")

    one_of = [str(x) for x in (g4.get("assert_snippets_union_contains_one_of") or []) if str(x).strip()]
    if one_of and not any(x in union for x in one_of):
        violations.append(f"G4_RECAP FAIL: snippets union missing all of {one_of!r}")

    if g4.get("require_timeline_excerpt", True):
        tr = policy.get("timeline_relpath")
        if not isinstance(tr, str) or not tr.strip():
            violations.append("G4_TIMELINE FAIL: corpus_policy.timeline_relpath missing or empty")
        else:
            tl = bundle.get("timeline_excerpt") or {}
            if not str(tl.get("text") or "").strip():
                violations.append(
                    "G4_TIMELINE FAIL: timeline excerpt empty (check corpus_policy.timeline_relpath "
                    f"and file under corpus_dir: {_norm_rel(tr)!r})"
                )

    detail: dict[str, Any] = {
        "levelup_context_bundle": bundle,
        "step3_detail": step3_detail,
    }
    return detail, len(violations) == 0, violations


def run_step2_through_step4(
    corpus_dir: Path | None = None,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step2_gold: dict[str, Any] | None = None,
    step3_gold: dict[str, Any] | None = None,
    step4_gold: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool, list[str]]:
    """Step 2 canonical + intent fixtures + Step 3 + Step 4 context bundle."""
    root = corpus_dir or resolve_corpus_dir(load_step0_gold())
    out, ok, viol = run_step2_and_step3(
        root, corpus_policy=corpus_policy, step2_gold=step2_gold, step3_gold=step3_gold
    )
    if not ok:
        return out, False, viol
    d4, ok4, v4 = run_step4_levelup_context_gates(
        root,
        step3_detail=out["power_baseline_detail"],
        corpus_policy=corpus_policy,
        step2_gold=step2_gold,
        step3_gold=step3_gold,
        step4_gold=step4_gold,
    )
    viol.extend(v4)
    out["levelup_context_detail"] = d4
    return out, ok4, viol


def main() -> None:
    root = resolve_corpus_dir(load_step0_gold())
    out, ok, viol = run_step2_through_step4(root)
    # Omit huge duplicate markdown from stdout: keep bundle + flags only.
    slim = {
        "corpus_dir": str(root),
        "ok": ok,
        "intent_fixtures_ok": out.get("intent_fixtures_ok"),
        "canonical_path": (out.get("canonical_detail") or {}).get("canonical_path"),
        "levelup_context_bundle": (out.get("levelup_context_detail") or {}).get("levelup_context_bundle"),
    }
    if slim["levelup_context_bundle"]:
        b = slim["levelup_context_bundle"]
        # Replace huge excerpts with lengths for CLI default view.
        slim_snips = []
        for sn in b.get("session_recap_snippets") or []:
            verb = str(sn.get("verbatim") or "")
            slim_snips.append(
                {
                    "corpus_relative_path": sn.get("corpus_relative_path"),
                    "keyword_score": sn.get("keyword_score"),
                    "verbatim_chars": len(verb),
                    "verbatim_preview": verb[:220] + ("…" if len(verb) > 220 else ""),
                }
            )
        anc = b.get("session_anchor_excerpt") or {}
        slim["levelup_context_bundle"] = {
            **{
                k: v
                for k, v in b.items()
                if k
                not in (
                    "statblock_excerpt",
                    "dossier_excerpt",
                    "timeline_excerpt",
                    "session_anchor_excerpt",
                    "session_recap_snippets",
                )
            },
            "statblock_excerpt": {
                "corpus_relative_path": (b.get("statblock_excerpt") or {}).get("corpus_relative_path"),
                "text_chars": len(str((b.get("statblock_excerpt") or {}).get("text") or "")),
            },
            "dossier_excerpt": {
                "corpus_relative_path": (b.get("dossier_excerpt") or {}).get("corpus_relative_path"),
                "text_chars": len(str((b.get("dossier_excerpt") or {}).get("text") or "")),
            },
            "timeline_excerpt": {
                "corpus_relative_path": (b.get("timeline_excerpt") or {}).get("corpus_relative_path"),
                "text_chars": len(str((b.get("timeline_excerpt") or {}).get("text") or "")),
            },
            "session_anchor_excerpt": {
                "corpus_relative_path": anc.get("corpus_relative_path"),
                "text_chars": len(str(anc.get("text") or "")),
            },
            "session_recap_snippets": slim_snips,
        }
    print(json.dumps(slim, indent=2, ensure_ascii=False))
    if viol:
        print("--- violations ---", file=sys.stderr)
        for line in viol:
            print(line, file=sys.stderr)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
