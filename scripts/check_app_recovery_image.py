#!/usr/bin/env python3
"""Build a local APP recovery image from an exact, label-matched Buddy SHA."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

FILES = ("Dockerfile.app-recovery", "scripts/application_state_authority.py")


def run(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sha", help="full reviewed recovery-tool commit SHA")
    parser.add_argument("runtime_sha", help="full Buddy runtime commit SHA")
    parser.add_argument("runtime", help="local runtime image tagged with that SHA")
    args = parser.parse_args()
    if not all(re.fullmatch(r"[0-9a-f]{40}", value) for value in (args.sha, args.runtime_sha)):
        parser.error("sha must be a full lowercase commit SHA")
    resolved = run("git", "rev-parse", "--verify", f"{args.sha}^{{commit}}").strip()
    if resolved != args.sha:
        parser.error("SHA does not resolve exactly")
    runtime_resolved = run("git", "rev-parse", "--verify", f"{args.runtime_sha}^{{commit}}").strip()
    if runtime_resolved != args.runtime_sha:
        parser.error("runtime SHA does not resolve exactly")
    image = json.loads(run("docker", "image", "inspect", args.runtime))[0]
    labels = image.get("Config", {}).get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != args.runtime_sha:
        parser.error("runtime image revision label does not match runtime SHA")
    image_id = image.get("Id", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        parser.error("runtime image has no valid immutable image ID")
    tag = f"buddy-app-recovery:{args.sha}-{args.runtime_sha}"
    existing = run("docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}")
    if tag in existing.splitlines():
        parser.error("recovery image tag already exists; choose an unused local image store")
    with tempfile.TemporaryDirectory(prefix="buddy-app-recovery-") as tmp:
        root = Path(tmp)
        for name in FILES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.run(
                ["git", "show", f"{args.sha if name == FILES[0] else args.runtime_sha}:{name}"], check=True, stdout=subprocess.PIPE
            ).stdout)
        subprocess.run([
            "docker", "build", "--file", str(root / FILES[0]), "--build-arg", f"BUDDY_RUNTIME_IMAGE={image_id}",
            "--label", f"org.opencontainers.image.revision={args.sha}",
            "--label", f"org.dungeonmind.runtime.revision={args.runtime_sha}",
            "--tag", tag, str(root),
        ], check=True)
    print(f"Built {tag} from runtime {image_id}")


if __name__ == "__main__":
    main()
