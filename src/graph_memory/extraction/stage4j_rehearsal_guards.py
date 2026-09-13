"""Fail-closed guards for Stage 4J isolated World rehearsal publication."""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import unquote, urlparse

LIVE_WORLD_AUTHORITY_PORT = 54330
LIVE_WORLD_DB_NAME = "dungeonmind_cutover_live"
REHEARSAL_DB_NAME_HINT = "dungeonmind_stage4j_rehearsal"
ALLOW_LIVE_WORLD_ENV = "DMB_STAGE4J_ALLOW_LIVE_WORLD"
WORLD_DSN_ENV = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"


class Stage4JRehearsalGuardError(RuntimeError):
    """Raised when a Stage 4J rehearsal action targets live Eldyrwild authority."""


def assert_rehearsal_world_db_url(url: str) -> None:
    """Refuse live Eldyrwild World authority; require rehearsal DSN.

    Fail closed when the URL looks like live cutover authority:
    - host port ``54330``
    - database name ``dungeonmind_cutover_live``
    - database name contains ``cutover_live``

    Override only when ``DMB_STAGE4J_ALLOW_LIVE_WORLD=1`` (explicit operator ack).
    """
    cleaned = (url or "").strip()
    if not cleaned:
        raise Stage4JRehearsalGuardError(
            f"{WORLD_DSN_ENV} is empty; point it at an isolated rehearsal database "
            f"(for example postgresql://dungeonmind@127.0.0.1:54329/{REHEARSAL_DB_NAME_HINT})"
        )

    parsed = urlparse(cleaned)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise Stage4JRehearsalGuardError(
            f"refusing non-postgresql world DSN scheme {parsed.scheme!r}"
        )

    db_name = _database_name_from_url(parsed)
    host = (parsed.hostname or "").lower()
    port = parsed.port
    live_fingerprints: list[str] = []

    if port == LIVE_WORLD_AUTHORITY_PORT:
        live_fingerprints.append(f"port:{LIVE_WORLD_AUTHORITY_PORT}")
    if ":54330" in cleaned:
        live_fingerprints.append("literal:54330")
    if db_name == LIVE_WORLD_DB_NAME:
        live_fingerprints.append(f"db:{LIVE_WORLD_DB_NAME}")
    if "cutover_live" in db_name.lower():
        live_fingerprints.append("db:cutover_live")

    allow_live = os.environ.get(ALLOW_LIVE_WORLD_ENV, "").strip() == "1"
    if live_fingerprints and not allow_live:
        raise Stage4JRehearsalGuardError(
            "refusing live Eldyrwild World authority for Stage 4J rehearsal "
            f"({', '.join(live_fingerprints)} on host={host!r} db={db_name!r}); "
            f"set {ALLOW_LIVE_WORLD_ENV}=1 only for explicit operator override"
        )


def rehearsal_world_database_url() -> str:
    """Return configured world DSN after rehearsal guard checks."""
    url = os.environ.get(WORLD_DSN_ENV, "").strip()
    assert_rehearsal_world_db_url(url)
    return url


def _database_name_from_url(parsed: Any) -> str:
    path = unquote(parsed.path or "").lstrip("/")
    return (path.split("/")[0] if path else "").strip()


__all__ = [
    "ALLOW_LIVE_WORLD_ENV",
    "LIVE_WORLD_AUTHORITY_PORT",
    "LIVE_WORLD_DB_NAME",
    "REHEARSAL_DB_NAME_HINT",
    "Stage4JRehearsalGuardError",
    "WORLD_DSN_ENV",
    "assert_rehearsal_world_db_url",
    "rehearsal_world_database_url",
]
