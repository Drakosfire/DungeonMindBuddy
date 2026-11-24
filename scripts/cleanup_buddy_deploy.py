"""Retain the serving and verified rollback Buddy releases after a healthy deploy."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess

if __package__:
    from .retire_buddy_release import docker
else:
    from retire_buddy_release import docker


TAG = re.compile(r"dungeonmindbuddy:([0-9a-f]{40})")
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
SOURCE_DIRECTORIES = (
    "apps", "ci", "corpus", "evals", "extraction_lab", "graph_data",
    "integrations", "patches", "schemas", "scripts", "src", "tests", "tools",
)
BUDDY_CACHE = (
    r"live-control-ui|live_control_server|probe_buddy_health\.py|bootstrap_local_play\.py|"
    r"prepare_patched_hermes\.py|patches/hermes-agent|"
    r"COPY.*--from=dependencies.*10001:10001.*/app/\.venv"
)


def inspect_image(tag, expected_id=None):
    match = TAG.fullmatch(tag)
    if not match:
        raise ValueError(f"Invalid Buddy release tag: {tag}")
    image, = json.loads(docker("image", "inspect", tag))
    label = (image["Config"]["Labels"] or {}).get("org.opencontainers.image.revision")
    if label != match[1] or (expected_id is not None and image["Id"] != expected_id):
        raise ValueError(f"Image identity failed verification: {tag}")
    return image


def inventory(project, serving, rollback):
    ids = docker("ps", "-aq", "--no-trunc").splitlines()
    containers = json.loads(docker("container", "inspect", *ids)) if ids else []
    active = [
        record for record in containers
        if record["State"]["Running"]
        and (record["Config"]["Labels"] or {}).get("com.docker.compose.project") == project
        and (record["Config"]["Labels"] or {}).get("com.docker.compose.service") == "buddy"
    ]
    if (
        len(active) != 1 or active[0]["Image"] != serving["Id"]
        or active[0]["State"].get("Health", {}).get("Status") != "healthy"
    ):
        raise ValueError("Expected one healthy Buddy container at the verified serving image")
    if rollback["Id"] == serving["Id"]:
        raise ValueError("Serving and rollback must be distinct images")
    return containers


def created(image):
    return datetime.fromisoformat(image["Created"].replace("Z", "+00:00"))


def related(left, right):
    return left == right or left in right.parents or right in left.parents


def cleanup(args):
    serving = inspect_image(args.serving_tag, args.serving_image)
    rollback = inspect_image(args.rollback_tag, args.rollback_image)
    containers = inventory(args.project, serving, rollback)
    protected = {record["Image"] for record in containers} | {serving["Id"], rollback["Id"]}
    tags = docker("image", "ls", "--format", "{{.Repository}}:{{.Tag}}", "dungeonmindbuddy").splitlines()
    candidates = {}
    for tag in sorted(set(tags)):
        if TAG.fullmatch(tag):
            image = inspect_image(tag)
            # Preserve staged builds and every image used by any container.
            if image["Id"] not in protected and created(image) < created(rollback):
                candidates[tag] = image

    root = args.release_root
    before = shutil.disk_usage(root).free
    for tag, image in candidates.items():
        print(f"{'Retiring' if args.apply else 'Would retire'} {tag}", flush=True)
        if args.apply:
            inventory(args.project, serving, rollback)
            inspect_image(tag, image["Id"])
            docker("image", "rm", "--no-prune", tag)

    # A generated release folder can hold a small Compose override still used
    # by the running stack. Preserve that file and the deployment evidence.
    cutoff = created(rollback).timestamp()
    for release in sorted(root.glob("buddy-*-releases/*")):
        if (
            not re.fullmatch(r"buddy-[0-9]+-releases", release.parent.name)
            or not re.fullmatch(r"[0-9a-f]{40}", release.name)
            or release.resolve() != release
            or not any((release / marker).is_file() for marker in ("rollout.sh", "buddy-release.previous"))
        ):
            continue
        tag = f"dungeonmindbuddy:{release.name}"
        overlay = release / f"compose.release.{release.name}.yaml"
        if tag in {args.serving_tag, args.rollback_tag} or not overlay.is_file():
            continue
        if overlay.is_symlink() or overlay.stat().st_mtime >= cutoff:
            continue
        if tag in tags and tag not in candidates:
            continue
        records = inventory(args.project, serving, rollback)
        references = []
        working_paths = [Path.cwd().resolve()]
        for record in records:
            references.extend(Path(mount["Source"]).resolve() for mount in record.get("Mounts", []) if mount.get("Source"))
            labels = record["Config"]["Labels"] or {}
            references.extend(
                Path(path).resolve()
                for key in ("config_files", "environment_file")
                for path in labels.get(f"com.docker.compose.project.{key}", "").split(",") if path
            )
        for line in Path("/proc/self/mountinfo").read_text().splitlines():
            mountpoint = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), line.split()[4])
            if mountpoint != "/":
                working_paths.append(Path(mountpoint))
        for process in Path("/proc").glob("[0-9]*/cwd"):
            try:
                working_paths.append(process.resolve(strict=True))
            except (PermissionError, FileNotFoundError, ProcessLookupError):
                continue
        for name in SOURCE_DIRECTORIES:
            path = release / name
            if (
                not path.is_dir() or path.resolve() != path
                or any(related(path, ref) for ref in references)
                or any(ref == path or path in ref.parents for ref in working_paths)
            ):
                continue
            print(f"{'Removing' if args.apply else 'Would remove'} {path}", flush=True)
            if args.apply:
                shutil.rmtree(path)

    print("Buddy-only cache selection:", flush=True)
    filters = ("--filter", "shared!=true", "--filter", f"description~={BUDDY_CACHE}")
    if args.apply:
        inventory(args.project, serving, rollback)
        inspect_image(args.rollback_tag, rollback["Id"])
        output = docker("buildx", "prune", "--force", *filters, "--filter", "until=1h")
        print(output.splitlines()[-1] if output else "No matching cache output")
        print(f"Filesystem free-space change: {shutil.disk_usage(root).free - before:+d} bytes")
    else:
        print(docker("buildx", "du", *filters).splitlines()[-4:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--serving-tag", required=True)
    parser.add_argument("--serving-image", required=True)
    parser.add_argument("--rollback-tag", required=True)
    parser.add_argument("--rollback-image", required=True)
    parser.add_argument("--release-root", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if any(not IMAGE_ID.fullmatch(value) for value in (args.serving_image, args.rollback_image)):
        parser.error("Expected full serving and rollback image IDs")
    if not args.release_root.is_dir() or args.release_root.resolve() != args.release_root:
        parser.error("Expected a canonical absolute release root")
    try:
        cleanup(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Buddy cleanup stopped: {error}\n")


if __name__ == "__main__":
    main()
