"""Mounted manual API over real APP source owners and public installed WK/Core."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dungeonmind.application.vnext import initialize_empty_knowledge_space
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)

from application_state.ingest.components import persist_component_payload
from application_state.source.service import get_source_markdown
from apps.live_control_server.integrations.dungeonmind import (
    native_world_source_admission as admission,
)
from apps.live_control_server.routes.graph_authoring import router
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import native_manual_knowledge as service
from apps.live_control_server.services.source_artifact_registry import (
    create_source_artifact_from_workspace_document,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)
from graph_memory.source_span import (
    build_source_span_index_for_text,
    source_span_index_to_dict,
)
from graph_memory.vnext.domain_runtime import (
    dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_manual_profile,
)
from tests.test_demo_j1_native_world_source_admission import _committed_source
from tests.test_governed_native_source_publication_adoption import (
    sql_repository as sql_repository,
)

TOKEN = "native-manual-test-operator-token-with-adequate-length"
PATH = "/api/live/graph-authoring/native-manual"
TEXT = "# A🐉 tower\r\n\r\nÉ traveller owns the tower.\r\n"


@pytest.fixture
def manual_case(application_state_dsn, monkeypatch, tmp_path, request):
    for key, value in dict(
        DMB_DEPLOYMENT_ENVIRONMENT="local",
        DMB_AUTH_MODE="local_operator",
        DMB_AGENT_GRAPH_AUTH_MODE="local_operator",
        DMB_AGENT_GRAPH_AUTH_ENVIRONMENT="local",
        DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN=TOKEN,
        DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY="native-manual-test-only-key",
    ).items():
        monkeypatch.setenv(key, value)
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        get_committed_page_snapshot,
    )
    from tests.application_state.world_catalog_fixtures import store_world
    from application_state.world_catalog.types import NativeGraphBindingRecord

    world = create_world_container(name="Manual existing World")
    space = world.native_graph_binding.native_world_id
    mode = getattr(request, "param", "memory")
    database = None
    if mode == "sql":
        repo, database = request.getfixturevalue("sql_repository")
    else:
        repo = InMemoryNativeSourceEvidenceRepository()
    from graph_memory.vnext.domain_runtime import (
        dungeonbuddy_dnd5e_semantic_profile,
        dungeonbuddy_dnd5e_custom_predicate_profile,
        dungeonbuddy_dnd5e_observation_profile,
    )

    profile = {
        "1": dungeonbuddy_dnd5e_semantic_profile,
        "2": dungeonbuddy_dnd5e_custom_predicate_profile,
        "3": dungeonbuddy_dnd5e_observation_profile,
    }.get(mode, dungeonbuddy_dnd5e_manual_profile)()
    domain = dungeonbuddy_world_domain_contract()
    genesis = initialize_empty_knowledge_space(
        repository=repo,
        space_id=space,
        initialization_id="manual-genesis",
        created_at=datetime.now(UTC),
        domain_contract=domain,
        semantic_profile=profile,
    )
    world = store_world(
        world.model_copy(
            update={
                "native_graph_binding": NativeGraphBindingRecord(
                    native_world_id=space,
                    binding_version=3,
                    status="active",
                    validated_at=datetime.now(UTC).isoformat(),
                    validated_head_revision_id=genesis.published_revision_id,
                )
            }
        )
    )
    world, record = _committed_source(
        tmp_path,
        markdown=(
            "É traveller 🐉 owns the tower."
            if mode in {"single", "admission-support"}
            else TEXT
        ),
        world=world,
        provisioned=True,
    )
    saved = get_committed_page_snapshot(tmp_path, record.document_id)
    text = saved.markdown
    monkeypatch.setattr(admission, "_repository", lambda: repo)
    if mode == "admission-support":
        # Compatibility fixture: a valid public admission with SUPPORT, not a
        # claim that today's ordinary saved-page owner chooses SUPPORT by default.
        from dungeonmind.application.vnext import publish_native_text_source_evidence
        from dungeonmind.contracts.vnext.native_source import (
            NativeTextSourceAdmissionV1,
        )

        pending = admission.get_native_world_source_status(
            tmp_path, record.document_id, expected_revision=record.revision
        )
        publish_native_text_source_evidence(
            repository=repo,
            domain_contract=domain,
            semantic_profile=profile,
            request=NativeTextSourceAdmissionV1(
                space_id=space,
                admission_id=pending.admission_id,
                expected_parent_revision_id=repo.get_head(space).head_revision_id,
                created_at=datetime.now(UTC),
                body_text=text,
                expected_body_sha256=sha256(text.encode()).hexdigest(),
                source_classification=admission.SOURCE_CLASSIFICATION,
                authority="primary",
                visibility={"kind": "labels_all", "labels": [service.GM_LABEL]},
                origin={
                    "namespace": admission.ORIGIN_NAMESPACE,
                    "object_id": record.document_id,
                    "revision_id": f"registry-revision:{record.revision}",
                },
                spans=[
                    dict(
                        client_ref=admission.WHOLE_DOCUMENT_SPAN_REF,
                        evidence_role="support",
                        start_byte=0,
                        end_byte=len(text.encode()),
                        expected_slice_sha256=sha256(text.encode()).hexdigest(),
                    )
                ],
            ),
        )
        admitted = admission.get_native_world_source_status(
            tmp_path, record.document_id, expected_revision=record.revision
        )
        assert admitted.state == "admitted"
    else:
        admitted = admission.admit_native_world_source(
            tmp_path,
            record.document_id,
            expected_revision=record.revision,
            expected_body_sha256=sha256(text.encode()).hexdigest(),
        )
    artifact = create_source_artifact_from_workspace_document(
        tmp_path, document_id=record.document_id, expected_revision=record.revision
    )
    source = get_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256,
    )
    index = build_source_span_index_for_text(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256,
        text=text,
    )
    span_bytes = json.dumps(source_span_index_to_dict(index)).encode()
    candidate = b'{"manual_facts_not_extracted":true,"promotable":false}'
    refs = {
        kind: ExtractionRunComponentRef(
            kind=kind, uri="fixture:database-owned", sha256=sha256(raw).hexdigest()
        )
        for kind, raw in [
            ("source_artifact", text.encode()),
            ("candidate_graph", candidate),
            ("source_span_index", span_bytes),
        ]
    }
    run = registry.create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=world.world_id,
        session_id=None,
        profile_id="manual-test:held-extraction",
        status=ExtractionRunStatus.VALIDATED,
        components=refs,
    )
    for kind, raw in [
        ("candidate_graph", candidate),
        ("source_span_index", span_bytes),
    ]:
        persist_component_payload(
            run_id=run.run_id, expected_revision=run.revision, kind=kind, payload=raw
        )
    run = registry.update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.REVIEWABLE,
        expected_revision=run.revision,
    )
    monkeypatch.setattr(service.native, "repository", lambda: repo)
    monkeypatch.setattr(service.native, "read_repository", lambda: repo)
    monkeypatch.setattr(service.config, "artifact_data_root", lambda *a: tmp_path)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(
        app, client=("127.0.0.1", 50123), headers={"Authorization": "Bearer " + TOKEN}
    )
    selector = dict(
        schema="dmb_native_manual_context_v1",
        managedWorldId=world.world_id,
        documentId=record.document_id,
        documentRevision=record.revision,
        bodySha256=artifact.content_sha256,
        runId=str(run.run_id),
        runRevision=run.revision,
    )
    return SimpleNamespace(
        repo=repo,
        domain=domain,
        profile=profile,
        client=client,
        selector=selector,
        space=space,
        world=world,
        record=record,
        run=run,
        index=index,
        source=source,
        admitted=admitted,
        dsn=application_state_dsn,
        text=text,
        database=database,
    )


def prepare_packet(c, *, kind="npc", mode="object"):
    context = c.client.post(PATH + "/context", json=c.selector)
    assert context.status_code == 200, context.text
    ctx = context.json()
    witness = ctx["spans"][0]
    # Original full body is CONTEXT. An explicit frozen header subrange is SUPPORT.
    request = dict(
        schema="dmb_native_manual_prepare_v1",
        source=ctx["source"],
        operationId=str(uuid4()),
        createdAt=datetime.now(UTC).isoformat(),
        expectedParentRevisionId=ctx["parentRevisionId"],
        expectedSourceAuthorityEpoch=ctx["sourceAuthorityEpoch"],
        witness=witness,
        operation=dict(
            kind=mode,
            objectKind=kind,
            name="Traveller " + kind,
            description="É description 🐉",
        ),
    )
    response = c.client.post(PATH + "/prepare", json=request)
    assert response.status_code == 200, response.text
    return request, response.json()["plan"]


def rows_snapshot(dsn):
    import psycopg
    from psycopg import sql

    with psycopg.connect(dsn) as conn:
        tables = conn.execute(
            "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"
        ).fetchall()
        return {
            (s, t): sorted(
                json.dumps(r[0], sort_keys=True, default=str)
                for r in conn.execute(
                    sql.SQL("SELECT to_jsonb(t) FROM {}.{} t").format(
                        sql.Identifier(s), sql.Identifier(t)
                    )
                )
            )
            for s, t in tables
        }


def snapshot(c):
    if c.database is not None:
        return rows_snapshot(c.database._database_url)
    return deepcopy(
        {k: v for k, v in c.repo.__dict__.items() if k != "_lock" and not callable(v)}
    )


def test_manual_real_APP_context_prepare_commit_primary_alias(manual_case):
    c = manual_case
    before = snapshot(c)
    request, plan = prepare_packet(c)
    assert snapshot(c) == before
    assert plan["publication"]["evidence"]["mode"] == "new_intervals"
    assert plan["review"]["source"]["appSourceRevisionId"] == str(
        c.source.source_revision_id
    )
    assert plan["publication"]["source_revision_id"] == c.admitted.source_revision_id
    assert plan["publication"]["source_revision_id"] != str(c.source.source_revision_id)
    again = c.client.post(PATH + "/prepare", json=request)
    assert again.json()["plan"] == plan
    committed = c.client.post(
        PATH + "/confirm", json={"schema": "dmb_native_manual_confirm_v1", "plan": plan}
    )
    assert committed.status_code == 200, committed.text
    assert not committed.json()["recovered"]
    after = snapshot(c)
    replay = c.client.post(
        PATH + "/confirm", json={"schema": "dmb_native_manual_confirm_v1", "plan": plan}
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["recovered"]
    assert replay.json()["receipt"] == committed.json()["receipt"]
    assert snapshot(c) == after


def confirm_packet(c, plan):
    return c.client.post(
        PATH + "/confirm", json={"schema": "dmb_native_manual_confirm_v1", "plan": plan}
    )


def read_context(c):
    return service.native.read_context(
        c.repo,
        c.space,
        c.repo.get_head(c.space).head_revision_id,
        None,
        scope_mode="world",
    )[0]


def assert_object(c, receipt, kind="npc", name=None, role=None):
    from dungeonmind.application.vnext.entity_reads import EntityReadService
    from dungeonmind.application.vnext.alias_search import AliasSearchReadService

    ids = [
        b["durable_id"]
        for b in receipt["result_bindings"]
        if b["result_kind"] == "entity"
    ]
    assert len(ids) == 1
    read = read_context(c)
    result = EntityReadService().get_complete_entity(read, ids[0])
    expected = name or "Traveller " + kind
    assert [a.alias_text for a in result.aliases] == [expected]
    assert any(
        h.alias.entity_id == ids[0]
        for h in AliasSearchReadService().search_aliases(read, expected).hits
    )
    facts = [service.native.assertion_contract(a) for a in result.assertions]
    assert any(a.predicate == "dnd5e:name" and a.value.value == expected for a in facts)
    assert any(
        a.predicate == "dnd5e:summary" and a.value.value == "É description 🐉"
        for a in facts
    )
    assert any(
        a.predicate == "dnd5e:classification"
        and a.value.term == service.TARGET.buddy_to_dm_kind[kind]
        for a in facts
    )
    assert all(not a.metadata.scope for a in facts)
    for a in facts:
        assert a.metadata.visibility.model_dump() == {
            "kind": "labels_any",
            "labels": ["dungeonbuddy.visibility:gm"],
        }
        assert (
            a.metadata.epistemic_basis,
            a.metadata.claim_mode,
            a.metadata.standing,
        ) == ("asserted", "dungeonbuddy.claim:fact", "established")
        assert a.metadata.temporal_scope.kind == "unknown"
        contexts = [
            m
            for m in a.metadata.domain_metadata
            if m.schema_term == "dungeonbuddy.domain_metadata:world_context_v1"
        ]
        assert len(contexts) == 1
        assert contexts[0].payload == {"role": role or kind}
    return ids[0]


@pytest.mark.parametrize("kind", list(service.TARGET.buddy_to_dm_kind))
def test_all_thirteen_kinds_real_manual_HTTP_readback(manual_case, kind):
    c = manual_case
    _, plan = prepare_packet(c, kind=kind)
    before = rows_snapshot(c.dsn)
    response = confirm_packet(c, plan)
    assert response.status_code == 200, response.text
    assert rows_snapshot(c.dsn) == before
    assert_object(c, response.json()["receipt"], kind)


@pytest.mark.parametrize("role", [None, "npc", "keeper of the gate"])
@pytest.mark.parametrize("manual_case", ["memory", "sql"], indirect=True)
def test_role_retained_without_replacing_kind(manual_case, role):
    c = manual_case
    request, _ = prepare_packet(c)
    request["operation"]["role"] = role
    response = c.client.post(PATH + "/prepare", json=request)
    assert response.status_code == 200, response.text
    plan = response.json()["plan"]
    items = plan["publication"]["contribution"]["items"]
    assert items  # full metadata is asserted from admitted records below
    committed = confirm_packet(c, plan)
    assert committed.status_code == 200, committed.text
    if c.database is not None:
        from dungeonmind.infrastructure.postgres import (
            PostgresNativeSourceEvidenceRepository,
        )

        c.repo = PostgresNativeSourceEvidenceRepository(c.database)
    assert_object(c, committed.json()["receipt"], role=role)


@pytest.mark.parametrize("mode", ["context", "prepare"])
def test_context_and_prepare_no_APP_or_Core_mutation(manual_case, monkeypatch, mode):
    c = manual_case
    before = (snapshot(c), rows_snapshot(c.dsn))

    def forbidden(*a, **k):
        pytest.fail("read-only manual request invoked a mutator")

    monkeypatch.setattr(
        service, "publish_governed_native_source_publication", forbidden
    )
    monkeypatch.setattr(admission, "admit_native_world_source", forbidden)
    from apps.live_control_server.services import (
        source_artifact_registry,
        graph_document_source,
    )
    import graph_memory.source_span as source_span_owner

    monkeypatch.setattr(admission, "initialize_empty_knowledge_space", forbidden)
    monkeypatch.setattr(admission, "publish_native_text_source_evidence", forbidden)
    monkeypatch.setattr(
        source_artifact_registry,
        "create_source_artifact_from_workspace_document",
        forbidden,
    )
    monkeypatch.setattr(
        graph_document_source, "resolve_graph_document_source", forbidden
    )
    monkeypatch.setattr(
        source_span_owner, "build_source_span_index_for_text", forbidden
    )
    if mode == "context":
        response = c.client.post(PATH + "/context", json=c.selector)
        assert response.status_code == 200, response.text
        assert response.json()["manualCapability"]
    else:
        prepare_packet(c)
    assert (snapshot(c), rows_snapshot(c.dsn)) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("documentId", str(uuid4())),
        ("documentRevision", 999),
        ("runId", str(uuid4())),
        ("runRevision", 999),
        ("bodySha256", "0" * 64),
        ("managedWorldId", "foreign"),
    ],
)
def test_context_wrong_exact_selection_refuses(manual_case, field, value):
    c = manual_case
    body = {**c.selector, field: value}
    before = (snapshot(c), rows_snapshot(c.dsn))
    response = c.client.post(PATH + "/context", json=body)
    assert response.status_code in (403, 404, 409, 422), response.text
    assert (snapshot(c), rows_snapshot(c.dsn)) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("appSourceRevisionId", str(uuid4())),
        ("appSourceArtifactId", "foreign"),
        ("spanIndexSha256", "0" * 64),
        ("nativeWorldId", "foreign"),
        ("bindingVersion", 99),
    ],
)
def test_prepare_substituted_commitments_refuse(manual_case, field, value):
    c = manual_case
    body, _ = prepare_packet(c)
    body["source"][field] = value
    before = (snapshot(c), rows_snapshot(c.dsn))
    response = c.client.post(PATH + "/prepare", json=body)
    assert response.status_code in (403, 404, 409, 422), response.text
    assert (snapshot(c), rows_snapshot(c.dsn)) == before


@pytest.mark.parametrize(
    "bad", ["unknown-kind", "role-bypass", "unicode-token", "nested-tamper", "expired"]
)
def test_invalid_request_never_mutates(manual_case, bad):
    c = manual_case
    body, plan = prepare_packet(c)
    if bad in ("unknown-kind", "role-bypass"):
        body["operation"]["objectKind"] = "unknown"
        body["operation"]["role"] = "npc" if bad == "role-bypass" else None
        endpoint, payload = "/prepare", body
    elif bad == "expired":
        body["createdAt"] = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        endpoint, payload = "/prepare", body
    else:
        if bad == "unicode-token":
            plan["token"] = "é"
        else:
            plan["publication"]["aliases"][0]["alias_text"] = "altered"
        endpoint, payload = (
            "/confirm",
            {"schema": "dmb_native_manual_confirm_v1", "plan": plan},
        )
    before = snapshot(c)
    response = c.client.post(PATH + endpoint, json=payload)
    assert response.status_code in (409, 422), response.text
    assert snapshot(c) == before


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_unauthenticated_before_any_IO(manual_case, monkeypatch, headers):
    c = manual_case

    def fail(*a, **k):
        pytest.fail("unauthorized IO")

    monkeypatch.setattr(service, "_source", fail)
    monkeypatch.setattr(service.native, "binding", fail)
    response = c.client.post(
        PATH + "/context",
        json=c.selector,
        headers={**headers, "Authorization": headers.get("Authorization", "")},
    )
    assert response.status_code == 401, response.text


@pytest.mark.parametrize("manual_case", ["memory", "sql"], indirect=True)
def test_all_45_directed_relationship_rules_and_inspectable_descriptions(manual_case):
    c = manual_case
    endpoints = {}
    for kind in service.TARGET.buddy_to_dm_kind:
        _, plan = prepare_packet(c, kind=kind)
        response = confirm_packet(c, plan)
        assert response.status_code == 200, response.text
        endpoints[kind] = dict(
            entityId=assert_object(c, response.json()["receipt"], kind),
            name="Traveller " + kind,
            objectKind=kind,
        )
    alternate_request, _ = prepare_packet(c, kind="location")
    alternate_request["operation"]["name"] = "Other location"
    alternate = c.client.post(PATH + "/prepare", json=alternate_request)
    assert alternate.status_code == 200, alternate.text
    committed = confirm_packet(c, alternate.json()["plan"])
    assert committed.status_code == 200, committed.text
    other_location = dict(
        entityId=assert_object(
            c, committed.json()["receipt"], "location", name="Other location"
        ),
        name="Other location",
        objectKind="location",
    )
    vocabulary = service.TARGET.world_object_loader()
    labels = service._catalog()["predicates"]
    assert len(labels) == 45
    from dungeonmind.domain.canonical import canonical_sha256

    matrix = {
        label: dict(
            term=entry["term"],
            reverse=entry["reverseEndpoints"],
            allowed_pairs=[
                (a, b)
                for a in service.TARGET.buddy_to_dm_kind
                for b in service.TARGET.buddy_to_dm_kind
                if service.mapping.edge_endpoint_kind_admission_reason(
                    buddy_predicate=label,
                    from_buddy_kind=a,
                    to_buddy_kind=b,
                    target=service.TARGET,
                    vocabulary=vocabulary,
                )
                is None
            ],
        )
        for label, entry in labels.items()
    }
    assert (
        canonical_sha256(matrix)
        == "0ac3bb2a41df5ddf129acd3f267bed46940a94676d62d2a028ea65b191a8b371"
    )
    for label in labels:
        a, z = next(
            (a, z)
            for a in endpoints
            for z in endpoints
            if (a != z or a == z == "location")
            and service.mapping.edge_endpoint_kind_admission_reason(
                buddy_predicate=label,
                from_buddy_kind=a,
                to_buddy_kind=z,
                target=service.TARGET,
                vocabulary=vocabulary,
            )
            is None
        )
        if label == "belongs_to":
            a, z = "creature", "npc"
        ctx = c.client.post(PATH + "/context", json=c.selector).json()
        body = dict(
            schema="dmb_native_manual_prepare_v1",
            source=ctx["source"],
            operationId=str(uuid4()),
            createdAt=datetime.now(UTC).isoformat(),
            expectedParentRevisionId=ctx["parentRevisionId"],
            expectedSourceAuthorityEpoch=ctx["sourceAuthorityEpoch"],
            witness=ctx["spans"][0],
            operation=dict(
                kind="relationship",
                source=endpoints[a],
                target=(other_location if a == z else endpoints[z]),
                predicate=label,
                label="Reviewed " + label,
                description="Relationship 🐉 " + label,
            ),
        )
        before = snapshot(c)
        prepared = c.client.post(PATH + "/prepare", json=body)
        assert prepared.status_code == 200, (label, prepared.text)
        assert snapshot(c) == before
        committed = confirm_packet(c, prepared.json()["plan"])
        assert committed.status_code == 200, (label, committed.text)
        read = read_context(c)
        term, reverse = service.mapping.resolve_buddy_predicate_mapping_v4(
            label, target=service.TARGET
        )
        left, right = endpoints[a], (other_location if a == z else endpoints[z])
        subject, target = (right, left) if reverse else (left, right)
        assertion_ids = [
            b["durable_id"]
            for b in committed.json()["receipt"]["result_bindings"]
            if b["result_kind"] == "assertion"
        ]
        assert len(assertion_ids) == 1
        actual = service.native.assertion_contract(
            read.parsed.get_assertion(assertion_ids[0])
        )
        assert actual.predicate == term
        assert actual.subject_entity_id == subject["entityId"]
        assert actual.value.entity_id == target["entityId"]
        assert actual.metadata.domain_metadata[0].payload == {
            "relationship_label": "Reviewed " + label,
            "relationship_context": "Relationship 🐉 " + label,
        }
        assert not actual.metadata.scope
        assert actual.metadata.epistemic_basis == "asserted"


def test_same_operation_competing_preparations_conflict(manual_case):
    c = manual_case
    request, first = prepare_packet(c)
    request["createdAt"] = (
        datetime.fromisoformat(request["createdAt"]) - timedelta(seconds=1)
    ).isoformat()
    second = c.client.post(PATH + "/prepare", json=request)
    assert second.status_code == 200, second.text
    assert first != second.json()["plan"]
    assert confirm_packet(c, first).status_code == 200
    before = snapshot(c)
    conflict = confirm_packet(c, second.json()["plan"])
    assert conflict.status_code == 409, conflict.text
    assert (
        conflict.json()["detail"]["code"]
        == "knowledge_publication_idempotency_conflict"
    )
    assert snapshot(c) == before


@pytest.mark.parametrize("manual_case", ["memory", "sql"], indirect=True)
def test_receipt_first_expired_withdrawn_descendant_no_mutable_reads(
    manual_case, monkeypatch
):
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand

    c = manual_case
    _, plan = prepare_packet(c)
    committed = confirm_packet(c, plan)
    assert committed.status_code == 200, committed.text
    stored = c.repo.get_revision(c.space, c.repo.get_head(c.space).head_revision_id)
    c.repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=c.space,
            parent_revision_id=stored.revision.revision_id,
            expected_parent_revision_id=stored.revision.revision_id,
            operation_ids=["later-head"],
            graph_schema=stored.revision.graph_schema,
            graph_payload=stored.graph_payload,
            domain_contract_ref=stored.revision.domain_contract_ref,
            semantic_profile_ref=stored.revision.semantic_profile_ref,
            migration_origin_ref=stored.revision.migration_origin_ref,
            created_at=datetime.now(UTC),
        )
    )
    c.repo.withdraw_native_source(
        space_id=c.space,
        source_artifact_id=c.admitted.source_artifact_id,
        source_revision_id=c.admitted.source_revision_id,
    )
    before = snapshot(c)

    def fail(*a, **k):
        pytest.fail("immutable replay touched mutable source/head/write")

    for name in (
        "get_committed_page_snapshot",
        "load_reviewable_extraction_data",
        "get_native_world_source_status",
    ):
        monkeypatch.setattr(service, name, fail)
    monkeypatch.setattr(service.sources, "get_source_markdown", fail)
    monkeypatch.setattr(c.repo, "get_head", fail)
    monkeypatch.setattr(c.repo, "open_native_source_view", fail)
    monkeypatch.setattr(c.repo, "publish_governed_native_source_publication", fail)

    class Future(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(UTC) + timedelta(days=2)

    monkeypatch.setattr(service, "datetime", Future)
    replay = confirm_packet(c, plan)
    assert replay.status_code == 200, replay.text
    assert replay.json()["receipt"] == committed.json()["receipt"]
    assert snapshot(c) == before


@pytest.mark.parametrize(
    "damage", ["missing-companion", "missing-child", "corrupt-child", "changed-intent"]
)
def test_recovery_corruption_never_falls_through_to_publish(
    manual_case, monkeypatch, damage
):
    from dataclasses import replace

    c = manual_case
    _, plan = prepare_packet(c)
    response = confirm_packet(c, plan)
    assert response.status_code == 200, response.text
    if damage == "missing-companion":
        del c.repo._source_publication_receipts[
            (c.space, plan["publication"]["publication_id"])
        ]
    elif damage == "missing-child":
        del c.repo._revisions[
            (
                c.space,
                response.json()["receipt"]["publication_receipt"][
                    "published_revision_id"
                ],
            )
        ]
    elif damage == "corrupt-child":
        key = (
            c.space,
            response.json()["receipt"]["publication_receipt"]["published_revision_id"],
        )
        c.repo._revisions[key] = replace(c.repo._revisions[key], _payload_json="{}")
    else:
        plan["publication"]["aliases"][0]["alias_text"] = "Different signed intent"
        from apps.live_control_server.models.native_manual_knowledge import (
            ManualPlanContent,
        )

        content = ManualPlanContent.model_validate(
            {k: v for k, v in plan.items() if k != "token"}
        )
        plan["token"] = service.sign_publication_intent(
            content.model_dump(mode="json", by_alias=True)
        )
    before = snapshot(c)

    def fail(*a, **k):
        pytest.fail("corrupt receipt attempted fresh fallback")

    monkeypatch.setattr(service, "_source", fail)
    monkeypatch.setattr(c.repo, "publish_governed_native_source_publication", fail)
    response = confirm_packet(c, plan)
    assert response.status_code == 409, response.text
    assert not response.json()["detail"]["outcome_unknown"]
    assert snapshot(c) == before


def advance_head(c):
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand

    stored = c.repo.get_revision(c.space, c.repo.get_head(c.space).head_revision_id)
    return c.repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=c.space,
            parent_revision_id=stored.revision.revision_id,
            expected_parent_revision_id=stored.revision.revision_id,
            operation_ids=[str(uuid4())],
            graph_schema=stored.revision.graph_schema,
            graph_payload=stored.graph_payload,
            domain_contract_ref=stored.revision.domain_contract_ref,
            semantic_profile_ref=stored.revision.semantic_profile_ref,
            migration_origin_ref=stored.revision.migration_origin_ref,
            created_at=datetime.now(UTC),
        )
    )


@pytest.mark.parametrize("fault", ["head", "epoch", "binding"])
def test_mid_context_drift_refuses_without_additional_mutation(
    manual_case, monkeypatch, fault
):
    from tests.application_state.world_catalog_fixtures import change_binding

    c = manual_case
    original = service._source
    calls = 0
    after_external = []

    def changed(*a, **k):
        nonlocal calls
        result = original(*a, **k)
        calls += 1
        if calls == 2:
            if fault == "head":
                advance_head(c)
            elif fault == "epoch":
                c.repo.withdraw_native_source(
                    space_id=c.space,
                    source_artifact_id=c.admitted.source_artifact_id,
                    source_revision_id=c.admitted.source_revision_id,
                )
            else:
                change_binding(c.world.world_id, binding_version=4)
            after_external.append((snapshot(c), rows_snapshot(c.dsn)))
        return result

    monkeypatch.setattr(service, "_source", changed)
    response = c.client.post(PATH + "/context", json=c.selector)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == (
        "manual_binding_changed" if fault == "binding" else "manual_authority_changed"
    )
    assert calls == 2 and len(after_external) == 1
    assert (snapshot(c), rows_snapshot(c.dsn)) == after_external[0]


@pytest.mark.parametrize("manual_case", ["sql"], indirect=True)
@pytest.mark.parametrize("mode", ["new_intervals", "existing_support"])
def test_SQL_atomic_reopen_exact_recovery_and_rollback(manual_case, mode, monkeypatch):
    from dungeonmind.infrastructure.postgres import (
        PostgresNativeSourceEvidenceRepository,
    )

    c = manual_case
    if mode == "existing_support":
        _, first = prepare_packet(c)
        assert confirm_packet(c, first).status_code == 200
    request, plan = prepare_packet(c)
    assert plan["publication"]["evidence"]["mode"] == mode
    before = (snapshot(c), rows_snapshot(c.dsn))
    fired = []

    def fault(*a, **k):
        fired.append(True)
        raise ConnectionError("actual after receipt insert rollback fault")

    with monkeypatch.context() as patch:
        patch.setattr(c.repo, "_after_native_receipt_insert", fault)
        failed = confirm_packet(c, plan)
    assert fired
    assert failed.status_code == 503, failed.text
    assert failed.json()["detail"]["outcome_unknown"]
    assert (snapshot(c), rows_snapshot(c.dsn)) == before
    committed = confirm_packet(c, plan)
    assert committed.status_code == 200, committed.text
    c.repo = PostgresNativeSourceEvidenceRepository(c.database)
    assert_object(c, committed.json()["receipt"])
    after = snapshot(c)
    replay = confirm_packet(c, plan)
    assert replay.status_code == 200, replay.text
    assert replay.json()["receipt"] == committed.json()["receipt"]
    assert snapshot(c) == after
    assert rows_snapshot(c.dsn) == before[1]


@pytest.mark.parametrize("error", [ConnectionError, RuntimeError])
def test_writer_lost_ack_resolves_exact_receipt_without_duplicate(
    manual_case, monkeypatch, error
):
    c = manual_case
    _, plan = prepare_packet(c)
    original = c.repo.publish_governed_native_source_publication
    calls = []

    def lost(**kwargs):
        result = original(**kwargs)
        calls.append(result)
        raise error("lost acknowledgement after commit")

    monkeypatch.setattr(c.repo, "publish_governed_native_source_publication", lost)
    response = confirm_packet(c, plan)
    assert response.status_code == 200, response.text
    assert len(calls) == 1 and response.json()["recovered"]
    before = snapshot(c)
    assert confirm_packet(c, plan).json() == response.json()
    assert len(calls) == 1 and snapshot(c) == before


def test_late_host_denial_no_receipt_probe_after_denial(manual_case, monkeypatch):
    from fastapi import HTTPException

    c = manual_case
    _, plan = prepare_packet(c)
    original = service._binding
    calls = []
    denied = []

    def guard(*args, **kwargs):
        calls.append(True)
        if len(calls) == 4:
            denied.append(True)
            raise HTTPException(403, detail={"code": "owner_transferred"})
        return original(*args, **kwargs)

    receipt = c.repo.get_native_source_publication_receipt

    def receipt_guard(*args, **kwargs):
        assert not denied, "receipt probe after host denial"
        return receipt(*args, **kwargs)

    monkeypatch.setattr(service, "_binding", guard)
    monkeypatch.setattr(c.repo, "get_native_source_publication_receipt", receipt_guard)
    before = snapshot(c)
    response = confirm_packet(c, plan)
    assert response.status_code == 403, response.text
    assert denied and len(calls) == 4
    assert snapshot(c) == before


@pytest.mark.parametrize("error", [RuntimeError, ConnectionError])
def test_unclassified_writer_failure_without_receipt_is_unknown(
    manual_case, monkeypatch, error
):
    c = manual_case
    _, plan = prepare_packet(c)
    fired = []

    def failed(**kwargs):
        fired.append(True)
        raise error("actual writer dispatch without known outcome")

    monkeypatch.setattr(c.repo, "publish_governed_native_source_publication", failed)
    before = snapshot(c)
    response = confirm_packet(c, plan)
    assert fired and response.status_code == 503, response.text
    assert response.json()["detail"]["outcome_unknown"]
    assert response.json()["detail"]["retry_original_packet"]
    assert snapshot(c) == before


def test_deterministic_writer_conflict_is_not_unknown(manual_case, monkeypatch):
    from dungeonmind.domain.errors import ImmutableRevisionConflictError

    c = manual_case
    _, plan = prepare_packet(c)

    def failed(**kwargs):
        raise ImmutableRevisionConflictError("known zero commit")

    monkeypatch.setattr(c.repo, "publish_governed_native_source_publication", failed)
    before = snapshot(c)
    response = confirm_packet(c, plan)
    assert response.status_code == 409, response.text
    assert not response.json()["detail"]["outcome_unknown"]
    assert snapshot(c) == before


@pytest.mark.parametrize("manual_case", ["1", "2", "3"], indirect=True)
def test_active_old_profile_context_requires_explicit_transition(manual_case):
    c = manual_case
    before = (snapshot(c), rows_snapshot(c.dsn))
    response = c.client.post(PATH + "/context", json=c.selector)
    assert response.status_code == 200, response.text
    ctx = response.json()
    assert ctx["transitionRequired"] and not ctx["manualCapability"]
    body = dict(
        schema="dmb_native_manual_prepare_v1",
        source=ctx["source"],
        operationId=str(uuid4()),
        createdAt=datetime.now(UTC).isoformat(),
        expectedParentRevisionId=ctx["parentRevisionId"],
        expectedSourceAuthorityEpoch=ctx["sourceAuthorityEpoch"],
        witness=ctx["spans"][0],
        operation=dict(kind="object", objectKind="npc", name="First object"),
    )
    response = c.client.post(PATH + "/prepare", json=body)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "manual_profile_transition_required"
    assert (snapshot(c), rows_snapshot(c.dsn)) == before


@pytest.mark.parametrize("phase", ["prepare", "confirm"])
def test_missing_signing_key_typed_zero_Core_IO(manual_case, monkeypatch, phase):
    c = manual_case
    body, plan = prepare_packet(c)
    monkeypatch.delenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY")

    def fail(*a, **k):
        pytest.fail("missing signing key reached Core/source IO")

    monkeypatch.setattr(service.native, "repository", fail)
    monkeypatch.setattr(service.native, "read_repository", fail)
    monkeypatch.setattr(service, "_source", fail)
    response = (
        c.client.post(PATH + "/prepare", json=body)
        if phase == "prepare"
        else confirm_packet(c, plan)
    )
    assert response.status_code == 503, response.text
    assert not response.json()["detail"]["outcome_unknown"]
    assert response.json()["detail"]["retry_original_packet"] == (phase == "confirm")


def test_resolved_player_denied_before_all_IO(manual_case, monkeypatch):
    from apps.live_control_server.services import agent_graph_auth

    c = manual_case
    monkeypatch.setattr(
        agent_graph_auth,
        "authenticate_native_graph_principal",
        lambda request: agent_graph_auth.NativeGraphPrincipal(
            subject="resolved-player", role="player", auth_method="local_operator"
        ),
    )

    def fail(*a, **k):
        pytest.fail("player reached native/APP IO")

    monkeypatch.setattr(service, "_source", fail)
    monkeypatch.setattr(service.native, "binding", fail)
    response = c.client.post(PATH + "/context", json=c.selector)
    assert response.status_code == 403, response.text


@pytest.mark.parametrize(
    "field,value",
    [("bindingVersion", True), ("documentRevision", "1"), ("runRevision", False)],
)
def test_request_scalar_types_not_coerced(manual_case, field, value):
    c = manual_case
    body, _ = prepare_packet(c)
    body["source"][field] = value
    before = snapshot(c)
    response = c.client.post(PATH + "/prepare", json=body)
    assert response.status_code == 422, response.text
    assert snapshot(c) == before


def test_context_interval_collision_and_UTF8_boundary_refuse(manual_case):
    c = manual_case
    body, _ = prepare_packet(c)
    # The persisted whole-document context range may not silently become support.
    body["witness"].update(
        startByte=0,
        endByte=len(c.text.encode()),
        sliceSha256=sha256(c.text.encode()).hexdigest(),
    )
    # Choose an actual indexed enclosing span only when it contains the whole body;
    # otherwise explicit span membership rejects before the Core collision guard.
    before = snapshot(c)
    response = c.client.post(PATH + "/prepare", json=body)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] in (
        "manual_witness_outside_span",
        "manual_context_interval_collision",
    )
    body, _ = prepare_packet(c)
    dragon = c.text.encode().index("🐉".encode())
    body["witness"].update(
        startByte=dragon + 1,
        endByte=dragon + 2,
        sliceSha256=sha256(c.text.encode()[dragon + 1 : dragon + 2]).hexdigest(),
    )
    response = c.client.post(PATH + "/prepare", json=body)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "manual_witness_utf8_invalid"
    assert snapshot(c) == before


def test_exact_CRLF_witness_uses_original_bytes_not_normalized_text():
    from apps.live_control_server.models.native_manual_knowledge import ManualWitness

    raw = TEXT.encode()
    index = build_source_span_index_for_text(
        source_artifact_id="fixture:raw",
        content_sha256=sha256(raw).hexdigest(),
        text=TEXT,
    )
    span = index.spans[0]
    end = len(TEXT.splitlines(keepends=True)[0].encode())
    assert raw[:end].endswith(b"\r\n") and "🐉".encode() in raw[:end]
    witness = ManualWitness(
        source_span_ref_id=span.source_span_id,
        start_byte=0,
        end_byte=end,
        slice_sha256=sha256(raw[:end]).hexdigest(),
    )
    service._witness(raw, SimpleNamespace(span_index=index), witness)
    with pytest.raises(service.ManualRefused):
        service._witness(
            raw.replace(b"\r\n", b"\n"), SimpleNamespace(span_index=index), witness
        )


def test_corrupt_persisted_index_real_APP_refuses_no_regeneration(manual_case):
    import psycopg

    c = manual_case
    with psycopg.connect(c.dsn) as conn:
        cursor = conn.execute(
            "UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='source_span_index'",
            (b"{}", c.run.run_id),
        )
        assert cursor.rowcount == 1
    before = (snapshot(c), rows_snapshot(c.dsn))
    response = c.client.post(PATH + "/context", json=c.selector)
    assert response.status_code == 500, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "manual_integrity_error"
    assert not detail["outcome_unknown"] and not detail["retry_original_packet"]
    assert (snapshot(c), rows_snapshot(c.dsn)) == before


@pytest.mark.parametrize("failure", ["inactive", "provisioning", "no-head"])
def test_not_currently_published_binding_refuses(manual_case, failure, monkeypatch):
    from tests.application_state.world_catalog_fixtures import change_binding

    c = manual_case
    if failure == "inactive":
        change_binding(c.world.world_id, status="inactive")
    elif failure == "no-head":
        del c.repo._heads[c.space]
    else:
        # A real catalog record with an unactivated reservation is not an active World.
        from application_state.world_catalog.service import create_world

        another = create_world(name="Still provisioning").record
        c.selector["managedWorldId"] = another.world_id
    before = (snapshot(c), rows_snapshot(c.dsn))
    response = c.client.post(PATH + "/context", json=c.selector)
    assert response.status_code in (404, 409), response.text
    if failure == "no-head":
        assert response.json()["detail"]["code"] == "manual_head_missing"
    assert (snapshot(c), rows_snapshot(c.dsn)) == before


def test_extension_support_creation_epoch_retained_but_current_epoch_fenced(
    manual_case,
):
    from dungeonmind.application.vnext import publish_native_source_evidence_extension
    from dungeonmind.contracts.vnext.native_source import (
        NativeSourceEvidenceExtensionV1,
    )

    c = manual_case
    ctx = c.client.post(PATH + "/context", json=c.selector).json()
    selected = ctx["spans"][0]

    def extend(operation, start, end):
        return publish_native_source_evidence_extension(
            repository=c.repo,
            domain_contract=c.domain,
            semantic_profile=c.profile,
            audience_labels=(service.GM_LABEL,),
            request=NativeSourceEvidenceExtensionV1(
                space_id=c.space,
                extension_id=operation,
                original_admission_id=c.admitted.admission_id,
                source_artifact_id=c.admitted.source_artifact_id,
                source_revision_id=c.admitted.source_revision_id,
                expected_body_sha256=c.admitted.body_sha256,
                expected_parent_revision_id=c.repo.get_head(c.space).head_revision_id,
                expected_source_authority_epoch=c.repo.open_native_source_view(
                    c.space
                ).epoch,
                created_at=datetime.now(UTC),
                spans=[
                    dict(
                        client_ref="chosen",
                        evidence_role="support",
                        start_byte=start,
                        end_byte=end,
                        expected_slice_sha256=sha256(
                            c.text.encode()[start:end]
                        ).hexdigest(),
                    )
                ],
            ),
        )

    first = extend(
        "manual-preexisting-extension", selected["startByte"], selected["endByte"]
    )
    extend("later-other-interval", 0, 1)
    _, plan = prepare_packet(c)
    assert plan["publication"]["evidence"]["mode"] == "existing_support"
    ref = plan["publication"]["evidence"]["support"][0]
    assert ref["introducing_kind"] == "extension"
    assert ref["proof_authority_epoch"] == first.source_authority_epoch
    assert (
        plan["publication"]["expected_source_authority_epoch"]
        > ref["proof_authority_epoch"]
    )
    before = c.repo.open_native_source_view(c.space).epoch
    committed = confirm_packet(c, plan)
    assert committed.status_code == 200, committed.text
    assert c.repo.open_native_source_view(c.space).epoch == before


@pytest.mark.parametrize("manual_case", ["single"], indirect=True)
def test_actual_context_exact_interval_collision_requires_operator_range_choice(
    manual_case,
):
    c = manual_case
    ctx = c.client.post(PATH + "/context", json=c.selector)
    assert ctx.status_code == 200, ctx.text
    ctx = ctx.json()
    witness = ctx["spans"][0]
    assert (witness["startByte"], witness["endByte"]) == (0, len(c.text.encode()))
    request = dict(
        schema="dmb_native_manual_prepare_v1",
        source=ctx["source"],
        operationId=str(uuid4()),
        createdAt=datetime.now(UTC).isoformat(),
        expectedParentRevisionId=ctx["parentRevisionId"],
        expectedSourceAuthorityEpoch=ctx["sourceAuthorityEpoch"],
        witness=witness,
        operation=dict(kind="object", objectKind="npc", name="Explicitly reviewed"),
    )
    before = (snapshot(c), rows_snapshot(c.dsn))
    response = c.client.post(PATH + "/prepare", json=request)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "manual_context_interval_collision"
    assert (snapshot(c), rows_snapshot(c.dsn)) == before
    request["witness"].update(
        startByte=0,
        endByte=len("É".encode()),
        sliceSha256=sha256("É".encode()).hexdigest(),
    )
    response = c.client.post(PATH + "/prepare", json=request)
    assert response.status_code == 200, response.text
    assert (snapshot(c), rows_snapshot(c.dsn)) == before


def test_raw_review_changed_but_normalized_fact_same_conflicts(manual_case):
    c = manual_case
    request, first = prepare_packet(c)
    request["operation"]["name"] = " " + request["operation"]["name"] + " "
    response = c.client.post(PATH + "/prepare", json=request)
    assert response.status_code == 200, response.text
    second = response.json()["plan"]
    assert (
        first["publication"]["contribution"]["items"]
        == second["publication"]["contribution"]["items"]
    )
    assert (
        first["publication"]["contribution"]["diagnostics"]
        != second["publication"]["contribution"]["diagnostics"]
    )
    committed = confirm_packet(c, first)
    assert committed.status_code == 200, committed.text
    before = snapshot(c)
    conflict = confirm_packet(c, second)
    assert conflict.status_code == 409, conflict.text
    assert (
        conflict.json()["detail"]["code"]
        == "knowledge_publication_idempotency_conflict"
    )
    assert snapshot(c) == before


@pytest.mark.parametrize("phase", ["prepare", "confirm"])
@pytest.mark.parametrize("fault", ["partial", "head-race"])
def test_identity_catalogue_refusal_typed_no_post_refusal_probe(
    manual_case, monkeypatch, phase, fault
):
    from dataclasses import replace
    from dungeonmind.application.vnext.entity_reads import (
        EntityReadService,
        EntityReadCompleteness,
    )
    from apps.live_control_server.services import native_graph_inspection as inspection

    c = manual_case
    endpoints = []
    for kind in ["npc", "location"]:
        _, plan = prepare_packet(c, kind=kind)
        response = confirm_packet(c, plan)
        assert response.status_code == 200, response.text
        endpoints.append(
            dict(
                entityId=assert_object(c, response.json()["receipt"], kind),
                name="Traveller " + kind,
                objectKind=kind,
            )
        )
    ctx = c.client.post(PATH + "/context", json=c.selector).json()
    request = dict(
        schema="dmb_native_manual_prepare_v1",
        source=ctx["source"],
        operationId=str(uuid4()),
        createdAt=datetime.now(UTC).isoformat(),
        expectedParentRevisionId=ctx["parentRevisionId"],
        expectedSourceAuthorityEpoch=ctx["sourceAuthorityEpoch"],
        witness=ctx["spans"][0],
        operation=dict(
            kind="relationship",
            source=endpoints[0],
            target=endpoints[1],
            predicate="located_in",
        ),
    )
    prepared = c.client.post(PATH + "/prepare", json=request)
    assert prepared.status_code == 200, prepared.text
    refused = []
    external = []
    if fault == "partial":
        original = EntityReadService.list_entities_with_aliases

        def partial(self, *a, **k):
            listing, aliases = original(self, *a, **k)
            refused.append(True)
            return replace(
                listing,
                completeness=EntityReadCompleteness(
                    status="partial", reason="result_truncated"
                ),
            ), aliases

        monkeypatch.setattr(EntityReadService, "list_entities_with_aliases", partial)
        code = "native_authoring_identities_partial"
    else:
        original = inspection._pinned

        def race(*a, **k):
            refused.append(True)
            del c.repo._heads[c.space]  # external concurrent removal at the owning read
            external.append(snapshot(c))
            return original(*a, **k)

        monkeypatch.setattr(inspection, "_pinned", race)
        code = "native_inspection_head_unavailable"
    old = c.repo.get_native_source_publication_receipt
    probes = []

    def receipt(*a, **k):
        assert not refused, "receipt probe after deterministic identity refusal"
        probes.append(True)
        return old(*a, **k)

    monkeypatch.setattr(c.repo, "get_native_source_publication_receipt", receipt)
    before = snapshot(c)
    response = (
        c.client.post(PATH + "/prepare", json=request)
        if phase == "prepare"
        else confirm_packet(c, prepared.json()["plan"])
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == code
    assert not response.json()["detail"]["outcome_unknown"]
    assert refused and bool(probes) == (phase == "confirm")
    assert snapshot(c) == (external[0] if external else before)


@pytest.mark.parametrize("manual_case", ["admission-support"], indirect=True)
def test_compatible_original_admission_SUPPORT_public_lookup_and_HTTP_reuse(
    manual_case,
):
    c = manual_case
    _, plan = prepare_packet(c)
    assert plan["publication"]["evidence"]["mode"] == "existing_support"
    ref = plan["publication"]["evidence"]["support"][0]
    assert ref["introducing_kind"] == "admission"
    before = c.repo.open_native_source_view(c.space).epoch
    response = confirm_packet(c, plan)
    assert response.status_code == 200, response.text
    assert c.repo.open_native_source_view(c.space).epoch == before
    assert_object(c, response.json()["receipt"])
