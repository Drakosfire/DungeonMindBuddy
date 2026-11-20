"""Bounded private-config constructor and provider-free receipt for the pinned run recipe."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from urllib.parse import urlsplit

from dotenv import dotenv_values

CANDIDATE = Path('/tmp/buddy-runtime-candidate-20261012')
ROLLBACK = Path('/tmp/buddy-automatic-chat-reconciliation')
DATA = Path('/home/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy')
PRIVATE = Path('/home/drakosfire/.local/state/dungeonmindbuddy/runtime-config')
SOURCES = (
    DATA / '.env',
    PRIVATE / 'dogfood-current-main.env',
    Path('/home/drakosfire/.local/state/dungeonmind/recovery/native-live-20261011/dogfood-runtime.env'),
)
OPERATOR = PRIVATE / 'dogfood-local-operator.env'
SESSION = ROLLBACK / 'evals/c2_live_prep/live/session_22'
NODE = Path('/media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/.hermes-runtime/node/bin')
PINS = {
    str(CANDIDATE): 'fad78a85d710f560bc297f867b6e3c1fa4f0940e',
    str(ROLLBACK): '98f0c225066fff9ec836b05ac7d78e0de983e8ff',
}


def _read_private(path):
    info = path.stat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise RuntimeError('private_configuration_permissions_invalid')
    values = dotenv_values(path, interpolate=False)
    if any(value is None for value in values.values()):
        raise RuntimeError('private_configuration_field_missing')
    return values


def build_environment(code_root=CANDIDATE):
    """Return an explicit environment in memory; never print or persist its values."""
    code_root = Path(code_root)
    head = subprocess.check_output(['git', '-C', str(code_root), 'rev-parse', 'HEAD'], text=True).strip()
    if PINS.get(str(code_root)) != head:
        raise RuntimeError('launcher_code_pin_changed')
    if any(path.exists() for path in (code_root / '.env', code_root / '.env.development', code_root.parent / '.env.development')):
        raise RuntimeError('incidental_dotenv_source_present')
    # No ambient credentials, DSNs, model overrides, Python path or venv selector.
    env = {key: os.environ[key] for key in ('HOME', 'USER', 'LANG', 'LC_ALL', 'TZ', 'PATH') if key in os.environ}
    for path in SOURCES:
        env.update(_read_private(path))
    dedicated = (env.get('DUNGEONBUDDY_OPENAI') or '').strip()
    if not dedicated:
        raise RuntimeError('dedicated_buddy_model_key_missing')
    env['OPENAI_API_KEY'] = dedicated
    env.update({
        'PATH': str(NODE) + ':' + env.get('PATH', ''),
        'DMB_AGENT_GRAPH_LOCAL_PROFILE': str(OPERATOR),
        'DMB_MANAGED_WORLD_DATA_ROOT': str(DATA), 'DMB_ARTIFACT_DATA_ROOT': str(DATA),
        'DMB_AGENT_GRAPH_REQUIRED_WORLD_ID': 'elderwyld',
        'DUNGEONMIND_SERVER_ROOT': '/home/drakosfire/Projects/DungeonOverMind/DungeonMindServer',
        'DUNGEONMIND_LIVE_SESSION_DIR': str(SESSION),
        'DMB_HERMES_GRAPH_AGENT_SESSION_PROFILES_ROOT': str(SESSION / 'hermes_agent_profiles'),
        'BUDDY_UI_PORT': '5202', 'BUDDY_API_PORT': '8000', 'DUNGEONMIND_SERVER_PORT': '7860',
        'RUN_NO_RELOAD': '1', 'UV_NO_SYNC': '1',
    })
    # Existing production validator owns the exact six operator fields.
    sys.path[:0] = [str(code_root / 'src'), str(code_root)]
    from src.bootstrap_env import read_local_graph_profile
    env.update(read_local_graph_profile(str(OPERATOR)))
    return env


def prove():
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (*SOURCES, OPERATOR)}
    env = build_environment()
    os.environ.clear()
    os.environ.update(env)
    from application_state.config import load_runtime_dsn
    from apps.live_control_server.config import artifact_data_root, managed_world_data_root, session_dir, world_graph_authority_mode, world_graph_authority_database_url
    from apps.live_control_server.services.agent_graph_policy import resolve_agent_graph_openai_inference
    from apps.live_control_server.services.agent_graph_auth import authenticate_native_graph_principal
    from starlette.requests import Request

    identities = {}
    for name, value in (
        ('native', world_graph_authority_database_url()),
        ('app', load_runtime_dsn()),
    ):
        parsed = urlsplit(value)
        identities[name] = {'host': parsed.hostname, 'port': parsed.port, 'database': parsed.path.lstrip('/')}
    assert identities == {
        'native': {'host': '127.0.0.1', 'port': 54330, 'database': 'dungeonmind_cutover_live_restore_20261011'},
        'app': {'host': '127.0.0.1', 'port': 54331, 'database': 'dungeonbuddy_application_state'},
    }
    assert world_graph_authority_mode() == 'dungeonmind'
    token = os.environ['DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN']
    principal = authenticate_native_graph_principal(Request({
        'type': 'http', 'method': 'GET', 'path': '/', 'query_string': b'',
        'client': ('127.0.0.1', 42200),
        'headers': [(b'authorization', ('Bearer ' + token).encode())],
    }))
    model = resolve_agent_graph_openai_inference(require_api_key=True)
    assert isinstance(model, tuple) and model[0] == 'openai-api'
    assert os.environ['OPENAI_API_KEY'] == env['DUNGEONBUDDY_OPENAI']
    assert artifact_data_root() == managed_world_data_root() == DATA.resolve()
    assert session_dir() == SESSION
    assert Path(os.environ['DMB_HERMES_GRAPH_AGENT_SESSION_PROFILES_ROOT']) == SESSION / 'hermes_agent_profiles'
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == checksum for path, checksum in before.items())
    receipt = {
        'candidate_head': PINS[str(CANDIDATE)],
        'private_sources_in_order': [str(path) for path in SOURCES],
        'operator_profile': str(OPERATOR), 'private_source_sha256': before,
        'incidental_configuration_absent': True, 'authority_identities': identities,
        'native_authority_mode': world_graph_authority_mode(),
        'artifact_root': str(artifact_data_root()), 'managed_root': str(managed_world_data_root()),
        'session_root': str(session_dir()),
        'profiles_root': os.environ['DMB_HERMES_GRAPH_AGENT_SESSION_PROFILES_ROOT'],
        'local_operator_mode': os.environ['DMB_AGENT_GRAPH_AUTH_MODE'],
        'local_operator_token_present': bool(token),
        'local_operator_gm_validation_passed': principal.role == 'gm',
        'dedicated_buddy_model_key_present': bool(env['DUNGEONBUDDY_OPENAI']),
        'dedicated_key_selected': True,
        'provider_identity': model[0], 'model_identity': model[1],
        'private_configs_unchanged': True,
        'listeners_started': False, 'provider_called': False, 'database_connected': False,
    }
    Path('/tmp/buddy-runtime-prep-20261012/effective-config.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    prove()
