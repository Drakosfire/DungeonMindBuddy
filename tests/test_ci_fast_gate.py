"""Additive contract guards; real DB/browser evidence is separate."""
import ast
from types import SimpleNamespace
import pytest
import yaml
from scripts import ci_fast as fast


def test_frontend_contract_uses_default_discovery_and_full_type_build():
    assert fast.CONTRACTS['frontend-tests'] == ('apps/live-control-ui', ('npm', 'test'))
    assert fast.CONTRACTS['frontend-build'] == ('apps/live-control-ui', ('npm', 'run', 'build'))
    assert 'tsc -b && vite build' in (fast.ROOT/'apps/live-control-ui/package.json').read_text()
    assert list((fast.ROOT/'apps/live-control-ui/src/localWorld').rglob('*.test.tsx'))


def test_database_witnesses_exist_at_the_real_owning_boundary():
    assert len(fast.DATABASE_WITNESSES) == 4
    for node in fast.DATABASE_WITNESSES:
        path, name = node.split('::')
        tree = ast.parse((fast.ROOT/path).read_text())
        assert any(isinstance(n, ast.FunctionDef) and n.name == name for n in tree.body)
    assert 'test_world_access_control.py' in fast.DATABASE_WITNESSES[0]


def test_failures_propagate_and_publish_exact_source_duration(monkeypatch, capsys):
    monkeypatch.setattr(fast.subprocess,'check_output',lambda *a,**k:'a'*40+'\n')
    calls=[]
    monkeypatch.setattr(fast.subprocess,'run',lambda *a,**k:calls.append((a,k)) or SimpleNamespace(returncode=7))
    assert fast.execute('frontend-tests') == 7
    assert calls[0][0][0] == ['npm','test']
    assert '"exit_code": 7' in capsys.readouterr().out


@pytest.mark.parametrize('key',['PYTEST_ADDOPTS','PYTEST_PLUGINS','PYTEST_DISABLE_PLUGIN_AUTOLOAD'])
def test_hidden_pytest_controls_fail_before_command(monkeypatch,key):
    monkeypatch.setenv(key,'hidden')
    monkeypatch.setattr(fast.subprocess,'run',lambda *a,**k:pytest.fail('must not run'))
    with pytest.raises(ValueError,match='inherited pytest'):
        fast.execute('auth-database')


def test_workflow_adds_unfiltered_mandatory_jobs_without_replacing_old_gates():
    workflow=yaml.load((fast.ROOT/'.github/workflows/additive-pr.yml').read_text(),Loader=yaml.BaseLoader)
    assert set(workflow['on']['pull_request']) == {'branches','types'}
    assert workflow['permissions'] == {'contents':'read'}
    assert set(workflow['jobs']) == {'frontend','auth-database','additive-result'}
    assert workflow['jobs']['additive-result']['if'] == 'always()'
    assert set(workflow['jobs']['additive-result']['needs']) == {'frontend','auth-database'}
    steps=workflow['jobs']['frontend']['steps']
    build=next(step for step in steps if step.get('id')=='build')
    assert "steps.prepare.outcome == 'success'" in build['if']
    assert not any('continue-on-error' in step for job in workflow['jobs'].values() for step in job['steps'])
    for path in ('hosted-validation.yml','world-ownership-core.yml'):
        assert (fast.ROOT/'.github/workflows'/path).is_file()
