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
    first = raw.index(b"\n\n") + 2
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
