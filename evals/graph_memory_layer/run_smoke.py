"""No-LLM smoke check for the Graph Memory Layer experiment scaffold."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TRACKING_DOC = REPO_ROOT / "Docs" / "Experiments" / "GRAPH-MEMORY-FORK-TRACKING.md"
PREFERRED_EXPERIMENT_DOC = (
    REPO_ROOT / "Docs" / "Experiments" / "EXPERIMENT-Graph-Memory-Layer.md"
)
FALLBACK_EXPERIMENT_DIRS = (
    REPO_ROOT / "Docs" / "Experiments",
    REPO_ROOT / "Docs" / "Design",
)
REQUIRED_DIRS = (
    REPO_ROOT / "evals" / "graph_memory_layer",
    REPO_ROOT / "evals" / "graph_memory_layer" / "artifacts",
    REPO_ROOT / "evals" / "graph_memory_layer" / "artifacts" / "baseline",
)
EXPECTED_STACKED_BRANCH = "graph-exp/00-fork-tracking-baseline"
FORBIDDEN_BRANCHES = {"main", "master"}


def find_experiment_doc() -> Path | None:
    """Find the graph-memory experiment plan, preferring the expected path."""
    if PREFERRED_EXPERIMENT_DOC.is_file():
        return PREFERRED_EXPERIMENT_DOC

    for directory in FALLBACK_EXPERIMENT_DIRS:
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.iterdir()):
            name = candidate.name.lower()
            is_experiment_plan = name.startswith("experiment") or "experiment" in name
            if not (
                candidate.is_file()
                and is_experiment_plan
                and "graph" in name
                and "fork-tracking" not in name
            ):
                continue
            if "memory" in name:
                return candidate
            heading = candidate.read_text(encoding="utf-8", errors="ignore")[:500].lower()
            if "graph" in heading and "memory" in heading:
                return candidate
    return None


def current_branch() -> str | None:
    """Return the current Git branch name, or None when Git is unavailable."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-git-context",
        action="store_true",
        help=(
            "enforce the future Graph Memory stacked branch contract; "
            "intended for post-bootstrap experiment PRs"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment_doc = find_experiment_doc()
    missing: list[str] = []
    failures: list[str] = []

    if not TRACKING_DOC.is_file():
        missing.append(str(TRACKING_DOC.relative_to(REPO_ROOT)))
    if experiment_doc is None:
        missing.append("Docs/Experiments/*Graph*Memory* or Docs/Design/*Graph*Memory*")

    for directory in REQUIRED_DIRS:
        if not directory.is_dir():
            missing.append(str(directory.relative_to(REPO_ROOT)))

    branch = current_branch() if args.check_git_context else None
    if args.check_git_context:
        if branch is None:
            failures.append("unable to determine current Git branch")
        elif branch in FORBIDDEN_BRANCHES:
            failures.append(f"current branch must not be {branch!r}")
        elif branch != EXPECTED_STACKED_BRANCH:
            failures.append(
                "current branch is "
                f"{branch!r}; expected {EXPECTED_STACKED_BRANCH!r}"
            )

    print("Graph Memory Layer smoke check")
    print(f"- fork tracking doc: {'found' if TRACKING_DOC.is_file() else 'missing'}")
    if experiment_doc is None:
        print("- experiment doc: missing")
    else:
        print(f"- experiment doc: found ({experiment_doc.relative_to(REPO_ROOT)})")
    print(
        "- baseline artifacts dir: "
        f"{'found' if REQUIRED_DIRS[-1].is_dir() else 'missing'}"
    )
    if args.check_git_context:
        print(
            "- git context: "
            f"{'ready' if not failures else 'blocked'}"
            f" ({branch or 'unknown'})"
        )

    if missing or failures:
        print("- no-LLM baseline scaffold: blocked")
        if missing:
            print("Missing required scaffold paths:")
            for path in missing:
                print(f"  - {path}")
        if failures:
            print("Git context failures:")
            for failure in failures:
                print(f"  - {failure}")
        return 1

    print("- no-LLM baseline scaffold: ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
