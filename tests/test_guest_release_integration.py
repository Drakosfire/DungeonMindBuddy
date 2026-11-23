"""Exercise the experimental candidate across real Core and APP authorities."""
from types import SimpleNamespace
from uuid import uuid4
import asyncio
import io

import httpx
import psycopg
import pytest
from dungeonmind.application.vnext import ParsedEntityRefValue
from fastapi import FastAPI
from PIL import Image, PngImagePlugin

from application_state import guest_release, media
from application_state.content.pages import PageMetadata, commit_page, create_page, snapshot_page
from application_state.world_catalog.service import create_world
from apps.live_control_server.services import guest_release_native_graph as native_reader
from apps.live_control_server.services import guest_release_preparation as preparation
from apps.live_control_server.services import guest_release_validation as validation
from apps.live_control_server.services import guest_release_selection as discovery
from apps.live_control_server.services import guest_release_media_selection as media_discovery
from apps.live_control_server.services.hosted_native_graph_access import hosted_world_media_owner
from apps.live_control_server.services.guest_release_evidence import GuestReleaseEvidenceError
from apps.live_control_server.routes import guest_release_public
from apps.live_control_server.routes import guest_releases as owner_routes
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services.dms_principal import DmsPrincipal
from tests import test_governed_native_source_publication_adoption as native_fixture


@pytest.mark.parametrize("role,custom,node_type", [
    ("support", False, "character"), ("context", False, "character"),
    ("support", False, "item"), ("support", True, "character"),
])
def test_first_world_compiler_release_selection_preserves_inference(application_state_dsn, monkeypatch, role, custom, node_type):
    import dungeonmind.application.vnext as native_api
    from tests import test_first_world_typed_evidence as first_world_fixture
    from tests.test_first_world_typed_evidence import _native_compilation_case, _compile_and_bind, _publish_compilation

    world = create_world(name="First World selection fixture", owner_subject="owner").record.world_id
    page = create_page(world_id=world, title="Source", metadata=PageMetadata(visibility_state="internal"))
    body = ("Scene: private heading\nÁlice meets Bob beside the towér.\nA safe clue.\nGM secret waits beneath the bridge."
            if role == "context" else "Álice meets Bob beside the towér.\nThey remember the bridge.\n\nUnrelated paragraph.")
    saved, revision = commit_page(str(page.page.work_object_id), body, world_id=world,
        expected_revision=page.page.object_revision, expected_working_copy_revision=None)
    publish_source = native_api.publish_native_text_source_evidence
    def source_with_page_origin(*, request, **kwargs):
        data = request.model_dump(mode="json")
        data["origin"] = {"namespace": "dungeonbuddy.workspace-document-registry",
            "object_id": str(page.page.work_object_id), "revision_id": f"registry-revision:{saved.page.object_revision}"}
        return publish_source(request=type(request).model_validate(data), **kwargs)
    monkeypatch.setattr(native_api, "publish_native_text_source_evidence", source_with_page_origin)
    if custom:
        build_effect = first_world_fixture._first_world_effect
        def effect_with_hyphen(**kwargs):
            kwargs["predicate"] = "works-for"
            return build_effect(**kwargs)
        monkeypatch.setattr(first_world_fixture, "_first_world_effect", effect_with_hyphen)
    case = _native_compilation_case(source_text=revision.markdown, native_role=role, custom=custom, node_type=node_type)
    _, bound = _compile_and_bind(case)
    result = _publish_compilation(case, bound)
    graph_revision = result.publication_receipt.published_revision_id
    independent_admission = None
    if role == "context":
        from hashlib import sha256
        from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
        separate_page = create_page(world_id=world, title="Separate recap", metadata=PageMetadata(visibility_state="internal"))
        separate_body = "\n".join(f"Recap line {index}." for index in range(205))
        separate_saved, separate_revision = commit_page(str(separate_page.page.work_object_id), separate_body, world_id=world,
            expected_revision=separate_page.page.object_revision, expected_working_copy_revision=None)
        raw = separate_revision.markdown.encode("utf-8")
        independent_admission = publish_source(repository=case.repo, domain_contract=case.domain, semantic_profile=case.profile,
            request=NativeTextSourceAdmissionV1(space_id=case.space, admission_id="separate-recap",
                expected_parent_revision_id=graph_revision, created_at=case.now, body_text=separate_revision.markdown,
                expected_body_sha256=sha256(raw).hexdigest(), source_classification="dungeonbuddy.source:worldbuilding",
                authority="primary", visibility={"kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]},
                origin={"namespace": "dungeonbuddy.workspace-document-registry", "object_id": str(separate_page.page.work_object_id),
                        "revision_id": f"registry-revision:{separate_saved.page.object_revision}"},
                spans=[{"client_ref": "recap", "evidence_role": "context", "start_byte": 0, "end_byte": len(raw),
                        "expected_slice_sha256": sha256(raw).hexdigest()}]))
        graph_revision = independent_admission.publication_receipt.published_revision_id
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.world_native_binding SET native_world_id=%s,status='active', "
            "binding_version=1,validated_at='now',validated_head_revision_id=%s, provisioning_id=NULL,"
            "initialization_revision_id=NULL WHERE world_id=%s", (case.space, graph_revision, world))
    binding = SimpleNamespace(native_world_id=case.space, binding_version=1)
    monkeypatch.setattr(native_reader, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(discovery, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(native_reader.native_registry_source, "read_repository", lambda: case.repo)
    options = discovery.selection_options(world_id=world)
    fields = options["fields"]
    assert {field["kind"] for field in fields} == {"name", "classification", "relationship"}
    assert all(field["basis"] == "inferred" for field in fields)
    names = {field["entity_id"]: field for field in fields if field["kind"] == "name"}
    kinds = {field["entity_id"]: field for field in fields if field["kind"] == "classification"}
    edge = next(field for field in fields if field["kind"] == "relationship")
    source = next(item for item in options["sources"] if "Álice" in item["excerpt"])
    assert source["evidence_role"] == role
    selected_sources = [preparation.SourceSelection(**{key: source[key] for key in preparation.SourceSelection.model_fields})]
    if role == "context":
        independent = discovery.selection_options(world_id=world, context_document_id=str(separate_page.page.work_object_id), offset=200)
        safe = next(item for item in independent["sources"] if item["excerpt"] == "Recap line 200.")
        selected_sources.append(preparation.SourceSelection(**{key: safe[key] for key in preparation.SourceSelection.model_fields}))
    selection = preparation.ReleaseSelection(graph_revision=graph_revision,
        sources=selected_sources,
        nodes=[preparation.NodeSelection(entity_id=entity, name_assertion_id=names[entity]["assertion_id"],
            kind_assertion_id=kinds[entity]["assertion_id"], name_source_index=0, kind_source_index=0)
            for entity in (edge["entity_id"], edge["target_id"])],
        relationships=[preparation.RelationshipSelection(assertion_id=edge["assertion_id"], subject_id=edge["entity_id"],
            predicate=edge["predicate"], evidence_id=source["evidence_id"], source_index=0)], asset_ids=[])
    release_id, digest = preparation._prepare_candidate(world_id=world, subject="owner", selection=selection)
    manifest, _ = guest_release.review(world_id=world, subject="owner", release_id=release_id)
    assert all(node["name_basis"] == "inferred" and node["kind_basis"] == "inferred" for node in manifest["graph"]["nodes"])
    assert manifest["graph"]["edges"][0]["basis"] == "inferred"
    if node_type == "item":
        assert any(node["kind"] == "buddy · item" for node in manifest["graph"]["nodes"])
    if custom:
        assert manifest["graph"]["edges"][0]["label"] == "custom · works-for"
    else:
        assert manifest["graph"]["edges"][0]["label"] == "dnd5e · located in"
    assert manifest["sources"][0]["evidence_role"] == role
    if role == "context":
        assert manifest["sources"][1]["text"] == "Recap line 200."
        assert manifest["sources"][1]["evidence_role"] == "context"
    assert "Reviewed description" not in str(manifest) and "Unrelated paragraph" not in str(manifest)
    assert "GM secret" not in str(manifest) and "private heading" not in str(manifest)
    assert case.repo.get_head(case.space).head_revision_id == graph_revision
    assert validation.validate_candidate(world_id=world, subject="owner", release_id=release_id, digest=digest) >= 0
    if role == "context":
        case.repo.withdraw_native_source(space_id=case.space, source_artifact_id=independent_admission.source_artifact_id,
                                         source_revision_id=independent_admission.source_revision_id)
        with pytest.raises(GuestReleaseEvidenceError):
            validation.validate_candidate(world_id=world, subject="owner", release_id=release_id, digest=digest)


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
    image_bytes = io.BytesIO()
    image_metadata = PngImagePlugin.PngInfo()
    image_metadata.add_text("private", "synthetic secret")
    Image.new("RGB", (2, 2), "red").save(image_bytes, format="PNG", pnginfo=image_metadata)
    asset = media.stage_image(image_bytes.getvalue(), hosted_world_media_owner(world), {"private": "synthetic provenance"})
    asset_id = asset["asset_id"]
    media_page = media_discovery.list_media(world_id=world)
    assert [item["id"] for item in media_page["assets"]] == [str(asset_id)]
    assert "provenance" not in str(media_page) and "receipt" not in str(media_page)
    mime, sanitized = media_discovery.preview_media(world_id=world, asset_id=asset_id)
    assert mime == "image/png" and b"synthetic secret" not in sanitized
    assert media_discovery.list_media(world_id="unrelated")["assets"] == []
    from application_state.errors import ApplicationStateNotFoundError
    with pytest.raises(ApplicationStateNotFoundError):
        media_discovery.preview_media(world_id="unrelated", asset_id=asset_id)
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
    # The root admission has a separate exact one-byte support span. It is
    # retained independently of the later graph-publication interval.
    sources.append(preparation.SourceSelection(document_id=document_id, revision_n=revision.revision_n,
        sha256=revision.content_sha256, start=0, end=1, excerpt=native_fixture.BODY[:1],
        evidence_id=case.root.bindings[0].evidence_ref_id))
    def index(assertion):
        return evidence_ids.index(assertion.metadata.evidence_ref_ids[0])
    nodes = [preparation.NodeSelection(entity_id=entity, name_assertion_id=names[entity].assertion_id,
        kind_assertion_id=kinds[entity].assertion_id, name_source_index=index(names[entity]),
        kind_source_index=index(kinds[entity])) for entity in (edge.subject_entity_id, edge.value.entity_id)]
    selection = preparation.ReleaseSelection(graph_revision=graph_revision, nodes=nodes, sources=sources,
        relationships=[preparation.RelationshipSelection(assertion_id=edge.assertion_id, subject_id=edge.subject_entity_id,
            predicate=edge.predicate, evidence_id=edge.metadata.evidence_ref_ids[0], source_index=index(edge))], asset_ids=[asset_id],
        saved_example=preparation.SavedExampleSelection(title="An owner scene", body="A saved scene",
            source_indexes=[0, len(sources) - 1], asset_id=asset_id, image_description="A small red image"),
        saved_choice=preparation.SavedChoiceSelection(prompt="What next", options=[
            preparation.SavedChoiceOption(label="Enter", outcome="A bell rings"),
            preparation.SavedChoiceOption(label="Wait", outcome="A lantern flickers")]))
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
            images = await client.post(f"/api/live/worlds/{world}/guest-releases/selection-media/list", json={},
                headers={"x-test-owner": "yes", "origin": "https://buddy.example"})
            assert images.status_code == 200 and images.json()["assets"][0]["id"] == str(asset_id)
            preview = await client.get(f"/api/live/worlds/{world}/guest-releases/selection-media/{asset_id}", headers={"x-test-owner": "yes"})
            assert preview.status_code == 200 and preview.content == sanitized and preview.headers["cache-control"] == "no-store"
            return await client.post(f"/api/live/worlds/{world}/guest-releases", json=selection.model_dump(mode="json"),
                headers={"x-test-owner": "yes", "origin": "https://buddy.example"})
    response = asyncio.run(prepare_over_http())
    assert response.status_code == 200
    from uuid import UUID
    release_id, digest = UUID(response.json()["release_id"]), response.json()["digest"]
    pending_id, pending_digest = preparation._prepare_candidate(world_id=world, subject="owner", selection=selection)
    manifest, reviewed_digest = guest_release.review(world_id=world, subject="owner", release_id=release_id)
    assert reviewed_digest == digest and len(manifest["graph"]["nodes"]) == 2
    assert manifest["projection_version"] == "explicit_native_assertions_v3"
    assert manifest["image_sanitizer_version"] == "bounded_png_v1"
    assert len(manifest["graph"]["edges"]) == 1
    assert len(manifest["assets"]) == 1
    example = manifest["saved_example"]
    assert example["title"] == "An owner scene" and example["body"] == "A saved scene"
    assert example["references"] == [manifest["sources"][0]["id"], manifest["sources"][-1]["id"]]
    assert example["image"] == {"id": manifest["assets"][0]["id"], "description": "A small red image"}
    assert manifest["saved_choice"] == {"version": "owner_saved_choice_v1", "prompt": "What next", "options": [
        {"label": "Enter", "outcome": "A bell rings"}, {"label": "Wait", "outcome": "A lantern flickers"}]}
    assert str(document_id) not in str(example) and str(asset_id) not in str(example)
    released_asset = UUID(manifest["assets"][0]["id"])
    assert released_asset != asset_id
    assert guest_release.review_asset(world_id=world, subject="owner", release_id=release_id, asset_id=released_asset) == (mime, sanitized)
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
    async def signed_out_asset():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(f"/api/live/guest-releases/{public_id}/releases/{release_id}/assets/{released_asset}")
    assert asyncio.run(signed_out_asset()).content == sanitized
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
    assert asyncio.run(signed_out_asset()).status_code == 404
    with pytest.raises(ApplicationStateNotFoundError):
        guest_release.public_manifest(public_id)
