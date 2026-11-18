"""Retire one recorded Buddy release after successful cutover."""
import argparse
import json
import re
import subprocess


def docker(*args):
    return subprocess.check_output(("docker", *args), text=True).strip()


def retire(project, tag, serving, rollback, *, apply=False):
    containers = docker("ps", "-aq", "--no-trunc").splitlines()
    records = json.loads(docker("container", "inspect", *containers)) if containers else []

    def belongs(record):
        labels = record["Config"]["Labels"] or {}
        return (
            labels.get("com.docker.compose.project") == project
            and labels.get("com.docker.compose.service") == "buddy"
        )

    active = [record for record in records if belongs(record) and record["State"]["Running"]]
    if len(active) != 1 or active[0]["Image"] != serving or active[0]["State"].get("Health", {}).get("Status") != "healthy":
        raise ValueError("Expected one healthy serving Buddy container at the supplied image ID")
    docker("image", "inspect", rollback)
    if tag not in docker("image", "ls", "--format", "{{.Repository}}:{{.Tag}}", "dungeonmindbuddy").splitlines():
        print(f"Already retired: {tag}")
        return
    image = docker("image", "inspect", "--format", "{{.Id}}", tag)
    if image in {serving, rollback}:
        raise ValueError("The candidate is the serving or rollback image")
    consumers = [record for record in records if record["Image"] == image]
    if any(not belongs(record) or record["State"]["Status"] not in {"exited", "created"} for record in consumers):
        raise ValueError("The candidate has a running or unrelated container")
    print(f"{'Retiring' if apply else 'Would retire'} {tag} ({image}) and {len(consumers)} stopped Buddy containers")
    if not apply:
        return
    print(docker("system", "df"))
    for record in consumers:
        docker("container", "rm", record["Id"])
    docker("image", "rm", "--no-prune", tag)
    print(docker("system", "df"))
    subprocess.run(["free", "-h"], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--retired-tag", required=True)
    parser.add_argument("--serving-image", required=True)
    parser.add_argument("--rollback-image", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"dungeonmindbuddy:[0-9a-f]{40}", args.retired_tag):
        parser.error("Expected a Buddy release tag with a full commit SHA")
    if any(not re.fullmatch(r"sha256:[0-9a-f]{64}", value) for value in (args.serving_image, args.rollback_image)):
        parser.error("Expected full SHA256 image IDs")
    try:
        retire(args.project, args.retired_tag, args.serving_image, args.rollback_image, apply=args.apply)
    except (ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Retirement stopped: {error}\n")


if __name__ == "__main__":
    main()
