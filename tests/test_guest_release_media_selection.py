from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.live_control_server.services import guest_release_media_selection as selection


def test_media_inventory_pages_without_exposing_receipts(monkeypatch):
    now = datetime(2026, 11, 20, tzinfo=UTC)
    rows = [{"asset_id": uuid4(), "created_at": now - timedelta(seconds=index), "width": 3, "height": 2,
             "receipt": {"delivery_url": "https://private.example"}, "provenance": {"prompt": "secret"}}
            for index in range(31)]
    seen = []
    def list_assets(owner, *, limit, before):
        seen.append((owner, limit, before))
        return rows if before is None else rows[30:]
    monkeypatch.setattr(selection.media, "list_assets", list_assets)
    first = selection.list_media(world_id="world")
    assert len(first["assets"]) == 30 and "private.example" not in str(first) and "secret" not in str(first)
    cursor = first["next"]
    assert cursor == {"before_time": rows[29]["created_at"].isoformat(), "before_id": str(rows[29]["asset_id"])}
    second = selection.list_media(world_id="world", before=(rows[29]["created_at"], rows[29]["asset_id"]))
    assert len(second["assets"]) == 1 and second["next"] is None
    assert seen[0] == ("hosted_world:world", 31, None)
