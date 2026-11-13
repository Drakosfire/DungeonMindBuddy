"""Drain a local service's output into a bounded pair of log files."""

import sys
from pathlib import Path

MAX_BYTES = 4 * 1024 * 1024


def drain(path: Path) -> None:
    previous = path.with_suffix(".log.1")
    with path.open("ab", buffering=0) as log:
        size = log.tell()
    while chunk := sys.stdin.buffer.read1(64 * 1024):
        if size + len(chunk) > MAX_BYTES:
            path.replace(previous)
            size = 0
        with path.open("ab", buffering=0) as log:
            log.write(chunk)
        size += len(chunk)


if __name__ == "__main__":
    drain(Path(sys.argv[1]))
