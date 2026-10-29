"""Preparation→owner-bound saved asset→source Save/reopen on real disposable APP."""

import io
import json
from uuid import UUID
from PIL import Image
import pytest

from application_state import media
from application_state.build_proposal.images import BuildImageService
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWritePrepareRequest,
    TiptapMarkdownWriteCommitRequest,
    prepare_tiptap_markdown_write,
    commit_tiptap_markdown_write,
    TiptapMarkdownWriteError,
    validate_saved_media_references,
)
from apps.live_control_server.services.workspace_document_registry import (
    get_workspace_document_snapshot,
)
from tests.test_build_image_tool import image_tool
from tests.test_build_insertion_tool import request_case as _request_case


def saved_image(owner):
    content = io.BytesIO()
    Image.new("RGB", (3, 2), "green").save(content, format="PNG")
    row = media.stage_image(content.getvalue(), owner, {"prompt": "Synthetic"})
    return row


def ready(row):
    fence = media.claim_upload(row["asset_id"], row["owner_id"])
    receipt = {
        "backend": "cloudflare_images",
        "account_id": "synthetic",
        "object_id": "buddy-" + row["asset_id"].hex,
        "original_sha256": row["content_sha256"],
        "provenance_sha256": row["provenance_sha256"],
        "owner_id": row["owner_id"],
        "asset_id": str(row["asset_id"]),
        "visibility": "public",
        "delivery_url": "https://imagedelivery.net/synthetic/buddy-"
        + row["asset_id"].hex
        + "/public",
    }
    return media.complete_upload(row["asset_id"], row["owner_id"], fence, receipt)


def test_prepared_image_association_and_actual_source_save_reopen(
    request_case, monkeypatch
):
    request, source, root = request_case
    tool, message, _, _ = image_tool(request, monkeypatch)
    action = UUID(json.loads(tool.dispatch(message)["resultJson"])["action_id"])
    store = BuildImageService()
    record = store.get(action, "local_operator")
    image = saved_image("local_operator")
    with pytest.raises(ApplicationStateConflictError):
        store.associate(action, image["asset_id"], "local_operator", record.revision)
    ready(image)
    updated = store.associate(
        action, image["asset_id"], "local_operator", record.revision
    )
    assert updated.asset_id == image["asset_id"]
    assert (
        store.associate(action, image["asset_id"], "local_operator", record.revision)
        == updated
    )
    markdown = (
        source.markdown.rstrip()
        + f"\n\n![Edge at dusk](dmb-media:{image['asset_id']})\n"
    )
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=source.record.document_id,
            markdown=markdown,
            expected_revision=source.loaded_revision,
        ),
    )
    assert not prepared.diagnostics or not any(
        "lossy" in d for d in prepared.diagnostics
    )
    committed = commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=source.record.document_id,
            markdown=markdown,
            expected_revision=prepared.registry_revision,
            writer_confirm_token=prepared.writer_confirm_token,
        ),
    )
    assert committed.bytes_written > 0
    reopened = get_workspace_document_snapshot(root, source.record.document_id)
    assert (
        f"dmb-media:{image['asset_id']}" in reopened.markdown
        and "Synthetic" not in reopened.markdown
    )
    foreign = ready(saved_image("foreign"))
    with pytest.raises(TiptapMarkdownWriteError):
        validate_saved_media_references(f"![Foreign](dmb-media:{foreign['asset_id']})")
    with pytest.raises(ApplicationStateNotFoundError):
        store.associate(action, foreign["asset_id"], "local_operator", updated.revision)


@pytest.fixture
def request_case(tmp_path, monkeypatch, application_state_dsn):
    return _request_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.mark.parametrize("destination", ["dmb-media:", "dmb&#45;media:", "dmb&#x2d;media:"])
def test_encoded_foreign_image_rejected_by_prepare_and_commit(request_case, destination):
    _, source, root = request_case
    foreign = ready(saved_image("foreign"))
    markdown = f"![Foreign]({destination}{foreign['asset_id']})"
    from apps.live_control_server.services.tiptap_markdown_write import has_saved_media_references
    assert has_saved_media_references(markdown)
    for operation, model in [
        (prepare_tiptap_markdown_write, TiptapMarkdownWritePrepareRequest),
        (commit_tiptap_markdown_write, TiptapMarkdownWriteCommitRequest),
    ]:
        values = dict(document_id=source.record.document_id, markdown=markdown,
                      expected_revision=source.loaded_revision)
        if model is TiptapMarkdownWriteCommitRequest:
            values["writer_confirm_token"] = "synthetic-unused-token"
        with pytest.raises(TiptapMarkdownWriteError, match="not available to this operator"):
            operation(root=root, request=model(**values))
    assert get_workspace_document_snapshot(root, source.record.document_id).markdown == source.markdown


@pytest.mark.parametrize("operation", ["prepare", "commit"])
def test_write_routes_require_auth_for_encoded_image(request_case, monkeypatch, operation):
    from fastapi import HTTPException
    from starlette.requests import Request
    from apps.live_control_server.routes import live
    _, source, _ = request_case
    values = dict(document_id=source.record.document_id,
                  markdown="![Foreign](dmb&#45;media:ac6c15cc-8c68-4732-8ae2-d9f3f051393a)",
                  expected_revision=source.loaded_revision)
    def refuse(request):
        raise HTTPException(401, "operator required")
    monkeypatch.setattr(live, "enforce_native_graph_gm", refuse)
    model = TiptapMarkdownWritePrepareRequest if operation == "prepare" else TiptapMarkdownWriteCommitRequest
    if operation == "commit":
        values["writer_confirm_token"] = "synthetic-unused-token"
    with pytest.raises(HTTPException) as error:
        getattr(live, "post_tiptap_markdown_write_" + operation)(
            model(**values), Request({"type": "http", "headers": []}))
    assert error.value.status_code == 401


@pytest.mark.parametrize("state", ["staged", "ready"])
def test_document_writer_saves_owned_retained_artwork_without_upload(request_case, state):
    _, source, root = request_case
    image = saved_image("local_operator")
    if state == "ready":
        ready(image)
    original = media.read_staged_bytes(image["asset_id"], "local_operator")
    markdown = source.markdown.rstrip() + f"\n\n![Private artwork](dmb-media:{image['asset_id']})\n"
    prepared = prepare_tiptap_markdown_write(root=root, request=TiptapMarkdownWritePrepareRequest(
        document_id=source.record.document_id, markdown=markdown, expected_revision=source.loaded_revision))
    commit_tiptap_markdown_write(root=root, request=TiptapMarkdownWriteCommitRequest(
        document_id=source.record.document_id, markdown=markdown, expected_revision=prepared.registry_revision,
        writer_confirm_token=prepared.writer_confirm_token))
    reopened = get_workspace_document_snapshot(root, source.record.document_id)
    assert reopened.markdown == markdown
    assert "data:" not in reopened.markdown and "https:" not in reopened.markdown
    assert media.get_asset(image["asset_id"], "local_operator")["state"] == state
    assert media.read_staged_bytes(image["asset_id"], "local_operator") == original


@pytest.mark.parametrize("change", ["uploading", "corrupt", "foreign"])
def test_commit_revalidates_private_asset_after_prepare(request_case, application_state_dsn, change):
    import psycopg
    _, source, root = request_case
    image = saved_image("local_operator")
    markdown = source.markdown.rstrip() + f"\n\n![Private artwork](dmb-media:{image['asset_id']})\n"
    prepared = prepare_tiptap_markdown_write(root=root, request=TiptapMarkdownWritePrepareRequest(
        document_id=source.record.document_id, markdown=markdown, expected_revision=source.loaded_revision))
    if change == "uploading":
        media.claim_upload(image["asset_id"], "local_operator")
    else:
        with psycopg.connect(application_state_dsn) as conn:
            if change == "corrupt":
                conn.execute("UPDATE media.storage SET staged_bytes=%s WHERE asset_id=%s", (b"corrupt", image["asset_id"]))
            else:
                conn.execute("UPDATE media.asset SET owner_id='foreign' WHERE asset_id=%s", (image["asset_id"],))
    with pytest.raises(TiptapMarkdownWriteError):
        commit_tiptap_markdown_write(root=root, request=TiptapMarkdownWriteCommitRequest(
            document_id=source.record.document_id, markdown=markdown, expected_revision=prepared.registry_revision,
            writer_confirm_token=prepared.writer_confirm_token))
    assert get_workspace_document_snapshot(root, source.record.document_id).markdown == source.markdown


def test_contextual_candidate_real_app_save_and_reopen_preserves_original(request_case, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from fastapi import Response
    from starlette.requests import Request
    from generationengine import GeneratedImage
    from apps.live_control_server.routes import media_images
    _, source, root = request_case
    parent = saved_image('local_operator')
    before = media.get_asset(parent['asset_id'], 'local_operator')
    original = media.read_staged_bytes(parent['asset_id'], 'local_operator')
    content = io.BytesIO(); Image.new('RGB', (5, 4), 'blue').save(content, format='PNG')
    client = SimpleNamespace(edit_image=AsyncMock(return_value=SimpleNamespace(
        images=[GeneratedImage(content=content.getvalue(), media_type='image/png')],
        observation=SimpleNamespace(model_dump=lambda **_: {'provider': 'synthetic'}))), aclose=AsyncMock())
    monkeypatch.setattr(media_images, 'enforce_native_graph_gm', lambda _: SimpleNamespace(subject='local_operator'))
    monkeypatch.setattr(media_images, '_fal_key', lambda: 'synthetic-never-sent')
    monkeypatch.setattr(media_images, '_image_client', lambda: client)
    result = asyncio.run(media_images.regenerate_image(parent['asset_id'], media_images.ContextualImageRequest(
        mode='image_to_image', instructions='Change the light.', expected_content_sha256=parent['content_sha256']),
        Request({'type':'http','headers':[]}), Response()))
    child = media.get_asset(result['asset_id'], 'local_operator')
    assert child['state'] == 'staged' and child['provenance']['parent_asset_id'] == str(parent['asset_id'])
    assert media.get_asset(parent['asset_id'], 'local_operator') == before
    assert media.read_staged_bytes(parent['asset_id'], 'local_operator') == original
    markdown = source.markdown.rstrip() + f"\n\n![Alternative](dmb-media:{result['asset_id']})\n"
    prepared = prepare_tiptap_markdown_write(root=root, request=TiptapMarkdownWritePrepareRequest(
        document_id=source.record.document_id, markdown=markdown, expected_revision=source.loaded_revision))
    commit_tiptap_markdown_write(root=root, request=TiptapMarkdownWriteCommitRequest(
        document_id=source.record.document_id, markdown=markdown, expected_revision=prepared.registry_revision,
        writer_confirm_token=prepared.writer_confirm_token))
    assert get_workspace_document_snapshot(root, source.record.document_id).markdown == markdown
    assert media.read_staged_bytes(child['asset_id'], 'local_operator') == content.getvalue()
