"""One metadata wave, unchanged body batches and integrity checks."""

from dataclasses import dataclass, replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.live_control_server.integrations.dungeonmind import world_graph_reads as reads
from apps.live_control_server.integrations.dungeonmind.source_anchor_wave import (
    source_anchor_wave,
)
from graph_memory.interaction import expansion_executor as executor
from graph_memory.interaction.session import (
    GraphRetrievalSession,
    SessionSnapshot,
    SourceAnchorState,
)
from graph_memory.interaction.session_store import create_session
from tests.test_batched_admitted_source_reads import setup as batch_setup


@pytest.fixture(name="setup")
def source_setup(tmp_path, monkeypatch):
    yield from batch_setup.__wrapped__(tmp_path, monkeypatch)


@dataclass(frozen=True)
class Services:
    binding: object
    bundle: object
    retrieval: object
    reviewed_source_wave: object = None
    source_anchor_wave: object = None


def wave_fixture(f, count=45):
    template = f.resolve.side_effect(
        SimpleNamespace(anchor_ids=(f.requests[0].anchor_id,))
    ).resolutions[0]
    ids = tuple(f"source-anchor:v1:wave-{i}" for i in range(count))
    result_rows = {
        key: SimpleNamespace(
            snapshot=f.snapshot,
            anchor_id=key,
            found=True,
            anchor=replace(template.anchor, anchor_id=key),
        )
        for key in ids
    }
    f.resolve.side_effect = lambda request: SimpleNamespace(
        snapshot=f.snapshot,
        resolutions=tuple(result_rows[key] for key in request.anchor_ids),
    )
    services = Services(f.services.binding, f.services.bundle, f.services.retrieval)
    requests = tuple(f.requests[0].model_copy(update={"anchor_id": key}) for key in ids)
    return services, requests, ids


def test_one_native_resolution_keeps_45_authorized_executor_receipts(
    setup, monkeypatch
):
    f = setup
    services, requests, ids = wave_fixture(f)
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:test",
            campaign_id="",
            revision_id="rev:test",
            scope_mode="world",
        ),
        source_anchors=[SourceAnchorState(anchor_id=key, readable=True) for key in ids],
    )
    create_session(session)
    direct_calls = Mock(
        side_effect=lambda reqs, **kwargs: reads.read_source_anchors_direct_v2(
            kwargs["native_services"], reqs, repo_root=f.root
        )
    )
    monkeypatch.setattr(
        executor.retrieval_service, "read_source_anchors_internal_v2", direct_calls
    )
    f.resolve.reset_mock()
    with source_anchor_wave(services, requests[0], ids) as bound:
        outputs = [
            executor.execute_read_graph_source(
                {
                    "retrievalSessionId": session.id,
                    "anchorIds": list(ids[start : start + 8]),
                    "maxChars": 4000,
                },
                receipt_version=2,
                native_services=bound,
            )
            for start in range(0, len(ids), 8)
        ]
        assert direct_calls.call_count == 6
        assert f.resolve.call_count == 1
    rows = [row for output in outputs for row in output["reads"]]
    assert len(rows) == 45
    assert [row["result"]["anchorId"] for row in rows] == list(ids)
    assert all(row["receipt"]["anchor_id"] == row["result"]["anchorId"] for row in rows)
    assert all(row["result"]["content"] == "first line" for row in rows)
    assert all(anchor.opened for anchor in session.source_anchors)
    with pytest.raises(reads.DirectWorldGraphReadError, match="closed"):
        reads.read_source_anchors_direct_v2(bound, requests[:8], repo_root=f.root)
    assert f.resolve.call_count == 1


@pytest.mark.parametrize(
    "fault", ["reordered", "missing", "world", "revision", "anchor"]
)
def test_bad_prefetch_returns_no_bound_services_or_body_reads(
    setup, fault, monkeypatch
):
    f = setup
    services, requests, ids = wave_fixture(f)
    original = f.resolve.side_effect

    def bad(request):
        result = original(request)
        if fault == "reordered":
            result.resolutions = result.resolutions[::-1]
        elif fault == "missing":
            result.resolutions = result.resolutions[:-1]
        elif fault in {"world", "revision"}:
            result.snapshot = SimpleNamespace(
                world_id="foreign" if fault == "world" else "world:test",
                revision_id="foreign" if fault == "revision" else "rev:test",
            )
        else:
            result.resolutions[0].anchor = replace(
                result.resolutions[0].anchor, anchor_id="foreign"
            )
        return result

    f.resolve.side_effect = bad
    monkeypatch.setattr(
        reads,
        "_source_anchor_read_from_resolution",
        lambda *a, **kw: pytest.fail("opened body"),
    )
    with pytest.raises(ValueError, match="identity differs"):
        with source_anchor_wave(services, requests[0], ids):
            pytest.fail("bad metadata was admitted")


def test_subsets_cannot_retarget_and_exception_closes_wave(setup):
    f = setup
    services, requests, ids = wave_fixture(f)
    with pytest.raises(LookupError):
        with source_anchor_wave(services, requests[0], ids) as bound:
            wave = bound.source_anchor_wave
            projection = reads._map_retrieval_context(requests[0], services.binding)
            for invalid in [("foreign",), (ids[0], ids[0])]:
                with pytest.raises(ValueError):
                    wave.resolve(projection, invalid)
            with pytest.raises(ValueError):
                wave.resolve(
                    SimpleNamespace(world_id="world:test", revision_pin="other"),
                    (ids[0],),
                )
            result = wave.resolve(projection, ids[:2])
            result.resolutions[0].anchor = None
            assert wave.resolve(projection, ids[:1]).resolutions[0].anchor is not None
            with pytest.raises(ValueError, match="nested"):
                with source_anchor_wave(bound, requests[0], ids):
                    pass
            raise LookupError("owner stopped")
    with pytest.raises(RuntimeError, match="closed"):
        wave.resolve(projection, ids[:1])


@pytest.mark.parametrize(
    "fault", ["foreign", "stale", "unreadable", "unadmitted", "duplicate", "inactive"]
)
def test_owner_rejects_invalid_acquisition_before_native_io(setup, monkeypatch, fault):
    from apps.live_control_server.services.agent_turn_service import (
        _PolicyExecutionAdapter,
    )

    f = setup
    _, requests, ids = wave_fixture(f)
    scope = SimpleNamespace(
        retrieval_session_id="placeholder", graph_revision="rev:test", campaign_id=None
    )
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:test",
            campaign_id="",
            revision_id="rev:test",
            scope_mode="world",
        ),
        source_anchors=[SourceAnchorState(anchor_id=key, readable=True) for key in ids],
    )
    create_session(session)
    scope.retrieval_session_id = session.id
    pins = {key: object() for key in ids}
    execution = SimpleNamespace(
        policy=SimpleNamespace(source_read_scope=scope),
        effective_source_pins=lambda: pins,
    )
    owner = SimpleNamespace(
        failure=None,
        fence=object(),
        last_provider_attempt_id="attempt",
        _broker_execution=lambda: execution,
        _broker_receipt=lambda: SimpleNamespace(
            graph_authority=SimpleNamespace(native_world_id="world:test")
        ),
    )
    if fault == "foreign":
        session.snapshot.world_id = "foreign"
    elif fault == "stale":
        session.snapshot.revision_id = "other"
    elif fault == "unreadable":
        session.source_anchors[0].readable = False
    elif fault == "unadmitted":
        pins.pop(ids[0])
    elif fault == "duplicate":
        ids = (*ids, ids[0])
    else:
        owner.last_provider_attempt_id = None
    monkeypatch.setattr(
        reads, "direct_services_from_config", lambda *a: pytest.fail("unauthorized IO")
    )
    with pytest.raises(ValueError, match="current admitted"):
        with _PolicyExecutionAdapter.source_read_acquisition(owner, ids):
            pass


def test_owner_installs_wave_and_clears_it_when_body_acquisition_stops(
    setup, monkeypatch
):
    from apps.live_control_server.services.agent_turn_service import (
        _PolicyExecutionAdapter,
    )

    f = setup
    services, requests, ids = wave_fixture(f)
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:test",
            campaign_id="",
            revision_id="rev:test",
            scope_mode="world",
        ),
        source_anchors=[SourceAnchorState(anchor_id=key, readable=True) for key in ids],
    )
    create_session(session)
    scope = SimpleNamespace(
        retrieval_session_id=session.id, graph_revision="rev:test", campaign_id=None
    )
    execution = SimpleNamespace(
        policy=SimpleNamespace(source_read_scope=scope),
        effective_source_pins=lambda: {key: object() for key in ids},
    )
    owner = SimpleNamespace(
        failure=None,
        fence=object(),
        last_provider_attempt_id="attempt",
        _broker_execution=lambda: execution,
        _broker_receipt=lambda: SimpleNamespace(
            graph_authority=SimpleNamespace(native_world_id="world:test")
        ),
    )
    monkeypatch.setattr(reads, "direct_services_from_config", lambda world: services)
    with pytest.raises(LookupError):
        with _PolicyExecutionAdapter.source_read_acquisition(owner, ids):
            bound = owner._build_native_acquisition_services
            assert bound.source_anchor_wave is not None
            results = reads.read_source_anchors_direct_v2(
                bound, requests[:8], repo_root=f.root
            )
            assert len(results) == 8 and all(
                row.result.content == "first line" for row in results
            )
            raise LookupError("body broker stopped")
    assert owner._build_native_acquisition_services is None
    with pytest.raises(reads.DirectWorldGraphReadError, match="closed"):
        reads.read_source_anchors_direct_v2(bound, requests[:8], repo_root=f.root)


def test_wave_respects_native_128_selector_capacity_without_new_body_limit(setup):
    f = setup
    services, requests, ids = wave_fixture(f, 129)
    f.resolve.reset_mock()
    with source_anchor_wave(services, requests[0], ids) as bound:
        assert [len(call.args[0].anchor_ids) for call in f.resolve.call_args_list] == [
            128,
            1,
        ]
        results = reads.read_source_anchors_direct_v2(
            bound, requests[-1:], repo_root=f.root
        )
        assert results[0].result.content == "first line"
