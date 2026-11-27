"""Fail-closed PostgreSQL frontend policy for the benchmark gateway.

The initial policy deliberately permits only parameter-free constants and
transaction controls. It is not an allowlist for Buddy application SQL.
"""
from collections import deque
import hashlib
import struct


# Exact bytes, not normalized SQL. These operations cannot access source data.
_SAFE = {
    b'SELECT 1': 'constant',
    b'SELECT 17': 'constant',
    b'BEGIN': 'transaction',
    b'COMMIT': 'transaction',
    b'ROLLBACK': 'transaction',
}
_MAX_NAMES = 128


class ProtocolDenied(ValueError):
    """An operation cannot be forwarded under this deliberately narrow policy."""


def _cstring(body, offset):
    end = body.find(b'\0', offset)
    if end < 0 or end - offset > 128:
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

    def __init__(self, *, max_messages=2000, max_attempts=500):
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
                 'category': _SAFE[query], 'outcome': 'pending'}
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
                self._attempt(query, 'simple')
                self.ready = False
                self.sync_pending = True
            elif tag == b'P':
                name, at = _cstring(body, 0)
                query, at = _cstring(body, at)
                if at + 2 != len(body) or struct.unpack_from('!H', body, at)[0] != 0:
                    self.deny('Parameterized or malformed Parse is unsupported')
                if query not in _SAFE:
                    self.deny('Unapproved SQL')
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
                at = _formats(body, at)
                if at + 2 > len(body) or struct.unpack_from('!H', body, at)[0] != 0:
                    self.deny('Bound parameters are unsupported')
                at = _formats(body, at + 2)
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
