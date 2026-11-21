"""Owner-only media choices for a private release candidate."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from application_state import media
from apps.live_control_server.services.guest_release_media import sanitize_release_image
from apps.live_control_server.services.hosted_native_graph_access import hosted_world_media_owner


def list_media(*, world_id: str, before: tuple[datetime, UUID] | None = None) -> dict:
    """Return a bounded page of World-owned image identities, never receipts."""
    rows = media.list_assets(hosted_world_media_owner(world_id), limit=31, before=before)
    page = rows[:30]
    cursor = None
    if len(rows) > 30:
        last = page[-1]
        cursor = {"before_time": last["created_at"].isoformat(), "before_id": str(last["asset_id"])}
    return {"assets": [{"id": str(row["asset_id"]), "width": row["width"], "height": row["height"],
                       "created_at": row["created_at"].isoformat()} for row in page], "next": cursor}


def preview_media(*, world_id: str, asset_id: UUID) -> tuple[str, bytes]:
    """Return sanitized bytes from the exact World-owned staged original."""
    content = media.read_staged_bytes(asset_id, hosted_world_media_owner(world_id))
    return sanitize_release_image(content)
