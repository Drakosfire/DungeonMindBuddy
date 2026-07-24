"""OpenAPI-generated DungeonMind statblock v1 DTOs.

Source fingerprint must match apps/live-control-ui vendored client and
DungeonMindServer openapi/dungeonbuddy-statblocks-v1.json.
"""

from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import (
    GeneratedStatblockCandidateV1,
    GenerationReceiptV1,
    StatblockDefinitionV1Input,
    ValidateDefinitionRequestV1,
    ValidationReceiptV1,
    ValidationResponseV1,
)

OPENAPI_FINGERPRINT = (
    "sha256:d51883b9495f8f42db88abdcb7d5290ca3790519eaf63c6350dbe91c3122a09c"
)

__all__ = [
    "OPENAPI_FINGERPRINT",
    "GeneratedStatblockCandidateV1",
    "GenerationReceiptV1",
    "StatblockDefinitionV1Input",
    "ValidateDefinitionRequestV1",
    "ValidationReceiptV1",
    "ValidationResponseV1",
]
