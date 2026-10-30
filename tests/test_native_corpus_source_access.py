"""Actual Core source-only reads; no APP/retained World/provider operations."""
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace

import pytest
from dungeonmind.application.vnext import (
    initialize_empty_knowledge_space,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
from graph_memory.vnext.domain_runtime import (
    GM_LABEL,
    dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_custom_predicate_profile,
)
from apps.live_control_server.integrations.dungeonmind.native_corpus_source import capture_native_sources

NOW = datetime(2026, 10, 29, tzinfo=UTC)
GM = SimpleNamespace(role="gm")
BODY = "# Source\n\nÉphanna heard the guard.\n\nThe party later reunited.\n"


@pytest.fixture
def lane():
    repo = InMemoryNativeSourceEvidenceRepository()
    domain = dungeonbuddy_world_domain_contract()
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    initialize_empty_knowledge_space(repository=repo, space_id="world:test",
        initialization_id="test:init", created_at=NOW, domain_contract=domain,
        semantic_profile=profile)
    bound = SimpleNamespace(managed_world_id="managed", native_world_id="world:test",
        binding_version=1, provisioning_id="provisioned:not-graph-active")
    return SimpleNamespace(repo=repo, domain=domain, profile=profile, bound=bound)


def admit(lane, name="first", *, body=BODY, multiple=False):
    raw = body.encode()
    first = len(body.splitlines(keepends=True)[0].encode())
    spans = [dict(client_ref="opening", evidence_role="support", start_byte=0,
        end_byte=first, expected_slice_sha256=sha256(raw[:first]).hexdigest())]
    if multiple:
        spans.append(dict(client_ref="later", evidence_role="context", start_byte=first,
            end_byte=len(raw), expected_slice_sha256=sha256(raw[first:]).hexdigest()))
    return publish_native_text_source_evidence(repository=lane.repo,
        domain_contract=lane.domain, semantic_profile=lane.profile,
        request=NativeTextSourceAdmissionV1(space_id="world:test", admission_id=name,
            expected_parent_revision_id=lane.repo.get_head("world:test").head_revision_id,
            created_at=NOW, body_text=body, expected_body_sha256=sha256(raw).hexdigest(),
            source_classification="dungeonbuddy.source:session_recap", authority="primary",
            visibility={"kind": "labels_any", "labels": [GM_LABEL]},
            origin={"namespace": "test.source", "object_id": name, "revision_id": "1"},
            spans=spans))


def capture(lane, **options):
    return capture_native_sources(managed_world_id="managed", principal=GM,
        repository=lane.repo, resolve_identity=lambda _: lane.bound, **options)


def test_provisioned_source_only_admission_discovers_full_body_without_assertions(lane):
    receipt = admit(lane)
    before = lane.repo.get_head("world:test")
    result = capture(lane)
    assert lane.repo.get_head("world:test") == before
    assert result.authority.provisioning_id == lane.bound.provisioning_id
    assert result.authority.revision_id == receipt.published_revision_id
    assert result.unavailable_source_count == 0
    (member,) = result.members
    assert member.campaign_scope == member.session_scope == "unestablished"
    assert result.bodies[(member.artifact.source_artifact_id, member.revision.source_revision_id)] == BODY
    # Body inspection beyond the original evidence interval is deliberate. It
    # must not create a new evidence span or claim that an assertion was read.
    assert member.access_end_byte < len(BODY.encode())
    snapshot = lane.repo.get_revision("world:test", receipt.published_revision_id)
    payload = snapshot.graph_payload
    assert not payload.get("assertions")
    assert lane.repo.get_native_source_admission_receipt("world:test", "first") == receipt


def test_old_revision_excludes_later_source_despite_current_source_epoch(lane):
    first = admit(lane)
    second = admit(lane, "second", body="# Later\n\nA different source.\n")
    old = capture(lane, revision_id=first.published_revision_id)
    current = capture(lane, revision_id=second.published_revision_id)
    assert len(old.members) == 1
    assert len(current.members) == 2
    assert old.authority.acquisition_epoch == current.authority.acquisition_epoch
    assert old.members[0].proof_epoch < old.authority.acquisition_epoch
    assert {m.artifact.source_artifact_id for m in old.members} == {first.source_artifact_id}


def test_multiple_evidence_intervals_deduplicate_source_pair(lane):
    admit(lane, multiple=True)
    result = capture(lane)
    assert len(result.members) == len(result.bodies) == 1
    assert result.unavailable_source_count == 0


@pytest.mark.parametrize("principal", [None, SimpleNamespace(role="player")])
def test_player_refuses_before_identity_or_repository_io(principal):
    def forbidden(*_):
        pytest.fail("Source ownership must not be read for unauthorized audience")
    with pytest.raises(ValueError, match="GM authority"):
        capture_native_sources(managed_world_id="managed", principal=principal,
            repository=object(), resolve_identity=forbidden)


def test_wrong_managed_identity_refuses_before_native_io(lane):
    with pytest.raises(ValueError, match="ownership differs"):
        capture_native_sources(managed_world_id="different", principal=GM,
            repository=object(), resolve_identity=lambda _: lane.bound)


def test_missing_head_is_unavailable_not_complete_empty_inventory(lane):
    lane.bound.native_world_id = "world:missing"
    with pytest.raises(ValueError, match="no head"):
        capture(lane)


def test_wrong_revision_refuses_instead_of_using_current_head(lane):
    admit(lane)
    with pytest.raises(ValueError, match="missing"):
        capture(lane, revision_id="rev:not-this-world")


def test_binding_change_during_capture_refuses(lane):
    admit(lane)
    count = 0
    def changing(_):
        nonlocal count
        count += 1
        return lane.bound if count == 1 else SimpleNamespace(**(vars(lane.bound) | {"binding_version": 2}))
    with pytest.raises(ValueError, match="ownership changed"):
        capture_native_sources(managed_world_id="managed", principal=GM,
            repository=lane.repo, resolve_identity=changing)


def test_corrupt_source_body_refuses_at_core_boundary(lane):
    receipt = admit(lane)
    key = ("world:test", receipt.source_revision_id)
    # Corrupt the actual in-memory persistence adapter, not an invented tool DTO.
    record = lane.repo._by_revision[key]
    corrupt = replace(record, body=b"corrupt")
    lane.repo._by_revision[key] = corrupt
    lane.repo._native_records[("world:test", receipt.source_artifact_id)] = corrupt
    for binding in receipt.bindings:
        span_key = ("world:test", binding.span_id)
        _, proof = lane.repo._by_span[span_key]
        lane.repo._by_span[span_key] = (corrupt, proof)
    from dungeonmind.application.vnext.errors import NativeTextSourceAccessIntegrityError
    with pytest.raises(NativeTextSourceAccessIntegrityError, match="integrity"):
        capture(lane)


def test_preparation_does_not_open_body_before_search_authorization(lane, monkeypatch):
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source as owner
    admit(lane)
    original = owner.open_admitted_native_text
    def forbidden(*_):
        pytest.fail("Body acquisition preceded the selected source search")
    monkeypatch.setattr(owner, "open_admitted_native_text", forbidden)
    prepared = owner.prepare_native_source_context(managed_world_id="managed", principal=GM,
        repository=lane.repo, resolve_identity=lambda _: lane.bound)
    monkeypatch.setattr(owner, "open_admitted_native_text", original)
    result = capture(lane, prepared=prepared)
    assert result.authority == prepared.authority
    assert len(result.members) == 1


def test_captured_provenance_cannot_be_mutated_through_core_models(lane):
    admit(lane)
    member = capture(lane).members[0]
    before = member.model_dump_json()
    exposed = member.artifact
    exposed.source_classification = "dungeonbuddy.source:worldbuilding"
    exposed.foreign_refs.append("injected:reference")
    exposed.visibility.labels.append("injected:audience")
    member.revision.content_sha256 = "0" * 64
    assert member.model_dump_json() == before
    assert member.artifact.source_classification == "dungeonbuddy.source:session_recap"
    assert "injected:reference" not in member.artifact.foreign_refs
    member.verify_body(BODY)


@pytest.mark.parametrize("body", [
    "# One\r\n\r\nÉphanna waited.\r\n\r\n## Two\r\nThe party reunited.\r\n",
    "Introduction\n\nHeading\n=======\n\n```md\n# Not a heading\n```\n\n## End\nLast line",
    "A source without headings.\nIts second line.\n",
])
def test_native_catalog_exact_utf8_crlf_and_existing_markdown_selectors(lane, body):
    from application_state.agent_conversation.native_corpus import (
        build_native_body_catalog, select_native_body_excerpt,
    )
    admit(lane, body=body)
    captured = capture(lane)
    catalog = build_native_body_catalog(captured.authority, captured.members[0], body)
    excerpts = [select_native_body_excerpt(catalog, body, row.section_id) for row in catalog.sections]
    assert "".join(row.text for row in excerpts) == body
    for excerpt in excerpts:
        section = excerpt.section
        assert body.encode()[section.byte_start:section.byte_end].decode() == excerpt.text
        assert "".join(body.splitlines(keepends=True)[section.line_start-1:section.line_end]) == excerpt.text
    assert "app_source_revision_id" not in catalog.model_dump()
    assert "assertion_id" not in catalog.model_dump()


def test_selected_body_excerpt_outside_original_evidence_interval_is_distinct(lane):
    from application_state.agent_conversation.native_corpus import (
        build_native_body_catalog, select_native_body_excerpt,
    )
    body = "# Opening\n\nOriginal interval is only this heading.\n\n# Later\n\nThe party reunited.\n"
    admit(lane, body=body)
    captured = capture(lane)
    member = captured.members[0]
    catalog = build_native_body_catalog(captured.authority, member, body)
    section = catalog.sections[-1]
    assert section.byte_start > member.access_end_byte
    excerpt = select_native_body_excerpt(catalog, body, section.section_id)
    assert "The party reunited" in excerpt.text
    assert excerpt.schema_version == "dmb_native_body_excerpt_v1"
    assert member.access_end_byte == catalog.source.access_end_byte


def test_forged_catalog_boundaries_cannot_select_different_body_text(lane):
    from application_state.agent_conversation.native_corpus import (
        NativeCorpusCatalogV1, build_native_body_catalog, select_native_body_excerpt,
    )
    from application_state.agent_conversation.native_statement_input import canonical
    body = "# One\n\nFirst.\n\n# Two\n\nSecond.\n"
    admit(lane, body=body)
    captured = capture(lane)
    catalog = build_native_body_catalog(captured.authority, captured.members[0], body)
    changed = catalog.model_dump(mode="json", exclude={"catalog_sha256"})
    # Preserve continuity and recompute an apparently valid catalog digest while
    # moving a character across the actual Markdown boundary.
    changed["sections"][0]["char_end"] += 1
    changed["sections"][0]["byte_end"] += 1
    changed["sections"][1]["char_start"] += 1
    changed["sections"][1]["byte_start"] += 1
    forged = NativeCorpusCatalogV1.model_validate(changed | {
        "catalog_sha256": sha256(canonical(changed).encode()).hexdigest()})
    with pytest.raises(ValueError, match="catalog differs"):
        select_native_body_excerpt(forged, body, forged.sections[0].section_id)


def test_changed_body_and_unknown_section_refuse(lane):
    from application_state.agent_conversation.native_corpus import (
        build_native_body_catalog, select_native_body_excerpt,
    )
    admit(lane)
    captured = capture(lane)
    catalog = build_native_body_catalog(captured.authority, captured.members[0], BODY)
    with pytest.raises(ValueError, match="source revision"):
        select_native_body_excerpt(catalog, BODY + "changed", catalog.sections[0].section_id)
    with pytest.raises(ValueError, match="not in its catalog"):
        select_native_body_excerpt(catalog, BODY, "f" * 64)
