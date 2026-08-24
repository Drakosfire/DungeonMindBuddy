from __future__ import annotations

from pathlib import Path

from apps.live_control_server.services.hermes_graph_query import (
    build_hermes_graph_turn_request,
)
from apps.live_control_server.services.recap_artifacts import RecapArtifactRecord
from graph_memory.interaction.latest_recap import (
    build_latest_recap_change_context,
    is_latest_recap_change_question,
    latest_recap_graph_facts_from_projection,
    latest_recap_graph_facts_from_store,
)


def _record(tmp_path: Path, session: int) -> RecapArtifactRecord:
    recap_path = tmp_path / f"Session {session} - recap.md"
    recap_path.write_text(f"# Session {session}\n", encoding="utf-8")
    return RecapArtifactRecord(
        artifact_id=f"longmont-c2/session-{session}",
        campaign_id="longmont-c2",
        session_id=f"session-{session}",
        source_artifact_id=f"source:session-{session}",
        source_recap_path=recap_path.relative_to(tmp_path).as_posix(),
        run_bundle_uri="",
        run_manifest_uri="",
        source_span_index_uri="",
        source_sha256=f"sha256:session-{session}",
        registered_at="2026-07-15T00:00:00Z",
        updated_at="2026-07-15T00:00:00Z",
    )


def _graph_store(*sessions: int) -> dict:
    source_artifacts = {
        f"source:session-{session}": {
            "campaign_id": "longmont-c2",
            "session_id": f"session-{session}",
        }
        for session in sessions
    }
    evidence = {
        f"evidence:session-{session}": {
            "source_artifact_id": f"source:session-{session}",
            "session_id": f"session-{session}",
        }
        for session in sessions
    }
    nodes = {
        f"event:session-{session}": {
            "evidence_ref_ids": [f"evidence:session-{session}"],
        }
        for session in sessions
    }
    return {
        "source_artifacts": source_artifacts,
        "evidence": evidence,
        "nodes": nodes,
        "edges": {},
    }


def _facts(*sessions: int, revision_id: str | None = "rev:head"):
    return latest_recap_graph_facts_from_store(
        _graph_store(*sessions),
        campaign_id="longmont-c2",
        revision_id=revision_id,
    )


def test_read_admitted_recap_excerpt_strips_frontmatter_and_truncates(
    tmp_path: Path,
) -> None:
    from graph_memory.interaction.latest_recap import read_admitted_recap_excerpt

    recap = tmp_path / "Session 24 - Recap.md"
    body = "Paragraph one about the North Gate.\n\n" + ("x" * 4000)
    recap.write_text(f"---\ntitle: S24\n---\n\n{body}\n", encoding="utf-8")

    excerpt = read_admitted_recap_excerpt(
        root=tmp_path,
        source_recap_path="Session 24 - Recap.md",
        max_chars=200,
    )
    assert excerpt is not None
    assert "title: S24" not in excerpt
    assert "North Gate" in excerpt
    assert "truncated" in excerpt.lower()


def test_latest_recap_context_discloses_memory_lag(tmp_path: Path) -> None:
    context = build_latest_recap_change_context(
        root=tmp_path,
        campaign_id="longmont-c2",
        facts=_facts(22),
        records=[_record(tmp_path, 22), _record(tmp_path, 23)],
    )

    assert context.status == "ready"
    assert context.outcome == "memory_lag"
    assert context.memory_lag is True
    assert context.latest_recap is not None
    assert context.latest_recap.session_id == "session-23"
    assert context.comparison_boundary is not None
    assert context.comparison_boundary.graph_revision_id == "rev:head"
    assert context.comparison_boundary.graph_latest_session_id == "session-22"
    assert context.graph_object_ids == ["event:session-23"] or context.graph_object_ids == []


def test_latest_recap_context_distinguishes_completed_no_change(tmp_path: Path) -> None:
    context = build_latest_recap_change_context(
        root=tmp_path,
        campaign_id="longmont-c2",
        facts=_facts(23),
        records=[_record(tmp_path, 23)],
    )

    assert context.outcome == "no_change"
    assert context.memory_lag is False
    assert "comparison_completed_no_later_graph_session" in context.diagnostic_codes


def test_latest_recap_context_distinguishes_unknown_and_source_unavailable(
    tmp_path: Path,
) -> None:
    unknown = build_latest_recap_change_context(
        root=tmp_path,
        campaign_id="longmont-c2",
        facts=_facts(),
        records=[],
    )
    missing_source = build_latest_recap_change_context(
        root=tmp_path,
        campaign_id="longmont-c2",
        facts=_facts(22),
        records=[RecapArtifactRecord(
            **{
                **_record(tmp_path, 23).model_dump(mode="python"),
                "source_recap_path": "missing/recap.md",
            }
        )],
    )

    assert unknown.outcome == "unknown"
    assert unknown.status == "unknown"
    assert missing_source.outcome == "source_unavailable"
    assert missing_source.status == "source_unavailable"


def test_s1_question_detection_preserves_free_form_text() -> None:
    assert is_latest_recap_change_question("What changed after the latest ingested recap?")
    assert is_latest_recap_change_question("Can you tell me what changed after the latest recap?")
    assert not is_latest_recap_change_question("What do we know about Tripod?")


def test_latest_recap_context_is_passed_to_the_hermes_session_packet(
    tmp_path: Path,
) -> None:
    envelope = {
        "world_id": "eldyrwild",
        "campaign_id": "longmont-c2",
        "revision_id": "rev:head",
        "focus": {"kind": "none", "session_id": None},
        "admissibility": "gm",
        "matched_node_ids": [],
        "nodes": [],
        "latest_recap_change": {
            "schema": "dmb_latest_recap_change_context_v1",
            "status": "ready",
            "campaign_id": "longmont-c2",
            "outcome": "memory_lag",
            "memory_lag": True,
            "latest_recap": {"session_id": "session-24"},
            "comparison_boundary": {
                "kind": "latest_admitted_recap_to_graph_head",
                "recap_session_id": "session-24",
                "graph_latest_session_id": "session-23",
                "graph_revision_id": "rev:head",
            },
            "diagnostic_codes": ["latest_recap_not_in_graph_head"],
        },
    }

    request, _ = build_hermes_graph_turn_request(
        question="What changed after the latest ingested recap?",
        graph_envelope=envelope,
        root=tmp_path,
    )

    assert request.retrieval_session is not None
    assert request.retrieval_session["latest_recap_change"]["outcome"] == "memory_lag"
    assert request.retrieval_session["intent_hint"] == "compare"

    from graph_memory.interaction.session_hydrate import hydrate_session_from_packet
    from graph_memory.interaction.session_store import get_session

    stored = get_session(request.retrieval_session_id)
    assert stored is not None
    assert stored.latest_recap_change is not None
    assert stored.latest_recap_change["outcome"] == "memory_lag"

    rehydrated = hydrate_session_from_packet(request.retrieval_session)
    assert rehydrated.latest_recap_change is not None
    assert rehydrated.latest_recap_change["latest_recap"]["session_id"] == "session-24"
    assert rehydrated.project_for_hermes()["latest_recap_change"]["memory_lag"] is True


def _projection(*sessions: int, revision_id: str = "rev:head"):
    from types import SimpleNamespace

    return SimpleNamespace(
        snapshot=SimpleNamespace(revision_id=revision_id),
        summary=SimpleNamespace(projection_truncated=False),
        source_artifacts=[
            SimpleNamespace(
                source_artifact_id=f"source:session-{session}",
                campaign_id="longmont-c2",
                session_id=f"session-{session}",
            )
            for session in sessions
        ],
        evidence=[
            SimpleNamespace(
                evidence_ref_id=f"evidence:session-{session}",
                source_artifact_id=f"source:session-{session}",
                session_id=f"session-{session}",
            )
            for session in sessions
        ],
        nodes=[
            SimpleNamespace(
                node_id=f"event:session-{session}",
                evidence_ref_ids=[f"evidence:session-{session}"],
            )
            for session in sessions
        ],
        relationships=[],
    )


def test_projection_facts_match_store_facts() -> None:
    store_facts = _facts(22, 23)
    projection_facts = latest_recap_graph_facts_from_projection(
        _projection(22, 23), campaign_id="longmont-c2"
    )
    assert projection_facts.session_ids == store_facts.session_ids
    assert (
        projection_facts.object_or_relationship_ids_by_session
        == store_facts.object_or_relationship_ids_by_session
    )


def test_latest_recap_context_distinguishes_changed(tmp_path: Path) -> None:
    context = build_latest_recap_change_context(
        root=tmp_path,
        campaign_id="longmont-c2",
        facts=_facts(22, 23),
        records=[_record(tmp_path, 22)],
    )
    assert context.outcome == "changed"
    assert "graph_contains_post_recap_session" in context.diagnostic_codes


def test_dungeonmind_latest_recap_uses_native_projection_not_hydration(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )
    from apps.live_control_server.services import world_graph_projection as projection_service
    from graph_memory.interaction import latest_recap as latest_recap_mod
    from graph_memory.interaction.latest_recap import resolve_latest_recap_change_context
    from graph_memory.world_supergraph import storage

    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    monkeypatch.delenv("DUNGEONMIND_WORLD_GRAPH_DIRECT_READ", raising=False)
    storage.clear_world_graph_cache_roots()

    def _explode(*_args, **_kwargs):
        raise AssertionError("hydrated Buddy graph must not run for latest-recap")

    monkeypatch.setattr(latest_recap_mod, "load_current_world_graph", _explode)
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    monkeypatch.setattr(world_graph_authority, "ensure_hydrated_authority", _explode)
    monkeypatch.setattr(
        projection_service,
        "project_world_graph",
        lambda request, root=None: _projection(22),
    )
    monkeypatch.setattr(
        latest_recap_mod,
        "list_recap_artifact_records",
        lambda repo, campaign_id=None: [
            _record(tmp_path, 22),
            _record(tmp_path, 23),
        ],
    )

    context = resolve_latest_recap_change_context(
        root=tmp_path,
        world_id="eldyrwild",
        campaign_id="longmont-c2",
        graph_revision_id="rev:head",
    )
    assert context.outcome == "memory_lag"
    assert context.comparison_boundary is not None
    assert context.comparison_boundary.graph_revision_id == "rev:head"
    assert context.comparison_boundary.graph_latest_session_id == "session-22"


def test_dungeonmind_latest_recap_native_failure_does_not_hydrate(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.integrations.dungeonmind_kernel import (
        world_graph_authority,
    )
    from apps.live_control_server.services import world_graph_projection as projection_service
    from graph_memory.interaction import latest_recap as latest_recap_mod
    from graph_memory.interaction.latest_recap import resolve_latest_recap_change_context
    from graph_memory.world_supergraph import storage

    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()

    def _explode(*_args, **_kwargs):
        raise AssertionError("hydrated Buddy graph must not run after native failure")

    monkeypatch.setattr(latest_recap_mod, "load_current_world_graph", _explode)
    monkeypatch.setattr(world_graph_authority, "route_service_read", _explode)
    monkeypatch.setattr(world_graph_authority, "ensure_hydrated_authority", _explode)
    monkeypatch.setattr(
        projection_service,
        "project_world_graph",
        lambda request, root=None: (_ for _ in ()).throw(
            projection_service.WorldGraphProjectionServiceError(
                "authority unavailable",
                code="authority_unavailable",
                status_code=503,
            )
        ),
    )
    monkeypatch.setattr(
        latest_recap_mod,
        "list_recap_artifact_records",
        lambda repo, campaign_id=None: [_record(tmp_path, 23)],
    )

    context = resolve_latest_recap_change_context(
        root=tmp_path,
        world_id="eldyrwild",
        campaign_id="longmont-c2",
        graph_revision_id="rev:head",
    )
    assert context.outcome == "unknown"
    assert context.diagnostic_codes == ["latest_recap_authority_unavailable"]


def test_explicit_fixture_root_latest_recap_still_uses_file_store(
    tmp_path: Path, monkeypatch
) -> None:
    from apps.live_control_server.services import world_graph_projection as projection_service
    from graph_memory.interaction import latest_recap as latest_recap_mod
    from graph_memory.interaction.latest_recap import resolve_latest_recap_change_context
    from graph_memory.world_supergraph import storage

    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, "dungeonmind")
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()

    def _explode_native(*_args, **_kwargs):
        raise AssertionError("explicit fixture roots must not use native projection")

    monkeypatch.setattr(projection_service, "project_world_graph", _explode_native)
    monkeypatch.setattr(
        latest_recap_mod,
        "load_current_world_graph",
        lambda root, world_id: (None, None, _graph_store(23)),
    )
    monkeypatch.setattr(
        latest_recap_mod,
        "list_recap_artifact_records",
        lambda repo, campaign_id=None: [_record(tmp_path, 23)],
    )

    context = resolve_latest_recap_change_context(
        root=tmp_path,
        graph_root=tmp_path / "fixture-graph",
        world_id="eldyrwild",
        campaign_id="longmont-c2",
        graph_revision_id="rev:head",
    )
    assert context.outcome == "no_change"
