from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def live_sessions_root() -> Path:
    return repo_root() / "evals/c2_live_prep/live"


def default_live_session_dir() -> Path:
    return live_sessions_root() / "session_22"


def session_workspace_dir(*, session: int) -> Path:
    return live_sessions_root() / f"session_{session}"


def resolve_allowed_output_dir(output_dir: Path) -> Path:
    """Resolve and ensure ``output_dir`` stays under the live sessions root."""
    root = live_sessions_root().resolve()
    resolved = output_dir.expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"output directory must be under {root}; got {resolved}"
        ) from exc
    return resolved


def workspace_has_live_files(path: Path) -> bool:
    markers = (
        "live_packet.json",
        "surface_layout.json",
        "event_log.jsonl",
        "job_queue.jsonl",
        "current_state.json",
        "recap.md",
    )
    return any((path / name).exists() for name in markers)
