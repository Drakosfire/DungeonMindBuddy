"""Report conservative domain predictions. This module never executes test selection."""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALL_SUITES = {'full-regression', 'frontend-tests', 'frontend-build', 'qualification-visual'}


def canonical(path: str) -> bool:
    return bool(path) and not path.startswith('/') and '\\' not in path and '..' not in PurePosixPath(path).parts and PurePosixPath(path).as_posix() == path


def validate(mapping: dict) -> None:
    if not isinstance(mapping, dict) or type(mapping.get('version')) is not int or mapping['version'] != 1 or mapping.get('mode') != 'shadow-only':
        raise ValueError('unsupported mapping version/mode')
    domains = mapping['domains']
    if not isinstance(domains, dict) or not domains or any(not isinstance(row, dict) or set(row) != {'depends_on', 'suites'} or
            not isinstance(row['depends_on'], list) or not isinstance(row['suites'], list) or
            not set(row['depends_on']) <= domains.keys() or not set(row['suites']) <= ALL_SUITES for row in domains.values()):
        raise ValueError('invalid domain closure or suite')
    if not isinstance(mapping['paths'], list) or not mapping['paths']:
        raise ValueError('invalid path list')
    for field in ('shared_files', 'shared_prefixes'):
        if not isinstance(mapping[field], list) or any(not isinstance(value, str) or not value for value in mapping[field]):
            raise ValueError('invalid shared paths')
    for rule in mapping['paths']:
        if not isinstance(rule, dict) or rule.get('domain') not in domains or ('exact' in rule) == ('prefix' in rule):
            raise ValueError('invalid path rule')
        value = rule.get('exact', rule.get('prefix'))
        if not isinstance(value, str) or not canonical(value.rstrip('/')) or not isinstance(rule.get('suffix', ''), str):
            raise ValueError('invalid path match')
    for start in domains:
        def visit(node, active):
            if node in active:
                raise ValueError('cyclic dependency')
            for child in domains[node]['depends_on']:
                visit(child, active | {node})
        visit(start, set())


def full(reason: str, **metadata) -> dict:
    return dict(version=1, mode='shadow-only', gating_enabled=False, full_fallback=True,
        reasons=[reason], domains=[], suites=sorted(ALL_SUITES), **metadata)


def select(changes: list[tuple[str, tuple[str, ...]]], mapping: dict, *, reliable=True, override=False) -> dict:
    if override:
        return full('explicit-full-override')
    if not reliable:
        return full('unreliable-diff')
    try:
        validate(mapping)
        if not changes:
            return full('empty-diff')
        domains = set()
        for status, paths in changes:
            if status not in {'A', 'M'}:
                return full('rename-deletion-or-nonordinary-change')
            if len(paths) != 1 or not canonical(paths[0]):
                return full('invalid-path')
            path = paths[0]
            if path in mapping['shared_files'] or any(path.startswith(p) for p in mapping['shared_prefixes']):
                return full('shared-contract-change')
            matches = {rule['domain'] for rule in mapping['paths'] if
                (rule.get('exact') == path or ('prefix' in rule and path.startswith(rule['prefix'])
                    and path.endswith(rule.get('suffix', ''))))}
            if not matches:
                return full('unknown-path')
            domains.update(matches)
        pending = list(domains)
        while pending:
            for child in mapping['domains'][pending.pop()]['depends_on']:
                if child not in domains:
                    domains.add(child)
                    pending.append(child)
        suites = {suite for domain in domains for suite in mapping['domains'][domain]['suites']}
        if 'full-regression' in suites:
            return full('runtime-domain-requires-full')
        return dict(version=1, mode='shadow-only', gating_enabled=False, full_fallback=False,
            reasons=['prediction-only-current-gates-unchanged'], domains=sorted(domains), suites=sorted(suites))
    except (KeyError, TypeError, ValueError, RecursionError):
        return full('invalid-mapping-or-input')


def parse_diff(raw: bytes) -> list[tuple[str, tuple[str, ...]]]:
    if not raw:
        return []
    if not raw.endswith(b'\0'):
        raise ValueError('truncated diff')
    tokens = raw.decode('utf-8', errors='strict').split('\0')[:-1]
    changes = []
    while tokens:
        status = tokens.pop(0)
        count = 2 if re.fullmatch(r'[RC](?:100|[1-9]?\d)', status) else 1
        if not re.fullmatch(r'[AMDTUXB]|[RC](?:100|[1-9]?\d)', status) or len(tokens) < count:
            raise ValueError('invalid status/record')
        paths = tuple(tokens[:count])
        del tokens[:count]
        if not all(canonical(path) for path in paths):
            raise ValueError('invalid diff path')
        changes.append((status, paths))
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    changes = []
    merge_base = None
    try:
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
            raise ValueError('dirty source')
        if not all(re.fullmatch('[0-9a-f]{40}', value) for value in (args.base, args.head)) or args.head != actual:
            raise ValueError('unverified source')
        merge_base = subprocess.check_output(['git', 'merge-base', args.base, args.head], cwd=ROOT, text=True).strip()
        raw = subprocess.check_output(['git', 'diff', '--name-status', '-z', merge_base, args.head, '--'], cwd=ROOT)
        changes = parse_diff(raw)
        mapping = json.loads((ROOT/'ci/domain-selection-v1.json').read_text())
        result = select(changes, mapping, override=args.full)
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        result = full('diff-or-mapping-read-error')
    result.update(source_sha=actual, requested_head=args.head, base=args.base, merge_base=merge_base,
        changes=[{'status': status, 'paths': list(paths)} for status, paths in changes])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
