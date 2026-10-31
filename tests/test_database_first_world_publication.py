"""First-World consumers use exact database evidence; native writes are never invoked."""
from pathlib import Path
import hashlib
import json
from types import SimpleNamespace

import psycopg
import pytest

from apps.live_control_server.models.extract_promote import (
    FirstWorldGraphConfirmRequest, FirstWorldGraphPrepareRequest,
)
from apps.live_control_server.ports.world_graph_initialization import WorldGraphInitializationState
from apps.live_control_server.services import first_world_graph_publication as service
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
from tests._cutover_d3a_blocker_safe_fixtures import (
    first_world_decisions, first_world_prepare_body, write_glass_orchard_bld08_run,
    _reseal_extraction_component_digest,
)

pytestmark = pytest.mark.usefixtures("application_state_dsn")


class ReachedNativeBoundary(Exception):
    pass


class NoPublicationAuthority:
    def __init__(self):
        self.preflights = []
        self.initializations = []

    def probe(self, world):
        return WorldGraphInitializationState(world_id=world, state="uninitialized")

    def preflight(self, request):
        self.preflights.append(request)

    def initialize(self, request):
        self.initializations.append(request)
        raise ReachedNativeBoundary("test stopped before any native publication")


def _case(monkeypatch, root, *, custom_span=False):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(root))
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(root / "graph"))
    monkeypatch.setenv("DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT", str(root / "held-live-graph"))
    monkeypatch.setattr(service.live_config, "repo_root", lambda: root)
    run_id, _ = write_glass_orchard_bld08_run(root)
    if custom_span:
        from graph_memory.source_span import build_stable_source_span_id
        data = registry.load_reviewable_extraction_data(root, run_id)
        index = json.loads(data.span_bytes)
        span = index["spans"][0].copy()
        span["start_line"], span["end_line"] = 1, len(data.source_bytes.decode().splitlines())
        span["source_span_id"] = build_stable_source_span_id(
            source_artifact_id=data.run.source_artifact_id, content_sha256=data.source_artifact.content_sha256,
            start_line=span["start_line"], end_line=span["end_line"],
        )
        assert span["source_span_id"] not in {row["source_span_id"] for row in index["spans"]}
        index["spans"] = [span]
        candidate = json.loads(data.candidate_bytes)
        for row in [*candidate["nodes"], *candidate["edges"]]:
            for ref in row["evidence_refs"]:
                ref["source_span_ref_id"] = span["source_span_id"]
        # Explicit fixture change to the run-owned database components. Old file
        # mirrors remain stale and must not replace this custom run-wide span.
        for kind, payload in (("candidate_graph", candidate), ("source_span_index", index)):
            raw = json.dumps(payload, sort_keys=True).encode()
            _reseal_extraction_component_digest(run_id, kind=kind,
                digest=hashlib.sha256(raw).hexdigest(), payload=raw)
    resolved = resolve_promotable_ingest_run(run_id, root=root)
    authority = NoPublicationAuthority()
    monkeypatch.setattr(service, "get_world_graph_initialization_authority", lambda **_: authority)
    request = FirstWorldGraphPrepareRequest.model_validate(first_world_prepare_body(run_id, first_world_decisions()))
    baseline = service.prepare_first_world(request)
    # The outer resolver still has a component-file gate. Pin its already-resolved
    # identity so this test exercises the publication consumer, not that successor.
    monkeypatch.setattr(service, "resolve_promotable_ingest_run", lambda *_a, **_k: resolved)
    return SimpleNamespace(root=root, resolved=resolved, authority=authority, request=request, baseline=baseline)


def _guard_evidence_files(monkeypatch, case):
    paths = {case.resolved.normalized_recap_path, case.resolved.candidate_graph_path,
             case.resolved.source_span_index_path}
    for path in paths:
        path.unlink()
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path in paths:
            pytest.fail("publication reopened an evidence-file mirror")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)


@pytest.mark.parametrize("custom_span", [False, True])
def test_prepare_and_confirm_use_same_sealed_database_input_without_evidence_files(monkeypatch, tmp_path, custom_span):
    case = _case(monkeypatch, tmp_path, custom_span=custom_span)
    _guard_evidence_files(monkeypatch, case)
    plan = service.prepare_first_world(case.request)
    assert plan == case.baseline
    assert len(case.authority.preflights) == 2
    with pytest.raises(ReachedNativeBoundary):
        service.confirm_first_world(FirstWorldGraphConfirmRequest(plan=plan))
    assert len(case.authority.preflights) == 3
    command = case.authority.initializations[0]
    assert command.source_plan_sha256 == plan.plan_digest
    assert command.source_revision_token == case.resolved.source_revision_id
    assert command.reviewed_contribution == case.authority.preflights[0].reviewed_contribution
    if custom_span:
        data = registry.load_reviewable_extraction_data(tmp_path, case.resolved.run_id)
        expected_span = data.span_index.spans[0].source_span_id
        evidence = [row for assertion in command.reviewed_contribution.accepted_assertions
                    for row in (assertion.value or {}).get("evidence", [])]
        assert evidence and {row["source_span_ref_id"] for row in evidence} == {expected_span}


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_database_failure_cannot_use_valid_mirrors_or_invoke_initialization(
    monkeypatch, tmp_path, application_state_dsn, kind, violation,
):
    case = _case(monkeypatch, tmp_path)
    before = len(case.authority.preflights)
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s",
                             (case.resolved.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s",
                             (case.resolved.source_artifact_id,))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s",
                         (case.resolved.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s",
                         (b"corrupt", case.resolved.run_id, kind))
    for action in (
        lambda: service.prepare_first_world(case.request),
        lambda: service.confirm_first_world(FirstWorldGraphConfirmRequest(plan=case.baseline)),
    ):
        with pytest.raises(service.ExtractPromoteError) as failure:
            action()
        assert failure.value.code == "run_not_promotable"
    assert len(case.authority.preflights) == before
    assert case.authority.initializations == []
    assert registry.get_extraction_run(tmp_path, case.resolved.run_id).status.value == "reviewable"
