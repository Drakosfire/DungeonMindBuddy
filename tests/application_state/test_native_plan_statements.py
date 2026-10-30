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
