"""Cross-lineage owner witness, not an ordinary-turn or live-provider benchmark."""
import asyncio
from hashlib import sha256
import json
from importlib.util import find_spec

import pytest


@pytest.mark.parametrize("choice", ["read", "skip"])
def test_pending_page_probe_witnesses_admitted_app_acquisition(monkeypatch, choice):
    """Pending App navigation imports the two watched owners after the hook is installed."""
    if find_spec("apps.live_control_server.services.build_pending_app_pages") is None:
        pytest.skip("Pending Build is absent from this source lineage")
    from tests.test_build_source_free_protocol import pending_app_runtime_case
    from apps.live_control_server.services import build_jev_dispatch, build_related_pages
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_related_pages import RelatedPageRead
    from evals.negative_retrieval.related_page_probe import observe_related_page_owners
    import httpx2

    # The serving test helper's synthetic policy predates the namespaced model.
    # This affects only the fake SDK transport and does not establish product routing.
    monkeypatch.setattr(build_jev_dispatch, "MODEL", "jev-1.14.0")
    monkeypatch.setenv("TYPESAFE_JEV_API_KEY", "synthetic-only")

    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            return httpx2.Response(200, request=request, json={"model": body["model"],
                "usage": {"input_tokens": 23, "output_tokens": 4}, "answers": {
                    key: {"type": "choice", "choice": choice, "confidence": 1,
                          "probabilities": {"read": float(choice == "read"),
                                            "skip": float(choice == "skip")}}
                    for key in body["questions"]}})

    with pending_app_runtime_case(monkeypatch) as (state, adapter):
        page = state.turn.graph_context_execution.events[-1].pages[0]
        execution = state.turn.graph_context_execution
        execution = type(execution).model_validate_json(execution.model_copy(update={
            "events": execution.events[:-1]}).model_dump_json(by_alias=True))
        state.turn = t.Turn.model_validate(state.turn.model_copy(update={"graph_context_execution": execution}))
        adapter.fence.renewer.update_turn(state.turn)
        monkeypatch.setattr(build_related_pages, "discover", lambda request: [page.model_dump(mode="json")])

        def materialize(pointer):
            assert pointer == page
            text = "Synthetic saved page."
            return dict(pointer.model_dump(mode="json"), content_sha256=sha256(text.encode()).hexdigest(), markdown=text)

        monkeypatch.setattr(build_related_pages, "materialize", materialize)
        harness = BuildJevHarness(decision_transport=Transport())
        harness.adapter, harness.calls, harness.timings, harness._inflight = adapter, [], [], {}
        with observe_related_page_owners() as records:
            asyncio.run(acquire_pending_app_pages(adapter, harness))
        assert sum(row["owner"] == "related_catalog_discovery" for row in records) == 1
        assert sum(row["owner"] == "related_page_materialization" for row in records) == (choice == "read")
        assert len([event for event in state.turn.graph_context_execution.events
                    if type(event) is RelatedPageRead]) == (choice == "read")
        assert all(row["state"] == "returned" for row in records)
