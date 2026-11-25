"""Seed released source pages into one isolated guest World."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from uuid import UUID, uuid4

from application_state.content import pages
from application_state.content import service as content
from application_state.errors import ApplicationStateUnavailableError

_MARKER = 'guest_document_seed'
_MAX_BUNDLE_BYTES = 16 * 1024 * 1024
_MAX_PAGES = 32
_MAX_REVISIONS = 256


def seed_guest_documents(conn, *, session_id: str, world_id: str) -> None:
    """Seed once, atomically with the caller's locked guest World binding.

    The bundle is an operator-selected immutable release artifact. Its source
    graph binding must equal the session's persisted snapshot, not the current
    process environment, because a session can outlive a release change.
    """
    path = os.environ.get('DMB_GUEST_DOCUMENT_BUNDLE', '').strip()
    if not path:
        return
    seeded = conn.execute(
        'SELECT value FROM application_state.index_graph_bindings WHERE session_id = %s::uuid AND key = %s',
        (session_id, _MARKER),
    ).fetchone()
    if seeded is not None:
        # Earlier releases seeded source pages without a document class. Repair
        # only those exact pages in this World, leaving all content and any class
        # the guest has since chosen untouched.
        try:
            receipt = json.loads(seeded[0])
            entries = receipt['entries']
            if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_PAGES:
                raise ValueError('invalid seed entries')
            ids = [UUID(entry['document_id']) for entry in entries]
            if len(set(ids)) != len(ids):
                raise ValueError('duplicate seed entries')
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ApplicationStateUnavailableError('Guest document seed receipt is invalid') from exc
        conn.execute(
            "UPDATE content.page_metadata m SET document_class = 'lore' "
            "FROM content.work_object w WHERE m.work_object_id = w.work_object_id "
            "AND w.world_id = %s AND w.kind = 'worldbuilding_source' "
            "AND w.work_object_id = ANY(%s::uuid[]) AND m.document_class IS NULL",
            (world_id, ids),
        )
        return
    snapshot = conn.execute(
        "SELECT value FROM application_state.index_graph_bindings WHERE session_id = %s::uuid AND key = 'source_snapshot'",
        (session_id,),
    ).fetchone()
    try:
        expected_digest = os.environ.get('DMB_GUEST_DOCUMENT_BUNDLE_SHA256', '').strip()
        if not re.fullmatch(r'[0-9a-f]{64}', expected_digest):
            raise ValueError('invalid bundle digest')
        with Path(path).open('rb') as bundle_file:
            raw = bundle_file.read(_MAX_BUNDLE_BYTES + 1)
        if not raw or len(raw) > _MAX_BUNDLE_BYTES:
            raise ValueError('invalid bundle size')
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            raise ValueError('bundle digest mismatch')
        bundle = json.loads(raw)
        saved = json.loads(snapshot[0]) if snapshot else None
        if (not isinstance(bundle, dict) or bundle.get('version') != 1
                or not isinstance(saved, dict)
                or not isinstance(saved.get('space_id'), str) or not saved['space_id']
                or not isinstance(saved.get('revision_id'), str) or not saved['revision_id']
                or bundle.get('graph_space') != saved.get('space_id')
                or bundle.get('graph_revision') != saved.get('revision_id')):
            raise ValueError('bundle does not match guest graph')
        documents = bundle.get('documents')
        if not isinstance(documents, list) or not 1 <= len(documents) <= _MAX_PAGES:
            raise ValueError('invalid document count')
        for doc in documents:
            if (not isinstance(doc, dict) or set(doc) != {'title', 'markdown'}
                    or not isinstance(doc['title'], str) or not doc['title'].strip()
                    or not isinstance(doc['markdown'], str)):
                raise ValueError('invalid document')
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ApplicationStateUnavailableError('Guest source documents are unavailable') from exc

    existing_count = conn.execute(
        "SELECT count(*) FROM content.work_object WHERE world_id = %s AND kind = 'worldbuilding_source'",
        (world_id,),
    ).fetchone()[0]
    if existing_count + len(documents) > _MAX_PAGES:
        raise ApplicationStateUnavailableError('Guest source documents exceed the World capacity')
    revisions, saved_bytes = conn.execute(
        "SELECT count(*), coalesce(sum(octet_length(r.markdown)), 0) "
        "FROM content.work_revision r JOIN content.work_object o ON o.work_object_id = r.work_object_id "
        "WHERE o.world_id = %s AND o.kind = 'worldbuilding_source'", (world_id,),
    ).fetchone()
    added_bytes = sum(len(doc['markdown'].encode('utf-8')) for doc in documents)
    if revisions + len(documents) > _MAX_REVISIONS or saved_bytes + added_bytes > _MAX_BUNDLE_BYTES:
        raise ApplicationStateUnavailableError('Guest source documents exceed the World capacity')
    entries = []
    for ordinal, doc in enumerate(documents):
        ident = uuid4()
        pages._insert_page(conn, ident, world_id, doc['title'], world_id, pages.PageMetadata(document_class='lore'))
        content._commit_in_connection(conn, str(ident), doc['markdown'],
                                      kind='worldbuilding_source', expected_revision=1)
        entries.append({'ordinal': ordinal, 'document_id': str(ident)})
    receipt = json.dumps({'version': 1, 'bundle_sha256': expected_digest, 'entries': entries},
                         sort_keys=True, separators=(',', ':'))
    conn.execute(
        'INSERT INTO application_state.index_graph_bindings(session_id, key, value) VALUES (%s::uuid, %s, %s)',
        (session_id, _MARKER, receipt),
    )
