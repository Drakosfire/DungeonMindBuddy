#!/usr/bin/env python3
"""Verify an exact merged serving PR before an off-main image build."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SHA = re.compile(r"[0-9a-f]{40}\Z")
BRANCH = re.compile(r"codex/[a-z0-9][a-z0-9._/-]{0,180}\Z")


def validate_pr(record: dict[str, Any], *, revision: str, branch: str) -> None:
    base = record.get("base")
    if (record.get("merged") is not True or record.get("merge_commit_sha") != revision
            or not isinstance(base, dict) or base.get("ref") != branch):
        raise ValueError("PR is not merged at the requested revision into the configured serving branch")


def verify(*, revision: str, parent: str, pr: str, branch: str, repository: str) -> None:
    if not SHA.fullmatch(revision) or not SHA.fullmatch(parent) or revision == parent:
        raise ValueError("exact, distinct candidate and serving-parent revisions are required")
    if not re.fullmatch(r"[1-9][0-9]{0,9}", pr):
        raise ValueError("a numeric merged serving PR is required")
    if not BRANCH.fullmatch(branch) or '..' in branch or branch.endswith(('/', '.', '.lock')):
        raise ValueError("a configured codex serving branch is required")
    if repository.lower() != "drakosfire/dungeonmindbuddy":
        raise ValueError("unexpected repository")
    record = json.loads(subprocess.check_output(
        ["gh", "api", f"repos/{repository}/pulls/{pr}"], text=True,
    ))
    validate_pr(record, revision=revision, branch=branch)
    ref = f"refs/remotes/origin/{branch}"
    if not os.environ.get("GH_TOKEN"):
        raise ValueError("GitHub token unavailable for serving-source verification")
    with tempfile.TemporaryDirectory(prefix="buddy-serving-fetch-") as directory:
        askpass = Path(directory) / "askpass"
        askpass.write_text('#!/bin/sh\ncase "$1" in *Username*) printf "%s\\n" x-access-token ;; *) printf "%s\\n" "$GH_TOKEN" ;; esac\n')
        askpass.chmod(0o700)
        env = {**os.environ, "GIT_ASKPASS": str(askpass), "GIT_TERMINAL_PROMPT": "0"}
        subprocess.run(["git", "fetch", "--no-tags", "origin", f"+refs/heads/{branch}:{ref}"], check=True, env=env)
    actual = subprocess.check_output(["git", "rev-parse", ref], text=True).strip()
    first_parent = subprocess.check_output(["git", "rev-parse", f"{revision}^1"], text=True).strip()
    if actual != revision or first_parent != parent:
        raise ValueError("candidate must be the configured serving branch tip and directly follow the expected serving parent")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--parent", required=True)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args()
    try:
        verify(revision=args.revision, parent=args.parent, pr=args.pr,
               branch=os.environ.get("BUDDY_SERVING_RELEASE_BRANCH", ""),
               repository=os.environ.get("GITHUB_REPOSITORY", ""))
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Serving release rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
