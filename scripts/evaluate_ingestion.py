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
    parser.add_argument('command', choices=['review-packet', 'assessment-assemble', 'assessment-report', 'baseline-freeze', 'baseline-verify', 'qualify', 'capture', 'observe', 'audit', 'audit-retained', 'report', 'pause',
                                           'source-qualify', 'source-execute', 'source-inspect', 'source-report',
                                           'publication-prepare', 'publication-qualify', 'publication-execute',
                                           'publication-inspect', 'publication-report',
                                           'correction-qualify', 'correction-execute', 'correction-inspect', 'correction-report'])
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--baseline-output', type=Path)
    parser.add_argument('--qualification-sha')
    parser.add_argument('--result', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--assessment-output', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--timing', type=Path)
    parser.add_argument('--packet-output', type=Path)
    parser.add_argument('--private-receipt', type=Path)
    parser.add_argument('--review-id')
    args = parser.parse_args()
    if args.command == 'review-packet':
        if (not all((args.result, args.packet_output, args.private_receipt, args.review_id))
                or any((args.manifest, args.review, args.assessment_output, args.audit,
                        args.timing, args.baseline_output, args.qualification_sha))):
            parser.error('review-packet requires only --result, --packet-output, --private-receipt and --review-id')
        from ingestion_evaluation.blinding import prepare
        print(json.dumps(prepare(args.result, args.packet_output, args.private_receipt, args.review_id)))
        return
    if any((args.packet_output, args.private_receipt, args.review_id)):
        parser.error('Review packet flags require review-packet')
    if args.command == 'assessment-assemble':
        if (not all((args.manifest, args.result, args.review, args.assessment_output))
                or args.baseline_output or args.qualification_sha):
            parser.error('assessment-assemble requires --manifest (Gold/criteria only), --result, '
                         '--review and --assessment-output; optional --audit and --timing')
        from ingestion_evaluation.assembly import assemble
        print(json.dumps(assemble(args.manifest, args.result, args.review, args.assessment_output,
                                  audit_path=args.audit, timing_path=args.timing)))
        return
    if any((args.result, args.review, args.assessment_output, args.audit, args.timing)):
        parser.error('Assessment assembly flags require assessment-assemble')
    if args.command == 'assessment-report':
        if not args.manifest or args.baseline_output or args.qualification_sha:
            parser.error('assessment-report requires only --manifest')
        from ingestion_evaluation.assessment import report
        print(json.dumps(report(args.manifest)))
        return
    if args.command.startswith('baseline-'):
        if not args.baseline_output or (args.command == 'baseline-freeze' and not args.manifest):
            parser.error('Baseline commands require --baseline-output; freeze also requires --manifest')
        if args.qualification_sha or (args.command == 'baseline-verify' and args.manifest):
            parser.error('Baseline commands do not accept execution qualifications or a verify manifest')
        from ingestion_evaluation.baseline import freeze, verify
        result = (freeze(args.manifest, args.baseline_output) if args.command == 'baseline-freeze'
                  else verify(args.baseline_output))
        print(json.dumps(result))
        return
    if not args.manifest or args.baseline_output:
        parser.error('Evaluation commands require --manifest and do not accept --baseline-output')
    manifest, sha = verify_manifest(args.manifest)
    source_mode = manifest.get('mode') == 'source_authority_v1'
    publication_mode = manifest.get('mode') == 'reviewed_publication_v1'
    correction_mode = manifest.get('mode') == 'reviewed_correction_v1'
    if (args.command.startswith('source-') != source_mode
            or args.command.startswith('publication-') != publication_mode
            or args.command.startswith('correction-') != correction_mode):
        parser.error('Source-authority and ordinary capture commands require their own explicit manifest mode')
    if correction_mode:
        if args.command == 'correction-execute' and not args.qualification_sha:
            parser.error('correction-execute requires --qualification-sha')
        from ingestion_evaluation.correction import CorrectionBackend, CorrectionRunner
        backend = None if args.command == 'correction-report' else CorrectionBackend(manifest)
        runner = CorrectionRunner(manifest, sha, backend)
        result = (runner.execute(args.qualification_sha) if args.command == 'correction-execute'
                  else getattr(runner, args.command.removeprefix('correction-'))())
        print(json.dumps(result, default=str))
        return
    if publication_mode:
        if args.command == 'publication-execute' and not args.qualification_sha:
            parser.error('publication-execute requires --qualification-sha')
        from ingestion_evaluation.publication import PublicationBackend, PublicationRunner
        backend = None if args.command == 'publication-report' else PublicationBackend(manifest)
        runner = PublicationRunner(manifest, sha, backend)
        result = (runner.execute(args.qualification_sha) if args.command == 'publication-execute'
                  else getattr(runner, args.command.removeprefix('publication-'))())
        print(json.dumps(result, default=str))
        return
    if source_mode:
        if args.command == 'source-execute' and not args.qualification_sha:
            parser.error('source-execute requires --qualification-sha')
        from ingestion_evaluation.source_authority import SourceAuthorityBackend, SourceAuthorityRunner
        backend = None if args.command == 'source-report' else SourceAuthorityBackend(manifest)
        runner = SourceAuthorityRunner(manifest, sha, backend)
        if args.command == 'source-execute':
            result = runner.execute(args.qualification_sha)
        else:
            result = getattr(runner, args.command.removeprefix('source-'))()
        print(json.dumps(result, default=str))
        return
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
