"""Prepare the released Apprentice Plan once inside a guest World transaction."""
from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from application_state.content import repository, service
from application_state.content.types import WorkObject

# This Plan was prepared from the published bundle with this immutable digest.
_BUNDLE_SHA256 = '9271b648306aa941ddb664e581214443cbcfb802f38d68fa2d4a35b7483a1b98'
_MARKER = 'guest_apprentice_plan_v1'


def seed_guest_apprentice_plan(conn, *, session_id: str, world_id: str) -> None:
    if (os.getenv('DMB_HOSTED_GUEST_PLAN_ENABLED') != '1'
            or os.getenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256') != _BUNDLE_SHA256):
        return
    rows = dict(conn.execute(
        'SELECT key, value FROM application_state.index_graph_bindings '
        'WHERE session_id = %s::uuid AND key IN (%s, %s)',
        (session_id, _MARKER, 'guest_document_seed'),
    ).fetchall())
    if _MARKER in rows:
        return
    try:
        source = json.loads(rows['guest_document_seed'])
    except (KeyError, ValueError, TypeError):
        return
    if not isinstance(source, dict) or source.get('bundle_sha256') != _BUNDLE_SHA256:
        return
    markdown = Path(__file__).with_name('sizzek_apprentice_plan.md').read_text(encoding='utf-8')
    now = repository.now_utc()
    plan = WorkObject(work_object_id=uuid4(), kind='plan', campaign_id=None,
                      world_id=world_id, title="Sizzek's Apprentice", target_session=None,
                      target_relpath=None, status='active', current_revision_id=None,
                      object_revision=1, created_at=now, updated_at=now)
    repository.insert_work_object(conn, plan)
    service._commit_in_connection(conn, str(plan.work_object_id), markdown, kind='plan',
                                  expected_revision=1, expected_world_id=world_id)
    conn.execute('INSERT INTO application_state.index_graph_bindings(session_id, key, value) '
                 'VALUES (%s::uuid, %s, %s)', (session_id, _MARKER, str(plan.work_object_id)))
