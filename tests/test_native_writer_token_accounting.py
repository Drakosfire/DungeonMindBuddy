"""Prepared offline counts on exact native writer bytes; no live providers."""

import asyncio
from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from generationengine.text_dispatch import PreparedTextDispatch

from application_state.agent_conversation.native_execution import (
    NativeWriterEstimatedBudgetV1,
)
from application_state.agent_conversation import types as t
from apps.live_control_server.services.plan_source_turn import _native_writer_budget
from apps.live_control_server.services.plan_jev_writer import authorize_native_writer
from apps.live_control_server.services.build_jev_writer import (
    WriterCapacityError,
    role_budget,
)
from tests.test_build_jev_estimated_continuations import counter
from tests.test_surface_native_execution import component, execution
from tests.test_surface_native_writer import actual_sdk_request


@pytest.fixture
def publication_lane(application_state_dsn, tmp_path, monkeypatch):
    from tests.test_source_statements import make_lane

    return make_lane(tmp_path, monkeypatch, narrow=True)


class AdmissionReached(Exception):
    pass


def writer_case(*, text="A source-local detail.", schema=None):
    accounting = counter()
    context, record = component("build", unavailable=True)
    budget = _native_writer_budget(role_budget() | {"model": "gpt-6-luna"}, accounting)
    policy = record.policy.model_copy(
        update={
            "controller_continuation_accounting": t.BuildControllerContinuationAccountingV4.model_validate(
                accounting.descriptor
            ),
            "writer_context_budget": budget,
        }
    )
    record = execution(context.context_receipt_sha256, policy)
    # The official SDK supplies its real serialized request; the synthetic frame
    # here tests host accounting only. HTTP tests below prove APP/source admission.
    raw = asyncio.run(actual_sdk_request({"text": text, "schema_test": schema},output_limit=None))
    prepared = PreparedTextDispatch(
        str(uuid4()),
        "openai",
        "responses",
        "gpt-6-luna",
        "POST",
        "https://api.openai.com/v1/responses",
        raw.encode(),
        sha256(raw.encode()).hexdigest(),
        len(raw.encode()),
    )
    captured = []

    def append(*args, **kwargs):
        captured.append(args[2])
        raise AdmissionReached

    adapter = SimpleNamespace(
        _broker_execution=lambda: record,
        _build_jev_accounting=accounting,
        budget={"estimator": "utf8_json_bytes_plus_64_per_node_v1"},
        fence=SimpleNamespace(append=append),
    )
    rules = SimpleNamespace(
        native=SimpleNamespace(record=SimpleNamespace(revision=1)), authoring=None
    )
    return SimpleNamespace(
        adapter=adapter,
        record=record,
        prepared=prepared,
        expected=json.loads(raw),
        captured=captured,
        rules=rules,
        accounting=accounting,
    )


def invoke(case):
    return authorize_native_writer(
        case.adapter, case.rules, {}, case.prepared, case.expected, {}
    )


def test_large_sdk_input_uses_complete_token_estimate_not_utf8_byte_refusal():
    case = writer_case(text="A sufficiently described source-local episode. " * 3500)
    assert len(case.prepared.body) > 128000
    with pytest.raises(AdmissionReached):
        invoke(case)
    (event,) = case.captured
    assert event.input_accounting_kind == "estimated_token_count"
    assert event.input_estimator == case.accounting.descriptor["policy"]
    assert event.input_tokens == case.accounting.estimate(case.expected)
    assert event.input_tokens + event.output_token_reserve <= 128000
    assert event.envelope_sha256 == case.prepared.body_sha256
    assert event.output_token_reserve == 0
    assert "max_output_tokens" not in case.expected
    assert case.record.policy.writer_context_budget.context_limit_tokens is None
    assert case.prepared.body.decode().find("source-local episode") >= 0


@pytest.mark.parametrize(
    "failure", ["missing", "version", "raising", "digest", "body"]
)
def test_unavailable_accounting_or_changed_sdk_input_never_admits(failure):
    case = writer_case()
    if failure == "missing":
        case.adapter._build_jev_accounting = None
    elif failure == "version":
        case.adapter._build_jev_accounting = replace(
            case.accounting, tokenizer_version="different"
        )
    elif failure == "raising":

        def unavailable(_):
            raise ValueError("synthetic missing prepared counter")

        case.adapter._build_jev_accounting = replace(
            case.accounting, count_tokens=unavailable
        )
    elif failure == "digest":
        case.prepared = replace(case.prepared, body_sha256="0" * 64)
    elif failure == "body":
        case.expected = case.expected | {"instructions": "changed"}
    with pytest.raises(ValueError):
        invoke(case)
    assert not case.captured


def test_instructions_and_output_schema_are_counted_before_admission():
    case = writer_case()
    # Preserve SDK body identity while changing the actual counted instruction
    # and schema payload. Count sees the complete object, not evidence alone.
    value = case.expected | {
        "instructions": "Specific instructions. " * 6000,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "large_schema",
                "schema": {
                    "type": "object",
                    "properties": {str(i): {"type": "string"} for i in range(200)},
                },
            }
        },
    }
    raw = json.dumps(value, ensure_ascii=False).encode()
    case.expected = value
    case.prepared = replace(
        case.prepared, body=raw, body_sha256=sha256(raw).hexdigest(), body_size=len(raw)
    )
    with pytest.raises(AdmissionReached):
        invoke(case)
    assert case.captured[0].input_tokens == case.accounting.estimate(value)
    assert case.captured[0].input_tokens > case.accounting.estimate(value["input"])


def test_ordinary_large_native_source_answers_with_estimated_authorization(
    publication_lane, tmp_path, monkeypatch
):
    from tests.test_surface_native_build_ordinary import _fresh_case

    text = "# Episode\nThe source describes a source-local episode.\n" + (
        "The explorers observed an unfamiliar landmark and recorded its appearance.\n"
        * 2100
    )
    case = _fresh_case(
        publication_lane,
        tmp_path,
        monkeypatch,
        None,
        False,
        False,
        False,
        native_body="direct_support",
        direct_source=True,
        native_source_text=text,
    )
    record = case.turn.graph_context_execution
    assert isinstance(
        record.policy.writer_context_budget, NativeWriterEstimatedBudgetV1
    )
    from application_state.agent_conversation.native_execution import NATIVE_WRITER_TYPES
    (event,) = [e for e in record.events if type(e) in NATIVE_WRITER_TYPES]
    raw = case.writer.calls[0].content
    assert len(raw) > 128000
    assert event.input_tokens == counter().estimate(json.loads(raw))
    assert event.output_token_reserve == 0
    assert "max_output_tokens" not in json.loads(raw)
    assert event.input_accounting_kind == "estimated_token_count"
    assert (
        case.turn.status == "completed" and case.turn.completion.native_body_citations
    )
    # Reload and altered policy still go through the owning concrete validator.
    assert (
        type(record).model_validate_json(record.model_dump_json(by_alias=True))
        == record
    )
    for mutation in (
        {"input_accounting_kind": "conservative_upper_bound"},
        {"input_estimator": "utf8_json_bytes_plus_64_per_node_v1"},
        {"input_tokens": 0},
        {"output_token_reserve": 4097},
    ):
        changed = record.model_copy(
            update={
                "events": [
                    e.model_copy(update=mutation) if e == event else e
                    for e in record.events
                ]
            }
        )
        with pytest.raises(ValueError):
            type(record).model_validate_json(changed.model_dump_json(by_alias=True))


def test_missing_counter_retains_a_context_preparation_diagnostic(
    tmp_path, monkeypatch
):
    from apps.live_control_server.services.build_failure_diagnostic import failure_code
    from apps.live_control_server.services.build_jev_writer import WriterAccountingError
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness

    monkeypatch.setattr(
        "apps.live_control_server.services.build_failure_diagnostic.artifact_data_root",
        lambda: tmp_path,
    )
    observations = []
    adapter = SimpleNamespace(
        turn=SimpleNamespace(turn_id=uuid4(), attempt=1),
        context_capture=SimpleNamespace(observe=observations.append),
    )
    try:
        raise RuntimeError("SDK wrapper") from WriterAccountingError(
            "prepared counter unavailable"
        )
    except RuntimeError as exc:
        BuildJevHarness()._capture_failure(adapter, exc)
    (event,) = observations
    assert (
        event["phase"] == "context_build"
        and event["stage"] == "writer_context_preparation"
    )
    assert event["code"] == "build_writer_accounting_unavailable"
    assert event["cause_type"] == "WriterAccountingError"
    assert (
        failure_code(ValueError("build_writer_accounting_unavailable"))
        == "build_execution_exception"
    )


def test_native_writer_has_no_artificial_128k_token_ceiling():
    case=writer_case()
    case.adapter._build_jev_accounting=replace(case.accounting,count_tokens=lambda _:256000)
    with pytest.raises(AdmissionReached):invoke(case)
    assert case.captured[0].input_tokens > 128000
    assert case.captured[0].output_token_reserve == 0


def test_native_writer_refuses_a_silently_reintroduced_output_cap():
    case=writer_case()
    value=case.expected | {'max_output_tokens':4096}
    raw=json.dumps(value).encode()
    case.expected=value
    case.prepared=replace(case.prepared,body=raw,body_sha256=sha256(raw).hexdigest(),body_size=len(raw))
    with pytest.raises(ValueError,match='output parameter'):invoke(case)
    assert not case.captured
