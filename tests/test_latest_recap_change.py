from __future__ import annotations

from pathlib import Path

from apps.live_control_server.services.hermes_graph_query import (
    build_hermes_graph_turn_request,
)
from apps.live_control_server.services.recap_artifacts import RecapArtifactRecord
from graph_memory.interaction.latest_recap import (
    build_latest_recap_change_context,
    is_latest_recap_change_question,
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
        graph_revision_id="rev:head",
        graph_store=_graph_store(22),
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
        graph_revision_id="rev:head",
        graph_store=_graph_store(23),
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
        graph_revision_id="rev:head",
        graph_store=_graph_store(),
        records=[],
    )
    missing_source = build_latest_recap_change_context(
        root=tmp_path,
        campaign_id="longmont-c2",
        graph_revision_id="rev:head",
        graph_store=_graph_store(22),
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
