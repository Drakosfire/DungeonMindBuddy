"""HTTP contract for GET /api/live/source-navigation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.source_artifact_registry import (
    create_recap_source_artifact,
    create_source_artifact_from_workspace_document,
    load_source_span_index,
    source_artifacts_path,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    workspace_documents_path,
)
from src.live_play.live_store import load_json, write_json

GLASS_ORCHARD_WORLD_ID = "the-glass-orchard"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "corpus" / "the-glass-orchard-markdown").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.source_navigation.repo_root",
        lambda: root,
    )
    return TestClient(create_app())


def _commit_markdown(
    root: Path,
    *,
    document_id: str,
    markdown: str,
    expected_revision: int,
    write_mode: str = "source_import",
) -> None:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=expected_revision,
            write_mode=write_mode,
        ),
    )
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=expected_revision,
            write_mode=write_mode,
        ),
    )


def _setup_glass_orchard_source(
    root: Path,
    markdown: str,
) -> tuple[str, str, str, int, int]:
    """Return artifact_id, document_id, span_id, start_line, end_line."""
    record = create_workspace_document(
        root,
        title="Hesta Source",
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        kind="worldbuilding_source",
        world_id=GLASS_ORCHARD_WORLD_ID,
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    _commit_markdown(
        root,
        document_id=record.document_id,
        markdown=markdown,
        expected_revision=1,
    )
    artifact = create_source_artifact_from_workspace_document(
        root,
        document_id=record.document_id,
        expected_revision=2,
    )
    index = load_source_span_index(root, artifact.source_artifact_id)
    assert len(index.spans) >= 2, "fixture markdown must yield multiple spans"
    second_span = index.spans[1]
    return (
        artifact.source_artifact_id,
        record.document_id,
        second_span.source_span_id,
        second_span.start_line,
        second_span.end_line,
    )


def _navigation_url(*, artifact_id: str, span_id: str) -> str:
    return (
        "/api/live/source-navigation"
        f"?source_artifact_id={artifact_id}&source_span_ref_id={span_id}"
    )


def _registry_digest(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_navigation_returns_highlightable_span(client: TestClient, root: Path) -> None:
    markdown = "# Hesta\n\nFirst paragraph.\n\nSecond paragraph for evidence.\n\nThird.\n"
    artifact_id, document_id, span_id, start_line, end_line = _setup_glass_orchard_source(
        root, markdown
    )

    response = client.get(_navigation_url(artifact_id=artifact_id, span_id=span_id))
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "dmb_build_source_navigation_v1"
    assert body["status"] == "exact"
    assert body["canHighlight"] is True
    assert body["sourceArtifactId"] == artifact_id
    assert body["sourceSpanRefId"] == span_id
    assert body["documentId"] == document_id
    assert body["worldId"] == GLASS_ORCHARD_WORLD_ID
    assert body["campaignId"] == GLASS_ORCHARD_WORLD_ID
    assert body["startLine"] == start_line
    assert body["endLine"] == end_line
    assert body["artifactContentSha256"] == body["currentContentSha256"]


def test_stale_navigation_after_source_mutation(client: TestClient, root: Path) -> None:
    markdown = "# Hesta\n\nFirst paragraph.\n\nSecond paragraph for evidence.\n\nThird.\n"
    artifact_id, document_id, span_id, start_line, end_line = _setup_glass_orchard_source(
        root, markdown
    )

    updated = "# Hesta\n\nRewritten source bytes.\n\nDifferent evidence.\n"
    _commit_markdown(
        root,
        document_id=document_id,
        markdown=updated,
        expected_revision=2,
        write_mode="authoring",
    )

    response = client.get(_navigation_url(artifact_id=artifact_id, span_id=span_id))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "stale"
    assert body["canHighlight"] is False
    assert body["documentId"] == document_id
    assert body["startLine"] == start_line
    assert body["endLine"] == end_line
    assert body["artifactContentSha256"] != body["currentContentSha256"]


def test_missing_artifact_returns_404(client: TestClient) -> None:
    response = client.get(
        _navigation_url(
            artifact_id="artifact:worldbuilding:missing",
            span_id="artifact:worldbuilding:missing:span:abc:1-1",
        )
    )
    assert response.status_code == 404


def test_missing_span_returns_404_without_first_win(client: TestClient, root: Path) -> None:
    markdown = "# Hesta\n\nFirst paragraph.\n\nSecond paragraph for evidence.\n\nThird.\n"
    artifact_id, _document_id, span_id, _start, _end = _setup_glass_orchard_source(
        root, markdown
    )
    foreign_span_id = f"{artifact_id}:span:deadbeef0000:99-99"

    response = client.get(
        _navigation_url(artifact_id=artifact_id, span_id=foreign_span_id)
    )
    assert response.status_code == 404
    assert "detail" in response.json()


def test_foreign_span_from_other_artifact_rejected(client: TestClient, root: Path) -> None:
    first_markdown = "# Alpha\n\nAlpha paragraph one.\n\nAlpha paragraph two.\n"
    first_artifact_id, _first_doc, _first_span, _, _ = _setup_glass_orchard_source(
        root, first_markdown
    )

    second_markdown = "# Beta\n\nBeta paragraph one.\n\nBeta paragraph two.\n"
    _second_artifact_id, _second_doc, second_span_id, _, _ = _setup_glass_orchard_source(
        root, second_markdown
    )

    response = client.get(
        _navigation_url(artifact_id=first_artifact_id, span_id=second_span_id)
    )
    assert response.status_code == 404


def test_recap_artifact_rejected(client: TestClient, root: Path) -> None:
    recap_path = root / "recaps" / "session-1.md"
    recap_path.parent.mkdir(parents=True)
    recap_path.write_text("# Recap\n\nSession notes.\n", encoding="utf-8")
    artifact = create_recap_source_artifact(
        root,
        campaign_id="longmont-c2",
        session_id="session-1",
        recap_path=recap_path,
    )
    index = load_source_span_index(root, artifact.source_artifact_id)
    span_id = index.spans[0].source_span_id

    response = client.get(
        _navigation_url(artifact_id=artifact.source_artifact_id, span_id=span_id)
    )
    assert response.status_code == 422


def test_foreign_world_lineage_mismatch_rejected(client: TestClient, root: Path) -> None:
    markdown = "# Hesta\n\nFirst paragraph.\n\nSecond paragraph for evidence.\n\nThird.\n"
    artifact_id, _document_id, span_id, _, _ = _setup_glass_orchard_source(root, markdown)

    registry_path = source_artifacts_path(root)
    payload = load_json(registry_path)
    for record in payload.get("records", []):
        if record.get("source_artifact_id") == artifact_id:
            record["world_id"] = "other-world"
            record["campaign_id"] = "other-world"
    write_json(registry_path, payload)

    response = client.get(_navigation_url(artifact_id=artifact_id, span_id=span_id))
    assert response.status_code == 409


def test_request_uses_only_artifact_and_span_authority(client: TestClient, root: Path) -> None:
    markdown = "# Hesta\n\nFirst paragraph.\n\nSecond paragraph for evidence.\n\nThird.\n"
    artifact_id, document_id, span_id, _, _ = _setup_glass_orchard_source(root, markdown)

    response = client.get(
        "/api/live/source-navigation",
        params={
            "source_artifact_id": artifact_id,
            "source_span_ref_id": span_id,
            "documentId": "00000000-0000-4000-8000-000000000099",
            "path": "corpus/hack/source.md",
            "startLine": "99",
            "endLine": "100",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["documentId"] == document_id
    assert body["status"] == "exact"


def test_navigation_is_read_only(client: TestClient, root: Path) -> None:
    markdown = "# Hesta\n\nFirst paragraph.\n\nSecond paragraph for evidence.\n\nThird.\n"
    artifact_id, document_id, span_id, _, _ = _setup_glass_orchard_source(root, markdown)

    artifact_registry = source_artifacts_path(root)
    workspace_registry = workspace_documents_path(root)
    before_artifact_registry = _registry_digest(artifact_registry)
    before_workspace_registry = _registry_digest(workspace_registry)
    target_relpath = None
    for record in load_json(workspace_registry).get("records", []):
        if record.get("document_id") == document_id:
            target_relpath = record.get("target_relpath")
            break
    assert target_relpath
    source_path = root / target_relpath
    before_source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()

    for _ in range(2):
        response = client.get(_navigation_url(artifact_id=artifact_id, span_id=span_id))
        assert response.status_code == 200
        assert response.json()["status"] == "exact"

    assert _registry_digest(artifact_registry) == before_artifact_registry
    assert _registry_digest(workspace_registry) == before_workspace_registry
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == before_source_digest
