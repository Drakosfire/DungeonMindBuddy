from __future__ import annotations

from pathlib import Path

import pytest

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
    WorkspaceDocumentRegistryError,
    create_workspace_document,
    discard_workspace_document,
    get_workspace_document,
)


def test_normalize_allows_worldbuilding_workspace_target() -> None:
    document_id = "11111111-1111-4111-8111-111111111111"
    relpath = f"out/workspace/worldbuilding/{document_id}.md"
    assert normalize_tiptap_target_relpath(relpath) == relpath


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
    assert "corpus was not mutated" in committed.diagnostics
    target = tmp_path / (record.target_relpath or "")
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == markdown
    assert not str(record.target_relpath).startswith("corpus/")
    loaded = get_workspace_document(tmp_path, record.document_id)
    assert loaded.content_status == "committed"


def test_lossy_markdown_diagnostics_block_tables_and_html() -> None:
    diagnostics = markdown_lossy_diagnostics("| a | b |\n| --- | --- |\n<div>x</div>\n")
    assert diagnostics
    assert any("line 1" in item for item in diagnostics)


def test_worldbuilding_prepare_commit_round_trip(tmp_path: Path) -> None:
    record = create_workspace_document(
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
    target = tmp_path / record.target_relpath
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "# Title\n\nA supported paragraph.\n"


def test_lossy_markdown_blocks_prepare_and_commit_for_worldbuilding(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
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
                expected_revision=1,
            ),
        )
    assert exc_info.value.status_code in {409, 422}
    assert not (tmp_path / record.target_relpath).exists()


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
    assert (tmp_path / target).read_text(encoding="utf-8") == markdown


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


def test_authorize_target_binds_worldbuilding_to_own_document_id() -> None:
    own_id = "11111111-1111-4111-8111-111111111111"
    other_id = "22222222-2222-4222-8222-222222222222"
    record = WorkspaceDocumentRecord(
        document_id=own_id,
        title="WB",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        target_relpath=f"out/workspace/worldbuilding/{other_id}.md",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    with pytest.raises(TiptapMarkdownWriteError):
        authorize_target_for_record(record)


@pytest.mark.parametrize(
    ("kind", "clean_target", "extra"),
    [
        (
            "worldbuilding_source",
            "out/workspace/worldbuilding/11111111-1111-4111-8111-111111111111.md",
            {
                "source_domain": "worldbuilding",
                "document_class": "lore",
                "authority_state": "draft",
                "visibility_state": "internal",
            },
        ),
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


def _backup_names(target: Path) -> set[str]:
    backups_dir = target.parent / ".backups"
    if not backups_dir.is_dir():
        return set()
    return {path.name for path in backups_dir.iterdir()}


def test_registry_failure_rolls_back_new_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Title\n\nBody.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    target = tmp_path / (record.target_relpath or "")
    assert not target.exists()
    backups_before = _backup_names(target)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise WorkspaceDocumentRegistryError("injected registry failure", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write.mark_workspace_document_committed_unlocked",
        boom,
    )
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    assert exc_info.value.status_code == 500
    assert not target.exists()
    assert _backup_names(target) == backups_before
    fresh = get_workspace_document(tmp_path, record.document_id)
    assert fresh.content_status == "draft"
    assert fresh.revision == record.revision


def test_registry_failure_restores_prior_file_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# prior\n", encoding="utf-8")
    markdown = "# Title\n\nReplacement.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    backups_before = _backup_names(target)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise WorkspaceDocumentRegistryError("injected registry failure", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write.mark_workspace_document_committed_unlocked",
        boom,
    )
    with pytest.raises(TiptapMarkdownWriteError):
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    assert target.read_text(encoding="utf-8") == "# prior\n"
    assert _backup_names(target) == backups_before


def test_registry_write_json_oserror_rolls_back_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# prior\n", encoding="utf-8")
    markdown = "# Title\n\nReplacement.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    backups_before = _backup_names(target)

    def boom_write_json(_path: Path, _data: object) -> None:
        raise OSError("simulated registry write_json failure")

    monkeypatch.setattr(
        "apps.live_control_server.services.workspace_document_registry.write_json",
        boom_write_json,
    )
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    assert exc_info.value.status_code == 500
    assert "registry" in str(exc_info.value).lower() or "persist" in str(exc_info.value).lower()
    assert target.read_text(encoding="utf-8") == "# prior\n"
    assert _backup_names(target) == backups_before
    fresh = get_workspace_document(tmp_path, record.document_id)
    assert fresh.content_status == "draft"
    assert fresh.revision == record.revision


def test_target_replace_oserror_restores_prior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# prior\n", encoding="utf-8")
    markdown = "# Title\n\nReplacement.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    backups_before = _backup_names(target)

    original_replace = Path.replace

    def boom_replace(self: Path, target_path: Path | str) -> Path:
        destination = Path(target_path)
        if destination.resolve() == target.resolve():
            raise OSError("simulated target replace failure")
        return original_replace(self, destination)

    monkeypatch.setattr(Path, "replace", boom_replace)
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    assert exc_info.value.status_code == 500
    assert "failed to write" in str(exc_info.value).lower()
    assert target.read_text(encoding="utf-8") == "# prior\n"
    assert _backup_names(target) == backups_before


def test_registry_failure_with_rollback_failure_reports_partial_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# prior\n", encoding="utf-8")
    markdown = "# Title\n\nReplacement.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    backups_before = _backup_names(target)

    def boom_registry(*_args: object, **_kwargs: object) -> None:
        raise WorkspaceDocumentRegistryError("injected registry failure", status_code=500)

    def boom_restore(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated rollback failure")

    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write.mark_workspace_document_committed_unlocked",
        boom_registry,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write._restore_prior_file_state",
        boom_restore,
    )
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    message = str(exc_info.value).lower()
    assert exc_info.value.status_code == 500
    assert "registry commit failed" in message
    assert "rollback" in message
    # Partial failure: new Markdown remains because rollback itself failed.
    assert target.read_text(encoding="utf-8") == markdown
    # Backup cleanup still runs after restore failure.
    assert _backup_names(target) == backups_before


def test_backup_cleanup_failure_is_reported_in_partial_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# prior\n", encoding="utf-8")
    markdown = "# Title\n\nReplacement.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )

    def boom_registry(*_args: object, **_kwargs: object) -> None:
        raise WorkspaceDocumentRegistryError("injected registry failure", status_code=500)

    original_unlink = Path.unlink

    def boom_unlink(self: Path, *args: object, **kwargs: object) -> None:
        if self.parent.name == ".backups":
            raise OSError("simulated backup cleanup failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write.mark_workspace_document_committed_unlocked",
        boom_registry,
    )
    monkeypatch.setattr(Path, "unlink", boom_unlink)
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    message = str(exc_info.value).lower()
    assert exc_info.value.status_code == 500
    assert "backup cleanup also failed" in message
    assert target.read_text(encoding="utf-8") == "# prior\n"


def test_discarded_document_cannot_write(tmp_path: Path) -> None:
    record = create_workspace_document(
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
    record = create_workspace_document(
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
    return create_workspace_document(
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
            expected_revision=1,
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
            expected_revision=1,
            write_mode="source_import",
        ),
    )
    assert committed.writer_ok is True
    target = tmp_path / (record.target_relpath or "")
    assert target.read_text(encoding="utf-8") == LOSSY_IMPORT_MARKDOWN.rstrip("\n") + "\n"


def test_source_import_blocks_same_body_in_authoring_mode(tmp_path: Path) -> None:
    record = _create_world_scoped_source(tmp_path)
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            expected_revision=1,
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
            expected_revision=1,
            write_mode="source_import",
        ),
    )
    commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=LOSSY_IMPORT_MARKDOWN,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=1,
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
            expected_revision=1,
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
                expected_revision=1,
                write_mode="authoring",
            ),
        )


def test_normalize_allows_world_scoped_corpus_source_target() -> None:
    document_id = "11111111-1111-4111-8111-111111111111"
    relpath = (
        f"corpus/eldyrwild-markdown/_dungeonbuddy/sources/{document_id}/source.md"
    )
    assert normalize_tiptap_target_relpath(relpath) == relpath
