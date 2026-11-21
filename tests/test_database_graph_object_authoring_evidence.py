"""Manual occurrence verification consumes exact APP source and run-index bytes."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import psycopg
import pytest

from apps.live_control_server.services import graph_object_authoring_prepare as owner
from apps.live_control_server.services.graph_object_authoring_commit import commit_graph_object_authoring_write
from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
from tests.test_graph_object_authoring_prepare import (
    FakeSourceAdmission, FakeWorldGraphAuthority, object_proposal, prepare_request,
)
from tests.test_graph_preview_runner import (
    FixtureClient, ProductionExtractionRequest, WORLDBUILDING_PLUMBING_PROFILE_ID,
    WORLDBUILDING_PLUMBING_PROFILE_VERSION, _admit_worldbuilding, _first_paragraph_span_id,
    run_production_extraction,
)

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv(owner.GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "synthetic-database-authoring")
    source = _admit_worldbuilding(tmp_path)
    result = run_production_extraction(ProductionExtractionRequest(
        repo_root=tmp_path, source=source, profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
        profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION, allow_llm=True,
        category_client=FixtureClient(span_ref=_first_paragraph_span_id(source))))
    assert result.failure_kind is None
    data = load_reviewable_extraction_data(tmp_path, result.run.run_id)
    resolved = SimpleNamespace(run_id=data.run.run_id, source_artifact=data.source_artifact,
        source_artifact_id=data.run.source_artifact_id, source_domain="worldbuilding",
        source_revision_id="sha256:" + data.source_artifact.content_sha256,
        campaign_id=data.run.campaign_id, world_id=data.source_artifact.world_id,
        source_span_index_path=tmp_path / data.run.components["source_span_index"].uri.removeprefix("repo://"),
        source_span_index_sha256=data.run.components["source_span_index"].sha256)
    request = prepare_request(campaignId=data.run.campaign_id, worldId=data.run.campaign_id,
        sourceRunId=data.run.run_id, proposals=[object_proposal(selection={
            "selectionKind":"text_span", "selectedText":"Mirathorn", "normalizedSelectedText":"Mirathorn",
            "sourceSpanRefId":data.span_index.spans[0].source_span_id})])
    assertions, _ = owner.build_assertions_from_proposals(request)
    admitted = Mock(return_value=SimpleNamespace(outcome="enough", content=source.source_text.strip()))
    monkeypatch.setattr("apps.live_control_server.services.worldbuilding_source_span_read.read_admitted_worldbuilding_span", admitted)
    from apps.live_control_server.services.graph_object_authoring_binding import GraphReviewPublicationContext
    monkeypatch.setattr("apps.live_control_server.services.graph_object_authoring_binding.resolve_publication_context",
        lambda request, resolved, **_: GraphReviewPublicationContext(request.world_id, request.campaign_id))
    return SimpleNamespace(root=tmp_path, data=data, resolved=resolved, request=request,
        assertions=assertions, admitted=admitted)


def verify(case):
    return owner.verify_graph_review_assertion_spans(assertions=case.assertions, resolved_source=case.resolved,
        source_root=case.root, world_id=case.request.world_id, campaign_id=case.request.campaign_id)


def test_graph_review_reads_actual_database_after_all_mirror_loss(case, monkeypatch):
    for path in case.root.rglob("*"):
        if path.is_file():
            path.unlink()
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: pytest.fail("manual verifier reopened file evidence"))
    proofs = verify(case)
    [proof] = proofs.values()
    assert proof.source_artifact_id == case.data.run.source_artifact_id
    assert proof.span_index_sha256 == hashlib.sha256(case.data.span_bytes).hexdigest()
    assert proof.span_content_sha256 == hashlib.sha256(case.data.source_bytes.strip()).hexdigest()
    case.admitted.assert_called_once()


@pytest.mark.parametrize("kind", ["source", "index"])
@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_database_failure_is_not_rescued_by_valid_mirrors(case, application_state_dsn, kind, damage):
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source":
            if damage == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (case.data.run.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (case.data.run.source_artifact_id,))
        elif damage == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind='source_span_index'", (case.data.run.run_id,))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='source_span_index'", (b"corrupt", case.data.run.run_id))
    with pytest.raises(owner.GraphObjectAuthoringError) as error:
        verify(case)
    assert error.value.code == "source_span_drift"
    case.admitted.assert_not_called()


@pytest.mark.parametrize("change", ["run", "digest"])
def test_current_run_binding_is_required(case, change):
    if change == "run":
        case.resolved.run_id = "missing-run"
    else:
        case.resolved.source_span_index_sha256 = "ab" * 32
    with pytest.raises(owner.GraphObjectAuthoringError) as error:
        verify(case)
    assert error.value.code == "source_span_drift"
    case.admitted.assert_not_called()


def test_actual_database_prepare_confirm_needs_no_mirrors(case):
    for path in case.root.rglob("*"):
        if path.is_file():
            path.unlink()
    authority, admission = FakeWorldGraphAuthority(), FakeSourceAdmission()
    prepared = owner.prepare_graph_object_authoring_write(case.request, corpus_root=case.root,
        authority=authority, source_admission=admission, resolved_source=case.resolved)
    request = owner.GraphObjectAuthoringCommitRequest.model_validate({
        **case.request.model_dump(mode="json", by_alias=True), "confirmToken":prepared.confirm_token})
    receipt = commit_graph_object_authoring_write(request, corpus_root=case.root,
        authority=authority, source_admission=admission, resolved_source=case.resolved)
    assert receipt.published_revision_id == "rev:d1"
    assert authority.publish_calls == 1



@pytest.fixture
def historical_manual_core_dsn(monkeypatch, record_property):
    """Own one loopback fixture DB; require clean release before its teardown."""
    import json
    import os
    from psycopg.conninfo import conninfo_to_dict
    from tests.test_native_recap_source_admission import native_core_dsn

    lifecycle = native_core_dsn.__wrapped__(monkeypatch)
    dsn = next(lifecycle)
    name = conninfo_to_dict(dsn)["dbname"]
    admin = os.environ["DMB_NATIVE_RECAP_TEST_ADMIN_DSN"]
    try:
        with psycopg.connect(dsn) as conn:
            migration = conn.execute("SELECT version_num FROM dungeonmind.alembic_version").fetchone()[0]
        yield dsn
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            connections = conn.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=%s", (name,),
            ).fetchone()[0]
        try:
            assert connections == 0, f"fixture connection leak: {name} has {connections} clients"
        finally:
            lifecycle.close()
        with psycopg.connect(admin, autocommit=True) as conn:
            absent = conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone() is None
        record_property("historical_manual_core_lifecycle", json.dumps(dict(
            database=name, migration=migration, connections_before_drop=connections, absent_after=absent,
        ), sort_keys=True))
        assert absent


def _database_rows_fingerprint(dsn, *, core=False):
    """Count AND hash every durable row; never return source text or credentials."""
    from psycopg import sql

    result = {}
    with psycopg.connect(dsn) as conn:
        tables = conn.execute(
            "SELECT table_schema,table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') "
            "ORDER BY table_schema,table_name"
        ).fetchall()
        for schema, table in tables:
            if core and schema != "dungeonmind":
                continue
            rows = conn.execute(sql.SQL(
                "SELECT to_jsonb(t)::text FROM {}.{} AS t ORDER BY to_jsonb(t)::text"
            ).format(sql.Identifier(schema), sql.Identifier(table)))
            digest, count = hashlib.sha256(), 0
            for (row,) in rows:
                count += 1
                digest.update(row.encode("utf-8") + b"\n")
            result[f"{schema}.{table}"] = (count, digest.hexdigest())
    return result


def _publish_historical_manual(case, dsn, monkeypatch):
    """Execute the historical producer and actual Core finalize/publication UoW.

    The seed is an honest public V6 revision, not a reviewed-initialization claim.
    Inject only the real repository bundle at the old service-bootstrap seam.
    Existing APP admitted-span presentation is stubbed by ``case``; APP bytes,
    span/index hashes, source admission and Core review/publication are real.
    """
    from datetime import UTC, datetime, timedelta
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresRepositoryBundle
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.ports.world_graph_source_admission import WorldGraphSourceAdmissionRequest
    from tests._cutover_direct_dungeonmind_read_helpers import _payload

    bundle = PostgresRepositoryBundle(PostgresDatabase(dsn))
    world = case.request.world_id
    stamp = datetime(2025, 1, 1, tzinfo=UTC)
    payload = _payload()
    payload.update(world_id=world, objects=[], relationships=[], evidence_refs=[])
    parent = bundle.world_graph.publish_revision(PublishRevisionCommand(
        world_id=world, parent_revision_id=None, expected_parent_revision_id=None,
        operation_ids=["fixture:historical-manual-seed"], graph_schema="dm_union_graph_v6",
        graph_payload=payload, created_at=stamp,
    ))
    parent_id = parent.revision_id
    admitted = DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn).prove_or_admit(
        WorldGraphSourceAdmissionRequest(
            world_id=world, campaign_id=case.request.campaign_id,
            source_artifact=case.data.source_artifact,
            source_revision_token=case.resolved.source_revision_id,
            source_body=case.data.source_bytes, expected_head_revision_id=parent_id,
        ),
    )
    actor = owner.graph_review_actor(case.request.campaign_id)
    contribution = owner.translate_assertions_to_contribution(
        world_id=world, campaign_id=case.request.campaign_id, actor=actor,
        source_artifact_id=case.resolved.source_artifact_id,
        source_revision_id=case.resolved.source_revision_id,
        assertions=case.assertions, verified_spans=verify(case),
    )
    operation = writes.graph_review_authority_operation_id(
        world_id=world, campaign_id=case.request.campaign_id, campaign_rel=case.request.campaign_rel,
        source_artifact_id=admitted.source_artifact_id, source_revision_id=admitted.source_revision_id,
        sealed_proposal_digest=owner.proposed_assertions_digest(case.assertions),
        expected_parent_revision_id=parent_id,
    )
    # Create and retain this packet ONCE, before publication, with the original
    # historical preparation clock. Never re-sign after the simulated lost reply.
    packet = owner.GraphObjectAuthoringCommitRequest.model_validate({
        **case.request.model_dump(mode="json", by_alias=True),
        "confirmToken": owner.sign_publication_intent(owner.publication_intent_payload(
            world_id=world, campaign_id=case.request.campaign_id, campaign_rel=case.request.campaign_rel,
            source_run_id=case.request.source_run_id, source_artifact_id=admitted.source_artifact_id,
            source_revision_id=admitted.source_revision_id, expected_parent_revision_id=parent_id,
            authority_operation_id=operation, expressibility=owner.classify_graph_review_expressibility(case.request.proposals), actor=actor,
            assertions_digest=owner.proposed_assertions_digest(case.assertions),
            expires_at=(stamp + timedelta(minutes=5)).isoformat(),
            contribution_digest=owner.contribution_binding_digest(contribution),
        )),
    })
    with monkeypatch.context() as publishing:
        publishing.setattr(writes, "_direct_services", lambda *_: SimpleNamespace(bundle=bundle))
        published = writes.publish_contribution_via_dungeonmind(
            world_id=world, expected_parent_revision_id=parent_id,
            operation_id=writes.derive_authority_review_operation_id(
                world_id=world, authority_operation_id=operation, operation_namespace="worldbuilding",
            ), actor=actor, contribution=contribution, database_url=dsn, publication_family="worldbuilding",
        )
    child_id = published["committed_revision_id"]
    child = bundle.world_graph.get_revision(world, child_id)
    descendant = bundle.world_graph.publish_revision(PublishRevisionCommand(
        world_id=world, parent_revision_id=child_id, expected_parent_revision_id=child_id,
        operation_ids=["fixture:later-manual-descendant"], graph_schema=child.revision.graph_schema,
        graph_payload=child.graph_payload, created_at=stamp + timedelta(days=1),
    ))
    # Fixture-only catalog lifecycle edit, matching the record and its ordinary
    # fingerprint. No classic public lifecycle API is invented by this witness.
    from dungeonmind.contracts.evidence import SourceStatus
    from dungeonmind.infrastructure.postgres.database import jsonb
    from dungeonmind.infrastructure.postgres.serialization import model_fingerprint
    artifact = bundle.sources.get_artifact(admitted.source_artifact_id).model_copy(
        update={"status": SourceStatus.RETRACTED},
    )
    with bundle.database.transaction() as conn:
        conn.execute(
            "UPDATE dungeonmind.source_artifacts SET status=%s,payload=%s,record_fingerprint=%s "
            "WHERE source_artifact_id=%s",
            (artifact.status.value, jsonb(artifact.model_dump(mode="json")), model_fingerprint(artifact),
             artifact.source_artifact_id),
        )
    assert bundle.sources.get_artifact(admitted.source_artifact_id).status is SourceStatus.RETRACTED
    assert bundle.world_graph.get_head(world).head_revision_id == descendant.revision_id != child_id
    return SimpleNamespace(bundle=bundle, packet=packet, world=world, parent=parent_id,
        child=child_id, operation=operation, descendant=descendant.revision_id)


@pytest.mark.parametrize("terminal", ["present", "absent", "corrupt_child"])
def test_real_postgres_historical_manual_recovery_after_withdrawal_and_descendant(
    case, historical_manual_core_dsn, application_state_dsn, monkeypatch, terminal,
):
    from dungeonmind.infrastructure.postgres import PostgresSourceRepository, PostgresWorldGraphRepository
    from dungeonmind.infrastructure.postgres.review_publication import PostgresFinalizedReviewPublicationRepository
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes

    dsn = historical_manual_core_dsn
    fixture = _publish_historical_manual(case, dsn, monkeypatch)
    original_token = fixture.packet.confirm_token
    with pytest.raises(owner.GraphObjectAuthoringError):
        owner.decode_publication_intent(original_token)
    monkeypatch.setattr(config, "world_graph_authority_database_url", lambda: dsn)
    if terminal != "present":
        with fixture.bundle.database.transaction() as conn:
            if terminal == "absent":
                conn.execute("DELETE FROM dungeonmind.finalized_review_publications WHERE published_revision_id=%s",
                             (fixture.child,))
            else:
                conn.execute("UPDATE dungeonmind.graph_revisions SET graph_payload='null'::jsonb "
                             "WHERE revision_id=%s", (fixture.child,))
    before = (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn))
    def forbidden(*args, **kwargs):
        pytest.fail("historical recovery opened mutable authority or a writer")
    for module, names in (
        (owner, ("resolve_graph_review_source", "verify_graph_review_assertion_spans", "prove_graph_review_source")),
        (writes, ("_direct_services", "_build_pair_to_dm", "publish_contribution_via_dungeonmind")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    from apps.live_control_server.services import graph_object_authoring_commit as commit
    for name in ("resolve_graph_review_source", "verify_graph_review_assertion_spans", "prove_graph_review_source"):
        monkeypatch.setattr(commit, name, forbidden)
    for path in (
        "apps.live_control_server.services.graph_run_registry.get_extraction_run",
        "apps.live_control_server.services.graph_run_registry.load_reviewable_extraction_data",
        "apps.live_control_server.services.workspace_document_registry.get_workspace_document",
        "apps.live_control_server.services.source_artifact_registry.get_source_artifact",
        "apps.live_control_server.services.source_artifact_registry.load_source_input_bytes",
        "apps.live_control_server.services.worldbuilding_source_span_read.read_admitted_worldbuilding_span",
        "dungeonmind.application.contribution_review_v3.finalize_contribution_review_v3",
        "dungeonmind.application.review_publication.publish_finalized_review",
    ):
        monkeypatch.setattr(path, forbidden)
    monkeypatch.setattr(PostgresSourceRepository, "get_artifact", forbidden)
    monkeypatch.setattr(PostgresWorldGraphRepository, "get_head", forbidden)
    monkeypatch.setattr(PostgresWorldGraphRepository, "publish_revision", forbidden)
    monkeypatch.setattr(PostgresFinalizedReviewPublicationRepository, "publish", forbidden)
    for _ in range(2):  # Each service call constructs fresh bare SQL readers.
        if terminal == "present":
            result = commit_graph_object_authoring_write(fixture.packet, recovery_only=True)
            assert result.result == result.idempotency_status == "already_applied"
            assert (result.world_id, result.parent_revision_id, result.published_revision_id, result.operation_id) == (
                fixture.world, fixture.parent, fixture.child, fixture.operation,
            )
            assert result.published_revision_id != fixture.descendant
            assert result.committed_proposal_ids == [case.request.proposals[0].local_proposal_id]
            assert result.created_node_ids == {
                case.request.proposals[0].local_proposal_id: owner.authored_object_node_id(case.assertions[0].assertion_id),
            }
        else:
            with pytest.raises(owner.GraphObjectAuthoringError) as error:
                commit_graph_object_authoring_write(fixture.packet, recovery_only=True)
            assert error.value.code == ("publication_receipt_unavailable" if terminal == "absent" else "authority_integrity")
        assert fixture.packet.confirm_token == original_token
        assert (_database_rows_fingerprint(dsn, core=True), _database_rows_fingerprint(application_state_dsn)) == before
