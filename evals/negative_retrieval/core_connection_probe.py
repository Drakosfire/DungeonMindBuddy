"""Partial witness of actual Core transactions; never a coverage certificate.

Only the pinned synchronous Core PostgreSQL owners are wrapped. The witness
does not enforce settings, inspect product results, or retain connection data.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from hashlib import sha256
from pathlib import Path
from threading import Lock
import inspect
import sys

from .source_window import _scope

_witness_sql = ContextVar("negative_retrieval_core_witness_sql", default=False)
_lock = Lock()
_poisoned = False


def validate_artifact(value, case_id):
    """Validate a partial witness without inferring completeness or absence."""
    fields = {'schema', 'case_id', 'window', 'coverage', 'status', 'connections',
              'transactions', 'verified', 'mismatches', 'errors', 'pending_at_close',
              'owner_source_sha256'}
    if (not isinstance(value, dict) or set(value) != fields
            or value['schema'] != 'dmb_negative_retrieval_core_connection_v1'
            or value['case_id'] != case_id or value['window'] != 'turn_post_v1'
            or value['coverage'] != 'partial'
            or value['status'] not in {'observed', 'uncertain', 'unavailable', 'not_started'}):
        raise ValueError('Invalid Core connection witness')
    for name in ('connections', 'transactions', 'verified'):
        group = value[name]
        if (not isinstance(group, dict) or set(group) != {'scoped', 'unscoped'}
                or any(type(n) is not int or n < 0 for n in group.values())):
            raise ValueError('Invalid Core connection counts')
    if (any(value['verified'][k] > value['transactions'][k] for k in ('scoped', 'unscoped'))
            or any(type(value[k]) is not int or value[k] < 0 for k in ('mismatches', 'errors', 'pending_at_close'))):
        raise ValueError('Invalid Core connection outcomes')
    digest = value['owner_source_sha256']
    if digest is not None and (not isinstance(digest, str) or len(digest) != 64
                               or any(c not in '0123456789abcdef' for c in digest)):
        raise ValueError('Invalid Core owner fingerprint')
    if value['status'] == 'observed' and (digest is None or value['mismatches'] or value['errors']
                                           or value['pending_at_close'] or value['verified'] != value['transactions']):
        raise ValueError('Uncertain Core observation cannot be marked observed')
    if value['status'] in {'unavailable', 'not_started'} and (digest is not None
            or any(value[name][scope] for name in ('connections', 'transactions', 'verified')
                   for scope in ('scoped', 'unscoped'))
            or value['mismatches'] or value['errors'] or value['pending_at_close']):
        raise ValueError('Unavailable Core observation cannot contain observed activity')
    return value


def _identity(connection):
    """Read database and principal identity in the product's current transaction."""
    from psycopg.rows import tuple_row
    token = _witness_sql.set(True)
    try:
        with connection.cursor(row_factory=tuple_row) as cursor:
            return cursor.execute("""
                SELECT current_database(),
                       (SELECT oid::text FROM pg_database WHERE datname=current_database()),
                       (SELECT system_identifier::text FROM pg_control_system()),
                       current_user, session_user,
                       current_setting('transaction_read_only') = 'on'
            """).fetchone()
    finally:
        _witness_sql.reset(token)


def _baseline(dsn, expected):
    """Qualify the non-writing login and its exact pinned database in memory."""
    import psycopg
    from evals.buddy_benchmark.cohort_capture import _endpoint, require_read_only_core

    _endpoint(dsn, expected)
    require_read_only_core(dsn)
    with psycopg.connect(dsn) as connection:
        actual = _identity(connection)
    if (not actual or tuple(actual[:3]) != (expected['database'], str(expected['oid']),
                                             str(expected['system_identifier']))
            or actual[3] != actual[4] or actual[5] is not True):
        raise ValueError('Core baseline identity or read-only session differs')
    return tuple(actual)


@contextmanager
def observe_core_connections(dsn, expected, *, scope_ref):
    """Check known Core transaction admissions without claiming exhaustive coverage.

    A mismatch raises within the product owner's context, preserving its rollback.
    The caller must run in a serial isolated process and pass its live turn token.
    """
    global _poisoned
    if not _lock.acquire(blocking=False):
        raise RuntimeError('Core connection observation requires a serial process')
    if _poisoned:
        _lock.release()
        raise RuntimeError('Core connection observer requires a fresh process')
    state = {'coverage': 'partial', 'status': 'not_started', 'connections': {'scoped': 0, 'unscoped': 0},
             'transactions': {'scoped': 0, 'unscoped': 0}, 'verified': {'scoped': 0, 'unscoped': 0},
             'mismatches': 0, 'errors': 0, 'pending_at_close': 0, 'owner_source_sha256': None}
    guard = Lock()
    baseline = None
    installed = []
    active = True
    pending = 0
    try:
        baseline = _baseline(dsn, expected)
        from dungeonmind.infrastructure.postgres.database import PostgresDatabase, _ScopedReadTransactions
        source = Path(inspect.getsourcefile(PostgresDatabase)).resolve(strict=True)
        state['owner_source_sha256'] = sha256(source.read_bytes()).hexdigest()
        owners = [(PostgresDatabase, 'connect', False), (PostgresDatabase, 'transaction', True),
                  (_ScopedReadTransactions, 'transaction', True)]
        for owner, name, transaction in owners:
            original = getattr(owner, name)
            unwrapped = inspect.unwrap(original)
            if any(inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)
                   for fn in (original, unwrapped)):
                raise TypeError('Asynchronous Core owner is unsupported')

            def bucket():
                return 'scoped' if scope_ref[0] is not None and _scope.get() is scope_ref[0] else 'unscoped'

            if transaction:
                def make_transaction(fn):
                    @wraps(fn)
                    @contextmanager
                    def wrapped(*args, **kwargs):
                        nonlocal pending
                        with guard:
                            watching = active
                            if watching:
                                pending += 1
                        if not watching:
                            # An alias retained beyond the window must be inert.
                            with fn(*args, **kwargs) as connection:
                                yield connection
                            return
                        entered = False
                        try:
                            with fn(*args, **kwargs) as connection:
                                entered = True
                                with guard:
                                    key = bucket()
                                    if active:
                                        state['transactions'][key] += 1
                                try:
                                    actual = _identity(connection)
                                except BaseException:
                                    with guard:
                                        if active:
                                            state['errors'] += 1
                                    raise
                                try:
                                    endpoint_matches = (connection.info.host, str(connection.info.port)) == (
                                        expected['host'], str(expected['port']))
                                except (AttributeError, KeyError, TypeError):
                                    endpoint_matches = False
                                if actual is None or tuple(actual) != baseline or not endpoint_matches:
                                    with guard:
                                        if active:
                                            state['mismatches'] += 1
                                    raise ValueError('Actual Core transaction differs from read-only baseline')
                                with guard:
                                    if active:
                                        state['verified'][key] += 1
                                yield connection
                        finally:
                            with guard:
                                if active and not entered:
                                    state['errors'] += 1
                                pending -= 1
                    return wrapped
                replacement = make_transaction(original)
            else:
                def make_connect(fn):
                    @wraps(fn)
                    def wrapped(*args, **kwargs):
                        connection = fn(*args, **kwargs)
                        with guard:
                            if active:
                                state['connections'][bucket()] += 1
                        return connection
                    return wrapped
                replacement = make_connect(original)
            setattr(owner, name, replacement)
            installed.append((owner, name, original, replacement))
        state['status'] = 'observed'
        yield state
    finally:
        failure = sys.exc_info()[1]
        with guard:
            active = False
            state['pending_at_close'] = pending
            if (pending or state['errors'] or state['mismatches']
                    or state['verified'] != state['transactions']):
                state['status'] = 'uncertain'
        try:
            for owner, name, original, replacement in reversed(installed):
                try:
                    if getattr(owner, name) is not replacement:
                        _poisoned = True
                    else:
                        setattr(owner, name, original)
                except BaseException:
                    _poisoned = True
        finally:
            _lock.release()
        if _poisoned:
            with guard:
                state['status'] = 'uncertain'
                state['errors'] += 1
            error = RuntimeError('Core connection hooks could not be restored; use a fresh process')
            if failure is None:
                raise error
            failure.add_note(str(error))
