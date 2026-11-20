"""Human source selectors, not source authority or answer-acquisition receipts."""

from apps.live_control_server.models.native_graph_inspection import (
    Closed,
    InspectionPin,
    Text,
)


class NativeSourceRead(Closed):
    scope: InspectionPin
    source_artifact_id: Text
    source_revision_id: Text
    evidence_ref_id: Text


class PublishedRecapRead(Closed):
    managed_world_id: Text
    campaign_id: Text
    session_id: Text


class PublishedRecapObjectsRead(PublishedRecapRead):
    scope: InspectionPin
    source_artifact_id: Text
    source_revision_id: Text
    entity_id: Text | None = None
