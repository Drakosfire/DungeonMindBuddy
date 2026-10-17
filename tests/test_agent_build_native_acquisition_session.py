"""Owning ordinary SDK/APP lifetime; native conformance lives in reviewed-source-wave tests."""

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from apps.live_control_server.integrations.dungeonmind import (
    reviewed_source_wave,
    selected_observation_reads,
)
from graph_memory.interaction import expansion_executor
from tests.test_agent_build_jev_ordinary_harness import (
    ordinary_case,
    DecisionWire,
    WriterWire,
    build_case as _build_case,
)
from tests.test_build_jev_read_batches import BatchDecisions
from tests.test_build_jev_estimated_continuations import counter
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def install_wave(monkeypatch, harness, *, fail=False):
    events, handles, graph_services, source_services = [], [], [], []
    original_graph = selected_observation_reads.select_observations_direct
    original_source = expansion_executor.execute_read_graph_source

    @contextmanager
    def wave(services, request):
        assert request.world_id == "native-build-world"
        assert request.revision_pin == "native-rev-3" and request.admissibility == "gm"
        assert request.source_revision_id == "source-rev-one"
        handle = SimpleNamespace(
            original=services, request=request.model_copy(deep=True), active=True
        )
        handles.append(handle)
        events.append("open")
        try:
            yield handle
        finally:
            handle.active = False
            events.append("close")

    def graph(services, request):
        assert services is handles[-1] and services.active
        graph_services.append(services)
        adapter = harness.adapter
        before = len(adapter._broker_execution().events)
        assert not adapter.authorize(
            {}
        )  # Refuse before claiming/appending or provider transport.
        assert len(adapter._broker_execution().events) == before
        with pytest.raises(ValueError, match="nested"):
            with adapter.build_native_acquisition(adapter._build_jev_driver):
                pass
        if fail:
            raise ValueError("synthetic native selection refusal")
        return original_graph(services.original, request)

    def source(arguments, *, receipt_version, native_services=None):
        assert native_services is handles[-1] and native_services.active
        source_services.append(native_services)
        return original_source(arguments, receipt_version=receipt_version)

    monkeypatch.setattr(reviewed_source_wave, "reviewed_source_wave", wave)
    monkeypatch.setattr(selected_observation_reads, "select_observations_direct", graph)
    monkeypatch.setattr(expansion_executor, "execute_read_graph_source", source)
    return events, handles, graph_services, source_services


def test_one_native_session_reaches_graph_and_source_then_closes_before_sdk(
    build_case, monkeypatch, tmp_path
):
    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = BatchDecisions(), WriterWire()
    harness = BuildJevHarness(
        decision_transport=decisions, writer_transport=writer, accounting=counter()
    )
    events, handles, graph_services, source_services = install_wave(
        monkeypatch, harness
    )
    result = execute(case, tmp_path, harness)
    assert result.answer.text == ("Frank believes the western gate is haunted.\n"
        "This answer uses partial retrieval and does not establish corpus completeness.")
    assert events == ["open", "close"] and not handles[0].active
    assert graph_services == source_services == handles
    assert reads == {"graph": 1, "source": 1} and len(writer.calls) == 1
    assert harness.adapter._build_native_acquisition_services is None
    assert harness.adapter.turn.status == "completed"


def test_native_failure_closes_session_without_fallback_or_writer(
    build_case, monkeypatch, tmp_path
):
    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = BatchDecisions(), WriterWire()
    harness = BuildJevHarness(
        decision_transport=decisions, writer_transport=writer, accounting=counter()
    )
    events, handles, _, source_services = install_wave(monkeypatch, harness, fail=True)
    with pytest.raises(Exception, match="could not be durably admitted"):
        execute(case, tmp_path, harness)
    assert events == ["open", "close"] and not handles[0].active
    assert harness.adapter._build_native_acquisition_services is None
    assert (
        reads == {"graph": 0, "source": 0} and not source_services and not writer.calls
    )


def test_new_turn_opens_fresh_session_and_default_mode_stays_separate(
    build_case, monkeypatch, tmp_path
):
    case, _ = ordinary_case(build_case, monkeypatch)
    harness = BuildJevHarness(
        decision_transport=DecisionWire(),
        writer_transport=WriterWire(),
        accounting=counter(),
    )
    events, handles, _, _ = install_wave(monkeypatch, harness)
    execute(case, tmp_path, harness)
    source, request, bootstrap = case
    second = (source, request.model_copy(update={"turn_id": str(uuid4())}), bootstrap)
    execute(second, tmp_path, harness)
    assert events == ["open", "close", "open", "close"]
    assert handles[0] is not handles[1] and all(not h.active for h in handles)
    # Source-only intent needs no native context even with an admitted batch policy.
    from apps.live_control_server.services.build_jev_transitions import (
        AcquisitionIntent,
        ReadAction,
    )

    adapter = harness.adapter
    driver = SimpleNamespace(
        step=AcquisitionIntent(
            actions=(
                ReadAction(
                    id="saved:1:1",
                    label="Saved",
                    kind="saved_build_section",
                    unit_ids=("saved:1:1",),
                ),
            )
        )
    )
    adapter._build_jev_driver = driver
    with adapter.build_native_acquisition(driver):
        assert adapter._build_native_acquisition_services is None
    assert len(handles) == 2


@pytest.fixture
def source_case(tmp_path, monkeypatch):
    from tests.test_batched_admitted_source_reads import setup

    yield from setup.__wrapped__(tmp_path, monkeypatch)


def test_real_source_executor_forwards_bound_services_without_reopening(
    source_case, monkeypatch
):
    from unittest.mock import Mock
    from apps.live_control_server.services import world_graph_retrieval
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads
    from graph_memory.interaction.session import (
        GraphRetrievalSession,
        SessionSnapshot,
        SourceAnchorState,
    )
    from graph_memory.interaction.session_store import create_session

    f = source_case
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:test",
            campaign_id="",
            revision_id="rev:test",
            scope_mode="world",
        ),
        source_anchors=[
            SourceAnchorState(anchor_id=r.anchor_id, readable=True) for r in f.requests
        ],
    )
    create_session(session)
    reopen = Mock(
        side_effect=AssertionError("bound source batch must not recreate services")
    )
    monkeypatch.setattr(world_graph_reads, "direct_services_from_config", reopen)
    monkeypatch.setattr(
        world_graph_retrieval, "_require_mounted_native_read", lambda *_: None
    )
    monkeypatch.setattr(expansion_executor, "artifact_data_root", lambda **_: f.root)
    actual = expansion_executor.execute_read_graph_source(
        {
            "retrievalSessionId": session.id,
            "anchorIds": [r.anchor_id for r in f.requests],
            "maxChars": 4000,
        },
        receipt_version=2,
        native_services=f.services,
    )
    reopen.assert_not_called()
    f.resolve.assert_called_once()
    assert [x["result"]["content"] for x in actual["reads"]] == [
        "first line",
        "second line",
    ]
    assert all(x["receipt"] is not None for x in actual["reads"])
    assert all(a.opened for a in session.source_anchors)


@pytest.mark.parametrize(
    "field", ["source_artifact_id", "source_revision_id", "world_id", "graph_revision"]
)
def test_mutated_source_binding_refuses_before_native_session(
    build_case, monkeypatch, tmp_path, field
):
    from dataclasses import replace

    class RetargetedHarness(BuildJevHarness):
        @staticmethod
        def _acquire(adapter, driver):
            changed = dict(adapter.bootstrap.build_source_discovery)
            changed[field] = "foreign"
            adapter.bootstrap = replace(
                adapter.bootstrap, build_source_discovery=changed
            )
            return BuildJevHarness._acquire(adapter, driver)

    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = BatchDecisions(), WriterWire()
    harness = RetargetedHarness(
        decision_transport=decisions, writer_transport=writer, accounting=counter()
    )
    events, handles, _, _ = install_wave(monkeypatch, harness)
    with pytest.raises(Exception, match="could not complete safely"):
        execute(case, tmp_path, harness)
    assert not events and not handles and not writer.calls
    assert reads == {"graph": 0, "source": 0}
