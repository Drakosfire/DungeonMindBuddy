"""Unit tests for World Graph browse session catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.world_graph_sessions import (
    contribution_campaign_session,
    list_world_graph_sessions,
)
from graph_memory.kernel.contribution_models import (
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.world_supergraph.contribution_store import (
    save_contribution_index,
    upsert_contribution_in_index,
    write_contribution_record,
    ContributionIndex,
)


def _assertion(
    *,
    contribution_id: str,
    campaign_scope: str | None = "longmont-c1",
    session_id: str | None = "session-1",
) -> GraphContributionAssertion:
    return GraphContributionAssertion(
        assertion_id=f"assertion:{contribution_id}:node",
        assertion_kind="node",
        subject_node_id="pc:test",
        value={"label": "Test"},
        evidence_ref_ids=[],
        campaign_scope=campaign_scope,
        temporal_scope={"session_id": session_id} if session_id else None,
        acceptance_state="accepted",
        contribution_id=contribution_id,
    )


def _contribution(
    *,
    contribution_id: str,
    campaign_scope: str | None = "longmont-c1",
    source_artifact_id: str | None = "artifact:recap:longmont-c1:session-1",
    session_via_temporal: bool = False,
) -> GraphContribution:
    assertions = []
    if session_via_temporal:
        assertions = [
            _assertion(
                contribution_id=contribution_id,
                campaign_scope=campaign_scope,
                session_id="session-9",
            )
        ]
        source_artifact_id = "artifact:other:not-a-recap"
    return GraphContribution(
        contribution_id=contribution_id,
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id=source_artifact_id,
        produced_at="2026-07-27T00:00:00Z",
        campaign_scope=campaign_scope,
        status="active",
        accepted_assertions=assertions,
    )


def test_contribution_campaign_session_from_recap_artifact() -> None:
    contrib = _contribution(
        contribution_id="contribution:aaaa1111bbbb2222",
        source_artifact_id="artifact:recap:longmont-c2:session-24",
        campaign_scope="longmont-c2",
    )
    assert contribution_campaign_session(contrib) == ("longmont-c2", "session-24")


def test_contribution_campaign_session_from_temporal_scope() -> None:
    contrib = _contribution(
        contribution_id="contribution:cccc3333dddd4444",
        session_via_temporal=True,
        campaign_scope="longmont-c1",
    )
    assert contribution_campaign_session(contrib) == ("longmont-c1", "session-9")


def test_list_world_graph_sessions_aggregates_active_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "apps.live_control_server.services.world_graph_sessions.load_corpus_normalized_recap_markdown",
        lambda **_kwargs: "# Session body\n",
    )
    monkeypatch.setattr(
        "graph_memory.kernel.open_current_world_graph",
        lambda *_args, **_kwargs: (
            type("Head", (), {"head_revision_id": "rev:test"})(),
            None,
            None,
        ),
    )

    world_id = "eldyrwild"
    active = _contribution(
        contribution_id="contribution:1111222233334444",
        source_artifact_id="artifact:recap:longmont-c1:session-1",
    )
    second = _contribution(
        contribution_id="contribution:5555666677778888",
        source_artifact_id="artifact:recap:longmont-c1:session-1",
    )
    other = _contribution(
        contribution_id="contribution:9999aaaabbbbcccc",
        campaign_scope="longmont-c2",
        source_artifact_id="artifact:recap:longmont-c2:session-23",
    )
    superseded = _contribution(
        contribution_id="contribution:ddddeeeeffff0000",
        source_artifact_id="artifact:recap:longmont-c1:session-2",
    )
    superseded = superseded.model_copy(update={"status": "superseded"})

    for contrib in (active, second, other, superseded):
        write_contribution_record(tmp_path, world_id, contrib)

    index = ContributionIndex(world_id=world_id)
    for contrib in (active, second, other):
        index = upsert_contribution_in_index(index, contrib)
    index = index.model_copy(
        update={
            "all_contribution_ids": [
                *index.all_contribution_ids,
                superseded.contribution_id,
            ],
            "superseded_contribution_ids": [superseded.contribution_id],
        }
    )
    save_contribution_index(tmp_path, world_id, index)

    response = list_world_graph_sessions(world_id=world_id, root=tmp_path)
    assert response.world_id == world_id
    assert response.head_revision_id == "rev:test"
    by_key = {(row.campaign_id, row.session_id): row for row in response.sessions}
    assert ("longmont-c1", "session-1") in by_key
    assert ("longmont-c2", "session-23") in by_key
    assert ("longmont-c1", "session-2") not in by_key
    assert by_key[("longmont-c1", "session-1")].contribution_count == 2
    assert by_key[("longmont-c1", "session-1")].recap_available is True
    assert by_key[("longmont-c1", "session-1")].browseable is True

    filtered = list_world_graph_sessions(
        world_id=world_id, campaign_id="longmont-c2", root=tmp_path
    )
    assert [row.session_id for row in filtered.sessions] == ["session-23"]
