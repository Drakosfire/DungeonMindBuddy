"""Graph paging preserves frozen authorized evidence without repeating IO."""

import hashlib
import json

import pytest

from apps.live_control_server.services.graph_tool_transport import (
    GraphToolPageCache,
    PAGE_BYTES,
    OVERVIEW_SCHEMA,
    TransportScope,
)
import graph_memory.hermes_graph_plugin as plugin
from tests.test_hermes_graph_agent import _default_scope

SCOPE = TransportScope("session:one", "world:eldyrwild", "rev:one")
ARGS = {
    "retrievalSessionId": SCOPE.retrieval_session_id,
    "operation": "search",
    "queryText": "keeper",
}


def _raw():
    return json.dumps(
        {
            "schema": "dmb_world_graph_retrieval_result_v1",
            "outcome": "enough",
            "nodes": [
                {"nodeId": f"npc:{i}", "label": "keeper", "summary": None}
                for i in range(80)
            ],
            "reviewedSourceObservations": [
                {
                    "assertionId": f"a:{i}",
                    "text": "The keeper believes the visitors may be scouts. " * 6,
                    "epistemicKind": "belief",
                    "reviewId": "review:one",
                    "evidenceRefIds": ["e:one"],
                }
                for i in range(80)
            ],
            "sourceAnchors": [
                {"anchorId": "opaque:one", "supportingAssertionIds": ["a:one"]}
            ],
            "addedClaimIds": ["a:new"],
            "claimLedger": [{"claim_id": "a:old"}, {"claim_id": "a:new"}],
            "coverage": {"truncatedFields": []},
        },
        ensure_ascii=False,
    )


def _pages(cache, raw, *, tool="expand_graph_retrieval", args=ARGS, scope=SCOPE):
    first = cache.present(tool, args, scope, raw)
    initial = json.loads(first)
    if initial.get("detailPageToken"):
        first = cache.continuation(
            tool, {**args, "resultPageToken": initial["detailPageToken"]}, scope
        )
    pages = [json.loads(first)]
    while pages[-1].get("nextPageToken"):
        next_args = {**args, "resultPageToken": pages[-1]["nextPageToken"]}
        page = cache.continuation(tool, next_args, scope)
        assert page is not None
        assert len(page.encode()) <= PAGE_BYTES
        pages.append(json.loads(page))
    return pages


def test_all_records_and_qualified_claim_delta_are_recoverable():
    raw = _raw()
    original = json.loads(raw)
    cache = GraphToolPageCache()
    pages = _pages(cache, raw)
    assert len(pages) > 1
    records = [r for p in pages for r in p["records"]]
    observations = [
        r["value"] for r in records if r["path"][0] == "reviewedSourceObservations"
    ]
    assert observations == original["reviewedSourceObservations"]
    assert all(r["epistemicKind"] == "belief" for r in observations)
    assert [r["value"] for r in records if r["path"][0] == "claimDelta"] == [
        {"claim_id": "a:new"}
    ]
    assert not any(r["path"][0] == "claimLedger" for r in records)
    assert json.loads(raw) == original
    assert pages[0]["transportTruncated"] and not pages[-1]["transportTruncated"]
    assert pages[-1]["remainingRecords"] == 0
    assert sum(len(p["records"]) for p in pages) == pages[0]["recordCount"]
    assert all(not p["coreTruncated"] for p in pages)
    anchors = [r["value"] for r in records if r["path"][0] == "sourceAnchors"]
    assert anchors == original["sourceAnchors"]


def test_unicode_source_fragments_preserve_exact_source_receipt_and_offsets():
    text = 'Ω 🐉 "\\\n' * 6000
    raw = json.dumps(
        {
            "schema": "dmb_world_graph_source_anchor_read_v1",
            "content": text,
            "sourceReadId": "read:one",
            "anchorId": "opaque:one",
            "contentSha256": "parent-digest",
        },
        ensure_ascii=False,
    )
    pages = _pages(
        GraphToolPageCache(),
        raw,
        tool="read_graph_source",
        args={"anchorIds": ["opaque:one"]},
    )
    records = [r for p in pages for r in p["records"]]
    pieces = [r for r in records if r["path"] == ["content"]]
    assert all(
        r["requiresReassembly"] and r["fragmentEncoding"] == "text" for r in pieces
    )
    assert "".join(r["fragment"] for r in pieces) == text
    assert pieces[0]["start"] == 0 and pieces[-1]["end"] == len(text)
    assert all(r["sha256"] == hashlib.sha256(text.encode()).hexdigest() for r in pieces)
    assert [r["value"] for r in records if r["path"] == ["sourceReadId"]] == [
        "read:one"
    ]


@pytest.mark.parametrize(
    "change", ["scope", "world", "revision", "tool", "request", "cold", "expired"]
)
def test_foreign_or_expired_continuation_never_silently_restarts(change):
    now = [0.0]
    cache = GraphToolPageCache(clock=lambda: now[0], lifetime=1)
    page = json.loads(cache.present("expand_graph_retrieval", ARGS, SCOPE, _raw()))
    args = {
        **ARGS,
        "resultPageToken": page.get("detailPageToken", page.get("nextPageToken")),
    }
    scope = SCOPE
    tool = "expand_graph_retrieval"
    if change == "scope":
        scope = TransportScope("foreign", "world:eldyrwild", "rev:one")
    if change == "world":
        scope = TransportScope(
            SCOPE.retrieval_session_id, "world:foreign", SCOPE.revision_id
        )
    if change == "revision":
        scope = TransportScope(
            SCOPE.retrieval_session_id, SCOPE.world_id, "rev:foreign"
        )
    if change == "tool":
        tool = "read_graph_source"
    if change == "request":
        args["queryText"] = "different"
    if change == "cold":
        cache = GraphToolPageCache()
    if change == "expired":
        now[0] = 2
    result = json.loads(cache.continuation(tool, args, scope))
    assert result["schema"] == "dmb_world_graph_retrieval_error_v1"
    assert result["code"] in {
        "foreign_graph_result_page",
        "expired_or_unknown_graph_result_page",
    }


@pytest.mark.parametrize("brokered", [False, True])
def test_plugin_pages_broker_and_direct_without_repeating_operation(
    monkeypatch, brokered
):
    calls = []

    def execute(name, args, **kwargs):
        calls.append((name, args))
        return _raw()

    monkeypatch.setattr(plugin, "execute_hermes_graph_interaction_tool_json", execute)
    policy = plugin.default_graph_only_capability_policy(_default_scope())
    pt = plugin.set_active_capability_policy(policy)
    st = plugin.set_active_retrieval_session_id("session:one")
    bt = None
    if brokered:
        from uuid import uuid4
        from apps.live_control_server.services.graph_tool_presentation import GraphToolPresentation
        parent = GraphToolPresentation(TransportScope("session:one", policy.graph_scope.world_id, policy.graph_scope.revision_pin))

        def broker(name, args):
            payload = (parent.continuation(name, args) if "resultPageToken" in args else
                parent.present(name, args, execute(name, args), uuid4()))
            return payload, {
                "retrieval_session_id": "session:one",
                "snapshot": {
                    "world_id": policy.graph_scope.world_id,
                    "revision_id": policy.graph_scope.revision_pin,
                },
            }

        bt = plugin.set_parent_graph_broker(broker, required=True)
    try:
        handler = plugin._handler_for("expand_graph_retrieval")
        first = json.loads(handler(ARGS))
        assert first["schema"] == OVERVIEW_SCHEMA
        count = len(calls)
        next_args = {**ARGS, "resultPageToken": first["detailPageToken"]}
        second = json.loads(handler(next_args))
        assert second["pageIndex"] == 0 and len(calls) == count == 1
        assert "resultPageToken" not in calls[0][1]
        if brokered:
            # The real parent registers failures as exact denial feedback.
            with pytest.raises(ValueError, match="foreign_graph_result_page"):
                parent.continuation("expand_graph_retrieval", {**next_args, "queryText": "changed"})
            return
        foreign = json.loads(handler({**next_args, "queryText": "changed"}))
        assert foreign["code"] == "foreign_graph_result_page" and len(calls) == 1
    finally:
        if bt is not None:
            plugin.reset_parent_graph_broker(bt)
        plugin.reset_active_retrieval_session_id(st)
        plugin.reset_active_capability_policy(pt)


def test_actual_harness_budget_preserves_large_cumulative_serial_transcript():
    from apps.live_control_server.services.hermes_graph_agent import (
        hermes_import_namespace,
    )

    with hermes_import_namespace():
        from tools.tool_result_storage import (
            maybe_persist_tool_result,
            enforce_turn_budget,
        )

        messages = []
        for i in range(32):
            raw = GraphToolPageCache().present(
                "expand_graph_retrieval", ARGS, SCOPE, _raw()
            )
            bounded = maybe_persist_tool_result(
                raw, "expand_graph_retrieval", str(i), env=None
            )
            messages.append(
                {"role": "tool", "tool_call_id": str(i), "content": bounded}
            )
            enforce_turn_budget(messages[-1:], env=None)
            assert json.loads(messages[-1]["content"])["schema"] == OVERVIEW_SCHEMA
        assert sum(len(m["content"]) for m in messages) > 200000
        assert all(
            json.loads(m["content"])["schema"] == OVERVIEW_SCHEMA for m in messages
        )


def test_evicted_result_token_fails_without_repeating_original():
    cache = GraphToolPageCache(max_bytes=60000)
    first = json.loads(cache.present("expand_graph_retrieval", ARGS, SCOPE, _raw()))
    cache.present(
        "expand_graph_retrieval", {**ARGS, "queryText": "different"}, SCOPE, _raw()
    )
    result = json.loads(
        cache.continuation(
            "expand_graph_retrieval",
            {**ARGS, "resultPageToken": first["detailPageToken"]},
            SCOPE,
        )
    )
    assert result["code"] == "expired_or_unknown_graph_result_page"


def test_overview_exposes_exact_qualified_discovery_and_admitted_source_handle():
    original = {
        "schema": "dmb_world_graph_retrieval_result_v1",
        "operation": "search",
        "outcome": "truncated",
        "coverage": {"truncatedFields": ["objects"]},
        "reviewedSourceObservationMatches": [
            {
                "assertionId": "assertion:belief",
                "subjectNodeId": "npc:keeper",
                "textExcerpt": "The keeper believes the visitors may be scouts.",
                "excerptStart": 0,
                "excerptEnd": 50,
                "textLength": 50,
                "textSha256": "original",
                "epistemicKind": "belief",
                "temporalScope": {"condition": "if visitors return"},
                "visibility": "gm",
                "evidenceRefIds": ["e:one"],
            }
        ],
        "sourceAnchors": [
            {"anchorId": "opaque:admitted", "evidenceRefId": "e:one", "readable": True}
        ],
        "nodes": [{"nodeId": "npc:keeper", "label": "Keeper", "summary": None}],
        "provenance": "full detail " * 4000,
    }
    raw = json.dumps(original)
    cache = GraphToolPageCache()
    result = json.loads(cache.present("expand_graph_retrieval", ARGS, SCOPE, raw))
    assert result["schema"] == OVERVIEW_SCHEMA
    assert result["coreTruncated"] and result["coreCoverage"] == original["coverage"]
    row = result["view"]["reviewedSourceObservationMatches"][0]
    assert (
        row["textExcerpt"]
        == original["reviewedSourceObservationMatches"][0]["textExcerpt"]
    )
    assert row["epistemicKind"] == "belief" and row["temporalScope"] == {
        "condition": "if visitors return"
    }
    assert row["discoveryOnly"] is True and row["sourceAnchorIds"] == [
        "opaque:admitted"
    ]
    assert row["sourceAnchorCount"] == 1
    assert (
        "nextPageToken" not in result
    )  # provenance is optional, not a drain instruction
    assert (
        len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode())
        <= PAGE_BYTES
    )
    assert json.loads(raw) == original
    for key, counts in result["counts"].items():
        assert counts["shown"] == len(result["view"][key])
        assert counts["total"] == counts["shown"] + counts["omitted"]


def test_overview_never_clips_large_qualification_or_text_into_fact():
    original = json.loads(_raw())
    original["reviewedSourceObservations"][0]["temporalScope"] = {
        "condition": "x" * 10000
    }
    cache = GraphToolPageCache()
    result = json.loads(
        cache.present("expand_graph_retrieval", ARGS, SCOPE, json.dumps(original))
    )
    shown = result["view"]["reviewedSourceObservations"]
    assert not any(r["assertionId"] == "a:0" for r in shown)
    assert result["counts"]["reviewedSourceObservations"]["omitted"] > 0
    assert (
        len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode())
        <= PAGE_BYTES
    )
