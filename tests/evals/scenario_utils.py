from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "evals" / "canon_layering"
SCENARIOS_DIR = EVAL_DIR / "scenarios"
MANIFEST_PATH = EVAL_DIR / "scenario_manifest.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest() -> dict[str, Any]:
    return load_json(MANIFEST_PATH)


def scenario_paths(scenario_id: str) -> dict[str, Path]:
    scenario_dir = SCENARIOS_DIR / scenario_id
    return {
        "evidence_units": scenario_dir / "input" / "evidence_units.json",
        "facts": scenario_dir / "input" / "facts.json",
        "conflicts": scenario_dir / "input" / "conflicts.json",
        "canon_decisions": scenario_dir / "input" / "canon_decisions.json",
        "world_expected": scenario_dir / "expected" / "world_projection.json",
    }

