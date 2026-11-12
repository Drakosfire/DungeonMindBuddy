from __future__ import annotations

import os
import subprocess
from pathlib import Path


HELPER = Path(__file__).resolve().parents[1] / "scripts" / "local_pdf_ocr_env.sh"


def _layout(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    workspace = tmp_path / "workspace"
    buddy = workspace / "DungeonMindBuddy"
    python = workspace / "RulesIngestion" / ".venv-deepseek-ocr2" / "bin" / "python"
    command = workspace / "GenerationEngine" / "GenerationEngine" / "scripts" / "run_local_ocr.py"
    projects = tmp_path / "Projects"
    revision = "a" * 40
    checkpoint = projects / ".cache" / "huggingface" / "hub" / "models--deepseek-ai--DeepSeek-OCR-2" / "snapshots" / revision
    buddy.mkdir(parents=True)
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\\n")
    python.chmod(0o755)
    command.parent.mkdir(parents=True)
    command.write_text("# local OCR worker\\n")
    (checkpoint.parent.parent / "refs").mkdir(parents=True)
    (checkpoint.parent.parent / "refs" / "main").write_text(f"{revision}\\n")
    checkpoint.mkdir(parents=True)
    return buddy, python, command, checkpoint


def _configure(buddy: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    script = f'source "{HELPER}"; configure_local_pdf_ocr "{buddy}"; printf "%s\\n" "${{BUDDY_OCR_PYTHON-}}" "${{BUDDY_OCR_COMMAND-}}" "${{BUDDY_OCR_CHECKPOINT-}}"'
    return subprocess.run(["bash", "-e", "-u", "-o", "pipefail", "-c", script], check=True, capture_output=True, text=True, env=env)


def test_launcher_discovers_existing_local_ocr_2_assets(tmp_path: Path) -> None:
    buddy, python, command, checkpoint = _layout(tmp_path)
    env = os.environ.copy()
    env.pop("BUDDY_OCR_PYTHON", None)
    env.pop("BUDDY_OCR_COMMAND", None)
    env.pop("BUDDY_OCR_CHECKPOINT", None)
    env.pop("HF_HUB_CACHE", None)
    env.pop("HF_HOME", None)
    env["DUNGEONMIND_WORKSPACE_ROOT"] = str(buddy.parent)
    env["DUNGEONMIND_PROJECTS_ROOT"] = str(tmp_path / "Projects")

    result = _configure(buddy, env)

    assert result.stdout.splitlines() == [str(python), str(command), str(checkpoint)]
    assert "cached DeepSeek OCR 2 model" in result.stderr


def test_launcher_accepts_cached_revision_without_final_newline(tmp_path: Path) -> None:
    buddy, python, command, checkpoint = _layout(tmp_path)
    ref = checkpoint.parent.parent / "refs" / "main"
    ref.write_text("a" * 40)
    env = os.environ.copy()
    env.pop("BUDDY_OCR_PYTHON", None)
    env.pop("BUDDY_OCR_COMMAND", None)
    env.pop("BUDDY_OCR_CHECKPOINT", None)
    env.pop("HF_HUB_CACHE", None)
    env.pop("HF_HOME", None)
    env["DUNGEONMIND_WORKSPACE_ROOT"] = str(buddy.parent)
    env["DUNGEONMIND_PROJECTS_ROOT"] = str(tmp_path / "Projects")

    result = _configure(buddy, env)

    assert result.stdout.splitlines() == [str(python), str(command), str(checkpoint)]
    assert "cached DeepSeek OCR 2 model" in result.stderr


def test_launcher_keeps_explicit_local_ocr_overrides(tmp_path: Path) -> None:
    buddy, _, _, _ = _layout(tmp_path)
    override_root = tmp_path / "override"
    python = override_root / "python"
    command = override_root / "worker.py"
    checkpoint = override_root / "checkpoint"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\\n")
    python.chmod(0o755)
    command.write_text("# custom worker\\n")
    checkpoint.mkdir()
    env = os.environ.copy()
    env.update({
        "BUDDY_OCR_PYTHON": str(python),
        "BUDDY_OCR_COMMAND": str(command),
        "BUDDY_OCR_CHECKPOINT": str(checkpoint),
    })

    result = _configure(buddy, env)

    assert result.stdout.splitlines() == [str(python), str(command), str(checkpoint)]
    assert "cached DeepSeek OCR 2 model" in result.stderr


def test_launcher_disables_incomplete_or_unpinned_local_cache(tmp_path: Path) -> None:
    buddy, _, _, _ = _layout(tmp_path)
    env = os.environ.copy()
    env.pop("BUDDY_OCR_PYTHON", None)
    env.pop("BUDDY_OCR_COMMAND", None)
    env.pop("BUDDY_OCR_CHECKPOINT", None)
    env.pop("HF_HUB_CACHE", None)
    env.pop("HF_HOME", None)
    env["DUNGEONMIND_WORKSPACE_ROOT"] = str(buddy.parent)
    env["DUNGEONMIND_PROJECTS_ROOT"] = str(tmp_path / "Projects")
    ref = tmp_path / "Projects" / ".cache" / "huggingface" / "hub" / "models--deepseek-ai--DeepSeek-OCR-2" / "refs" / "main"
    ref.write_text("../untrusted-path\\n")

    result = _configure(buddy, env)

    assert result.stdout.splitlines() == ["", "", ""]
    assert "Local PDF OCR unavailable" in result.stderr
