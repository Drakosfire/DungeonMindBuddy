"""Database-name isolation guards. Never target World Graph / product cutover DBs."""

from __future__ import annotations

from urllib.parse import unquote, urlparse

from application_state.errors import ApplicationStateIsolationError

FORBIDDEN_DATABASE_NAMES = frozenset(
    {
        "postgres",
        "template0",
        "template1",
        "dungeonmind",
        "dungeonmind_cutover_live",
    }
)

FORBIDDEN_NAME_SUBSTRINGS = ("cutover_live",)
FORBIDDEN_NAME_PREFIXES = ("dungeonmind",)

WORLD_DSN_ENV_NAMES = (
    "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
    "DUNGEONMIND_DATABASE_URL",
    "DMB_CUTOVER_TEST_DATABASE_URL",
)


def database_name_from_dsn(dsn: str) -> str:
    cleaned = dsn.strip()
    if not cleaned:
        raise ApplicationStateIsolationError("application-state DSN is empty")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ApplicationStateIsolationError(
            f"application-state DSN scheme must be postgresql, not {parsed.scheme!r}"
        )
    path = unquote(parsed.path or "").lstrip("/")
    name = path.split("/")[0].strip()
    if not name:
        raise ApplicationStateIsolationError("application-state DSN is missing a database name")
    return name


def assert_safe_application_state_database_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ApplicationStateIsolationError("application-state database name is empty")
    lowered = cleaned.lower()
    if lowered in FORBIDDEN_DATABASE_NAMES:
        raise ApplicationStateIsolationError(
            f"refusing application-state database name {cleaned!r}: denylist"
        )
    if any(fragment in lowered for fragment in FORBIDDEN_NAME_SUBSTRINGS):
        raise ApplicationStateIsolationError(
            f"refusing application-state database name {cleaned!r}: cutover_live"
        )
    if any(lowered.startswith(prefix) for prefix in FORBIDDEN_NAME_PREFIXES):
        raise ApplicationStateIsolationError(
            f"refusing application-state database name {cleaned!r}: dungeonmind* denylist"
        )
    return cleaned


def assert_safe_application_state_dsn(dsn: str) -> str:
    name = database_name_from_dsn(dsn)
    assert_safe_application_state_database_name(name)
    return dsn.strip()


def assert_dsn_is_not_world_graph(dsn: str, *, world_dsns: dict[str, str]) -> None:
    candidate = dsn.strip()
    for env_name, world_dsn in world_dsns.items():
        other = (world_dsn or "").strip()
        if other and candidate == other:
            raise ApplicationStateIsolationError(
                f"application-state DSN must not equal {env_name}"
            )
        if other:
            try:
                if database_name_from_dsn(candidate) == database_name_from_dsn(other):
                    raise ApplicationStateIsolationError(
                        f"application-state database name collides with {env_name}"
                    )
            except ApplicationStateIsolationError:
                raise
            except Exception:
                continue
