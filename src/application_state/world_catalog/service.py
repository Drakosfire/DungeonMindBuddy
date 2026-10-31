"""Buddy World metadata persistence. This never admits sources or publishes facts."""
from __future__ import annotations

from dataclasses import dataclass
import re

import psycopg
from psycopg.rows import dict_row
from pydantic import ValidationError

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError, ApplicationStateIntegrityError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work
from application_state.world_catalog.types import (
    REGISTRY_SCHEMA, RECORD_SCHEMA, WorldContainerRecord, WorldContainerRegistryDocument,
)

_PERMISSIONS = ('read', 'write', 'manage', 'share')


@dataclass(frozen=True)
class StoredWorld:
    record: WorldContainerRecord
    revision: int


@dataclass(frozen=True)
class WorldCatalogAdoption:
    status: str
    world_count: int
    access_grant_count: int
    native_binding_count: int


def _validated_record(record: WorldContainerRecord) -> WorldContainerRecord:
    try:
        record = WorldContainerRecord.model_validate(record.model_dump(mode='json'))
    except (ValidationError, AttributeError) as exc:
        raise ApplicationStateValidationError('invalid World metadata') from exc
    if record.schema_version != RECORD_SCHEMA or not re.fullmatch(r'[a-z][a-z0-9_-]{0,62}', record.world_id):
        raise ApplicationStateValidationError('World storage requires an exact current World identity')
    if not record.name.strip() or not record.source_root_relpath or not record.created_at:
        raise ApplicationStateValidationError('World storage requires complete metadata')
    return record


def _records(conn, *, world_id: str | None = None) -> list[StoredWorld]:
    where = '' if world_id is None else ' WHERE world_id=%s'
    params = () if world_id is None else (world_id,)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT * FROM workspace.managed_world' + where + ' ORDER BY world_id', params)
        rows = cur.fetchall()
        cur.execute('SELECT * FROM workspace.world_native_binding' + where, params)
        bindings = {row['world_id']: row for row in cur.fetchall()}
        cur.execute('SELECT * FROM workspace.world_access_grant' + where + ' ORDER BY world_id,ordinal', params)
        grants = {}
        for row in cur.fetchall():
            grants.setdefault(row['world_id'], []).append({
                'subject': row['subject'], 'granted_by_subject': row['granted_by_subject'],
                'permissions': [p for p in _PERMISSIONS if row['can_' + p]],
            })
    result = []
    try:
        for row in rows:
            data = dict(row)
            revision = data.pop('revision')
            binding = bindings.get(row['world_id'])
            if binding is not None:
                binding = dict(binding)
                binding.pop('world_id')
                if binding['status'] == 'provisioning':
                    for key in ('validated_at', 'validated_head_revision_id', 'initialization_revision_id'):
                        if binding.pop(key) is not None:
                            raise ValueError('provisioning descriptor has published metadata')
                    binding['schema_version'] = 'dmb_managed_world_native_graph_provisioning_v1'
                data['native_graph_binding'] = binding
            data['access_grants'] = grants.get(row['world_id'], [])
            result.append(StoredWorld(_validated_record(WorldContainerRecord.model_validate(data)), revision))
    except (ValueError, ApplicationStateValidationError) as exc:
        raise ApplicationStateIntegrityError('stored World metadata is invalid') from exc
    return result


def list_worlds() -> list[StoredWorld]:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        return _records(conn)


def get_world(world_id: str) -> StoredWorld | None:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        rows = _records(conn, world_id=world_id)
        return rows[0] if rows else None


def _write(conn, record: WorldContainerRecord, *, revision: int) -> None:
    written = conn.execute('''INSERT INTO workspace.managed_world
        (world_id,name,source_root_relpath,created_at,owner_subject,revision)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT(world_id) DO UPDATE SET name=EXCLUDED.name,
            source_root_relpath=EXCLUDED.source_root_relpath,created_at=EXCLUDED.created_at,
            owner_subject=EXCLUDED.owner_subject,revision=EXCLUDED.revision
        WHERE workspace.managed_world.revision=%s AND %s > 0
        RETURNING world_id''',
        (record.world_id, record.name, record.source_root_relpath, record.created_at, record.owner_subject,
         revision, revision - 1, revision - 1)).fetchone()
    if written is None:
        raise ApplicationStateConflictError('World metadata changed; reload before writing')
    conn.execute('DELETE FROM workspace.world_native_binding WHERE world_id=%s', (record.world_id,))
    binding = record.native_graph_binding
    if binding is not None:
        conn.execute('''INSERT INTO workspace.world_native_binding
            (world_id,native_world_id,status,binding_version,validated_at,validated_head_revision_id,
             provisioning_id,initialization_revision_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
            (record.world_id, binding.native_world_id, binding.status, binding.binding_version,
             getattr(binding, 'validated_at', None), getattr(binding, 'validated_head_revision_id', None),
             binding.provisioning_id, getattr(binding, 'initialization_revision_id', None)))
    conn.execute('DELETE FROM workspace.world_access_grant WHERE world_id=%s', (record.world_id,))
    for ordinal, grant in enumerate(record.access_grants):
        conn.execute('''INSERT INTO workspace.world_access_grant
            (world_id,subject,granted_by_subject,ordinal,can_read,can_write,can_manage,can_share)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
            (record.world_id, grant.subject, grant.granted_by_subject, ordinal,
             *(permission in grant.permissions for permission in _PERMISSIONS)))


def save_world(record: WorldContainerRecord, *, expected_revision: int) -> StoredWorld:
    """One exact metadata CAS; native descriptors are retained data, not verification."""
    record = _validated_record(record)
    if type(expected_revision) is not int or expected_revision < 0:
        raise ApplicationStateValidationError('an exact nonnegative World revision is required')
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    try:
        with unit_of_work(dsn) as conn:
            row = conn.execute('SELECT revision FROM workspace.managed_world WHERE world_id=%s FOR UPDATE',
                               (record.world_id,)).fetchone()
            current = row[0] if row else 0
            if current != expected_revision:
                raise ApplicationStateConflictError('World metadata changed; reload before writing')
            _write(conn, record, revision=current + 1)
    except psycopg.IntegrityError as exc:
        raise ApplicationStateConflictError('World identity or native claim conflicts with stored metadata') from exc
    return StoredWorld(record, current + 1)


def adopt_world_catalog(document: WorldContainerRegistryDocument, *, dry_run: bool = True) -> WorldCatalogAdoption:
    """Explicit all-or-nothing import into an empty catalog, or exact no-op replay.

    Files are caller-supplied migration input only. No live reader calls this;
    no source admission, native validation/publication or schema upgrade occurs.
    """
    try:
        document = WorldContainerRegistryDocument.model_validate(document.model_dump(mode='json'))
    except (ValidationError, AttributeError) as exc:
        raise ApplicationStateValidationError('invalid World catalog') from exc
    if document.schema_version != REGISTRY_SCHEMA:
        raise ApplicationStateValidationError('World adoption requires the current explicit catalog format')
    records = sorted((_validated_record(record) for record in document.records), key=lambda record: record.world_id)
    if len({record.world_id for record in records}) != len(records):
        raise ApplicationStateValidationError('World adoption cannot merge duplicate identities')
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    try:
        with unit_of_work(dsn) as conn:
            # Serialize adoption with every normal metadata writer. The caller
            # must decide conflicts; this never merges catalogs or repairs rows.
            conn.execute('LOCK TABLE workspace.managed_world IN EXCLUSIVE MODE')
            existing = _records(conn)
            if existing:
                if [row.record for row in existing] != records:
                    raise ApplicationStateConflictError('World catalog is populated with different metadata')
                status = 'already_present'
            elif dry_run:
                status = 'would_adopt'
            else:
                for record in records:
                    _write(conn, record, revision=1)
                status = 'adopted'
    except psycopg.IntegrityError as exc:
        raise ApplicationStateConflictError('World catalog identities conflict; nothing was adopted') from exc
    return WorldCatalogAdoption(status, len(records), sum(len(row.access_grants) for row in records),
                                sum(row.native_graph_binding is not None for row in records))
