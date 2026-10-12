"""Read-only operator launcher/rollback planning receipt; no credentials or bodies."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import urlopen

RUNTIME = Path('/tmp/buddy-automatic-chat-reconciliation')
CANDIDATE = Path('/tmp/buddy-agent-source-targets')
PIDS = {'ui': 497672, 'buddy_api': 497657, 'web_api': 497651}
GROUP = 497628
SAFE_ENV = (
    'DMB_AGENT_GRAPH_LOCAL_PROFILE', 'DMB_MANAGED_WORLD_DATA_ROOT', 'DMB_ARTIFACT_DATA_ROOT',
    'DUNGEONMIND_SERVER_ROOT', 'DUNGEONMIND_SERVER_PORT', 'BUDDY_API_PORT', 'BUDDY_UI_PORT',
    'RUN_NO_RELOAD', 'UV_NO_SYNC', 'HERMES_HOME', 'DUNGEONMIND_GRAPH_INGEST_RUNS_ROOT',
    'DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT',
)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    entries = sorted((str(p.relative_to(root)), sha(p)) for p in root.rglob('*') if p.is_file())
    return {'files': len(entries), 'inventory_sha256': hashlib.sha256(
        json.dumps(entries, separators=(',', ':')).encode()).hexdigest()}


raw_env = Path('/proc/497657/environ').read_bytes().split(b'\0')
env = {key.decode(): value.decode() for row in raw_env if b'=' in row
       for key, value in [row.split(b'=', 1)]}
safe_env = {key: env[key] for key in SAFE_ENV if key in env}
processes = []
for name, pid in PIDS.items():
    proc = Path('/proc') / str(pid)
    stat = proc.joinpath('stat').read_text().split()
    assert int(stat[4]) == GROUP
    processes.append({'service': name, 'pid': pid, 'pgid': int(stat[4]),
                      'cwd': str(proc.joinpath('cwd').resolve()),
                      'executable': str(proc.joinpath('exe').resolve())})
assert next(p for p in processes if p['service'] == 'buddy_api')['cwd'] == str(RUNTIME)
files = {}
for name in ('run', 'pyproject.toml', 'uv.lock', 'apps/live-control-ui/package-lock.json', '.env', '.env.development'):
    path = RUNTIME / name
    if path.is_file():
        files[name] = {'sha256': sha(path), 'resolved_path': str(path.resolve())}
state_root = RUNTIME / 'evals/c2_live_prep/live/session_22'
pointer = state_root / 'hermes_thread_pointers.json'
state = {'pointer_sha256': sha(pointer),
         'hermes_profiles': inventory(state_root / 'hermes_agent_profiles')}
profile = Path(safe_env['DMB_AGENT_GRAPH_LOCAL_PROFILE']) if 'DMB_AGENT_GRAPH_LOCAL_PROFILE' in safe_env else None
if profile is not None and profile.is_file():
    files['operator_profile'] = {'sha256': sha(profile), 'resolved_path': str(profile.resolve())}
dependency_probe = (
    'import importlib.metadata,json; d=importlib.metadata.distribution("dungeonmind"); '
    'v=json.loads(d.read_text("direct_url.json") or "{}"); '
    'print(json.dumps({"version":d.version,"commit":v.get("vcs_info",{}).get("commit_id")}))'
)
installed_core = json.loads(subprocess.check_output([str(RUNTIME / '.venv/bin/python'), '-c', dependency_probe], text=True))
authority_identities = {}
for name in ('DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL', 'DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL'):
    if name in env:
        parsed = urlsplit(env[name])
        authority_identities[name] = {'host': parsed.hostname, 'port': parsed.port,
                                     'database': parsed.path.lstrip('/')}
health = {}
for port in (5202, 8000, 7860):
    with urlopen('http://127.0.0.1:' + str(port) + '/health', timeout=5) as response:
        health[str(port)] = response.status
node = next(p for p in processes if p['service'] == 'ui')['executable']
node_version = subprocess.check_output([node, '--version'], text=True).strip()
receipt = {
    'observed_at_utc': datetime.now(timezone.utc).isoformat(),
    'candidate_head': git(CANDIDATE, 'rev-parse', 'HEAD'),
    'candidate_tree': git(CANDIDATE, 'rev-parse', 'HEAD^{tree}'),
    'candidate_launcher_sha256': sha(CANDIDATE / 'run'),
    'candidate_lock_sha256': sha(CANDIDATE / 'uv.lock'),
    'runtime_checkout': str(RUNTIME), 'rollback_head': git(RUNTIME, 'rev-parse', 'HEAD'),
    'rollback_tree': git(RUNTIME, 'rev-parse', 'HEAD^{tree}'),
    'runtime_status': git(RUNTIME, 'status', '--porcelain').splitlines(),
    'processes': processes, 'safe_launch_environment': safe_env,
    'preserved_files': files, 'operator_state': state,
    'python_environment': str((RUNTIME / '.venv').resolve()),
    'installed_runtime_core': installed_core, 'node_version': node_version,
    'candidate_required_core': '13143455b304d748c249bd7bd628134c421bf6d9',
    'live_environment_matches_candidate_core': installed_core['commit'] == '13143455b304d748c249bd7bd628134c421bf6d9',
    'authority_identities': authority_identities, 'health_status': health,
    'live_ports': [5202, 8000, 7860],
    'quiet_authority': 'not granted; fresh open-turn/action and operator-state snapshot required',
    'runtime_swapped': False,
}
Path('/tmp/server-mounted-recap-proof-20261012/launcher-rollback-receipt.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, sort_keys=True))
