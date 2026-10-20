"""Authenticated historical Rules inspect; exact persisted evidence, not catalog lookup."""
import asyncio
import json
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from application_state.agent_conversation import AgentConversationService
from application_state.errors import ApplicationStateNotFoundError
from apps.live_control_server.routes import agent
from tests.test_rules_build_parent import build_case, run_parent


@pytest.fixture
def api(monkeypatch):
    token = "rules-historical-test-token-" * 2
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    state = SimpleNamespace(calls=[], admissions=[], service=None, admit=True)

    def admit(value):
        state.admissions.append(value)
        if not state.admit:
            raise HTTPException(status_code=404, detail={"code": "world_owner_unavailable"})
        return value

    def service(request):
        assert state.admissions
        state.calls.append(True)
        return state.service

    monkeypatch.setattr(agent, "_verified_world_id", admit)
    monkeypatch.setattr(agent, "_conversation_service", service)
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")

    async def get(*, world="elderwyld", turn=None, support=None, query=None, authorized=True):
        path = f"/api/live/agent/worlds/{world}/conversation/turns/{turn or uuid4()}/rules-passages/{support or uuid4()}"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)), base_url="http://test") as client:
            return await client.get(path + "?" + (query or ""), headers={"Authorization": f"Bearer {token}"} if authorized else {})

    async def history(query=""):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)), base_url="http://test") as client:
            return await client.get("/api/live/agent/worlds/elderwyld/conversation?" + query,
                headers={"Authorization": f"Bearer {token}"})

    state.history = history
    state.get = get
    return state


def test_live_parent_capsule_survives_current_catalog_failure_and_rejects_foreign_selectors(
    application_state_dsn, build_case, tmp_path, monkeypatch, api,
):
    completed, _, _, _, _ = run_parent(build_case, tmp_path, monkeypatch)
    envelope = completed.envelope
    cited = completed.accepted_binding.support_table[0]
    api.service = AgentConversationService()
    from apps.live_control_server.services import rules_lookup
    def unavailable(*args, **kwargs):
        pytest.fail("Historical inspect must not reopen the current catalog")
    monkeypatch.setattr(rules_lookup, "query_rules", unavailable)
    monkeypatch.setattr(rules_lookup, "admitted_bundle", unavailable)
    selectors = dict(conversation_id=str(envelope.conversation_id), attempt=envelope.attempt,
        support_sha256=cited.support_sha256)
    def read(**updates):
        args = dict(world=envelope.world_id, turn=str(envelope.turn_id), support=str(cited.support_id),
            query=urlencode(selectors))
        args.update(updates)
        return asyncio.run(api.get(**args))
    response = read()
    assert response.status_code == 200, response.text
    assert response.json()["schema"] == "dmb_rules_historical_passage_v1"
    assert response.json()["support_sha256"] == cited.support_sha256
    assert response.json()["support"]["support_id"] == str(cited.support_id)
    assert response.headers["cache-control"] == "no-store" and len(response.content) <= 32768
    for change in ({"conversation_id": str(uuid4())}, {"attempt": envelope.attempt + 1}, {"support_sha256": "0" * 64}):
        denied = read(query=urlencode({**selectors, **change}))
        assert denied.status_code == 404 and "support" not in denied.json()
    assert read(world="foreign-world").status_code == 404
    assert read(turn=str(uuid4())).status_code == 404
    assert read(support=str(uuid4())).status_code == 404
    # The transport revalidates an injected service's return identity too.
    from application_state.agent_conversation.rules_authority_passages import RulesHistoricalPassageV1
    passage = RulesHistoricalPassageV1.model_validate_json(response.content)
    api.service = SimpleNamespace(inspect_rules_passage=lambda _: passage.model_copy(update={"world_id": "foreign-world"}))
    assert read().status_code == 409


@pytest.mark.parametrize("kind", ["auth", "world", "duplicate", "unknown", "missing", "attempt", "digest", "uuid", "turn", "support"])
def test_admission_and_canonical_selectors_precede_private_storage(api, kind):
    selectors = dict(conversation_id=str(uuid4()), attempt="1", support_sha256="a" * 64)
    if kind == "unknown": selectors["extra"] = "x"
    if kind == "missing": selectors.pop("support_sha256")
    if kind == "attempt": selectors["attempt"] = "01"
    if kind == "digest": selectors["support_sha256"] = "A" * 64
    if kind == "uuid": selectors["conversation_id"] = selectors["conversation_id"].replace("-", "")
    if kind == "world": api.admit = False
    response = asyncio.run(api.get(authorized=kind != "auth",
        turn="not-a-uuid" if kind == "turn" else None,
        support="not-a-uuid" if kind == "support" else None,
        query=urlencode(selectors) + ("&attempt=1" if kind == "duplicate" else "")))
    assert response.status_code == (401 if kind == "auth" else 404 if kind == "world" else 422)
    assert not api.calls
    if kind == "auth": assert not api.admissions


def test_private_store_error_is_sanitized(api):
    def missing(_):
        raise ApplicationStateNotFoundError("private foreign source details")
    api.service = SimpleNamespace(inspect_rules_passage=missing)
    response = asyncio.run(api.get(query=urlencode(dict(conversation_id=str(uuid4()), attempt="1", support_sha256="a" * 64))))
    assert response.status_code == 404 and "private" not in response.text


@pytest.mark.parametrize("base", [False, True])
def test_mixed_history_round_trip_and_pagination_preserve_full_text_and_sealed_attribution(
    application_state_dsn, build_case, tmp_path, monkeypatch, api, base,
):
    from apps.live_control_server.models.agent_turn import AgentConversationHistoryResponseV4
    from application_state.agent_conversation.rules_authority_types import canonical_sha256

    first, _, _, _, _ = run_parent(build_case, tmp_path, monkeypatch, base=base)
    source, request, bootstrap = build_case
    second, _, _, _, _ = run_parent(
        (source, request.model_copy(update={"turn_id": str(uuid4())}), bootstrap),
        tmp_path, monkeypatch, query=False, question="Discuss this further.",
    )
    api.service = AgentConversationService()
    for correlation in ("false", "true"):
        response = asyncio.run(api.history("include_turn_correlation=" + correlation))
        assert response.status_code == 200, response.text
        page = AgentConversationHistoryResponseV4.model_validate_json(response.content)
        mixed, ordinary = page.turns
        assert mixed.turn_id == first.envelope.turn_id
        assert ordinary.turn_id == second.turn_id
        assert mixed.assistant_text == first.assistant_text
        assert mixed.idempotency_key == first.envelope.idempotency_key
        assert mixed.rules_context.accepted_binding == first.accepted_binding
        assert (mixed.rules_context.base_context is not None) == base
        serialized = mixed.rules_context.model_dump_json(by_alias=True)
        assert "excerpt_text" not in serialized and "packet_json" not in serialized
        assert "support_capsules" not in serialized
        if base:
            assert mixed.rules_context.base_context.completion == first.base_projection.turn.completion
        # Neither the row nor parent page may silently accept mismatched ownership/text.
        raw = response.json()
        raw["turns"][0]["assistant_text"] += " changed"
        with pytest.raises(ValueError):
            AgentConversationHistoryResponseV4.model_validate_json(json.dumps(raw))
        raw = response.json()
        raw["conversation_id"] = raw["active_conversation_id"] = str(uuid4())
        with pytest.raises(ValueError):
            AgentConversationHistoryResponseV4.model_validate_json(json.dumps(raw))
        raw = response.json()
        context = raw["turns"][0]["rules_context"]
        context["accepted_binding"]["graph_used"] = True
        context["accepted_binding_sha256"] = canonical_sha256(context["accepted_binding"])
        with pytest.raises(ValueError):
            AgentConversationHistoryResponseV4.model_validate_json(json.dumps(raw))
    newest = asyncio.run(api.history("limit=1&include_turn_correlation=true"))
    assert newest.status_code == 200 and newest.json()["schema"] == "dmb_agent_conversation_history_v3"
    assert newest.json()["next_before_sequence"] == second.sequence
    older = asyncio.run(api.history("limit=1&before_sequence=" + str(second.sequence)))
    assert older.status_code == 200, older.text
    assert older.json()["schema"] == "dmb_agent_conversation_history_v4"
    assert older.json()["next_before_sequence"] == first.envelope.sequence
    assert older.json()["turns"][0]["assistant_text"] == first.assistant_text
