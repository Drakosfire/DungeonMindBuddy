"""Creation routes use real HTTP/auth and disposable APP persistence.

Hosted identity transport/catalog are synthetic through the existing owner
fixture. These tests do not claim real DMS or deployed browser qualification.
"""
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import psycopg
import pytest

from tests.test_hosted_native_graph_access import (
    OTHER_OWNER, hosted as hosted, recap_lane as recap_lane,
)


def _source(hosted, tmp_path):
    from application_state.content.service import commit_plan
    from apps.live_control_server.services.workspace_document_registry import create_world_owned_plan_v2
    from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
    from tests.test_prepared_tables import source

    plan = create_world_owned_plan_v2(tmp_path, world_id="managed", title="Creation authority")
    commit_plan(plan.document_id, V2_SOURCE_MARKDOWN + "\n\n" + source(),
                expected_world_id="managed", expected_revision=plan.revision)
    saved = hosted.client.request("GET", f"/api/live/workspace-documents/{plan.document_id}/committed-revision")
    assert saved.status_code == 200, saved.text
    record = saved.json()
    return dict(playable_artifact_id=plan.document_id,
                expected_playable_revision=record["revision_n"],
                expected_playable_work_revision_id=record["work_revision_id"],
                expected_playable_content_sha256=record["content_sha256"])


def _counts(dsn, run_id):
    with psycopg.connect(dsn) as conn:
        return tuple(conn.execute(f"SELECT count(*) FROM play.{table} WHERE run_id=%s", (run_id,)).fetchone()[0]
                     for table in ("session_creation_cancellation", "session_preparation", "run"))


@pytest.mark.parametrize("mode", ["local", "hosted"])
def test_creation_routes_cancel_and_replay(application_state_dsn, hosted, tmp_path, monkeypatch, mode):
    body = _source(hosted, tmp_path)
    if mode == "local":
        from apps.live_control_server.routes.play_runs import router
        from apps.live_control_server.services.agent_graph_auth import (
            AUTH_ENVIRONMENT_ENV, AUTH_MODE_ENV, LOCAL_OPERATOR_TOKEN_ENV,
        )
        from tests.test_agent_graph_auth import _clear_auth_environment, LOCAL_OPERATOR_TOKEN

        _clear_auth_environment(monkeypatch)
        monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
        monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
        monkeypatch.setenv(AUTH_ENVIRONMENT_ENV, "local")
        monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
        monkeypatch.setenv(LOCAL_OPERATOR_TOKEN_ENV, LOCAL_OPERATOR_TOKEN)
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, client=("127.0.0.1", 12345))
        def request(method, path, *, authorized=True, **kwargs):
            headers = {"Authorization": "Bearer " + LOCAL_OPERATOR_TOKEN} if authorized else {}
            return client.request(method, path, headers=headers, **kwargs)
        denied = 401
    else:
        def request(method, path, *, authorized=True, **kwargs):
            return hosted.client.request(method, path,
                session="owner-session" if authorized else "other-session", **kwargs)
        denied = 403
    path = "/api/live/world-play-runs/v2/preparation?world_id=managed"
    assert request("POST", path, json=body, authorized=False).status_code == denied
    preview = request("POST", path, json=body)
    assert preview.status_code == 200, preview.text
    intent = preview.json()["request"]
    run_id = uuid4()
    base = f"/api/live/world-play-runs/v2/{run_id}/creation"
    assert request("GET", base + "?world_id=managed", authorized=False).status_code == denied
    assert request("GET", base + "?world_id=managed").json() is None
    cancel = base + ":cancel?world_id=managed"
    assert request("POST", cancel, json=intent, authorized=False).status_code == denied
    assert _counts(application_state_dsn, run_id) == (0, 0, 0)
    response = request("POST", cancel, json=intent)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "canceled"
    assert request("POST", cancel, json=intent).json() == response.json()
    assert request("GET", base + "?world_id=managed").json() == response.json()
    assert _counts(application_state_dsn, run_id) == (1, 0, 0)


def test_hosted_cancellation_rechecks_authority_before_insertion(
    application_state_dsn, hosted, tmp_path, monkeypatch,
):
    from apps.live_control_server.routes import combat_scene_templates

    body = _source(hosted, tmp_path)
    preview = hosted.client.request("POST", "/api/live/world-play-runs/v2/preparation?world_id=managed", json=body)
    assert preview.status_code == 200, preview.text
    original = combat_scene_templates.require_hosted_plan_world_context
    calls = []
    def transfer_and_deny(request, world_id):
        calls.append(world_id)
        hosted.records["managed"] = hosted.records["managed"].model_copy(update={"owner_subject": OTHER_OWNER})
        original(request, world_id)
    monkeypatch.setattr(combat_scene_templates, "require_hosted_plan_world_context", transfer_and_deny)
    run_id = uuid4()
    response = hosted.client.request("POST",
        f"/api/live/world-play-runs/v2/{run_id}/creation:cancel?world_id=managed",
        json=preview.json()["request"])
    assert response.status_code == 403, response.text
    assert calls == ["managed"]
    assert _counts(application_state_dsn, run_id) == (0, 0, 0)
