from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from application_state.agent_conversation import conversation_drafts
from application_state.agent_conversation.service import AgentConversationService
from application_state.agent_conversation.types import TurnResult, TurnSubmission
from application_state.engine import connect
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError
from tests.application_state.test_agent_conversation_service import _new, _provenance, _submitted_intent


def test_independent_conversation_draft_edits(application_state_dsn, monkeypatch):
    service = AgentConversationService()
    world_id = "turn-world"
    conversation = _new(service, world_id, expected_revision=0)
    conversation_id = conversation.conversation_id

    def finish_draft(title, conversation_revision):
        text = f"Draft {title} in chat."
        accepted = service.accept_turn(TurnSubmission(
            world_id=world_id,
            conversation_id=conversation_id,
            idempotency_key=uuid4(),
            expected_conversation_revision=conversation_revision,
            user_text=text,
            provenance=_provenance(world_id),
            submitted_intent_v1=_submitted_intent(world_id, text),
        ))
        running = service.begin_turn(world_id, conversation_id, accepted.turn_id, expected_revision=1)
        service.complete_turn(TurnResult(
            world_id=world_id,
            conversation_id=conversation_id,
            turn_id=accepted.turn_id,
            expected_revision=running.revision,
            assistant_text=title,
        ))
        return dict(world_id=world_id, conversation_id=conversation_id, turn_id=accepted.turn_id)

    first = finish_draft("First", 1)
    second = finish_draft("Second", service.get_active_conversation(world_id).revision)

    with connect(application_state_dsn) as conn:
        for scope, title in [(first, "First"), (second, "Second")]:
            conversation_drafts.create_draft(conn, **scope, markdown=title)
    assert service.conversation_draft_turn_ids(
        world_id, conversation_id, [first["turn_id"], second["turn_id"], uuid4()],
    ) == {first["turn_id"], second["turn_id"]}
    assert service.conversation_draft_turn_ids(
        world_id, uuid4(), [first["turn_id"], second["turn_id"]],
    ) == set()

    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import hosted_native_graph_access

    monkeypatch.setattr(hosted_native_graph_access, "require_conversation_access", lambda *a, **kw: None)
    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    monkeypatch.setattr(agent, "_conversation_service", lambda request: AgentConversationService())
    app = FastAPI()
    app.include_router(agent.router)
    base = f"/agent/worlds/{world_id}/conversations"
    first_path = f"{base}/{conversation_id}/drafts/{first['turn_id']}"
    second_path = f"{base}/{conversation_id}/drafts/{second['turn_id']}"
    with TestClient(app) as client:
        for path, title in [(first_path, "First"), (second_path, "Second")]:
            response = client.put(path, json={"expected_revision": 1, "markdown": f"{title} edited"})
            assert response.status_code == 200, response.text
            assert response.json() == {"revision": 2, "markdown": f"{title} edited"}
    with TestClient(app) as client:
        assert client.get(first_path).json() == {"revision": 2, "markdown": "First edited"}
        assert client.get(second_path).json() == {"revision": 2, "markdown": "Second edited"}
        assert client.put(first_path, json={"expected_revision": 1, "markdown": "Stale"}).status_code == 409
        assert client.get(f"{base}/{uuid4()}/drafts/{first['turn_id']}").status_code == 404
    _check_variant_response_loss(service, second, monkeypatch, app, second_path)

    body = {"idempotency_key": "confirmed-key"}
    receipt = {"revision_id": "saved-revision"}
    with pytest.raises(ApplicationStateNotFoundError):
        service.claim_conversation_variant_save(
            **{**first, "conversation_id": uuid4()}, revision=2, create_request=body,
        )
    with pytest.raises(ApplicationStateConflictError):
        service.claim_conversation_variant_save(**first, revision=1, create_request=body)
    assert service.claim_conversation_variant_save(**first, revision=2, create_request=body) is None
    assert service.claim_conversation_variant_save(**first, revision=2, create_request=body) is None
    with pytest.raises(ApplicationStateConflictError):
        service.claim_conversation_variant_save(
            **first, revision=2, create_request={"idempotency_key": "different-key"},
        )
    assert service.record_conversation_variant_receipt(**first, revision=2, receipt=receipt) == receipt
    assert service.claim_conversation_variant_save(**first, revision=2, create_request=body) == receipt
    with pytest.raises(ApplicationStateConflictError):
        service.record_conversation_variant_receipt(
            **first, revision=2, receipt={"revision_id": "different-revision"},
        )
    with connect(application_state_dsn) as conn:
        assert conn.execute(
            "SELECT assistant_text FROM agent.turn WHERE turn_id = %s", (first["turn_id"],)
        ).fetchone()[0] == "First"


def test_draft_route_checks_access_before_read_or_edit(monkeypatch):
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import hosted_native_graph_access

    def deny(*args, **kwargs):
        raise HTTPException(status_code=403)

    def unexpected(*args, **kwargs):
        pytest.fail("Conversation storage was opened before authorization")

    monkeypatch.setattr(hosted_native_graph_access, "require_conversation_access", deny)
    monkeypatch.setattr(agent, "_verified_world_id", unexpected)
    monkeypatch.setattr(agent, "_conversation_service", unexpected)
    app = FastAPI()
    app.include_router(agent.router)
    path = f"/agent/worlds/turn-world/conversations/{uuid4()}/drafts/{uuid4()}"
    with TestClient(app) as client:
        assert client.get(path).status_code == 403
        review = f"{path}/variant-reviews/{uuid4()}"
        assert client.get(review).status_code == 403
        assert client.post(f"{review}/confirm").status_code == 403
        assert client.put(path, json={"expected_revision": 1, "markdown": "Edit"}).status_code == 403



def _check_variant_response_loss(service, scope, monkeypatch, app, draft_path, *, existing_review=None, existing_definition=None, mounted_client=None):
    from contextlib import nullcontext
    import json
    from pathlib import Path
    from types import SimpleNamespace

    from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import (
        canonicalize_definition_dict, compute_definition_digest,
    )
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import downstream_unavailable
    from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import locator_from_exact_revision
    from apps.live_control_server.integrations.dungeonmind_statblocks.generated import StatblockDefinitionV1Input
    from apps.live_control_server.integrations.dungeonmind_statblocks.models import ExactRevisionResourceV1
    from apps.live_control_server.services import conversation_variant_save
    from tests.test_statblock_acceptance_reconciliation import _definition, _locator

    definition = _definition() if existing_definition is None else StatblockDefinitionV1Input.model_validate(existing_definition)
    digest = compute_definition_digest(definition)
    fixture = Path(__file__).parents[1] / "fixtures/statblocks/v1/exact-revision-response.json"
    raw = json.loads(fixture.read_text())
    mechanics = definition.model_dump(mode="json")
    raw.update(statblock_id="sb_variant01", revision_id="rev_variant01", definition=mechanics,
               canonical_definition=canonicalize_definition_dict(mechanics), definition_digest=digest)
    raw["validation_receipt"]["definition_digest"] = digest
    exact = ExactRevisionResourceV1.model_validate(raw)
    locator = locator_from_exact_revision(exact)
    exact_reads = []
    exact_response = exact
    portrait_response = None

    review_id = existing_review or uuid4()
    if existing_review is None:
        stale_review_id = uuid4()
        for revision, identifier in [(2, review_id), (1, stale_review_id)]:
            service.store_conversation_variant_review(
                **scope, review_id=identifier, revision=revision,
                definition=definition.model_dump(mode="json"),
                base_locator=_locator().model_dump(mode="json"),
            )
        with pytest.raises(ApplicationStateConflictError, match="draft changed"):
            conversation_variant_save.save_variant(
                service, **scope,
                confirmation=conversation_variant_save.ConfirmConversationVariant(review_id=stale_review_id),
                client=object(),
            )

    create_bodies = []
    append_bodies = []

    class StatblockStub:
        def close(self):
            pass

        def validate_definition(self, request):
            assert not create_bodies
            return SimpleNamespace(
                definition_digest=digest,
                validation_receipt=SimpleNamespace(definition_digest=digest, status="valid", issues=[]),
            )

        def get_exact_revision(self, statblock_id, revision_id):
            exact_reads.append((statblock_id, revision_id))
            if portrait_response is not None and revision_id == portrait_response.revision_id:
                return portrait_response
            return exact_response

        def create_statblock(self, body):
            create_bodies.append(body)
            if len(create_bodies) == 1:
                raise downstream_unavailable("Lost response after remote commit")
            assert create_bodies[0] == body
            return SimpleNamespace(locator=locator)

        def append_revision(self, statblock_id, body):
            nonlocal portrait_response
            assert statblock_id == locator.statblock_id
            append_bodies.append(body)
            if len(append_bodies) == 1:
                portrait_response = ExactRevisionResourceV1.model_validate({
                    **raw,
                    "revision_id": "rev_portrait01",
                    "parent_revision_id": locator.revision_id,
                    "asset_bindings": body["asset_bindings"],
                    "provenance": {"accepted_through": body["accepted_through"]},
                })
                raise downstream_unavailable("Lost portrait response after remote commit")
            assert body == append_bodies[0]
            return portrait_response

    monkeypatch.setattr(conversation_variant_save, "DungeonMindStatblockV1Client", StatblockStub)
    from apps.live_control_server.routes import combat_encounters
    monkeypatch.setattr(combat_encounters, "require_combat_encounter_access", lambda *_: None)
    monkeypatch.setattr(combat_encounters, "_verified_world", lambda world_id: world_id)
    app.include_router(combat_encounters.router)
    review_path = f"{draft_path}/variant-reviews/{review_id}"
    with (nullcontext(mounted_client) if mounted_client is not None else TestClient(app)) as client:
        assert client.get(draft_path).json()["variant_review_ids"] == [str(review_id)]
        review = client.get(review_path)
        assert review.status_code == 200, review.text
        assert review.json()["saved"] is False
        assert review.json()["definition"] == definition.model_dump(mode="json")
        assert client.get(review_path.replace(str(scope["conversation_id"]), str(uuid4()))).status_code == 404
        assert client.get(f"{review_path}/saved").status_code == 404
        assert client.post(f"{review_path}/confirm").status_code == 503
        assert client.get(f"{review_path}/saved").status_code == 404
        recovered = client.post(f"{review_path}/confirm")
        assert recovered.status_code == 200, recovered.text
        assert recovered.json() == locator.model_dump(mode="json")
        assert client.get(review_path).json()["saved"] is True

        opened = client.get(f"{review_path}/saved")
        assert opened.status_code == 200, opened.text
        assert opened.json()["locator"] == recovered.json()
        assert opened.json()["revision"]["definition"] == json.loads(exact.canonical_definition)
        foreign_path = review_path.replace(str(scope["conversation_id"]), str(uuid4()))
        assert client.get(f"{foreign_path}/saved").status_code == 404
        assert exact_reads == [(locator.statblock_id, locator.revision_id)]
        exact_response = exact.model_copy(update={"revision_id": "rev_foreign"})
        assert client.get(f"{review_path}/saved").status_code == 500
        exact_response = exact
        combat = "/api/live/combat/encounters"
        world_query = f"?world_id={scope['world_id']}"
        selection = {key: str(scope[key]) for key in ("conversation_id", "turn_id")}
        selection["review_id"] = str(review_id)
        preview = client.post(f"{combat}/conversation-variant/preview{world_query}", json=selection)
        assert preview.status_code == 200, preview.text
        snapshot = preview.json()
        assert snapshot["locator"] == recovered.json()
        foreign = dict(selection, conversation_id=str(uuid4()))
        assert client.post(f"{combat}/conversation-variant/preview{world_query}", json=foreign).status_code == 404
        created = client.post(f"{combat}{world_query}", json={"title": "Saved variant encounter"})
        assert created.status_code == 200, created.text
        encounter = created.json()
        route = f"{combat}/{encounter['encounter_id']}{world_query}"
        encounter["draft"]["entities"].append({
            "id": str(uuid4()), "name": "Saved variant", "order": 1, "mechanics_snapshot": snapshot,
        })
        saved = client.put(route, json={"expected_revision": encounter["revision"], "draft": encounter["draft"]})
        assert saved.status_code == 200, saved.text
        reopened = client.get(route)
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()["draft"]["entities"][0]["mechanics_snapshot"] == snapshot



        def unexpected_client():
            pytest.fail("Completed replay tried to open a downstream client")

        with monkeypatch.context() as replay:
            replay.setattr(conversation_variant_save, "DungeonMindStatblockV1Client", unexpected_client)
            assert client.post(f"{review_path}/confirm").json() == recovered.json()

        from datetime import UTC, datetime
        from apps.live_control_server.routes import agent
        from apps.live_control_server.services.statblock_saved_revision import media

        asset_id = uuid4()
        admissions = []

        def admit(selected, owner):
            assert (selected, owner) == (asset_id, "portrait-owner")
            admissions.append(selected)
            return {
                "state": "ready", "created_at": datetime.now(UTC), "mime_type": "image/png",
                "width": 256, "height": 256,
                "receipt": {
                    "backend": "cloudflare_images", "visibility": "public", "object_id": str(asset_id),
                    "delivery_url": "https://images.example/portrait.png",
                },
            }

        monkeypatch.setattr(agent, "enforce_native_graph_gm", lambda request: SimpleNamespace(subject="portrait-owner"))
        monkeypatch.setattr(media, "get_asset", admit)
        operation_id = str(uuid4())
        command = {"operation_id": operation_id, "base": recovered.json(), "portrait_asset_id": str(asset_id)}
        save_path = f"{review_path}/saved/portrait"
        open_path = f"{review_path}/saved?portrait_operation_id={operation_id}"
        assert client.post(f"{foreign_path}/saved/portrait", json=command).status_code == 404
        assert client.post(save_path, json=command).status_code == 503
        assert client.get(open_path).status_code == 409
        changed = dict(command, portrait_asset_id=str(uuid4()))
        assert client.post(save_path, json=changed).status_code == 409
        saved_portrait = client.post(save_path, json=command)
        assert saved_portrait.status_code == 200, saved_portrait.text
        assert saved_portrait.json()["revision_id"] == "rev_portrait01"
        assert saved_portrait.json()["definition_digest"] == locator.definition_digest
        reopened_portrait = client.get(open_path)
        assert reopened_portrait.status_code == 200, reopened_portrait.text
        assert reopened_portrait.json()["revision"]["asset_bindings"] == append_bodies[0]["asset_bindings"]
        assert client.get(f"{review_path}/saved").json()["locator"] == recovered.json()
        assert len(admissions) == 1
        assert len(append_bodies) == 2
    assert len(create_bodies) == 2
