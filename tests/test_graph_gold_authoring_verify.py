import json
import shutil
from pathlib import Path

from apps.live_control_server.services.graph_gold_authoring_commit import GraphGoldAuthoringCommitRequest, commit_graph_gold_authoring_preview
from apps.live_control_server.services.graph_gold_authoring_verify import GraphGoldAuthoringVerifyCommitRequest, verify_graph_gold_authoring_commit
from apps.live_control_server.services.graph_gold_review import build_gold_graph_projection

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


def commit_request(proposals):
    return GraphGoldAuthoringCommitRequest(campaign_id="longmont-c1", session_id="session-1", proposals=proposals)


def verify_request(response):
    return GraphGoldAuthoringVerifyCommitRequest(campaign_id="longmont-c1", session_id="session-1", commit_id=response.commit_id, applied_operations=response.applied_operations)


def test_commit_add_node_then_verify_reports_fixture_or_projection(tmp_path):
    root = temp_root(tmp_path)
    commit = commit_graph_gold_authoring_preview(commit_request([node_span()]), root=root)
    verify = verify_graph_gold_authoring_commit(verify_request(commit), root=root)
    assert verify.verification_status in {"verified", "partial"}
    assert verify.checked_operations[0].verification_status in {"found_in_gold_projection", "found_in_fixture_only"}
    assert "node" in verify.checked_operations[0].summary.lower()


def test_commit_add_edge_then_verify_reports_fixture_or_projection(tmp_path):
    root = temp_root(tmp_path)
    commit = commit_graph_gold_authoring_preview(commit_request([relationship()]), root=root)
    verify = verify_graph_gold_authoring_commit(verify_request(commit), root=root)
    assert verify.checked_operations[0].verification_status in {"found_in_gold_projection", "found_in_fixture_only"}


def test_link_intent_verifies_event_only_without_identity_link(tmp_path):
    root = temp_root(tmp_path)
    before_edges = len(json.loads((root / FIXTURE_REL).read_text())["edges"])
    commit = commit_graph_gold_authoring_preview(commit_request([link_intent()]), root=root)
    verify = verify_graph_gold_authoring_commit(verify_request(commit), root=root)
    assert verify.checked_operations[0].verification_status == "recorded_event_only"
    assert "no identity link was written" in verify.checked_operations[0].summary
    assert len(json.loads((root / FIXTURE_REL).read_text())["edges"]) == before_edges


def test_blocked_or_unknown_commit_verifies_cleanly(tmp_path):
    root = temp_root(tmp_path)
    blocked = commit_graph_gold_authoring_preview(commit_request([]), root=root)
    verify = verify_graph_gold_authoring_commit(verify_request(blocked), root=root)
    assert verify.verification_status == "blocked"
    unknown = GraphGoldAuthoringVerifyCommitRequest(campaign_id="longmont-c1", session_id="session-1", commit_id="missing", applied_operations=[])
    missing = verify_graph_gold_authoring_commit(unknown, root=root)
    assert any(d.code == "commit_event_missing" for d in missing.diagnostics)


def test_verify_is_read_only_and_missing_target_is_diagnostic(tmp_path):
    root = temp_root(tmp_path)
    commit = commit_graph_gold_authoring_preview(commit_request([node_span()]), root=root)
    before = (root / FIXTURE_REL).read_bytes()
    payload = commit.model_copy(deep=True)
    payload.applied_operations[0].target_id = "authored:node:missing"
    verify = verify_graph_gold_authoring_commit(verify_request(payload), root=root)
    assert verify.checked_operations[0].verification_status == "missing"
    assert (root / FIXTURE_REL).read_bytes() == before
    assert verify.diagnostics


def test_projection_builder_loads_committed_fixture_after_node_and_edge(tmp_path):
    root = temp_root(tmp_path)
    commit_graph_gold_authoring_preview(commit_request([node_span(proposal_id="local-node")]), root=root)
    commit_graph_gold_authoring_preview(commit_request([relationship(proposal_id="local-edge")]), root=root)
    projection = build_gold_graph_projection(campaign_id="longmont-c1", session_id="session-1", root=root)
    assert projection.node_views
