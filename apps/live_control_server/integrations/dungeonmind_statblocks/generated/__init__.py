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
    "sha256:fbe8bd42144e742e6b6274dd5d111ac009c43fc67c1a8a6c76ccac78498378b3"
)

__all__ = [
    "OPENAPI_FINGERPRINT",
    "GeneratedStatblockCandidateV1",
    "GenerationReceiptV1",
    "ValidationReceiptV1",
]
