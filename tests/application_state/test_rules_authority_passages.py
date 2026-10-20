"""One accepted historical source capsule through real PostgreSQL projection."""

from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_passages import (
    RulesHistoricalPassageRequestV1,
    read_historical_rules_passage,
)
from application_state.agent_conversation.rules_authority_types import (
    canonical_bytes,
    canonical_sha256,
)
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
)
from tests.application_state.test_rules_authority_completion import ready_rules


def accepted(dsn):
    turn, result = ready_rules(dsn)
    completed = AgentConversationService().complete_mixed_turn(result)
    ref = completed.accepted_binding.support_table[0]
    request = RulesHistoricalPassageRequestV1(
        world_id=turn.world_id,
        conversation_id=turn.conversation_id,
        turn_id=turn.turn_id,
        attempt=turn.attempt,
        support_id=ref.support_id,
        support_sha256=ref.support_sha256,
    )
    return turn, completed, request


def test_one_cited_capsule_is_selected_once_without_catalog_or_full_ledger(
    application_state_dsn,
):
    turn, completed, request = accepted(application_state_dsn)
    queries = []

    class CountCursor(psycopg.Cursor):
        def execute(self, query, params=None, **kwargs):
            queries.append(str(query))
            return super().execute(query, params, **kwargs)

    with psycopg.connect(application_state_dsn, cursor_factory=CountCursor) as conn:
        passage = read_historical_rules_passage(conn, request)
    assert len(queries) == 1 and "r.payload->'supports'->" in queries[0]
    assert (
        "THEN r.payload ELSE" not in queries[0] and "assistant_text" not in queries[0]
    )
    assert "40960" in queries[0]
    assert passage.support.excerpt_text == completed.assistant_text
    assert (
        passage.support_sha256
        == canonical_sha256(passage.support)
        == request.support_sha256
    )
    assert len(canonical_bytes(passage)) <= 32768
    assert AgentConversationService().inspect_rules_passage(request) == passage


@pytest.mark.parametrize(
    "field",
    [
        "world_id",
        "conversation_id",
        "turn_id",
        "attempt",
        "support_id",
        "support_sha256",
    ],
)
def test_unknown_cross_owner_attempt_or_uncited_digest_is_not_resolved(
    application_state_dsn, field
):
    _, _, request = accepted(application_state_dsn)
    fields = request.model_dump(mode="python", by_alias=True)
    fields[field] = {
        "world_id": "another-world",
        "attempt": request.attempt + 1,
        "support_sha256": "f" * 64,
    }.get(field, uuid4())
    with pytest.raises(ApplicationStateNotFoundError):
        AgentConversationService().inspect_rules_passage(
            RulesHistoricalPassageRequestV1(**fields)
        )


@pytest.mark.parametrize(
    "corruption", ["summary_seal", "source_text", "source_oversized", "source_missing"]
)
def test_corrupt_or_oversized_source_is_never_repaired_from_current_catalog(
    application_state_dsn, corruption
):
    turn, _, request = accepted(application_state_dsn)
    with psycopg.connect(application_state_dsn) as conn:
        if corruption == "summary_seal":
            conn.execute(
                "UPDATE agent.turn_rules_execution SET accepted_binding_sha256=%s WHERE turn_id=%s",
                ("f" * 64, turn.turn_id),
            )
        else:
            payload = conn.execute(
                "SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s",
                (turn.turn_id,),
            ).fetchone()[0]
            key = str(request.support_id)
            if corruption == "source_missing":
                del payload["supports"][key]
            elif corruption == "source_oversized":
                payload["supports"][key]["oversized"] = "x" * 50000
            else:
                payload["supports"][key]["support"]["excerpt_text"] = (
                    "Changed source text."
                )
            conn.execute(
                "UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s",
                (Jsonb(payload), turn.turn_id),
            )
    with pytest.raises(ApplicationStateIntegrityError):
        AgentConversationService().inspect_rules_passage(request)


def test_uncited_body_in_storage_cannot_mint_a_historical_citation(
    application_state_dsn,
):
    turn, _, request = accepted(application_state_dsn)
    other = uuid4()
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute(
            "SELECT payload FROM agent.turn_rules_execution WHERE turn_id=%s",
            (turn.turn_id,),
        ).fetchone()[0]
        # Deliberate fixture storage damage; the accepted source map remains the
        # authority and this unclaimed body must never be selected by the reader.
        payload["supports"][str(other)] = payload["supports"][str(request.support_id)]
        conn.execute(
            "UPDATE agent.turn_rules_execution SET payload=%s WHERE turn_id=%s",
            (Jsonb(payload), turn.turn_id),
        )
    fields = request.model_dump(mode="python", by_alias=True)
    fields["support_id"] = other
    with pytest.raises(ApplicationStateNotFoundError):
        AgentConversationService().inspect_rules_passage(
            RulesHistoricalPassageRequestV1(**fields)
        )
