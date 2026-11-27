"""Restricted PostgreSQL wire gateway for owned, synthetic benchmark fixtures.

This first policy permits only parameter-free constants and transaction control;
it cannot run Buddy turns or qualify an acquisition journal. The trusted host
retains the owned-clone credential. The untrusted worker receives only a Unix
socket and must be network-isolated separately.
"""
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Lock, Thread
import json
import os
import socket
import stat
import struct
import subprocess
import sys
import time

from .gateway_protocol import FrontendPolicy, ProtocolDenied
_MAX_FRAME = 1024 * 1024
_MAX_BYTES = 8 * 1024 * 1024
_MAX_SESSIONS = 4
_MAX_LIFETIME = 60
_IDLE_TIMEOUT = 10
_PROTOCOL_V3 = 196608
_OWNER_TIMEOUT = 5
_CONNECT_TIMEOUT = 3


def _checked_owner_dsn():
    """Run the existing ownership guard in a bounded child of this worker group."""
    code = ('from evals.negative_retrieval.owned_db_fixture import checked_owned_dsn; '
            'checked_owned_dsn()')
    try:
        result = subprocess.run([sys.executable, '-B', '-c', code], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                timeout=_OWNER_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Owned App verification timed out') from exc
    if result.returncode:
        raise RuntimeError('Owned App verification failed')
    return os.environ['DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL']


def _exact(sock, count):
    parts = bytearray()
    while len(parts) < count:
        data = sock.recv(count - len(parts))
        if not data:
            raise EOFError('PostgreSQL stream closed')
        parts.extend(data)
    return bytes(parts)


def _message(tag, body):
    return tag + struct.pack('!I', len(body) + 4) + body


def _startup(sock, database):
    """Reject worker-controlled target, role, options, cancellation and replication."""
    for _ in range(3):
        size = struct.unpack('!I', _exact(sock, 4))[0]
        if not 8 <= size <= 4096:
            raise ProtocolDenied('Invalid startup length')
        body = _exact(sock, size - 4)
        version = struct.unpack_from('!I', body)[0]
        if version in (80877103, 80877104) and len(body) == 4:
            sock.sendall(b'N')  # Refuse SSL/GSS; the local Unix socket is the boundary.
            continue
        if version != _PROTOCOL_V3 or not body.endswith(b'\0\0'):
            raise ProtocolDenied('Unsupported startup protocol')
        fields = body[4:-1].split(b'\0')
        if fields[-1:] != [b''] or len(fields) % 2 != 1:
            raise ProtocolDenied('Malformed startup fields')
        pairs = list(zip(fields[0:-1:2], fields[1:-1:2]))
        if len(dict(pairs)) != len(pairs):
            raise ProtocolDenied('Duplicate startup field')
        values = dict(pairs)
        if (set(values) - {b'user', b'database', b'client_encoding', b'application_name'}
                or values.get(b'user') != b'sandbox'
                or values.get(b'database') != database.encode('utf-8')
                or values.get(b'client_encoding', b'UTF8').upper() not in {b'UTF8', b'UTF-8'}
                or values.get(b'application_name', b'') not in {b'', b'buddy-negative-eval'}):
            raise ProtocolDenied('Startup does not match the fixed sandbox identity')
        return
    raise ProtocolDenied('Too many startup negotiations')


class _ClosedDatabaseGateway:
    """Single-use, bounded gateway. Its seal describes transport only."""

    def __init__(self, directory, dsn, identity):
        self.directory = Path(directory)
        self.path = self.directory / '.s.PGSQL.15432'
        self._dsn, self._identity = dsn, dict(identity)
        self._database = identity['database']
        self._lock = Lock()
        self._stop = Event()
        self._listener = None
        self._listener_thread = None
        self._threads = []
        self._backend_threads = []
        self._policies = []
        self._sessions = []
        self._sockets = set()
        self._errors = []
        self._bytes = 0
        self._deadline = None
        self._socket_identity = None
        self._finished = False
        self._closed = False

    def start(self):
        directory = self.directory.resolve(strict=True)
        info = directory.stat()
        if (directory != self.directory.absolute() or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700
                or any(directory.iterdir()) or self.path.exists() or self.path.is_symlink()):
            raise ValueError('Gateway requires a private, owned, empty socket path')
        self._listener = socket.socket(socket.AF_UNIX)
        try:
            self._listener.bind(str(self.path))
            os.chmod(self.path, 0o600)
            socket_info = self.path.lstat()
            self._socket_identity = (socket_info.st_dev, socket_info.st_ino)
            self._listener.listen(_MAX_SESSIONS)
            self._listener.settimeout(.2)
            self._deadline = time.monotonic() + _MAX_LIFETIME
            self._listener_thread = Thread(target=self._accept, name='negative-db-gateway')
            self._listener_thread.start()
        except BaseException:
            self._listener.close()
            self._remove_socket()
            raise
        return self

    def _record_error(self, reason):
        with self._lock:
            self._errors.append(reason)
            self._stop.set()

    def _count_bytes(self, count):
        with self._lock:
            self._bytes += count
            if self._bytes > _MAX_BYTES:
                raise ProtocolDenied('Gateway byte limit exceeded')

    def _accept(self):
        while not self._stop.is_set():
            if time.monotonic() >= self._deadline:
                self._record_error('lifetime_limit')
                break
            try:
                client, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if not self._stop.is_set():
                    self._record_error('listener_failure')
                break
            with self._lock:
                if len(self._threads) >= _MAX_SESSIONS:
                    client.close()
                    self._errors.append('session_limit')
                    self._stop.set()
                    break
                policy = FrontendPolicy()
                self._policies.append(policy)
                self._sockets.add(client)
                thread = Thread(target=self._serve, args=(client, policy), name='negative-db-session')
                self._threads.append(thread)
                try:
                    thread.start()
                except BaseException:
                    self._threads.pop()
                    self._sockets.discard(client)
                    client.close()
                    self._errors.append('session_start_failed')
                    self._stop.set()
                    break

    def _serve(self, client, policy):
        import psycopg
        client.settimeout(_IDLE_TIMEOUT)
        raw = None
        backend_thread = None
        try:
            with client:
                _startup(client, self._database)
                if _checked_owner_dsn() != self._dsn:
                    raise ProtocolDenied('Owned App connection changed')
                with psycopg.connect(self._dsn, sslmode='disable', autocommit=True,
                                     connect_timeout=_CONNECT_TIMEOUT,
                                     options='-c statement_timeout=3000') as backend:
                    # Track the actual socket before issuing the identity query:
                    # shutdown can then interrupt a stalled query.
                    raw = socket.socket(fileno=os.dup(backend.pgconn.socket))
                    raw.settimeout(_IDLE_TIMEOUT)
                    with self._lock:
                        self._sockets.add(raw)
                    actual = backend.execute('''SELECT current_database(),
                        (SELECT oid::text FROM pg_database WHERE datname=current_database()),
                        (SELECT system_identifier::text FROM pg_control_system()),
                        current_user, session_user''').fetchone()
                    if (backend.pgconn.ssl_in_use
                            or (backend.info.host, str(backend.info.port)) != (
                                self._identity['host'], str(self._identity['port']))
                            or backend.info.hostaddr != self._identity['host']
                            or backend.info.user != self._identity['user']
                            or actual != (self._database, str(self._identity['oid']),
                                          str(self._identity['system_identifier']),
                                          self._identity['user'], self._identity['user'])):
                        raise ProtocolDenied('Backend differs from owned local database')
                    client.sendall(_message(b'R', struct.pack('!I', 0)))
                    for key in ('server_version', 'server_encoding', 'client_encoding', 'DateStyle',
                                'integer_datetimes', 'standard_conforming_strings', 'TimeZone', 'IntervalStyle'):
                        value = backend.pgconn.parameter_status(key.encode())
                        if value is not None:
                            client.sendall(_message(b'S', key.encode() + b'\0' + value + b'\0'))
                    client.sendall(_message(b'Z', b'I'))
                    backend_thread = Thread(target=self._relay, args=(raw, client, policy, False))
                    backend_thread.start()
                    with self._lock:
                        self._backend_threads.append(backend_thread)
                    self._relay(client, raw, policy, True)
                    try:
                        raw.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    backend_thread.join(_IDLE_TIMEOUT)
                    if backend_thread.is_alive():
                        self._record_error('backend_relay_not_closed')
        except BaseException:
            self._record_error('session_failure')
        finally:
            if raw is not None:
                raw.close()
            with self._lock:
                self._sockets.discard(client)
                if raw is not None:
                    self._sockets.discard(raw)
                self._sessions.append(policy.snapshot())

    def _relay(self, source, destination, policy, frontend):
        try:
            while not self._stop.is_set():
                tag = _exact(source, 1)
                size = struct.unpack('!I', _exact(source, 4))[0]
                if not 4 <= size <= _MAX_FRAME:
                    raise ProtocolDenied('Frame size exceeds policy')
                body = _exact(source, size - 4)
                self._count_bytes(size + 1)
                with self._lock:
                    if frontend:
                        policy.frontend(tag, body)
                    else:
                        policy.backend(tag, body)
                destination.sendall(tag + struct.pack('!I', size) + body)
                if frontend and tag == b'X':
                    return
        except (EOFError, ConnectionResetError, BrokenPipeError):
            with self._lock:
                if not policy.ended:
                    policy.failed = True
                    self._errors.append('unexpected_disconnect')
        except BaseException:
            with self._lock:
                policy.failed = True
                self._errors.append('protocol_or_relay_failure')
            self._stop.set()

    def _remove_socket(self):
        if self._socket_identity is None:
            return
        try:
            info = self.path.lstat()
            if (info.st_dev, info.st_ino) != self._socket_identity or not stat.S_ISSOCK(info.st_mode):
                raise RuntimeError('Gateway socket identity changed')
            self.path.unlink()
            self._socket_identity = None
        except FileNotFoundError:
            raise RuntimeError('Gateway socket disappeared')

    def _close(self):
        if self._closed:
            return
        deadline = time.monotonic() + _IDLE_TIMEOUT
        def join(thread):
            thread.join(max(0, deadline - time.monotonic()))
        self._stop.set()
        if self._listener is not None:
            self._listener.close()
        if self._listener_thread is not None:
            join(self._listener_thread)
        if any(thread.is_alive() for thread in self._threads):
            self._record_error('forced_shutdown')
            with self._lock:
                sockets = tuple(self._sockets)
            for sock in sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            for thread in self._threads:
                join(thread)
        for thread in self._backend_threads:
            join(thread)
        if ((self._listener_thread is not None and self._listener_thread.is_alive())
                or any(thread.is_alive() for thread in self._threads)
                or any(thread.is_alive() for thread in self._backend_threads)):
            self._record_error('threads_not_closed')
        try:
            self._remove_socket()
        except RuntimeError:
            self._record_error('socket_cleanup_failed')
        self._closed = (self._socket_identity is None
                        and (self._listener_thread is None or not self._listener_thread.is_alive())
                        and not any(thread.is_alive() for thread in self._threads)
                        and not any(thread.is_alive() for thread in self._backend_threads))

    def finish(self, worker):
        """Close the gateway only after the actual worker process has exited."""
        if self._finished or not isinstance(worker, subprocess.Popen) or worker.poll() is None:
            raise ValueError('A finished, directly observed worker is required')
        # Let already-exited workers' Terminate frames drain before stopping.
        for thread in self._threads:
            thread.join(1)
        self._close()
        if not self._closed:
            raise RuntimeError('Gateway resources remain open; clone ownership must be retained')
        self._finished = True
        with self._lock:
            sessions = list(self._sessions)
            errors = list(self._errors)
            total_bytes = self._bytes
        clean = (worker.returncode == 0 and len(sessions) == len(self._threads) and bool(sessions)
                 and not errors and all(s['ended'] and s['ready'] and not s['failed']
                                        and not s['pending'] and not s['sync_pending']
                                        and s['transaction_status'] == 'I' for s in sessions))
        return {'schema': 'dmb_negative_retrieval_closed_db_gateway_v1',
                'status': 'transport_sealed' if clean else 'unsealed',
                'sessions': sessions, 'errors': errors, 'bytes': total_bytes,
                'limitations': ['constant and transaction-control SQL only',
                                'worker and container isolation are not attested',
                                'not a complete acquisition journal or qualified benchmark']}


@contextmanager
def owned_gateway(directory):
    """Bind the trusted gateway to this live workstream's verified App clone."""
    from psycopg.conninfo import conninfo_to_dict
    dsn = _checked_owner_dsn()
    ledger_path = Path(os.environ['DMB_NEGATIVE_RETRIEVAL_OWNER_LEDGER']).resolve(strict=True)
    identity = json.loads(ledger_path.read_bytes())['database']
    connection = conninfo_to_dict(dsn)
    if connection['dbname'] != identity['database'] or not connection.get('user'):
        raise ValueError('Gateway target does not match its owner receipt')
    identity['user'] = connection['user']  # In-memory only; never sent to the worker or journal.
    gateway = _ClosedDatabaseGateway(Path(directory).absolute(), dsn, identity).start()
    try:
        yield gateway
    finally:
        if not gateway._finished:
            failure = sys.exc_info()[1]
            try:
                gateway._close()
            except BaseException as cleanup:
                if failure is None:
                    raise
                failure.add_note('Gateway cleanup failed: ' + type(cleanup).__name__)
            else:
                if gateway._errors or not gateway._closed:
                    error = RuntimeError('Gateway cleanup or observation was incomplete')
                    if failure is None:
                        raise error
                    failure.add_note(str(error))
