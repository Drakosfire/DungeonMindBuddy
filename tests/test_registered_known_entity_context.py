from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_preview_runner import run_recap_production_extraction
from apps.live_control_server.services.graph_run_registry import get_extraction_run
from src.graph_memory.extraction.known_entity_registry import known_entities_from_world_graph


class RecordingClient:
    def __init__(self):
        self.messages = {}

    def run_pass(self, pass_name, *, user_content, **kwargs):
        self.messages[pass_name] = user_content
        span = re.search(r"### (\S+) /", user_content).group(1)
        ref = {"source_span_ref_id": span, "anchor_quotes": ["Lantern Inn"]}
        if pass_name == "location_pass":
            parsed = {"observation_nodes": [{
                "node_id": "location:inn", "label": "Lantern Inn", "node_type": "location",
                "description": "An inn", "importance": "medium", "evidence_refs": [ref],
            }]}
        elif pass_name == "actor_pass" and "Vela serves" in user_content and "`node:vela`" not in user_content:
            parsed = {"observation_nodes": [{
                "node_id": "new:vela", "label": "Vela", "node_type": "character",
                "description": "Serves ale at the inn", "importance": "medium",
                "evidence_refs": [{"source_span_ref_id": span, "anchor_quotes": ["Vela"]}],
            }]}
        elif pass_name == "edge_pass" and '"node:vela"' in user_content.split("## Consolidated nodes", 1)[1]:
            parsed = {"observation_edges": [{
                "edge_id": "edge:vela-inn", "from_node_id": "node:vela", "to_node_id": "location:inn",
                "label": "Vela is at the inn", "relationship_type": "present_at", "predicate_family": "spatial",
                "evidence_refs": [{"source_span_ref_id": span, "anchor_quotes": ["Vela serves ale at the Lantern Inn."]}],
            }]}
        elif pass_name == "edge_pass":
            parsed = {"observation_edges": []}
        elif pass_name == "beat_pass":
            parsed = {"observation_beats": []}
        else:
            parsed = {"observation_nodes": []}
        return {"parsed": parsed, "raw_text": json.dumps(parsed), "usage": {},
                "cost_usd": 0.0, "elapsed_ms": 0.0, "response_id": "synthetic"}


@pytest.mark.parametrize("context,mentioned", [(True, True), (False, True), (True, False)])
def test_registered_known_npc_context_survives_run_readback(tmp_path, application_state_dsn, monkeypatch, context, mentioned):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    path = tmp_path / "recap.txt"
    path.write_text("Vela serves ale at the Lantern Inn.\n" if mentioned else "The Lantern Inn is quiet.\n")
    client = RecordingClient()
    entities = tuple(known_entities_from_world_graph({"nodes": [{
        "node_id": "node:vela", "label": "Vela", "kind": "dnd5e:npc",
    }]}, include_kinds=None))
    kwargs = {"extra_known_entities": entities} if context else {}
    result = run_recap_production_extraction(
        repo_root=tmp_path, campaign_id="longmont-c2", session_id="session-24", recap_path=path,
        profile="category_baseline", model_id="deepseek/deepseek-v4.1-flash", category_client=client,
        **kwargs,
    )
    assert result.failure_kind is None
    assert str(result.run.status.value) == "reviewable"
    reopened = get_extraction_run(tmp_path, result.run.run_id)
    assert reopened.run_id == result.run.run_id
    assert reopened.status == result.run.status
    child = subprocess.run(
        [sys.executable, "-c", (
            "import sys,json; sys.path[:0]=[sys.argv[1],sys.argv[1]+'/src']; "
            "from pathlib import Path; "
            "from apps.live_control_server.services.graph_run_registry import get_extraction_run; "
            "r=get_extraction_run(Path(sys.argv[2]),sys.argv[3]); "
            "print(json.dumps({'run_id':r.run_id,'status':r.status.value,"
            "'components':{k:v.sha256 for k,v in r.components.items()}}))"
        ), str(Path(__file__).resolve().parents[1]), str(tmp_path), reopened.run_id],
        check=True, capture_output=True, text=True,
    )
    fresh = json.loads(child.stdout)
    assert fresh["run_id"] == reopened.run_id
    assert fresh["status"] == "reviewable"
    assert fresh["components"]["candidate_graph"] == reopened.components["candidate_graph"].sha256
    candidate = reopened.components["candidate_graph"]
    candidate_path = tmp_path / candidate.uri.removeprefix("repo://")
    payload = candidate_path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == candidate.sha256
    saved = json.loads(payload)
    canonical = [n for n in saved["nodes"] if n["node_id"] == "node:vela"]
    assert len(canonical) == int(context and mentioned)
    if context and mentioned:
        assert canonical[0]["proposed_action"] == "anchor"
        assert canonical[0].get("corpus_ref") is None
        assert any(e["from_node_id"] == "node:vela" for e in saved["edges"])
        assert '"node:vela"' in client.messages["edge_pass"].split("## Consolidated nodes", 1)[1]
        mentions = reopened.components["provenance_index"]
        mention_bytes = (tmp_path / mentions.uri.removeprefix("repo://")).read_bytes()
        assert hashlib.sha256(mention_bytes).hexdigest() == mentions.sha256
        assert "node:vela" in mention_bytes.decode()
    else:
        assert not any(e["from_node_id"] == "node:vela" for e in saved["edges"])
