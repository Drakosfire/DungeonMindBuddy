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
