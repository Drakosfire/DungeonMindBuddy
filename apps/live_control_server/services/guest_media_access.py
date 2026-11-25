"""Session-bound allocation controls for guest-created private artwork."""
from contextlib import contextmanager

from fastapi import HTTPException

from application_state.engine import connect
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.services.guest_build_access import _lock_guest_session, require_guest_build_world
from apps.live_control_server.services.hosted_native_graph_access import hosted_world_media_owner

MAX_GUEST_ASSETS = 4
MAX_GUEST_ASSET_BYTES = 20 * 1024 * 1024


@contextmanager
def guest_generation_lease(request, world_id):
    """Allow one in-flight generation per session across all server workers."""
    require_guest_build_world(request, world_id)
    with connect() as conn:
        conn.autocommit = True
        key = "guest-image:" + world_id
        acquired = conn.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (key,)).fetchone()[0]
        if not acquired:
            raise HTTPException(409, detail="An image is already being generated for this guest World.")
        try:
            count, total = conn.execute("SELECT count(*), coalesce(sum(byte_length), 0) FROM media.asset WHERE owner_id = %s", (hosted_world_media_owner(world_id),)).fetchone()
            if count >= MAX_GUEST_ASSETS or total >= MAX_GUEST_ASSET_BYTES:
                raise HTTPException(409, detail="This guest World has reached its image limit.")
            yield
        finally:
            conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (key,))


def authorize_guest_image_stage(request, conn, owner, content_bytes):
    world_id = getattr(request.state, "guest_build_world", None)
    if not world_id or owner != hosted_world_media_owner(world_id):
        raise ApplicationStateConflictError("Guest image World does not match the session")
    _lock_guest_session(request, conn, world_id)
    count, total = conn.execute("SELECT count(*), coalesce(sum(byte_length), 0) FROM media.asset WHERE owner_id = %s", (owner,)).fetchone()
    if count >= MAX_GUEST_ASSETS or total + content_bytes > MAX_GUEST_ASSET_BYTES:
        raise ApplicationStateConflictError("This guest World has reached its image limit")
