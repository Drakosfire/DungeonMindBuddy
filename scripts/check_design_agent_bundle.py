"""Check the repository design-agent export against its canonical source index."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "Docs/Design/INDEX-design-agent-source-set.md"
BUNDLE = ROOT / "Docs/Sources/design-agent"
BUNDLE_INDEX = "ACTIVE_REFERENCE/INDEX-design-agent-source-set.md"
MAPPING = re.compile(
    r"\]\(([^)]+)\)(?:\s*\|\s*|\s*→\s*)"
    r"`((?:ACTIVE_AUTHORITY|ACTIVE_REFERENCE|PROCESS|SOURCE_ANCHOR)/[^`]+)`"
)


def main() -> int:
    canonical = MAPPING.findall(INDEX.read_text(encoding="utf-8"))
    expected = {export for _, export in canonical}
    if not canonical or len(expected) != len(canonical) or BUNDLE_INDEX not in expected:
        print("Invalid or duplicate entries in the canonical source index")
        return 1

    actual = {path.relative_to(BUNDLE).as_posix() for path in BUNDLE.rglob("*") if path.is_file()}
    expected.add("README.md")
    problems = [f"Missing export: {path}" for path in sorted(expected - actual)]
    problems.extend(f"Unexpected export: {path}" for path in sorted(actual - expected))

    for source, export in canonical:
        source_path = INDEX.parent / source
        if not source_path.is_file():
            problems.append(f"Missing canonical source: {source}")
        elif export in actual and export != BUNDLE_INDEX:
            if source_path.read_bytes() != (BUNDLE / export).read_bytes():
                problems.append(f"Drift: {export}")

    if BUNDLE_INDEX in actual:
        index_path = BUNDLE / BUNDLE_INDEX
        bundled = MAPPING.findall(index_path.read_text(encoding="utf-8"))
        if sorted(export for _, export in bundled) != sorted(export for _, export in canonical):
            problems.append("Bundled index mappings differ from the canonical index")
        for link, export in bundled:
            if (index_path.parent / link).resolve() != (BUNDLE / export).resolve():
                problems.append(f"Bundled index link does not target its export: {export}")

    for problem in problems:
        print(problem)
    if not problems:
        print(f"Verified {len(canonical)} mapped design-agent exports")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
