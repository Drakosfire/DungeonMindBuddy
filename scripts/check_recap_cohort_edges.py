#!/usr/bin/env python3
"""Check that review explicitly accounts for edges incident to selected Events."""

import argparse
import json
from pathlib import Path


from graph_memory.ingestion.cohort_edge_review import build_prepare_request, validate, validate_prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("manifest", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-request", type=Path)
    mode.add_argument("--build-prepare-request", type=Path, metavar="BASE_REQUEST")
    args = parser.parse_args()
    try:
        candidate = json.loads(args.candidate.read_text())
        manifest = json.loads(args.manifest.read_text())
        if args.build_prepare_request:
            base = json.loads(args.build_prepare_request.read_text())
            print(json.dumps(build_prepare_request(candidate, manifest, base), indent=2))
            return
        count = (validate_prepare(candidate, manifest, json.loads(args.prepare_request.read_text()))
                 if args.prepare_request else validate(candidate, manifest))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"Checked {count} explicit edge decisions.")


if __name__ == "__main__":
    main()
