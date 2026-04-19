"""Unit tests for ``--detach`` argv filtering in step1_recap_ingest_run."""

from __future__ import annotations

import importlib

_mod = importlib.import_module(
    "evals.session_recap_ingest_vertical_slice.step1_recap_ingest_run"
)
_filter = _mod._filter_argv_for_detach_child


def test_filter_strips_detach_aliases_and_log() -> None:
    assert _filter(["--n", "5", "--detach"]) == ["--n", "5"]
    assert _filter(["--background", "--quiet"]) == ["--quiet"]
    assert _filter(["--detach-follow", "--n", "2"]) == ["--n", "2"]
    assert _filter(["--detach-log", "/tmp/x.log", "--n", "3"]) == ["--n", "3"]
    assert _filter(["--detach-log=/tmp/y.log", "-v"]) == ["-v"]


def test_filter_preserves_other_flags() -> None:
    assert _filter(["--n", "5", "--model", "gpt", "--runs-root", "/tmp/r"]) == [
        "--n",
        "5",
        "--model",
        "gpt",
        "--runs-root",
        "/tmp/r",
    ]
