"""OpenAPI-generated DungeonMind statblock v1 DTOs.

Source fingerprint must match apps/live-control-ui vendored client and
DungeonMindServer openapi/dungeonbuddy-statblocks-v1.json.
"""

from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import (
    CreateStatblockRequestV1,
    CreateStatblockResponseV1,
    GeneratedStatblockCandidateV1,
    GenerationReceiptV1,
    ReviseCandidateRequestV1,
    StatblockDefinitionV1Input,
    ValidateDefinitionRequestV1,
    ValidationReceiptV1,
    ValidationResponseV1,
)

OPENAPI_FINGERPRINT = (
    "sha256:770cb3ae5e72b0997b3b9a99462bc64f53a632a94aa2bc21dffa6bc7297662fe"
)

__all__ = [
    "OPENAPI_FINGERPRINT",
    "CreateStatblockRequestV1",
    "CreateStatblockResponseV1",
    "GeneratedStatblockCandidateV1",
    "GenerationReceiptV1",
    "ReviseCandidateRequestV1",
    "StatblockDefinitionV1Input",
    "ValidateDefinitionRequestV1",
    "ValidationReceiptV1",
    "ValidationResponseV1",
]
