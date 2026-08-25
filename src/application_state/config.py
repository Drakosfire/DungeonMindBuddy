"""Application-state DSN parsing. No World Graph fallback."""

from __future__ import annotations

import os

from application_state.errors import ApplicationStateUnavailableError
from application_state.naming import (
    WORLD_DSN_ENV_NAMES,
    assert_dsn_is_not_world_graph,
    assert_safe_application_state_dsn,
)

APPLICATION_STATE_DSN_ENV = "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"
TEST_ADMIN_DSN_ENV = "DMB_APPLICATION_STATE_TEST_DATABASE_URL"


def _world_dsns_from_env() -> dict[str, str]:
    return {name: os.environ.get(name, "") for name in WORLD_DSN_ENV_NAMES}


def plan_kind_uses_postgres() -> bool:
    """True after the Plan kind is switched: app-state DSN is configured.

    Unset DSN is the pre-switch window (file registry remains Plan authority).
    A set but unusable DSN is switched and must fail closed with no file fallback.
    """
    return bool(os.environ.get(APPLICATION_STATE_DSN_ENV, "").strip())


def load_runtime_dsn() -> str:
    raw = os.environ.get(APPLICATION_STATE_DSN_ENV, "").strip()
    if not raw:
        raise ApplicationStateUnavailableError(
            f"{APPLICATION_STATE_DSN_ENV} is not set; Plan kind cannot use application state"
        )
    try:
        assert_safe_application_state_dsn(raw)
        assert_dsn_is_not_world_graph(raw, world_dsns=_world_dsns_from_env())
    except ApplicationStateUnavailableError:
        raise
    except Exception as exc:
        raise ApplicationStateUnavailableError(str(exc)) from exc
    return raw


def load_test_admin_dsn() -> str:
    raw = os.environ.get(TEST_ADMIN_DSN_ENV, "").strip()
    if not raw:
        raise ApplicationStateUnavailableError(
            f"{TEST_ADMIN_DSN_ENV} is not set; cannot create ephemeral application-state databases"
        )
    return raw
