"""Ordinary authenticated inspection over actual Core/WK memory authority; no DB/providers."""

import copy
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dungeonmind.application.vnext import publish_native_text_source_evidence
from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
from worldkeeper.application import contracts as wk
from apps.live_control_server.routes.native_graph_inspection import router
from apps.live_control_server.services import native_graph_inspection as service
from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as transport,
)
from graph_memory.vnext.domain_runtime import CAMPAIGN_SCOPE_AXIS
from tests.test_native_recap_preparation import lane as recap_lane, TOKEN  # noqa: F401 -- pytest fixture discovery


@pytest.fixture
def inspection(request, monkeypatch):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    lane = request.getfixturevalue("recap_lane")
    bound = {"managed_world_id": "managed", **lane.bound}

    def binding(world):
        if world != "managed":
            raise ValueError("different World")
        return copy.deepcopy(bound)

    monkeypatch.setattr(service.native, "binding", binding)
    monkeypatch.setattr(service.native, "read_repository", lambda: lane.repo)
    meta = wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, lane.run.campaign_id),),
        visibility=wk.Visibility("labels_any", ("dungeonbuddy.visibility:gm",)),
        epistemic_basis="speculative",
        claim_mode="dungeonbuddy.claim:belief",
        standing="provisional",
        temporal_scope=wk.TemporalScope(kind="unknown"),
        evidence_ref_ids=(lane.support_ids["first"],),
    )
    ops = [
        wk.CreateObject(
            f"object:{i}",
            (
                wk.CreateFact(
                    f"name:{i}", "dnd5e:name", wk.LiteralFactValue(f"Object {i}"), meta
                ),
            ),
        )
        for i in range(30)
    ]
    ops += [
        wk.CreateObject("endpoint"),
        wk.CreateObject("isolated"),
        wk.CreateRelationship(
            "relationship",
            wk.ResultOf("object:0"),
            "dnd5e:located_in",
            wk.ResultOf("endpoint"),
            meta,
        ),
        wk.CreateObject(
            "other-campaign",
            (
                wk.CreateFact(
                    "elsewhere",
                    "dnd5e:name",
                    wk.LiteralFactValue("Elsewhere"),
                    replace(meta, scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, "c2"),)),
                ),
            ),
        ),
    ]
    runtime = transport.runtime(
        lane.repo,
        lane.domain,
        lane.profile,
        now=datetime.now(UTC),
        operation_id="inspection-fixture",
    )
    result = runtime.commit_prepared_change(
        runtime.prepare_change(
            wk.WorldChangeIntent(lane.bound["native_world_id"], "fixture", tuple(ops))
        ),
        confirmed_by="local_operator",
    )
    objects = {r.client_op_id: r.durable_object_id for r in result.object_results}
    assertions = {
        r.client_op_id: r.durable_assertion_id for r in result.assertion_results
    }
    app = FastAPI()
    app.include_router(router)
    client = TestClient(
        app, client=("127.0.0.1", 50000), headers={"Authorization": "Bearer " + TOKEN}
    )
    return SimpleNamespace(**locals())


def catalog(lane, **extra):
    r = lane.client.post(
        "/api/live/native-graph-inspection/catalog",
        json={"managed_world_id": "managed", **extra},
    )
    assert r.status_code == 200, r.text
    return r.json()


def read(lane, pin, selection):
    return lane.client.post(
        "/api/live/native-graph-inspection/read",
        json={"scope": pin, "selection": selection},
    )


def test_actual_catalogue_and_selected_details_preserve_native_records_without_body_prefetch(
    inspection, monkeypatch
):
    x = inspection
    monkeypatch.setattr(
        service, "open_admitted_native_text", lambda *_: pytest.fail("body prefetched")
    )
    before = copy.deepcopy(
        {k: v for k, v in x.lane.repo.__dict__.items() if k != "_lock"}
    )
    p = catalog(x, scope_mode="campaign", campaign_id=x.lane.run.campaign_id)
    ids = {e["entity_id"] for e in p["catalogue"]["entities"]}
    assert (
        len(ids) == 31
        and x.objects["endpoint"] in ids
        and x.objects["isolated"] not in ids
    )
    assert x.objects["other-campaign"] not in ids
    a = next(a for a in p["assertions"] if a["assertion_id"] == x.assertions["name:0"])
    assert (
        a["metadata"]["claim_mode"],
        a["metadata"]["epistemic_basis"],
        a["metadata"]["standing"],
    ) == ("dungeonbuddy.claim:belief", "speculative", "provisional")
    assert a["metadata"]["temporal_scope"] == {"kind": "unknown"}
    r = read(x, p["scope"], {"kind": "entity", "entity_id": x.objects["endpoint"]})
    assert r.status_code == 200 and r.json()["schema"] == "dmb_native_graph_entity_v1"
    assert all(
        a["subject_entity_id"] != x.objects["endpoint"]
        for a in r.json()["entity"]["assertions"]
    )
    assert {k: v for k, v in x.lane.repo.__dict__.items() if k != "_lock"} == before


def test_catalog_and_selected_entity_preserve_nested_temporal_metadata(inspection):
    x = inspection
    payload = {"episode": "session-29", "qualified": True, "nested": [None, {"order": 2, "_sample": {"_saved": True}}]}
    meta = replace(
        x.meta,
        temporal_scope=wk.TemporalScope(
            kind="domain_ref", schema_term="dungeonbuddy.time:fictional_anchor_v1",
            payload=payload,
        ),
        domain_metadata=(wk.DomainMetadata.from_json(
            "dungeonbuddy.domain_metadata:world_context_v1", {"uncertain": ["who reported it"]}
        ),),
    )
    runtime = transport.runtime(x.lane.repo, x.lane.domain, x.lane.profile,
                                now=datetime.now(UTC), operation_id="nested-metadata")
    result = runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent(
        x.lane.bound["native_world_id"], "fixture", (wk.UseExisting(x.objects["object:0"], (
            wk.CreateFact("nested-summary", "dnd5e:summary", wk.LiteralFactValue("A reported event."), meta),
        )),),
    )), confirmed_by="local_operator")
    assertion_id = result.assertion_results[0].durable_assertion_id
    before = copy.deepcopy({k: v for k, v in x.lane.repo.__dict__.items() if k != "_lock"})
    p = catalog(x)
    assertion = next(a for a in p["assertions"] if a["assertion_id"] == assertion_id)
    assert assertion["metadata"]["temporal_scope"] == {
        "kind": "domain_ref", "schema": "dungeonbuddy.time:fictional_anchor_v1", "payload": payload,
    }
    assert assertion["metadata"]["domain_metadata"] == [{
        "schema": "dungeonbuddy.domain_metadata:world_context_v1", "payload": {"uncertain": ["who reported it"]},
    }]
    assert assertion["value"] == {"kind": "literal", "value": "A reported event."}
    detail = read(x, p["scope"], {"kind": "entity", "entity_id": x.objects["object:0"]})
    assert detail.status_code == 200, detail.text
    detailed = next(a for a in detail.json()["entity"]["assertions"] if a["assertion_id"] == assertion_id)
    assert detailed["metadata"]["temporal_scope"]["payload"] == payload
    assert {k: v for k, v in x.lane.repo.__dict__.items() if k != "_lock"} == before


def test_only_selected_admitted_support_opens_exact_utf8_span(inspection):
    x = inspection
    p = catalog(x)
    r = read(
        x,
        p["scope"],
        {
            "kind": "source",
            "assertion_id": x.assertions["name:0"],
            "evidence_ref_id": x.lane.support_ids["first"],
        },
    )
    assert r.status_code == 200, r.text
    source = r.json()["source"]
    expected = x.lane.text.splitlines(keepends=True)[0].encode()
    assert source["text"].encode() == expected and "towér".encode() in expected
    assert (
        source["span_sha256"] == sha256(expected).hexdigest()
        and source["body_sha256"] == x.lane.digest
    )
    assert "body_text" not in source and source["span_end_byte"] - source[
        "span_start_byte"
    ] == len(expected)
    assert (
        read(
            x,
            p["scope"],
            {
                "kind": "source",
                "assertion_id": x.assertions["name:0"],
                "evidence_ref_id": x.lane.support_ids["unrelated"],
            },
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "alter", ["world", "native", "binding", "revision", "entity", "assertion", "role"]
)
def test_forged_scope_and_selection_are_refused(inspection, alter):
    x = inspection
    p = catalog(x)
    scope = p["scope"]
    selection = {"kind": "entity", "entity_id": x.objects["object:0"]}
    if alter == "world":
        scope["managed_world_id"] = "foreign"
    elif alter == "native":
        scope["native_world_id"] = "foreign"
    elif alter == "binding":
        scope["binding_version"] += 1
    elif alter == "revision":
        scope["revision_id"] = "rev:absent"
    elif alter == "entity":
        selection["entity_id"] = x.objects["isolated"]
    elif alter == "assertion":
        selection = {
            "kind": "source",
            "assertion_id": "asrt:foreign",
            "evidence_ref_id": x.lane.support_ids["first"],
        }
    else:
        scope["role"] = "gm"
    assert read(x, scope, selection).status_code in {409, 422}


def test_authentication_and_closed_scope(inspection):
    x = inspection
    x.client.headers.clear()
    assert (
        x.client.post(
            "/api/live/native-graph-inspection/catalog",
            json={"managed_world_id": "managed"},
        ).status_code
        == 401
    )
    x.client.headers["Authorization"] = "Bearer " + TOKEN
    for payload in [
        dict(managed_world_id="managed", role="gm"),
        dict(managed_world_id="managed", scope_mode="campaign"),
        dict(managed_world_id="managed", campaign_id="c1"),
    ]:
        assert (
            x.client.post(
                "/api/live/native-graph-inspection/catalog", json=payload
            ).status_code
            == 422
        )


def test_historical_valid_support_survives_later_source_epoch(inspection):
    x = inspection
    p = catalog(x)
    repo = x.lane.repo
    body = "Another later source."
    publish_native_text_source_evidence(
        repository=repo,
        domain_contract=x.lane.domain,
        semantic_profile=x.lane.profile,
        request=NativeTextSourceAdmissionV1(
            space_id=x.lane.bound["native_world_id"],
            admission_id="later-source",
            expected_parent_revision_id=repo.get_head(
                x.lane.bound["native_world_id"]
            ).head_revision_id,
            created_at=datetime.now(UTC),
            body_text=body,
            expected_body_sha256=sha256(body.encode()).hexdigest(),
            source_classification="dungeonbuddy.source:session_recap",
            authority="primary",
            visibility={"kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]},
            spans=[
                dict(
                    client_ref="context",
                    evidence_role="context",
                    start_byte=0,
                    end_byte=len(body),
                    expected_slice_sha256=sha256(body.encode()).hexdigest(),
                )
            ],
        ),
    )
    r = read(
        x,
        p["scope"],
        {
            "kind": "source",
            "assertion_id": x.assertions["name:0"],
            "evidence_ref_id": x.lane.support_ids["first"],
        },
    )
    assert r.status_code == 200, r.text
    assert (
        r.json()["scope"] == p["scope"]
        and r.json()["source"]["text"] == x.lane.text.splitlines(keepends=True)[0]
    )


def test_missing_head_is_not_a_successful_empty_catalogue(inspection, monkeypatch):
    monkeypatch.setattr(inspection.lane.repo, "get_head", lambda *_: None)
    r = inspection.client.post(
        "/api/live/native-graph-inspection/catalog",
        json={"managed_world_id": "managed"},
    )
    assert (
        r.status_code == 409
        and r.json()["detail"]["code"] == "native_inspection_head_unavailable"
    )


def test_current_binding_drift_refuses_instead_of_returning_an_old_packet(
    inspection, monkeypatch
):
    x = inspection
    first = x.binding("managed")
    calls = iter([first, {**first, "binding_version": first["binding_version"] + 1}])
    monkeypatch.setattr(service.native, "binding", lambda *_: next(calls))
    response = x.client.post(
        "/api/live/native-graph-inspection/catalog",
        json={"managed_world_id": "managed"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "native_inspection_binding_changed"


def test_player_cannot_use_gm_inspection_service(inspection):
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.models.native_graph_inspection import InspectionScope
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as caught:
        service.catalog(
            InspectionScope(managed_world_id="managed"),
            NativeGraphPrincipal("player", "player", "local_operator"),
        )
    assert caught.value.status_code == 403


def test_wrong_campaign_cannot_open_an_existing_assertion_source(inspection):
    x = inspection
    p = catalog(x, scope_mode="campaign", campaign_id="other")
    assert p["catalogue"]["entities"] == []
    response = read(
        x,
        p["scope"],
        {
            "kind": "source",
            "assertion_id": x.assertions["name:0"],
            "evidence_ref_id": x.lane.support_ids["first"],
        },
    )
    assert response.status_code == 409


def test_withdrawn_source_is_withheld_at_same_graph_pin(inspection):
    x = inspection
    pin = catalog(x)["scope"]
    selection = {
        "kind": "source",
        "assertion_id": x.assertions["name:0"],
        "evidence_ref_id": x.lane.support_ids["first"],
    }
    before = read(x, pin, selection)
    assert before.status_code == 200
    source = before.json()["source"]
    assert source["text"] == x.lane.text.splitlines(keepends=True)[0]
    repo = x.lane.repo
    space = x.lane.bound["native_world_id"]
    head = repo.get_head(space)
    events = repo.head_events(space)
    repo.withdraw_native_source(
        space_id=space,
        source_artifact_id=source["source_artifact_id"],
        source_revision_id=source["source_revision_id"],
    )
    after = read(x, pin, selection)
    assert after.status_code == 409
    assert source["text"] not in after.text
    assert repo.get_head(space) == head
    assert repo.head_events(space) == events


def test_native_complete_object_binding_opens_exact_pinned_citation(inspection):
    x = inspection
    scope = catalog(x, scope_mode="campaign", campaign_id=x.lane.run.campaign_id)["scope"]
    route = "/api/live/native-graph-inspection/complete-object"
    payload = {
            "scope": scope,
            "request": {
                "schema": "dmb_world_graph_object_projection_request_v1",
                "worldId": scope["managed_world_id"],
                "scopeMode": "campaign",
                "campaignId": scope["campaign_id"],
                "revisionPin": scope["revision_id"],
                "nodeId": x.objects["object:0"],
            },
    }
    response = x.client.post(route, json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["snapshot"]["revisionId"] == scope["revision_id"]
    evidence_id = x.lane.support_ids["first"]
    binding = next(
        row for row in result["sourceBindings"] if row["evidenceRefId"] == evidence_id
    )
    citation = read(x, scope, {
        "kind": "source",
        "assertion_id": x.assertions["name:0"],
        "evidence_ref_id": evidence_id,
    })
    assert citation.status_code == 200, citation.text
    assert citation.json()["scope"] == scope
    source = citation.json()["source"]
    expected = x.lane.text.splitlines(keepends=True)[0].encode()
    assert source["text"].encode() == expected
    assert binding["excerpt"].encode() == expected
    assert result["node"]["adjacency"][0]["sourceExcerpt"].encode() == expected
    assert result["relatedNodes"][0]["adjacency"][0]["sourceExcerpt"].encode() == expected
    # Classic presentation trims the paragraph delimiter. Native citation keeps it.
    from apps.live_control_server.models.world_graph_object_projection import (
        WorldGraphObjectProjectionSourceBinding,
    )
    from apps.live_control_server.services.world_graph_object_projection import (
        _apply_durable_bindings,
    )

    classic_binding = WorldGraphObjectProjectionSourceBinding(
        evidence_ref_id=evidence_id,
        source_artifact_id=binding["sourceArtifactId"],
        source_revision_id=binding["sourceRevisionId"],
        content_sha256=x.lane.digest,
        source_span_ref_id="src:fixture:paragraph:1",
        provenance_status="span_unresolvable",
    )
    classic, = _apply_durable_bindings(
        SimpleNamespace(source_bindings=[classic_binding]),
        records={
            (classic_binding.source_artifact_id, x.lane.digest): SimpleNamespace(
                markdown=x.lane.text, media_type="text/markdown",
            ),
        },
    )
    assert classic.provenance_status == "excerpt_ready"
    assert classic.excerpt == binding["excerpt"].removesuffix("\r\n")
    assert binding["provenanceStatus"] == "excerpt_ready"
    assert source["span_sha256"] == sha256(expected).hexdigest()
    assert source["source_artifact_id"] == binding["sourceArtifactId"]
    assert source["body_sha256"] == binding["contentSha256"] == x.lane.digest

    repo = x.lane.repo
    space = scope["native_world_id"]
    head = repo.get_head(space)
    events = repo.head_events(space)
    repo.withdraw_native_source(
        space_id=space,
        source_artifact_id=source["source_artifact_id"],
        source_revision_id=source["source_revision_id"],
    )
    after = x.client.post(route, json=payload)
    assert after.status_code == 409, after.text
    assert "excerpt" not in after.json()
    assert expected.decode().strip() not in after.text
    assert repo.get_head(space) == head
    assert repo.head_events(space) == events


def test_native_complete_object_requires_matching_pin(inspection, monkeypatch):
    x = inspection
    scope = catalog(x, scope_mode="campaign", campaign_id=x.lane.run.campaign_id)["scope"]
    request = {
        "schema": "dmb_world_graph_object_projection_request_v1",
        "worldId": scope["managed_world_id"],
        "scopeMode": "campaign",
        "campaignId": scope["campaign_id"],
        "revisionPin": scope["revision_id"],
        "nodeId": x.objects["endpoint"],
    }
    route = "/api/live/native-graph-inspection/complete-object"
    calls = []
    get_revision = x.lane.repo.get_revision

    def counted_revision(space_id, revision_id):
        calls.append((space_id, revision_id))
        return get_revision(space_id, revision_id)

    with monkeypatch.context() as capture:
        capture.setattr(x.lane.repo, "get_revision", counted_revision)
        response = x.client.post(route, json={"scope": scope, "request": request})
    assert calls == [(scope["native_world_id"], scope["revision_id"])]
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["found"]
    assert result["node"]["nodeId"] == request["nodeId"]
    assert result["snapshot"]["revisionId"] == scope["revision_id"]
    assert result["snapshot"]["scopeMode"] == "campaign"
    foreign = x.client.post(
        route,
        json={"scope": scope, "request": {**request, "nodeId": x.objects["other-campaign"]}},
    )
    assert foreign.status_code == 409, foreign.text

    response = x.client.post(
        route, json={"scope": scope, "request": {**request, "revisionPin": "rev:other"}}
    )
    assert response.status_code == 409
    response = x.client.post(
        route, json={"scope": {**scope, "binding_version": scope["binding_version"] + 1},
                     "request": request}
    )
    assert response.status_code == 409
    repo = x.lane.repo
    body = "Another later source."
    publish_native_text_source_evidence(
        repository=repo,
        domain_contract=x.lane.domain,
        semantic_profile=x.lane.profile,
        request=NativeTextSourceAdmissionV1(
            space_id=x.lane.bound["native_world_id"],
            admission_id="later-source",
            expected_parent_revision_id=repo.get_head(
                x.lane.bound["native_world_id"]
            ).head_revision_id,
            created_at=datetime.now(UTC),
            body_text=body,
            expected_body_sha256=sha256(body.encode()).hexdigest(),
            source_classification="dungeonbuddy.source:session_recap",
            authority="primary",
            visibility={"kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]},
            spans=[
                dict(
                    client_ref="context",
                    evidence_role="context",
                    start_byte=0,
                    end_byte=len(body),
                    expected_slice_sha256=sha256(body.encode()).hexdigest(),
                )
            ],
        ),
    )
    historical = x.client.post(route, json={"scope": scope, "request": request})
    assert historical.status_code == 200, historical.text
    historical_result = historical.json()
    assert historical_result["node"] == result["node"]
    assert historical_result["snapshot"]["revisionId"] == scope["revision_id"]
    assert historical_result["snapshot"]["isHead"] is False
    resolved = x.client.post(route, json={"request": request})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["snapshot"] == historical_result["snapshot"]
    assert resolved.json()["node"] == historical_result["node"]

    x.client.headers.pop("Authorization")
    assert x.client.post(route, json={"scope": scope, "request": request}).status_code == 401


def test_product_complete_object_dispatches_selected_world_to_native(inspection, monkeypatch):
    from apps.live_control_server.routes.world_graph_retrieval import router as product_router

    x = inspection
    x.app.include_router(product_router)
    monkeypatch.setenv("DMB_NATIVE_COMPLETE_OBJECT_WORLD", "managed")
    scope = catalog(x, scope_mode="campaign", campaign_id=x.lane.run.campaign_id)["scope"]
    request = {
        "schema": "dmb_world_graph_object_projection_request_v1",
        "worldId": "managed",
        "scopeMode": "campaign",
        "campaignId": scope["campaign_id"],
        "revisionPin": scope["revision_id"],
        "nodeId": x.objects["object:0"],
    }
    route = "/api/live/world-graph/retrieval/complete-object"
    expected = x.client.post(
        "/api/live/native-graph-inspection/complete-object", json={"request": request}
    )
    actual = x.client.post(route, json=request)
    assert expected.status_code == actual.status_code == 200, actual.text
    assert actual.json() == expected.json()
    assert actual.json()["sourceBindings"]
    other_campaign = {**request, "nodeId": x.objects["other-campaign"]}
    campaign = x.client.post(route, json=other_campaign)
    assert campaign.status_code == 409, campaign.text
    world = x.client.post(route, json={**other_campaign, "scopeMode": "world"})
    assert world.status_code == 200, world.text
    assert world.json()["node"]["nodeId"] == other_campaign["nodeId"]
    assert world.json()["snapshot"]["revisionId"] == scope["revision_id"]
    rejected = x.client.post(route, json={**request, "revisionPin": "rev:unavailable"})
    assert rejected.status_code == 409, rejected.text
    x.client.headers.pop("Authorization")
    assert x.client.post(route, json=request).status_code == 401


def test_catalog_fetches_the_pinned_revision_once(inspection, monkeypatch):
    repo = inspection.lane.repo
    get_revision = repo.get_revision
    reads = []

    def count_revision_read(space_id, revision_id):
        reads.append((space_id, revision_id))
        return get_revision(space_id, revision_id)

    monkeypatch.setattr(repo, "get_revision", count_revision_read)
    result = catalog(inspection, scope_mode="campaign", campaign_id=inspection.lane.run.campaign_id)
    scope = result["scope"]
    assert reads == [(scope["native_world_id"], scope["revision_id"])]
    assert result["assertions"]


def test_managed_projection_uses_native_authorized_graph(inspection, monkeypatch):
    from apps.live_control_server.routes.world_graph_projection import router as projection_router
    from apps.live_control_server.services import managed_world_graph_projection as managed

    lane = inspection.lane
    space = lane.bound["native_world_id"]
    binding = managed.VerifiedManagedWorldBinding("managed", space, 1, "")
    monkeypatch.setattr(managed, "resolve_managed_world_binding", lambda *a, **kw: binding)
    monkeypatch.setenv("DMB_VNEXT_MANAGED_PROJECTION_WORLD", "managed")

    def forbidden(*args, **kwargs):
        pytest.fail("Native managed route used the classic graph")

    monkeypatch.setattr(managed, "project_world_graph", forbidden)
    inspection.app.include_router(projection_router)
    revision = lane.repo.get_head(space).head_revision_id
    response = inspection.client.post(
        "/api/live/world-graph/managed-projection",
        json={
            "schema": "dmb_managed_world_graph_projection_request_v1",
            "managedWorldId": "managed",
            "revisionPin": revision,
            "queryText": "Object 0",
        },
    )
    assert response.status_code == 200, response.text
    projection = response.json()["projection"]
    assert projection["snapshot"]["revisionId"] == revision
    nodes = {node["nodeId"]: node for node in projection["nodes"]}
    source = nodes[inspection.objects["object:0"]]
    target = nodes[inspection.objects["endpoint"]]
    assert source["adjacency"][0]["direction"] == "outgoing"
    assert target["adjacency"][0]["direction"] == "incoming"
    assert target["evidenceRefIds"] == []
    assert target["evidenceBadges"] == []
    assert source["campaignScopeUnknown"] is True
    assert source["campaignScope"] is None
    assert [badge["evidenceRefId"] for badge in source["evidenceBadges"]] == source["evidenceRefIds"]
    assert source["suggestedExpansions"][0]["nodeId"] == target["nodeId"]
    assert projection["queryContext"]["matchedNodeIds"][:2] == [source["nodeId"], target["nodeId"]]
    assert "relationship_or_related_object_phrase" in projection["queryContext"]["matchReasons"][target["nodeId"]]
    assert projection["attributes"] == []
    assert lane.repo.get_head(space).head_revision_id == revision
    unavailable = inspection.client.post(
        "/api/live/world-graph/managed-projection",
        json={
            "schema": "dmb_managed_world_graph_projection_request_v1",
            "managedWorldId": "managed",
            "revisionPin": "missing-native-revision",
        },
    )
    assert unavailable.status_code >= 400
    assert "projection" not in unavailable.json()
    assert lane.repo.get_head(space).head_revision_id == revision

    citation = read(
        inspection,
        catalog(inspection)["scope"],
        {
            "kind": "source",
            "assertion_id": inspection.assertions["name:0"],
            "evidence_ref_id": lane.support_ids["first"],
        },
    )
    assert citation.status_code == 200, citation.text
    cited_source = citation.json()["source"]
    projected_citation = next(
        item for item in projection["evidence"]
        if item["evidenceRefId"] == lane.support_ids["first"]
    )
    assert projected_citation["sourceArtifactId"] == cited_source["source_artifact_id"]
    assert cited_source["text"] == lane.text.splitlines(keepends=True)[0]
    head = lane.repo.get_head(space)
    events = lane.repo.head_events(space)
    lane.repo.withdraw_native_source(
        space_id=space,
        source_artifact_id=cited_source["source_artifact_id"],
        source_revision_id=cited_source["source_revision_id"],
    )
    after = inspection.client.post(
        "/api/live/world-graph/managed-projection",
        json={
            "schema": "dmb_managed_world_graph_projection_request_v1",
            "managedWorldId": "managed",
            "revisionPin": revision,
        },
    )
    assert after.status_code == 200, after.text
    assert lane.support_ids["first"] not in {
        item["evidenceRefId"] for item in after.json()["projection"]["evidence"]
    }
    assert lane.repo.get_head(space) == head
    assert lane.repo.head_events(space) == events


@pytest.mark.parametrize("depth", [1, 2])
def test_native_neighborhood_citation_round_trip(inspection, depth):
    x = inspection
    historical_pin = catalog(
        x, scope_mode="campaign", campaign_id=x.lane.run.campaign_id
    )["scope"]
    runtime = transport.runtime(
        x.lane.repo, x.lane.domain, x.lane.profile,
        now=datetime.now(UTC), operation_id="inspection-second-hop",
    )
    extension = runtime.commit_prepared_change(
        runtime.prepare_change(wk.WorldChangeIntent(x.lane.bound["native_world_id"], "second-hop", (
            wk.CreateObject("boundary"),
            wk.CreateRelationship(
                "second-edge", wk.DurableObjectRef(x.objects["endpoint"]),
                "dnd5e:located_in", wk.ResultOf("boundary"), x.meta,
            ),
        ))),
        confirmed_by="local_operator",
    )
    boundary = extension.object_results[0].durable_object_id
    pin = catalog(x, scope_mode="campaign", campaign_id=x.lane.run.campaign_id)["scope"]
    seed = x.objects["object:0"]
    foreign = x.objects["other-campaign"]
    response = read(x, pin, {
        "kind": "neighborhood",
        "seed_node_ids": [seed, foreign, "ent:absent"],
        "max_depth": depth,
    })
    assert response.status_code == 200, response.text
    packet = response.json()
    assert packet["scope"] == pin
    expected = [seed, x.objects["endpoint"]] + ([boundary] if depth == 2 else [])
    assert packet["node_ids"] == expected
    assert set(packet["missing_seed_node_ids"]) == {foreign, "ent:absent"}
    capped = read(x, pin, {
        "kind": "neighborhood",
        "seed_node_ids": [seed],
        "max_depth": depth,
        "max_nodes": 1,
        "max_relationships": 1,
    })
    assert capped.status_code == 200, capped.text
    assert capped.json()["node_ids"] == [seed]
    assert capped.json()["nodes_truncated"] is True
    assert capped.json()["relationships"] == []
    historical = read(x, historical_pin, {
        "kind": "neighborhood",
        "seed_node_ids": [seed],
        "max_depth": depth,
    })
    assert historical.status_code == 200, historical.text
    assert historical.json()["scope"] == historical_pin
    assert historical.json()["node_ids"] == [seed, x.objects["endpoint"]]
    assert len(historical.json()["relationships"]) == 1
    edges = packet["relationships"]
    assert len(edges) == depth
    assert [edge["edgeId"] for edge in edges] == sorted(edge["edgeId"] for edge in edges)
    for edge in edges:
        source = read(x, pin, {
            "kind": "source",
            "assertion_id": edge["edgeId"],
            "evidence_ref_id": edge["evidenceRefIds"][0],
        })
        assert source.status_code == 200, source.text
        assert source.json()["source"]["text"] == x.lane.text.splitlines(keepends=True)[0]


def test_shared_neighborhood_anchor_reopens_exact_citation(inspection, monkeypatch):
    from apps.live_control_server.routes.world_graph_retrieval import router as retrieval_router
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import native_anchor_id
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadRequest

    x = inspection
    body = "Second source: café."
    digest = sha256(body.encode()).hexdigest()
    space = x.lane.bound["native_world_id"]
    second = publish_native_text_source_evidence(
        repository=x.lane.repo, domain_contract=x.lane.domain, semantic_profile=x.lane.profile,
        request=NativeTextSourceAdmissionV1(
            space_id=space, admission_id="neighborhood-second-source",
            expected_parent_revision_id=x.lane.repo.get_head(space).head_revision_id,
            created_at=datetime.now(UTC), body_text=body, expected_body_sha256=digest,
            source_classification="dungeonbuddy.source:session_recap", authority="primary",
            visibility={"kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]},
            spans=[dict(client_ref="support", evidence_role="support", start_byte=0,
                        end_byte=len(body.encode()), expected_slice_sha256=digest)],
        ),
    )
    second_id = second.bindings[0].evidence_ref_id
    runtime = transport.runtime(
        x.lane.repo, x.lane.domain, x.lane.profile,
        now=datetime.now(UTC), operation_id="neighborhood-multisource",
    )
    committed = runtime.commit_prepared_change(
        runtime.prepare_change(wk.WorldChangeIntent(space, "multisource", (
            wk.CreateObject("second-target"),
        wk.UseExisting(x.objects["object:0"], (
            wk.CreateFact("source-kind", "dungeonbuddy:source_classification",
                          wk.TermRefFactValue("dungeonbuddy.source:session_recap"), x.meta),
        )),
            wk.CreateRelationship(
                "multisource-edge", wk.DurableObjectRef(x.objects["object:0"]),
                "dnd5e:located_in", wk.ResultOf("second-target"),
                replace(x.meta, evidence_ref_ids=(x.lane.support_ids["first"], second_id)),
            ),
        ))), confirmed_by="local_operator",
    )
    multi_edge = committed.assertion_results[0].durable_assertion_id
    pin = catalog(x, scope_mode="campaign", campaign_id=x.lane.run.campaign_id)["scope"]
    request = WorldGraphSourceAnchorReadRequest.model_validate({
        "schema": "dmb_world_graph_source_anchor_read_request_v1",
        "worldId": "managed",
        "campaignId": x.lane.run.campaign_id,
        "revisionPin": pin["revision_id"],
        "anchorId": native_anchor_id(x.assertions["relationship"], x.lane.support_ids["first"]),
    })
    monkeypatch.setenv("DMB_NATIVE_NEIGHBORHOOD_WORLD", "managed")
    x.app.include_router(retrieval_router)
    neighborhood = x.client.post(
        "/api/live/world-graph/retrieval/neighborhood",
        json={
            "schema": "dmb_world_graph_neighborhood_request_v1",
            "worldId": "managed",
            "campaignId": x.lane.run.campaign_id,
            "revisionPin": pin["revision_id"],
            "seedNodeIds": [x.objects["object:0"]],
        },
    )
    assert neighborhood.status_code == 200, neighborhood.text
    packet = neighborhood.json()
    assert packet["requestSummary"] == {
        "seed_node_ids": [x.objects["object:0"]],
        "max_depth": 1,
    }
    assert packet["nodes"][0]["label"] == "Object 0"
    attribute, = packet["attributes"]
    assert attribute["predicate"] == "dungeonbuddy:source_classification"
    assert attribute["value"] == {"term": "dungeonbuddy.source:session_recap"}
    assert attribute["subjectNodeId"] == x.objects["object:0"]
    assert attribute["evidenceRefIds"] == [x.lane.support_ids["first"]]
    anchor = next(row for row in packet["sourceAnchors"] if row["evidenceRefId"] == x.lane.support_ids["first"])
    assert set(anchor["supportingAssertionIds"]) == {x.assertions["relationship"], multi_edge}
    assert len(packet["sourceAnchors"]) == 2
    assert anchor["revisionId"] == pin["revision_id"]
    response = x.client.post(
        "/api/live/world-graph/retrieval/source-anchor/read",
        json=request.model_dump(mode="json", by_alias=True),
    )
    assert response.status_code == 200, response.text
    assert response.json()["outcome"] == "enough"
    assert response.json()["content"] == x.lane.text.splitlines(keepends=True)[0]
    exact_sources = {
        x.lane.support_ids["first"]: x.lane.text.splitlines(keepends=True)[0],
        second_id: body,
    }
    multi_anchors = [
        row for row in packet["sourceAnchors"] if multi_edge in row["supportingAssertionIds"]
    ]
    assert {row["evidenceRefId"] for row in multi_anchors} == set(exact_sources)
    assert len({row["sourceArtifactId"] for row in multi_anchors}) == 2
    for row in multi_anchors:
        opened = x.client.post(
            "/api/live/world-graph/retrieval/source-anchor/read",
            json={**request.model_dump(mode="json", by_alias=True), "anchorId": row["anchorId"]},
        )
        assert opened.status_code == 200, opened.text
        assert opened.json()["content"] == exact_sources[row["evidenceRefId"]]
    for change in ({"campaignId": "foreign"}, {"revisionPin": None}):
        refused = x.client.post(
            "/api/live/world-graph/retrieval/source-anchor/read",
            json={**request.model_dump(mode="json", by_alias=True), **change},
        )
        assert refused.status_code == 200, refused.text
        assert refused.json()["outcome"] == "empty"
        assert refused.json()["content"] is None


def test_shared_native_neighborhood_requires_authentication(inspection, monkeypatch):
    from apps.live_control_server.routes.world_graph_retrieval import router

    inspection.app.include_router(router)
    monkeypatch.setenv("DMB_NATIVE_NEIGHBORHOOD_WORLD", "managed")
    inspection.client.headers.pop("Authorization")
    response = inspection.client.post(
        "/api/live/world-graph/retrieval/neighborhood",
        json={
            "schema": "dmb_world_graph_neighborhood_request_v1",
            "worldId": "managed",
            "campaignId": inspection.lane.run.campaign_id,
            "seedNodeIds": [inspection.objects["object:0"]],
        },
    )
    assert response.status_code == 401, response.text


def test_shared_exact_object_selects_one_native_node(inspection, monkeypatch):
    from apps.live_control_server.routes import world_graph_retrieval as routes
    from fastapi.testclient import TestClient

    lane = inspection
    monkeypatch.setenv("DMB_NATIVE_EXACT_OBJECT_WORLD", "managed")
    monkeypatch.setattr(routes, "get_campaign_object", lambda _: pytest.fail("classic object fallback"))
    lane.app.include_router(routes.router)
    node_id = lane.objects["object:0"]
    response = lane.client.post(
        "/api/live/world-graph/retrieval/object",
        json={
            "schema": "dmb_world_graph_object_request_v1",
            "worldId": "managed",
            "campaignId": lane.lane.run.campaign_id,
            "nodeId": node_id,
            "bounds": {"maxNodes": 1},
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["operation"] == "object"
    assert payload["requestSummary"] == {"node_id": node_id}
    assert payload["resolvedNodeId"] == node_id
    assert [node["nodeId"] for node in payload["nodes"]] == [node_id]
    assert payload["relationships"]
    anchor, = payload["sourceAnchors"]
    assert lane.assertions["name:0"] in anchor["supportingAssertionIds"]
    opened = lane.client.post(
        "/api/live/world-graph/retrieval/source-anchor/read",
        json={
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            "worldId": "managed",
            "campaignId": lane.lane.run.campaign_id,
            "revisionPin": payload["snapshot"]["revisionId"],
            "anchorId": anchor["anchorId"],
        },
    )
    assert opened.status_code == 200, opened.text
    assert opened.json()["content"] == lane.lane.text.split("\r\n\r\n", 1)[0] + "\r\n"

    missing = lane.client.post(
        "/api/live/world-graph/retrieval/object",
        json={
            "schema": "dmb_world_graph_object_request_v1",
            "worldId": "managed",
            "campaignId": lane.lane.run.campaign_id,
            "nodeId": "ent:missing",
            "revisionPin": payload["snapshot"]["revisionId"],
        },
    )
    assert missing.status_code == 200, missing.text
    assert missing.json()["outcome"] == "empty"
    assert missing.json()["snapshot"]["revisionId"] == payload["snapshot"]["revisionId"]
    assert missing.json()["resolvedNodeId"] is None

    with TestClient(lane.app, client=("127.0.0.1", 50000)) as anonymous:
        denied = anonymous.post(
            "/api/live/world-graph/retrieval/object",
            json={
                "schema": "dmb_world_graph_object_request_v1",
                "worldId": "managed",
                "campaignId": lane.lane.run.campaign_id,
                "nodeId": node_id,
            },
        )
    assert denied.status_code == 401, denied.text


def test_shared_evidence_resolves_native_target_kinds(inspection, monkeypatch):
    from apps.live_control_server.routes import world_graph_retrieval as routes

    monkeypatch.setenv("DMB_NATIVE_EVIDENCE_WORLD", "managed")
    monkeypatch.setattr(routes, "get_object_evidence", lambda _: pytest.fail("classic evidence fallback"))
    inspection.app.include_router(routes.router)
    base = {"worldId": "managed", "campaignId": inspection.lane.run.campaign_id}
    prefix = "/api/live/world-graph/retrieval"
    for kind, target_id, field in (
        ("node", inspection.objects["object:0"], "nodes"),
        ("attribute", inspection.assertions["name:0"], "attributes"),
        ("relationship", inspection.assertions["name:0"], "relationships"),
        ("relationship", inspection.assertions["relationship"], "relationships"),
    ):
        response = inspection.client.post(
            prefix + "/evidence",
            json={
                **base,
                "schema": "dmb_world_graph_evidence_request_v1",
                "target": {"kind": kind, "id": target_id},
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["operation"] == "evidence"
        if kind == "relationship" and target_id == inspection.assertions["name:0"]:
            assert result["outcome"] == "empty"
            assert result[field] == result["sourceAnchors"] == []
            continue
        assert len(result[field]) == 1
        anchor = result["sourceAnchors"][0]
        opened = inspection.client.post(
            prefix + "/source-anchor/read",
            json={
                **base,
                "schema": "dmb_world_graph_source_anchor_read_request_v1",
                "revisionPin": result["snapshot"]["revisionId"],
                "anchorId": anchor["anchorId"],
            },
        )
        assert opened.status_code == 200, opened.text


def test_shared_search_preserves_admitted_seed_under_node_bound(inspection, monkeypatch):
    from apps.live_control_server.routes import world_graph_retrieval as routes

    monkeypatch.setenv("DMB_NATIVE_SEARCH_WORLD", "managed")
    monkeypatch.setattr(routes, "search_campaign_graph", lambda _: pytest.fail("classic search fallback"))
    inspection.app.include_router(routes.router)
    from collections import Counter
    from dungeonmind.application.vnext import EntityReadService

    reads = Counter()
    original_read = EntityReadService.get_complete_entity

    def count_complete_read(self, context, entity_id):
        reads[entity_id] += 1
        return original_read(self, context, entity_id)

    monkeypatch.setattr(EntityReadService, "get_complete_entity", count_complete_read)
    seeds = sorted(inspection.objects[key] for key in ("object:0", "object:1"))
    response = inspection.client.post(
        "/api/live/world-graph/retrieval/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            "worldId": "managed",
            "campaignId": inspection.lane.run.campaign_id,
            "queryText": "Object",
            "seedNodeIds": [*reversed(seeds), "ent:missing"],
            "bounds": {"maxNodes": 1},
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["operation"] == "search"
    assert result["matchedNodeIds"] == seeds
    assert [node["nodeId"] for node in result["nodes"]] == seeds
    assert all("exact_seed" in result["matchReasons"][seed] for seed in seeds)
    assert result["coverage"]["missingSeedNodeIds"] == ["ent:missing"]

    assert reads == Counter({seed: 1 for seed in [*seeds, "ent:missing"]})

    lexical = inspection.client.post(
        "/api/live/world-graph/retrieval/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            "worldId": "managed",
            "campaignId": inspection.lane.run.campaign_id,
            "queryText": "Object 1",
            "bounds": {"maxNodes": 1},
        },
    )
    assert lexical.status_code == 200, lexical.text
    result = lexical.json()
    assert result["matchedNodeIds"] == [inspection.objects["object:1"]]
    assert result["relationships"] == []
    anchor, = result["sourceAnchors"]
    assert anchor["evidenceRefId"] == inspection.lane.support_ids["first"]

    foreign_scope = inspection.client.post(
        "/api/live/world-graph/retrieval/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            "worldId": "managed",
            "campaignId": "campaign:foreign",
            "queryText": inspection.objects["object:1"],
            "seedNodeIds": [inspection.objects["object:1"]],
        },
    )
    assert foreign_scope.status_code == 200, foreign_scope.text
    result = foreign_scope.json()
    assert result["matchedNodeIds"] == result["nodes"] == result["sourceAnchors"] == []
    assert result["coverage"]["missingSeedNodeIds"] == [inspection.objects["object:1"]]


def test_native_search_source_pin_matches_batch_receipt(inspection, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads
    from apps.live_control_server.services import native_graph_inspection as native, world_graph_retrieval
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from graph_memory.retrieval.models import WorldGraphSearchRequest, WorldGraphSourceAnchorReadRequest

    principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
    scope = {"worldId": "managed", "campaignId": inspection.lane.run.campaign_id}
    search_request = WorldGraphSearchRequest.model_validate({
        **scope, "schema": "dmb_world_graph_search_request_v1", "queryText": "Object 1",
        "bounds": {"maxNodes": 1},
    })
    binding = inspection.lane.bound
    with pytest.raises(native.InspectionUnavailable, match="native_inspection_binding_changed"):
        native.shared_search(
            search_request, principal, include_source_pins=True,
            expected_native_world_id=binding["native_world_id"],
            expected_binding_version=binding["binding_version"] + 1,
        )
    search = native.shared_search(
        search_request, principal, include_source_pins=True,
        expected_native_world_id=binding["native_world_id"],
        expected_binding_version=binding["binding_version"],
    )
    pin, = search.source_pins
    monkeypatch.setattr(world_graph_reads, "direct_services_from_config",
                        lambda *_: pytest.fail("classic source reader invoked"))
    receipt, = world_graph_retrieval.read_source_anchors_internal_v2((
        WorldGraphSourceAnchorReadRequest.model_validate({
            **scope, "schema": "dmb_world_graph_source_anchor_read_request_v1",
            "revisionPin": pin.graph_revision, "anchorId": pin.anchor_id,
        }),
    ), native_principal=principal)
    assert receipt.result.content == inspection.lane.text.splitlines(keepends=True)[0]
    assert receipt.result.snapshot.revision_id == receipt.graph_revision == pin.graph_revision
    assert receipt.source_revision_id == pin.source_revision_id
    assert receipt.evidence_ref_id == pin.evidence_ref_id
    assert receipt.source_artifact_id == pin.source_artifact_id
    assert receipt.source_span_ref_id == receipt.result.source_span_ref_id

    from graph_memory.interaction import expansion_executor
    from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot, SourceAnchorState

    from types import SimpleNamespace

    authority = SimpleNamespace(
        managed_world_id=scope["worldId"], native_world_id=inspection.lane.bound["native_world_id"],
        binding_version=inspection.lane.bound["binding_version"], graph_revision=pin.graph_revision,
    )
    assert authority.managed_world_id != authority.native_world_id
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(world_id=authority.native_world_id, campaign_id=scope["campaignId"],
                                 revision_id=pin.graph_revision),
        question="Object 1",
        source_anchors=[SourceAnchorState(anchor_id=pin.anchor_id, readable=True)],
    )
    monkeypatch.setattr(expansion_executor, "artifact_data_root", lambda **_: inspection.lane.tmp_path)
    monkeypatch.setattr(expansion_executor, "get_session", lambda _: session)
    monkeypatch.setattr(expansion_executor, "replace_session", lambda _: None)
    batch = expansion_executor.execute_read_graph_source({
        "retrievalSessionId": session.id, "anchorIds": [pin.anchor_id],
    }, receipt_version=2, native_principal=principal, native_authority=authority)
    read, = batch["reads"]
    assert read["result"]["content"] == receipt.result.content
    assert read["receipt"]["source_revision_id"] == pin.source_revision_id
    assert read["receipt"]["graph_revision"] == pin.graph_revision
    assert session.source_reads[0].receipt_v2 is not None

    stale_authority = SimpleNamespace(**{
        **vars(authority), "binding_version": authority.binding_version + 1,
    })
    rejected = expansion_executor.execute_read_graph_source({
        "retrievalSessionId": session.id, "anchorIds": [pin.anchor_id],
    }, receipt_version=2, native_principal=principal, native_authority=stale_authority)
    denied_read, = rejected["reads"]
    assert denied_read["receipt"] is None
    assert denied_read["result"]["code"] == "native_source_unavailable"
    assert "content" not in denied_read["result"]


def test_native_recap_pages_reauthorize_exact_span_after_withdrawal(inspection):
    from apps.live_control_server.models.native_graph_inspection import InspectionRead
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.services.native_graph_inspection import InspectionUnavailable
    from apps.live_control_server.services.native_recap_pages import read_native_recap_page

    x = inspection
    principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
    request = InspectionRead.model_validate({
        "scope": catalog(x)["scope"],
        "selection": {
            "kind": "source",
            "assertion_id": x.assertions["name:0"],
            "evidence_ref_id": x.lane.support_ids["first"],
        },
    })
    first = read_native_recap_page(request, principal, max_chars=2)
    cursor = first["next_continuation"]
    assert cursor
    last = read_native_recap_page(request, principal, max_chars=1000, continuation=cursor)
    assert first["source"]["text"] + last["source"]["text"] == x.lane.text.splitlines(keepends=True)[0]
    assert last["next_continuation"] is None
    discovered = x.client.post("/api/live/native-graph-inspection/related-recaps", json={
        "scope": request.scope.model_dump(mode="json"),
        "assertion_id": request.selection.assertion_id,
    })
    assert discovered.status_code == 200
    target, = discovered.json()["targets"]
    assert target["selection"] == request.selection.model_dump(mode="json")
    assert target["source_revision_id"] == first["source"]["source_revision_id"]
    route = "/api/live/native-graph-inspection/recap-page"
    payload = {"read": request.model_dump(mode="json"), "max_chars": 2}
    assert x.client.post(route, json=payload).json() == first
    assert x.client.post(route, json={**payload, "continuation": cursor + "0"}).status_code == 409
    with pytest.raises(ValueError, match="invalid recap continuation"):
        read_native_recap_page(request, principal, max_chars=2, continuation=cursor + "0")

    repo = x.lane.repo
    space = request.scope.native_world_id
    head = repo.get_head(space)
    repo.withdraw_native_source(
        space_id=space,
        source_artifact_id=first["source"]["source_artifact_id"],
        source_revision_id=first["source"]["source_revision_id"],
    )
    with pytest.raises(InspectionUnavailable):
        read_native_recap_page(request, principal, max_chars=2, continuation=cursor)
    assert repo.get_head(space) == head
    withdrawn = x.client.post(route, json={**payload, "continuation": cursor})
    assert withdrawn.status_code == 409
    assert "source" not in withdrawn.json()
    x.client.headers.pop("Authorization")
    assert x.client.post(route, json=payload).status_code == 401
    assert x.client.post("/api/live/native-graph-inspection/related-recaps", json={
        "scope": request.scope.model_dump(mode="json"),
        "assertion_id": request.selection.assertion_id,
    }).status_code == 401
