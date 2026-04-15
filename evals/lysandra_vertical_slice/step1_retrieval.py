"""Step 1 — keyword retrieval over corpus subtrees and gates G1.1–G1.3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evals.lysandra_vertical_slice.step0_corpus_environment import load_step0_gold, resolve_corpus_dir

_SLICE_DIR = Path(__file__).resolve().parent


def corpus_policy_path() -> Path:
    return _SLICE_DIR / "gold" / "corpus_policy.json"


def step1_gold_path() -> Path:
    return _SLICE_DIR / "gold" / "step1_retrieval.json"


def load_corpus_policy() -> dict[str, Any]:
    return json.loads(corpus_policy_path().read_text(encoding="utf-8"))


def load_step1_gold() -> dict[str, Any]:
    return json.loads(step1_gold_path().read_text(encoding="utf-8"))


def _norm_rel(p: str) -> str:
    return p.strip().replace("\\", "/")


def score_text_for_aliases(text: str, aliases: list[str]) -> int:
    """Case-insensitive non-overlapping-ish score: sum of counts per alias (substring match)."""
    low = text.lower()
    total = 0
    for a in aliases:
        s = str(a).strip()
        if not s:
            continue
        needle = s.lower()
        total += low.count(needle)
    return total


def _iter_scan_files(corpus_dir: Path, scan_subdirs: list[str]) -> list[Path]:
    out: list[Path] = []
    for name in scan_subdirs:
        root = corpus_dir / name
        if not root.is_dir():
            continue
        out.extend(p for p in root.rglob("*.md") if p.is_file())
    return out


def keyword_scan_ranked(
    corpus_dir: Path,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step1_gold: dict[str, Any] | None = None,
) -> list[tuple[str, int]]:
    """
    Rank markdown files under ``scan_subdirs`` by total alias substring hits.

    Returns ``(relpath_posix, score)`` descending by score, then ascending path.
    """
    policy = corpus_policy or load_corpus_policy()
    g1 = step1_gold or load_step1_gold()
    aliases = [str(x) for x in (policy.get("aliases") or []) if str(x).strip()]
    scan = [str(x) for x in (g1.get("scan_subdirs") or ["Longmont Campaign", "Elderwyld"])]
    cap_raw = g1.get("max_file_read_chars")
    cap = int(cap_raw) if cap_raw is not None else 400_000

    scored: list[tuple[str, int]] = []
    for path in _iter_scan_files(corpus_dir, scan):
        try:
            rel = path.relative_to(corpus_dir).as_posix()
        except ValueError:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        sample = raw if cap <= 0 else raw[:cap]
        scored.append((_norm_rel(rel), score_text_for_aliases(sample, aliases)))

    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def run_step1_gates(
    ranked: list[tuple[str, int]],
    *,
    corpus_policy: dict[str, Any] | None = None,
    step1_gold: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """
    Check G1.1–G1.3 for an ordered ranked list (highest score first).

    G1.3 applies to **all** ranked paths (not only top_k).
    """
    policy = corpus_policy or load_corpus_policy()
    g1 = step1_gold or load_step1_gold()
    violations: list[str] = []

    allowed = [str(p) for p in (policy.get("corpus_roots_allowed_prefixes") or []) if str(p).strip()]
    for rel, _ in ranked:
        if not any(rel.startswith(pref) for pref in allowed):
            violations.append(f"G1.3 FAIL: path outside allowed corpus roots: `{rel}`")

    if violations:
        return False, violations

    top_k = max(1, int(g1.get("top_k") or 50))
    order = [r for r, _ in ranked]
    top_set = set(order[:top_k])

    required = [_norm_rel(str(p)) for p in (g1.get("required_paths_retrieved") or []) if str(p).strip()]
    for req in required:
        if req not in top_set:
            violations.append(
                f"G1.1 FAIL: required path not in top_{top_k} by keyword score: `{req}` "
                f"(expand aliases, corpus, or top_k; see gold/step1_retrieval.json)."
            )

    canon = policy.get("canonical_statblock_relpath")
    if isinstance(canon, str) and canon.strip():
        c = _norm_rel(canon)
        if c not in top_set:
            violations.append(f"G1.2 FAIL: canonical_statblock_relpath not in top_{top_k}: `{c}`")
    else:
        seeds: list[str] = []
        for key in ("primary_reference_relpath", "session_anchor_relpath"):
            v = policy.get(key)
            if isinstance(v, str) and v.strip():
                seeds.append(_norm_rel(v))
        for s in seeds:
            if s not in top_set:
                violations.append(
                    f"G1.2 FAIL: Step-2 seed path from corpus_policy not in top_{top_k}: `{s}` "
                    f"(canonical_statblock_relpath is null — dossier + session_anchor must recall)."
                )

    return len(violations) == 0, violations


def run_step1_keyword_scan_and_gates(
    corpus_dir: Path | None = None,
    *,
    corpus_policy: dict[str, Any] | None = None,
    step1_gold: dict[str, Any] | None = None,
) -> tuple[list[tuple[str, int]], bool, list[str]]:
    """Run scan + gates; returns ``(ranked, ok, violations)``."""
    root = corpus_dir or resolve_corpus_dir(load_step0_gold())
    ranked = keyword_scan_ranked(root, corpus_policy=corpus_policy, step1_gold=step1_gold)
    ok, viol = run_step1_gates(ranked, corpus_policy=corpus_policy, step1_gold=step1_gold)
    return ranked, ok, viol


# --- Optional diagnostics (stable for snapshots / debugging) ---


def summarize_top_ranked(ranked: list[tuple[str, int]], n: int = 12) -> str:
    lines = [f"Top {n} by alias hit count (Step 1 keyword scan):"]
    for rel, sc in ranked[:n]:
        lines.append(f"  {sc:4d}  {rel}")
    return "\n".join(lines)
