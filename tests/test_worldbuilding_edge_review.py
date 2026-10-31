"""Opt-in advisory pipeline, immutable subset and registered evidence boundaries."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from application_state.ingest.components import get_component_bytes

from src.graph_memory.extraction.bounded_recap_execution import BoundedRecapPassClient, DEEPSEEK_MODEL
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError, CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient, run_category_pipeline,
)
from src.graph_memory.extraction.worldbuilding_edge_review import apply_review, review_prompt, json_copy
from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_ADVISORY_REVIEW_PROFILE as PROFILE

BODY = "Mayor Elara leads the Council. Mirathorn stands near the lake."
REF = {"source_span_ref_id": "span-1", "anchor_quotes": [BODY]}


def outputs(span="span-1"):
    ref = {**REF, "source_span_ref_id": span}
    return {
        "actor_pass": {"observation_nodes": [{"node_id": "actor:elara", "label": "Mayor Elara",
            "node_type": "character", "description": "Mayor Elara leads the Council.", "evidence_refs": [ref]}]},
        "collective_pass": {"observation_nodes": [{"node_id": "group:council", "label": "Council",
            "node_type": "faction", "description": "The Council.", "evidence_refs": [ref]}]},
        "edge_pass": {"observation_edges": [{"edge_id": "edge:leads", "from_node_id": "actor:elara",
            "to_node_id": "group:council", "relationship_type": "leads", "label": "leads", "evidence_refs": [ref]}]},
    }


class Client(BoundedRecapPassClient):
    """Explicit bounded-client test subclass; no provider/network/worker access."""
    def __init__(self, payload=None, retained=None, fail=False):
        self.limits = SimpleNamespace(provider="openrouter", model=DEEPSEEK_MODEL, max_calls=8)
        self.calls = []
        self.fixture = FixtureCategoryGraphPassClient(payload or outputs())
        self.retained = ["edge:leads"] if retained is None else retained
        self.fail = fail
        self.prompts = []

    def run_pass(self, name, **kwargs):
        self.calls.append({"pass_name": name, "observation": None})
        self.prompts.append(kwargs["user_content"])
        if name == "edge_review_pass":
            if self.fail:
                raise CategoryGraphExtractionError("PRIVATE BODY not public", pass_name=name,
                                                   raw_model_response="{bad review — 测试")
            result = {"parsed": {"retained_edge_ids": self.retained}, "raw_text": "  reviewer text\n",
                      "usage": None, "cost_usd": None, "elapsed_ms": 1, "response_id": None}
        else:
            result = self.fixture.run_pass(name, **kwargs)
            result["raw_text"] = "  " + json.dumps(result["parsed"]) + "\n"
        return result


def options(profile=PROFILE, model=DEEPSEEK_MODEL):
    return CategoryGraphExtractionOptions(campaign_id="synthetic", session_id=None, session_number=None,
        source_text=BODY, source_artifact_id="artifact:test", model_id=model,
        source_span_index={"source_artifact_id": "artifact:test", "source_ref_id": "artifact:test:text",
            "spans": [{"source_span_ref_id": "span-1", "span_id": "span-1", "text": BODY,
                       "line_start": 1, "line_end": 1}]}, profile=profile, enable_party_claimed_fill=False)


@pytest.mark.parametrize("bad", [None, {}, {"retained_edge_ids": ["unknown"]},
    {"retained_edge_ids": ["e", "e"]}, {"retained_edge_ids": [1]},
    {"retained_edge_ids": [""]}, {"retained_edge_ids": [" "]},
    {"retained_edge_ids": "e"}, {"retained_edge_ids": [], "rewrites": []}])
def test_malformed_or_rewritten_subset_fails(bad):
    with pytest.raises(ValueError):
        apply_review({"edges": [{"edge_id": "e"}]}, bad)


def test_selection_copies_originals_and_preserves_order_refs_and_qualifiers():
    graph = {"nodes": [{"node_id": "n"}], "edges": [
        {"edge_id": "b", "label": "unchanged", "evidence_refs": [REF], "qualifier": "alleged"},
        {"edge_id": "a", "evidence_refs": [REF]}, {"edge_id": "c", "evidence_refs": [REF]}]}
    original = deepcopy(graph)
    result, diag = apply_review(graph, {"retained_edge_ids": ["c", "b"]})
    assert result["edges"] == [graph["edges"][0], graph["edges"][2]]
    assert diag["deferred"] == [graph["edges"][1]]
    assert result["deferred_items"][0]["evidence_refs"] == [REF]
    assert result["deferred_items"][0]["reason"].endswith("not_proven_false")
    result["edges"][0]["label"] = "changed"
    assert graph == original


@pytest.mark.parametrize("edges", [[{"edge_id": "e"}, {"edge_id": "e"}], [{"edge_id": 3}], [{"edge_id": " "}]])
def test_input_ids_reject_before_review_call(edges):
    with pytest.raises(ValueError):
        review_prompt({"edges": edges}, [])


def test_disposition_collision_and_unsafe_evidence_reject():
    with pytest.raises(ValueError, match="collision"):
        apply_review({"edges": [{"edge_id": "e"}], "deferred_items": [
            {"item_id": "deferred:advisory-edge-review:e"}]}, {"retained_edge_ids": []})
    for value in [object(), {"unsafe": object()}, float("nan"), {1: "key"}, (1, 2)]:
        with pytest.raises(ValueError, match="JSON safe"):
            json_copy(value)


@pytest.mark.parametrize("bad_client", [None, FixtureCategoryGraphPassClient({}), SimpleNamespace()])
def test_invalid_executor_never_calls(bad_client):
    with pytest.raises(CategoryGraphExtractionError, match="explicit matching"):
        run_category_pipeline(bad_client, options())


@pytest.mark.parametrize("provider,model,requested", [
    ("unregistered", DEEPSEEK_MODEL, DEEPSEEK_MODEL),
    ("openrouter", DEEPSEEK_MODEL, "other")])
def test_wrong_route_or_model_rejects_before_calls(provider, model, requested):
    client = Client()
    client.limits.provider, client.limits.model = provider, model
    with pytest.raises(CategoryGraphExtractionError):
        run_category_pipeline(client, options(model=requested))
    assert not client.calls


@pytest.mark.parametrize("retained", [["edge:leads"], []])
def test_pipeline_same_writer_review_instance_exact_source_and_canonical_envelope(retained):
    from src.graph_memory.extraction.category_candidate_graph_extractor import canonical_graph_for_runner
    client = Client(retained=retained)
    result = run_category_pipeline(client, options())
    assert [call["pass_name"] for call in client.calls] == [p.pass_id for p in PROFILE.node_passes] + ["edge_pass", "edge_review_pass"]
    prompt = json.loads(client.prompts[-1])
    assert prompt["source_packet"][0]["text"] == BODY
    assert result.candidate_graph == canonical_graph_for_runner(result.envelope, drop_empty_evidence_edges=False)
    assert len(result.candidate_graph["edges"]) == len(retained)
    bundle = json.loads(result.private_response_evidence)
    assert bundle["schema"] == "dmb_private_extraction_review_bundle_v1"
    assert len(bundle["completed_passes"]) == len(client.calls)
    assert bundle["completed_passes"][-1]["raw_text"] == "  reviewer text\n"
    assert bundle["completed_passes"][-1]["cost_usd"] is None
    assert all(row["observation"] is None for row in bundle["execution_observations"])
    assert bundle["advisory"]["semantic_acceptance"] is False
    assert not result.candidate_graph["nodes"][0]["semantic_state"]["canon_state"] == "accepted"


def test_empty_edges_skip_review_and_old_profile_does_not_change():
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_ROLE_SUPPORT_PROFILE
    client = Client(payload={"edge_pass": {"observation_edges": []}})
    result = run_category_pipeline(client, options())
    assert "edge_review_pass" not in [call["pass_name"] for call in client.calls]
    assert json.loads(result.private_response_evidence)["advisory"]["skipped"] == "no_generated_edges"
    old = run_category_pipeline(FixtureCategoryGraphPassClient(outputs()), options(profile=GAZETTEER_ROLE_SUPPORT_PROFILE))
    assert old.private_response_evidence is None and len(old.candidate_graph["edges"]) == 1


@pytest.mark.parametrize("fail,retained", [(True, []), (False, ["unknown"])])
def test_failed_review_retains_completed_passes_and_safe_error(fail, retained):
    with pytest.raises(CategoryGraphExtractionError) as caught:
        run_category_pipeline(Client(fail=fail, retained=retained), options())
    assert "PRIVATE BODY" not in str(caught.value)
    bundle = json.loads(caught.value.raw_model_response)
    assert bundle["schema"] == "dmb_private_extraction_failure_bundle_v1"
    assert len(bundle["completed_passes"]) == (5 if fail else 6)
    assert all("seam_request_sha256" in item for item in bundle["completed_passes"])
    if fail:
        assert bundle["failure"]["raw_text"] == "{bad review — 测试"


@pytest.mark.parametrize("fail", [False, True])
def test_registered_success_and_failure_evidence_reopens(tmp_path, application_state_dsn, monkeypatch, fail):
    import tempfile
    original = tempfile.mkstemp
    def unavailable_private_file(*args, **kwargs):
        if kwargs.get("prefix") in {".raw-response-", ".private-json-"}:
            raise OSError("private mirror storage unavailable")
        return original(*args, **kwargs)
    monkeypatch.setattr(tempfile, "mkstemp", unavailable_private_file)
    from tests.test_worldbuilding_profile_pipeline import _admit_fixture_source, _load_fixture, _pass_outputs_for_span
    from src.graph_memory.extraction.graph_preview_runner import ProductionExtractionRequest, run_production_extraction
    source, span = _admit_fixture_source(tmp_path)
    client = Client(_pass_outputs_for_span(_load_fixture(), span), retained=[], fail=fail)
    result = run_production_extraction(ProductionExtractionRequest(repo_root=tmp_path, source=source,
        profile_id=PROFILE.profile_id, profile_version=PROFILE.profile_version,
        model_id=DEEPSEEK_MODEL, allow_llm=True, category_client=client, output_dir=tmp_path / "out"))
    assert bool(result.failure_kind) is fail
    assert result.run.status.value == ("failed" if fail else "reviewable")
    assert (result.candidate_graph is None) is fail
    component = result.run.components["raw_model_response"]
    content = get_component_bytes(run_id=result.run.run_id, kind=component.kind,
        content_sha256=component.sha256)
    assert hashlib.sha256(content).hexdigest() == component.sha256
    assert not list(tmp_path.rglob("raw_model_response.txt"))
    assert not list(tmp_path.rglob("consolidation_diagnostics.json"))
    bundle = json.loads(content)
    assert bundle["completed_passes"] and bundle["source_sha256"] == source.source_sha256
    assert BODY not in json.dumps(result.diagnostics)
    child = subprocess.run([sys.executable, "-c", '''
import hashlib,json,sys
from pathlib import Path
from apps.live_control_server.services.graph_run_registry import get_extraction_run
from application_state.ingest.components import get_component_bytes
root=Path(sys.argv[1]); run=get_extraction_run(root,sys.argv[2])
ref=run.components['raw_model_response']; data=get_component_bytes(run_id=run.run_id,kind=ref.kind,content_sha256=ref.sha256)
assert hashlib.sha256(data).hexdigest()==ref.sha256
assert json.loads(data)['completed_passes']
print('reopened')
''', str(tmp_path), result.run.run_id], env=dict(os.environ), text=True, capture_output=True)
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == "reopened"


def test_existing_budget_is_not_automatically_increased():
    client = Client()
    client.limits.max_calls = 5
    with pytest.raises(CategoryGraphExtractionError, match="existing run budget"):
        run_category_pipeline(client, options())
    assert client.limits.max_calls == 5 and not client.calls


def test_review_schema_and_generation_prompts_are_unchanged():
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_ROLE_SUPPORT_PROFILE
    import jsonschema
    schema = schema_for_pass_spec(PROFILE.edge_review_pass)
    jsonschema.validate({"retained_edge_ids": []}, schema)
    new, old = Client(), Client()
    run_category_pipeline(new, options())
    run_category_pipeline(old, options(profile=GAZETTEER_ROLE_SUPPORT_PROFILE))
    assert new.prompts[:-1] == old.prompts
    assert PROFILE.source_section_retainer is GAZETTEER_ROLE_SUPPORT_PROFILE.source_section_retainer


def test_inherited_role_guard_defers_before_reviewer_and_cannot_be_reversed():
    from dataclasses import replace
    body = "Barin Stonefoot – Proprietor of Coppervein Mining Co."
    payload = outputs()
    actor = payload["actor_pass"]["observation_nodes"][0]
    actor.update(label="Barin Stonefoot", description=body)
    target = payload.pop("collective_pass")["observation_nodes"][0]
    target.update(label="Coppervein Mining Co.", node_type="location", description=body)
    payload["location_pass"] = {"observation_nodes": [target]}
    payload["edge_pass"]["observation_edges"][0].update(relationship_type="owns", label="owns")
    for item in [actor, target, payload["edge_pass"]["observation_edges"][0]]:
        item["evidence_refs"] = [{"source_span_ref_id": "span-1", "anchor_quotes": [body]}]
    opt = options()
    opt = replace(opt, source_text=body, source_span_index={**opt.source_span_index,
        "spans": [{"source_span_ref_id": "span-1", "span_id": "span-1", "text": body,
                   "line_start": 1, "line_end": 1}]})
    client = Client(payload=payload)
    result = run_category_pipeline(client, opt)
    assert not result.candidate_graph["edges"]
    assert result.candidate_graph["deferred_items"]
    assert "edge_review_pass" not in [call["pass_name"] for call in client.calls]
    assert json.loads(result.private_response_evidence)["advisory"]["skipped"] == "no_generated_edges"


def test_response_without_json_safe_metadata_retains_available_raw_without_echo():
    class Unsafe(Client):
        def run_pass(self, name, **kwargs):
            result = super().run_pass(name, **kwargs)
            result["cost_usd"] = object()
            return result
    with pytest.raises(CategoryGraphExtractionError) as caught:
        run_category_pipeline(Unsafe(), options())
    bundle = json.loads(caught.value.raw_model_response)
    assert bundle["pending_pass"]["returned_raw_text"].startswith("  ")
    assert bundle["failure"]["type"] == "ValueError"
    assert not bundle["completed_passes"]
    assert "object at" not in caught.value.raw_model_response


def test_provider_failure_before_any_response_has_unknown_evidence():
    class NoResponse(Client):
        def run_pass(self, name, **kwargs):
            raise RuntimeError("SECRET provider exception")
    with pytest.raises(CategoryGraphExtractionError) as caught:
        run_category_pipeline(NoResponse(), options())
    bundle = json.loads(caught.value.raw_model_response)
    assert bundle["failure"] == {"type": "RuntimeError", "raw_text": None}
    assert bundle["completed_passes"] == []
    assert "SECRET" not in str(caught.value) + caught.value.raw_model_response


def test_success_storage_failure_is_not_reviewable_or_replayed(tmp_path, application_state_dsn, monkeypatch):
    from tests.test_worldbuilding_profile_pipeline import _admit_fixture_source, _load_fixture, _pass_outputs_for_span
    from src.graph_memory.extraction import graph_preview_runner as runner
    source, span = _admit_fixture_source(tmp_path)
    client = Client(_pass_outputs_for_span(_load_fixture(), span), retained=[])
    drafts = []
    original_create = runner._create_draft_run
    def capture_draft(*args, **kwargs):
        run = original_create(*args, **kwargs)
        drafts.append(run)
        return run
    monkeypatch.setattr(runner, "_create_draft_run", capture_draft)
    from application_state.ingest import components
    original = components.persist_component_payload
    def unavailable(**kwargs):
        if kwargs["kind"] == runner.ExtractionRunComponentKind.RAW_MODEL_RESPONSE:
            raise OSError("private success bundle in database error")
        return original(**kwargs)
    monkeypatch.setattr(components, "persist_component_payload", unavailable)
    with pytest.raises(RuntimeError, match="persist private"):
        runner.run_production_extraction(runner.ProductionExtractionRequest(repo_root=tmp_path, source=source,
            profile_id=PROFILE.profile_id, profile_version=PROFILE.profile_version,
            model_id=DEEPSEEK_MODEL, allow_llm=True, category_client=client, output_dir=tmp_path / "out"))
    assert len(client.calls) == 6
    assert not list((tmp_path / "out").rglob("candidate_graph.json"))
    from apps.live_control_server.services.graph_run_registry import get_extraction_run
    run = get_extraction_run(tmp_path, drafts[0].run_id)
    assert run.status.value == "prepared"
    assert "raw_model_response" not in run.components and "candidate_graph" not in run.components


@pytest.mark.parametrize("fail_review", [False, True])
def test_real_bounded_attempt_accounting_survives_registered_bundle(
    tmp_path, application_state_dsn, monkeypatch, fail_review,
):
    from src.graph_memory.extraction import bounded_recap_execution as bounded
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome
    from src.graph_memory.extraction.graph_preview_runner import ProductionExtractionRequest, run_production_extraction
    from tests.test_worldbuilding_profile_pipeline import _admit_fixture_source, _load_fixture, _pass_outputs_for_span
    from tests.test_bounded_recap_execution import deepseek_observation
    from generationengine.types import TextResult

    source, span = _admit_fixture_source(tmp_path)
    fixture = _pass_outputs_for_span(_load_fixture(), span)
    names = [spec.pass_id for spec in PROFILE.node_passes] + ["edge_pass", "edge_review_pass"]
    evidence_dir = tmp_path / "private" / "attempts"
    evidence_dir.parent.mkdir(mode=0o700)
    invoked = []
    expected_refs = []

    def worker(factory, request, *, deadline, attempt_evidence=None):
        name = names[len(invoked)]
        invoked.append(name)
        parsed = fixture.get(name, {"observation_nodes": []})
        if name == "edge_review_pass":
            parsed = {"retained_edge_ids": []}
        # These are actual worker-seam receipts, not run_pass overrides.
        obs = deepseek_observation(provider_attempt_count=2, conformance_retry_count=1,
            transport_retry_count=0, input_tokens=101, output_tokens=23,
            cached_input_tokens=17, reasoning_tokens=5, latency_ms=12,
            provider_response_id="response-known", cost_usd=None)
        payload = obs.model_dump(mode="json")
        for ordinal in (1, 2):
            event = {"operation_id": name, "event_id": name + str(ordinal),
                "ordinal": ordinal, "kind": "initial" if ordinal == 1 else "conformance_retry",
                "response_status": "returned", "provider": "openrouter",
                "requested_model": DEEPSEEK_MODEL, "resolved_model": DEEPSEEK_MODEL,
                "response_model": DEEPSEEK_MODEL, "provider_response_id": "response-known"}
            path, sha = bounded._write_private_response_evidence(evidence_dir,
                ordinal=len(invoked), pass_name=name, request=request,
                context_hashes={"source": source.source_sha256}, raw_observation=payload,
                response_text="first invalid text" if ordinal == 1 else json.dumps(parsed),
                attempt_event=event)
            if name == "edge_review_pass":
                expected_refs.append((str(path), sha))
        if fail_review and name == "edge_review_pass":
            return _WorkerOutcome({"kind": "provider_failure", "failure_code": "STRUCTURED_OUTPUT_INVALID",
                "observation": {**payload, "state": "failed", "failure_code": "STRUCTURED_OUTPUT_INVALID",
                                "private_provider_field": "EXCLUDE_PRIVATE_MARKER"}}, False)
        return _WorkerOutcome({"kind": "result", "result": TextResult(
            text=json.dumps(parsed), parsed=parsed, observation=obs).model_dump(mode="json")}, False)

    monkeypatch.setattr(bounded, "_execute_in_owned_process", worker)
    client = BoundedRecapPassClient(bounded.RecapExecutionLimits(provider="openrouter", model=DEEPSEEK_MODEL),
        response_artifact_dir=evidence_dir, request_context_hashes={"source": source.source_sha256})
    client.private_client_field = "EXCLUDE_PRIVATE_MARKER"
    result = run_production_extraction(ProductionExtractionRequest(repo_root=tmp_path, source=source,
        profile_id=PROFILE.profile_id, profile_version=PROFILE.profile_version,
        model_id=DEEPSEEK_MODEL, allow_llm=True, category_client=client, output_dir=tmp_path / "out"))
    assert len(invoked) == 6 and len(client.calls) == 6, (client.calls, result.diagnostics)  # 6 invocations != 12 attempts.
    assert bool(result.failure_kind) is fail_review
    assert result.run.status.value == ("failed" if fail_review else "reviewable")
    ref = result.run.components["raw_model_response"]
    data = get_component_bytes(run_id=result.run.run_id, kind=ref.kind, content_sha256=ref.sha256)
    assert hashlib.sha256(data).hexdigest() == ref.sha256
    assert b"EXCLUDE_PRIVATE_MARKER" not in data
    bundle = json.loads(data)
    observation = bundle["execution_observations"][-1]["observation"]
    assert {key: observation[key] for key in (
        "provider_attempt_count", "conformance_retry_count", "transport_retry_count",
        "input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens",
        "latency_ms", "provider_response_id", "cost_usd")} == {
        "provider_attempt_count": 2, "conformance_retry_count": 1, "transport_retry_count": 0,
        "input_tokens": 101, "output_tokens": 23, "cached_input_tokens": 17,
        "reasoning_tokens": 5, "latency_ms": 12, "provider_response_id": "response-known", "cost_usd": None}
    refs = bundle["execution_observations"][-1]["attempt_evidence"]
    assert [(item["path"], item["sha256"]) for item in refs] == expected_refs
    assert [item["ordinal"] for item in refs] == [1, 2]
    for path, sha in expected_refs:
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha
    child = subprocess.run([sys.executable, "-c", '''
import json,hashlib,sys
from pathlib import Path
from apps.live_control_server.services.graph_run_registry import get_extraction_run
from application_state.ingest.components import get_component_bytes
root=Path(sys.argv[1]); run=get_extraction_run(root,sys.argv[2]); ref=run.components['raw_model_response']
data=get_component_bytes(run_id=run.run_id,kind=ref.kind,content_sha256=ref.sha256); assert hashlib.sha256(data).hexdigest()==ref.sha256
row=json.loads(data)['execution_observations'][-1]
assert row['observation']['provider_attempt_count']==2 and row['observation']['conformance_retry_count']==1
for item in row['attempt_evidence']: assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
print('attempt-evidence-reopened')
''', str(tmp_path), result.run.run_id], env=dict(os.environ), text=True, capture_output=True)
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == "attempt-evidence-reopened"


def test_version14_schema_and_prompt_bytes_remain_frozen():
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    graph = {"nodes": [], "edges": [{"edge_id": "e035"}]}
    rows = [{"source_span_ref_id": "s", "text": "source"}]
    assert review_prompt(graph, rows) == json.dumps({"source_packet": rows,
        "endpoint_navigation_not_accepted_truth": [], "edge_proposals": graph["edges"]},
        ensure_ascii=False, allow_nan=False)
    assert schema_for_pass_spec(PROFILE.edge_review_pass) == {"type": "object", "properties": {
        "retained_edge_ids": {"type": "array", "items": {"type": "string"}}},
        "required": ["retained_edge_ids"], "additionalProperties": False}


@pytest.mark.parametrize('bad', [(), [], ('',), (' ',), (1,), ('e035', 'e035')])
def test_specialized_catalog_is_immutable_and_rejects_bad_ids(bad):
    from dataclasses import replace
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_CONSTRAINED_REVIEW_PROFILE as profile
    with pytest.raises(ValueError):
        replace(profile.edge_review_pass, allowed_edge_ids=bad)


def test_unbound_specialized_spec_cannot_execute_and_bound_schema_is_exact():
    from dataclasses import replace, FrozenInstanceError
    import jsonschema
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_CONSTRAINED_REVIEW_PROFILE as profile
    spec = profile.edge_review_pass
    with pytest.raises(ValueError, match='unbound'):
        schema_for_pass_spec(spec)
    from src.graph_memory.extraction.bounded_recap_execution import RecapExecutionLimits
    client = BoundedRecapPassClient(RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL),
        engine_factory=lambda: pytest.fail('unbound spec must not execute'))
    with pytest.raises(ValueError, match='unbound'):
        client.run_pass(spec.pass_id, model_id=DEEPSEEK_MODEL, instructions='test', user_content='test', pass_spec=spec)
    assert not client.calls
    bound = replace(spec, allowed_edge_ids=('e035', 'e040'))
    with pytest.raises(FrozenInstanceError):
        bound.allowed_edge_ids = ('e034',)
    schema = schema_for_pass_spec(bound)
    assert schema['properties']['retained_edge_ids'] == {'type': 'array',
        'items': {'type': 'string', 'enum': ['e035', 'e040']}, 'uniqueItems': True}
    jsonschema.validate({'retained_edge_ids': []}, schema)
    for values in [['e034'], ['e035', 'e035']]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({'retained_edge_ids': values}, schema)


def test_version15_changes_only_review_request_and_keeps_application_guard():
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_CONSTRAINED_REVIEW_PROFILE as profile
    old, new = Client(), Client()
    a = run_category_pipeline(old, options())
    b = run_category_pipeline(new, options(profile=profile))
    assert old.prompts[:-1] == new.prompts[:-1]
    assert a.candidate_graph == b.candidate_graph
    assert json.loads(new.prompts[-1])['allowed_edge_ids'] == ['edge:leads']
    with pytest.raises(CategoryGraphExtractionError):
        run_category_pipeline(Client(retained=['unknown']), options(profile=profile))
    empty = Client(payload={'edge_pass': {'observation_edges': []}})
    run_category_pipeline(empty, options(profile=profile))
    assert len(empty.calls) == 5


@pytest.mark.parametrize('returned', ['e035', 'e034'])
def test_real_bounded_catalog_excludes_role_removed_id_and_retains_registered_failure(
    tmp_path, application_state_dsn, monkeypatch, returned,
):
    from src.graph_memory.extraction import bounded_recap_execution as bounded
    from src.graph_memory.extraction._recap_inference_worker import _WorkerOutcome
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_CONSTRAINED_REVIEW_PROFILE as profile
    from src.graph_memory.extraction.category_candidate_graph_extractor import source_packet_rows_from_span_index
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from src.graph_memory.extraction.graph_preview_runner import ProductionExtractionRequest, run_production_extraction
    from src.graph_memory.predicate_catalog import predicate_family_for_type
    from tests.test_graph_preview_runner import _admit_worldbuilding
    from tests.test_bounded_recap_execution import deepseek_observation
    from generationengine.types import TextResult

    text = 'Barin Stonefoot – Proprietor of Coppervein Mining Co.\n\nMayor Elara owns the Ledger Inn.\n'
    source = _admit_worldbuilding(tmp_path, text)
    rows = source_packet_rows_from_span_index(source.source_span_index, source_text=source.source_text)
    refs = [{'source_span_ref_id': row['source_span_ref_id'], 'anchor_quotes': [row['text']]} for row in rows]
    assert len(refs) == 2
    def node(ident, label, kind, index):
        return dict(node_id=ident, label=label, node_type=kind, description=rows[index]['text'],
                    importance='medium', evidence_refs=[refs[index]])
    payloads = {spec.pass_id: {key: [] for key in schema_for_pass_spec(spec)['required']}
                for spec in profile.node_passes}
    payloads['actor_pass']['observation_nodes'] = [node('a:barin', 'Barin Stonefoot', 'character', 0),
        node('a:elara', 'Mayor Elara', 'character', 1)]
    payloads['location_pass']['observation_nodes'] = [node('l:copper', 'Coppervein Mining Co.', 'location', 0),
        node('l:ledger', 'Ledger Inn', 'location', 1)]
    payloads['edge_pass'] = {'observation_edges': [dict(edge_id=ident, from_node_id=actor, to_node_id=place,
        label='owns', relationship_type='owns', predicate_family=predicate_family_for_type('owns'),
        evidence_refs=[refs[index]]) for ident, actor, place, index in [
            ('e034', 'a:barin', 'l:copper', 0), ('e035', 'a:elara', 'l:ledger', 1)]]}
    names = [spec.pass_id for spec in profile.node_passes] + ['edge_pass', 'edge_review_pass']
    seen = []
    def worker(factory, request_value, *, deadline, attempt_evidence=None):
        name = names[len(seen)]
        seen.append(name)
        if name == 'edge_review_pass':
            selection = request_value['json_schema']['properties']['retained_edge_ids']
            assert selection == {'type': 'array', 'items': {'type': 'string', 'enum': ['e035']}, 'uniqueItems': True}
            prompt = json.loads(request_value['user_prompt'])
            assert prompt['allowed_edge_ids'] == ['e035']
            assert [edge['edge_id'] for edge in prompt['edge_proposals']] == ['e035']
            parsed = {'retained_edge_ids': [returned]}
        else:
            parsed = payloads[name]
        return _WorkerOutcome({'kind': 'result', 'result': TextResult(text=json.dumps(parsed), parsed=parsed,
            observation=deepseek_observation()).model_dump(mode='json')}, False)
    monkeypatch.setattr(bounded, '_execute_in_owned_process', worker)
    client = BoundedRecapPassClient(bounded.RecapExecutionLimits(provider='openrouter', model=DEEPSEEK_MODEL))
    result = run_production_extraction(ProductionExtractionRequest(repo_root=tmp_path, source=source,
        profile_id=profile.profile_id, profile_version=profile.profile_version, model_id=DEEPSEEK_MODEL,
        allow_llm=True, category_client=client, output_dir=tmp_path / 'out'))
    assert len(client.calls) == len(seen) == 6
    if returned == 'e035':
        assert result.failure_kind is None and result.run.status.value == 'reviewable'
        assert [edge['edge_id'] for edge in result.candidate_graph['edges']] == ['e035']
    else:
        assert result.failure_kind and result.run.status.value == 'failed' and result.candidate_graph is None
        assert client.calls[-1]['consumer_failure'] == 'ValidationError'
    ref = result.run.components['raw_model_response']
    data = get_component_bytes(run_id=result.run.run_id, kind=ref.kind, content_sha256=ref.sha256)
    assert hashlib.sha256(data).hexdigest() == ref.sha256
    bundle = json.loads(data)
    assert len(bundle['completed_passes']) == (6 if returned == 'e035' else 5)
    assert bundle['execution_observations'][-1]['observation']['provider_attempt_count'] == 1
    assert bundle['execution_observations'][-1]['observation']['cost_usd'] is None


def test_prebound_profile_rejects_before_writer_or_reviewer_inference():
    from dataclasses import replace
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import GAZETTEER_CONSTRAINED_REVIEW_PROFILE as profile
    prebound = replace(profile, edge_review_pass=replace(profile.edge_review_pass, allowed_edge_ids=('edge:leads',)))
    client = Client()
    with pytest.raises(CategoryGraphExtractionError, match='must be unbound'):
        run_category_pipeline(client, options(profile=prebound))
    assert not client.calls


@pytest.mark.parametrize('provider,model', [
    ('openai','gpt-6.1-sol'), ('openai','gpt-6-luna'),
    ('vercel','moonshotai/kimi-k3.1-pro'), ('vercel','anthropic/claude-haiku-5.5'),
    ('vercel','google/gemini-3.8-flash'), ('vercel','anthropic/claude-sonnet-5.5'),
    ('openrouter','vendor/new-model'),
])
def test_advisory_uses_same_explicit_target_and_existing_pass_contract(provider, model):
    client = Client()
    client.limits.provider, client.limits.model = provider, model
    result = run_category_pipeline(client, options(model=model))
    assert [call['pass_name'] for call in client.calls] == [p.pass_id for p in PROFILE.node_passes] + ['edge_pass','edge_review_pass']
    assert result.model_id == model
    assert json.loads(client.prompts[-1])['source_packet'][0]['text'] == BODY
    assert [e['edge_id'] for e in result.candidate_graph['edges']] == ['edge:leads']
