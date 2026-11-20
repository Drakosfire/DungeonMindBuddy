"""Exercise the experimental candidate across real Core and APP authorities."""
from types import SimpleNamespace
from uuid import uuid4
import asyncio

import httpx
import psycopg
import pytest
from dungeonmind.application.vnext import ParsedEntityRefValue
from fastapi import FastAPI

from application_state import guest_release
from application_state.content.pages import PageMetadata, commit_page, create_page, snapshot_page
from application_state.world_catalog.service import create_world
from apps.live_control_server.services import guest_release_native_graph as native_reader
from apps.live_control_server.services import guest_release_preparation as preparation
from apps.live_control_server.services import guest_release_validation as validation
from apps.live_control_server.services import guest_release_selection as discovery
from apps.live_control_server.services.guest_release_evidence import GuestReleaseEvidenceError
from apps.live_control_server.routes import guest_release_public
from apps.live_control_server.routes import guest_releases as owner_routes
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.dms_principal import DmsPrincipal
from tests import test_governed_native_source_publication_adoption as native_fixture


def test_private_source_candidate_review_publish_and_withdrawal(application_state_dsn, monkeypatch):
    world = create_world(name="Guest integration fixture", owner_subject="owner").record.world_id
    page = create_page(world_id=world, title="Private source", metadata=PageMetadata(visibility_state="internal"))
    document_id = page.page.work_object_id
    committed, revision = commit_page(str(document_id), native_fixture.BODY, world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    # APP commits normalize line endings; Core must ingest the committed bytes,
    # not the pre-save input, for its proof to identify the same revision.
    monkeypatch.setattr(native_fixture, "BODY", revision.markdown)
    monkeypatch.setattr(native_fixture, "RAW", revision.markdown.encode("utf-8"))
    admission = native_fixture.NativeTextSourceAdmissionV1
    monkeypatch.setattr(native_fixture, "NativeTextSourceAdmissionV1", lambda **kwargs: admission(
        **kwargs, origin={"namespace": "dungeonbuddy.workspace-document-registry", "object_id": str(document_id),
                          "revision_id": f"registry-revision:{committed.page.object_revision}"}))
    case = native_fixture.setup()
    _, receipt = native_fixture.exercise(case, "new_intervals", primary=False)
    graph_revision = receipt.publication_receipt.published_revision_id
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.world_native_binding SET native_world_id=%s,status='active', "
            "binding_version=1,validated_at='now',validated_head_revision_id=%s, "
            "provisioning_id=NULL,initialization_revision_id=NULL WHERE world_id=%s", (case.space, graph_revision, world))
    binding = SimpleNamespace(native_world_id=case.space, binding_version=1)
    monkeypatch.setattr(native_reader, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(discovery, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(native_reader.native_registry_source, "read_repository", lambda: case.repo)
    _, context, support, _ = native_reader.read_owner_graph(managed_world_id=world, revision_id=graph_revision)
    options = discovery.selection_options(world_id=world)
    assert options["graph_revision"] == graph_revision
    assert any(item["kind"] == "name" for item in options["fields"])
    assert options["sources"] and options["sources"][0]["visibility"] == "internal"
    assert options["sources"][0]["excerpt"] == native_fixture.BODY[1:]
    assertions = [context.parsed.get_assertion(item) for item in support.listing.admitted_assertion_ids]
    names = {a.subject_entity_id: a for a in assertions if a.predicate == "dnd5e:name"}
    kinds = {a.subject_entity_id: a for a in assertions if a.predicate == "dnd5e:classification"}
    edge = next(a for a in assertions if isinstance(a.value, ParsedEntityRefValue)
                and a.subject_entity_id in names and a.subject_entity_id in kinds
                and a.value.entity_id in names and a.value.entity_id in kinds
                and a.subject_entity_id != a.value.entity_id)
    selected = [names[edge.subject_entity_id], kinds[edge.subject_entity_id],
                names[edge.value.entity_id], kinds[edge.value.entity_id], edge]
    evidence_ids = list(dict.fromkeys(a.metadata.evidence_ref_ids[0] for a in selected))
    sources = [preparation.SourceSelection(document_id=document_id, revision_n=revision.revision_n,
        sha256=revision.content_sha256, start=1, end=len(native_fixture.BODY), excerpt=native_fixture.BODY[1:],
        evidence_id=evidence_id) for evidence_id in evidence_ids]
    def index(assertion):
        return evidence_ids.index(assertion.metadata.evidence_ref_ids[0])
    nodes = [preparation.NodeSelection(entity_id=entity, name_assertion_id=names[entity].assertion_id,
        kind_assertion_id=kinds[entity].assertion_id, name_source_index=index(names[entity]),
        kind_source_index=index(kinds[entity])) for entity in (edge.subject_entity_id, edge.value.entity_id)]
    selection = preparation.ReleaseSelection(graph_revision=graph_revision, nodes=nodes, sources=sources,
        relationships=[preparation.RelationshipSelection(assertion_id=edge.assertion_id, subject_id=edge.subject_entity_id,
            predicate=edge.predicate, evidence_id=edge.metadata.evidence_ref_ids[0], source_index=index(edge))], asset_ids=[])
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(hosted_auth.TRUSTED_FRONTEND_ORIGINS_ENV, "https://buddy.example")
    monkeypatch.setenv("DMB_GUEST_RELEASE_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_RELEASE_PREPARE_ENABLED", "1")
    monkeypatch.setattr(hosted_auth, "hosted_world_access", lambda: {world: frozenset({"owner"})})
    monkeypatch.setattr(owner_routes, "_owned_world", lambda subject, world_id: SimpleNamespace(world_id=world_id))
    owner_app = FastAPI()
    owner_app.include_router(owner_routes.router)
    from apps.live_control_server.main import HOSTED_WORLD_SCOPE_RESOLVERS
    owner_resolvers = {key: value for key, value in HOSTED_WORLD_SCOPE_RESOLVERS.items()
                       if value is owner_routes.resolve_hosted_guest_release_world}
    hosted_auth.install_hosted_request_boundary(owner_app, world_scope_resolvers=owner_resolvers)
    async def principal(request):
        return DmsPrincipal("owner") if request.headers.get("x-test-owner") else None
    owner_app.state.dms_principal_resolver = principal
    async def prepare_over_http():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=owner_app), base_url="http://test") as client:
            url = f"/api/live/worlds/{world}/guest-releases/selection-options"
            assert (await client.get(url)).status_code == 401
            inventory = await client.get(url, headers={"x-test-owner": "yes"})
            assert inventory.status_code == 200 and inventory.headers["cache-control"] == "no-store"
            assert inventory.json()["graph_revision"] == graph_revision
            assert any(field["assertion_id"] == edge.assertion_id for field in inventory.json()["fields"])
            return await client.post(f"/api/live/worlds/{world}/guest-releases", json=selection.model_dump(mode="json"),
                headers={"x-test-owner": "yes", "origin": "https://buddy.example"})
    response = asyncio.run(prepare_over_http())
    assert response.status_code == 200
    from uuid import UUID
    release_id, digest = UUID(response.json()["release_id"]), response.json()["digest"]
    pending_id, pending_digest = preparation._prepare_candidate(world_id=world, subject="owner", selection=selection)
    manifest, reviewed_digest = guest_release.review(world_id=world, subject="owner", release_id=release_id)
    assert reviewed_digest == digest and len(manifest["graph"]["nodes"]) == 2
    assert manifest["projection_version"] == "explicit_native_assertions_v1"
    assert manifest["image_sanitizer_version"] == "bounded_png_v1"
    assert len(manifest["graph"]["edges"]) == 1
    assert all(node["name_temporal"] == "unknown" for node in manifest["graph"]["nodes"])
    assert guest_release.review_source_visibility(world_id=world, subject="owner", release_id=release_id) == {
        source["id"]: "internal" for source in manifest["sources"]}
    public_id, _ = validation.publish_candidate(world_id=world, subject="owner", release_id=release_id,
        digest=digest, expected_version=0, operation_id=uuid4())
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
    monkeypatch.setenv(hosted_auth.DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(hosted_auth.AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv("DMB_GUEST_RELEASE_ENABLED", "1")
    monkeypatch.setenv("DMB_GUEST_RELEASE_PUBLIC_ENABLED", "1")
    app = FastAPI()
    app.include_router(guest_release_public.router)
    hosted_auth.install_hosted_request_boundary(app)
    async def signed_out_read():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(f"/api/live/guest-releases/{public_id}")
    public_response = asyncio.run(signed_out_read())
    assert public_response.status_code == 200 and public_response.json()["manifest"] == manifest
    assert public_response.headers["cache-control"] == "no-store"
    current = snapshot_page(str(document_id), world_id=world)
    commit_page(str(document_id), "A later private edit", world_id=world,
        expected_revision=current.page.object_revision, expected_working_copy_revision=current.working_copy_revision)
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
    changed_options = discovery.selection_options(world_id=world)
    assert changed_options["fields"] == [] and changed_options["sources"] == []
    case.repo.withdraw_native_source(space_id=case.space, source_artifact_id=case.root.source_artifact_id,
                                     source_revision_id=case.root.source_revision_id)
    with pytest.raises(GuestReleaseEvidenceError):
        validation.publish_candidate(world_id=world, subject="owner", release_id=pending_id,
            digest=pending_digest, expected_version=1, operation_id=uuid4())
    # Withdrawal affects new candidates, not the explicitly published copy.
    assert guest_release.public_manifest(public_id) == (release_id, manifest)
    guest_release.revoke(world_id=world, subject="owner", release_id=release_id)
    assert asyncio.run(signed_out_read()).status_code == 404
    from application_state.errors import ApplicationStateNotFoundError
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_manifest(public_id)
