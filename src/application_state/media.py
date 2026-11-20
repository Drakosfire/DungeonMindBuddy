"""Durable owner-scoped image candidates; network storage is a consumer port."""

from __future__ import annotations

import hashlib
import io
import json
import warnings
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work

_MAX_IMAGE_BYTES = 10_000_000
_MAX_PIXELS = 40_000_000
_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def _uuid(value: str | UUID) -> UUID:
    return UUID(str(value))


def _owner(owner: str) -> str:
    if not isinstance(owner, str) or not owner.strip():
        raise ApplicationStateValidationError(
            "An authenticated media owner is required."
        )
    return owner


def _image_identity(content: bytes) -> dict[str, Any]:
    if not content or len(content) > _MAX_IMAGE_BYTES:
        raise ApplicationStateValidationError(
            "Image must contain at most 10 MB of valid image data."
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                mime = _FORMATS.get(image.format)
                width, height = image.size
                if mime is None or width * height > _MAX_PIXELS:
                    raise ApplicationStateValidationError(
                        "Unsupported image encoding or dimensions."
                    )
                image.verify()
            # verify() checks structure but JPEG may defer pixel decoding.
            with Image.open(io.BytesIO(content)) as image:
                if getattr(image, "is_animated", False):
                    raise ApplicationStateValidationError(
                        "Animated media is not supported by this image writer."
                    )
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ApplicationStateValidationError(
            "The image could not be decoded."
        ) from error
    return {
        "mime_type": mime,
        "width": width,
        "height": height,
        "byte_length": len(content),
        "content_sha256": hashlib.sha256(content).hexdigest(),
    }


def _read(conn, asset_id: UUID, owner: str, *, lock: bool = False) -> dict[str, Any]:
    row = (
        conn.cursor(row_factory=dict_row)
        .execute(
            "SELECT a.*, s.state, s.fence, s.receipt FROM media.asset a JOIN media.storage s USING(asset_id) "
            "WHERE a.asset_id=%s AND a.owner_id=%s"
            + (" FOR UPDATE OF s" if lock else ""),
            (asset_id, _owner(owner)),
        )
        .fetchone()
    )
    if row is None:
        raise ApplicationStateNotFoundError("Media asset not found.")
    return row


def get_asset(
    asset_id: str | UUID, owner: str, *, dsn: str | None = None
) -> dict[str, Any]:
    with unit_of_work(dsn) as conn:
        return _read(conn, _uuid(asset_id), owner)


def stage_image(
    content: bytes,
    owner: str,
    provenance: dict[str, Any],
    *,
    asset_id: str | UUID | None = None,
    dsn: str | None = None,
) -> dict[str, Any]:
    """The caller must stage before acknowledging the generated candidate."""
    owner = _owner(owner)
    identity = _image_identity(content)
    if not isinstance(provenance, dict):
        raise ApplicationStateValidationError("Media provenance must be an object.")
    try:
        encoded = json.dumps(provenance, allow_nan=False, sort_keys=True).encode()
    except (TypeError, ValueError) as error:
        raise ApplicationStateValidationError(
            "Media provenance must be JSON-safe."
        ) from error
    if len(encoded) > 262144:
        raise ApplicationStateValidationError(
            "Media provenance exceeds its storage limit."
        )
    provenance = json.loads(encoded)
    identity["provenance_sha256"] = hashlib.sha256(encoded).hexdigest()
    aid = _uuid(asset_id) if asset_id is not None else uuid4()
    with unit_of_work(dsn) as conn:
        inserted = conn.execute(
            "INSERT INTO media.asset(asset_id,owner_id,mime_type,width,height,byte_length,content_sha256,provenance_sha256,provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (asset_id) DO NOTHING RETURNING asset_id",
            (
                aid,
                owner,
                identity["mime_type"],
                identity["width"],
                identity["height"],
                identity["byte_length"],
                identity["content_sha256"],
                identity["provenance_sha256"],
                Jsonb(provenance),
            ),
        ).fetchone()
        if inserted:
            conn.execute(
                "INSERT INTO media.storage(asset_id,staged_bytes) VALUES (%s,%s)",
                (aid, content),
            )
        row = _read(conn, aid, owner)
        if (
            any(row[key] != value for key, value in identity.items())
            or row["provenance"] != provenance
        ):
            raise ApplicationStateConflictError(
                "This asset identity already describes different content or provenance."
            )
        return row


def read_staged_bytes(
    asset_id: str | UUID, owner: str, *, dsn: str | None = None
) -> bytes:
    with unit_of_work(dsn) as conn:
        row = _read(conn, _uuid(asset_id), owner)
        content = bytes(
            conn.execute(
                "SELECT staged_bytes FROM media.storage WHERE asset_id=%s",
                (_uuid(asset_id),),
            ).fetchone()[0]
        )
        if (
            len(content) != row["byte_length"]
            or hashlib.sha256(content).hexdigest() != row["content_sha256"]
        ):
            raise ApplicationStateIntegrityError(
                "Staged media bytes do not match the asset identity."
            )
        return content


def list_assets(
    owner: str,
    *,
    limit: int = 30,
    before: tuple[datetime, UUID] | None = None,
    dsn: str | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 100:
        raise ApplicationStateValidationError(
            "Media page size must be between 1 and 100."
        )
    params: list[Any] = [_owner(owner)]
    boundary = ""
    if before:
        boundary = " AND (a.created_at,a.asset_id) < (%s,%s)"
        params.extend(before)
    params.append(limit)
    with unit_of_work(dsn) as conn:
        return (
            conn.cursor(row_factory=dict_row)
            .execute(
                "SELECT a.*,s.state,s.fence,s.receipt FROM media.asset a JOIN media.storage s USING(asset_id) "
                "WHERE a.owner_id=%s"
                + boundary
                + " ORDER BY a.created_at DESC,a.asset_id DESC LIMIT %s",
                params,
            )
            .fetchall()
        )


def claim_upload(asset_id: str | UUID, owner: str, *, dsn: str | None = None) -> UUID:
    """Exactly one caller may start an upload. Unknown is never a retryable stage."""
    with unit_of_work(dsn) as conn:
        row = _read(conn, _uuid(asset_id), owner, lock=True)
        if row["state"] != "staged":
            raise ApplicationStateConflictError(
                "Media upload already started; read or reconcile its recorded outcome."
            )
        fence = uuid4()
        conn.execute(
            "UPDATE media.storage SET state='uploading',fence=%s,updated_at=clock_timestamp() WHERE asset_id=%s",
            (fence, _uuid(asset_id)),
        )
        return fence


def mark_upload_unknown(
    asset_id: str | UUID, owner: str, fence: str | UUID, *, dsn: str | None = None
) -> None:
    with unit_of_work(dsn) as conn:
        row = _read(conn, _uuid(asset_id), owner, lock=True)
        if row["fence"] != _uuid(fence) or row["state"] not in {"uploading", "unknown"}:
            raise ApplicationStateConflictError("Media upload fence is stale.")
        conn.execute(
            "UPDATE media.storage SET state='unknown',updated_at=clock_timestamp() WHERE asset_id=%s",
            (_uuid(asset_id),),
        )


def complete_upload(
    asset_id: str | UUID,
    owner: str,
    fence: str | UUID,
    verified_receipt: dict[str, Any],
    *,
    dsn: str | None = None,
) -> dict[str, Any]:
    """Only a trusted storage adapter may supply a verified receipt; never a browser."""
    required = {
        "backend",
        "account_id",
        "object_id",
        "original_sha256",
        "visibility",
        "delivery_url",
        "asset_id",
        "owner_id",
        "provenance_sha256",
    }
    if (
        not isinstance(verified_receipt, dict)
        or not required <= verified_receipt.keys()
    ):
        raise ApplicationStateValidationError("A verified storage receipt is required.")
    if any(
        not isinstance(verified_receipt[k], str) or not verified_receipt[k]
        for k in required
    ):
        raise ApplicationStateValidationError(
            "Storage receipt fields must be nonempty strings."
        )
    if verified_receipt["visibility"] not in {
        "public",
        "private",
    } or not verified_receipt["delivery_url"].startswith("https://"):
        raise ApplicationStateValidationError("Storage delivery receipt is invalid.")
    with unit_of_work(dsn) as conn:
        row = _read(conn, _uuid(asset_id), owner, lock=True)
        if row["fence"] != _uuid(fence):
            raise ApplicationStateConflictError("Media upload fence is stale.")
        if row["state"] == "ready" and row["receipt"] == verified_receipt:
            return row
        if row["state"] not in {"uploading", "unknown"}:
            raise ApplicationStateConflictError(
                "Media is not awaiting this storage result."
            )
        if (
            verified_receipt["original_sha256"] != row["content_sha256"]
            or verified_receipt["asset_id"] != str(row["asset_id"])
            or verified_receipt["owner_id"] != row["owner_id"]
            or verified_receipt["provenance_sha256"] != row["provenance_sha256"]
        ):
            raise ApplicationStateIntegrityError(
                "Storage receipt does not identify the original media bytes."
            )
        conn.execute(
            "UPDATE media.storage SET state='ready',receipt=%s,updated_at=clock_timestamp() WHERE asset_id=%s",
            (Jsonb(verified_receipt), _uuid(asset_id)),
        )
    return get_asset(asset_id, owner, dsn=dsn)


def mark_upload_rejected(
    asset_id: str | UUID, owner: str, fence: str | UUID, *, dsn: str | None = None
) -> None:
    """Trusted adapter only: a definitive rejection accepted no storage write."""
    with unit_of_work(dsn) as conn:
        row = _read(conn, _uuid(asset_id), owner, lock=True)
        if row["fence"] != _uuid(fence) or row["state"] != "uploading":
            raise ApplicationStateConflictError(
                "Media upload fence is stale or its outcome is uncertain."
            )
        conn.execute(
            "UPDATE media.storage SET state='staged',fence=NULL,updated_at=clock_timestamp() WHERE asset_id=%s",
            (_uuid(asset_id),),
        )
