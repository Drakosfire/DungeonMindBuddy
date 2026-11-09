"""Run the exact installed DungeonMind pin's canonical migrations, never a fake schema."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess


def installed_core_pin() -> str:
    metadata = importlib.metadata.distribution("dungeonmind")
    direct = json.loads(metadata.read_text("direct_url.json"))
    if direct["url"] != "https://github.com/Drakosfire/DungeonMind.git":
        raise ValueError("unexpected DungeonMind source owner")
    pin = direct["vcs_info"]["commit_id"]
    if len(pin) != 40 or any(char not in "0123456789abcdef" for char in pin):
        raise ValueError("DungeonMind source must have an exact commit")
    return pin


def prepare_checkout(destination: Path) -> str:
    pin = installed_core_pin()
    if destination.exists():
        raise ValueError("canonical migration checkout must be a fresh task-owned path")
    subprocess.run(["git", "clone", "--no-checkout", "--filter=blob:none", "https://github.com/Drakosfire/DungeonMind.git", str(destination)], check=True)
    subprocess.run(["git", "-C", str(destination), "checkout", "--detach", pin], check=True)
    actual = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
    if actual != pin:
        raise ValueError("canonical migrations do not match installed Core")
    return pin


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps({"core_source_sha": prepare_checkout(args.destination)}))
