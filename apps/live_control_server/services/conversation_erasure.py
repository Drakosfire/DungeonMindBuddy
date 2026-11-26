"""Drain file erasures recorded by the conversation database transaction."""

from __future__ import annotations

import asyncio
import logging
import os
import stat
from contextlib import ExitStack
from uuid import UUID

import psycopg

from application_state.agent_conversation.service import _ready_dsn
from application_state.errors import ApplicationStateError, ApplicationStateUnavailableError
from application_state.unit_of_work import unit_of_work
from apps.live_control_server.config import ArtifactDataRootError, artifact_data_root

_EVIDENCE_DIRECTORIES = {
    "prompt": "agent_request_evidence",
    "failure": "agent_failure_evidence",
}
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_LOG = logging.getLogger(__name__)


def _erase_file(kind: str, evidence_id: UUID) -> None:
    directory_name = _EVIDENCE_DIRECTORIES[kind]
    with ExitStack() as stack:
        directory = os.open(artifact_data_root(), _DIRECTORY_FLAGS)
        stack.callback(os.close, directory)
        for name in ("out", directory_name):
            try:
                directory = os.open(name, _DIRECTORY_FLAGS, dir_fd=directory)
            except FileNotFoundError:
                return
            stack.callback(os.close, directory)
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise PermissionError("Evidence directory is not private")
        try:
            os.unlink(f"{evidence_id}.json", dir_fd=directory)
        except FileNotFoundError:
            pass
        os.fsync(directory)


def _drain(conversation_id: UUID | None = None) -> bool:
    with unit_of_work(_ready_dsn()) as conn:
        rows = conn.execute(
            "SELECT * FROM agent.lock_conversation_erasure_files(%s)", (conversation_id,),
        ).fetchall()
        for target, kind, evidence_id in rows:
            try:
                _erase_file(kind, evidence_id)
            except (OSError, ArtifactDataRootError) as exc:
                _LOG.warning("Conversation evidence cleanup deferred: %s", type(exc).__name__)
                conn.execute("""
                    UPDATE agent.conversation_erasure_file
                    SET retry_after = clock_timestamp() + interval '5 minutes'
                    WHERE conversation_id=%s AND kind=%s AND evidence_id=%s
                """, (target, kind, evidence_id))
                continue
            conn.execute("""
                DELETE FROM agent.conversation_erasure_file
                WHERE conversation_id=%s AND kind=%s AND evidence_id=%s
            """, (target, kind, evidence_id))
        if conversation_id is None:
            return not rows
        return conn.execute("""
            SELECT NOT EXISTS (SELECT 1 FROM agent.conversation_erasure_file WHERE conversation_id=%s)
        """, (conversation_id,)).fetchone()[0]


def finish_conversation_erasure(conversation_id: UUID) -> None:
    try:
        if _drain(conversation_id):
            return
    except (OSError, ArtifactDataRootError, psycopg.Error) as exc:
        _LOG.warning("Conversation evidence cleanup deferred: %s", type(exc).__name__)
        raise ApplicationStateUnavailableError("Deletion is finishing. Retry to check its result.") from exc
    raise ApplicationStateUnavailableError("Deletion is finishing. Retry to check its result.")


async def recover_conversation_erasures(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.to_thread(_drain)
        except (ApplicationStateError, OSError, ArtifactDataRootError, psycopg.Error) as exc:
            _LOG.warning("Conversation evidence cleanup deferred: %s", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=60)
        except TimeoutError:
            continue
