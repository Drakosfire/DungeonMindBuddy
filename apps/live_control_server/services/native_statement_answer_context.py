"""Trusted native statement/source composition at one immutable read revision."""

from fastapi.encoders import jsonable_encoder
from dungeonmind.application.vnext import EntityReadService, open_admitted_native_text
from application_state.agent_conversation.native_statement_input import (
    NativeStatementFrameV1,
)
from . import source_statements as statements


def authority(ref, kind):
    return {
        "authority_id": getattr(ref, kind + "_id"),
        "revision": getattr(ref, kind + "_revision"),
        "descriptor_sha256": ref.descriptor_sha256,
    }


def header(snapshot):
    r = snapshot.revision
    return {
        "space_id": r.space_id,
        "revision_id": r.revision_id,
        "parent_revision_id": r.parent_revision_id,
        "domain_ref": authority(r.domain_contract_ref, "domain"),
        "profile_ref": authority(r.semantic_profile_ref, "profile"),
        "graph_sha256": snapshot.graph_payload_sha256,
    }


def build_frame(selection, principal):
    if principal is None or principal.role not in {"gm", "player"}:
        raise ValueError("Authenticated native principal required")
    bound = statements.native.binding(selection.managed_world_id)
    repo = statements.native.repository()
    space = bound["native_world_id"]
    snapshot = repo.get_revision(space, selection.revision_id)
    if snapshot is None:
        raise ValueError("Selected immutable native revision is unavailable")
    h = header(snapshot)
    if (
        h["domain_ref"] != selection.domain_ref
        or h["profile_ref"] != selection.profile_ref
    ):
        raise ValueError("Native authority reference differs from selection")
    pinned = statements._context(
        repo, space, selection.revision_id, selection.campaign_id, principal.role
    )
    subject = EntityReadService().get_complete_entity(pinned[0], selection.subject_id)
    if not subject.found or not subject.assertions:
        raise ValueError("Selected native subject is unavailable in this scope")
    read = statements.read_subject(
        managed_world_id=selection.managed_world_id,
        campaign_id=selection.campaign_id,
        revision_id=selection.revision_id,
        entity_id=selection.subject_id,
        principal=principal,
    )
    gaps = list(read["gap_codes"])
    supports = []
    for bundle in read["statements"]:
        try:
            original = statements._recover(repo, space, bundle["payload"])
            if (
                original is None
                or original["bundle"]["statement_id"] != bundle["statement_id"]
            ):
                raise ValueError("Original qualified statement publication unavailable")
            child = original["receipt"]["published_revision_id"]
            ancestry, seen, cursor = [], set(), selection.revision_id
            while cursor is not None:
                if cursor in seen:
                    raise ValueError("Native correspondence ancestry cycles")
                seen.add(cursor)
                node = repo.get_revision(space, cursor)
                if node is None:
                    raise ValueError("Native correspondence ancestry unavailable")
                row = header(node)
                ancestry.append(row)
                if cursor == child:
                    if (
                        row["parent_revision_id"]
                        != original["receipt"]["expected_parent_revision_id"]
                        or row["graph_sha256"]
                        != original["receipt"]["graph_payload_sha256"]
                    ):
                        raise ValueError("Native original receipt/header differs")
                    break
                cursor = row["parent_revision_id"]
            else:
                raise ValueError("Read revision is not descended from publication")
            payload = bundle["payload"]
            opened = open_admitted_native_text(
                pinned[1], payload["proof"]["evidence_ref_id"]
            )
            if opened.status != "available":
                raise ValueError("Exact admitted source unavailable")
            clause = payload["clause"]
            supports.append(
                {
                    "statement_id": bundle["statement_id"],
                    "payload": payload,
                    "semantic_digest": bundle["semantic_digest"],
                    "assertion_ids": bundle["assertion_ids"],
                    "publication_receipt": original["receipt"],
                    "result_mappings": original["bindings"],
                    "ancestry": ancestry,
                    "source_artifact_id": opened.source_artifact_id,
                    "source_revision_id": opened.source_revision_id,
                    "source_body_sha256": opened.body_sha256,
                    "clause_start_byte": clause["start_byte"],
                    "clause_end_byte": clause["end_byte"],
                    "clause_sha256": clause["clause_sha256"],
                    "clause_text": payload["quote"],
                }
            )
        except (ValueError, TypeError, KeyError, AttributeError):
            gaps.append("statement_correspondence_unavailable")
    if statements.native.binding(selection.managed_world_id) != bound:
        raise ValueError("Native binding changed during context composition")
    return NativeStatementFrameV1.model_validate(
        jsonable_encoder(
            {
                "managed_world_id": selection.managed_world_id,
                "native_world_id": space,
                "binding_version": bound["binding_version"],
                "campaign_id": selection.campaign_id,
                "role": principal.role,
                "revision_id": selection.revision_id,
                "domain_ref": h["domain_ref"],
                "profile_ref": h["profile_ref"],
                "subject_id": selection.subject_id,
                "status": "partial"
                if gaps
                else "complete"
                if supports
                else "no_visible_statements",
                "gap_codes": sorted(set(gaps)),
                "supports": supports,
            }
        )
    )
