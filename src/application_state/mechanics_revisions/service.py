"""Claim-fenced durable append intents; no producer IO or mechanics ownership."""
from datetime import UTC,datetime
from uuid import UUID
from psycopg.types.json import Jsonb
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.unit_of_work import unit_of_work
from application_state.errors import ApplicationStateConflictError,ApplicationStateIntegrityError
from .types import RevisionOperation,RevisionOperationSummary


def _dsn():
    dsn=load_runtime_dsn();assert_at_head(dsn=dsn);return dsn


def _load(row):
    if row is None:return None
    try:return RevisionOperation.model_validate(row[0])
    except ValueError as exc:raise ApplicationStateIntegrityError('Stored revision operation is invalid') from exc


def _read(conn,operation_id):
    return _load(conn.execute('SELECT payload FROM mechanics_revision.operation WHERE operation_id=%s',(operation_id,)).fetchone())


def read(*,world_id,draft_id,operation_id):
    with unit_of_work(_dsn()) as conn:record=_read(conn,operation_id)
    if record and (record.world_id!=world_id or record.draft_id!=UUID(str(draft_id))):
        raise ApplicationStateConflictError('Revision operation belongs to a different work item')
    return record


_SUMMARY_SQL="(payload - ARRAY['request_body','input_digest','request_digest','updated_at','schema']) || jsonb_build_object('schema','dmb_mechanics_revision_summary_v1','change_summary',payload#>'{request_body,change_summary}')"


def _summary(row):
    if row is None:return None
    try:return RevisionOperationSummary.model_validate(row[0])
    except ValueError as exc:raise ApplicationStateIntegrityError('Stored revision summary is invalid') from exc


def list_operations(*,world_id,draft_id,limit=50,offset=0):
    # Same existing product list bound; metadata page only, no mechanics reads.
    if limit<1 or limit>100 or offset<0:raise ValueError('Invalid revision page')
    with unit_of_work(_dsn()) as conn:
        return [_summary(row) for row in conn.execute('SELECT '+_SUMMARY_SQL+' FROM mechanics_revision.operation '
            'WHERE world_id=%s AND draft_id=%s ORDER BY created_at,operation_id LIMIT %s OFFSET %s',
            (world_id,draft_id,limit,offset)).fetchall()]


def claim(record: RevisionOperation):
    if record.state!='prepared':raise ValueError('Only a new intent may be claimed')
    record=RevisionOperation.model_validate(record.model_dump(mode='json',by_alias=True))
    with unit_of_work(_dsn()) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('mechanics-revision-key:'+str(record.operation_id),))
        if conn.execute('SELECT 1 FROM mechanics_revision.cancellation WHERE operation_id=%s',(record.operation_id,)).fetchone():
            raise ApplicationStateConflictError('This Save was canceled before dispatch; create a new operation for further edits')
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('mechanics-revision:'+record.base.statblock_id,))
        old=_read(conn,record.operation_id)
        if old:
            if any(getattr(old,key)!=getattr(record,key) for key in ('world_id','draft_id','origin','origin_acceptance_operation_id','base','input_digest','request_body','request_digest','definition_digest')):
                raise ApplicationStateConflictError('Revision operation key has a different intent')
            return old,False
        if conn.execute("SELECT 1 FROM mechanics_revision.operation WHERE statblock_id=%s AND state IN ('prepared','outcome_unknown') LIMIT 1",(record.base.statblock_id,)).fetchone():
            raise ApplicationStateConflictError('An unresolved Save must be recovered before a new revision')
        conn.execute('INSERT INTO mechanics_revision.operation(operation_id,world_id,draft_id,statblock_id,state,created_at,payload) '
            'VALUES(%s,%s,%s,%s,%s,%s,%s)',(record.operation_id,record.world_id,record.draft_id,record.base.statblock_id,
            record.state,record.created_at,Jsonb(record.model_dump(mode='json',by_alias=True))))
        return record,True


def settle(record,*,state,result=None,refusal_code=None):
    with unit_of_work(_dsn()) as conn:
        row=conn.execute('SELECT payload FROM mechanics_revision.operation WHERE operation_id=%s FOR UPDATE',(record.operation_id,)).fetchone()
        current=_load(row)
        if current is None or current.request_digest!=record.request_digest or current.world_id!=record.world_id or current.draft_id!=record.draft_id:
            raise ApplicationStateConflictError('Revision operation changed')
        if current.state in {'committed','refused'}:
            if current.state!=state or current.result!=result or current.refusal_code!=refusal_code:
                raise ApplicationStateConflictError('Revision already has a different terminal outcome')
            return current
        if state not in {'outcome_unknown','committed','refused'} or (current.state=='prepared' and state!='outcome_unknown'):
            raise ValueError('Invalid revision transition')
        changed=current.model_dump(mode='json',by_alias=True)|dict(state=state,result=result.model_dump(mode='json') if result else None,
            refusal_code=refusal_code,updated_at=datetime.now(UTC).isoformat())
        updated=RevisionOperation.model_validate(changed)
        conn.execute('UPDATE mechanics_revision.operation SET state=%s,payload=%s WHERE operation_id=%s',
            (state,Jsonb(updated.model_dump(mode='json',by_alias=True)),record.operation_id))
        return updated


def find_revision(*,world_id,draft_id,revision_id):
    with unit_of_work(_dsn()) as conn:
        rows=conn.execute("SELECT payload FROM mechanics_revision.operation WHERE world_id=%s AND draft_id=%s "
            "AND state='committed' AND payload#>>'{result,revision_id}'=%s LIMIT 2",(world_id,draft_id,revision_id)).fetchall()
    if len(rows)>1:raise ApplicationStateIntegrityError('Saved revision has ambiguous provenance')
    return _load(rows[0]) if rows else None


def unresolved(*,world_id,draft_id):
    with unit_of_work(_dsn()) as conn:
        return _summary(conn.execute("SELECT "+_SUMMARY_SQL+" FROM mechanics_revision.operation WHERE world_id=%s AND draft_id=%s "
            "AND state IN ('prepared','outcome_unknown') LIMIT 1",(world_id,draft_id)).fetchone())



def cancel_if_absent(*,world_id,draft_id,operation_id):
    """A missing read alone cannot fence a still-running preflight/claim."""
    with unit_of_work(_dsn()) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('mechanics-revision-key:'+str(operation_id),))
        record=_read(conn,operation_id)
        if record:
            if record.world_id!=world_id or record.draft_id!=UUID(str(draft_id)):
                raise ApplicationStateConflictError('Revision operation belongs to another work item')
            return record
        previous=conn.execute('SELECT world_id,draft_id FROM mechanics_revision.cancellation WHERE operation_id=%s',(operation_id,)).fetchone()
        if previous and previous!=(world_id,UUID(str(draft_id))):
            raise ApplicationStateConflictError('Canceled Save belongs to another work item')
        conn.execute('INSERT INTO mechanics_revision.cancellation(operation_id,world_id,draft_id) VALUES(%s,%s,%s) '
            'ON CONFLICT(operation_id) DO NOTHING',(operation_id,world_id,draft_id))
        return None
