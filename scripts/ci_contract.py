"""Named, reusable CI contracts. Inventory is additive; it never selects PR tests."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
LANES = {"fast", "domain-integration", "qualification"}


def contracts(root: Path = ROOT) -> dict:
    data = json.loads((root / "ci/contracts.json").read_text())
    if data["version"] != 1:
        raise ValueError("unsupported CI contract version")
    return data["contracts"]


def discover(root: Path = ROOT) -> set[str]:
    """Match pytest testpaths/default file patterns, Vitest defaults and UI Playwright.

    Include non-ignored untracked tests, so a missing git add cannot hide a test.
    This inventories files, not imported/parametrized test cases or safety claims.
    """
    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "tests", "apps/live-control-ui"],
        cwd=root,
    ).decode().split("\0")
    found = set()
    for path in paths:
        name = Path(path).name
        python = path.startswith("tests/") and name.endswith(".py") and (
            name.startswith("test_") or name.endswith("_test.py")
        )
        frontend = path.startswith("apps/live-control-ui/") and bool(
            re.search(r"\.(?:test|spec)\.[cm]?[jt]sx?$", name)
        )
        browser = path.startswith("apps/live-control-ui/tests/") and name.endswith(".pw.ts")
        if (python or frontend or browser) and (root / path).is_file():
            found.add(path)
    return found


def validate_inventory(root: Path = ROOT) -> dict:
    inventory = json.loads((root / "ci/test-classification.json").read_text())
    if inventory["version"] != 1 or set(inventory["lanes"]) != LANES:
        raise ValueError("unsupported classification contract")
    assigned = Counter(path for files in inventory["lanes"].values() for path in files)
    found = discover(root)
    problems = {
        "unclassified": sorted(found - assigned.keys()),
        "stale": sorted(assigned.keys() - found),
        "duplicate": sorted(path for path, count in assigned.items() if count != 1),
    }
    if any(problems.values()):
        raise ValueError(json.dumps(problems, indent=2))
    config = inventory["discovery_config"]
    pytest_config = tomllib.loads((root / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    if pytest_config["testpaths"] != ["tests"] or pytest_config.get("python_files", ["test_*.py", "*_test.py"]) != ["test_*.py", "*_test.py"]:
        raise ValueError("pytest discovery changed: review the inventory discovery contract")
    for path, expected in config.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"discovery configuration changed: {path}; review and refresh inventory")
    return {"discovered_test_files": len(found), "lane_file_counts": {
        lane: len(files) for lane, files in inventory["lanes"].items()
    }}


def sha(root: Path = ROOT) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def emit(report: dict) -> None:
    print(json.dumps(report, sort_keys=True), flush=True)


def execute(name: str, root: Path = ROOT) -> int:
    catalog = contracts(root)
    if name == "full-regression":
        validate_inventory(root)
        steps = [
            {"cwd": ".", "argv": ["{python}", "-m", "pytest", "tests"]},
            {"cwd": "apps/live-control-ui", "argv": ["npm", "test"]},
            {"cwd": "apps/live-control-ui", "argv": ["npm", "run", "build"]},
            {"cwd": "apps/live-control-ui", "argv": ["npm", "run", "ui:visual"]},
        ]
    else:
        contract = catalog[name]
        steps = contract.get("steps", [contract])
    revision = sha(root)
    for step in steps:
        argv = [sys.executable if arg == "{python}" else arg for arg in step["argv"]]
        started = time.monotonic()
        emit({"sha": revision, "contract": name, "argv": argv, "cwd": step["cwd"], "event": "start"})
        try:
            result = subprocess.run(argv, cwd=root / step["cwd"], check=False).returncode
        except OSError as error:
            print(str(error), file=sys.stderr)
            result = 127
        emit({"sha": revision, "contract": name, "elapsed_seconds": round(time.monotonic() - started, 3), "exit_code": result})
        if result:
            return result if result > 0 else 128 - result
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inventory", "commands", "run"])
    parser.add_argument("contract", nargs="?")
    args = parser.parse_args()
    if args.action == "inventory":
        started = time.monotonic()
        try:
            report = validate_inventory()
        except ValueError as error:
            print(error, file=sys.stderr)
            return 1
        emit({"sha": sha(), **report, "inventory_elapsed_seconds": round(time.monotonic() - started, 3)})
        return 0
    if args.action == "commands":
        for name, contract in contracts().items():
            for step in contract.get("steps", [contract]):
                print(name, step["cwd"], shlex.join(step["argv"]), sep="\t")
        return 0
    if args.contract not in {*contracts(), "full-regression"}:
        parser.error("run requires a named contract (see commands) or full-regression")
    return execute(args.contract)


if __name__ == "__main__":
    raise SystemExit(main())
