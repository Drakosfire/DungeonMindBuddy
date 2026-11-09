import json
from itertools import combinations
import pytest
from scripts import ci_domain_shadow as shadow


def mapping():
    return json.loads((shadow.ROOT/'ci/domain-selection-v1.json').read_text())


def test_docs_and_isolated_presentation_are_predictions_only():
    for path, suites in [('Docs/Guide.md',set()),('apps/live-control-ui/src/guidedTour/guidedTour.css',{'frontend-tests','frontend-build','qualification-visual'})]:
        result=shadow.select([('M',(path,))],mapping())
        assert set(result['suites'])==suites
        assert result['mode']=='shadow-only' and result['gating_enabled'] is False


@pytest.mark.parametrize('path',['AGENTS.md','ci/contracts.json','.github/workflows/x.yml','scripts/new.py',
    'src/application_state/migrations/new.py','apps/live_control_server/services/hosted_auth.py',
    'apps/live-control-ui/package-lock.json','unknown/new.ts','apps/live-control-ui/src/styles.css'])
def test_shared_and_unknown_changes_require_full(path):
    assert set(shadow.select([('M',(path,))],mapping())['suites'])==shadow.ALL_SUITES


@pytest.mark.parametrize('status,paths',[('D',('Docs/x.md',)),('R100',('Docs/x.md','Docs/y.md')),('C50',('Docs/x.md','README.md'))])
def test_rename_deletion_and_copy_are_full(status,paths):
    raw=(status+'\0'+'\0'.join(paths)+'\0').encode()
    assert shadow.parse_diff(raw)==[(status,paths)]
    assert shadow.select(shadow.parse_diff(raw),mapping())['full_fallback']


@pytest.mark.parametrize('raw',[b'M\0Docs/x.md',b'R100\0Docs/x.md\0',b'Z\0x\0',b'M\0../x\0',b'M\0x//y\0',b'M\0\xff\0'])
def test_malformed_diffs_cannot_be_silently_used(raw):
    with pytest.raises((ValueError,UnicodeError)):
        shadow.parse_diff(raw)


def test_dependency_closure_and_invalid_mapping_fail_closed():
    assert shadow.select([('M',('apps/live_control_server/services/native_graph_reads.py',))],mapping())['full_fallback']
    broken=mapping()
    broken['domains']['runtime']['depends_on']=['native']
    assert shadow.select([('M',('Docs/x.md',))],broken)['full_fallback']
    assert shadow.select([],mapping())['full_fallback']
    assert shadow.select([('M',('Docs/x.md',))],mapping(),reliable=False)['full_fallback']
    assert shadow.select([('M',('Docs/x.md',))],mapping(),override=True)['full_fallback']


def test_mixed_changes_are_monotone_and_never_lose_required_suites():
    records=[('M',(p,)) for p in ['Docs/x.md','apps/live-control-ui/src/guidedTour/guidedTour.css','unknown.py','src/application_state/schema.py']]
    for count in range(1,len(records)+1):
        for subset in combinations(records,count):
            before=set(shadow.select(list(subset),mapping())['suites'])
            for extra in records:
                assert before <= set(shadow.select([*subset,extra],mapping())['suites'])


@pytest.mark.parametrize('fault,path',[('tenant','apps/live_control_server/services/hosted_auth.py'),
    ('cas','src/application_state/world_catalog/service.py'),('publication','apps/live_control_server/services/native_authored_references.py'),
    ('draft','apps/live-control-ui/src/localWorld/localWorldSurface/LocalWorldSurface.tsx')])
def test_fault_origin_replay_demands_full_not_a_product_fault_proof(fault,path):
    result=shadow.select([('M',(path,))],mapping())
    assert result['full_fallback'],fault
    assert 'full-regression' in result['suites']


@pytest.mark.parametrize('problem',['head','history','dirty'])
def test_cli_source_or_diff_errors_publish_full_fallback(monkeypatch,tmp_path,problem):
    import sys
    import subprocess
    output=tmp_path/'report.json'
    sha='a'*40
    monkeypatch.setattr(sys,'argv',['shadow','--base','b'*40,'--head','c'*40 if problem=='head' else sha,'--output',str(output)])
    def git(argv,**kwargs):
        if argv[1]=='rev-parse':
            return sha+'\n'
        if argv[1]=='status':
            return ' M tracked.py' if problem=='dirty' else ''
        raise subprocess.CalledProcessError(1,argv)
    monkeypatch.setattr(shadow.subprocess,'check_output',git)
    assert shadow.main()==0
    report=json.loads(output.read_text())
    assert report['source_sha']==sha and report['full_fallback']
    assert report['gating_enabled'] is False


def test_workflow_has_no_selector_consumer_or_write_permission():
    import yaml
    data=yaml.load((shadow.ROOT/'.github/workflows/domain-shadow.yml').read_text(),Loader=yaml.BaseLoader)
    assert data['permissions']=={'contents':'read'}
    assert set(data['on']['pull_request'])=={'branches','types'}
    commands='\n'.join(step.get('run','') for step in data['jobs']['shadow-report']['steps'])
    assert 'ci_domain_shadow.py --base' in commands
    assert 'ci_fast.py' not in commands and 'ci_contract.py run' not in commands


@pytest.mark.parametrize('field,value',[('domains',['runtime']),('domains','runtime'),('domains',None),
    ('paths',None),('paths',[None]),('shared_files',None),('shared_prefixes',[None]),('version',True)])
def test_malformed_mapping_shapes_publish_full_fallback(field,value):
    broken=mapping()
    broken[field]=value
    result=shadow.select([('M',('Docs/x.md',))],broken)
    assert result['full_fallback'] and set(result['suites'])==shadow.ALL_SUITES


def test_actual_pinned_historical_changes_replay_to_full():
    from scripts.ci_shadow_evidence import historical_replay, HISTORY
    results = historical_replay()
    assert [row['commit'] for row in results] == list(HISTORY)
    assert all(row['changes'] and row['parent'] != row['commit'] for row in results)
    assert all(row['prediction']['gating_enabled'] is False and
               row['prediction']['full_fallback'] for row in results)


@pytest.mark.parametrize('outcome', ['error', 'skip', 'extra', 'absent', 'wrong-failure'])
def test_fault_evidence_rejects_non_owner_assertion_outcomes(tmp_path, outcome):
    from scripts.ci_shadow_evidence import check_junit
    rows = {
        'error': '<testcase><error>setup failure</error></testcase>',
        'skip': '<testcase><skipped/></testcase>',
        'extra': '<testcase/><testcase/>',
        'absent': '<testcase/>',
        'wrong-failure': '<testcase><failure>RuntimeError: unrelated defect</failure></testcase>',
    }
    path = tmp_path/'out.xml'
    path.write_text('<testsuite>'+rows[outcome]+'</testsuite>')
    with pytest.raises(RuntimeError):
        check_junit(path, fault='tenant', expected=1)


def test_fault_origins_are_backend_full_fallback_and_no_selection_consumer():
    from scripts.ci_shadow_evidence import FAULTS
    for target, path in FAULTS.values():
        assert target.startswith('tests/') and '::test_' in target
        prediction = shadow.select([('M', (path,))], mapping())
        assert prediction['full_fallback'] and set(prediction['suites']) == shadow.ALL_SUITES
        assert prediction['gating_enabled'] is False
