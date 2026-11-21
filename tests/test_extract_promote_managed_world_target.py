"""The selected managed World is part of the reviewed publication authority."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from apps.live_control_server.models.extract_promote import (
    ExtractPromotePrepareRequest,
)
from apps.live_control_server.services import extract_promote
from apps.live_control_server.services.managed_world_graph_projection import (
    VerifiedManagedWorldBinding,
)


def _binding(*, native: str = "native-world", version: int = 1) -> VerifiedManagedWorldBinding:
    return VerifiedManagedWorldBinding(
        managed_world_id="managed-world",
        native_world_id=native,
        binding_version=version,
        source_root_relpath="corpus/managed-world-markdown",
    )


def _package(*, candidate: Path | None = None) -> dict:
    effect: dict = {"world_id": "native-world"}
    if candidate is not None:
        effect["candidate_admission"] = {"candidate_locator": str(candidate)}
    return extract_promote._seal_publication_target({"effect": effect}, _binding())


def test_legacy_run_only_prepare_fails_before_run_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extract_promote, "resolve_promotable_ingest_run",
        lambda *_a, **_k: pytest.fail("unbound request resolved a run"),
    )
    with pytest.raises(extract_promote.ExtractPromoteError) as exc:
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id="legacy"))
    assert exc.value.code == "publication_target_required"
    assert exc.value.status_code == 422


def test_http_prepare_requires_explicit_managed_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing
    from fastapi import FastAPI
    from apps.live_control_server.routes.extract_promote import router

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(router)

    async def call():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/live/extract-promote/prepare", json={"runId": "legacy"}
            )

    response = asyncio.run(call())
    assert response.status_code == 422
    assert response.json()["code"] == "publication_target_required"


def test_foreign_declared_source_world_rejects_before_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _id: _binding())
    monkeypatch.setattr(
        extract_promote, "resolve_promotable_ingest_run",
        lambda *_a, **_k: SimpleNamespace(world_id="foreign-world"),
    )
    with pytest.raises(extract_promote.ExtractPromoteError) as exc:
        extract_promote.prepare(
            ExtractPromotePrepareRequest(run_id="source-run", managed_world_id="managed-world")
        )
    assert exc.value.code == "source_world_mismatch"




def _historical_case(tmp_path, monkeypatch):
    from tests.test_cutover_native_governed_write import _original_extract_reader_case
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    from apps.live_control_server import config
    real_binding = recovery.authorize_current_target
    request, original, history, calls = _original_extract_reader_case(tmp_path, monkeypatch)
    monkeypatch.setattr(recovery, "authorize_current_target", real_binding)
    monkeypatch.setattr(config, "world_graph_authority_mode", lambda: config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    def forbidden(*args, **kwargs):
        pytest.fail("historical confirm entered mutable source/head or writer")
    for name in ("world_graph_root", "load_bound_extraction_run", "_assert_recap_semantics_at_confirm", "_assert_current_recap_ingest_context"):
        monkeypatch.setattr(extract_promote, name, forbidden)
    monkeypatch.setattr("apps.live_control_server.integrations.dungeonmind.world_graph_writes.confirm_extract_promote_via_dungeonmind", forbidden)
    return request, original, history, calls


def _historical_binding(*, native="eldyrwild", version=1):
    return VerifiedManagedWorldBinding(managed_world_id="managed-history", native_world_id=native,
        binding_version=version, source_root_relpath="retained-unused")


def test_confirm_rejects_remapped_binding_before_candidate_or_writer(monkeypatch, tmp_path):
    from apps.live_control_server.integrations.dungeonmind import historical_extract_recovery as recovery
    request, _, _, calls = _historical_case(tmp_path, monkeypatch)
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _: _historical_binding(native="other-world"))
    monkeypatch.setattr(recovery, "_bare_readers", lambda: pytest.fail("remapped target read private history"))
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        extract_promote.confirm(request)
    assert error.value.code == "publication_target_changed"
    assert calls == []


def test_confirm_rechecks_binding_at_original_receipt_disclosure(monkeypatch, tmp_path):
    request, _, _, calls = _historical_case(tmp_path, monkeypatch)
    seen = 0
    def resolve(_):
        nonlocal seen
        seen += 1
        return _historical_binding(version=1 if seen == 1 else 2)
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", resolve)
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        extract_promote.confirm(request)
    assert error.value.code == "publication_target_changed" and seen == 2
    assert calls == ["terminal", "parent", "source_revision"]


def test_confirm_receipt_uses_original_sealed_native_world(monkeypatch, tmp_path):
    request, original, history, calls = _historical_case(tmp_path, monkeypatch)
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _: _historical_binding())
    receipt = extract_promote.confirm(request)
    assert receipt.world_id == request.review_package["effect"]["world_id"] == "eldyrwild"
    assert receipt.committed_revision_id == history.publication.published_revision_id
    assert receipt.accepted_assertion_ids == [item.assertion_id for item in original.accepted_assertions]
    assert receipt.outcome == "already_applied" and receipt.head_advanced is False
    assert calls == ["terminal", "parent", "source_revision"]


def test_recap_confirm_replay_never_reopens_current_head_or_writes(monkeypatch, tmp_path):
    request, _, history, calls = _historical_case(tmp_path, monkeypatch)
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _: _historical_binding())
    first = extract_promote.confirm(request)
    second = extract_promote.confirm(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.outcome == second.outcome == "already_applied"
    assert first.committed_revision_id == history.publication.published_revision_id
    assert calls == ["terminal", "parent", "source_revision"] * 2


def test_http_classic_prepare_retired_after_target_admission(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes.extract_promote import router
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _: _historical_binding())
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", lambda *a, **k: pytest.fail("retired prepare opened run"))
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post("/api/live/extract-promote/prepare", json={"runId": "retained-run", "managedWorldId": "managed-history"})
    assert response.status_code == 410
    assert response.json()["code"] == "classic_extract_prepare_retired"



@pytest.mark.parametrize("path", ["/api/live/extract-promote/prepare", "/api/live/extract-promote/confirm"])
def test_classic_extract_preserves_hosted_policy_denial(monkeypatch, path):
    from apps.live_control_server.main import create_app
    from apps.live_control_server.services.hosted_auth import HOSTED_WORLD_ROUTE_POLICY_ERROR
    from tests.test_hosted_auth import _AsyncASGITestClient, _resolver, DmsPrincipal
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setenv("AUTH_TRUSTED_FRONTEND_ORIGINS", "https://buddy.dungeonmind.net")
    app = create_app()
    app.state.dms_principal_resolver = _resolver(DmsPrincipal(subject="synthetic-owner"))
    response = _AsyncASGITestClient(app).post(path, json={}, headers={"Origin": "https://buddy.dungeonmind.net"})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == HOSTED_WORLD_ROUTE_POLICY_ERROR
