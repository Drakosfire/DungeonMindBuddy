from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from apps.live_control_server.services.source_artifact_registry import (
    create_source_artifact_from_workspace_document,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    mark_workspace_document_committed,
)


SOURCE = "The Elderwyld is a continent on the edge of reality.\nMirathorn is a city.\n"


def _registered_source(root: Path):
    record = create_workspace_document(
        root,
        title="The City of Mirathorn",
        campaign_id="elderwyld",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    path = root / (record.target_relpath or "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SOURCE, encoding="utf-8")
    committed = mark_workspace_document_committed(root, record.document_id)
    artifact = create_source_artifact_from_workspace_document(
        root,
        document_id=committed.document_id,
        expected_revision=committed.revision,
    )
    return committed, artifact


class _FakeBoundedClient:
    instances: list["_FakeBoundedClient"] = []

    def __init__(self, limits: Any, **kwargs: Any) -> None:
        self.limits = limits
        self.kwargs = kwargs
        self.instances.append(self)

    def ledger(self) -> dict[str, Any]:
        return {"pass_invocation_count": 6, "calls": []}


class _FakeRun:
    run_id = "run-mirathorn"
    status = SimpleNamespace(value="reviewable")


def test_generationengine_execution_pins_exact_source_profile_and_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services import worldbuilding_ge_execution as service

    committed, artifact = _registered_source(tmp_path)
    expected_sha = artifact.content_sha256
    assert expected_sha
    captured: list[Any] = []
    _FakeBoundedClient.instances.clear()
    monkeypatch.setattr(service, "BoundedRecapPassClient", _FakeBoundedClient)
    monkeypatch.setattr(service, "run_production_extraction", lambda request: captured.append(request) or SimpleNamespace(run=_FakeRun(), failure_kind=None, diagnostics=[]))

    result = service.run_gazetteer_15_with_generation_engine(
        repo_root=tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        document_id=committed.document_id,
        document_revision=committed.revision,
        expected_content_sha256=expected_sha,
    )

    assert result.run.run_id == "run-mirathorn"
    request = captured[0]
    assert request.source.source_artifact_id == artifact.source_artifact_id
    assert request.source.source_sha256 == expected_sha
    assert request.source.source_text == SOURCE
    assert (request.profile_id, request.profile_version) == (
        "worldbuilding_gazetteer_v1",
        "1.5",
    )
    assert request.model_id == "deepseek/deepseek-v4.1-flash"
    client = _FakeBoundedClient.instances[0]
    assert client.limits.provider == "openrouter"
    assert client.limits.model == "deepseek/deepseek-v4.1-flash"
    assert client.limits.max_calls == 8
    assert client.limits.max_output_tokens == 8192
    assert client.limits.edge_max_output_tokens == 8192
    assert client.kwargs["request_context_hashes"]["source_content"] == expected_sha
    ledger = next((tmp_path / "out/graph_memory/runs/extraction").rglob("inference_call_ledger.json"))
    ledger_json = json.loads(ledger.read_text(encoding="utf-8"))
    assert ledger_json["schema_version"] == "dmb_worldbuilding_generationengine_ledger_v1"
    assert ledger_json["document_revision"] == committed.revision
    assert ledger_json["source_sha256"] == expected_sha
    assert ledger_json["run_id"] == "run-mirathorn"
    assert ledger.stat().st_mode & 0o777 == 0o600
    assert ledger.parent.stat().st_mode & 0o077 == 0


def test_generationengine_execution_rejects_digest_mismatch_before_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services import worldbuilding_ge_execution as service

    committed, artifact = _registered_source(tmp_path)
    _FakeBoundedClient.instances.clear()
    monkeypatch.setattr(service, "BoundedRecapPassClient", _FakeBoundedClient)

    with pytest.raises(service.WorldbuildingExecutionInputError):
        service.run_gazetteer_15_with_generation_engine(
            repo_root=tmp_path,
            source_artifact_id=artifact.source_artifact_id,
            document_id=committed.document_id,
            document_revision=committed.revision,
            expected_content_sha256="0" * 64,
        )

    assert _FakeBoundedClient.instances == []
    assert not (tmp_path / "out/graph_memory/runs/extraction").exists()
