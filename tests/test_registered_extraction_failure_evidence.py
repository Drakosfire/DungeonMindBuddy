import hashlib
import json
import os
import subprocess
import sys

import pytest

from application_state.ingest.components import get_component_bytes, verify_transition_component_bytes

from tests.test_worldbuilding_profile_pipeline import (
    _admit_fixture_source,
    _load_fixture,
    _pass_outputs_for_span,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    FixtureCategoryGraphPassClient,
    CategoryGraphExtractionError,
)
from src.graph_memory.extraction import graph_preview_runner as runner
from src.graph_memory.extraction.worldbuilding_extraction_profile import (
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
)


def run_failure(root, raw):
    source, span = _admit_fixture_source(root)
    fixture = FixtureCategoryGraphPassClient(
        _pass_outputs_for_span(_load_fixture(), span)
    )
    completed = []

    class Client:
        def run_pass(self, name, **kwargs):
            if name == "edge_pass":
                raise CategoryGraphExtractionError(
                    "synthetic edge JSON failure",
                    pass_name=name,
                    raw_model_response=raw,
                )
            result = fixture.run_pass(name, **kwargs)
            completed.append(name)
            return result

    result = runner.run_production_extraction(
        runner.ProductionExtractionRequest(
            repo_root=root,
            source=source,
            profile_id=WORLDBUILDING_PROFILE_ID,
            profile_version=WORLDBUILDING_PROFILE_VERSION,
            allow_llm=True,
            category_client=Client(),
        )
    )
    assert completed and result.run.status.value == "failed"
    assert result.candidate_graph is None
    assert "candidate_graph" not in result.run.components
    from apps.live_control_server.services.graph_run_registry import load_run_source_input
    assert load_run_source_input(root, result.run)[1] == source.source_text.encode()
    return result


@pytest.mark.parametrize("raw", ["private returned source — 测试\n{bad json}", ""])
def test_registered_failure_retains_exact_private_response_and_fresh_read(
    tmp_path,
    application_state_dsn,
    raw,
):
    result = run_failure(tmp_path, raw)
    component = result.run.components["raw_model_response"]
    assert get_component_bytes(run_id=result.run.run_id, kind=component.kind,
        content_sha256=component.sha256) == raw.encode()
    assert component.sha256 == hashlib.sha256(raw.encode()).hexdigest()
    assert component.exists
    assert not list(tmp_path.rglob("raw_model_response.txt"))
    assert not list(tmp_path.rglob(".raw-response-*"))
    if raw:
        assert raw not in json.dumps(result.diagnostics)
    script = """
import hashlib,sys
from pathlib import Path
from apps.live_control_server.services.graph_run_registry import get_extraction_run
from application_state.ingest.components import get_component_bytes
root=Path(sys.argv[1]); run=get_extraction_run(root,sys.argv[2])
assert run.status.value=='failed'
ref=run.components['raw_model_response']
data=get_component_bytes(run_id=run.run_id,kind=ref.kind,content_sha256=ref.sha256)
assert hashlib.sha256(data).hexdigest()==ref.sha256==sys.argv[3]
print('private-failure-evidence-reopened')
"""
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(tmp_path),
            result.run.run_id,
            component.sha256,
        ],
        env=dict(os.environ),
        text=True,
        capture_output=True,
    )
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == "private-failure-evidence-reopened"


def test_no_raw_response_does_not_invent_evidence(tmp_path, application_state_dsn):
    result = run_failure(tmp_path, None)
    assert "raw_model_response" not in result.run.components
    assert not list(tmp_path.rglob("raw_model_response.txt"))


def test_private_consolidation_diagnostics_component_is_digest_bound(tmp_path, application_state_dsn):
    payload = {
        "livestock_semantic_hygiene": {
            "deferred_proposals": {
                "deferred:livestock-section:edge:edge:goats": {
                    "item_id": "deferred:livestock-section:edge:edge:goats",
                    "kind": "edge",
                    "proposal": {
                        "edge_id": "edge:goats",
                        "from_node_id": "event:goats",
                        "to_node_id": "place:exampleland",
                        "relationship_type": "located_in",
                        "label": "",
                        "qualifiers": {"certainty": "qualified"},
                        "evidence_refs": [
                            {"source_span_ref_id": "span:goats", "anchor_quotes": ["Float Goats"]}
                        ],
                    },
                }
            }
        }
    }
    from application_state.ingest import service as ingest
    run = ingest.create_extraction_run(runner.ExtractionRun(run_id="diagnostics-run", source_artifact_id="source:input", source_domain="worldbuilding"))
    component = runner._retain_private_json_component(
        payload=payload,
        kind=runner.ExtractionRunComponentKind.CONSOLIDATION_DIAGNOSTICS, run=run,
    )
    raw = verify_transition_component_bytes(run_id=run.run_id, expected_revision=run.revision,
        kind=component.kind, content_sha256=component.sha256)

    assert component.kind.value == "consolidation_diagnostics"
    assert component.exists
    assert component.sha256 == hashlib.sha256(raw).hexdigest()
    assert json.loads(raw) == payload
    assert not list(tmp_path.rglob("consolidation_diagnostics.json"))


def test_private_diagnostics_write_failure_does_not_echo_payload(tmp_path, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("database unavailable with PRIVATE_BODY SOURCE_TEXT")

    monkeypatch.setattr("application_state.ingest.components.persist_component_payload", unavailable)
    with pytest.raises(RuntimeError, match="Could not persist private extraction diagnostics") as exc:
        runner._retain_private_json_component(
            payload={"private": "SOURCE_TEXT"},
            kind=runner.ExtractionRunComponentKind.CONSOLIDATION_DIAGNOSTICS,
            run=runner.ExtractionRun(run_id="unexecuted", source_artifact_id="source", source_domain="worldbuilding"),
        )
    assert "SOURCE_TEXT" not in str(exc.value)


def test_storage_failure_cannot_report_retention_or_return_candidate(
    tmp_path,
    application_state_dsn,
    monkeypatch,
):
    from application_state.ingest import components
    from application_state.ingest.service import list_extraction_runs

    calls = []
    original = components.persist_component_payload
    def unavailable_private_output(**kwargs):
        if kwargs["kind"] == runner.ExtractionRunComponentKind.RAW_MODEL_RESPONSE:
            calls.append(kwargs["payload"])
            raise OSError("private body in database error")
        return original(**kwargs)
    monkeypatch.setattr(components, "persist_component_payload", unavailable_private_output)
    with pytest.raises(RuntimeError, match="persist private") as error:
        run_failure(tmp_path, "private body")
    assert str(error.value) == "Could not persist private extraction response evidence"
    assert calls == [b"private body"]
    [saved] = list_extraction_runs()
    assert saved.status.value == "prepared"
    assert "raw_model_response" not in saved.components and "candidate_graph" not in saved.components
    assert not list(tmp_path.rglob("candidate_graph.json"))


def test_writer_failure_is_controlled_and_never_echoes_body(tmp_path, monkeypatch):
    def unavailable(**kwargs):
        raise OSError("database unavailable with PRIVATE_BODY SOURCE_TEXT")

    monkeypatch.setattr("application_state.ingest.components.persist_component_payload", unavailable)
    with pytest.raises(RuntimeError, match="Could not persist private") as exc:
        runner._retain_private_response("PRIVATE_BODY",
            run=runner.ExtractionRun(run_id="unexecuted", source_artifact_id="source", source_domain="worldbuilding"))
    assert "PRIVATE_BODY" not in str(exc.value)


def test_private_file_unavailability_does_not_block_database_failure_retention(
    tmp_path, application_state_dsn, monkeypatch,
):
    import tempfile
    original = tempfile.mkstemp
    def unavailable_private_file(*args, **kwargs):
        if kwargs.get("prefix") in {".raw-response-", ".private-json-"}:
            raise OSError("private mirror storage unavailable")
        return original(*args, **kwargs)
    monkeypatch.setattr(tempfile, "mkstemp", unavailable_private_file)
    result = run_failure(tmp_path, "retained in database — 测试")
    ref = result.run.components["raw_model_response"]
    assert get_component_bytes(run_id=result.run.run_id, kind=ref.kind,
        content_sha256=ref.sha256) == "retained in database — 测试".encode()
    assert not list(tmp_path.rglob("raw_model_response.txt"))
    assert not list(tmp_path.rglob("consolidation_diagnostics.json"))


def test_database_diagnostic_failure_stops_before_candidate(tmp_path, application_state_dsn, monkeypatch):
    from application_state.ingest import components
    from application_state.ingest.service import list_extraction_runs
    from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

    original = components.persist_component_payload
    def unavailable_private_output(**kwargs):
        if kwargs["kind"] == runner.ExtractionRunComponentKind.CONSOLIDATION_DIAGNOSTICS:
            raise OSError("database error containing SOURCE_TEXT")
        return original(**kwargs)
    monkeypatch.setattr(components, "persist_component_payload", unavailable_private_output)
    with pytest.raises(RuntimeError, match="Could not persist private extraction diagnostics") as error:
        _run_recap_extraction(tmp_path, client=FixtureClient())
    assert "SOURCE_TEXT" not in str(error.value)
    [saved] = list_extraction_runs()
    assert saved.status.value == "prepared"
    assert "consolidation_diagnostics" not in saved.components and "candidate_graph" not in saved.components
    assert not list(tmp_path.rglob("candidate_graph.json"))


def test_private_diagnostic_serialization_refuses_non_json_without_storage(monkeypatch):
    def unexpected(**kwargs):
        pytest.fail("invalid private JSON reached storage")
    monkeypatch.setattr("application_state.ingest.components.persist_component_payload", unexpected)
    for value in (float("nan"), object()):
        with pytest.raises(RuntimeError, match="Could not persist private extraction diagnostics") as error:
            runner._retain_private_json_component(payload={"private": value},
                kind=runner.ExtractionRunComponentKind.CONSOLIDATION_DIAGNOSTICS,
                run=runner.ExtractionRun(run_id="unexecuted", source_artifact_id="source", source_domain="worldbuilding"))
        assert "object at" not in str(error.value)
