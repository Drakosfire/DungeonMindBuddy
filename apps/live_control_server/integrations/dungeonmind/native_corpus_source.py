"""Trusted, read-only native corpus composition through existing Core access."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Callable, Mapping
from typing import Any

from dungeonmind.application.vnext import (
    open_admitted_native_text,
    open_native_text_source_access_context,
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
    return NativeCorpusContext(authority, bound, access, resolve_identity)


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
            opened = open_admitted_native_text(access, evidence.evidence_ref_id)
            if opened.status != "available":
                continue
            snapshot = access.source_view.get_provenance_snapshot(
                artifact_ids=[pair[0]], revision_ids=[pair[1]])
            artifact, revision = snapshot.get_artifact(pair[0]), snapshot.get_revision(pair[1])
            if artifact is None or revision is None:
                raise ValueError("Authorized native corpus provenance is unavailable")
            member = NativeCorpusMemberV1(artifact_json=canonical(artifact), revision_json=canonical(revision),
                evidence_ref_id=evidence.evidence_ref_id,
                access_span_id=evidence.source_span_ref_id,
                access_start_byte=opened.span_start_byte,
                access_end_byte=opened.span_end_byte,
                access_slice_sha256=opened.span_sha256,
                proof_epoch=opened.source_authority_epoch)
            if (opened.source_artifact_id, opened.source_revision_id) != pair:
                raise ValueError("Native corpus access returned a different source pair")
            if member.proof_epoch > authority.acquisition_epoch:
                raise ValueError("Native corpus proof postdates its coherent source view")
            member.verify_body(opened.body_text)
            members.append(member)
            bodies[pair] = opened.body_text
            break
        else:
            unavailable += 1
    if prepared.resolve_identity(managed_world_id) != prepared.binding:
        raise ValueError("Native source ownership changed during capture")
    return NativeCorpusCapture(authority, tuple(members), MappingProxyType(bodies), unavailable)
