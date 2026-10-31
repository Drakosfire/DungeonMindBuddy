"""Native-authorized recap context reads use exact APP bodies, never mirrors."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

from apps.live_control_server.integrations.dungeonmind import world_graph_reads as reader
from tests.test_recap_source_read_continuity import _context_fixture_v2

pytest_plugins = ("tests.application_state.conftest",)
pytestmark = pytest.mark.usefixtures("application_state_dsn")

RAW = b"# Session 16 Recap\r\nUnicode \xce\xa9 text.\r\nTail.\r\n# Next\r\nExcluded.\r\n"


def test_context_pages_need_no_files_and_preserve_exact_bytes(tmp_path, monkeypatch):
    services, _, request, mirror, _ = _context_fixture_v2(tmp_path, RAW)
    mirror.unlink()
    parts = []
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *a, **k: pytest.fail("recap context reopened a file"))
        while True:
            page = reader.read_recap_context_direct_v2(services, request, repo_root=tmp_path)
            assert (page.line_start, page.line_end) == (2, 3)
            parts.append(page.content)
            if page.next_continuation is None:
                break
            request = request.model_copy(update={"continuation": page.next_continuation})
    assert "".join(parts) == "Unicode Ω text.\r\nTail.\r\n"


@pytest.mark.parametrize("fault", ["missing", "body", "world", "campaign", "session", "domain", "media", "encoding"])
def test_valid_file_cannot_rescue_missing_or_corrupt_app_body(tmp_path, application_state_dsn, fault):
    services, _, request, mirror, descriptors = _context_fixture_v2(tmp_path, RAW)
    artifact_id = descriptors[request.context_anchor_id].source_artifact_id
    with psycopg.connect(application_state_dsn) as conn:
        if fault == "missing":
            conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (artifact_id,))
        else:
            # Controlled corruption in this disposable APP fixture. Column
            # names are test-owned literals, never request input.
            column, value = {
                "body": ("markdown", "changed"), "world": ("world_id", "foreign"),
                "campaign": ("campaign_id", "foreign"), "session": ("session_id", "session-99"),
                "domain": ("source_domain", "worldbuilding"), "media": ("media_type", "image/png"),
                "encoding": ("encoding", "latin-1"),
            }[fault]
            from psycopg import sql
            table = "artifact" if fault in {"world", "campaign", "session", "domain"} else "revision"
            conn.execute(sql.SQL("UPDATE source.{} SET {}=%s WHERE source_artifact_id=%s").format(sql.Identifier(table), sql.Identifier(column)), (value, artifact_id))
    assert mirror.read_bytes() == RAW
    with pytest.raises(reader.DirectWorldGraphReadError) as failure:
        reader.read_recap_context_direct_v2(services, request, repo_root=tmp_path)
    assert failure.value.code == "source_unavailable"


def test_app_owner_outage_remains_unavailable_despite_valid_file(tmp_path, monkeypatch):
    from application_state.errors import ApplicationStateUnavailableError
    from application_state.source import service
    services, _, request, mirror, _ = _context_fixture_v2(tmp_path, RAW)
    def unavailable(**kwargs):
        raise ApplicationStateUnavailableError("synthetic source owner outage")
    monkeypatch.setattr(service, "get_source_markdown", unavailable)
    with pytest.raises(reader.DirectWorldGraphReadError) as failure:
        reader.read_recap_context_direct_v2(services, request, repo_root=tmp_path)
    assert failure.value.code == "source_unavailable" and failure.value.status_code == 503
    assert mirror.read_bytes() == RAW


@pytest.mark.parametrize("foreign_campaign", [False, True])
def test_world_scope_reads_only_descriptor_owned_campaign(tmp_path, foreign_campaign):
    services, _, request, _, descriptors = _context_fixture_v2(tmp_path, RAW)
    native = services.retrieval.resolve_source_context(None, context_anchor_id=request.context_anchor_id, allow_selector_v2=True)
    snapshot = SimpleNamespace(**{**vars(native.snapshot), "campaign_id": None, "scope_mode": reader.ScopeModeV2.WORLD_CROSS_CAMPAIGN})
    services.retrieval.resolve_source_context = lambda *a, **k: replace(native, snapshot=snapshot,
        context=descriptors[request.context_anchor_id])
    request = request.model_copy(update={"campaign_id": "", "scope_mode": "world"})
    if foreign_campaign:
        descriptors[request.context_anchor_id] = replace(native.context, campaign_id="foreign")
        with pytest.raises(reader.DirectWorldGraphReadError):
            reader.read_recap_context_direct_v2(services, request, repo_root=tmp_path)
    else:
        assert reader.read_recap_context_direct_v2(services, request, repo_root=tmp_path).content


@pytest.mark.parametrize("field,value", [("expected_session_id", "session-17"), ("content_sha256", "f" * 64), ("source_artifact_id", "missing")])
def test_descriptor_cannot_substitute_another_registered_source(tmp_path, field, value):
    services, _, request, _, descriptors = _context_fixture_v2(tmp_path, RAW)
    descriptor = descriptors[request.context_anchor_id]
    if field == "expected_session_id":
        selector = replace(descriptor.section_selector, expected_session_id=value,
            canonical_heading="# Session 17 Recap", legacy_session_heading="## Session 17:")
        descriptor = replace(descriptor, section_selector=selector)
    else:
        descriptor = replace(descriptor, **{field: value})
    descriptors[request.context_anchor_id] = descriptor
    with pytest.raises(reader.DirectWorldGraphReadError):
        reader.read_recap_context_direct_v2(services, request, repo_root=tmp_path)


def test_uri_is_identity_metadata_and_never_a_file_open_target(tmp_path):
    services, _, request, _, descriptors = _context_fixture_v2(tmp_path, RAW)
    descriptor = descriptors[request.context_anchor_id]
    descriptors[request.context_anchor_id] = replace(descriptor, source_uri="repo://../../never-open.md")
    page = reader.read_recap_context_direct_v2(services, request, repo_root=tmp_path)
    assert page.content
    descriptors[request.context_anchor_id] = descriptor
    with pytest.raises(reader.DirectWorldGraphReadError):
        reader.read_recap_context_direct_v2(services, request.model_copy(update={"continuation": page.next_continuation}), repo_root=tmp_path)


@pytest.mark.integration
def test_native_context_and_historical_graph_pin_read_without_files(tmp_path, monkeypatch, application_state_dsn):
    from tests.test_recap_source_read_continuity import _prepare_session, _confirm_via_product_seam
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from graph_memory.retrieval.models import RecapContextIndexRequestV2, RecapContextReadRequestV2
    source = "# Session 22 Recap\nA synthetic native recap body.\n# Next\nExcluded.\n"
    case = _prepare_session(tmp_path, monkeypatch, application_state_dsn,
        world_id="world:recap-context", campaign_id="longmont-c2", session_id="session-22",
        node_id="node:location:context", recap_text=source)
    receipt = _confirm_via_product_seam(case)
    revision = receipt["committed_revision_id"]
    services = reader.build_direct_world_graph_read_services(database_url=case.dsn, world_id=case.world_id)
    common = dict(worldId=case.world_id, campaignId=case.campaign_id, scopeMode="campaign", revisionPin=revision)
    index = reader.list_recap_context_direct_v2(services, RecapContextIndexRequestV2.model_validate({
        "schema": "dmb_recap_context_index_request_v2", **common}))
    assert len(index.entries) == 1
    descriptor = index.entries[0]
    request = RecapContextReadRequestV2.model_validate({"schema": "dmb_recap_context_read_request_v2", **common,
        "contextAnchorId": descriptor.context_anchor_id, "maxChars": 7})
    # Advance the head without changing any source or facts. The original
    # pinned context must retain its exact body after the operational tree goes.
    parent = services.bundle.world_graph.get_revision(case.world_id, revision)
    services.bundle.world_graph.publish_revision(PublishRevisionCommand(
        world_id=case.world_id, parent_revision_id=revision, expected_parent_revision_id=revision,
        operation_ids=["test:context-descendant"], graph_schema=parent.revision.graph_schema,
        graph_payload=parent.graph_payload, created_at=parent.revision.created_at))
    for file in case.repo.rglob("*"):
        if file.is_file():
            file.unlink()
    pages = []
    while True:
        page = reader.read_recap_context_direct_v2(services, request, repo_root=case.repo)
        assert not page.snapshot.is_head
        pages.append(page.content)
        if page.next_continuation is None:
            break
        request = request.model_copy(update={"continuation": page.next_continuation})
    assert "".join(pages) == "A synthetic native recap body.\n"
    wrong = request.model_copy(update={"revision_pin": "revision:missing", "continuation": None})
    with pytest.raises(reader.DirectWorldGraphReadError):
        reader.read_recap_context_direct_v2(services, wrong, repo_root=case.repo)
    # Corrupt only the fresh native fixture's revision metadata. Core must
    # revoke the old context identity; Buddy must not serve the valid APP body.
    with psycopg.connect(case.dsn) as conn:
        conn.execute("UPDATE dungeonmind.source_revisions SET content_sha256=%s WHERE source_artifact_id=%s",
                     ("f" * 64, case.artifact_id))
    fresh = reader.build_direct_world_graph_read_services(database_url=case.dsn, world_id=case.world_id)
    try:
        rejected = reader.read_recap_context_direct_v2(fresh,
            request.model_copy(update={"continuation": None}), repo_root=case.repo)
    except reader.DirectWorldGraphReadError:
        pass
    else:
        assert rejected.outcome == "empty" and rejected.content is None
