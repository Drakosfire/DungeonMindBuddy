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
