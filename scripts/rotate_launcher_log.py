"""Drain a local service's output into a bounded pair of log files."""

import fcntl
import sys
from pathlib import Path

MAX_BYTES = 4 * 1024 * 1024


def drain(path: Path) -> None:
    previous = path.with_suffix(".log.1")
    with path.with_suffix(".log.lock").open("ab") as lock:
        while chunk := sys.stdin.buffer.read1(64 * 1024):
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                size = path.stat().st_size if path.exists() else 0
                if size > MAX_BYTES:
                    with path.open("rb") as log:
                        log.seek(-MAX_BYTES, 2)
                        tail = log.read()
                    previous.write_bytes(tail)
                    path.write_bytes(b"")
                elif size + len(chunk) > MAX_BYTES:
                    path.replace(previous)
                with path.open("ab") as log:
                    log.write(chunk)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == "__main__":
    drain(Path(sys.argv[1]))
