"""Step 0 gates: corpus root exists and fingerprint matches gold (vertical slice benchmark)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.agent.planner_cache import corpus_fingerprint

_SLICE_DIR = Path(__file__).resolve().parent
# …/DungeonMindBuddy/evals/lysandra_vertical_slice → repo root is parents[1] (DungeonMindBuddy).
_REPO_ROOT = _SLICE_DIR.parents[1]


def step0_gold_path() -> Path:
    return _SLICE_DIR / "gold" / "step0_environment.json"


def load_step0_gold() -> dict[str, Any]:
    return json.loads(step0_gold_path().read_text(encoding="utf-8"))


def resolve_corpus_dir(gold: dict[str, Any] | None = None) -> Path:
    g = gold or load_step0_gold()
    rel = str(g.get("corpus_root_relpath") or "corpus/eldyrwild-markdown").strip()
    return (_REPO_ROOT / rel).resolve()


def _env_nonempty(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _env_one_of(name: str, values: list[str]) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    return raw in {v.lower() for v in values}


def statblock_service_gate_passes(gold: dict[str, Any]) -> bool:
    cfg = gold.get("statblock_service_gate") or {}
    for rule in cfg.get("pass_if_any") or []:
        env = str(rule.get("env", "")).strip()
        if not env:
            continue
        if rule.get("require_non_empty") and _env_nonempty(env):
            return True
        one_of = rule.get("require_one_of")
        if isinstance(one_of, list) and _env_one_of(env, [str(x) for x in one_of]):
            return True
    return False


def run_step0_gates(
    *,
    corpus_dir: Path | None = None,
    gold: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """
    Returns ``(all_passed, violations)`` with human-readable violation strings.

    Gates: G0.1 corpus directory exists; G0.2 fingerprint vs gold;
    G0.3 statblock URL, mock flag, or explicit CI skip flag.
    """
    g = gold or load_step0_gold()
    root = corpus_dir or resolve_corpus_dir(g)
    violations: list[str] = []

    if not root.is_dir():
        violations.append(f"G0.1 FAIL: corpus directory missing or not a directory: {root}")
        return False, violations

    expected = str(g.get("expected_fingerprint", "")).strip()
    if not expected:
        violations.append("G0.2 FAIL: gold step0_environment.json missing expected_fingerprint")
        return False, violations

    actual = corpus_fingerprint(root)
    if actual != expected and not bool(g.get("allow_fingerprint_drift")):
        violations.append(
            f"G0.2 FAIL: corpus fingerprint mismatch (update gold if corpus changed intentionally). "
            f"expected={expected} actual={actual} root={root}"
        )

    if not statblock_service_gate_passes(g):
        violations.append(
            "G0.3 FAIL: set DUNGEONMIND_STATBLOCK_URL, or LYSANDRA_SLICE_MOCK_STATBLOCK=1, "
            "or LYSANDRA_SLICE_SKIP_STATBLOCK_URL_GATE=1 for corpus-only runs."
        )

    return len(violations) == 0, violations
