"""The selected managed World is part of the reviewed publication authority."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from apps.live_control_server.models.extract_promote import (
    ExtractPromoteConfirmRequest,
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


def test_legacy_recap_run_reaches_selected_world_source_adoption_without_lineage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_text(
        '{"campaign_id":"campaign-a","session_id":"session-22","nodes":[]}',
        encoding="utf-8",
    )
    resolved = SimpleNamespace(
        world_id=None,
        source_domain="recap",
        ingest_context=None,
        campaign_id="campaign-a",
        session_id="session-22",
        sealed_source_uri="repo://historical/recap.md",
        candidate_graph_path=candidate,
        diagnostics=[],
        extraction_profile=None,
        registry_context_graph_path=None,
        source_artifact_id="artifact:recap:historical",
        source_revision_id=None,
    )
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _id: _binding())
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", lambda *_a, **_k: resolved)
    monkeypatch.setattr(extract_promote, "_recap_semantic_assessment", lambda _run: (None, None))
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _uri: None)
    def source_adoption(source_id: str):
        raise RuntimeError(f"historical run reached exact source adoption: {source_id}")

    monkeypatch.setattr(extract_promote, "_require_canonical_source_artifact", source_adoption)
    with pytest.raises(RuntimeError, match="artifact:recap:historical"):
        extract_promote.prepare(
            ExtractPromotePrepareRequest(
                run_id="historical-recap-run", managed_world_id="managed-world"
            )
        )


def test_confirm_rejects_remapped_binding_before_candidate_or_writer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        extract_promote, "_resolve_publication_target", lambda _id: _binding(native="other-world")
    )
    monkeypatch.setattr(
        extract_promote, "world_graph_root", lambda: pytest.fail("opened graph root")
    )
    request = ExtractPromoteConfirmRequest(review_package=_package(), assertion_ids=["a"])
    with pytest.raises(extract_promote.ExtractPromoteError) as exc:
        extract_promote.confirm(request)
    assert exc.value.code == "publication_target_changed"


def test_confirm_rechecks_binding_at_governed_write_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.services import candidate_graph_admission

    candidate = tmp_path / "candidate.json"
    candidate.write_text("{}", encoding="utf-8")
    request = ExtractPromoteConfirmRequest(
        review_package=_package(candidate=candidate), assertion_ids=["a"]
    )
    seen = 0

    def resolve(_id: str) -> VerifiedManagedWorldBinding:
        nonlocal seen
        seen += 1
        return _binding(version=1 if seen == 1 else 2)

    monkeypatch.setattr(extract_promote, "_resolve_publication_target", resolve)
    monkeypatch.setattr(extract_promote, "world_graph_root", lambda: tmp_path)
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: None)
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _uri: None)
    monkeypatch.setattr(extract_promote, "_assert_recap_semantics_at_confirm", lambda *_a: None)
    monkeypatch.setattr(
        config, "world_graph_authority_mode", lambda: config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setattr(
        candidate_graph_admission, "confirm_candidate_graph_admission",
        lambda **kwargs: kwargs["governed_confirm"](),
    )
    monkeypatch.setattr(
        world_graph_writes, "confirm_extract_promote_via_dungeonmind",
        lambda *_a, **_k: pytest.fail("binding drift reached governed writer"),
    )
    with pytest.raises(extract_promote.ExtractPromoteError) as exc:
        extract_promote.confirm(request)
    assert exc.value.code == "publication_target_changed"
    assert seen == 2


def test_confirm_receipt_uses_sealed_native_world(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.services import candidate_graph_admission

    candidate = tmp_path / "candidate.json"
    candidate.write_text("{}", encoding="utf-8")
    request = ExtractPromoteConfirmRequest(
        review_package=_package(candidate=candidate), assertion_ids=["a"]
    )
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _id: _binding())
    monkeypatch.setattr(extract_promote, "world_graph_root", lambda: tmp_path)
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: None)
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _uri: None)
    monkeypatch.setattr(extract_promote, "_assert_recap_semantics_at_confirm", lambda *_a: None)
    monkeypatch.setattr(
        config, "world_graph_authority_mode", lambda: config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setattr(
        candidate_graph_admission, "confirm_candidate_graph_admission",
        lambda **kwargs: kwargs["governed_confirm"](),
    )
    seen: list[str] = []

    def publish(request, **_kwargs):
        seen.append(request.review_package["effect"]["world_id"])
        return {
            "world_id": "native-world",
            "outcome": "committed",
            "published": True,
            "post_publication_verification": "passed",
            "committed_revision_id": "revision:committed",
            "accepted_assertion_ids": ["a"],
            "affected_object_ids": ["node:a"],
        }

    monkeypatch.setattr(world_graph_writes, "confirm_extract_promote_via_dungeonmind", publish)
    receipt = extract_promote.confirm(request)
    assert seen == ["native-world"]
    assert receipt.world_id == "native-world"
    assert receipt.committed_revision_id == "revision:committed"


def test_recap_confirm_replay_survives_head_advance_without_second_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.services import candidate_graph_admission, recap_ingest_context

    candidate = tmp_path / "candidate.json"
    candidate.write_text("{}", encoding="utf-8")
    context = {
        "schema": "dm_world_campaign_ingest_context_v1",
        "managed_world_id": "managed-world",
        "native_world_id": "native-world",
        "binding_version": 1,
        "campaign_id": "campaign-a",
        "head_revision_id": "revision:parent",
        "graph_schema": "dm_graph_v1",
        "graph_payload_sha256": "a" * 64,
    }
    package = extract_promote._seal_recap_ingest_context(
        _package(candidate=candidate), context
    )
    request = ExtractPromoteConfirmRequest(review_package=package, assertion_ids=["a"])
    monkeypatch.setattr(extract_promote, "_resolve_publication_target", lambda _id: _binding())
    monkeypatch.setattr(extract_promote, "world_graph_root", lambda: tmp_path)
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: None)
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _uri: None)
    monkeypatch.setattr(extract_promote, "_assert_recap_semantics_at_confirm", lambda *_a: None)
    monkeypatch.setattr(
        config, "world_graph_authority_mode", lambda: config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setattr(
        candidate_graph_admission, "confirm_candidate_graph_admission",
        lambda **kwargs: kwargs["governed_confirm"](),
    )

    class Snapshot:
        def __init__(self, head: str) -> None:
            self.head = head

        def as_lineage(self) -> dict[str, object]:
            return {**context, "head_revision_id": self.head}

    heads = iter(("revision:committed", "revision:committed"))
    monkeypatch.setattr(
        recap_ingest_context,
        "read_recap_ingest_context",
        lambda **_kwargs: Snapshot(next(heads)),
    )
    writes = 0

    def publish(_request, **_kwargs):
        nonlocal writes
        if writes:
            return {
                "world_id": "native-world",
                "outcome": "already_applied",
                "published": False,
                "committed_revision_id": "revision:committed",
                "accepted_assertion_ids": ["a"],
                "affected_object_ids": ["node:a"],
            }
        writes += 1
        return {
            "world_id": "native-world",
            "outcome": "committed",
            "published": True,
            "post_publication_verification": "passed",
            "committed_revision_id": "revision:committed",
            "accepted_assertion_ids": ["a"],
            "affected_object_ids": ["node:a"],
        }

    monkeypatch.setattr(world_graph_writes, "confirm_extract_promote_via_dungeonmind", publish)
    first = extract_promote.confirm(request)
    second = extract_promote.confirm(request)
    assert first.outcome == "committed"
    assert second.outcome == "already_applied"
    assert writes == 1
