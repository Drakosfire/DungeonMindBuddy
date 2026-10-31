from __future__ import annotations
from tests.page_fixtures import create_page_fixture, page_text, save_page

from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteConflictError,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    authorize_target_for_record,
    commit_tiptap_markdown_write,
    markdown_lossy_diagnostics,
    normalize_tiptap_target_relpath,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    create_workspace_document,
    discard_workspace_document,
    get_workspace_document,
    get_workspace_document_snapshot,
)




def test_normalize_allows_plan_workspace_target() -> None:
    document_id = "11111111-1111-4111-8111-111111111111"
    relpath = f"out/workspace/plan/{document_id}.md"
    assert normalize_tiptap_target_relpath(relpath) == relpath


def test_normalize_rejects_traversal_and_escape() -> None:
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath("../secrets.md")
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath("/tmp/escape.md")
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath("out/workspace/worldbuilding/not-a-uuid.md")
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath("out/workspace/plan/not-a-uuid.md")


def test_authorize_target_binds_plan_workspace_to_own_document_id() -> None:
    own_id = "11111111-1111-4111-8111-111111111111"
    other_id = "22222222-2222-4222-8222-222222222222"
    record = WorkspaceDocumentRecord(
        document_id=own_id,
        title="Plan draft",
        campaign_id="eldyrwild",
        kind="plan",
        target_relpath=f"out/workspace/plan/{other_id}.md",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    with pytest.raises(TiptapMarkdownWriteError):
        authorize_target_for_record(record)


def test_plan_workspace_prepare_commit_round_trip(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="If the party goes north",
        campaign_id="longmont-c2",
        kind="plan",
        target_session=27,
    )
    assert record.target_relpath == f"out/workspace/plan/{record.document_id}.md"
    markdown = "# North fork\n\nBody.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    assert prepared.target_relpath == record.target_relpath

    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=1,
        ),
    )
    assert committed.writer_ok is True
    assert committed.bytes_written
    assert "WorkRevision committed in PostgreSQL" in committed.diagnostics
    target = tmp_path / (record.target_relpath or "")
    assert not target.exists()
    loaded = get_workspace_document(tmp_path, record.document_id)
    assert loaded.content_status == "committed"


def test_world_scope_requires_versioned_prepare_and_commit_contracts() -> None:
    with pytest.raises(ValidationError, match="World-scoped writes require the V2 schema"):
        TiptapMarkdownWritePrepareRequest(
            document_id="doc-a",
            markdown="# Plan\n",
            scope_mode="world",
            world_id="world-a",
        )
    with pytest.raises(ValidationError, match="V2 World writes require scope_mode=world"):
        TiptapMarkdownWritePrepareRequest(
            document_id="doc-a",
            markdown="# Plan\n",
            schema_version="dmb_tiptap_markdown_write_prepare_v2",
            scope_mode="world",
        )

    with pytest.raises(ValidationError, match="World-scoped writes require the V2 schema"):
        TiptapMarkdownWriteCommitRequest(
            document_id="doc-a",
            markdown="# Plan\n",
            writer_confirm_token="confirmation",
            scope_mode="world",
            world_id="world-a",
        )
    with pytest.raises(ValidationError, match="V2 World writes require scope_mode=world"):
        TiptapMarkdownWriteCommitRequest(
            document_id="doc-a",
            markdown="# Plan\n",
            writer_confirm_token="confirmation",
            schema_version="dmb_tiptap_markdown_write_commit_v2",
            scope_mode="world",
        )


def test_lossy_markdown_diagnostics_block_tables_and_html() -> None:
    diagnostics = markdown_lossy_diagnostics("| a | b |\n| --- | --- |\n<div>x</div>\n")
    assert diagnostics
    assert any("line 1" in item for item in diagnostics)


@pytest.mark.parametrize("envelope", ["", "---\ntitle: Edge\n---\n"])
def test_worldbuilding_editor_table_prepare_commit_readback(tmp_path: Path, envelope: str) -> None:
    record = _create_world_scoped_source(tmp_path)
    record = save_page(tmp_path, record.document_id, envelope + '# Edge\nA fort town.\n')
    markdown = envelope + "# Edge\n\n| d20 | Soldier | Detail |\n| --- | --- | --- |\n| 1 | Mara | Gate guard |\n| 20 | Pell | Peacekeeper |\n"
    before = page_text(tmp_path, record.document_id).encode("utf-8")
    prepared = prepare_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWritePrepareRequest(
        document_id=record.document_id, markdown=markdown, expected_revision=record.revision))
    assert prepared.writer_ok and prepared.writer_confirm_token
    assert page_text(tmp_path, record.document_id).encode("utf-8") == before
    committed = commit_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWriteCommitRequest(
        document_id=record.document_id, markdown=markdown, expected_revision=record.revision,
        writer_confirm_token=prepared.writer_confirm_token))
    assert committed.writer_ok
    assert page_text(tmp_path, record.document_id) == markdown
    assert get_workspace_document(tmp_path, record.document_id).revision == record.revision + 1


@pytest.mark.parametrize("markdown", [
    "| a | b |\n| --- | --- |\n| one | two | discarded |",
    "| a | b |\n| --- | --- |\n| one |",
    "| a | b |\n| :--- | --- |\n| one | two |",
    "| a | b |\n| --- | --- |\n| <b>unsafe</b> | two |",
    "| a | b |\n| --- | --- |\n| ![image](https://example.com) | two |",
    "| a | b |",
])
def test_editor_table_admission_still_rejects_non_roundtrippable_tables(markdown):
    assert markdown_lossy_diagnostics(markdown, allow_editor_tables=True)


def test_worldbuilding_prepare_commit_round_trip(tmp_path: Path) -> None:
    record = create_page_fixture(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Title\n\nA supported paragraph.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    assert prepared.target_relpath == f"worldbuilding_source:{record.document_id}"

    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=record.revision,
        ),
    )
    assert committed.writer_ok is True
    assert committed.bytes_written
    assert get_workspace_document(tmp_path, record.document_id).content_status == "committed"
    assert page_text(tmp_path, record.document_id) == "# Title\n\nA supported paragraph.\n"


def test_lossy_markdown_blocks_prepare_and_commit_for_worldbuilding(tmp_path: Path) -> None:
    record = create_page_fixture(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Title\n\n| a | b |\n| :--- | ---: |\n| 1 | 2 |\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
        ),
    )
    assert prepared.writer_ok is False
    assert prepared.writer_confirm_token is None
    assert any("lossy" in item for item in prepared.diagnostics)

    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token="deadbeef",
                expected_revision=record.revision,
            ),
        )
    assert exc_info.value.status_code in {409, 422}
    assert not list(tmp_path.rglob("*.md"))


@pytest.mark.parametrize("kind", ["plan", "runbook"])
def test_lossy_markdown_is_advisory_for_plan_and_runbook(tmp_path: Path, kind: str) -> None:
    if kind == "plan":
        target = (
            "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/"
            "Session Prep/Session 23 Prep.md"
        )
    else:
        target = "evals/c2_live_prep/mireward-prep/content/tiptap/advisory-lossy.md"
    record = create_workspace_document(
        tmp_path,
        title="Advisory Doc",
        campaign_id="eldyrwild",
        kind=kind,  # type: ignore[arg-type]
        target_relpath=target,
    )
    markdown = "# Title\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    assert any("lossy" in item for item in prepared.diagnostics)
    assert any("advisory" in item.lower() for item in prepared.warnings)

    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=1,
        ),
    )
    assert committed.writer_ok is True
    snapshot = get_workspace_document_snapshot(tmp_path, record.document_id)
    assert snapshot.markdown == markdown
    assert snapshot.file_exists is False


def test_plan_and_runbook_cannot_authorize_foreign_worldbuilding_path() -> None:
    foreign_target = (
        "out/workspace/worldbuilding/11111111-1111-4111-8111-111111111111.md"
    )
    for kind, document_id in (
        ("plan", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ("runbook", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    ):
        record = WorkspaceDocumentRecord(
            document_id=document_id,
            title=f"Cross-kind {kind}",
            campaign_id="eldyrwild",
            kind=kind,  # type: ignore[arg-type]
            target_relpath=foreign_target,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        with pytest.raises(TiptapMarkdownWriteError):
            authorize_target_for_record(record)




@pytest.mark.parametrize(
    ("kind", "clean_target", "extra"),
    [
        (
            "plan",
            "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
            {},
        ),
        (
            "runbook",
            "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md",
            {},
        ),
    ],
)
def test_authorize_rejects_whitespace_contaminated_targets(
    kind: str,
    clean_target: str,
    extra: dict[str, str],
) -> None:
    document_id = "11111111-1111-4111-8111-111111111111"
    record = WorkspaceDocumentRecord(
        document_id=document_id,
        title="Whitespace target",
        campaign_id="eldyrwild",
        kind=kind,  # type: ignore[arg-type]
        target_relpath=f" {clean_target} ",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        **extra,  # type: ignore[arg-type]
    )
    with pytest.raises(TiptapMarkdownWriteError, match="normalized repo-relative path"):
        authorize_target_for_record(record)
















def test_discarded_document_cannot_write(tmp_path: Path) -> None:
    record = create_page_fixture(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    discard_workspace_document(tmp_path, record.document_id)
    with pytest.raises(TiptapMarkdownWriteError):
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id=record.document_id,
                markdown="# Title\n\nBody.\n",
                expected_revision=2,
            ),
        )


def test_stale_revision_prepare_conflicts(tmp_path: Path) -> None:
    record = create_page_fixture(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id=record.document_id,
                markdown="# Title\n\nBody.\n",
                expected_revision=99,
            ),
        )
    assert exc_info.value.status_code == 409


LOSSY_IMPORT_MARKDOWN = """# Hesta's Apothecary

![Hesta behind the counter](assets/hesta.webp)

| Item | Price |
|---|---:|
| Healing draught | 25 gp |

---

<section data-source-note="preserve-me">
Awkward HTML block.
</section>
"""


def _ensure_eldyrwild_world_root(root: Path) -> None:
    (root / "corpus" / "eldyrwild-markdown").mkdir(parents=True)


def _create_world_scoped_source(root: Path):
    _ensure_eldyrwild_world_root(root)
    return create_page_fixture(
        root,
        title="Imported Source",
        campaign_id="longmont-c2",
        kind="worldbuilding_source",
        world_id="eldyrwild",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )


def test_source_import_preserves_lossy_markdown_byte_for_byte(tmp_path: Path) -> None:
    record = _create_world_scoped_source(tmp_path)
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    assert markdown_lossy_diagnostics(LOSSY_IMPORT_MARKDOWN)

    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    assert committed.writer_ok is True
    assert page_text(tmp_path, record.document_id) == LOSSY_IMPORT_MARKDOWN


def test_source_import_preserves_trailing_blank_lines_without_normalization(
    tmp_path: Path,
) -> None:
    record = _create_world_scoped_source(tmp_path)
    exact_markdown = "# Exact import\n\nBody line.\n\n\n\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=exact_markdown,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=exact_markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    assert committed.writer_ok is True
    assert page_text(tmp_path, record.document_id) == exact_markdown


def test_source_import_preserves_markdown_without_trailing_newline(tmp_path: Path) -> None:
    record = _create_world_scoped_source(tmp_path)
    exact_markdown = "# No trailing newline"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=exact_markdown,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=exact_markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    assert committed.writer_ok is True
    assert page_text(tmp_path, record.document_id) == exact_markdown


def test_source_import_blocks_same_body_in_authoring_mode(tmp_path: Path) -> None:
    record = _create_world_scoped_source(tmp_path)
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            expected_revision=record.revision,
        ),
    )
    assert prepared.writer_ok is False
    assert prepared.writer_confirm_token is None


def test_second_source_import_rejected_after_initial_commit(tmp_path: Path) -> None:
    record = _create_world_scoped_source(tmp_path)
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id=record.document_id,
                markdown=LOSSY_IMPORT_MARKDOWN,
                expected_revision=2,
                write_mode="source_import",
            ),
        )


def test_source_import_stale_revision_and_mode_mismatch_fail_closed(tmp_path: Path) -> None:
    record = _create_world_scoped_source(tmp_path)
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            expected_revision=record.revision,
            write_mode="source_import",
        ),
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=LOSSY_IMPORT_MARKDOWN,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=record.revision,
                write_mode="authoring",
            ),
        )




@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_worldbuilding_preserves_existing_yaml_while_saving_body(tmp_path, newline):
    record = _create_world_scoped_source(tmp_path)
    envelope = newline.join(["--- ", "title: Mirathorn", "source_class: seed_reference", "---", ""])
    record = save_page(tmp_path, record.document_id, ((envelope + '# Lore' + newline + 'Old body.' + newline).encode()).decode("utf-8"))
    changed = envelope + "# Lore" + newline + "Edited body." + newline
    prepared = prepare_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWritePrepareRequest(
        document_id=record.document_id, markdown=changed, expected_revision=record.revision))
    assert prepared.writer_ok and prepared.writer_confirm_token
    assert not any("unsupported" in item for item in prepared.diagnostics + prepared.warnings)
    commit_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWriteCommitRequest(
        document_id=record.document_id, markdown=changed, expected_revision=record.revision,
        writer_confirm_token=prepared.writer_confirm_token))
    assert page_text(tmp_path, record.document_id).encode("utf-8") == changed.replace("\r\n", "\n").encode()
    reopened = get_workspace_document_snapshot(tmp_path, record.document_id)
    assert get_workspace_document(tmp_path, record.document_id).revision == record.revision + 1
    assert reopened.markdown == changed.replace("\r\n", "\n")
    assert reopened.loaded_revision == record.revision + 1


@pytest.mark.parametrize("case", ["changed", "removed", "added", "malformed", "unclosed", "thematic", "html", "table"])
def test_worldbuilding_yaml_exception_does_not_admit_lossy_or_metadata_changes(tmp_path, case):
    record = _create_world_scoped_source(tmp_path)
    envelope = "---\ntitle: Mirathorn\n---\n"
    original = envelope + "# Lore\nBody.\n"
    record = save_page(tmp_path, record.document_id, (original.encode()).decode("utf-8"))
    proposed = {
        "changed": original.replace("title: Mirathorn", "title: Other"),
        "removed": "# Lore\nBody.\n",
        "added": original,
        "malformed": "---\nno YAML key\n---\n# Lore\n",
        "unclosed": "---\ntitle: Mirathorn\n# Lore\n",
        "thematic": original + "---\n",
        "html": original + "<div>Unsupported</div>\n",
        "table": original + "| a | b |\n",
        "line-endings": original.replace("\n", "\r\n"),
    }[case]
    if case == "added":
        record = save_page(tmp_path, record.document_id, b'# Lore\nBody.\n'.decode('utf-8'))
    before = page_text(tmp_path, record.document_id).encode("utf-8")
    prepared = prepare_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWritePrepareRequest(
        document_id=record.document_id, markdown=proposed, expected_revision=record.revision))
    assert not prepared.writer_ok and prepared.writer_confirm_token is None
    if case in {"thematic", "html", "table"}:
        assert "line 6: unsupported Markdown block would be lossy on commit" in prepared.diagnostics
    assert page_text(tmp_path, record.document_id).encode("utf-8") == before
    assert get_workspace_document(tmp_path, record.document_id).revision == record.revision


@pytest.mark.parametrize("intervening", ["body", "metadata"])
def test_preserved_yaml_authoring_still_requires_exact_save_basis(tmp_path, intervening):
    record = _create_world_scoped_source(tmp_path)
    original = "---\ntitle: Lore\n---\n# Lore\nOld.\n"
    record = save_page(tmp_path, record.document_id, original)
    changed = original.replace("Old.", "Edited.")
    prepared = prepare_tiptap_markdown_write(root=tmp_path, request=TiptapMarkdownWritePrepareRequest(
        document_id=record.document_id, markdown=changed, expected_revision=record.revision))
    assert prepared.writer_ok
    request = TiptapMarkdownWriteCommitRequest(document_id=record.document_id,
        markdown=changed, expected_revision=record.revision, writer_confirm_token=prepared.writer_confirm_token)
    if intervening == "body":
        record = save_page(tmp_path, record.document_id, original.replace('Old.', 'Concurrent.'))
    else:
        from apps.live_control_server.services.workspace_document_registry import update_workspace_document_metadata
        update_workspace_document_metadata(tmp_path, record.document_id, title="New title", expected_revision=record.revision)
    before = page_text(tmp_path, record.document_id).encode("utf-8")
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit_tiptap_markdown_write(root=tmp_path, request=request)
    assert page_text(tmp_path, record.document_id).encode("utf-8") == before
