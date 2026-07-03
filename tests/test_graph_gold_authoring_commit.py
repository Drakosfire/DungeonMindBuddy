import json
import shutil
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_gold_authoring_commit import (
    GraphGoldAuthoringCommitRequest,
    commit_graph_gold_authoring_preview,
)
from apps.live_control_server.services.graph_gold_authoring_prepare import (
    GraphGoldAuthoringPrepareRequest,
    prepare_graph_gold_authoring_preview,
)
from apps.live_control_server.services.graph_gold_review import GraphGoldReviewError

FIXTURE_REL = Path("evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json")


def temp_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    dest = root / FIXTURE_REL
    dest.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_REL, dest)
    return root


def node_span(**overrides):
    data = {"proposal_id":"local-1","proposal_type":"node_from_span","created_at_iso":"2026-07-03T00:00:00Z","status":"accepted_local","lane_role":"live","source_text":"Tripod Null-Calf","source_offsets":{"start":1,"end":17},"suggested_label":"Tripod Null-Calf","suggested_kind":None}
    data.update(overrides); return data


def relationship(**overrides):
    data = {"proposal_id":"local-3","proposal_type":"relationship_assertion","created_at_iso":"2026-07-03T00:00:00Z","status":"accepted_local","lane_role":"live","source_node":{"lane_role":"live","node_id":"node:heroes-party","label":"Heroes / Party"},"target_node":{"lane_role":"live","node_id":"node:stone-bridge-town","label":"Stone Bridge"},"predicate":"threatens"}
    data.update(overrides); return data


def link_intent(**overrides):
    data = {"proposal_id":"local-4","proposal_type":"existing_object_link_intent","created_at_iso":"2026-07-03T00:00:00Z","status":"accepted_local","selected_node":{"lane_role":"live","node_id":"node:heroes-party","label":"Heroes / Party"},"candidate":{"candidate_id":"g1","label":"Heroes / Party","source":"gold_fixture","confidence":"high","score":0.95}}
    data.update(overrides); return data


def request(proposals, **overrides):
    data = {"campaign_id":"longmont-c1", "session_id":"session-1", "proposals": proposals}
    data.update(overrides)
    return GraphGoldAuthoringCommitRequest(**data)


def prepare_request(proposals, **overrides):
    data = {"campaign_id":"longmont-c1", "session_id":"session-1", "proposals": proposals}
    data.update(overrides)
    return GraphGoldAuthoringPrepareRequest(**data)


def load_fixture(root: Path):
    return json.loads((root / FIXTURE_REL).read_text())


def test_blocked_prepare_prevents_commit_and_does_not_mutate(tmp_path):
    root = temp_root(tmp_path)
    before = (root / FIXTURE_REL).read_bytes()
    response = commit_graph_gold_authoring_preview(request([]), root=root)
    assert response.commit_status == "blocked"
    assert response.backup_relpath is None
    assert (root / FIXTURE_REL).read_bytes() == before


def test_accepted_node_from_span_commits_node_backup_and_event(tmp_path):
    root = temp_root(tmp_path)
    response = commit_graph_gold_authoring_preview(request([node_span()]), root=root)
    assert response.commit_status == "committed"
    assert response.changed_counts.nodes_added == 1
    assert response.commit_id
    assert response.backup_relpath and (root / response.backup_relpath).is_file()
    assert response.event_log_relpath and (root / response.event_log_relpath).is_file()
    graph = load_fixture(root)
    assert any(n["node_id"] == "authored:node:local-1" and n["semantic_state"]["authority_state"] == "human_authored" for n in graph["nodes"])
    event = json.loads((root / response.event_log_relpath).read_text().splitlines()[-1])
    assert event["commit_id"] == response.commit_id
    assert "nodes_added" not in response.model_dump()


def test_link_intent_records_intent_but_writes_no_identity_link(tmp_path):
    root = temp_root(tmp_path)
    before_edges = len(load_fixture(root)["edges"])
    response = commit_graph_gold_authoring_preview(request([link_intent()]), root=root)
    assert response.changed_counts.link_intents_recorded == 1
    assert response.applied_operations[0].status == "recorded_intent"
    assert len(load_fixture(root)["edges"]) == before_edges


def test_self_relationship_and_unknown_predicate_block_without_mutation(tmp_path):
    root = temp_root(tmp_path)
    before = (root / FIXTURE_REL).read_bytes()
    response = commit_graph_gold_authoring_preview(request([relationship(target_node={"lane_role":"live","node_id":"node:heroes-party","label":"Heroes / Party"})]), root=root)
    assert response.commit_status == "blocked"
    assert (root / FIXTURE_REL).read_bytes() == before
    response2 = commit_graph_gold_authoring_preview(request([relationship(predicate="canonizes")]), root=root)
    assert response2.commit_status == "blocked"
    assert (root / FIXTURE_REL).read_bytes() == before


def test_unsupported_fixture_version_and_campaign_mismatch_raise_without_mutation(tmp_path):
    root = temp_root(tmp_path)
    before = (root / FIXTURE_REL).read_bytes()
    with pytest.raises(GraphGoldReviewError) as exc:
        commit_graph_gold_authoring_preview(request([node_span()], fixture_version="x"), root=root)
    assert exc.value.status_code == 422
    with pytest.raises(GraphGoldReviewError) as exc2:
        commit_graph_gold_authoring_preview(request([node_span()], campaign_id="wrong"), root=root)
    assert exc2.value.status_code == 422
    assert (root / FIXTURE_REL).read_bytes() == before


def test_duplicate_commit_does_not_duplicate_authored_node(tmp_path):
    root = temp_root(tmp_path)
    first = commit_graph_gold_authoring_preview(request([node_span()]), root=root)
    assert first.changed_counts.nodes_added == 1
    second = commit_graph_gold_authoring_preview(request([node_span()]), root=root)
    assert second.commit_status == "blocked"
    assert [n.get("node_id") for n in load_fixture(root)["nodes"]].count("authored:node:local-1") == 1


def test_fingerprint_mismatch_blocks_without_mutation(tmp_path):
    root = temp_root(tmp_path)
    before = (root / FIXTURE_REL).read_bytes()
    response = commit_graph_gold_authoring_preview(request([node_span()], expected_prepare_fingerprint="nope"), root=root)
    assert response.commit_status == "blocked"
    assert any(d.code == "prepare_fingerprint_mismatch" for d in response.diagnostics)
    assert (root / FIXTURE_REL).read_bytes() == before


def test_stale_fixture_fingerprint_blocks_without_mutation_backup_or_event(tmp_path):
    root = temp_root(tmp_path)
    fixture_path = root / FIXTURE_REL
    prepare_response = prepare_graph_gold_authoring_preview(prepare_request([node_span()]), root=root)
    externally_mutated = json.dumps({"nodes": [], "edges": [], "external_change": True}, indent=2).encode("utf-8")
    fixture_path.write_bytes(externally_mutated)

    response = commit_graph_gold_authoring_preview(
        request(
            [node_span()],
            expected_prepare_fingerprint=prepare_response.prepare_fingerprint,
            expected_fixture_state_fingerprint=prepare_response.fixture_state_fingerprint,
        ),
        root=root,
    )

    assert response.commit_status == "blocked"
    assert any(d.code == "fixture_state_fingerprint_mismatch" for d in response.diagnostics)
    assert response.backup_relpath is None
    assert response.event_log_relpath is None
    assert fixture_path.read_bytes() == externally_mutated


def test_matching_fixture_fingerprint_allows_commit(tmp_path):
    root = temp_root(tmp_path)
    prepare_response = prepare_graph_gold_authoring_preview(prepare_request([node_span()]), root=root)
    response = commit_graph_gold_authoring_preview(
        request(
            [node_span()],
            expected_prepare_fingerprint=prepare_response.prepare_fingerprint,
            expected_fixture_state_fingerprint=prepare_response.fixture_state_fingerprint,
        ),
        root=root,
    )
    assert response.commit_status == "committed"
    assert response.changed_counts.nodes_added == 1


def test_add_edge_and_fixture_reloadable_as_json(tmp_path):
    root = temp_root(tmp_path)
    response = commit_graph_gold_authoring_preview(request([relationship()]), root=root)
    assert response.changed_counts.edges_added == 1
    graph = load_fixture(root)
    assert any(e["edge_id"] == "authored:edge:local-3" for e in graph["edges"])
