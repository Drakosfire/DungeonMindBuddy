from __future__ import annotations

import asyncio
import builtins
import inspect
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from generationengine import (
    FailureCode,
    GenerationEngineError,
    InferenceFailure,
    InferenceObservation,
    ObservationState,
    TextRequest,
    TextResult,
)

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.live_agent_loop import process_live_query
from src.live_play import live_query_context

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_23"
TEST_MANIFEST_PATH = "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"


@pytest.fixture
def isolated_session_23(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in (
        "live_packet.json",
        "surface_layout.json",
        "current_state.json",
        "recap.md",
    ):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture
def client(isolated_session_23: Path) -> TestClient:
    return TestClient(create_app())


def test_context_lookup_returns_packet_with_admitted_and_rejected_evidence(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "context_lookup"
    assert body["answer"]
    assert body["mutations"] == []
    packet = body["context_packet"]
    assert packet
    assert packet["admitted_evidence"], "expected admitted evidence"
    assert isinstance(packet["rejected_evidence"], list)

    policy = body["provenance"].get("grounding_prompt_policy") or {}
    assert policy == {
        "uses_admitted_evidence": True,
        "forbids_rejected_support": True,
        "requires_evidence_id_citations": True,
        "read_only": True,
    }
    assert "grounded_prompt" not in body["provenance"]
    prompt = live_query_context.render_grounded_prompt(
        "What Session 22 outcomes matter for Session 23 prep?",
        packet,
    )
    assert "ADMITTED EVIDENCE" in prompt
    assert "REJECTED EVIDENCE" in prompt
    assert "Do not use rejected evidence as support." in prompt
    assert "Never claim write capability in this response path; it is read-only." in prompt


def test_context_lookup_citations_reference_admitted_evidence(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    packet = body["context_packet"]
    admitted_ids = {row.get("evidence_id") for row in packet["admitted_evidence"]}
    rejected_ids = {row.get("evidence", {}).get("evidence_id") for row in packet["rejected_evidence"]}
    citations = body.get("citations") or []
    assert citations, "expected at least one citation"
    for row in citations:
        evidence_id = row["evidence_id"]
        assert evidence_id in admitted_ids
        assert evidence_id not in rejected_ids
    assert "ingest_status" not in {row.get("source_role") for row in packet["admitted_evidence"]}
    assert "audit" not in {row.get("authority") for row in packet["admitted_evidence"]}


def test_ingest_question_surfaces_rejected_reason_codes(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "After ingesting Session 22 raw notes, what Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    packet = body["context_packet"]
    assert packet["rejected_evidence"]
    assert all("reason_code" in row for row in packet["rejected_evidence"])


def test_context_lookup_mutation_request_is_refused_read_only(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What should we prep next, and can you create a new Mireward location hub and write it?",
            "manifest_path": TEST_MANIFEST_PATH,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "context_lookup"
    assert body["mutations"] == []
    assert "read-only" in body["answer"].lower()


def test_context_lookup_missing_manifest_is_truthful(client: TestClient) -> None:
    response = client.post(
        "/api/live/query",
        json={
            "campaign_id": "longmont-c2",
            "session": 23,
            "mode": "live",
            "text": "What Session 22 outcomes matter for Session 23 prep?",
            "manifest_path": "evals/c2_live_prep/benchmarks/does_not_exist.json",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "missing_context_manifest"
    assert body["context_packet"] is None
    assert "cannot ground this answer" in body["answer"].lower()


def test_context_lookup_does_not_read_gold_or_dogfood_trace(
    isolated_session_23: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_open = builtins.open

    def guarded_open(path, *args, **kwargs):
        lowered = str(path).lower()
        if "gold" in lowered:
            raise AssertionError("live query must not read gold")
        if "c2s23_dogfood_" in lowered or "c2s23_dogfood_planner_summary" in lowered:
            raise AssertionError("live query must not read dogfood traces")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)
    before_events = (isolated_session_23 / "event_log.jsonl").read_text(encoding="utf-8")
    before_jobs = (isolated_session_23 / "job_queue.jsonl").read_text(encoding="utf-8")
    body = process_live_query(
        "What Session 22 outcomes matter for Session 23 prep?",
        base=isolated_session_23,
        root=ROOT,
        request_manifest_path=TEST_MANIFEST_PATH,
    )
    assert body["mode"] == "context_lookup"
    assert (isolated_session_23 / "event_log.jsonl").read_text(encoding="utf-8") == before_events
    assert (isolated_session_23 / "job_queue.jsonl").read_text(encoding="utf-8") == before_jobs


def test_context_lookup_without_manifest_defaults_is_truthful_when_dogfood_off(
    isolated_session_23: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_C2S23_DOGFOOD_DEFAULTS", raising=False)
    packet_path = isolated_session_23 / "live_packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    for key in ("planning_manifest_path", "active_manifest_path", "manifest_path"):
        packet.pop(key, None)
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    body = process_live_query(
        "What Session 22 outcomes matter for Session 23 prep?",
        base=isolated_session_23,
        root=ROOT,
    )
    assert body["mode"] == "context_lookup"
    assert body["status"] == "missing_context_manifest"
    assert body["context_packet"] is None


def test_context_lookup_stubbed_llm_path_emits_citations(
    isolated_session_23: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_llm_answer(
        *,
        question: str,
        packet: dict[str, object],
        root: Path,
        world_graph_prompt_block: str | None = None,
    ) -> tuple[str | None, list[str]]:
        del world_graph_prompt_block
        admitted = list(packet.get("admitted_evidence") or [])
        assert admitted, "expected admitted evidence for stubbed llm test"
        evidence_id = str(admitted[0].get("evidence_id") or "ev-unknown")
        return f"Stub grounded answer citing [{evidence_id}].", []

    monkeypatch.setattr(live_query_context, "_run_llm_grounded_answer", _fake_llm_answer)
    body = process_live_query(
        "What Session 22 outcomes matter for Session 23 prep?",
        base=isolated_session_23,
        root=ROOT,
        request_manifest_path=TEST_MANIFEST_PATH,
    )
    assert body["mode"] == "context_lookup"
    assert body["status"] == "ok"
    assert "stub grounded answer citing" in body["answer"].lower()
    assert body["citations"], "expected citations from stubbed llm answer"
    assert "llm_grounding_call_failed" not in (body.get("warnings") or [])


def _grounding_packet() -> dict[str, object]:
    return {
        "admitted_evidence": [
            {
                "evidence_id": "ev-1",
                "source_role": "play_recap",
                "authority": "canon_play",
                "path": "x.md",
                "line_start": 1,
                "line_end": 1,
                "unit_id": "u",
                "text_excerpt": "Tripod is a siege scout.",
            }
        ],
        "rejected_evidence": [],
    }


def _text_result(text: str | None) -> TextResult:
    return TextResult(
        text=text,
        observation=InferenceObservation(
            latency_ms=0,
            retry_count=0,
            state=ObservationState.COMPLETED,
        ),
    )


class _RecordingGE:
    def __init__(self, outcome: str | None | BaseException = "Grounded [ev-1].") -> None:
        self.outcome = outcome
        self.requests: list[TextRequest] = []

    async def generate_text(self, request: TextRequest) -> TextResult:
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return _text_result(self.outcome)


def _generation_error(code: FailureCode, message: str) -> GenerationEngineError:
    failure = InferenceFailure.from_code(code, message)
    observation = InferenceObservation(
        latency_ms=0,
        retry_count=0,
        state=ObservationState.FAILED,
        failure_code=code,
    )
    return GenerationEngineError(failure, observation)


def _configure_grounding_test(
    monkeypatch: pytest.MonkeyPatch,
    client: _RecordingGE,
    *,
    model: str = "gpt-5.3-chat-latest",
) -> None:
    monkeypatch.setattr(live_query_context, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setattr(live_query_context, "_load_api_key", lambda: "sk-test")
    monkeypatch.setattr(live_query_context, "_live_query_model", lambda _root: model)
    monkeypatch.setattr(live_query_context.GenerationClient, "from_env", lambda: client)


def test_llm_grounded_answer_uses_exact_generationengine_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RecordingGE("  Grounded [ev-1].  ")
    _configure_grounding_test(monkeypatch, client)

    answer, warnings = live_query_context._run_llm_grounded_answer(
        question="What about the Tripod?",
        packet=_grounding_packet(),
        root=ROOT,
    )
    assert answer == "Grounded [ev-1]."
    assert warnings == []
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.user_prompt == live_query_context.render_grounded_prompt(
        "What about the Tripod?", _grounding_packet(), world_graph_prompt_block=None
    )
    assert request.system_prompt is None
    assert request.provider == "openai"
    assert request.model == "gpt-5.3-chat-latest"
    assert request.profile is None
    assert request.temperature is None
    assert request.max_output_tokens == 400
    assert request.json_schema is None
    assert request.schema_name is None


def test_llm_grounded_answer_forwards_alternate_buddy_model(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _RecordingGE()
    _configure_grounding_test(monkeypatch, client, model="gpt-4o-mini")
    live_query_context._run_llm_grounded_answer(
        question="What about the Tripod?", packet=_grounding_packet(), root=ROOT
    )
    assert client.requests[0].model == "gpt-4o-mini"


def test_llm_grounded_answer_missing_key_is_silent_and_constructs_no_ge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(live_query_context, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setattr(live_query_context, "_load_api_key", lambda: None)

    def _boom() -> None:
        raise AssertionError("GE must not be constructed without product credentials")

    monkeypatch.setattr(live_query_context.GenerationClient, "from_env", _boom)
    assert live_query_context._run_llm_grounded_answer(
        question="What about the Tripod?", packet=_grounding_packet(), root=ROOT
    ) == (None, [])


def test_llm_grounded_answer_maps_configuration_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _RecordingGE(
        _generation_error(FailureCode.CONFIGURATION_UNAVAILABLE, "OpenAI client unavailable.")
    )
    _configure_grounding_test(monkeypatch, client)
    assert live_query_context._run_llm_grounded_answer(
        question="What about the Tripod?", packet=_grounding_packet(), root=ROOT
    ) == (None, ["llm_client_unavailable"])


def test_llm_grounded_answer_uses_safe_normalized_failure_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RecordingGE(_generation_error(FailureCode.PROVIDER_ERROR, "Provider request failed."))
    _configure_grounding_test(monkeypatch, client)
    answer, warnings = live_query_context._run_llm_grounded_answer(
        question="What about the Tripod?", packet=_grounding_packet(), root=ROOT
    )
    assert answer is None
    assert warnings == ["llm_grounding_call_failed:Provider request failed."]
    assert "sk-secret" not in warnings[0]
    assert "openai.com" not in warnings[0]


def test_live_query_ge_failure_uses_deterministic_grounded_fallback(
    isolated_session_23: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RecordingGE(_generation_error(FailureCode.PROVIDER_ERROR, "Provider request failed."))
    _configure_grounding_test(monkeypatch, client)

    body = process_live_query(
        "What Session 22 outcomes matter for Session 23 prep?",
        base=isolated_session_23,
        root=ROOT,
        request_manifest_path=TEST_MANIFEST_PATH,
    )

    assert body["status"] == "ok"
    assert body["answer"]
    assert body["citations"]
    assert "llm_grounding_call_failed:Provider request failed." in body["warnings"]
    assert body.get("mutations") in (None, [])


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_llm_grounded_answer_empty_result_uses_existing_fallback_warning(
    monkeypatch: pytest.MonkeyPatch,
    empty: str | None,
) -> None:
    client = _RecordingGE(empty)
    _configure_grounding_test(monkeypatch, client)
    assert live_query_context._run_llm_grounded_answer(
        question="What about the Tripod?", packet=_grounding_packet(), root=ROOT
    ) == (None, ["llm_empty_answer_fallback_used"])


def test_llm_grounded_answer_constructs_ge_inside_awaited_context_and_does_not_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(live_query_context, "load_dungeonmindbuddy_dotenv", lambda: None)
    monkeypatch.setattr(live_query_context, "_load_api_key", lambda: "sk-test")
    loops: list[asyncio.AbstractEventLoop] = []
    clients: list[_RecordingGE] = []

    def _from_env() -> _RecordingGE:
        loops.append(asyncio.get_running_loop())
        client = _RecordingGE()
        clients.append(client)
        return client

    monkeypatch.setattr(live_query_context.GenerationClient, "from_env", _from_env)
    for _ in range(2):
        assert live_query_context._run_llm_grounded_answer(
            question="What about the Tripod?", packet=_grounding_packet(), root=ROOT
        )[0] == "Grounded [ev-1]."
    assert len(loops) == 2
    assert len(clients) == 2
    assert clients[0] is not clients[1]


def test_llm_grounded_answer_is_safe_inside_active_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RecordingGE()
    _configure_grounding_test(monkeypatch, client)

    async def _inside_loop() -> tuple[str | None, list[str]]:
        return live_query_context._run_llm_grounded_answer(
            question="What about the Tripod?", packet=_grounding_packet(), root=ROOT
        )

    assert asyncio.run(_inside_loop()) == ("Grounded [ev-1].", [])


def test_live_query_source_uses_ge_and_keeps_eval_compatibility_helper() -> None:
    source = inspect.getsource(live_query_context)
    assert "from openai import OpenAI" not in source
    assert "responses.create(" not in source
    assert ".generate_text(" in source
    assert "def _extract_answer_text" in source

    telemetry_source = (
        ROOT / "evals/c2_live_prep/run_live_query_telemetry_trace.py"
    ).read_text(encoding="utf-8")
    assert "_extract_answer_text" in telemetry_source
