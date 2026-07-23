"""OpenAPI-generated DungeonMind statblock v1 DTOs.

Source fingerprint must match apps/live-control-ui vendored client and
DungeonMindServer openapi/dungeonbuddy-statblocks-v1.json.
"""

from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import (
    GeneratedStatblockCandidateV1,
    GenerationReceiptV1,
    ValidationReceiptV1,
)

OPENAPI_FINGERPRINT = (
    "sha256:75bef3f4d3cffa30532e557fb822fe1d0cb3877a9a46d5b83ff637f3078cd748"
)

__all__ = [
    "OPENAPI_FINGERPRINT",
    "GeneratedStatblockCandidateV1",
    "GenerationReceiptV1",
    "ValidationReceiptV1",
]
