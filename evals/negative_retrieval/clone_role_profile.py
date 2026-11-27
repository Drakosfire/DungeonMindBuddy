"""Host-only, crash-reconcilable profile for one owned synthetic revision.

This deliberately does not secure an application turn. The caller must enforce
worker isolation and role containment; the profile grants a restricted read and
is usable only under the existing exclusive owner/worker contract.
"""
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4
import json
import os
import stat

from psycopg import connect, sql
from psycopg.conninfo import conninfo_to_dict

from .owned_db_fixture import checked_owned_dsn

_SCHEMA = 'dmb_negative_clone_role_profile_v1'
_ROLE = 'pg_database_owner'


def _owner():
    dsn = checked_owned_dsn()
    ledger = json.loads(Path(os.environ['DMB_NEGATIVE_RETRIEVAL_OWNER_LEDGER']).read_bytes())
    clone = ledger['database']
    endpoint = conninfo_to_dict(dsn)
    identity = {k: clone[k] for k in ('database', 'host', 'port', 'oid', 'system_identifier')}
    identity['user'] = endpoint['user']
    run = Path(ledger['current_run']).resolve(strict=True)
    return dsn, identity, run


def _receipt_path(path, run):
    path = Path(path)
    if not path.is_absolute() or path.name != 'clone-role-profile.json':
        raise ValueError('Invalid profile receipt name')
    parent = path.parent.resolve(strict=True)
    if parent.parent != run.parent or path.parent != parent:
        raise ValueError('Receipt is outside this owner workstream')
    info = parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Receipt directory is not private and owned')
    return parent / path.name


def _store(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return sha256(raw).hexdigest()


def _load(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        info = os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > 65536:
            raise ValueError('Profile receipt is not private and owned')
        raw = f.read(65537)
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('schema') != _SCHEMA:
        raise ValueError('Invalid profile receipt')
    return value, sha256(raw).hexdigest()


def _connect(dsn, identity):
    # Verify the same guarded DSN again before opening the actual writing session.
    if checked_owned_dsn() != dsn:
        raise ValueError('Owned database connection changed')
    conn = connect(dsn, connect_timeout=3, options='-c statement_timeout=5000 -c lock_timeout=2000')
    try:
        actual = conn.execute('''SELECT current_database(),
            (SELECT oid::text FROM pg_database WHERE datname=current_database()),
            (SELECT system_identifier::text FROM pg_control_system()), current_user, session_user''').fetchone()
        if (actual != (identity['database'], str(identity['oid']), str(identity['system_identifier']),
                       identity['user'], identity['user'])
                or (conn.info.host, conn.info.port, conn.info.user) !=
                   (identity['host'], identity['port'], identity['user'])
                or conn.info.hostaddr != identity['host'] or conn.pgconn.ssl_in_use):
            raise ValueError('Writing connection does not match the owned clone')
        return conn
    except BaseException:
        conn.close()
        raise


def _snapshot(conn):
    relation = conn.execute('''SELECT c.oid::text,n.oid::text,pg_get_userbyid(c.relowner),
        pg_get_userbyid(n.nspowner),c.relrowsecurity,c.relforcerowsecurity,c.relacl::text,n.nspacl::text,
        has_table_privilege(%s,c.oid,'SELECT'),has_schema_privilege(%s,n.oid,'USAGE'),
        pg_has_role(%s,c.relowner,'MEMBER')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.oid='content.work_revision'::regclass''', (_ROLE, _ROLE, _ROLE)).fetchone()
    columns = conn.execute('''SELECT attnum,attacl::text FROM pg_attribute
        WHERE attrelid='content.work_revision'::regclass AND attnum>0 AND NOT attisdropped
        AND attacl IS NOT NULL ORDER BY attnum''').fetchall()
    policies = conn.execute('''SELECT polname,polcmd,polpermissive,polroles::text,
        pg_get_expr(polqual,polrelid),pg_get_expr(polwithcheck,polrelid)
        FROM pg_policy WHERE polrelid='content.work_revision'::regclass ORDER BY polname''').fetchall()
    role = conn.execute('''SELECT oid::text,rolcanlogin,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,
        rolinherit FROM pg_roles WHERE rolname=%s''', (_ROLE,)).fetchone()
    memberships = conn.execute('''SELECT roleid::text,admin_option FROM pg_auth_members
        WHERE member=(SELECT oid FROM pg_roles WHERE rolname=%s) ORDER BY roleid''', (_ROLE,)).fetchall()
    if relation is None or role is None:
        raise ValueError('Profile objects are missing')
    return {'relation': list(relation), 'columns': [list(r) for r in columns],
            'policies': [list(r) for r in policies], 'role': list(role),
            'memberships': [list(r) for r in memberships]}


def _lock_and_check_idle(conn):
    conn.execute('LOCK TABLE content.work_revision IN ACCESS EXCLUSIVE MODE')
    others = conn.execute('''SELECT count(*) FROM pg_stat_activity
        WHERE datid=(SELECT oid FROM pg_database WHERE datname=current_database())
        AND pid<>pg_backend_pid()''').fetchone()[0]
    if others:
        raise ValueError('Owned clone still has other database sessions')


def _install(conn, policy, revision):
    conn.execute('ALTER TABLE content.work_revision ENABLE ROW LEVEL SECURITY')
    conn.execute(sql.SQL('CREATE POLICY {} ON content.work_revision FOR SELECT TO pg_database_owner '
                         'USING (work_revision_id = {}::uuid)').format(sql.Identifier(policy), sql.Literal(str(revision))))
    conn.execute('GRANT USAGE ON SCHEMA content TO pg_database_owner')
    conn.execute('GRANT SELECT ON content.work_revision TO pg_database_owner')


def _remove(conn, policy):
    conn.execute(sql.SQL('DROP POLICY {} ON content.work_revision').format(sql.Identifier(policy)))
    conn.execute('ALTER TABLE content.work_revision DISABLE ROW LEVEL SECURITY')
    conn.execute('REVOKE SELECT ON content.work_revision FROM pg_database_owner')
    conn.execute('REVOKE USAGE ON SCHEMA content FROM pg_database_owner')


def install(receipt_path, fixture_revision):
    """Install a fixed profile after the trusted caller verifies synthetic provenance."""
    if not isinstance(fixture_revision, UUID):
        raise TypeError('Fixture identity must be a host-validated UUID')
    dsn, identity, run = _owner()
    path = _receipt_path(receipt_path, run)
    if path.parent != run:
        raise ValueError('New profile receipt must belong to the current run')
    policy = 'buddy_negative_scope_' + uuid4().hex
    with _connect(dsn, identity) as conn:
        _lock_and_check_idle(conn)
        baseline = _snapshot(conn)
        relation, role = baseline['relation'], baseline['role']
        if (relation[4:6] != [False, False] or relation[8:] != [False, False, False]
                or baseline['policies'] or role[1:6] != [False] * 5):
            raise ValueError('Unexpected baseline: clone requires operator review')
        conn.execute('SAVEPOINT profile_preview')
        _install(conn, policy, fixture_revision)
        active = _snapshot(conn)
        _remove(conn, policy)
        cleaned = _snapshot(conn)
        conn.execute('ROLLBACK TO SAVEPOINT profile_preview')
        if _snapshot(conn) != baseline:
            raise ValueError('Profile preview did not roll back exactly')
        receipt = {'schema': _SCHEMA, 'identity': identity, 'policy': policy,
                   'revision': str(fixture_revision), 'baseline': baseline,
                   'active': active, 'cleaned': cleaned}
        digest = _store(path, receipt)  # Durable before the committing transaction.
        _install(conn, policy, fixture_revision)
        if _snapshot(conn) != active:
            raise ValueError('Profile installation differs from preview')
    return {'receipt_sha256': digest, 'state': 'active'}


def recover(receipt_path):
    """Reconcile a prior committed or interrupted install; fail closed on drift."""
    dsn, identity, run = _owner()
    path = _receipt_path(receipt_path, run)
    receipt, digest = _load(path)
    if receipt.get('identity') != identity:
        raise ValueError('Profile receipt identifies a different clone')
    policy = receipt.get('policy')
    if (not isinstance(policy, str) or not policy.startswith('buddy_negative_scope_')
            or len(policy) != 53 or any(c not in '0123456789abcdef' for c in policy[21:])):
        raise ValueError('Invalid profile policy identity')
    UUID(receipt['revision'])
    with _connect(dsn, identity) as conn:
        _lock_and_check_idle(conn)
        current = _snapshot(conn)
        if current == receipt.get('baseline') == receipt.get('cleaned'):
            state = 'inactive'
        elif current == receipt.get('baseline'):
            state = 'not_applied'
        elif current == receipt.get('cleaned'):
            state = 'already_cleaned'
        elif current == receipt.get('active'):
            _remove(conn, policy)
            if _snapshot(conn) != receipt.get('cleaned'):
                raise ValueError('Profile cleanup differs from preview')
            state = 'cleaned'
        else:
            raise ValueError('Profile state drifted; quarantine the owned clone')
    return {'receipt_sha256': digest, 'state': state}
