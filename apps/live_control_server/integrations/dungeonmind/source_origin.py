"""Metadata-only native source provenance for future section-read admission.

This is not a read grant. The APP owner must bind its donor to the actual stored
turn/attempt and persist authorization before any source body is loaded.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from uuid import UUID

from application_state.agent_conversation.types import (
    GraphSourceScopeAnchorV2, ValidatedGraphOperationEventV3,
)
from dungeonmind.contracts.evidence import SourceArtifactV2, SourceDomain, SourceStatus
from dungeonmind.contracts.projection_v2 import WorldGraphProjectionRequestV2
from dungeonmind.domain.canonical import canonical_json, canonical_sha256

from .world_graph_reads import DirectWorldGraphReadServices, _dnd_anchor_id


class SourceOriginUnavailable(ValueError):
    """The exact source chain cannot be established; no body may be read."""


@dataclass(frozen=True)
class NativeSourceOrigin:
    donor_event_id: UUID | None
    source_artifact_id: str
    native_source_revision_id: str
    content_sha256: str
    # Canonical JSON retains structured metadata without mutable nested objects.
    proof_json: str

    @property
    def proof_sha256(self) -> str:
        return canonical_sha256(json.loads(self.proof_json))


def verify_native_source_origin(
    services: DirectWorldGraphReadServices,
    *,
    projection: WorldGraphProjectionRequestV2,
    donor: ValidatedGraphOperationEventV3,
    pin: GraphSourceScopeAnchorV2,
) -> NativeSourceOrigin:
    """Re-project an exact donor; never open a locator, source body or latest text.

    Arguments belong to the trusted producer, not an API/model request. This
    function does not prove ledger membership or managed-World authentication.
    Those mandatory checks belong to the later APP admission owner.
    """
    if (not isinstance(donor, ValidatedGraphOperationEventV3)
            or not projection.revision_pin
            or donor.graph_revision != projection.revision_pin
            or services.binding.world_id != projection.world_id
            or pin not in donor.returned_source_pins
            or pin.evidence_ref_id not in donor.evidence_ref_ids):
        raise SourceOriginUnavailable("Source donor differs from frozen Graph scope")
    try:
        resolution = services.retrieval.resolve_source_anchor(
            projection, anchor_id=_dnd_anchor_id(pin.anchor_id))
        snapshot, anchor = resolution.snapshot, resolution.anchor
        if (not resolution.found or anchor is None or not anchor.can_open_source
                or resolution.anchor_id != _dnd_anchor_id(pin.anchor_id)
                or anchor.anchor_id != resolution.anchor_id
                or snapshot.world_id != projection.world_id
                or snapshot.campaign_id != projection.campaign_id
                or snapshot.focus != projection.focus
                or snapshot.scope_mode != projection.scope_mode
                or snapshot.admissibility != projection.admissibility
                or snapshot.revision_id != projection.revision_pin
                or anchor.evidence_ref_id != pin.evidence_ref_id
                or anchor.source_artifact_id != pin.source_artifact_id
                or anchor.source_revision_id != pin.source_revision_id):
            raise SourceOriginUnavailable("Native source resolution differs from donor")
        artifact = anchor.artifact
        if (not isinstance(artifact, SourceArtifactV2)
                or artifact.source_artifact_id != pin.source_artifact_id
                or artifact.world_id != projection.world_id
                or artifact.status != SourceStatus.ACTIVE
                or artifact.visibility is None
                or artifact.source_domain not in {SourceDomain.WORLDBUILDING, SourceDomain.SESSION_RECAP}):
            raise SourceOriginUnavailable("Native source artifact is unavailable")
        revision = services.bundle.sources.get_revision(pin.source_revision_id)
        if (revision is None
                or revision.source_revision_id != pin.source_revision_id
                or revision.source_artifact_id != pin.source_artifact_id
                or not re.fullmatch(r"[0-9a-f]{64}", revision.content_sha256)):
            raise SourceOriginUnavailable("Native source revision is unavailable")
        proof = {
            "schema": "dmb_native_source_origin_proof_v1",
            "projection": projection.model_dump(mode="json"),
            "donor": donor.model_dump(mode="json"),
            "donor_sha256": canonical_sha256(donor.model_dump(mode="json")),
            "pin": pin.model_dump(mode="json"),
            "resolution": {
                "snapshot": snapshot.model_dump(mode="json"),
                "anchor_id": anchor.anchor_id,
                "evidence_ref_id": anchor.evidence_ref_id,
                "source_artifact_id": anchor.source_artifact_id,
                "source_revision_id": anchor.source_revision_id,
                "locator_identity": anchor.locator_identity,
                "source_span_ref_id": anchor.source_span_ref_id,
                "can_open_source": anchor.can_open_source,
                "can_highlight_span": anchor.can_highlight_span,
                "supporting_object_ids": list(anchor.supporting_object_ids),
                "supporting_relationship_ids": list(anchor.supporting_relationship_ids),
                "supporting_assertion_ids": list(anchor.supporting_assertion_ids),
                "evidence": anchor.evidence.model_dump(mode="json"),
                "artifact": artifact.model_dump(mode="json"),
            },
            "revision": revision.model_dump(mode="json"),
        }
        return NativeSourceOrigin(donor.event_id, pin.source_artifact_id,
                                  pin.source_revision_id, revision.content_sha256,
                                  canonical_json(proof))
    except SourceOriginUnavailable:
        raise
    except Exception as exc:
        raise SourceOriginUnavailable("Native source provenance unavailable") from exc
