from __future__ import annotations

import hashlib
import json
import multiprocessing
from dataclasses import dataclass
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


SOURCE = "The Azure Reach is a continent at the edge of reality.\nAsterport is a city.\n"


def _registered_source(root: Path):
    record = create_workspace_document(
        root,
        title="The City of Asterport",
        campaign_id="azure-reach",
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
    run_id = "run-worldbuilding"
    status = SimpleNamespace(value="reviewable")


@pytest.mark.parametrize("profile_version", ["1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11"])
def test_generationengine_execution_pins_exact_source_profile_and_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile_version: str,
) -> None:
    from apps.live_control_server.services import worldbuilding_ge_execution as service

    committed, artifact = _registered_source(tmp_path)
    expected_sha = artifact.content_sha256
    assert expected_sha
    captured: list[Any] = []
    _FakeBoundedClient.instances.clear()
    monkeypatch.setattr(service, "BoundedRecapPassClient", _FakeBoundedClient)
    monkeypatch.setattr(service, "run_production_extraction", lambda request: captured.append(request) or SimpleNamespace(run=_FakeRun(), failure_kind=None, diagnostics=[]))

    result = service.run_gazetteer_with_generation_engine(
        repo_root=tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        document_id=committed.document_id,
        document_revision=committed.revision,
        expected_content_sha256=expected_sha,
        profile_version=profile_version,
    )

    assert result.run.run_id == "run-worldbuilding"
    request = captured[0]
    assert request.source.source_artifact_id == artifact.source_artifact_id
    assert request.source.source_sha256 == expected_sha
    assert request.source.source_text == SOURCE
    assert (request.profile_id, request.profile_version) == (
        "worldbuilding_gazetteer_v1",
        profile_version,
    )
    assert request.model_id == "deepseek/deepseek-v4.1-flash"
    client = _FakeBoundedClient.instances[0]
    assert client.limits.provider == "openrouter"
    assert client.limits.model == "deepseek/deepseek-v4.1-flash"
    assert client.limits.max_calls == 8
    assert client.limits.max_output_tokens == 8192
    assert client.limits.edge_max_output_tokens == 8192
    assert client.kwargs["request_context_hashes"]["source_content"] == expected_sha
    assert client.kwargs["request_context_hashes"]["profile_identity"] == hashlib.sha256(
        f"worldbuilding_gazetteer_v1@{profile_version}".encode()
    ).hexdigest()
    ledger = next((tmp_path / "out/graph_memory/runs/extraction").rglob("inference_call_ledger.json"))
    ledger_json = json.loads(ledger.read_text(encoding="utf-8"))
    assert ledger_json["schema_version"] == "dmb_worldbuilding_generationengine_ledger_v1"
    assert ledger_json["document_revision"] == committed.revision
    assert ledger_json["source_sha256"] == expected_sha
    assert ledger_json["profile_id"] == f"worldbuilding_gazetteer_v1@{profile_version}"
    assert ledger_json["run_id"] == "run-worldbuilding"
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
        service.run_gazetteer_with_generation_engine(
            repo_root=tmp_path,
            source_artifact_id=artifact.source_artifact_id,
            document_id=committed.document_id,
            document_revision=committed.revision,
            expected_content_sha256="0" * 64,
            profile_version="1.6",
        )

    assert _FakeBoundedClient.instances == []
    assert not (tmp_path / "out/graph_memory/runs/extraction").exists()


def test_publication_binding_reads_pair_from_loaded_property_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys
    from types import ModuleType

    from apps.live_control_server.services import worldbuilding_graph_publication

    class _VocabularyRef:
        def __init__(self, vocabulary_id: str, revision: str, digest: str) -> None:
            self.vocabulary_id = vocabulary_id
            self.vocabulary_revision = revision
            self.catalog_sha256 = digest

        def model_dump(self, *, mode: str) -> dict[str, str]:
            assert mode == "json"
            return {
                "vocabulary_id": self.vocabulary_id,
                "vocabulary_revision": self.vocabulary_revision,
                "catalog_sha256": self.catalog_sha256,
            }

    object_ref = _VocabularyRef(
        "dungeonmind.dnd5e.world_object", "world-object-v6", "object-v6-digest"
    )
    property_ref = _VocabularyRef(
        "dungeonmind.dnd5e.world_property", "world-property-v4", "property-v4-digest"
    )
    object_module = ModuleType(
        "dungeonmind_dnd.application.world_object_vocabulary"
    )
    object_module.builtin_world_object_v6_vocabulary_ref = lambda: object_ref
    object_module.load_builtin_world_object_v6_vocabulary = lambda: SimpleNamespace(
        predicates=[SimpleNamespace(term="dnd5e:governs")]
    )
    property_module = ModuleType(
        "dungeonmind_dnd.application.world_property_vocabulary"
    )
    property_module.builtin_world_property_v4_vocabulary_ref = lambda: property_ref
    property_module.load_builtin_world_property_v4_vocabulary = lambda: SimpleNamespace(
        world_object_vocabulary=object_ref
    )
    monkeypatch.setitem(
        sys.modules,
        "dungeonmind_dnd.application.world_object_vocabulary",
        object_module,
    )
    monkeypatch.setitem(
        sys.modules,
        "dungeonmind_dnd.application.world_property_vocabulary",
        property_module,
    )

    binding = worldbuilding_graph_publication._worldbuilding_native_vocabulary_binding()

    assert binding["worldObjectVocabulary"] == object_ref.model_dump(mode="json")
    assert binding["worldPropertyVocabulary"] == property_ref.model_dump(mode="json")


@dataclass
class _FakeGenerationEngineFactory:
    calls: Any

    def __call__(self):
        from generationengine import GenerationClient

        return GenerationClient(
            text_providers={"openrouter": _SchemaAwareFakeProvider(self.calls)}
        )


class _SchemaAwareFakeProvider:
    def __init__(self, calls: Any) -> None:
        self.calls = calls

    async def generate(self, call: Any) -> Any:
        from generationengine.providers.base import TextGenerationResult

        with self.calls.get_lock():
            self.calls.value += 1
            ordinal = self.calls.value
        if ordinal == 1:
            text = "not-json"
        else:
            schema = call.json_schema or {}
            text = json.dumps({key: [] for key in schema.get("required", [])})
        return TextGenerationResult(
            text=text,
            provider_request_id=f"request-{ordinal}",
            provider_response_id=f"response-{ordinal}",
            response_model=call.model,
            input_tokens=5,
            output_tokens=3,
        )

    async def stream(self, call: Any):
        if False:
            yield call


@pytest.mark.parametrize("profile_version", ["1.5", "1.11"])
@pytest.mark.parametrize("fail_ledger", [False, True])
def test_real_ge_service_composition_tracks_conformance_and_fails_closed(
    tmp_path: Path,
    application_state_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
    fail_ledger: bool,
    profile_version: str,
) -> None:
    from apps.live_control_server.services import worldbuilding_ge_execution as service
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run,
        get_reviewable_extraction_run,
    )
    from src.graph_memory.extraction.bounded_recap_execution import (
        BoundedRecapPassClient,
    )
    from src.graph_memory.ingestion.extraction_run import ExtractionRunStatus

    committed, artifact = _registered_source(tmp_path)
    provider_calls = multiprocessing.get_context("spawn").Value("i", 0)
    clients: list[BoundedRecapPassClient] = []
    results: list[Any] = []
    factory = _FakeGenerationEngineFactory(provider_calls)

    class InjectedBoundedClient(BoundedRecapPassClient):
        def __init__(self, limits: Any, **kwargs: Any) -> None:
            super().__init__(limits, engine_factory=factory, **kwargs)
            clients.append(self)

    real_runner = service.run_production_extraction

    def capture_runner_result(request: Any) -> Any:
        result = real_runner(request)
        results.append(result)
        return result

    monkeypatch.setattr(service, "BoundedRecapPassClient", InjectedBoundedClient)
    monkeypatch.setattr(service, "run_production_extraction", capture_runner_result)
    if fail_ledger:
        def fail_private_ledger(path: Path, payload: dict[str, Any]) -> None:
            raise service.WorldbuildingExecutionEvidenceError("simulated ledger failure")

        monkeypatch.setattr(service, "_write_private_json", fail_private_ledger)

    def perform_run() -> Any:
        return service.run_gazetteer_with_generation_engine(
            repo_root=tmp_path,
            source_artifact_id=artifact.source_artifact_id,
            document_id=committed.document_id,
            document_revision=committed.revision,
            expected_content_sha256=artifact.content_sha256 or "",
            profile_version=profile_version,
        )

    if fail_ledger:
        with pytest.raises(
            service.WorldbuildingExecutionEvidenceError,
            match="simulated ledger failure",
        ):
            perform_run()
    else:
        result = perform_run()
        assert result.run.status == ExtractionRunStatus.REVIEWABLE
        ledger = next(
            (tmp_path / "out/graph_memory/runs/extraction").rglob(
                "inference_call_ledger.json"
            )
        )
        ledger_payload = json.loads(ledger.read_text(encoding="utf-8"))
        assert ledger_payload["run_id"] == result.run.run_id
        assert ledger_payload["execution"]["attempt_counts"]["conformance_retries"] == {
            "total": 1,
            "known_total": 1,
            "complete": True,
        }
        assert ledger_payload["execution"]["attempt_counts"]["transport_retries"] == {
            "total": 0,
            "known_total": 0,
            "complete": True,
        }

    assert len(results) == 1
    original = results[0]
    execution = clients[0].ledger()
    assert provider_calls.value == execution["pass_invocation_count"] + 1
    assert execution["attempt_counts"]["conformance_retries"]["known_total"] == 1
    assert execution["attempt_counts"]["transport_retries"]["known_total"] == 0
    correction = execution["calls"][0]["attempt_evidence"]
    assert [item["kind"] for item in correction] == ["initial", "conformance"]

    if fail_ledger:
        root = service.artifact_data_root(tmp_path)
        failed = get_extraction_run(root, original.run.run_id)
        assert failed.status == ExtractionRunStatus.FAILED
        assert failed.lineage["usage_ledger_state"] == "missing"
        assert "inference_call_ledger_persistence_failed" in failed.diagnostics.errors
        with pytest.raises(GraphRunRegistryError, match="not reviewable"):
            get_reviewable_extraction_run(root, original.run.run_id)


def test_unknown_profile_rejects_before_source_or_provider_work(tmp_path, monkeypatch):
    from apps.live_control_server.services import worldbuilding_ge_execution as service
    def forbidden(*_args, **_kwargs):
        pytest.fail("Unsupported profile reached source or provider execution")
    monkeypatch.setattr(service, "load_registered_source_artifact_text", forbidden)
    monkeypatch.setattr(service, "BoundedRecapPassClient", forbidden)
    monkeypatch.setattr(service, "run_production_extraction", forbidden)
    with pytest.raises(service.WorldbuildingExecutionInputError, match="unsupported Gazetteer"):
        service.run_gazetteer_with_generation_engine(
            repo_root=tmp_path, source_artifact_id="missing", document_id="missing",
            document_revision=1, expected_content_sha256="0" * 64, profile_version="1.12",
        )
