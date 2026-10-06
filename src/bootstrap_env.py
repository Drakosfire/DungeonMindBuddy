"""Load local env files so ``OPENAI_API_KEY`` and friends match CLI behavior without manual ``export``."""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

_log = logging.getLogger(__name__)

# ``src/bootstrap_env.py`` → repo root is parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_GRAPH_PROFILE_ENV = "DMB_AGENT_GRAPH_LOCAL_PROFILE"
_LOCAL_GRAPH_PROFILE_KEYS = frozenset({
    "DMB_AGENT_GRAPH_AUTH_MODE",
    "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT",
    "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN",
    "DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN",
    "DMB_AGENT_GRAPH_LOCAL_API_HOST",
    "DMB_AGENT_GRAPH_SESSION_STORE",
})


class LocalGraphProfileError(RuntimeError):
    """An opted-in private local Graph profile failed closed."""


def read_local_graph_profile(path_text: str) -> dict[str, str]:
    """Read only the six local auth/session fields from an owner-private file."""
    path = Path(path_text)
    if not path.is_absolute() or path.is_symlink():
        raise LocalGraphProfileError("local_graph_profile_path_invalid")
    try:
        file_stat = path.stat()
        parent_stat = path.parent.stat()
    except OSError as exc:
        raise LocalGraphProfileError("local_graph_profile_unavailable") from exc
    if (
        not stat.S_ISREG(file_stat.st_mode)
        or file_stat.st_uid != os.getuid()
        or stat.S_IMODE(file_stat.st_mode) != 0o600
        or parent_stat.st_uid != os.getuid()
        or stat.S_IMODE(parent_stat.st_mode) & 0o077
    ):
        raise LocalGraphProfileError("local_graph_profile_permissions_invalid")
    try:
        values = dotenv_values(path, interpolate=False)
    except (OSError, UnicodeError, ValueError) as exc:
        raise LocalGraphProfileError("local_graph_profile_unreadable") from exc
    if set(values) != _LOCAL_GRAPH_PROFILE_KEYS or any(
        not isinstance(value, str) or not value for value in values.values()
    ):
        raise LocalGraphProfileError("local_graph_profile_fields_invalid")
    profile = {key: values[key] for key in _LOCAL_GRAPH_PROFILE_KEYS}
    token = profile["DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN"]
    if (
        profile["DMB_AGENT_GRAPH_AUTH_MODE"] != "local_operator"
        or profile["DMB_AGENT_GRAPH_AUTH_ENVIRONMENT"] not in {"local", "development", "dev"}
        or len(token) < 32
        or any(character.isspace() for character in token)
        or not Path(profile["DMB_AGENT_GRAPH_SESSION_STORE"]).is_absolute()
    ):
        raise LocalGraphProfileError("local_graph_profile_fields_invalid")
    return profile


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
    profile_path = os.environ.get(LOCAL_GRAPH_PROFILE_ENV, "").strip()
    if profile_path:
        # This explicit private overlay owns its six fields even when the
        # ordinary dotenv loader was asked not to override ambient settings.
        os.environ.update(read_local_graph_profile(profile_path))
