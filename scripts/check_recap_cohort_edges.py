#!/usr/bin/env python3
"""Check that review explicitly accounts for edges incident to selected Events."""

import argparse
import json
from pathlib import Path


from graph_memory.ingestion.cohort_edge_review import validate, validate_prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--prepare-request", type=Path)
    args = parser.parse_args()
    try:
        candidate = json.loads(args.candidate.read_text())
        manifest = json.loads(args.manifest.read_text())
        count = (validate_prepare(candidate, manifest, json.loads(args.prepare_request.read_text()))
                 if args.prepare_request else validate(candidate, manifest))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Checked {count} explicit edge decisions.")


if __name__ == "__main__":
    main()
