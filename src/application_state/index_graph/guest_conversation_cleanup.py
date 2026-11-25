"""Delete retained conversation records only for one expired guest session.

Unexpected dependent records make the transaction fail rather than widening
the deletion. The caller owns scheduling and may retry after a failed attempt.
"""
from uuid import UUID
import logging
from threading import Lock

from application_state.errors import ApplicationStateConflictError
from application_state.unit_of_work import unit_of_work

_sweep_lock = Lock()
_cursor = None


def cleanup_expired_guest_conversations(*, limit: int = 8) -> None:
    """Opportunistically retry a bounded batch after guest session activity."""
    global _cursor
    if not 1 <= limit <= 32:
        raise ValueError('Invalid guest cleanup batch size')
    if not _sweep_lock.acquire(blocking=False):
        return
    try:
        with unit_of_work() as conn:
            conn.execute("SET LOCAL statement_timeout = '5s'")
            query = ("SELECT s.expires_at, s.session_id::text FROM application_state.index_graph_sessions s "
                     "JOIN agent.world_state a ON a.world_id='guest-' || replace(s.session_id::text, '-', '') "
                     "WHERE s.expires_at <= clock_timestamp() ")
            if _cursor is None:
                rows = conn.execute(query + 'ORDER BY s.expires_at, s.session_id LIMIT %s', (limit,)).fetchall()
            else:
                rows = conn.execute(query + 'AND (s.expires_at, s.session_id) > (%s, %s::uuid) '
                                    'ORDER BY s.expires_at, s.session_id LIMIT %s', (*_cursor, limit)).fetchall()
                if not rows:
                    rows = conn.execute(query + 'ORDER BY s.expires_at, s.session_id LIMIT %s', (limit,)).fetchall()
            _cursor = rows[-1] if rows else None
        for _, session_id in rows:
            try:
                cleanup_expired_guest_conversation(session_id)
            except Exception:
                logging.getLogger(__name__).exception('Guest conversation cleanup failed; it will be retried')
    finally:
        _sweep_lock.release()


def cleanup_expired_guest_conversation(session_id: str) -> None:
    try:
        canonical = str(UUID(session_id))
    except (ValueError, TypeError, AttributeError):
        raise ApplicationStateConflictError('Invalid guest session') from None
    if canonical != session_id:
        raise ApplicationStateConflictError('Invalid guest session')
    world_id = f'guest-{UUID(canonical).hex}'
    with unit_of_work() as conn:
        conn.execute("SET LOCAL lock_timeout = '250ms'")
        conn.execute("SET LOCAL statement_timeout = '5s'")
        session = conn.execute(
            'SELECT expires_at <= clock_timestamp() FROM application_state.index_graph_sessions '
            'WHERE session_id=%s::uuid FOR UPDATE SKIP LOCKED', (canonical,),
        ).fetchone()
        if session is None or not session[0]:
            raise ApplicationStateConflictError('Guest session is not expired')
        owner = conn.execute('SELECT owner_subject FROM workspace.managed_world WHERE world_id=%s', (world_id,)).fetchone()
        if owner is None or owner[0] != f'guest-session:{canonical}':
            raise ApplicationStateConflictError('Guest World ownership differs from its session')
        turns = 'SELECT turn_id FROM agent.turn WHERE world_id=%s'
        for table in ('turn_context_trace', 'turn_rules_execution', 'turn_reviewed_action'):
            conn.execute(f'DELETE FROM agent.{table} WHERE turn_id IN ({turns})', (world_id,))
        for table in ('command_resolution', 'import_receipt', 'command_receipt', 'composer_draft'):
            conn.execute(f'DELETE FROM agent.{table} WHERE world_id=%s', (world_id,))
        conn.execute('DELETE FROM agent.build_proposal_review WHERE world_id=%s', (world_id,))
        conn.execute('DELETE FROM agent.build_proposal WHERE world_id=%s', (world_id,))
        conn.execute('DELETE FROM agent.world_state WHERE world_id=%s', (world_id,))
        conn.execute('DELETE FROM agent.turn WHERE world_id=%s', (world_id,))
        conn.execute('DELETE FROM agent.conversation WHERE world_id=%s', (world_id,))
