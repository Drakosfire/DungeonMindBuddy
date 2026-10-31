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
