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
    assert registry.get_extraction_run(case.resolved.run_id).status.value == "reviewable"


from apps.live_control_server.services import extract_promote as facade
from apps.live_control_server.services import first_world_graph_publication as owner


@pytest.mark.parametrize("operation", ["prepare_first_world", "confirm_first_world"])
def test_facade_forwards_exact_authorizer_and_preserves_denial(monkeypatch, operation):
    request = object()
    response = object()
    seen = []

    def authorize(world_id):
        seen.append(world_id)
        if world_id == "forbidden-world":
            raise PermissionError("World access denied")

    def implementation(value, *, authorize_world):
        assert value is request
        assert authorize_world is authorize
        authorize_world("allowed-world")
        return response

    monkeypatch.setattr(owner, operation, implementation)
    assert getattr(facade, operation)(request, authorize_world=authorize) is response
    assert seen == ["allowed-world"]

    def denied(value, *, authorize_world):
        assert value is request
        authorize_world("forbidden-world")
        pytest.fail("publication must stop after authorization denial")

    monkeypatch.setattr(owner, operation, denied)
    with pytest.raises(PermissionError, match="World access denied"):
        getattr(facade, operation)(request, authorize_world=authorize)
    assert seen == ["allowed-world", "forbidden-world"]


@pytest.mark.parametrize("operation", ["prepare_first_world", "confirm_first_world"])
def test_internal_call_without_authorizer_preserves_optional_contract(monkeypatch, operation):
    request = object()
    response = object()

    def implementation(value, *, authorize_world):
        assert value is request
        assert authorize_world is None
        return response

    monkeypatch.setattr(owner, operation, implementation)
    assert getattr(facade, operation)(request) is response


@pytest.fixture
def native_first_world_core_dsn(monkeypatch):
    from tests.test_native_recap_source_admission import native_core_dsn
    yield from native_core_dsn.__wrapped__(monkeypatch)


def _native_core_counts(dsn):
    from psycopg import sql
    with psycopg.connect(dsn) as conn:
        names = [row[0] for row in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='dungeonmind' ORDER BY tablename")]
        return {name: conn.execute(sql.SQL("SELECT count(*) FROM dungeonmind.{}").format(
                    sql.Identifier(name))).fetchone()[0] for name in names}


@pytest.mark.parametrize("admitted", [False, True])
@pytest.mark.parametrize("one_paragraph", [False, True])
def test_native_first_world_prepare_is_read_only_with_absent_or_admitted_source(
    native_first_world_core_dsn, application_state_dsn, monkeypatch, tmp_path, admitted, one_paragraph,
):
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresNativeSourceEvidenceRepository
    from apps.live_control_server import config
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldPrepareRequest
    from apps.live_control_server.services.native_first_world_publication import (
        prepare_native_first_world, decode_native_plan,
    )
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import admit_native_world_source
    from apps.live_control_server.services.world_container_registry import get_world_container
    from tests.application_state.world_catalog_fixtures import world_snapshot

    if one_paragraph:
        import tests._cutover_d3a_blocker_safe_fixtures as helpers
        original_save = helpers.save_page
        monkeypatch.setattr(helpers, "save_page", lambda root, document, text:
            original_save(root, document, "Worldbuilding source for promote. A second paragraph."))
    case = _case(monkeypatch, tmp_path)
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "native-first-world-test-only")
    monkeypatch.setattr(config, "world_graph_authority_database_url", lambda: native_first_world_core_dsn)
    repository = PostgresNativeSourceEvidenceRepository(PostgresDatabase(native_first_world_core_dsn))
    document = case.baseline.workspace_document_id
    if admitted:
        status = admit_native_world_source(tmp_path, document,
            expected_revision=int(case.baseline.workspace_document_revision),
            expected_body_sha256=case.resolved.source_revision_id.removeprefix("sha256:"))
        assert status.state == "admitted"
    before = _native_core_counts(native_first_world_core_dsn)
    world = get_world_container(case.baseline.world_id)
    catalog_before = world_snapshot()
    request = NativeFirstWorldPrepareRequest.model_validate({
        "schema": "dmb_native_first_world_prepare_request_v1", "runId": case.request.run_id,
        "decisions": [d.model_dump(mode="json", by_alias=True) for d in case.request.decisions],
    })
    plan = prepare_native_first_world(request, principal_subject="test-operator", repository=repository)
    assert _native_core_counts(native_first_world_core_dsn) == before
    assert world_snapshot() == catalog_before
    assert plan.source_stage.admission_state == ("admitted" if admitted else "absent")
    assert (plan.source_stage.native_source_artifact_id is not None) == admitted
    assert decode_native_plan(plan, principal_subject="test-operator") == plan
    if one_paragraph and admitted:
        assert plan.source_stage.existing_bindings
        assert {b.evidence_role for b in plan.source_stage.existing_bindings} == {"context"}
        assert all(b.proof.start_byte == 0 and b.proof.end_byte == len("Worldbuilding source for promote. A second paragraph.".encode())
                   for b in plan.source_stage.existing_bindings)
    elif not admitted:
        assert not plan.source_stage.existing_bindings
    assert not case.authority.initializations
