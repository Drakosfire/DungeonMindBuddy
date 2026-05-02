"""Stage B preflight: normalized gold routing integrity + capture signature (sentence_units).

Used by ``step2_route_run`` and ``step2_discourse_pipeline_run`` to fail fast before LLM spend.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from evals.sentence_routing_retrieval_falsification.grader import normalize_gold_routing_matches
from evals.sentence_routing_retrieval_falsification.stage_b_gold_stability import (
    unit_set_signature,
)


def canonical_normalized_gold_fingerprint(gold_routing: dict[str, Any]) -> str:
    """Stable hash of ``must_route`` + ``must_abstain`` rows after normalization (order-preserving)."""
    blob = json.dumps(
        {
            "must_route": gold_routing.get("must_route") or [],
            "must_abstain": gold_routing.get("must_abstain") or [],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def preflight_stage_b_gold_and_capture(
    gold_routing: dict[str, Any],
    sentence_units: list[dict[str, Any]],
    *,
    expected_capture_signature: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    """
    Normalize gold routing rows and build reproducibility metadata.

    Returns ``(normalized_gold_routing, normalize_errors, preflight_meta)``.
    ``normalize_errors`` must be empty for a successful preflight.
    """
    norm, errors = normalize_gold_routing_matches(gold_routing, sentence_units)
    capture_signature = unit_set_signature(sentence_units)
    if isinstance(expected_capture_signature, dict) and expected_capture_signature:
        for key in ("sentence_unit_count", "unit_id_sha16"):
            got = capture_signature.get(key)
            want = expected_capture_signature.get(key)
            if got != want:
                errors.append(f"capture_signature.{key}: expected {want!r} got {got!r}")
    mr = norm.get("must_route") or []
    ma = norm.get("must_abstain") or []
    meta: dict[str, Any] = {
        "capture_signature": capture_signature,
        "expected_capture_signature": expected_capture_signature or None,
        "gold_routing_normalized_fingerprint_sha16": canonical_normalized_gold_fingerprint(norm),
        "must_route_rows": len(mr) if isinstance(mr, list) else 0,
        "must_abstain_rows": len(ma) if isinstance(ma, list) else 0,
        "normalize_errors": list(errors),
        "preflight_ok": len(errors) == 0,
    }
    return norm, errors, meta


def _load_units_for_cli(raw: dict[str, Any], *, corpus_root: Path, prior_json: Path | None) -> list[dict[str, Any]]:
    from evals.sentence_routing_retrieval_falsification.step2_route_run import _load_sentence_units

    return _load_sentence_units(raw, corpus_root, prior_json)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute or update Stage B capture signatures for a scenario JSON.",
    )
    parser.add_argument("--scenario-json", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--prior-json", type=Path, default=None)
    parser.add_argument(
        "--write-expected-capture-signature",
        action="store_true",
        help="Persist current sentence-unit signature to scenario.expected_capture_signature.",
    )
    args = parser.parse_args()

    scenario_path = args.scenario_json.resolve()
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    units = _load_units_for_cli(
        raw,
        corpus_root=args.corpus_root.resolve(),
        prior_json=args.prior_json.resolve() if args.prior_json else None,
    )
    sig = unit_set_signature(units)
    if args.write_expected_capture_signature:
        raw["expected_capture_signature"] = sig
        scenario_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(sig, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
