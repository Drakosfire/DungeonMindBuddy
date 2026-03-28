from __future__ import annotations

import importlib


def test_runner_enforces_campaign_scope(monkeypatch) -> None:
    module = importlib.import_module("evals.mirathorn_vertical_slice.run_council_room_question_set")
    observed_commands: list[str] = []

    class _StubCLI:
        def __init__(self, *, store_dir, verbose) -> None:  # noqa: ANN001
            _ = (store_dir, verbose)

        def handle_line(self, line: str) -> bool:
            observed_commands.append(line)
            return True

    monkeypatch.setattr(module, "DungeonBuddyCLI", _StubCLI)
    summary = module.run()
    ask_commands = [cmd for cmd in observed_commands if cmd.startswith("ask ")]
    assert len(ask_commands) == 5
    assert all("--campaign longmont-c1" in cmd for cmd in ask_commands)
    assert all("--require-campaign" in cmd for cmd in ask_commands)
    assert "overall_strict" in summary
    assert "overall_semantic" in summary
