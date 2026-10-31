#!/usr/bin/env python3
"""Explicit offline World metadata adoption. Ordinary product boot never imports files."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from application_state.errors import ApplicationStateError, ApplicationStateValidationError
from application_state.world_catalog.service import adopt_world_catalog
from application_state.world_catalog.types import WorldContainerRegistryDocument


def adopt_file(path: Path, *, expected_sha256: str, apply: bool = False):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ApplicationStateValidationError('World catalog input differs from its reviewed SHA-256')
    document = WorldContainerRegistryDocument.model_validate(json.loads(raw))
    return adopt_world_catalog(document, dry_run=not apply)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        report = adopt_file(args.input, expected_sha256=args.expected_sha256, apply=args.apply)
    except (OSError, ValueError, ApplicationStateError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}))
        return 1
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
