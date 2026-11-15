"""Check local Docker and persistent storage capacity before a Buddy release."""
import argparse
import os
from pathlib import Path
import subprocess


MIB = 1024 * 1024


def docker_root():
    if os.environ.get("DOCKER_HOST") or os.environ.get("DOCKER_CONTEXT"):
        raise ValueError("Run on the deployment host with the default local Docker context")
    selected = subprocess.check_output(["docker", "context", "show"], text=True).strip()
    if selected != "default":
        raise ValueError("Select the default local Docker context before deploying")
    endpoint = subprocess.check_output(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}", "default"],
        text=True,
    ).strip()
    if not endpoint.startswith("unix://"):
        raise ValueError("The default Docker endpoint must be a local Unix socket")
    return Path(subprocess.check_output(
        ["docker", "--context", "default", "info", "--format", "{{.DockerRootDir}}"],
        text=True,
    ).strip())


def free_bytes(path):
    if not path.is_absolute() or not path.is_dir():
        raise ValueError(f"Expected an existing absolute filesystem path: {path}")
    stat = os.statvfs(path)
    return stat.f_bavail * stat.f_frsize


def available_memory():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            _, amount, unit = line.split()
            if unit == "kB":
                return int(amount) * 1024
            break
    raise ValueError("Linux MemAvailable could not be measured")


def positive_mib(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Enter a positive MiB minimum")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--persistent-root", type=Path, required=True)
    parser.add_argument("--min-docker-mib", type=positive_mib, required=True)
    parser.add_argument("--min-persistent-mib", type=positive_mib, required=True)
    parser.add_argument("--min-ram-mib", type=positive_mib, required=True)
    args = parser.parse_args()
    try:
        docker_path = docker_root()
        persistent = args.persistent_root
        docker_free = free_bytes(docker_path)
        persistent_free = free_bytes(persistent)
        shared = docker_path.stat().st_dev == persistent.stat().st_dev
        checks = [
            ("Docker disk", docker_free, args.min_docker_mib),
            ("Persistent disk", persistent_free, args.min_persistent_mib),
            ("Available RAM", available_memory(), args.min_ram_mib),
        ]
        if shared:
            checks.append((
                "Shared Docker and persistent disk",
                min(docker_free, persistent_free),
                args.min_docker_mib + args.min_persistent_mib,
            ))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Capacity check unavailable: {error}\n")
    failed = False
    for label, available, minimum in checks:
        passed = available >= minimum * MIB
        print(f"{label}: {available // MIB} MiB available, {minimum} MiB required ({'pass' if passed else 'fail'})")
        failed |= not passed
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
