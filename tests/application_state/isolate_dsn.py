"""Keep the operator product application-state DSN out of default tests.

Loaded globally via pytest ``-p`` so Plan's one-way PostgreSQL switch cannot
mutate the operator database from tests that never requested a disposable DSN.
Tests that opt into ``application_state_dsn`` keep that fixture's URL.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_application_state_dsn(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    if "application_state_dsn" in request.fixturenames:
        return
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
