#!/usr/bin/env python3
"""Run Session 22 live-turn classifier benchmark against gold (writes disk artifact)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_GOLD = _REPO / "evals/c2_live_prep/gold/session_22_live_turn_classifier.json"
_ARTIFACT_DIR = _REPO / "evals/c2_live_prep/artifacts/runs"
_LAST = _REPO / "evals/c2_live_prep/last_session_22_classifier_benchmark.json"


def main() -> int:
    sys.path.insert(0, str(_REPO))
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv
    from src.live_play.classify_live_turn import classify_live_turn

    load_dungeonmindbuddy_dotenv()

    gold = json.loads(_GOLD.read_text(encoding="utf-8"))
    fixtures = gold["fixtures"]
    results: list[dict] = []
    passed = 0

    for row in fixtures:
        got = classify_live_turn(row["user_line"], allow_heuristic_fallback=False)
        expect = row["expect"]
        def _routing(exp: dict) -> dict:
            return {
                "latency_mode": exp["latency_mode"],
                "event_type": exp["event_type"],
                "table_id": exp.get("table_id"),
                "roll": exp.get("roll"),
                "skill_check": exp.get("skill_check"),
            }

        got_r = {
            "latency_mode": got.latency_mode,
            "event_type": got.event_type,
            "table_id": got.table_id,
            "roll": got.roll,
            "skill_check": got.skill_check,
        }
        candidates = [_routing(expect)] + [
            _routing(alt) for alt in row.get("routing_alternates") or []
        ]
        ok = got_r in candidates
        if ok:
            passed += 1
        results.append(
            {
                "id": row["id"],
                "user_line": row["user_line"],
                "pass": ok,
                "got": {
                    "latency_mode": got.latency_mode,
                    "event_type": got.event_type,
                    "intent": got.intent,
                    "table_id": got.table_id,
                    "roll": got.roll,
                    "skill_check": got.skill_check,
                    "confidence": got.confidence,
                },
                "expect": expect,
            }
        )

    payload = {
        "schema": "c2_live_turn_classifier_run_v1",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "gold": str(_GOLD.relative_to(_REPO)),
        "fixture_count": len(fixtures),
        "pass_count": passed,
        "fail_count": len(fixtures) - passed,
        "results": results,
    }

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = _ARTIFACT_DIR / day
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    artifact_path = out_dir / f"session_22_classifier_{stamp}.json"
    artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _LAST.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        f"Session 22 classifier: {passed}/{len(fixtures)} pass "
        f"(artifact: {artifact_path.relative_to(_REPO)})"
    )
    for row in results:
        if not row["pass"]:
            print(f"  FAIL {row['id']}: {row['got']} != {row['expect']}")
    return 0 if passed == len(fixtures) else 1


if __name__ == "__main__":
    raise SystemExit(main())
