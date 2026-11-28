"""Publication-owned JPEG snapshots, separate from reusable PDF reviews."""

from base64 import b64decode
from binascii import Error
from uuid import UUID

from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from application_state.unit_of_work import unit_of_work

from .purge import require_available_statblocks
from .service import _dsn

_MAX_BYTES = 16 * 1024 * 1024


def _read(conn, key) -> bytes | None:
    row = conn.execute(
        """SELECT jpeg FROM mechanics_revision.pdf_portrait
           WHERE statblock_id=%s AND world_id=%s AND draft_id=%s AND review_id=%s""",
        key,
    ).fetchone()
    return None if row is None else bytes(row[0])


def retain(*, statblock_id: str, world_id: str, draft_id: UUID, review_id: UUID, artwork: str) -> None:
    if len(artwork) > 4 * ((_MAX_BYTES + 2) // 3):
        raise ApplicationStateValidationError("Saved statblock portrait is too large")
    try:
        jpeg = b64decode(artwork, validate=True)
    except (Error, ValueError) as exc:
        raise ApplicationStateValidationError("Saved statblock portrait is invalid") from exc
    if len(jpeg) > _MAX_BYTES or not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
        raise ApplicationStateValidationError("Saved statblock portrait is invalid")
    key = (statblock_id, world_id, draft_id, review_id)
    with unit_of_work(_dsn()) as conn:
        require_available_statblocks(conn, (statblock_id,))
        conn.execute(
            """INSERT INTO mechanics_revision.pdf_portrait
               (statblock_id, world_id, draft_id, review_id, jpeg) VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT DO NOTHING""",
            (*key, jpeg),
        )
        if _read(conn, key) != jpeg:
            raise ApplicationStateConflictError("Existing statblock portrait differs from this publication")


def read(*, statblock_id: str, world_id: str, draft_id: UUID, review_id: UUID) -> bytes | None:
    with unit_of_work(_dsn()) as conn:
        return _read(conn, (statblock_id, world_id, draft_id, review_id))
