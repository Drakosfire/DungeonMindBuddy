"""Native writer capture and cross-family exposure refusal at their owning checks."""
from threading import RLock
from types import SimpleNamespace
from uuid import uuid4
import pytest
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector


@pytest.mark.parametrize('case', ['missing_response', 'foreign_response', 'foreign_producer'])
def test_native_writer_draft_requires_exact_acknowledged_producer(case):
    attempt = uuid4()
    authorization = SimpleNamespace(kind='plan_native_writer_authorized_v1', provider_attempt_id=attempt)
    events = [authorization]
    if case != 'missing_response':
        events.append(SimpleNamespace(kind='provider_outcome', outcome='response_received',
            provider_attempt_id=uuid4() if case == 'foreign_response' else attempt))
    collector = ContextTraceCollector.__new__(ContextTraceCollector)
    collector.fence = SimpleNamespace(renewer=SimpleNamespace(_lock=RLock(),
        _turn=SimpleNamespace(graph_context_execution=SimpleNamespace(events=events))))
    with pytest.raises(ApplicationStateValidationError, match='producing provider response'):
        collector.answer_draft('Unvalidated synthetic output',
            producing_provider_attempt_id=uuid4() if case == 'foreign_producer' else attempt)


@pytest.mark.parametrize('body_end,clause_start,explicit,expected', [
    (5, 5, False, 'explicit full-document'),
    (6, 4, False, None),
    (10, 5, True, None),
])
def test_body_and_statement_exposure_share_one_original_byte_union(body_end, clause_start, explicit, expected):
    from application_state.agent_conversation.native_corpus import (
        validate_combined_exposure, NativeBodySearchObservedV1)
    from application_state.agent_conversation.native_plan_statements import NativePlanStatementReadObservedV1
    catalog = SimpleNamespace(catalog_sha256='catalog', body_bytes=10, source=SimpleNamespace(
        artifact=SimpleNamespace(source_artifact_id='artifact'),
        revision=SimpleNamespace(source_revision_id='revision', content_sha256='digest')))
    search = NativeBodySearchObservedV1.model_construct(catalogs=(catalog,))
    support = SimpleNamespace(source_artifact_id='artifact', source_revision_id='revision',
        source_body_sha256='digest', clause_start_byte=clause_start,
        clause_end_byte=10 if clause_start == 5 else 8)
    statement = NativePlanStatementReadObservedV1.model_construct(
        reads=(SimpleNamespace(support=support, source_body_bytes=10),))
    body = SimpleNamespace(excerpt=SimpleNamespace(catalog_sha256='catalog',
        section=SimpleNamespace(byte_start=0, byte_end=body_end),
        selector_policy='native_full_document_v1' if explicit else 'native_section_v1'))
    execution = SimpleNamespace(events=(search, statement))
    if expected:
        with pytest.raises(ValueError, match=expected):
            validate_combined_exposure(execution, (body,))
    else:
        validate_combined_exposure(execution, (body,))
