"""One native metadata resolution, real immutable body joins and v2 receipts."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from graph_memory.interaction import expansion_executor as executor
from graph_memory.interaction.session import (
    GraphRetrievalSession,
    SessionSnapshot,
    SourceAnchorState,
)
from graph_memory.interaction.session_store import clear_sessions, create_session
from graph_memory.retrieval.models import (
    WorldGraphRetrievalSnapshot,
    WorldGraphSourceAnchorReadRequest,
)
from graph_memory.source_span import build_stable_source_span_id
from tests.test_recap_source_read_continuity import (
    ARTIFACT_ID,
    _anchor,
    _digest_hex,
    _FakeSources,
)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    source = tmp_path / "source.md"
    source.write_text("first line\nsecond line\n")
    digest = _digest_hex(source.read_bytes())
    native_snapshot = SimpleNamespace(world_id="world:test", revision_id="rev:test")
    projection = SimpleNamespace(world_id="world:test", revision_pin="rev:test")
    anchors = {}
    for line in (1, 2):
        span = build_stable_source_span_id(
            source_artifact_id=ARTIFACT_ID,
            content_sha256=digest,
            start_line=line,
            end_line=line,
        )
        anchor = replace(
            _anchor(locator_identity=span, uri="repo://source.md"),
            anchor_id=f"source-anchor:v1:batch-{line}",
        )
        anchors[anchor.anchor_id] = anchor

    def resolution(anchor_id):
        return SimpleNamespace(
            snapshot=native_snapshot,
            anchor_id=anchor_id,
            found=anchor_id in anchors,
            anchor=anchors.get(anchor_id),
        )

    resolve = Mock(
        side_effect=lambda request: SimpleNamespace(
            snapshot=native_snapshot,
            resolutions=tuple(resolution(i) for i in request.anchor_ids),
        )
    )
    sources = _FakeSources(locator="repo://source.md", digest=digest)
    sources.get_revision = Mock(wraps=sources.get_revision)
    services = SimpleNamespace(
        binding=object(),
        bundle=SimpleNamespace(sources=sources),
        retrieval=SimpleNamespace(
            resolve_source_anchors=resolve,
            resolve_source_anchor=lambda _request, anchor_id: resolution(anchor_id),
        ),
    )
    monkeypatch.setattr(direct, "_map_retrieval_context", lambda *_args: projection)
    monkeypatch.setattr(direct, "_dnd_anchor_id", lambda value: value)
    monkeypatch.setattr(
        direct,
        "_retrieval_snapshot_view",
        lambda _snapshot, *, focus: WorldGraphRetrievalSnapshot(
            world_id="world:test",
            campaign_id="",
            revision_id="rev:test",
            head_revision_id="rev:test",
            is_head=True,
            scope_mode="world",
            focus=focus,
            admissibility="gm",
        ),
    )
    requests = tuple(
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": "dmb_world_graph_source_anchor_read_request_v1",
                "worldId": "world:test",
                "campaignId": "",
                "scopeMode": "world",
                "admissibility": "gm",
                "revisionPin": "rev:test",
                "anchorId": key,
                "maxChars": 4000,
            }
        )
        for key in anchors
    )
    clear_sessions()
    yield SimpleNamespace(
        root=tmp_path,
        source=source,
        services=services,
        requests=requests,
        resolve=resolve,
        sources=sources,
        snapshot=native_snapshot,
    )
    clear_sessions()


def test_batch_body_parity_and_revision_digest_deduplication(setup):
    f = setup
    singles = tuple(
        direct.read_source_anchor_direct_v2(f.services, r, repo_root=f.root)
        for r in f.requests
    )
    f.sources.get_revision.reset_mock()
    batch = direct.read_source_anchors_direct_v2(
        f.services, f.requests, repo_root=f.root
    )
    f.resolve.assert_called_once()
    # Content opener may load immutable revision metadata too; count only the
    # dedicated digest lookup rather than conflating all repository reads.
    assert [x.result.model_dump() for x in batch] == [
        x.result.model_dump() for x in singles
    ]
    assert [x.result.content for x in batch] == ["first line", "second line"]
    assert [x.source_revision_sha256 for x in batch] == [
        x.source_revision_sha256 for x in singles
    ]


def test_digest_helper_runs_once_per_exact_revision(setup, monkeypatch):
    f = setup
    digest = Mock(wraps=direct._source_revision_digest)
    monkeypatch.setattr(direct, "_source_revision_digest", digest)
    direct.read_source_anchors_direct_v2(f.services, f.requests, repo_root=f.root)
    assert digest.call_count == 1


@pytest.mark.parametrize(
    "fault", ["missing", "reordered", "foreign_revision", "duplicated"]
)
def test_bad_native_batch_never_opens_a_body(setup, monkeypatch, fault):
    f = setup
    original = f.resolve.side_effect

    def bad(request):
        result = original(request)
        if fault == "missing":
            result.resolutions = result.resolutions[:-1]
        elif fault == "reordered":
            result.resolutions = result.resolutions[::-1]
        elif fault == "duplicated":
            result.resolutions = (result.resolutions[0],) * 2
        else:
            result.snapshot = SimpleNamespace(
                world_id="world:test", revision_id="rev:foreign"
            )
        return result

    f.resolve.side_effect = bad
    opener = Mock(side_effect=AssertionError("body opener must not run"))
    monkeypatch.setattr(direct, "_anchor_read_view", opener)
    with pytest.raises(direct.DirectWorldGraphReadError):
        direct.read_source_anchors_direct_v2(f.services, f.requests, repo_root=f.root)
    opener.assert_not_called()


def test_mixed_request_contexts_fail_before_native_resolution(setup):
    f = setup
    changed = f.requests[1].model_copy(update={"revision_pin": "rev:foreign"})
    with pytest.raises(direct.DirectWorldGraphReadError):
        direct.read_source_anchors_direct_v2(
            f.services, (f.requests[0], changed), repo_root=f.root
        )
    f.resolve.assert_not_called()


@pytest.mark.parametrize("fault", ["changed_bytes", "missing_body"])
def test_metadata_found_never_promotes_an_unavailable_body(setup, fault):
    f = setup
    if fault == "changed_bytes":
        f.source.write_text("changed\nsecond line\n")
    else:
        f.source.unlink()
    reads = direct.read_source_anchors_direct_v2(
        f.services, f.requests, repo_root=f.root
    )
    assert all(
        item.result.outcome == "unavailable" and item.result.content is None
        for item in reads
    )


def test_actual_executor_uses_one_batch_and_records_only_opened_bodies(
    setup, monkeypatch
):
    f = setup
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
    monkeypatch.setattr(
        executor.retrieval_service,
        "read_source_anchors_internal_v2",
        lambda requests, **_kw: direct.read_source_anchors_direct_v2(
            f.services, requests, repo_root=f.root
        ),
    )
    output = executor.execute_read_graph_source(
        {
            "retrievalSessionId": session.id,
            "anchorIds": [r.anchor_id for r in f.requests],
            "maxChars": 4000,
        },
        receipt_version=2,
    )
    f.resolve.assert_called_once()
    assert [item["result"]["content"] for item in output["reads"]] == [
        "first line",
        "second line",
    ]
    assert all(item["receipt"] is not None for item in output["reads"])
    assert all(anchor.opened for anchor in session.source_anchors)


@pytest.mark.parametrize("fault", ["missing", "reordered"])
def test_executor_rejects_malformed_internal_batch_without_open_receipts(setup, monkeypatch, fault):
    f = setup
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:test", campaign_id="", revision_id="rev:test", scope_mode="world"
        ),
        source_anchors=[SourceAnchorState(anchor_id=r.anchor_id, readable=True) for r in f.requests],
    )
    create_session(session)

    def malformed(requests, **_kw):
        reads = direct.read_source_anchors_direct_v2(f.services, requests, repo_root=f.root)
        return reads[:-1] if fault == "missing" else reads[::-1]

    monkeypatch.setattr(executor.retrieval_service, "read_source_anchors_internal_v2", malformed)
    output = executor.execute_read_graph_source(
        {"retrievalSessionId": session.id, "anchorIds": [r.anchor_id for r in f.requests]},
        receipt_version=2,
    )
    assert len(output["reads"]) == 2
    assert all(item["receipt"] is None for item in output["reads"])
    assert all(item["result"]["code"] == "source_batch_unverifiable" for item in output["reads"])
    assert not any(anchor.opened for anchor in session.source_anchors)
