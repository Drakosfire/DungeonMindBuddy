"""Named, reusable CI contracts. Inventory is additive; it never selects PR tests."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import signal
import os
from collections import Counter
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""}:
    sys.path.insert(0, str(ROOT))
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
    pytest_config = tomllib.loads((root / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    if pytest_config["testpaths"] != ["tests"] or pytest_config.get("python_files", ["test_*.py", "*_test.py"]) != ["test_*.py", "*_test.py"]:
        raise ValueError("pytest discovery changed: review the inventory discovery contract")
    scripts = json.loads((root / "apps/live-control-ui/package.json").read_text())["scripts"]
    expected_scripts = {
        "test": "vitest run",
        "ui:visual": "playwright test --config playwright.ui.config.ts",
    }
    for name, expected in expected_scripts.items():
        if scripts.get(name) != expected:
            raise ValueError(f"frontend discovery command changed: {name}; review inventory")
    browser_candidates = sorted(
        path for path in found
        if path.startswith("apps/live-control-ui/tests/") and path.endswith(".pw.ts")
    )
    # The runner discovery job verifies the visual suite's reviewed file selection.
    visual_files = [path for path in browser_candidates if Path(path).name == "ui-visual.pw.ts"]
    return {
        "discovered_test_files": len(found),
        "lane_file_counts": {lane: len(files) for lane, files in inventory["lanes"].items()},
        "browser_candidate_files": len(browser_candidates),
        "playwright_visual_files": len(visual_files),
    }


def sha(root: Path = ROOT) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def emit(report: dict) -> None:
    print(json.dumps(report, sort_keys=True), flush=True)


def _group_live(group: int) -> bool:
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / "stat").read_text().split(") ", 1)[1].split()
        except (OSError, IndexError):
            continue
        if fields[2] == str(group) and fields[0] != "Z":
            return True
    return False


def _run_worker(argv: list[str], cwd: Path) -> int:
    child = subprocess.Popen(argv, cwd=cwd, start_new_session=True)
    interrupted = False
    while True:
        try:
            result = child.wait()
            while _group_live(child.pid):
                time.sleep(0.1)
            break
        except KeyboardInterrupt:
            interrupted = True
            if _group_live(child.pid):
                try:
                    os.killpg(child.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
            # Repeated interrupts cannot release the database owner while its
            # exact child or descendants are still alive.
    if interrupted:
        raise KeyboardInterrupt
    return result


class _ContractFailed(Exception):
    def __init__(self, code: int):
        self.code = code


def run_contracts(names: list[str], root: Path = ROOT) -> int:
    """One App owner around all selected serial suites, never one clone per step."""
    catalog = contracts(root)
    needs_app = "full-regression" in names or any(
        "pytest" in step["argv"]
        for name in names if name in catalog
        for step in catalog[name].get("steps", [catalog[name]])
    )
    from scripts.ci_app_database import app_workstream, assignment_environment
    try:
        with app_workstream() if needs_app else nullcontext(None) as assignment:
            with assignment_environment(assignment) if assignment else nullcontext():
                failed = 0
                for name in names:
                    result = execute(name, root, catalog=catalog)
                    if result and not failed:
                        failed = result
                if failed:
                    raise _ContractFailed(failed)
    except _ContractFailed as failure:
        for note in getattr(failure, "__notes__", []):
            print(note, file=sys.stderr)
        return failure.code
    return 0


def execute(name: str, root: Path = ROOT, *, catalog: dict | None = None) -> int:
    if catalog is None:
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
            result = _run_worker(argv, root / step["cwd"])
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
    parser.add_argument("contract", nargs="*")
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
    catalog = contracts()
    if not args.contract or any(name not in {*catalog, "full-regression"} for name in args.contract):
        parser.error("run requires a named contract (see commands) or full-regression")
    return run_contracts(args.contract)


if __name__ == "__main__":
    raise SystemExit(main())
