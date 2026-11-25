"""Prepare the released Apprentice Plan once inside a guest World transaction."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from application_state.content import repository, service
from application_state.content.types import WorkObject

# The Plan was prepared from this exact released source text.
_SOURCE_SHA256 = '4a4da5b1dbb135d256e1b680fcce2da5b2ba7f5d2e400e4cdf511ca16ff80aac'
_MARKER = 'guest_apprentice_plan_v1'


def seed_guest_apprentice_plan(conn, *, session_id: str, world_id: str) -> None:
    if os.getenv('DMB_HOSTED_GUEST_PLAN_ENABLED') != '1':
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
    bundle_digest = os.getenv('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', '')
    if not isinstance(source, dict) or source.get('bundle_sha256') != bundle_digest:
        return
    try:
        with Path(os.environ['DMB_GUEST_DOCUMENT_BUNDLE']).open('rb') as bundle_file:
            raw = bundle_file.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != bundle_digest:
            return
        bundle = json.loads(raw)
        docs = bundle['documents']
        candidates = [doc['markdown'] for doc in docs if doc.get('title') == "Sizzek's Apprentice"]
        if len(candidates) != 1 or hashlib.sha256(candidates[0].encode('utf-8')).hexdigest() != _SOURCE_SHA256:
            return
    except (KeyError, OSError, UnicodeError, ValueError, TypeError, AttributeError):
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
