"""Real APP metadata binding; no retained DBs or model provider IO."""

from uuid import uuid4

import pytest
from application_state.agent_conversation.context_trace import TracePromptReference
from application_state.errors import ApplicationStateValidationError
from tests.application_state.test_agent_conversation_context_trace_postgres import (
    _setup_turn,
)


def test_app_rejects_prompt_handle_without_matching_durable_authorization(
    application_state_dsn,
):
    service, _, binding, _ = _setup_turn()
    observation = TracePromptReference(
        sequence=0,
        elapsed_ms=1,
        evidence_id=uuid4(),
        provider_attempt_id=uuid4(),
        provider="openai",
        model="synthetic",
        api_mode="responses",
        serializer_version="serializer",
        payload_sha256="a" * 64,
        payload_utf8_bytes=2,
    )
    with pytest.raises(
        ApplicationStateValidationError, match="durable provider authorization"
    ):
        service.append_context_trace(**binding, observation=observation)
    assert (
        service.list_context_trace_attempts(
            world_id=binding["world_id"], turn_id=binding["turn_id"]
        )[0].observations
        == []
    )
