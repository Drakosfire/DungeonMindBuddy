"""Bounded historical diff replay and disposable, process-local fault witnesses.

Not a selector consumer: every baseline witness runs, and injected failures are
required evidence, never a substitute for or exclusion from ordinary CI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from scripts import ci_domain_shadow as shadow

ROOT = Path(__file__).resolve().parents[1]
WORLD = 'tests/test_world_access_control.py::'
PAGE = 'tests/application_state/test_authored_pages_postgres.py::'
FAULTS = {
    'tenant': (WORLD+'test_owner_has_normal_world_use_and_new_world_is_private',
               'apps/live_control_server/services/world_container_registry.py'),
    'cas': (WORLD+'test_stale_world_cas_cannot_overwrite_serialized_access_state',
            'src/application_state/world_catalog/service.py'),
    'publication': (PAGE+'test_page_draft_save_history_and_database_only_reads',
                    'src/application_state/content/pages.py'),
    'draft': (PAGE+'test_page_draft_save_history_and_database_only_reads',
              'src/application_state/content/pages.py'),
}
HISTORY = (
    'fb3a2d0615a7ad31c1b51f5703180654877801f0',  # private Worlds/action grants
    '4abd73e3b0268dc10ed60b2eb14f4d4c67a30ee9',  # APP metadata owner and CAS
    '6e61f79934b87814aff77ff294ab7908e847f663',  # shared authored page storage
    'dc462abdf191334a8a4ab76b99f4831b2f05ff29',  # newer local draft/save race
)


def historical_replay() -> list[dict]:
    mapping = json.loads((ROOT/'ci/domain-selection-v1.json').read_text())
    results = []
    for commit in HISTORY:
        parent = subprocess.check_output(['git', 'rev-parse', commit+'^'], cwd=ROOT, text=True).strip()
        raw = subprocess.check_output(['git', 'diff', '--name-status', '-z', parent, commit, '--'], cwd=ROOT)
        changes = shadow.parse_diff(raw)
        prediction = shadow.select(changes, mapping)
        if not prediction['full_fallback'] or set(prediction['suites']) != shadow.ALL_SUITES:
            raise RuntimeError('historical high-risk change missed: '+commit)
        results.append(dict(commit=commit, parent=parent, changes=changes, prediction=prediction,
                            scope='actual historical diff replay; historical product tests not rerun'))
    return results


def pytest_addoption(parser):
    parser.addoption('--shadow-injected-fault', choices=tuple(FAULTS))


def pytest_runtest_call(item):
    """Only an explicitly requested witness subprocess can install a fault."""
    fault = item.config.getoption('--shadow-injected-fault')
    if fault is None:
        return
    if item.nodeid != FAULTS[fault][0]:
        raise RuntimeError('fault injection attempted outside its exact witness')
    monkeypatch = item._request.getfixturevalue('monkeypatch')
    if fault == 'tenant':
        from apps.live_control_server.services import world_container_registry as registry
        monkeypatch.setattr(registry, 'require_world_permission', lambda record, **_kwargs: record)
    elif fault == 'cas':
        from application_state.world_catalog import service
        original = service.save_world
        monkeypatch.setattr(service, 'save_world', lambda record, **_kwargs:
            original(record, expected_revision=service.get_world(record.world_id).revision))
    else:
        from application_state.content import pages
        original = pages.commit_page if fault == 'publication' else pages.save_draft
        if fault == 'publication':
            monkeypatch.setattr(pages, 'commit_page', lambda document_id, markdown, **kwargs:
                original(document_id, markdown+'\nINJECTED PUBLICATION CORRUPTION', **kwargs))
        else:
            monkeypatch.setattr(pages, 'save_draft', lambda document_id, markdown, **kwargs:
                pages.get_page(document_id, world_id=kwargs['world_id']))


def check_junit(path: Path, *, fault: str | None, expected: int) -> None:
    cases = list(ET.parse(path).getroot().iter('testcase'))
    if len(cases) != expected or any(case.find('error') is not None or case.find('skipped') is not None for case in cases):
        raise RuntimeError('unexpected collection/setup/skip outcome')
    failures = [case.find('failure') for case in cases if case.find('failure') is not None]
    if fault is None:
        if failures:
            raise RuntimeError('ordinary witness baseline failed')
    elif len(failures) != 1 or not all(term in (failures[0].text or '') for term in {
            'tenant': ('DID NOT RAISE', 'WorldAccessDenied'),
            'cas': ('DID NOT RAISE', 'ApplicationStateConflictError'),
            'publication': ('AssertionError', 'INJECTED PUBLICATION CORRUPTION', 'Second body'),
            'draft': ('AssertionError', 'draft.from_working_copy'),
        }[fault]):
        raise RuntimeError('fault did not reach its expected owner assertion')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if not os.environ.get('DMB_APPLICATION_STATE_TEST_DATABASE_URL'):
        raise RuntimeError('explicit disposable APP test database is required')
    if any(os.environ.get(key) for key in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD')):
        raise RuntimeError('inherited pytest controls forbidden')
    report = dict(source_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  mode='shadow-only', gating_enabled=False, rollout_ready=False,
                  historical=historical_replay(), runs=[],
                  limitations='four backend fault samples; no frontend/native-publication or general zero-miss proof')
    mapping = json.loads((ROOT/'ci/domain-selection-v1.json').read_text())
    witnesses = sorted({value[0] for value in FAULTS.values()})
    try:
        for name, fault in [('baseline-before', None), *((name, name) for name in FAULTS), ('baseline-after', None)]:
            targets = witnesses if fault is None else [FAULTS[fault][0]]
            junit = args.output/(name+'.xml')
            command = [sys.executable, '-m', 'pytest', '-q', '--tb=short', '-p', 'scripts.ci_shadow_evidence',
                       '--junitxml='+str(junit.resolve()), *targets]
            if fault:
                command += ['--shadow-injected-fault', fault]
                prediction = shadow.select([('M', (FAULTS[fault][1],))], mapping)
                if not prediction['full_fallback'] or 'full-regression' not in prediction['suites']:
                    raise RuntimeError('injected product fault origin missed')
            started = time.monotonic()
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=300)
            (args.output/(name+'.log')).write_text(completed.stdout+completed.stderr)
            report['runs'].append(dict(name=name, command=command, exit_code=completed.returncode, elapsed_seconds=round(time.monotonic()-started, 3)))
            if completed.returncode != (0 if fault is None else 1):
                raise RuntimeError('unexpected pytest exit: '+name)
            check_junit(junit, fault=fault, expected=len(targets))
        report['bounded_evidence_passed'] = True
    finally:
        (args.output/'evidence.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
