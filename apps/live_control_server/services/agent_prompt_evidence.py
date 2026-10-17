"""Owner-private exact prepared request capture; never normal history or telemetry."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
import stat
from uuid import UUID, uuid4

from apps.live_control_server.config import artifact_data_root

MAX_PROMPT_BYTES = 16 * 1024 * 1024


class PromptEvidenceError(ValueError):
    pass


@contextmanager
def _directory():
    """Directory descriptors prevent symlink/path substitution under the data root."""
    descriptors = []
    try:
        current = os.open(artifact_data_root(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(current)
        for name in ("out", "agent_request_evidence"):
            try:
                os.mkdir(name, mode=0o700, dir_fd=current)
            except FileExistsError:
                pass
            current = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            descriptors.append(current)
        info = os.fstat(current)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise PromptEvidenceError("prompt_evidence_directory_not_private")
        yield current
    except OSError as exc:
        raise PromptEvidenceError("prompt_evidence_unavailable") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _validated_bytes(payload_json: str, digest: str, size: int) -> bytes:
    payload = payload_json.encode("utf-8", errors="strict")
    if not 0 < len(payload) <= MAX_PROMPT_BYTES or len(payload) != size or sha256(payload).hexdigest() != digest:
        raise PromptEvidenceError("prompt_evidence_integrity_failure")
    if not isinstance(json.loads(payload_json), dict):
        raise PromptEvidenceError("prompt_evidence_invalid_envelope")
    return payload


def store_prompt(payload_json: str, *, digest: str, size: int) -> UUID:
    payload = _validated_bytes(payload_json, digest, size)
    evidence_id = uuid4()
    name = str(evidence_id) + ".json"
    with _directory() as directory:
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(directory)
        except BaseException:
            os.unlink(name, dir_fd=directory)
            raise
    return evidence_id


def read_prompt(reference) -> str:
    # Only a verified APP observation may reach this function. No caller path.
    name = str(UUID(str(reference.evidence_id))) + ".json"
    with _directory() as directory:
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size != reference.payload_utf8_bytes
                        or not 0 < info.st_size <= MAX_PROMPT_BYTES):
                    raise PromptEvidenceError("prompt_evidence_integrity_failure")
                payload = stream.read(MAX_PROMPT_BYTES + 1)
        except OSError as exc:
            raise PromptEvidenceError("prompt_evidence_unavailable") from exc
    try:
        text = payload.decode("utf-8", errors="strict")
        _validated_bytes(text, reference.payload_sha256, reference.payload_utf8_bytes)
    except (UnicodeError, ValueError) as exc:
        raise PromptEvidenceError("prompt_evidence_integrity_failure") from exc
    return text
