"""No-LLM smoke check for the Graph Memory Layer experiment scaffold."""

from __future__ import annotations

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


def find_experiment_doc() -> Path | None:
    """Find the graph-memory experiment plan, preferring the expected path."""
    if PREFERRED_EXPERIMENT_DOC.is_file():
        return PREFERRED_EXPERIMENT_DOC

    for directory in FALLBACK_EXPERIMENT_DIRS:
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.iterdir()):
            name = candidate.name.lower()
            if candidate.is_file() and "graph" in name and "memory" in name:
                return candidate
    return None


def main() -> int:
    experiment_doc = find_experiment_doc()
    missing: list[str] = []

    if not TRACKING_DOC.is_file():
        missing.append(str(TRACKING_DOC.relative_to(REPO_ROOT)))
    if experiment_doc is None:
        missing.append("Docs/Experiments/*Graph*Memory* or Docs/Design/*Graph*Memory*")

    for directory in REQUIRED_DIRS:
        if not directory.is_dir():
            missing.append(str(directory.relative_to(REPO_ROOT)))

    print("Graph Memory Layer smoke check")
    print(f"- fork tracking doc: {'found' if TRACKING_DOC.is_file() else 'missing'}")
    print(f"- experiment doc: {'found' if experiment_doc is not None else 'missing'}")
    print(
        "- baseline artifacts dir: "
        f"{'found' if REQUIRED_DIRS[-1].is_dir() else 'missing'}"
    )

    if missing:
        print("- no-LLM baseline scaffold: blocked")
        print("Missing required scaffold paths:")
        for path in missing:
            print(f"  - {path}")
        return 1

    print("- no-LLM baseline scaffold: ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
