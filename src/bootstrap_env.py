"""Load local env files so ``OPENAI_API_KEY`` and friends match CLI behavior without manual ``export``."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

_log = logging.getLogger(__name__)

# ``src/bootstrap_env.py`` → repo root is parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[1]


def load_dungeonmindbuddy_dotenv(*, override: bool = True) -> None:
    """
    Load the first existing file from this list (later files override earlier when ``override``).

    Order matches ``src/cli.py`` expectations, with ``.env`` first for common local setups:

    - ``<repo>/.env``
    - ``<repo>/.env.development``
    - ``<parent>/.env.development`` (monorepo / shared dev env)
    """
    candidates = [
        _REPO_ROOT / ".env",
        _REPO_ROOT / ".env.development",
        _REPO_ROOT.parent / ".env.development",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            load_dotenv(path, override=override)
        except OSError as exc:
            _log.warning("Could not load env file %s: %s. Continuing.", path, exc)
