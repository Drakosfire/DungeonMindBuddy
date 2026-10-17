from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
import asyncio

import httpx
import pytest
from fastapi import FastAPI

from apps.live_control_server.services import agent_prompt_evidence as owner
from apps.live_control_server.routes import agent
from application_state.agent_conversation.context_trace import (
    TracePromptReference,
    TurnContextTraceV1,
)
from datetime import datetime, UTC


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    text = '{"instructions":"Synthetic é instructions", "input":[{"role":"user","content":"Hello"}]}'
    digest, size = sha256(text.encode()).hexdigest(), len(text.encode())
    identity = owner.store_prompt(text, digest=digest, size=size)
    reference = TracePromptReference(
        sequence=0,
        elapsed_ms=1,
        evidence_id=identity,
        provider_attempt_id=uuid4(),
        provider="openai",
        model="synthetic",
        api_mode="responses",
        serializer_version="serializer",
        payload_sha256=digest,
        payload_utf8_bytes=size,
    )
    return (
        text,
        reference,
        tmp_path / "out/agent_request_evidence" / (str(identity) + ".json"),
    )


def test_exact_bytes_private_storage_and_no_overwrite(evidence):
    text, ref, path = evidence
    assert owner.read_prompt(ref) == text
    assert path.read_bytes() == text.encode()
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize(
    "corruption", ["digest", "size", "symlink", "directory", "permissions", "missing"]
)
def test_refuses_corruption_and_unavailable_files(evidence, corruption):
    _, ref, path = evidence
    if corruption == "digest":
        path.write_bytes(b"X" * ref.payload_utf8_bytes)
    elif corruption == "size":
        path.write_bytes(b"short")
    elif corruption == "symlink":
        path.unlink()
        path.symlink_to("/etc/passwd")
    elif corruption == "directory":
        path.unlink()
        path.mkdir()
    elif corruption == "permissions":
        path.chmod(0o644)
    else:
        path.unlink()
    with pytest.raises(owner.PromptEvidenceError):
        owner.read_prompt(ref)


def test_refuses_symlink_storage_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    (tmp_path / "out").mkdir()
    (tmp_path / "out/agent_request_evidence").symlink_to(tmp_path)
    with pytest.raises(owner.PromptEvidenceError):
        owner.store_prompt("{}", digest=sha256(b"{}").hexdigest(), size=2)


def test_input_digest_size_and_technical_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    for digest, size in [("a" * 64, 2), (sha256(b"{}").hexdigest(), 3)]:
        with pytest.raises(owner.PromptEvidenceError):
            owner.store_prompt("{}", digest=digest, size=size)
    monkeypatch.setattr(owner, "MAX_PROMPT_BYTES", 1)
    with pytest.raises(owner.PromptEvidenceError):
        owner.store_prompt("{}", digest=sha256(b"{}").hexdigest(), size=2)
    assert not (tmp_path / "out").exists()


def test_new_evidence_never_overwrites_existing_blob(evidence, monkeypatch):
    text, ref, path = evidence
    monkeypatch.setattr(owner, "uuid4", lambda: ref.evidence_id)
    with pytest.raises(owner.PromptEvidenceError):
        owner.store_prompt(text, digest=ref.payload_sha256, size=ref.payload_utf8_bytes)
    assert path.read_text() == text


def test_scoped_authenticated_route_and_no_path_selectors(evidence, monkeypatch):
    text, ref, _ = evidence
    token = "synthetic-local-prompt-token-" * 2
    for key, value in {
        "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": token,
    }.items():
        monkeypatch.setenv(key, value)
    trace = TurnContextTraceV1(
        trace_id=uuid4(),
        world_id="world",
        conversation_id=uuid4(),
        turn_id=uuid4(),
        attempt=1,
        execution_start_sequence=0,
        started_at=datetime.now(UTC),
        observations=[ref],
    )
    reads = []

    def read(**binding):
        reads.append(binding)
        return [trace]

    monkeypatch.setattr(agent, "_verified_world_id", lambda value: value)
    monkeypatch.setattr(
        agent,
        "_conversation_service",
        lambda _: SimpleNamespace(list_context_trace_attempts=read),
    )
    app = FastAPI()
    app.include_router(agent.router, prefix="/api/live")
    path = f"/api/live/agent/worlds/world/conversation/turns/{trace.turn_id}/context-trace/{trace.trace_id}/prompt/{ref.provider_attempt_id}"

    async def get(url=path, auth=True):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url="http://test",
        ) as client:
            return await client.get(
                url, headers={"Authorization": "Bearer " + token} if auth else {}
            )

    assert asyncio.run(get(auth=False)).status_code == 401 and not reads
    response = asyncio.run(get())
    assert response.status_code == 200 and response.json()["payload_json"] == text
    assert response.headers["cache-control"] == "no-store"
    assert asyncio.run(get(path + "?path=/etc/passwd")).status_code == 422
    assert asyncio.run(get(path.replace("/world/", "/foreign/"))).status_code == 404
    assert (
        asyncio.run(
            get(path.replace(str(ref.provider_attempt_id), str(uuid4())))
        ).status_code
        == 404
    )
    assert (
        asyncio.run(get(path.replace(str(trace.trace_id), str(uuid4())))).status_code
        == 404
    )
    trace.observations = []
    assert asyncio.run(get()).status_code == 404  # Orphan blob is not read authority.
