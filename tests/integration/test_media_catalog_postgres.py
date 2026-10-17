"""Disposable PostgreSQL proof of durable image identity and upload fencing."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from PIL import Image
from psycopg import sql

from application_state import media
from application_state.authority import (
    backup_authority,
    compute_fingerprint,
    restore_authority,
)
from application_state.cli import upgrade_to_head
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)


@pytest.fixture(scope="module")
def database():
    admin = "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/postgres"
    name = "buddy_media_test_" + uuid4().hex[:12]
    dsn = admin.rsplit("/", 1)[0] + "/" + name
    previous = os.environ.get("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL")
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        upgrade_to_head(dsn=dsn)
        yield dsn
    finally:
        if previous is None:
            os.environ.pop("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", None)
        else:
            os.environ["DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"] = previous
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (name,),
            )
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def png():
    out = io.BytesIO()
    Image.new("RGB", (3, 2), "green").save(out, format="PNG")
    return out.getvalue()


def receipt(row):
    return dict(
        backend="cloudflare_images",
        account_id="synthetic-account",
        object_id=str(row["asset_id"]),
        delivery_url="https://imagedelivery.net/synthetic/"
        + str(row["asset_id"])
        + "/public",
        original_sha256=row["content_sha256"],
        provenance_sha256=row["provenance_sha256"],
        asset_id=str(row["asset_id"]),
        owner_id=row["owner_id"],
        visibility="public",
    )


def test_durable_stage_owner_isolation_and_idempotency(database):
    content = png()
    row = media.stage_image(
        content,
        "owner-a",
        {"prompt": "Synthetic swamp", "model": "synthetic"},
        dsn=database,
    )
    aid = row["asset_id"]
    assert row["state"] == "staged" and row["width"] == 3 and row["height"] == 2
    assert media.read_staged_bytes(aid, "owner-a", dsn=database) == content
    assert (
        media.get_asset(aid, "owner-a", dsn=database)["provenance"]["prompt"]
        == "Synthetic swamp"
    )
    assert (
        media.stage_image(
            content, "owner-a", row["provenance"], asset_id=aid, dsn=database
        )["asset_id"]
        == aid
    )
    with pytest.raises(ApplicationStateConflictError):
        media.stage_image(
            content, "owner-a", {"prompt": "Different"}, asset_id=aid, dsn=database
        )
    for operation in [media.get_asset, media.read_staged_bytes, media.claim_upload]:
        with pytest.raises(ApplicationStateNotFoundError):
            operation(aid, "other-owner", dsn=database)
    assert not media.list_assets("other-owner", dsn=database)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "from application_state.media import get_asset; import sys; print(get_asset(sys.argv[1], 'owner-a')['state'])",
            str(aid),
        ],
        env=os.environ | {"DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL": database},
        capture_output=True,
        text=True,
        check=True,
    )
    assert child.stdout.strip() == "staged"


def test_one_concurrent_upload_claim_and_unknown_is_not_retryable(database):
    row = media.stage_image(png(), "concurrent-owner", {}, dsn=database)
    aid = row["asset_id"]

    def claim():
        try:
            return media.claim_upload(aid, "concurrent-owner", dsn=database)
        except ApplicationStateConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: claim(), range(2)))
    fence = next(value for value in outcomes if value)
    assert sum(value is not None for value in outcomes) == 1
    with pytest.raises(ApplicationStateConflictError):
        media.mark_upload_unknown(aid, "concurrent-owner", uuid4(), dsn=database)
    media.mark_upload_unknown(aid, "concurrent-owner", fence, dsn=database)
    with pytest.raises(ApplicationStateConflictError):
        media.claim_upload(aid, "concurrent-owner", dsn=database)
    assert media.get_asset(aid, "concurrent-owner", dsn=database)["state"] == "unknown"
    for key in ["original_sha256", "provenance_sha256", "owner_id", "asset_id"]:
        bad = receipt(row) | {key: "incorrect"}
        with pytest.raises(ApplicationStateIntegrityError):
            media.complete_upload(aid, "concurrent-owner", fence, bad, dsn=database)
    ready = media.complete_upload(
        aid, "concurrent-owner", fence, receipt(row), dsn=database
    )
    assert ready["state"] == "ready"
    assert media.complete_upload(
        aid, "concurrent-owner", fence, receipt(row), dsn=database
    )["receipt"] == receipt(row)
    assert media.read_staged_bytes(aid, "concurrent-owner", dsn=database) == png()


def test_corrupt_staging_fails_closed(database):
    row = media.stage_image(png(), "corrupt-owner", {}, dsn=database)
    with psycopg.connect(database) as conn:
        conn.execute(
            "UPDATE media.storage SET staged_bytes=%s WHERE asset_id=%s",
            (b"not an image", row["asset_id"]),
        )
    with pytest.raises(ApplicationStateIntegrityError):
        media.read_staged_bytes(row["asset_id"], "corrupt-owner", dsn=database)


def test_keyset_pagination_handles_tied_timestamps(database):
    for _ in range(4):
        media.stage_image(png(), "page-owner", {}, dsn=database)
    with psycopg.connect(database) as conn:
        conn.execute(
            "UPDATE media.asset SET created_at='2026-10-16T00:00:00Z' WHERE owner_id='page-owner'"
        )
    first = media.list_assets("page-owner", limit=2, dsn=database)
    second = media.list_assets(
        "page-owner",
        limit=2,
        before=(first[-1]["created_at"], first[-1]["asset_id"]),
        dsn=database,
    )
    assert len({row["asset_id"] for row in first + second}) == 4
    assert not media.list_assets(
        "page-owner",
        before=(second[-1]["created_at"], second[-1]["asset_id"]),
        dsn=database,
    )


def test_backup_fingerprint_covers_media_bytes(database):
    row = media.stage_image(png(), "backup-owner", {}, dsn=database)
    before = compute_fingerprint(database)
    domains = {item.name: item for item in before.domains}
    assert domains["media.asset"].row_count > 0
    assert domains["media.storage"].row_count > 0
    with psycopg.connect(database) as conn:
        conn.execute(
            "UPDATE media.storage SET staged_bytes=%s WHERE asset_id=%s",
            (b"changed", row["asset_id"]),
        )
    after = compute_fingerprint(database)
    assert before.digest != after.digest


def test_validation_rejects_nonimages_before_persistence(database):
    with pytest.raises(ApplicationStateValidationError):
        media.stage_image(b"not-image", "validation-owner", {}, dsn=database)
    with pytest.raises(ApplicationStateValidationError):
        media.stage_image(png(), "", {}, dsn=database)


def test_real_backup_restore_keeps_candidate_and_storage_receipt(database, tmp_path):
    row = media.stage_image(
        png(), "restore-owner", {"prompt": "Keep original"}, dsn=database
    )
    fence = media.claim_upload(row["asset_id"], "restore-owner", dsn=database)
    ready = media.complete_upload(
        row["asset_id"], "restore-owner", fence, receipt(row), dsn=database
    )
    dump = tmp_path / "media.dump"
    backup_authority(source_dsn=database, out_path=dump)
    name = "buddy_media_restore_" + uuid4().hex[:12]
    target = database.rsplit("/", 1)[0] + "/" + name
    admin = database.rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        restore_authority(
            target_dsn=target,
            backup_path=dump,
            expect_fingerprint=compute_fingerprint(database),
        )
        assert media.get_asset(row["asset_id"], "restore-owner", dsn=target) == ready
        assert (
            media.read_staged_bytes(row["asset_id"], "restore-owner", dsn=target)
            == png()
        )
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (name,),
            )
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def test_known_rejection_can_retry_same_bytes_but_unknown_cannot(database):
    row = media.stage_image(png(), "rejected-owner", {}, dsn=database)
    first = media.claim_upload(row["asset_id"], "rejected-owner", dsn=database)
    media.mark_upload_rejected(row["asset_id"], "rejected-owner", first, dsn=database)
    second = media.claim_upload(row["asset_id"], "rejected-owner", dsn=database)
    assert second != first
    with pytest.raises(ApplicationStateConflictError):
        media.complete_upload(
            row["asset_id"], "rejected-owner", first, receipt(row), dsn=database
        )
    media.mark_upload_unknown(row["asset_id"], "rejected-owner", second, dsn=database)
    with pytest.raises(ApplicationStateConflictError):
        media.mark_upload_rejected(
            row["asset_id"], "rejected-owner", second, dsn=database
        )
    assert (
        media.read_staged_bytes(row["asset_id"], "rejected-owner", dsn=database)
        == png()
    )
