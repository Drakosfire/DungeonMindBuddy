"""Actual Build service reader fence, synthetic rows only; no DB/provider access."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

import pytest
from application_state.build_proposal import service
from application_state.build_proposal.types import BuildProposalBasis, BuildProposalReservation, BuildProposalRecord
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError

ID = UUID('00000000-0000-4000-8000-000000000001')

def legacy():
    basis = BuildProposalBasis(world_id='synthetic', document_id='page', registry_revision=1,
        content_sha256='a'*64, visibility='internal', draft_sha256='b'*64,
        caret=1, draft_generation=0, selection_generation=0)
    reservation = BuildProposalReservation(idempotency_key=ID, conversation_id=ID,
        expected_pointer_revision=1, basis=basis, instruction='Synthetic prose request')
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return BuildProposalRecord(action_id=ID, reservation=reservation,
        request_fingerprint=reservation.fingerprint, after_turn_sequence=0, revision=1,
        state='reserved', created_at=now, updated_at=now, claim_expires_at=now).model_dump(mode='json')

class Connection:
    def __init__(self, rows):
        self.rows, self.statements = rows, []
    def execute(self, statement, parameters):
        self.statements.append(statement)
        assert statement.startswith('SELECT '), 'reader attempted a write'
        return self
    def fetchone(self):
        if self.statements[-1].startswith('SELECT 1 '):
            return (1,)
        return (self.rows[0],) if self.rows else None
    def fetchall(self):
        return [(row,) for row in self.rows]

def bind(monkeypatch, rows):
    conn = Connection(rows)
    @contextmanager
    def unit(_dsn):
        yield conn
    monkeypatch.setattr(service, 'unit_of_work', unit)
    monkeypatch.setattr(service, '_ready_dsn', lambda: 'synthetic-not-a-database')
    return conn

def test_legacy_serialization_fingerprint_and_author_selection_meaning_are_unchanged():
    raw = legacy()
    assert 'selection' not in raw['reservation']['basis']
    assert service._load((raw,)).model_dump(mode='json') == raw
    assert service._load((raw,)).reservation.fingerprint == raw['request_fingerprint']

@pytest.mark.parametrize('version', ['dmb_build_document_proposal_v2', 'dmb_build_document_proposal_v99'])
@pytest.mark.parametrize('operation', ['get', 'list', 'advance'])
def test_future_markdown_refuses_without_hiding_or_writing(monkeypatch, version, operation):
    raw = legacy(); raw['schema_version'] = version
    raw['reservation']['prose_target'] = {'opaque_future_binding': 'must remain intact'}
    before = deepcopy(raw); conn = bind(monkeypatch, [raw]); owner = service.BuildProposalService()
    with pytest.raises(ApplicationStateConflictError, match='updated reader'):
        if operation == 'list': owner.list('synthetic', ID)
        elif operation == 'get': owner.get('synthetic', ID)
        else: owner.advance('synthetic', ID, expected_revision=1, state='authorized')
    assert raw == before
    assert all(sql.startswith('SELECT ') for sql in conn.statements)

def test_legacy_rows_and_shared_image_filter_remain_unchanged(monkeypatch):
    raw = legacy(); image = {'schema_version': 'dmb_build_image_preparation_v2'}
    bind(monkeypatch, [image, raw])
    assert [x.model_dump(mode='json') for x in service.BuildProposalService().list('synthetic', ID)] == [raw]
    with pytest.raises(ApplicationStateNotFoundError): service._load((image,))

def test_mixed_history_does_not_silently_hide_future_markdown(monkeypatch):
    raw = legacy(); future = deepcopy(raw); future['schema_version'] = 'dmb_build_document_proposal_v2'
    bind(monkeypatch, [raw, {'schema_version': 'dmb_build_image_preparation_v2'}, future])
    with pytest.raises(ApplicationStateConflictError): service.BuildProposalService().list('synthetic', ID)

@pytest.mark.parametrize('field', ['prose_catalog', 'prose_target'])
def test_legacy_reservation_does_not_silently_accept_new_provenance(field):
    from pydantic import ValidationError
    raw = legacy()['reservation']
    raw[field] = {'schema': 'future-prose-provenance'}
    with pytest.raises(ValidationError):
        BuildProposalReservation.model_validate(raw)
