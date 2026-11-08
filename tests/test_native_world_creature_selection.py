"""Native creature selection exercises actual Core admission and WK revisions."""

import copy
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from worldkeeper.application import contracts as wk
from dungeonmind.application.vnext.entity_reads import EntityReadCompleteness
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.routes.world_mechanics_associations import router
from apps.live_control_server.services import world_creature_selection as creatures
from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as transport,
)
from graph_memory.vnext.domain_runtime import CAMPAIGN_SCOPE_AXIS, GM_LABEL
from tests.test_native_recap_preparation import lane as recap_lane, TOKEN  # noqa: F401


@pytest.fixture
def selected(request, monkeypatch):
    lane = request.getfixturevalue("recap_lane")
    bound = {"managed_world_id": "managed", **lane.bound}

    def binding(world):
        if world != "managed":
            raise ValueError("foreign World")
        return copy.deepcopy(bound)

    monkeypatch.setattr(creatures.native, "binding", binding)
    monkeypatch.setattr(creatures.native, "read_repository", lambda: lane.repo)
    meta = wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, lane.run.campaign_id),),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        temporal_scope=wk.TemporalScope(kind="unknown"),
        evidence_ref_ids=(lane.support_ids["first"],),
    )
    operations = []
    for key, kind in [
        ("one", "dungeonbuddy:character"),
        ("two", "dungeonbuddy:creature"),
        ("authored", "dnd5e:npc"),
        ("place", "dnd5e:location"),
    ]:
        operations.append(
            wk.CreateObject(
                key,
                (
                    wk.CreateFact(
                        key + ".name",
                        "dnd5e:name",
                        wk.LiteralFactValue("Same name"),
                        meta,
                    ),
                    wk.CreateFact(
                        key + ".kind",
                        "dnd5e:classification",
                        wk.TermRefFactValue(kind),
                        meta,
                    ),
                ),
            )
        )
    operations.append(
        wk.CreateObject(
            "unclassified",
            (
                wk.CreateFact(
                    "not-a-kind",
                    "dnd5e:name",
                    wk.LiteralFactValue("Monster NPC threat"),
                    meta,
                ),
            ),
        )
    )
    runtime = transport.runtime(
        lane.repo,
        lane.domain,
        lane.profile,
        now=datetime.now(UTC),
        operation_id="native-creatures-fixture",
    )
    result = runtime.commit_prepared_change(
        runtime.prepare_change(
            wk.WorldChangeIntent(
                lane.bound["native_world_id"], "fixture", tuple(operations)
            )
        ),
        confirmed_by="local_operator",
    )
    ids = {item.client_op_id: item.durable_object_id for item in result.object_results}
    app = FastAPI()
    app.include_router(router)
    client = TestClient(
        app, client=("127.0.0.1", 50000), headers={"Authorization": "Bearer " + TOKEN}
    )
    return SimpleNamespace(**locals())


def test_actual_admission_excludes_location_and_name_guesses_and_keeps_exact_ids(
    selected,
):
    x = selected
    response = x.client.get(
        "/api/live/world-mechanics/associations/creatures?world_id=managed"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    targets = body["targets"]
    assert body["schema"] == "dmb_native_world_creatures_v1"
    assert {t["node_id"] for t in targets} == {
        x.ids["one"],
        x.ids["two"],
        x.ids["authored"],
    }
    assert all(
        t["label"] == "Same name"
        and t["role"] == ""
        and t["campaign_scope"] == x.lane.run.campaign_id
        and t["graph_revision_id"] == body["revision_id"]
        for t in targets
    )
    assert {t["kind"] for t in targets} == {"character", "creature", "npc"}
    view = creatures.catalog("managed")
    for target in view.targets:
        assert creatures.require_target(target, view, head=True) == target


def test_binding_foreign_and_tampered_selection_fail_without_fallback(selected):
    x = selected
    view = creatures.catalog("managed")
    target = view.targets[0]
    for change in [
        {"label": "Guessed"},
        {"node_id": x.ids["place"]},
        {"native_world_id": "foreign"},
        {"kind": "location"},
        {"binding_version": target.binding_version + 1},
        {"campaign_scope": "foreign"},
    ]:
        with pytest.raises(ApplicationStateConflictError):
            creatures.require_target(target.model_copy(update=change), view, head=True)
    x.bound["binding_version"] += 1
    with pytest.raises(ApplicationStateConflictError):
        creatures.require_target(target, view, head=True)
    response = x.client.get(
        "/api/live/world-mechanics/associations/creatures?world_id=foreign"
    )
    assert response.status_code == 503 and "targets" not in response.json()


def test_pinned_identity_can_be_read_but_cannot_claim_current_head(selected):
    x = selected
    old = creatures.catalog("managed")
    target = old.targets[0]
    runtime = transport.runtime(
        x.lane.repo,
        x.lane.domain,
        x.lane.profile,
        now=datetime.now(UTC),
        operation_id="next-creature-revision",
    )
    runtime.commit_prepared_change(
        runtime.prepare_change(
            wk.WorldChangeIntent(
                x.lane.bound["native_world_id"],
                "new head",
                (
                    wk.CreateObject(
                        "other",
                        (
                            wk.CreateFact(
                                "name",
                                "dnd5e:name",
                                wk.LiteralFactValue("Other"),
                                x.meta,
                            ),
                        ),
                    ),
                ),
            )
        ),
        confirmed_by="local_operator",
    )
    pinned = creatures.catalog("managed", revision_id=old.revision_id)
    assert pinned.head_revision_id != pinned.revision_id
    assert creatures.require_target(target, pinned) == target
    with pytest.raises(ApplicationStateConflictError):
        creatures.require_target(target, pinned, head=True)


def test_partial_coverage_does_not_invalidate_core_admitted_choices(
    selected, monkeypatch
):
    original = creatures.EntityReadService.list_entities
    monkeypatch.setattr(
        creatures.EntityReadService,
        "list_entities",
        lambda self, read: replace(
            original(self, read),
            completeness=EntityReadCompleteness("partial", "support_unavailable"),
        ),
    )
    view = creatures.catalog("managed")
    assert view.completeness == "partial" and len(view.targets) == 3
    creatures.require_target(view.targets[0], view, head=True)


def test_native_creature_read_requires_the_existing_gm_boundary(selected):
    response = selected.client.get(
        "/api/live/world-mechanics/associations/creatures?world_id=managed",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401
