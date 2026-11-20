"""Reserved World PDF admission against disposable Buddy and Core stores."""
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from apps.live_control_server.config import WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV
from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
from apps.live_control_server.routes import agent
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
from apps.live_control_server.services.world_container_registry import create_world_container
from tests.test_native_recap_source_admission import native_core_dsn as native_core_dsn
NOW = datetime(2026, 11, 11, tzinfo=UTC)


def test_upload_provisions_reserved_world_once(
    native_core_dsn, application_state_dsn, tmp_path, monkeypatch,
):
    token = token_urlsafe(32)
    for key, value in {
        WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV: native_core_dsn,
        "DMB_MANAGED_WORLD_DATA_ROOT": str(tmp_path),
        "DMB_DEPLOYMENT_ENVIRONMENT": "local",
        "DMB_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
        "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": token,
    }.items():
        monkeypatch.setenv(key, value)
    world = create_world_container(name="PDF Event fixture")
    space = world.native_graph_binding.native_world_id
    repo = native.repository()
    pdf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.write(pdf)
    auth = {"Authorization": f"Bearer {token}"}
    app = FastAPI()
    app.include_router(agent.router)
    source = f"/agent/worlds/{world.world_id}/build-pdf-sources"
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        admission = {"admission_id": str(uuid4())}
        headers = auth | {"Content-Type": "application/pdf", "X-Pdf-Created-At": NOW.isoformat()}
        assert repo.get_head(space) is None
        malformed = client.post(source, params=admission, content=b"%PDF-1.7\ninvalid", headers=headers)
        assert malformed.status_code == 422, malformed.text
        assert repo.get_head(space) is None
        upload = client.post(source, params=admission,
            content=pdf.getvalue(), headers=auth | {
                "Content-Type": "application/pdf", "X-Pdf-Created-At": NOW.isoformat(),
            })
        assert upload.status_code == 200, upload.text
        assert upload.json()["content_sha256"] == sha256(pdf.getvalue()).hexdigest()
        head = repo.get_head(space)
        assert head is not None
        retry = client.post(source, params=admission, content=pdf.getvalue(), headers=headers)
        assert retry.status_code == 200, retry.text
        assert retry.json() == upload.json()
        assert repo.get_head(space) == head
        assert repo.get_native_pdf_source(space, upload.json()["source_revision_id"])[3] == pdf.getvalue()
