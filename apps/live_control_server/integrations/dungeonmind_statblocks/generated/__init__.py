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
    "sha256:df46327f24180150aadd28a8fe6477ceabde40c300b64c931b27e639a762f36a"
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
