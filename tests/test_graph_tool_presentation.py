"""Exact parent presentations authorize only currently delivered complete records."""

import json
from uuid import uuid4

import pytest

from apps.live_control_server.services.graph_tool_presentation import (
    GraphToolPresentation,
)
from apps.live_control_server.services.graph_tool_transport import GraphToolPageCache
from tests.test_graph_tool_transport import ARGS, SCOPE, _raw

TOOL = "expand_graph_retrieval"


def detail_pages(parent, first, tool=TOOL, args=ARGS):
    value = json.loads(first)
    token = value.get("detailPageToken") or value.get("nextPageToken")
    pages = [] if value.get("detailPageToken") else [first]
    while token:
        page = parent.continuation(tool, {**args, "resultPageToken": token})
        pages.append(page)
        token = json.loads(page).get("nextPageToken")
    return pages


def test_initial_complete_records_and_details_authorize_exact_subsets_and_repeats():
    args = {**ARGS, "operation": "object"}
    parent = GraphToolPresentation(SCOPE)
    raw = json.loads(_raw())
    raw["relationships"] = [
        {
            "edgeId": f"r:{i}",
            "sourceNodeId": "one",
            "targetNodeId": "two",
            "predicate": "knows",
            "epistemicKind": "belief",
            "temporalScope": {"kind": "past"},
        }
        for i in range(80)
    ]
    raw["sourceAnchors"][0]["evidenceRefId"] = "e:one"
    event_id = uuid4()
    first = parent.present(TOOL, args, json.dumps(raw), event_id)
    (overview,) = parent.inclusion(TOOL, [first])
    assert overview.assertion_ids and len(overview.assertion_ids) < 80
    assert not overview.relationship_ids
    assert overview.evidence_ref_ids == {"e:one"}
    assert not overview.complete
    pages = detail_pages(parent, first, args=args)
    (partial,) = parent.inclusion(TOOL, pages[:1])
    assert partial.assertion_ids and len(partial.assertion_ids) < 80
    assert not partial.relationship_ids
    (complete,) = parent.inclusion(TOOL, list(reversed(pages)) + pages)
    assert complete.assertion_ids == frozenset(f"a:{i}" for i in range(80))
    assert complete.relationship_ids == frozenset(f"r:{i}" for i in range(80))
    assert complete.evidence_ref_ids == {"e:one"} and complete.event_id == event_id
    changed = json.loads(pages[0])
    changed["records"][0]["value"].pop("epistemicKind")
    with pytest.raises(ValueError, match="Unknown"):
        parent.inclusion(TOOL, [json.dumps(changed)])
    with pytest.raises(ValueError):
        parent.inclusion("read_graph_source", [pages[0]])
    with pytest.raises(ValueError):
        GraphToolPresentation(SCOPE).inclusion(TOOL, [pages[0]])


def test_fragments_require_exact_current_envelope_reassembly():
    parent = GraphToolPresentation(SCOPE)
    raw = json.loads(_raw())
    raw["reviewedSourceObservations"] = [
        dict(raw["reviewedSourceObservations"][0], text="long qualified text. " * 1500)
    ]
    first = parent.present(TOOL, ARGS, json.dumps(raw), uuid4())
    pages = detail_pages(parent, first)
    assert len(pages) > 2
    for page in pages:
        (exposure,) = parent.inclusion(TOOL, [page])
        assert not exposure.assertion_ids
    (exposure,) = parent.inclusion(TOOL, pages)
    assert exposure.assertion_ids == {"a:0"}
    # Previous inclusions must not leak fragment coverage into a later request.
    (exposure,) = parent.inclusion(TOOL, [pages[-1]])
    assert not exposure.assertion_ids


@pytest.mark.parametrize("tool", ["read_graph_source", "read_related_recap_context"])
def test_source_and_context_need_complete_passage_and_metadata(tool):
    parent = GraphToolPresentation(SCOPE)
    raw = json.dumps(
        {
            "schema": "synthetic_source_v1",
            "content": "Ω 🐉 quoted passage. " * 2000,
            "sourceReadId": "read:one",
            "epistemicKind": "belief",
            "truncated": False,
        },
        ensure_ascii=False,
    )
    first = parent.present(tool, ARGS, raw, uuid4())
    pages = detail_pages(parent, first, tool)
    for page in pages:
        assert not parent.inclusion(tool, [page])[0].complete
    assert parent.inclusion(tool, pages)[0].complete
    assert not parent.inclusion(tool, pages[:-1])[0].complete


def test_small_exact_result_and_ambiguous_origin():
    parent = GraphToolPresentation(SCOPE)
    raw = json.dumps(
        {
            "attributes": [
                {"assertionId": "a:one", "value": "exact", "epistemicKind": "belief"}
            ]
        }
    )
    assert parent.present(TOOL, ARGS, raw, uuid4()) == raw
    (exposure,) = parent.inclusion(TOOL, [raw, raw])
    assert exposure.complete and exposure.assertion_ids == {"a:one"}
    parent.present(TOOL, ARGS, raw, uuid4())
    with pytest.raises(ValueError, match="ambiguous"):
        parent.inclusion(TOOL, [raw])


@pytest.mark.parametrize("change", ["request", "session", "tool", "expired", "forged"])
def test_continuation_cannot_restart_or_rebind(change):
    now = [0.0]
    parent = GraphToolPresentation(
        SCOPE, cache=GraphToolPageCache(clock=lambda: now[0], lifetime=1)
    )
    first = json.loads(parent.present(TOOL, ARGS, _raw(), uuid4()))
    args = {**ARGS, "resultPageToken": first["detailPageToken"]}
    tool = TOOL
    if change == "request":
        args["queryText"] = "changed"
    elif change == "session":
        args["retrievalSessionId"] = "foreign"
    elif change == "tool":
        tool = "read_graph_source"
    elif change == "expired":
        now[0] = 2
    else:
        args["resultPageToken"] = "forged"
    with pytest.raises(ValueError):
        parent.continuation(tool, args)


def test_parent_bytes_survive_real_harness_dispatch_and_provider_serializer(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from tests.test_hermes_graph_dispatch_adapter import _agent, _call
    from tests.test_hermes_graph_agent import _default_scope
    from apps.live_control_server.services.hermes_graph_agent import (
        hermes_import_namespace,
    )
    from apps.live_control_server.services.hermes_graph_dispatch_adapter import (
        install_graph_serial_dispatch,
    )
    import graph_memory.hermes_graph_plugin as plugin

    harness = _agent(tmp_path, monkeypatch)
    policy = plugin.default_graph_only_capability_policy(_default_scope())
    from apps.live_control_server.services.graph_tool_transport import TransportScope

    parent = GraphToolPresentation(
        TransportScope(
            "session:one", policy.graph_scope.world_id, policy.graph_scope.revision_pin
        )
    )
    calls = []

    def broker(tool, args):
        calls.append(args)
        raw = json.loads(_raw())
        raw["sourceAnchors"][0]["evidenceRefId"] = "e:one"
        return parent.present(tool, args, json.dumps(raw), uuid4()), None

    pt = plugin.set_active_capability_policy(policy)
    st = plugin.set_active_retrieval_session_id("session:one")
    bt = plugin.set_parent_graph_broker(broker, required=True)
    try:
        with hermes_import_namespace():
            import run_agent
            from agent.transports.chat_completions import ChatCompletionsTransport

            monkeypatch.setattr(
                run_agent,
                "handle_function_call",
                lambda name, args, *a, **kw: plugin._handler_for(name)(args),
            )
            install_graph_serial_dispatch(harness)
            call = _call(0)
            call.function.arguments = json.dumps({"operation": "object", "targets": [{"kind": "node", "id": "npc:0"}]})
            assistant = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": TOOL,
                            "arguments": call.function.arguments,
                        },
                    }
                ],
            }
            messages = [assistant]
            harness._execute_tool_calls(
                SimpleNamespace(tool_calls=[call], content=None),
                messages,
                "task:one",
                7,
            )
            provider = ChatCompletionsTransport().build_kwargs(
                model="gpt-6-luna",
                messages=messages,
                request_overrides={"parallel_tool_calls": False},
            )
            delivered = provider["messages"][1]["content"]
            overview = json.loads(delivered)
            assert overview["schema"] == "dmb_graph_tool_overview_v1"
            assert "needed complete detail record" in overview["detailUse"]
            assert "Do not drain unrelated pages" in overview["detailUse"]
            assert "Open the supporting source" in overview["interpretation"]
            assert len(delivered.encode()) <= 8000
            assert 0 < len(parent.inclusion(TOOL, [delivered])[0].assertion_ids) < 80
            assert len(calls) == 1
    finally:
        plugin.reset_parent_graph_broker(bt)
        plugin.reset_active_retrieval_session_id(st)
        plugin.reset_active_capability_policy(pt)


def test_per_target_closures_do_not_union_refs_or_admit_discovery_rows():
    parent = GraphToolPresentation(SCOPE)
    raw = json.loads(_raw())
    raw['reviewedSourceObservations'] = [
        {'assertionId': 'a:one', 'text': 'One fact', 'evidenceRefIds': ['e:b', 'e:a']},
        {'assertionId': 'a:two', 'text': 'Other fact', 'evidenceRefIds': ['e:other']},
    ]
    raw['attributes'] = []
    raw['relationships'] = []
    first = parent.present(TOOL, ARGS, json.dumps(raw), uuid4())
    exposure, = parent.inclusion(TOOL, [first])
    # A raw small result delivers both exact records; references stay disjoint.
    assert exposure.claim_evidence == (
        ('assertion', 'a:one', ('e:a', 'e:b')),
        ('assertion', 'a:two', ('e:other',)),
    )
    large = GraphToolPresentation(SCOPE, cache=GraphToolPageCache(page_bytes=8000))
    raw['reviewedSourceObservations'][0]['text'] = 'qualified ' * 1500
    first = large.present(TOOL, ARGS, json.dumps(raw), uuid4())
    discovery, = large.inclusion(TOOL, [first])
    assert discovery.claim_evidence == ()
    pages = detail_pages(large, first)
    complete, = large.inclusion(TOOL, pages)
    assert complete.claim_evidence == exposure.claim_evidence
    partial, = large.inclusion(TOOL, [pages[0]])
    assert not any(target == 'a:one' for _, target, _ in partial.claim_evidence)
    # An earlier completed reassembly cannot authorize a later partial envelope.
    partial_again, = large.inclusion(TOOL, [pages[-1]])
    assert not any(target == 'a:one' for _, target, _ in partial_again.claim_evidence)
