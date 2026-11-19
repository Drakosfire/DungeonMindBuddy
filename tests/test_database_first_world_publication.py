"""Native first-World lifecycle and retained historical database-evidence boundaries."""
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
        # Current database-owned components can expose object locators without
        # any file mirror. Guard every path below, deleting only actual mirrors.
        if path.is_file():
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


def _native_stage_case(monkeypatch, tmp_path, dsn, *, admitted=False, one_paragraph=False):
    """Real prepared reservation/source in fixture-owned APP and Core databases."""
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresNativeSourceEvidenceRepository
    from apps.live_control_server import config
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldPrepareRequest
    from apps.live_control_server.services import native_first_world_publication as native
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import admit_native_world_source

    if one_paragraph:
        import tests._cutover_d3a_blocker_safe_fixtures as helpers
        original_save = helpers.save_page
        monkeypatch.setattr(helpers, "save_page", lambda root, document, text:
            original_save(root, document, "Worldbuilding source for promote. A second paragraph."))
    case = _case(monkeypatch, tmp_path)
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "native-first-world-test-only")
    monkeypatch.setattr(config, "world_graph_authority_database_url", lambda: dsn)
    repository = PostgresNativeSourceEvidenceRepository(PostgresDatabase(dsn))
    if admitted:
        result = admit_native_world_source(tmp_path, case.baseline.workspace_document_id,
            expected_revision=int(case.baseline.workspace_document_revision),
            expected_body_sha256=case.resolved.source_revision_id.removeprefix("sha256:"))
        assert result.state == "admitted"
    request = NativeFirstWorldPrepareRequest.model_validate({
        "schema": "dmb_native_first_world_prepare_request_v1", "runId": case.request.run_id,
        "decisions": [d.model_dump(mode="json", by_alias=True) for d in case.request.decisions]})
    plan = native.prepare_native_first_world(request, principal_subject="test-operator", repository=repository)
    return SimpleNamespace(**vars(case), repository=repository, plan=plan, native=native)


@pytest.mark.parametrize("admitted", [False, True])
@pytest.mark.parametrize("one_paragraph", [False, True])
def test_native_first_world_stages_real_source_only_parent_exact_bindings_and_readonly_replay(
    native_first_world_core_dsn, monkeypatch, tmp_path, admitted, one_paragraph,
):
    from apps.live_control_server.services.native_first_world_compilation import bind_first_world_native_intent
    from tests.application_state.world_catalog_fixtures import world_snapshot

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn,
                              admitted=admitted, one_paragraph=one_paragraph)
    catalog = world_snapshot()
    parent, bindings = case.native.resolve_native_first_world_stages(case.repository, case.plan)
    assert not parent.entities_by_id and not parent.assertions_by_id and not parent.aliases_by_id
    assert parent.semantic_profile_ref.profile_revision == case.plan.target_profile_ref.profile_revision
    required = case.native._intent(case.plan).audit["source_requirements"]
    assert {b.reviewed_evidence_ref_id for b in bindings} == {r["reviewed_evidence_ref_id"] for r in required}
    packet = bind_first_world_native_intent(case.native._intent(case.plan), parent=parent,
        native_space_id=parent.space_id, bindings=bindings, produced_at=case.native._time(case.plan.created_at))
    assert packet.request.aliases and packet.request.contribution.items
    root = case.repository.get_native_source_admission_receipt(parent.space_id, case.plan.source_stage.admission_id)
    extension = case.repository.get_native_source_evidence_extension_receipt(parent.space_id, case.plan.source_stage.extension_id)
    if one_paragraph:
        assert extension is None
        assert {parent.evidence_by_id[b.proof.evidence_ref_id].evidence_role for b in bindings} == {"context"}
        assert all(b.proof.evidence_ref_id == root.bindings[0].evidence_ref_id for b in bindings)
    else:
        assert extension is not None
        assert {parent.evidence_by_id[b.proof.evidence_ref_id].evidence_role for b in bindings} <= {"support", "context"}
    before = _native_core_counts(native_first_world_core_dsn)
    events = case.repository.head_events(parent.space_id)
    def forbidden(*_args, **_kwargs):
        pytest.fail("immutable source-stage recovery touched a mutable source, reservation or write")
    monkeypatch.setattr(case.native, "_stage_fresh", forbidden)
    monkeypatch.setattr(case.native, "_reservation", forbidden)
    monkeypatch.setattr(case.native.source_owner, "_load_exact_snapshot", forbidden)
    monkeypatch.setattr(case.repository, "publish_revision", forbidden)
    recovered, recovered_bindings = case.native.resolve_native_first_world_stages(case.repository, case.plan, recovery_only=True)
    assert recovered == parent and recovered_bindings == bindings
    assert _native_core_counts(native_first_world_core_dsn) == before
    assert case.repository.head_events(parent.space_id) == events
    assert world_snapshot() == catalog
    assert not case.authority.initializations


def test_native_first_world_stage_recovery_survives_withdrawal_without_source_access_or_writes(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from dungeonmind.application.vnext.native_source_access import open_native_text_source_access_context, open_admitted_native_text
    from graph_memory.vnext.domain_runtime import GM_LABEL, dungeonbuddy_world_domain_contract

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    parent, bindings = case.native.resolve_native_first_world_stages(case.repository, case.plan)
    source = bindings[0].source_revision
    case.repository.withdraw_native_source(space_id=parent.space_id, source_artifact_id=source.source_artifact_id,
                                          source_revision_id=source.source_revision_id)
    before = _native_core_counts(native_first_world_core_dsn)
    def forbidden(*_args, **_kwargs):
        pytest.fail("withdrawn committed-source recovery invoked current access or publication")
    import dungeonmind.application.vnext.native_source_extension as extension
    monkeypatch.setattr(extension, "publish_native_source_evidence_extension", forbidden)
    monkeypatch.setattr(case.native.source_owner, "_load_exact_snapshot", forbidden)
    monkeypatch.setattr(case.native, "_stage_fresh", forbidden)
    recovered, recovered_bindings = case.native.resolve_native_first_world_stages(case.repository, case.plan, recovery_only=True)
    assert recovered == parent and recovered_bindings == bindings
    assert _native_core_counts(native_first_world_core_dsn) == before
    context = open_native_text_source_access_context(repository=case.repository, space_id=parent.space_id,
        revision_id=parent.revision_id, domain_contract=dungeonbuddy_world_domain_contract(), audience_labels=[GM_LABEL])
    assert open_admitted_native_text(context, bindings[0].proof.evidence_ref_id).status == "unavailable"


def test_native_first_world_stage_recovery_refuses_missing_receipts_without_creating_them(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from dungeonmind.domain.errors import PersistenceIntegrityError
    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    before = _native_core_counts(native_first_world_core_dsn)
    with pytest.raises(PersistenceIntegrityError, match="genesis receipt missing"):
        case.native.resolve_native_first_world_stages(case.repository, case.plan, recovery_only=True)
    assert _native_core_counts(native_first_world_core_dsn) == before


def test_native_first_world_stage_lost_extension_ack_recovers_original_parent_epoch_and_time(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    import dungeonmind.application.vnext.native_source_extension as extension
    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    original = extension.publish_native_source_evidence_extension
    called = []
    def lose_ack(**kwargs):
        receipt = original(**kwargs)
        called.append((kwargs["request"].model_dump(mode="json"), receipt))
        raise ConnectionError("lost extension acknowledgement after commit")
    monkeypatch.setattr(extension, "publish_native_source_evidence_extension", lose_ack)
    with pytest.raises(ConnectionError, match="lost extension"):
        case.native.resolve_native_first_world_stages(case.repository, case.plan)
    assert len(called) == 1
    monkeypatch.setattr(extension, "publish_native_source_evidence_extension", lambda **_kwargs:
                        pytest.fail("committed extension was submitted again"))
    parent, bindings = case.native.resolve_native_first_world_stages(case.repository, case.plan)
    actual = case.repository.get_native_source_evidence_extension_receipt(parent.space_id, case.plan.source_stage.extension_id)
    assert actual == called[0][1]
    assert actual.publication_receipt.expected_parent_revision_id == called[0][0]["expected_parent_revision_id"]
    assert bindings
    count = _native_core_counts(native_first_world_core_dsn)
    assert case.native.resolve_native_first_world_stages(case.repository, case.plan, recovery_only=True) == (parent, bindings)
    assert _native_core_counts(native_first_world_core_dsn) == count


@pytest.mark.parametrize("damage", ["intent", "proof", "parent"])
def test_native_first_world_stage_recovery_rejects_extension_corruption(
    native_first_world_core_dsn, monkeypatch, tmp_path, damage,
):
    from dungeonmind.domain.errors import PersistenceIntegrityError
    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    case.native.resolve_native_first_world_stages(case.repository, case.plan)
    original = case.repository.get_native_source_evidence_extension_receipt
    def corrupted(space, operation):
        receipt = original(space, operation)
        if receipt is None or operation != case.plan.source_stage.extension_id:
            return receipt
        if damage == "intent":
            return receipt.model_copy(update={"intent_sha256": "0" * 64})
        if damage == "proof":
            return receipt.model_copy(update={"proofs": [receipt.proofs[0].model_copy(update={"slice_sha256": "0" * 64}), *receipt.proofs[1:]]})
        return receipt.model_copy(update={"publication_receipt": receipt.publication_receipt.model_copy(
            update={"expected_parent_revision_id": "rev:foreign"})})
    monkeypatch.setattr(case.repository, "get_native_source_evidence_extension_receipt", corrupted)
    before = _native_core_counts(native_first_world_core_dsn)
    with pytest.raises((PersistenceIntegrityError, ValueError)):
        case.native.resolve_native_first_world_stages(case.repository, case.plan, recovery_only=True)
    assert _native_core_counts(native_first_world_core_dsn) == before


def test_native_first_world_stage_unapplied_write_refuses_source_epoch_drift(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn, admitted=True)
    stage = case.plan.source_stage
    case.repository.withdraw_native_source(space_id=case.plan.native_target.native_world_id,
        source_artifact_id=stage.native_source_artifact_id, source_revision_id=stage.native_source_revision_id)
    before = _native_core_counts(native_first_world_core_dsn)
    with pytest.raises(case.native.ExtractPromoteError) as refusal:
        case.native.resolve_native_first_world_stages(case.repository, case.plan)
    assert refusal.value.code == "native_first_world_source_changed"
    assert _native_core_counts(native_first_world_core_dsn) == before


@pytest.mark.parametrize("admitted", [False, True])
@pytest.mark.parametrize("one_paragraph", [False, True])
def test_native_first_world_confirm_activates_and_recovers_without_mutable_run(
    native_first_world_core_dsn, monkeypatch, tmp_path, admitted, one_paragraph,
):
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldConfirmRequest
    from apps.live_control_server.services.world_container_registry import get_world_container
    from tests.application_state.world_catalog_fixtures import world_snapshot

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn,
                              admitted=admitted, one_paragraph=one_paragraph)
    request = NativeFirstWorldConfirmRequest.model_validate({
        "schema": "dmb_native_first_world_confirm_request_v1",
        "plan": case.plan.model_dump(mode="json", by_alias=True)})
    result = case.native.confirm_native_first_world(request, principal_subject="test-operator",
                                                    repository=case.repository)
    assert result.outcome == "initialized"
    assert result.activation_status == "active" and not result.recovered
    assert result.source_status == "available"
    binding = get_world_container(case.plan.world_id).native_graph_binding
    assert binding.status == "active"
    assert binding.validated_head_revision_id == result.committed_revision_id
    counts = _native_core_counts(native_first_world_core_dsn)
    catalog = world_snapshot()
    def forbidden(*args, **kwargs):
        pytest.fail("committed first-World recovery consulted mutable state or wrote a revision")
    monkeypatch.setattr(case.native, "resolve_promotable_ingest_run", forbidden)
    monkeypatch.setattr(case.native.source_owner, "_load_exact_snapshot", forbidden)
    monkeypatch.setattr(case.repository, "publish_prospective_publication", forbidden)
    recovered = case.native.confirm_native_first_world(request, principal_subject="test-operator",
                                                       repository=case.repository)
    assert recovered.outcome == "already_initialized" and recovered.recovered
    assert recovered.native_publication == result.native_publication
    assert recovered.committed_revision_id == result.committed_revision_id
    assert _native_core_counts(native_first_world_core_dsn) == counts
    assert world_snapshot() == catalog
    assert not case.authority.initializations


def test_native_first_world_reuse_rejects_role_changed_after_real_introduction(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from dungeonmind.domain.errors import PersistenceIntegrityError
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn, admitted=True, one_paragraph=True)
    parent_id = case.plan.source_stage.head_revision_id
    stored = case.repository.get_revision(case.plan.native_target.native_world_id, parent_id)
    import copy
    payload = copy.deepcopy(stored.graph_payload)
    assert len(payload["evidence"]) == 1 and payload["evidence"][0]["evidence_role"] == "context"
    payload["evidence"][0]["evidence_role"] = "support"
    command = PublishKnowledgeRevisionCommand(
        space_id=stored.revision.space_id, parent_revision_id=parent_id, expected_parent_revision_id=parent_id,
        operation_ids=["test-source-only-role-mutation"], graph_schema=stored.revision.graph_schema,
        graph_payload=payload, domain_contract_ref=stored.revision.domain_contract_ref,
        semantic_profile_ref=stored.revision.semantic_profile_ref, migration_origin_ref=None,
        created_at=stored.revision.created_at)
    mutated = case.repository.publish_revision(command)
    parsed = case.native._parsed(case.repository, stored.revision.space_id, mutated.revision.revision_id)
    root = case.repository.get_native_source_admission_receipt(stored.revision.space_id, case.plan.source_stage.admission_id)
    before = _native_core_counts(native_first_world_core_dsn)
    with pytest.raises(PersistenceIntegrityError, match="original evidence role or metadata changed"):
        case.native._existing_bindings(case.repository, parsed, root, case.native._intent(case.plan),
                                      case.repository.open_native_source_view(stored.revision.space_id))
    assert _native_core_counts(native_first_world_core_dsn) == before


@pytest.mark.parametrize("outage", ["app", "core"])
def test_native_first_world_pending_activation_recovers_after_withdrawal_without_mutable_state(
    native_first_world_core_dsn, monkeypatch, tmp_path, outage,
):
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldConfirmRequest
    from apps.live_control_server.services import world_graph_binding as activation

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    request = NativeFirstWorldConfirmRequest.model_validate({"schema": "dmb_native_first_world_confirm_request_v1",
        "plan": case.plan.model_dump(mode="json", by_alias=True)})
    from dungeonmind.domain.errors import PersistenceUnavailableError
    save = activation._save_binding_record
    activate = activation.activate_native_first_world
    def offline(*args, **kwargs):
        if outage == "core":
            raise PersistenceUnavailableError("injected Core read outage after verified graph commit")
        raise activation.WorldGraphBindingError("injected APP outage", status_code=503)
    monkeypatch.setattr(activation, "_save_binding_record" if outage == "app" else "activate_native_first_world", offline)
    pending = case.native.confirm_native_first_world(request, principal_subject="test-operator", repository=case.repository)
    assert pending.outcome == "activation_pending" and pending.activation_status == "pending"
    admission = case.repository.get_native_source_admission_receipt(case.plan.native_target.native_world_id,
                                                                   case.plan.source_stage.admission_id)
    case.repository.withdraw_native_source(space_id=case.plan.native_target.native_world_id,
        source_artifact_id=admission.source_artifact_id, source_revision_id=admission.source_revision_id)
    monkeypatch.setattr(activation, "_save_binding_record", save)
    monkeypatch.setattr(activation, "activate_native_first_world", activate)
    def forbidden(*args, **kwargs):
        pytest.fail("committed recovery reloaded source/run or republished graph")
    monkeypatch.setattr(case.native.source_owner, "_load_exact_snapshot", forbidden)
    monkeypatch.setattr(case.native, "resolve_promotable_ingest_run", forbidden)
    monkeypatch.setattr(case.repository, "publish_prospective_publication", forbidden)
    before = _native_core_counts(native_first_world_core_dsn)
    recovered = case.native.confirm_native_first_world(request, principal_subject="test-operator", repository=case.repository)
    assert recovered.outcome == "already_initialized" and recovered.activation_status == "active"
    assert recovered.source_status == "unavailable" and recovered.recovered
    assert recovered.native_publication == pending.native_publication
    assert _native_core_counts(native_first_world_core_dsn) == before


def test_native_first_world_lost_graph_response_recovers_one_actual_publication(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldConfirmRequest

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    request = NativeFirstWorldConfirmRequest.model_validate({"schema": "dmb_native_first_world_confirm_request_v1",
        "plan": case.plan.model_dump(mode="json", by_alias=True)})
    publish = case.repository.publish_prospective_publication
    calls = []
    def lose_response(*args, **kwargs):
        result = publish(*args, **kwargs)
        calls.append(result.publication_receipt.published_revision_id)
        raise RuntimeError("injected response lost after durable graph commit")
    monkeypatch.setattr(case.repository, "publish_prospective_publication", lose_response)
    result = case.native.confirm_native_first_world(request, principal_subject="test-operator", repository=case.repository)
    assert result.outcome == "initialized" and result.activation_status == "active"
    assert calls == [result.committed_revision_id]
    events = case.repository.head_events(case.plan.native_target.native_world_id)
    assert sum(e.target_revision_id == result.committed_revision_id for e in events) == 1


def test_native_first_world_current_owner_denial_before_graph_is_not_outcome_unknown(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from fastapi import HTTPException
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldConfirmRequest
    from apps.live_control_server.services.world_container_registry import get_world_container

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    request = NativeFirstWorldConfirmRequest.model_validate({"schema": "dmb_native_first_world_confirm_request_v1",
        "plan": case.plan.model_dump(mode="json", by_alias=True)})
    def authorize(world):
        assert world == case.plan.world_id
        if case.repository.get_native_source_evidence_extension_receipt(
                case.plan.native_target.native_world_id, case.plan.source_stage.extension_id) is not None:
            raise HTTPException(status_code=403, detail="owner revoked before graph")
    with pytest.raises(HTTPException) as error:
        case.native.confirm_native_first_world(request, principal_subject="test-operator",
                                               repository=case.repository, authorize_world=authorize)
    assert error.value.status_code == 403
    assert case.repository.get_prospective_publication(case.plan.native_target.native_world_id,
                                                       case.plan.publication_id) is None
    assert get_world_container(case.plan.world_id).native_graph_binding.status == "provisioning"


def test_native_first_world_mounted_local_http_uses_signed_protocol_and_recovers(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    import asyncio
    import httpx
    from fastapi import FastAPI
    from apps.live_control_server.routes.extract_promote import router
    from apps.live_control_server.services import agent_graph_auth as auth

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    monkeypatch.setattr(case.native, "_repository", lambda: case.repository)
    token = "native-first-world-test-local-token-0123456789"
    monkeypatch.setenv(auth.AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv(auth.AUTH_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(auth.LOCAL_OPERATOR_TOKEN_ENV, token)
    app = FastAPI()
    app.include_router(router)
    prepare_body = {"schema": "dmb_native_first_world_prepare_request_v1", "runId": case.request.run_id,
                    "decisions": [d.model_dump(mode="json", by_alias=True) for d in case.request.decisions]}
    path = "/api/live/extract-promote/worldbuilding/first-world"

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 55000)),
                                     base_url="http://testserver") as client:
            before = _native_core_counts(native_first_world_core_dsn)
            denied = await client.post(path + "/prepare", json=prepare_body)
            assert denied.status_code == 401
            headers = {"Authorization": "Bearer " + token}
            forged_proxy = await client.post(path + "/prepare", json=prepare_body,
                                             headers={**headers, "X-Forwarded-For": "127.0.0.1"})
            assert forged_proxy.status_code == 403
            selectors = await client.post(path + "/prepare?world_id=foreign", json=prepare_body, headers=headers)
            assert selectors.status_code == 422
            response = await client.post(path + "/prepare", json=prepare_body, headers=headers)
            assert response.status_code == 200, response.text
            plan = response.json()
            assert plan["schema"] == "dmb_native_first_world_plan_v1" and plan["preparedBy"] == "local_operator"
            assert _native_core_counts(native_first_world_core_dsn) == before
            confirm = {"schema": "dmb_native_first_world_confirm_request_v1", "plan": plan}
            import copy
            forged = copy.deepcopy(confirm)
            forged["plan"]["preparedBy"] = "another-operator"
            denied = await client.post(path + "/confirm", json=forged, headers=headers)
            assert denied.status_code == 409
            assert _native_core_counts(native_first_world_core_dsn) == before
            published = await client.post(path + "/confirm", json=confirm, headers=headers)
            assert published.status_code == 200, published.text
            assert published.json()["activationStatus"] == "active"
            def forbidden(*args, **kwargs):
                pytest.fail("mounted committed recovery reloaded the mutable run")
            monkeypatch.setattr(case.native, "resolve_promotable_ingest_run", forbidden)
            counts = _native_core_counts(native_first_world_core_dsn)
            replay = await client.post(path + "/confirm", json=confirm, headers=headers)
            assert replay.status_code == 200, replay.text
            assert replay.json()["outcome"] == "already_initialized"
            assert replay.json()["nativePublication"] == published.json()["nativePublication"]
            assert _native_core_counts(native_first_world_core_dsn) == counts
    asyncio.run(exercise())
    assert not case.authority.initializations


def test_native_first_world_mounted_hosted_http_current_owner_and_signed_recovery(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from fastapi import FastAPI
    from application_state.world_catalog import service as catalog
    from apps.live_control_server.routes.extract_promote import router
    from apps.live_control_server.services.world_container_registry import _stored_world
    from apps.live_control_server.services import hosted_auth, hosted_native_graph_access as access
    from tests.test_hosted_native_graph_access import _OfflineClient, OWNER, OTHER_OWNER, FRONTEND_ORIGIN

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    stored = _stored_world(case.plan.world_id)
    catalog.save_world(stored.record.model_copy(update={"owner_subject": OWNER}), expected_revision=stored.revision)
    monkeypatch.setattr(case.native, "_repository", lambda: case.repository)
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(hosted_auth.TRUSTED_FRONTEND_ORIGINS_ENV, FRONTEND_ORIGIN)
    monkeypatch.setenv(hosted_auth.HOSTED_WORLD_ACCESS_ENV, json.dumps({case.plan.world_id: [OWNER, OTHER_OWNER]}))
    app = FastAPI()
    app.include_router(router)
    hosted_auth.install_hosted_request_boundary(app, world_scope_resolvers={
        ("POST", access.FIRST_WORLD_PREPARE_PATH): access.resolve_hosted_first_world,
        ("POST", access.FIRST_WORLD_CONFIRM_PATH): access.resolve_hosted_first_world,
    })
    client = _OfflineClient(app)
    prepare = {"schema": "dmb_native_first_world_prepare_request_v1", "runId": case.request.run_id,
               "decisions": [d.model_dump(mode="json", by_alias=True) for d in case.request.decisions]}
    before = _native_core_counts(native_first_world_core_dsn)
    assert client.request("POST", access.FIRST_WORLD_PREPARE_PATH, json=prepare, session="other-session").status_code == 403
    assert client.request("POST", access.FIRST_WORLD_PREPARE_PATH, json=prepare, session=None).status_code == 401
    response = client.request("POST", access.FIRST_WORLD_PREPARE_PATH, json=prepare)
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["preparedBy"] == "hosted_dms:" + OWNER
    assert _native_core_counts(native_first_world_core_dsn) == before
    confirm = {"schema": "dmb_native_first_world_confirm_request_v1", "plan": plan}
    import copy
    forged = copy.deepcopy(confirm)
    forged["plan"]["worldId"] = "foreign"
    assert client.request("POST", access.FIRST_WORLD_CONFIRM_PATH, json=forged).status_code == 403
    assert client.request("POST", access.FIRST_WORLD_CONFIRM_PATH, json=confirm, session="other-session").status_code == 403
    assert _native_core_counts(native_first_world_core_dsn) == before
    published = client.request("POST", access.FIRST_WORLD_CONFIRM_PATH, json=confirm)
    assert published.status_code == 200, published.text
    assert published.json()["activationStatus"] == "active"
    def forbidden(*args, **kwargs):
        pytest.fail("hosted committed receipt recovery reloaded a mutable run")
    from apps.live_control_server.services import promotable_ingest_run
    monkeypatch.setattr(promotable_ingest_run, "resolve_promotable_ingest_run", forbidden)
    monkeypatch.setattr(case.native, "resolve_promotable_ingest_run", forbidden)
    counts = _native_core_counts(native_first_world_core_dsn)
    recovered = client.request("POST", access.FIRST_WORLD_CONFIRM_PATH, json=confirm)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["outcome"] == "already_initialized"
    assert recovered.json()["nativePublication"] == published.json()["nativePublication"]
    assert _native_core_counts(native_first_world_core_dsn) == counts
    assert not case.authority.initializations


@pytest.mark.parametrize("changed", ["run", "parent", "epoch", "reservation", "principal", "body"])
def test_native_first_world_stale_unapplied_review_refuses_without_core_or_app_mutation(
    native_first_world_core_dsn, monkeypatch, tmp_path, changed,
):
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldConfirmRequest
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from apps.live_control_server.services.world_container_registry import _stored_world
    from tests.application_state.world_catalog_fixtures import world_snapshot
    from application_state.world_catalog import service as catalog
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn, admitted=True)
    space = case.plan.native_target.native_world_id
    if changed == "run":
        data = registry.load_reviewable_extraction_data(tmp_path, case.plan.run_id)
        _reseal_extraction_component_digest(case.plan.run_id, kind="candidate_graph",
            digest=hashlib.sha256(data.candidate_bytes).hexdigest(), payload=data.candidate_bytes)
    elif changed == "parent":
        stored = case.repository.get_revision(space, case.plan.source_stage.head_revision_id)
        case.repository.publish_revision(PublishKnowledgeRevisionCommand(
            space_id=space, parent_revision_id=stored.revision.revision_id,
            expected_parent_revision_id=stored.revision.revision_id, operation_ids=["unrelated-source-only-change"],
            graph_schema=stored.revision.graph_schema, graph_payload=stored.graph_payload,
            domain_contract_ref=stored.revision.domain_contract_ref,
            semantic_profile_ref=stored.revision.semantic_profile_ref, migration_origin_ref=None,
            created_at=stored.revision.created_at))
    elif changed == "epoch":
        stage = case.plan.source_stage
        case.repository.withdraw_native_source(space_id=space, source_artifact_id=stage.native_source_artifact_id,
                                              source_revision_id=stage.native_source_revision_id)
    elif changed == "reservation":
        stored = _stored_world(case.plan.world_id)
        binding = stored.record.native_graph_binding.model_copy(update={"provisioning_id": "provision:" + "f" * 32})
        catalog.save_world(stored.record.model_copy(update={"native_graph_binding": binding}), expected_revision=stored.revision)
    elif changed == "body":
        from tests.page_fixtures import save_page
        save_page(tmp_path, case.plan.workspace_document_id, "Changed committed worldbuilding source.")
    counts, app = _native_core_counts(native_first_world_core_dsn), world_snapshot()
    request = NativeFirstWorldConfirmRequest.model_validate({"schema": "dmb_native_first_world_confirm_request_v1",
        "plan": case.plan.model_dump(mode="json", by_alias=True)})
    from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import NativeWorldSourceAdmissionError
    from graph_memory.worldbuilding_write_plan import WorldbuildingWritePlanError
    with pytest.raises((ExtractPromoteError, NativeWorldSourceAdmissionError, WorldbuildingWritePlanError)):
        case.native.confirm_native_first_world(request, repository=case.repository,
            principal_subject="wrong-principal" if changed == "principal" else "test-operator")
    assert _native_core_counts(native_first_world_core_dsn) == counts
    assert world_snapshot() == app
    assert case.repository.get_prospective_publication(space, case.plan.publication_id) is None


def test_native_first_world_without_custom_edge_does_not_publish_profile_transition(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from apps.live_control_server.models.native_first_world_publication import (
        NativeFirstWorldPrepareRequest, NativeFirstWorldConfirmRequest,
    )
    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    decisions = [d.model_dump(mode="json", by_alias=True) for d in case.request.decisions]
    for row in decisions:
        if row["decision"] == "accept":
            row["decision"] = "reject"
    plan = case.native.prepare_native_first_world(NativeFirstWorldPrepareRequest.model_validate({
        "schema": "dmb_native_first_world_prepare_request_v1", "runId": case.plan.run_id, "decisions": decisions}),
        principal_subject="test-operator", repository=case.repository)
    assert plan.target_profile_ref.profile_revision == "1"
    result = case.native.confirm_native_first_world(NativeFirstWorldConfirmRequest.model_validate({
        "schema": "dmb_native_first_world_confirm_request_v1", "plan": plan.model_dump(mode="json", by_alias=True)}),
        principal_subject="test-operator", repository=case.repository)
    assert result.activation_status == "active"
    assert case.repository.get_publication_receipt(plan.native_target.native_world_id,
                                                   plan.source_stage.profile_transition_id) is None
    parsed = case.native._parsed(case.repository, plan.native_target.native_world_id, result.committed_revision_id)
    assert parsed.semantic_profile_ref.profile_revision == "1"


def test_native_first_world_lost_extension_ack_is_typed_unknown_and_retry_uses_original_stage(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldConfirmRequest
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    import dungeonmind.application.vnext.native_source_extension as extension
    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    request = NativeFirstWorldConfirmRequest.model_validate({"schema": "dmb_native_first_world_confirm_request_v1",
        "plan": case.plan.model_dump(mode="json", by_alias=True)})
    publish = extension.publish_native_source_evidence_extension
    def lose_response(**kwargs):
        publish(**kwargs)
        raise ConnectionError("injected lost durable extension response")
    monkeypatch.setattr(extension, "publish_native_source_evidence_extension", lose_response)
    with pytest.raises(ExtractPromoteError) as error:
        case.native.confirm_native_first_world(request, principal_subject="test-operator", repository=case.repository)
    assert error.value.code == "native_first_world_outcome_unknown" and error.value.status_code == 503
    prior = case.repository.get_native_source_evidence_extension_receipt(case.plan.native_target.native_world_id,
                                                                       case.plan.source_stage.extension_id)
    assert prior is not None
    monkeypatch.setattr(extension, "publish_native_source_evidence_extension",
                        lambda **kwargs: pytest.fail("committed extension was repeated"))
    result = case.native.confirm_native_first_world(request, principal_subject="test-operator", repository=case.repository)
    assert result.activation_status == "active"
    assert case.repository.get_native_source_evidence_extension_receipt(case.plan.native_target.native_world_id,
                                                                       case.plan.source_stage.extension_id) == prior


def test_native_first_world_deterministic_graph_conflict_keeps_original_type_and_zero_graph_mutation(
    native_first_world_core_dsn, monkeypatch, tmp_path,
):
    from dungeonmind.domain.errors import ImmutableRevisionConflictError
    from apps.live_control_server.models.native_first_world_publication import NativeFirstWorldConfirmRequest
    from tests.application_state.world_catalog_fixtures import world_snapshot

    case = _native_stage_case(monkeypatch, tmp_path, native_first_world_core_dsn)
    case.native.resolve_native_first_world_stages(case.repository, case.plan)
    counts, app = _native_core_counts(native_first_world_core_dsn), world_snapshot()
    conflict = ImmutableRevisionConflictError("injected deterministic zero-commit graph conflict")
    def refuse(*args, **kwargs):
        raise conflict
    monkeypatch.setattr(case.repository, "publish_prospective_publication", refuse)
    request = NativeFirstWorldConfirmRequest.model_validate({"schema": "dmb_native_first_world_confirm_request_v1",
        "plan": case.plan.model_dump(mode="json", by_alias=True)})
    with pytest.raises(ImmutableRevisionConflictError) as error:
        case.native.confirm_native_first_world(request, principal_subject="test-operator", repository=case.repository)
    assert error.value is conflict
    assert _native_core_counts(native_first_world_core_dsn) == counts
    assert world_snapshot() == app
    assert case.repository.get_prospective_publication(case.plan.native_target.native_world_id,
                                                       case.plan.publication_id) is None
