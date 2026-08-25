"""Keep the operator product application-state DSN out of default tests.

Loaded globally via pytest ``-p`` so Plan/Runbook's one-way PostgreSQL switch
cannot mutate the operator database from tests that never requested a disposable
DSN. Tests that opt into ``application_state_dsn`` keep that fixture's URL.

Switched Content kinds are also opted in by nodeid (see
``needs_disposable_application_state``) so the normal Play/workspace regression
surface is green without sprinkling ``pytest_plugins`` through globals.
"""

from __future__ import annotations

import pytest

SWITCHED_CONTENT_NODE_TOKENS = (
    "tests/test_workspace_document_registry.py",
    "tests/test_tiptap_markdown_write.py",
    "tests/test_live_tiptap_markdown_write.py",
    "tests/test_play_",
    "tests/test_live_play_run",
    "tests/test_live_play_active_run",
    "tests/application_state/",
)


def needs_disposable_application_state(nodeid: str) -> bool:
    normalized = nodeid.replace("\\", "/")
    return any(token in normalized for token in SWITCHED_CONTENT_NODE_TOKENS)


@pytest.fixture(autouse=True)
def _isolate_application_state_dsn(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    if "application_state_dsn" in request.fixturenames:
        return
    if needs_disposable_application_state(request.node.nodeid):
        return
    monkeypatch.delenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", raising=False)
