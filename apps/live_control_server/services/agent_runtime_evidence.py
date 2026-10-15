"""Opt-in private observations of ordinary runtime execution; never authority."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import stat
from uuid import uuid4

ENV = "DMB_AGENT_PRIVATE_EVIDENCE_DIR"
MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_DIRECTORY_BYTES = 64 * 1024 * 1024
_LOG = logging.getLogger(__name__)


def _encoded(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode()


def _publish(directory: Path, name: str, value: dict) -> str:
    """Publish a private immutable observation without replacing prior evidence."""
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("capture_filename_invalid")
    data = _encoded(value)
    if len(data) > MAX_PAYLOAD_BYTES:
        raise OverflowError("capture_size_limit")
    if not directory.is_absolute() or directory.resolve() != directory:
        raise ValueError("capture_directory_invalid")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Capture is optional on hosts without this private POSIX publication seam.
    # Import here so disabled capture remains portable and has no IO effect.
    import fcntl

    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = f".{uuid4().hex}.pending"
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        info = os.fstat(descriptor)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise PermissionError("capture_directory_not_private")
        total = sum(
            os.stat(item, dir_fd=descriptor, follow_symlinks=False).st_size
            for item in os.listdir(descriptor)
        )
        if total + len(data) > MAX_DIRECTORY_BYTES:
            raise OverflowError("capture_directory_limit")
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=descriptor,
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(
                temporary,
                name,
                src_dir_fd=descriptor,
                dst_dir_fd=descriptor,
                follow_symlinks=False,
            )
            os.fsync(descriptor)
        finally:
            os.unlink(temporary, dir_fd=descriptor)
    finally:
        os.close(descriptor)
    return sha256(data).hexdigest()


def _implementation():
    root = Path(__file__).resolve().parents[3]
    paths = [
        "uv.lock",
        "pyproject.toml",
        "apps/live_control_server/services/agent_runtime_evidence.py",
        "apps/live_control_server/services/agent_turn_service.py",
    ]
    return {
        path: sha256((root / path).read_bytes()).hexdigest()
        if (root / path).is_file()
        else None
        for path in paths
    }


def run_with_private_evidence(runtime, invocation, *, binding):
    """Observe exactly this ordinary Build dispatch, preserving its result/error.

    This is runtime input and returned data, not an exact provider wire capture
    or a validated APP execution receipt. Missing worker data stays missing.
    """
    configured = os.environ.get(ENV)
    surface = invocation.context_packet.surface_context
    if not configured or surface is None or surface.surface_id != "build":
        return runtime.run(invocation)
    capture_id = uuid4().hex
    directory = Path(configured)
    envelope = None
    try:
        invocation_data = asdict(invocation)
        envelope = {
            "schema": "dmb_private_agent_runtime_observation_v1",
            "capture_id": capture_id,
            "capture_state": "unvalidated_observation",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "binding": dict(binding),
            "runtime": asdict(runtime.descriptor),
            "implementation_sha256": _implementation(),
            "input_kind": "runtime_invocation_not_provider_wire",
            "invocation": invocation_data,
            "invocation_sha256": sha256(_encoded(invocation_data)).hexdigest(),
        }
        _publish(directory, f"{capture_id}-input.json", envelope)
    except Exception:
        _LOG.warning("Agent private evidence incomplete: input_capture_failed")
        envelope = None
    result = None
    failure_class = None
    try:
        result = runtime.run(invocation)
        return result
    except BaseException as exc:
        failure_class = type(exc).__name__
        raise
    finally:
        if envelope is not None:
            try:
                output = None
                if result is not None:
                    output = {
                        "status": result.status,
                        "final_text": result.final_text,
                        "messages": result.messages,
                        "runtime_session_id": result.runtime_session_id,
                        "answer_scope": result.answer_scope,
                        "tool_events": [asdict(event) for event in result.tool_events],
                        "retrieval_session": result.context_updates.get(
                            "retrieval_session"
                        ),
                        "retrieval_session_id": result.context_updates.get(
                            "retrieval_session_id"
                        ),
                        "observed_model_call_count": result.observed_model_call_count,
                        "error_code": result.error_code,
                    }
                record = {
                    **envelope,
                    "result": output,
                    "exception_class": failure_class,
                    "capture_completeness": "returned_data_only"
                    if output is not None
                    else "input_only_runtime_exception",
                }
                try:
                    digest = _publish(directory, f"{capture_id}-result.json", record)
                    _LOG.info(
                        "Agent private evidence captured: id=%s sha256=%s",
                        capture_id,
                        digest,
                    )
                except OverflowError:
                    _publish(
                        directory,
                        f"{capture_id}-incomplete.json",
                        {
                            "schema": envelope["schema"],
                            "capture_id": capture_id,
                            "binding": envelope["binding"],
                            "invocation_sha256": envelope["invocation_sha256"],
                            "capture_completeness": "incomplete",
                            "reason": "capture_size_limit",
                        },
                    )
                    _LOG.warning(
                        "Agent private evidence incomplete: capture_size_limit"
                    )
            except Exception:
                _LOG.warning("Agent private evidence incomplete: result_capture_failed")
