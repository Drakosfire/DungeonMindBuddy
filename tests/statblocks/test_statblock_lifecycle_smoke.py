from __future__ import annotations

import json

import pytest

from scripts import statblock_lifecycle_smoke
from src.statblocks.v2_contract import StatBlockGeneratorHealth


def _json_from_stdout(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def test_script_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        statblock_lifecycle_smoke.main(["--help"])

    assert exc_info.value.code == 0
    assert "statblock lifecycle" in capsys.readouterr().out.lower()


def test_health_mock_emits_ok_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = statblock_lifecycle_smoke.main(["health", "--provider", "mock"])

    output = _json_from_stdout(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "ok"
    assert output["command_type"] == "statblock.generator.health"
    assert output["health"]["status"] == "ok"  # type: ignore[index]


def test_generate_fixture_mock_emits_artifact_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = statblock_lifecycle_smoke.main(
        ["generate-fixture", "--provider", "mock"]
    )

    output = _json_from_stdout(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "ok"
    assert output["command_type"] == "statblock.draft.generate"
    assert output["artifact"]["draft_id"] == "mock-generated-draft"  # type: ignore[index]


def test_render_fixture_mock_emits_artifact_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = statblock_lifecycle_smoke.main(["render-fixture", "--provider", "mock"])

    output = _json_from_stdout(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "ok"
    assert output["command_type"] == "statblock.draft.render"
    assert output["artifact"]["draft_id"] == "mock-rendered-draft"  # type: ignore[index]


def test_http_generate_fixture_requires_confirmation_before_provider_construction(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_constructed() -> object:
        raise AssertionError("HTTP provider should not be constructed without confirmation")

    monkeypatch.setattr(
        statblock_lifecycle_smoke,
        "DungeonMindServerStatBlockGeneratorClient",
        fail_if_constructed,
    )

    exit_code = statblock_lifecycle_smoke.main(
        ["generate-fixture", "--provider", "http"]
    )

    output = _json_from_stdout(capsys.readouterr().out)
    assert exit_code == 1
    assert output["status"] == "error"
    assert output["error"]["code"] == "live_generate_confirmation_required"  # type: ignore[index]
    assert output["error"]["details"]["safe_default"] == "mock"  # type: ignore[index]
    assert "mock provider is safe" in output["diagnostics"][0]  # type: ignore[index]


def test_http_health_uses_http_provider_constructor_without_live_network(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    constructed = False
    closed = False

    class FakeHTTPProvider:
        def __init__(self) -> None:
            nonlocal constructed
            constructed = True

        def health(self) -> StatBlockGeneratorHealth:
            return StatBlockGeneratorHealth(status="ok", service="fake-http")

        def close(self) -> None:
            nonlocal closed
            closed = True

    monkeypatch.setattr(
        statblock_lifecycle_smoke,
        "DungeonMindServerStatBlockGeneratorClient",
        FakeHTTPProvider,
    )

    exit_code = statblock_lifecycle_smoke.main(["health", "--provider", "http"])

    output = _json_from_stdout(capsys.readouterr().out)
    assert exit_code == 0
    assert constructed is True
    assert closed is True
    assert output["status"] == "ok"
    assert output["health"]["service"] == "fake-http"  # type: ignore[index]
