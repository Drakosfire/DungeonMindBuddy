"""Private exception evidence; safe class/stage metadata is the only trace projection."""
from hashlib import sha256
import json
import os
import re
import stat
import traceback
from uuid import uuid4

from apps.live_control_server.config import artifact_data_root


def _name(exc):
    name = type(exc).__name__
    return name if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', name) else 'Exception'


def store_failure(exc, *, stage, turn_id, attempt):
    identity = uuid4()
    chain = []
    current = exc
    seen = set()
    while current is not None and id(current) not in seen and len(chain) < 8:
        seen.add(id(current))
        chain.append(_name(current))
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    # TracebackException omits frame locals. Clamp message-rich tracebacks; record truncation.
    text = ''.join(traceback.TracebackException.from_exception(exc, capture_locals=False).format())
    truncated = len(text) > 64000
    payload = json.dumps({'schema': 'dmb_build_failure_diagnostic_v1', 'diagnostic_id': str(identity),
        'turn_id': str(turn_id), 'attempt': attempt, 'stage': stage, 'exception_types': chain,
        'traceback': text[-64000:], 'truncated': truncated}, ensure_ascii=False).encode()
    descriptors = []
    try:
        directory = os.open(artifact_data_root(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(directory)
        for name in ('out', 'agent_failure_evidence'):
            try:
                os.mkdir(name, mode=0o700, dir_fd=directory)
            except FileExistsError:
                pass
            directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            descriptors.append(directory)
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError('failure_evidence_directory_not_private')
        filename = str(identity) + '.json'
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(directory)
        except BaseException:
            os.unlink(filename, dir_fd=directory)
            raise
    finally:
        for fd in reversed(descriptors):
            os.close(fd)
    return {'diagnostic_id': identity, 'diagnostic_sha256': sha256(payload).hexdigest(),
        'exception_type': chain[0], 'cause_type': chain[-1], 'stage': stage}


def failure_code(exc):
    """Only an exact host-owned failure gets an explanatory public code."""
    from .build_jev_writer import WriterCapacityError
    current = exc
    seen = set()
    while current is not None and id(current) not in seen and len(seen) < 8:
        seen.add(id(current))
        if type(current) is WriterCapacityError and current.code in {"build_writer_request_over_budget", "build_writer_context_over_budget"}:
            return current.code
        if type(current) is ValueError and str(current) == "World passage lacks its host-provided source name":
            return "build_source_name_missing"
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return "build_execution_exception"
