"""Focused App-fence transport trust, pins, lock and receipt boundary checks."""
import hashlib
from io import BytesIO
from importlib.machinery import SourceFileLoader
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'deploy/production/deploy-buddy-app-fence'
REV, OLD, REC = 'a' * 40, 'b' * 40, 'c' * 40
IMAGE, OLD_IMAGE, REC_IMAGE = ('sha256:' + letter * 64 for letter in 'abc')
REGISTRY = 'sha256:' + 'd' * 64


@pytest.fixture
def helper():
    loader = SourceFileLoader('app_fence_transport', str(HELPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture
def packet(tmp_path, helper):
    root = tmp_path / 'policy'
    directory = root / 'app-fence-packets' / REV
    directory.mkdir(parents=True)
    for folder in [root, directory.parent, directory]:
        folder.chmod(0o700)
    release = {'candidate_source': REV, 'candidate_image': IMAGE, 'old_source': OLD,
               'old_image': OLD_IMAGE, 'recovery_source': REC, 'recovery_image': REC_IMAGE}
    qualification = dict(status='accepted', evidence_sha256='e' * 64,
                         candidate_revision=REV, candidate_id=IMAGE,
                         recovery_revision=REC, recovery_id=REC_IMAGE,
                         source_schema='20261125_0211', target_schema='20261125_0212')
    for name, value in [('operator.py', b'# approved operator\n'),
                        ('dogfood_engine_transport.py', b'# approved transport\n'),
                        ('release.json', json.dumps(release).encode()),
                        ('qualification.json', json.dumps(qualification).encode())]:
        (directory / name).write_bytes(value)
        (directory / name).chmod(0o600)
    manifest = dict(schema='buddy_app_fence_packet_v1', candidate_revision=REV,
                    registry_digest=REGISTRY, candidate_id=IMAGE,
                    rollback_revision=OLD, rollback_id=OLD_IMAGE,
                    recovery_revision=REC, recovery_id=REC_IMAGE,
                    source_schema='20261125_0211', target_schema='20261125_0212',
                    guest_build='review=0;graph=1;build=1;plan=1', files={})
    def seal():
        manifest['files'] = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                             for name in helper.FILES}
        data = json.dumps(manifest).encode()
        (directory / 'manifest.json').write_bytes(data)
        (directory / 'manifest.json').chmod(0o600)
        return [REV, REGISTRY, IMAGE, OLD, OLD_IMAGE, hashlib.sha256(data).hexdigest()]
    return root, directory, manifest, seal


def test_exact_qualified_packet_is_loaded(helper, packet):
    root, directory, manifest, seal = packet
    args = seal()
    actual, loaded = helper.load_packet(args, root=root, uid=os.getuid())
    assert actual == directory and loaded == manifest


@pytest.mark.parametrize('change', ['candidate', 'rollback', 'qualification', 'schema', 'backward_schema', 'old_recovery', 'extra', 'files', 'duplicate'])
def test_resealed_wrong_contract_is_refused(helper, packet, change):
    root, directory, manifest, seal = packet
    if change == 'candidate':
        p = directory / 'release.json'
        p.write_text(json.dumps(json.loads(p.read_text()) | {'candidate_image': OLD_IMAGE}))
    elif change == 'rollback':
        manifest['rollback_id'] = REC_IMAGE
    elif change == 'qualification':
        p = directory / 'qualification.json'
        p.write_text(json.dumps(json.loads(p.read_text()) | {'recovery_id': OLD_IMAGE}))
    elif change == 'schema':
        manifest['target_schema'] = manifest['source_schema']
    elif change == 'backward_schema':
        manifest['target_schema'] = '20261125_0210'
    elif change == 'old_recovery':
        manifest['recovery_id'], manifest['recovery_revision'] = OLD_IMAGE, OLD
    elif change == 'extra':
        manifest['command'] = 'unapproved command'
    args = seal()
    if change == 'files':
        manifest['files']['../../outside.py'] = 'e' * 64
        data = json.dumps(manifest).encode()
        (directory / 'manifest.json').write_bytes(data)
        args[-1] = hashlib.sha256(data).hexdigest()
    elif change == 'duplicate':
        data = (directory / 'manifest.json').read_bytes()
        data = b'{"schema":"buddy_app_fence_packet_v1",' + data[1:]
        (directory / 'manifest.json').write_bytes(data)
        args[-1] = hashlib.sha256(data).hexdigest()
    with pytest.raises(ValueError):
        helper.load_packet(args, root=root, uid=os.getuid())


@pytest.mark.parametrize('change', ['tamper', 'symlink', 'writable_file', 'writable_dir', 'owner', 'manifest_hash', 'unsealed_code', 'cache_directory'])
def test_untrusted_packet_cannot_be_loaded(helper, packet, change):
    root, directory, manifest, seal = packet
    args = seal()
    uid = os.getuid()
    if change == 'tamper':
        (directory / 'operator.py').write_text('# changed after approval\n')
    elif change == 'symlink':
        p = directory / 'operator.py'
        data = p.read_bytes()
        p.unlink()
        target = root / 'outside.py'
        target.write_bytes(data)
        p.symlink_to(target)
    elif change == 'writable_file':
        (directory / 'operator.py').chmod(0o666)
    elif change == 'writable_dir':
        directory.chmod(0o777)
    elif change == 'owner':
        uid += 1
    elif change == 'unsealed_code':
        (directory / 'sitecustomize.py').write_text('# not reviewed\n')
        (directory / 'sitecustomize.py').chmod(0o600)
    elif change == 'cache_directory':
        (directory / '__pycache__').mkdir(mode=0o700)
    else:
        args[-1] = '0' * 64
    expected = {'tamper': 'packet file digest differs', 'manifest_hash': 'packet digest differs',
                'symlink': 'untrusted packet path', 'writable_file': 'untrusted packet path',
                'writable_dir': 'untrusted packet path', 'owner': 'untrusted packet path', 'unsealed_code': 'unsealed packet code',
                'cache_directory': 'unexpected packet file type'}
    with pytest.raises(ValueError, match=expected[change]):
        helper.load_packet(args, root=root, uid=uid)


@pytest.mark.parametrize('mode', ['valid', 'wrong_fd', 'missing_marker', 'contended'])
def test_inherited_lock_is_real_and_remains_held(tmp_path, mode):
    lock = tmp_path / 'lock'
    lock.touch()
    code = '''
import fcntl,os,sys
from pathlib import Path
from importlib.machinery import SourceFileLoader
import importlib.util
loader=SourceFileLoader('fence',sys.argv[1]);spec=importlib.util.spec_from_loader(loader.name,loader)
m=importlib.util.module_from_spec(spec);loader.exec_module(m)
m.LOCK=Path(sys.argv[2]);mode=sys.argv[3]
fd=os.open(str(m.LOCK)+('.wrong' if mode=='wrong_fd' else ''),os.O_RDWR|os.O_CREAT,0o600)
os.dup2(fd,9)
if mode!='missing_marker':os.environ['BUDDY_DEPLOY_LOCK_HELD']='1'
if mode=='contended':
 other=os.open(m.LOCK,os.O_RDWR);fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:m.require_lock()
except (ValueError,BlockingIOError):
 assert mode!='valid';print('refused')
else:
 assert mode=='valid'
 other=os.open(m.LOCK,os.O_RDWR)
 try:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:print('held')
 else:raise AssertionError('deployment lock was not held')
'''
    result = subprocess.run([os.sys.executable, '-c', code, str(HELPER), str(lock), mode],
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ('held' if mode == 'valid' else 'refused')


@pytest.mark.parametrize('failure', [None, 'stale', 'bad_image', 'prepare', 'apply', 'tamper_prepare', 'tamper_apply', 'wrong_live'])
def test_deploy_receipts_follow_real_phase_results(helper, packet, monkeypatch, capsys, failure):
    root, directory, manifest, seal = packet
    args = seal()
    real_load = helper.load_packet
    monkeypatch.setattr(helper, 'CONFIG_ROOT', root)
    monkeypatch.setattr(helper, 'load_packet', lambda values: real_load(values, root=root, uid=os.getuid()))
    monkeypatch.setattr(helper, 'require_lock', lambda: None)
    identities = iter([f'{OLD} {OLD_IMAGE} healthy', f'{OLD} {OLD_IMAGE} healthy',
                       f'{REV} {IMAGE} healthy' if failure != 'wrong_live' else f'{OLD} {OLD_IMAGE} healthy'])
    monkeypatch.setattr(helper, 'identity', lambda: 'stale' if failure == 'stale' else next(identities))
    calls = []
    def run(argv):
        calls.append(argv)
        if 'inspect' in argv:
            return json.dumps({'Id': OLD_IMAGE if failure == 'bad_image' else IMAGE, 'Os': 'linux', 'Architecture': 'amd64', 'Config': {'Labels': {
                'org.opencontainers.image.revision': REV, 'org.dungeonmindbuddy.serving-parent': OLD,
                'org.dungeonmindbuddy.guest-build': manifest['guest_build']}}})
        return ''
    monkeypatch.setattr(helper, 'run', run)
    phases = []
    def operator(argv, **kwargs):
        assert argv[:-1] == ['/usr/bin/python3', '-E', '-s', '-B', str(directory / 'operator.py')]
        assert kwargs == {'check': True, 'env': helper.ENV, 'pass_fds': (9,)}
        phases.append(argv[-1])
        if failure == 'tamper_' + argv[-1]:
            (directory / 'operator.py').write_text('# changed by phase\n')
        if argv[-1] == failure:
            raise subprocess.CalledProcessError(1, argv)
    monkeypatch.setattr(helper.subprocess, 'run', operator)
    if failure:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            helper.deploy(args)
    else:
        helper.deploy(args)
    output = capsys.readouterr().out
    assert ('BUDDY_LIVE' in output) is (failure is None)
    assert (root / 'serving').exists() is (failure is None)
    assert ('BUDDY_STAGED' in output) is (failure not in {'stale', 'bad_image', 'prepare', 'tamper_prepare'})
    if failure == 'stale':
        assert not calls and not phases
    elif failure == 'bad_image':
        assert calls and not phases
    else:
        assert phases == (['prepare'] if failure in {'prepare', 'tamper_prepare'} else ['prepare', 'apply'])
    if failure is None:
        assert f'BUDDY_STAGED {REV} {IMAGE} {REGISTRY}' in output
        assert (root / 'serving').read_text() == f'BUDDY_LIVE {REV} {IMAGE}\n'


def test_dispatcher_accepts_only_fixed_fence_grammar(tmp_path):
    entry = tmp_path / 'entry'
    stub = tmp_path / 'fence'
    stub.write_text('#!/bin/bash\nprintf "%s\\n" "$BUDDY_DEPLOY_LOCK_HELD" "$@"\ncat\n')
    stub.chmod(0o755)
    entry.write_text((ROOT / 'deploy/production/deploy-buddy-release').read_text()
                     .replace('/run/lock/buddy-production-deploy.lock', str(tmp_path / 'lock'))
                     .replace('/usr/local/sbin/deploy-buddy-app-fence', str(stub)))
    good = f'app-fence {REV} {REGISTRY} {IMAGE} {OLD} {OLD_IMAGE} ' + 'e' * 64
    data = '{"manifest.json":"example"}'
    result = subprocess.run(['bash', str(entry), good], input=data,
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['1', REV, REGISTRY, IMAGE, OLD, OLD_IMAGE, 'e' * 64, data]
    for bad in [good + ' extra', good + '\n', good.replace(REV, '../operator', 1), good.replace('app-fence', 'app-fence;false', 1)]:
        result = subprocess.run(['bash', str(entry), bad], text=True, capture_output=True, timeout=10)
        assert result.returncode != 0 and not result.stdout


def test_workflow_uses_same_queue_and_pinned_receipts():
    import yaml
    workflow = yaml.load((ROOT / '.github/workflows/deploy-buddy-app-fence.yml').read_text(), Loader=yaml.BaseLoader)
    ordinary = yaml.load((ROOT / '.github/workflows/deploy-buddy.yml').read_text(), Loader=yaml.BaseLoader)
    assert workflow['permissions'] == {'contents': 'read'}
    assert workflow['concurrency'] == ordinary['concurrency']
    job = workflow['jobs']['deploy']
    assert job['environment'] == 'buddy-production' and job['if'] == "github.ref == 'refs/heads/main'"
    run = job['steps'][1]['run']
    assert 'persist-credentials' in job['steps'][0]['with']
    assert 'app-fence-releases' in run and '< "$ssh_dir/release.json"' in run
    assert 'ssh -n' not in run
    assert '${{ inputs.' not in run and 'StrictHostKeyChecking=yes' in run
    assert 'BUDDY_STAGED $REVISION $CANDIDATE_ID $REGISTRY_DIGEST' in run
    assert 'BUDDY_LIVE $REVISION $CANDIDATE_ID' in run
    assert 'status" == 401' in job['steps'][2]['run']


def test_ordinary_image_dispatch_keeps_existing_protocol(tmp_path):
    entry = tmp_path / 'entry'
    docker = tmp_path / 'docker'
    docker.write_text(f'#!/bin/bash\nprintf "%s\\n" "{OLD} {OLD_IMAGE} healthy"\n')
    docker.chmod(0o755)
    stage = tmp_path / 'stage'
    stage.write_text('#!/bin/bash\nprintf "normal-stage %s\\n" "$*"\n')
    stage.chmod(0o755)
    activate = tmp_path / 'activate'
    activate.write_text('#!/bin/bash\nprintf "normal-live %s\\n" "$*"\n')
    activate.chmod(0o755)
    source = (ROOT / 'deploy/production/deploy-buddy-release').read_text()
    source = source.replace('export PATH=/usr/sbin:/usr/bin:/sbin:/bin', f'export PATH={tmp_path}:/usr/bin:/bin')
    source = source.replace('/run/lock/buddy-production-deploy.lock', str(tmp_path / 'lock'))
    source = source.replace('/usr/local/sbin/stage-buddy-release', str(stage))
    source = source.replace('/usr/local/sbin/activate-buddy-release', str(activate))
    entry.write_text(source)
    request = f'{REV} {REGISTRY} {IMAGE} {OLD} {OLD_IMAGE} default'
    result = subprocess.run(['bash', str(entry), request], text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [f'normal-stage {request}', f'normal-live {REV}']


@pytest.mark.parametrize('operation,timeout', [('pull', 600), ('inspect', 30)])
def test_docker_failure_preserves_diagnostics_and_bounds(helper, monkeypatch, capsys, operation, timeout):
    def fail(argv, **kwargs):
        assert kwargs['timeout'] == timeout and kwargs['env'] == helper.ENV
        raise subprocess.CalledProcessError(1, argv, stderr='Docker operation was denied')
    monkeypatch.setattr(helper.subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        helper.run(['/usr/bin/docker', operation])
    assert 'Docker operation was denied' in capsys.readouterr().err


@pytest.mark.parametrize('change', [None, 'script', 'invalid_digest', 'policy', 'oversize', 'tampered_release'])
def test_authenticated_release_staging(helper, packet, change):
    root, directory, manifest, seal = packet
    if change == 'policy':
        path = directory / 'release.json'
        release = json.loads(path.read_text())
        path.write_text(json.dumps(release | {'backup_tool': 'untrusted-image'}))
    args = seal()
    program = root / 'app-fence-programs' / manifest['files']['operator.py']
    program.mkdir(parents=True)
    program.chmod(0o700)
    program.parent.chmod(0o700)
    for name in helper.PROGRAMS:
        (program / name).write_bytes((directory / name).read_bytes())
        (program / name).chmod(0o600)
        (directory / name).unlink()
    policy = program / 'policy.json'
    policy.write_text('{}')
    policy.chmod(0o600)
    data = {name: (directory / name).read_text() for name in helper.DATA_FILES}
    for name in data:
        (directory / name).unlink()
    directory.rmdir()
    if change == 'script':
        data['operator.py'] = 'assert False'
    elif change == 'invalid_digest':
        args[-1] = 'f' * 64
    elif change == 'tampered_release':
        data['release.json'] += ' '
    elif change == 'oversize':
        data['release.json'] += ' ' * helper.MAX_REQUEST_BYTES

    request = json.dumps(data).encode()
    if change:
        message = {
            'script': 'three reviewed JSON files',
            'invalid_digest': 'submitted manifest digest differs',
            'policy': 'installed program policy',
            'oversize': 'exceeds bounds',
            'tampered_release': 'packet file digest differs',
        }[change]
        with pytest.raises(ValueError, match=message):
            helper.stage_release_data(args, request, root=root, uid=os.getuid())
        assert not directory.exists()
        return

    helper.stage_release_data(args, request, root=root, uid=os.getuid())
    assert helper.load_packet(args, root=root, uid=os.getuid()) == (directory, manifest)
    journal = directory / 'journal.json'
    journal.write_text('{"phase":"drained"}')
    journal.chmod(0o600)
    helper.stage_release_data(args, request, root=root, uid=os.getuid())
    assert journal.read_text() == '{"phase":"drained"}'


def test_request_read_returns_at_most_one_byte_beyond_limit(helper):
    stream = BytesIO(b'a' * (helper.MAX_REQUEST_BYTES + 100))
    assert len(helper.read_request(stream)) == helper.MAX_REQUEST_BYTES + 1
