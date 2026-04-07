from __future__ import annotations

import importlib
import json
from pathlib import Path


class _StubStore:
    """Minimal store for council-room runner scope block (real CLI not used in stubs)."""

    evidence_units: list = []

    def project(self, campaign_id: str) -> dict:  # noqa: ARG002
        return {"entities": {}}

    def list_entities(self) -> list:
        return []


def _install_stub_cli(module, monkeypatch, answer: str = "stub answer with observed chandelier") -> None:
    class _StubCLI:
        def __init__(self, *, store_dir, verbose) -> None:  # noqa: ANN001
            _ = (store_dir, verbose)
            self.store = _StubStore()

        def handle_line(self, line: str) -> bool:
            _ = line
            return True

    monkeypatch.setattr(module, "DungeonBuddyCLI", _StubCLI)

    def _fake_redirect_stdout(capture):
        from contextlib import contextmanager

        @contextmanager
        def _cm():
            capture.write(answer)
            yield

        return _cm()

    monkeypatch.setattr(module, "redirect_stdout", _fake_redirect_stdout)


def _prepare_eval_tree(base: Path) -> None:
    out = base / "evals" / "mirathorn_vertical_slice" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase_d_store").mkdir(parents=True, exist_ok=True)


def test_runner_enforces_campaign_scope(monkeypatch, tmp_path) -> None:
    module = importlib.import_module("evals.mirathorn_vertical_slice.run_council_room_question_set")
    observed_commands: list[str] = []

    class _StubCLI:
        def __init__(self, *, store_dir, verbose) -> None:  # noqa: ANN001
            _ = (store_dir, verbose)
            self.store = _StubStore()

        def handle_line(self, line: str) -> bool:
            observed_commands.append(line)
            return True

    monkeypatch.setattr(module, "DungeonBuddyCLI", _StubCLI)
    monkeypatch.chdir(tmp_path)
    _prepare_eval_tree(tmp_path)
    monkeypatch.delenv(module.WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV, raising=False)
    summary = module.run()
    ask_commands = [cmd for cmd in observed_commands if cmd.startswith("ask ")]
    expected_questions = module._load_gold_questions(module.GOLD_QUESTIONS_PATH)
    assert len(ask_commands) == len(expected_questions)
    assert all("--campaign longmont-c1" in cmd for cmd in ask_commands)
    assert all("--require-campaign" in cmd for cmd in ask_commands)
    assert "overall_strict" in summary
    assert "overall_semantic" in summary
    assert summary.get("artifact_write_skipped") is True


def test_no_artifact_write_without_opt_in_even_if_openai_key_set(monkeypatch, tmp_path) -> None:
    """Dotenv can repopulate OPENAI_API_KEY; writes must not depend on that."""
    module = importlib.import_module("evals.mirathorn_vertical_slice.run_council_room_question_set")
    monkeypatch.chdir(tmp_path)
    _prepare_eval_tree(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.delenv(module.WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV, raising=False)
    _install_stub_cli(module, monkeypatch)
    module.run()
    out = tmp_path / "evals" / "mirathorn_vertical_slice" / "output"
    assert not (out / "council_room_question_set.json").exists()
    assert not (out / "council_room_question_set.md").exists()


def test_artifact_write_requires_opt_in_exactly_one(monkeypatch, tmp_path) -> None:
    module = importlib.import_module("evals.mirathorn_vertical_slice.run_council_room_question_set")
    monkeypatch.chdir(tmp_path)
    _prepare_eval_tree(tmp_path)
    monkeypatch.setenv(module.WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV, "true")
    _install_stub_cli(module, monkeypatch)
    module.run()
    out = tmp_path / "evals" / "mirathorn_vertical_slice" / "output"
    assert not (out / "council_room_question_set.json").exists()


def test_artifact_write_when_opt_in_and_nonempty_answers(monkeypatch, tmp_path) -> None:
    module = importlib.import_module("evals.mirathorn_vertical_slice.run_council_room_question_set")
    monkeypatch.chdir(tmp_path)
    _prepare_eval_tree(tmp_path)
    monkeypatch.setenv(module.WRITE_COUNCIL_ROOM_QUESTION_SET_ARTIFACTS_ENV, "1")
    _install_stub_cli(module, monkeypatch)
    summary = module.run()
    out = tmp_path / "evals" / "mirathorn_vertical_slice" / "output"
    jpath = out / "council_room_question_set.json"
    assert jpath.exists()
    assert (out / "council_room_question_set.md").exists()
    assert summary.get("artifact_write_skipped") is False
    data = json.loads(jpath.read_text(encoding="utf-8"))
    assert "overall_strict" in data
