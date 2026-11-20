from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from apps.live_control_server.routes import live

def _snapshot_files(base: Path) -> dict[str, bytes]:
    return {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }


LEGACY_COMBAT_ROUTES = [
    ("GET", "/api/live/combat/current"),
    ("PATCH", "/api/live/combat/current/entities/old-actor"),
    ("POST", "/api/live/combat/current/entities/old-actor/hp-delta"),
    ("POST", "/api/live/combat/current/sort-initiative"),
    ("POST", "/api/live/combat/current/active-turn"),
    ("POST", "/api/live/combat/current/turn"),
    ("GET", "/api/live/combat/saves"),
    ("POST", "/api/live/combat/current/load"),
    ("POST", "/api/live/combat/current/unload"),
    ("POST", "/api/live/combat/current/new"),
    ("POST", "/api/live/combat/saves"),
    ("POST", "/api/live/statblocks/view/generated/old-statblock/combat/add"),
]


def _invoke_route_handler(method: str, path: str) -> None:
    route = next(
        route
        for route in live.router.routes
        if hasattr(route, "methods")
        and method in (route.methods or ())
        and route.path_regex.fullmatch(path)
    )
    path_params = {
        parameter.name: "legacy-id"
        for parameter in route.dependant.path_params
    }
    assert route.status_code == 410
    route.endpoint(**path_params)


@pytest.mark.parametrize(("method", "path"), LEGACY_COMBAT_ROUTES)
def test_legacy_combat_routes_are_retired_without_changing_existing_saves(
    tmp_path: Path,
    monkeypatch,
    method: str,
    path: str,
) -> None:
    session_dir = tmp_path / "session_22"
    session_dir.mkdir()
    legacy_files = {
        "combat/current_combat.json": b'{"legacy":"current"}\n',
        "combat/saves/old-slot.json": b'{"legacy":"save"}\n',
        "combat/backups/old-backup.json": b'{"legacy":"backup"}\n',
    }
    for relative_path, content in legacy_files.items():
        destination = session_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    before = _snapshot_files(session_dir)
    with pytest.raises(HTTPException) as raised:
        _invoke_route_handler(method, path)

    assert raised.value.status_code == 410
    assert raised.value.detail == (
        "Checkout-local Combat is retired. Use World-owned Combat encounters."
    )
    assert _snapshot_files(session_dir) == before
    for relative_path, content in legacy_files.items():
        assert (session_dir / relative_path).read_bytes() == content


def test_legacy_current_get_does_not_initialize_a_checkout_local_encounter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    session_dir = tmp_path / "session_22"
    session_dir.mkdir()
    with pytest.raises(HTTPException) as raised:
        _invoke_route_handler("GET", "/api/live/combat/current")

    assert raised.value.status_code == 410
    assert not (session_dir / "combat" / "current_combat.json").exists()
