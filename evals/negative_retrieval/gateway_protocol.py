"""Fail-closed PostgreSQL frontend policy for the benchmark gateway.

The default permits only parameter-free constants, transaction controls and
idle deallocation of prepared statements.
An experimental host-only policy also accepts one exact fixture revision read.
Neither policy is an allowlist for a full Buddy turn.
"""
from collections import deque
import hashlib
import struct
from uuid import UUID


# Exact bytes, not normalized SQL. These operations cannot access source data.
_SAFE = {
    b'SELECT 1': 'constant',
    b'SELECT 17': 'constant',
    b'BEGIN': 'transaction',
    b'COMMIT': 'transaction',
    b'ROLLBACK': 'transaction',
    b'DEALLOCATE ALL': 'session',
}
# Exact production query bytes observed in a synthetic owned-clone replay.
_REVISION_SQL = (b"\n            SELECT work_revision_id, work_object_id, world_id, revision_n,"
                 b"\n                   markdown, content_sha256, created_at"
                 b"\n            FROM content.work_revision"
                 b"\n            WHERE work_revision_id = $1"
                 b"\n            ")
_MAX_NAMES = 128


class ProtocolDenied(ValueError):
    """An operation cannot be forwarded under this deliberately narrow policy."""


def _cstring(body, offset, limit=128):
    end = body.find(b'\0', offset)
    if end < 0 or end - offset > limit:
        raise ProtocolDenied('Malformed protocol name')
    return body[offset:end], end + 1


def _formats(body, offset):
    if offset + 2 > len(body):
        raise ProtocolDenied('Malformed format list')
    count = struct.unpack_from('!H', body, offset)[0]
    offset += 2
    if count > 1 or offset + 2 * count > len(body):
        raise ProtocolDenied('Unsupported format list')
    for _ in range(count):
        if struct.unpack_from('!H', body, offset)[0] not in (0, 1):
            raise ProtocolDenied('Unsupported format code')
        offset += 2
    return offset


class FrontendPolicy:
    """Track one backend session. A denied or ambiguous session cannot seal."""

    def __init__(self, *, fixture_revision=None, max_messages=2000, max_attempts=500):
        if fixture_revision is not None and not isinstance(fixture_revision, UUID):
            raise TypeError("fixture_revision must be a host-validated UUID")
        self._fixture_revision = fixture_revision
        self.statements = {}
        self.portals = {}
        self.pending = deque()
        self.events = []
        self.messages = 0
        self.max_messages = max_messages
        self.max_attempts = max_attempts
        self.failed = False
        self.ended = False
        self.ready = True
        self.sync_pending = False
        self.transaction_status = 'I'

    def deny(self, reason):
        self.failed = True
        raise ProtocolDenied(reason)

    def _attempt(self, query, kind):
        if len(self.events) >= self.max_attempts:
            self.deny('Attempt limit exceeded')
        event = {'sequence': len(self.events), 'kind': kind,
                 'query_sha256': hashlib.sha256(query).hexdigest(),
                 'category': (_SAFE[query] if query in _SAFE else 'saved_revision_body'), 'outcome': 'pending'}
        self.events.append(event)
        self.pending.append(event)

    def frontend(self, tag, body):
        """Validate one frame and record its execution before it may be sent."""
        try:
            self.messages += 1
            if self.messages > self.max_messages or self.ended or self.failed:
                self.deny('Session unavailable or message limit exceeded')
            if not isinstance(tag, bytes) or len(tag) != 1 or not isinstance(body, bytes):
                self.deny('Malformed frontend frame')
            if self.sync_pending:
                self.deny('Pipelining across synchronization is unsupported')
            if tag == b'Q':
                if not self.ready or not body.endswith(b'\0') or b'\0' in body[:-1]:
                    self.deny('Malformed or pipelined simple query')
                query = body[:-1]
                if query not in _SAFE:
                    self.deny('Unapproved SQL')
                if query == b'DEALLOCATE ALL':
                    if self.transaction_status != 'I' or self.pending:
                        self.deny('Deallocation requires an idle session')
                    self.statements.clear()
                    self.portals.clear()
                self._attempt(query, 'simple')
                self.ready = False
                self.sync_pending = True
            elif tag == b'P':
                name, at = _cstring(body, 0)
                query, at = _cstring(body, at, limit=1024)
                if query == b'DEALLOCATE ALL':
                    self.deny('Prepared deallocation is unsupported')
                revision_query = query == _REVISION_SQL and self._fixture_revision is not None
                if at + 2 > len(body):
                    self.deny('Malformed Parse')
                count = struct.unpack_from('!H', body, at)[0]
                at += 2
                if revision_query:
                    if count not in (0, 1) or at + 4 * count != len(body):
                        self.deny('Malformed revision parameter types')
                    if count and struct.unpack_from('!I', body, at)[0] not in (0, 2950):
                        self.deny('Unexpected revision parameter type')
                elif query not in _SAFE or count != 0 or at != len(body):
                    self.deny('Unapproved SQL or parameter types')
                if name and name in self.statements:
                    self.deny('Duplicate prepared statement')
                if len(self.statements) >= _MAX_NAMES and name not in self.statements:
                    self.deny('Prepared statement limit exceeded')
                self.statements[name] = query
                if not name:
                    self.portals.pop(b'', None)
                self.ready = False
            elif tag == b'B':
                portal, at = _cstring(body, 0)
                statement, at = _cstring(body, at)
                if statement not in self.statements:
                    self.deny('Unknown prepared statement')
                format_start = at
                at = _formats(body, at)
                format_count = struct.unpack_from('!H', body, format_start)[0]
                binary = format_count == 1 and struct.unpack_from('!H', body, format_start + 2)[0] == 1
                if at + 2 > len(body):
                    self.deny('Malformed parameter count')
                count = struct.unpack_from('!H', body, at)[0]
                at += 2
                if self.statements[statement] == _REVISION_SQL:
                    if count != 1 or at + 4 > len(body):
                        self.deny('Revision requires one parameter')
                    length = struct.unpack_from('!i', body, at)[0]
                    at += 4
                    expected = (self._fixture_revision.bytes if binary
                                else str(self._fixture_revision).encode('ascii'))
                    if length != len(expected) or body[at:at + length] != expected:
                        self.deny('Revision parameter does not match fixture')
                    at += length
                elif count != 0:
                    self.deny('Bound parameters are unsupported')
                at = _formats(body, at)
                if at != len(body) or (portal and portal in self.portals):
                    self.deny('Malformed or duplicate portal')
                if len(self.portals) >= _MAX_NAMES and portal not in self.portals:
                    self.deny('Portal limit exceeded')
                self.portals[portal] = self.statements[statement]
                self.ready = False
            elif tag in (b'D', b'C'):
                if not body or body[:1] not in (b'S', b'P'):
                    self.deny('Unsupported Describe or Close')
                name, at = _cstring(body, 1)
                target = self.statements if body[:1] == b'S' else self.portals
                if at != len(body) or name not in target:
                    self.deny('Unknown Describe or Close target')
                if tag == b'C':
                    del target[name]
                self.ready = False
            elif tag == b'E':
                portal, at = _cstring(body, 0)
                if (portal not in self.portals or at + 4 != len(body)
                        or struct.unpack_from('!I', body, at)[0] != 0):
                    self.deny('Unknown or limited Execute portal')
                self._attempt(self.portals[portal], 'execute')
                self.ready = False
            elif tag == b'S':
                if body:
                    self.deny('Malformed Sync')
                self.sync_pending = True
            elif tag == b'X':
                if body or self.pending or not self.ready or self.transaction_status != 'I':
                    self.deny('Termination with unresolved work')
                self.ended = True
            else:
                self.deny('Unsupported frontend protocol')
        except (IndexError, struct.error, ProtocolDenied) as exc:
            self.failed = True
            if isinstance(exc, ProtocolDenied):
                raise
            raise ProtocolDenied('Malformed frontend protocol') from exc

    def backend(self, tag, body):
        """Account for completion without interpreting result or error contents."""
        if tag == b'C':
            if not self.pending:
                self.deny('Unmatched command completion')
            self.pending.popleft()['outcome'] = 'completed'
        elif tag == b'E':
            if self.pending:
                self.pending.popleft()['outcome'] = 'failed'
            self.failed = True
        elif tag == b'Z':
            if body not in (b'I', b'T', b'E') or self.pending:
                self.deny('Unresolved or malformed backend completion')
            self.ready = True
            self.sync_pending = False
            self.transaction_status = body.decode('ascii')
            if body == b'I':
                self.portals.clear()
            if body == b'E':
                self.failed = True
        elif tag not in (b'1', b'2', b'3', b'D', b'T', b'n', b'S', b'N'):
            self.deny('Unsupported backend protocol')

    def snapshot(self):
        return {'events': [dict(event) for event in self.events],
                'failed': self.failed, 'ended': self.ended,
                'pending': len(self.pending), 'ready': self.ready,
                'sync_pending': self.sync_pending, 'transaction_status': self.transaction_status}
