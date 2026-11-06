#!/usr/bin/env python3
"""Run a pinned isolated Buddy evaluation. See Docs/Guides/ingestion-evaluation.md."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ingestion_evaluation.runner import Runner, verify_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['qualify', 'capture', 'observe', 'audit', 'audit-retained', 'report', 'pause'])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--qualification-sha')
    args = parser.parse_args()
    manifest, sha = verify_manifest(args.manifest)
    if args.command == 'pause':
        # This durable marker stops later requests, allowing the in-flight ordinary turn to settle.
        (Path(manifest['_output']) / 'PAUSE').touch(exist_ok=True)
        print(json.dumps({'state': 'pause_requested', 'in_flight': 'not cancelled or retried'}))
        return
    if args.command == 'report':
        result = Runner(manifest, sha, None).report()
    else:
        from ingestion_evaluation.buddy import Buddy
        runner = Runner(manifest, sha, Buddy(manifest))
        if args.command == 'capture':
            if not args.qualification_sha:
                parser.error('capture requires --qualification-sha')
            result = runner.capture(args.qualification_sha)
        elif args.command == 'audit-retained':
            result = runner.audit(retained=True)
        else:
            result = getattr(runner, args.command)()
    print(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
