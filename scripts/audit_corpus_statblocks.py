"""Inventory candidate statblock sources at a Git revision for offline review.

Run from the repository root. The output identifies
source files to review before typed mechanics import.
"""

import argparse
import hashlib
import json
from pathlib import PurePosixPath
import re
import subprocess


CORPUS_ROOTS = (
    "corpus/eldyrwild-markdown",
    "corpus/Eldyrwild and Campaign Unprocessed",
)
MECHANIC_FIELDS = re.compile(
    r"^\s*(?:[-*|]\s*)?\**(?:armor class|hit points|challenge rating)\b",
    re.IGNORECASE | re.MULTILINE,
)
MECHANICS_JSON = re.compile(r'["\x27](?:armorClass|armor_class|hitPoints|hit_points)["\x27]')
STATBLOCK_META = re.compile(
    r"^(?:title|source_type|document_class):[^\n]*stat[ _-]?block",
    re.IGNORECASE | re.MULTILINE,
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def inventory(commit: str):
    paths = git("ls-tree", "-r", "-z", "--name-only", commit, "--", *CORPUS_ROOTS)
    for name in paths.decode().split("\0"):
        path = PurePosixPath(name)
        if path.suffix.lower() != ".md":
            continue
        if any(part.endswith("_p0") for part in path.parts) or path.name in {
            "README.md", "EVALUATION_REPORT.md", "stageA.surface.md",
        }:
            continue
        data = git("show", f"{commit}:{path}")
        try:
            markdown = data.decode("utf-8")
        except UnicodeDecodeError:
            if "statblock" in str(path).lower():
                yield {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                       "signals": ["unreadable_utf8"]}
            continue
        statblock_path = (
            "statblock" in path.name.lower()
            or "Statblocks and Tokens" in path.parts
            or "Statblocks" in path.parts
        )
        fields = {match.group().strip(" -*|").lower() for match in MECHANIC_FIELDS.finditer(markdown)}
        signals = [
            label for label, present in (
                ("statblock_path", statblock_path),
                ("statblock_metadata", STATBLOCK_META.search(markdown)),
                ("multiple_mechanic_fields", len(fields) >= 2),
                ("embedded_mechanics_json", MECHANICS_JSON.search(markdown)),
            ) if present
        ]
        if signals:
            yield {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "signals": signals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD")
    args = parser.parse_args()
    commit = git(
        "rev-parse", "--verify", "--end-of-options", f"{args.revision}^{{commit}}"
    ).decode().strip()
    print(json.dumps({"commit": commit, "candidates": list(inventory(commit))}, indent=2))


if __name__ == "__main__":
    main()
