"""Trusted, read-only native corpus composition through existing Core access."""
from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from collections.abc import Callable, Mapping
from typing import Any

from dungeonmind.application.vnext import (
    open_admitted_native_text,
    open_native_text_source_access_context,
    refresh_native_text_source_access_context,
)
from application_state.agent_conversation.native_statement_input import canonical
from application_state.agent_conversation.native_corpus import (
    NativeCorpusAuthorityV1,
    NativeCorpusMemberV1,
)
from graph_memory.vnext.domain_runtime import GM_LABEL, PLAYER_LABEL
from . import native_registry_source as native


@dataclass(frozen=True)
class NativeCorpusContext:
    """Host-only coherent access; opening it does not acquire source bodies."""
    authority: NativeCorpusAuthorityV1
    binding: Any
    access: Any
    resolve_identity: Callable
    principal: Any
    repository: Any


@dataclass(frozen=True)
class NativeCorpusCapture:
    authority: NativeCorpusAuthorityV1
    members: tuple[NativeCorpusMemberV1, ...]
    bodies: Mapping[tuple[str, str], str]
    unavailable_source_count: int


def _ref(ref, family):
    return {"authority_id": getattr(ref, family + "_id"),
            "revision": getattr(ref, family + "_revision"),
            "descriptor_sha256": ref.descriptor_sha256}


def prepare_native_source_context(*, managed_world_id, principal, revision_id=None,
                                  repository=None, resolve_identity=None):
    """Freeze membership in R and one coherent acquisition epoch, never latest IDs.

    Dependencies are trusted host/test seams. No request supplies a repository,
    binding record, provider data or body. Source ownership does not grant Graph
    authority. Missing heads and integrity failures propagate as unavailable;
    callers must not turn them into apparently complete empty membership.
    """
    if principal is None or principal.role != "gm":
        raise ValueError("GM authority is required for cross-campaign source inspection")
    if resolve_identity is None:
        from ...services.managed_world_graph_projection import resolve_managed_source_identity
        resolve_identity = resolve_managed_source_identity
    bound = resolve_identity(managed_world_id)
    if bound.managed_world_id != managed_world_id:
        raise ValueError("Native source ownership differs from requested World")
    repo = repository if repository is not None else native.repository()
    space = bound.native_world_id
    if revision_id is None:
        head = repo.get_head(space)
        if head is None:
            raise ValueError("Native source authority has no head")
        revision_id = head.head_revision_id
    domain, _profile = native.descriptors(repo, space, revision_id)
    access = open_native_text_source_access_context(repository=repo, space_id=space,
        revision_id=revision_id, domain_contract=domain,
        audience_labels=(GM_LABEL, PLAYER_LABEL))
    authority = NativeCorpusAuthorityV1(managed_world_id=managed_world_id,
        native_world_id=space, binding_version=bound.binding_version,
        provisioning_id=bound.provisioning_id, revision_id=revision_id,
        domain_ref=_ref(access.parsed.domain_contract_ref, "domain"),
        profile_ref=_ref(access.parsed.semantic_profile_ref, "profile"),
        acquisition_epoch=access.source_view.epoch)
    if resolve_identity(managed_world_id) != bound:
        raise ValueError("Native source ownership changed during context preparation")
    return NativeCorpusContext(authority, bound, access, resolve_identity, principal, repo)


def open_native_corpus_member(prepared, evidence_ref_id):
    """Open one exact Core member; shared by selected and corpus-search callers."""
    authority, access = prepared.authority, prepared.access
    evidence = access.parsed.get_evidence(evidence_ref_id)
    if evidence is None or evidence.source_revision_id is None:
        return None
    opened = open_admitted_native_text(access, evidence_ref_id)
    if opened.status != "available":
        return None
    pair = (evidence.source_artifact_id, evidence.source_revision_id)
    snapshot = access.source_view.get_provenance_snapshot(artifact_ids=[pair[0]], revision_ids=[pair[1]])
    artifact, revision = snapshot.get_artifact(pair[0]), snapshot.get_revision(pair[1])
    if artifact is None or revision is None:
        raise ValueError("Authorized native corpus provenance is unavailable")
    member = NativeCorpusMemberV1(artifact_json=canonical(artifact), revision_json=canonical(revision),
        evidence_ref_id=evidence.evidence_ref_id, access_span_id=evidence.source_span_ref_id,
        access_start_byte=opened.span_start_byte, access_end_byte=opened.span_end_byte,
        access_slice_sha256=opened.span_sha256, proof_epoch=opened.source_authority_epoch)
    if ((opened.source_artifact_id, opened.source_revision_id) != pair
            or member.proof_epoch > authority.acquisition_epoch):
        raise ValueError("Native corpus access differs from its coherent selected source")
    member.verify_body(opened.body_text)
    if prepared.resolve_identity(authority.managed_world_id) != prepared.binding:
        raise ValueError("Native source ownership changed during opening")
    return member, opened.body_text


def read_authored_source(prepared, reference):
    """Current human input names an exact original selector; Core admits the read."""
    from dungeonmind.application.vnext import list_admitted_native_text_sources
    from application_state.agent_conversation.native_corpus import (
        build_native_body_catalog, select_native_full_document, select_native_body_excerpt,
    )
    authority = prepared.authority
    if (reference.managed_world_id, reference.native_world_id, reference.binding_version) != (
            authority.managed_world_id, authority.native_world_id, authority.binding_version):
        raise ValueError("Selected source World binding changed; choose it again")
    original = prepare_native_source_context(managed_world_id=authority.managed_world_id,
        principal=prepared.principal, revision_id=reference.knowledge_revision,
        repository=prepared.repository, resolve_identity=prepared.resolve_identity)
    eligible = [row for row in list_admitted_native_text_sources(original.access).sources
        if row.source_artifact.source_artifact_id == reference.source_artifact_id
        and row.source_revision.source_revision_id == reference.source_revision_id
        and row.source_revision.content_sha256 == reference.content_sha256
        and reference.evidence_ref_id in row.evidence_ref_ids]
    if len(eligible) != 1:
        raise ValueError("Selected source is absent from its original revision; choose it again")
    fresh = prepare_native_source_context(managed_world_id=authority.managed_world_id,
        principal=prepared.principal, revision_id=authority.revision_id,
        repository=prepared.repository, resolve_identity=prepared.resolve_identity)
    if fresh.authority.model_dump(exclude={'acquisition_epoch'}) != authority.model_dump(exclude={'acquisition_epoch'}):
        raise ValueError("Selected source authority changed")
    result = open_native_corpus_member(fresh, reference.evidence_ref_id)
    if result is None:
        raise ValueError("The exact selected source is unavailable; no newer source was substituted")
    member, text = result
    if (member.artifact.source_artifact_id, member.revision.source_revision_id,
            member.revision.content_sha256) != (reference.source_artifact_id,
                reference.source_revision_id, reference.content_sha256):
        raise ValueError("Selected source opening returned a different exact version")
    catalog = build_native_body_catalog(authority, member, text)
    excerpt = (select_native_full_document(catalog, text) if reference.selection_kind == 'full_document'
               else select_native_body_excerpt(catalog, text, reference.section_id))
    return catalog, excerpt


def capture_native_sources(*, managed_world_id, principal, revision_id=None,
                           repository=None, resolve_identity=None, prepared=None):
    """Acquire bodies only after the caller has durably authorized source search."""
    if principal is None or principal.role != "gm":
        raise ValueError("GM authority is required for cross-campaign source inspection")
    if prepared is None:
        prepared = prepare_native_source_context(managed_world_id=managed_world_id,
            principal=principal, revision_id=revision_id, repository=repository,
            resolve_identity=resolve_identity)
    authority, access = prepared.authority, prepared.access
    if authority.managed_world_id != managed_world_id:
        raise ValueError("Prepared native source authority differs from requested World")
    if revision_id is not None and authority.revision_id != revision_id:
        raise ValueError("Prepared native source authority differs from requested revision")
    # Include source-only admissions: an assertion supporter is not a condition
    # for source inspection. Unavailable pairs are not exposed as model labels.
    pairs = {}
    for evidence in access.parsed.evidence_by_id.values():
        if (evidence.source_revision_id is not None
                and evidence.source_span_ref_id is not None
                and evidence.can_open_source and evidence.can_highlight_span):
            pairs.setdefault((evidence.source_artifact_id, evidence.source_revision_id), []).append(evidence)
    members, bodies, unavailable = [], {}, 0
    for pair, candidates in sorted(pairs.items()):
        for evidence in sorted(candidates, key=lambda row: row.evidence_ref_id):
            result = open_native_corpus_member(prepared, evidence.evidence_ref_id)
            if result is None:
                continue
            member, text = result
            members.append(member)
            bodies[pair] = text
            break
        else:
            unavailable += 1
    if prepared.resolve_identity(managed_world_id) != prepared.binding:
        raise ValueError("Native source ownership changed during capture")
    return NativeCorpusCapture(authority, tuple(members), MappingProxyType(bodies), unavailable)


def read_native_corpus_member(*, authority, member, principal, prepared):
    """Refresh Core source access while reusing the prepared exact Graph revision."""
    fresh = _refresh_native_context(prepared, authority=authority, principal=principal)
    evidence = fresh.access.parsed.evidence_by_id.get(member.evidence_ref_id)
    if (evidence is None or evidence.source_artifact_id != member.artifact.source_artifact_id
            or evidence.source_revision_id != member.revision.source_revision_id
            or evidence.source_span_ref_id != member.access_span_id):
        raise ValueError("Selected native source member differs from original revision membership")
    opened = open_admitted_native_text(fresh.access, member.evidence_ref_id)
    if fresh.resolve_identity(authority.managed_world_id) != fresh.binding:
        raise ValueError("Native source ownership changed during the selected read")
    if opened.status != "available":
        return None
    if (opened.source_artifact_id != member.artifact.source_artifact_id
            or opened.source_revision_id != member.revision.source_revision_id
            or opened.span_start_byte != member.access_start_byte
            or opened.span_end_byte != member.access_end_byte
            or opened.span_sha256 != member.access_slice_sha256
            or opened.source_authority_epoch > fresh.authority.acquisition_epoch):
        raise ValueError("Selected native source read differs from its original access proof")
    member.verify_body(opened.body_text)
    if fresh.resolve_identity(authority.managed_world_id) != fresh.binding:
        raise ValueError("Native source ownership changed during the selected read")
    return opened.body_text


def _refresh_native_context(prepared, *, authority, principal):
    """One freshness boundary for selected native source reads."""
    if principal is None or principal.role != "gm":
        raise ValueError("GM authority is required for cross-campaign source inspection")
    original = authority.model_dump(mode="json", exclude={"acquisition_epoch"})
    if (prepared.principal != principal
            or prepared.authority.model_dump(mode="json", exclude={"acquisition_epoch"}) != original
            or prepared.resolve_identity(authority.managed_world_id) != prepared.binding):
        raise ValueError("Native source authority changed before the selected read")
    access = refresh_native_text_source_access_context(
        repository=prepared.repository, context=prepared.access)
    if access.source_view.epoch < authority.acquisition_epoch:
        raise ValueError("Native source authority moved backwards before the selected read")
    fresh = replace(prepared, access=access, authority=authority.model_copy(
        update={"acquisition_epoch": access.source_view.epoch}))
    return fresh


def read_direct_native_source(prepared, *, authority, source_artifact_id, source_revision_id, content_sha256):
    """Read one explicit original catalogue choice through refreshed Core access."""
    from dungeonmind.application.vnext import list_admitted_native_text_sources
    from application_state.agent_conversation.native_corpus import build_native_body_catalog, select_native_full_document

    def matches(item):
        return (item.source_artifact.source_artifact_id, item.source_revision.source_revision_id,
                item.source_revision.content_sha256) == (source_artifact_id, source_revision_id, content_sha256)

    fresh = _refresh_native_context(prepared, authority=authority, principal=prepared.principal)
    # The original revision is membership authority. A current source bearing a
    # similar name, or one admitted later, cannot satisfy this selection.
    if not any(matches(item) for item in list_admitted_native_text_sources(prepared.access).sources):
        raise ValueError("Direct source choice is absent from its original admitted catalogue")
    eligible = [item for item in list_admitted_native_text_sources(fresh.access).sources if matches(item)]
    if not eligible:
        return None  # Revoked or unavailable; never substitute a different source.
    for evidence_ref_id in sorted(eligible[0].evidence_ref_ids):
        result = open_native_corpus_member(fresh, evidence_ref_id)
        if result is None:
            continue
        member, body = result
        if (member.artifact.source_artifact_id, member.revision.source_revision_id,
                member.revision.content_sha256) != (source_artifact_id, source_revision_id, content_sha256):
            raise ValueError("Direct source opening changed the exact selected revision")
        catalog = build_native_body_catalog(fresh.authority, member, body)
        return catalog, select_native_full_document(catalog, body)
    return None
