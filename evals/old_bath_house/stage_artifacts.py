"""Stage the verified Meatling draft and acceptance proof in a new fixture root."""

import argparse
import json
from hashlib import sha256
from pathlib import Path
from uuid import UUID


def stage(export, digest, root, pins):
    data = export.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Meatling export checksum differs")
    files = json.loads(data)
    draft_id = str(UUID(pins["minion"]["draftId"]))
    draft_path = f"out/threat_drafts/{draft_id}.json"
    draft = files[draft_path]
    acceptance_path, = set(files) - {draft_path}
    acceptance = files[acceptance_path]
    operation = str(UUID(acceptance["operation_id"]))
    if (
        acceptance_path != f"out/statblock_acceptance_operations/{draft_id}/{operation}.json"
        or draft["draft_id"] != draft_id or draft["world_id"] != pins["worldId"]
        or draft["workflow_state"] != "mechanics_saved"
        or acceptance["source_draft_id"] != draft_id
        or acceptance["locator"] != pins["minion"]["originalLocator"]
    ):
        raise ValueError("Meatling acceptance proof differs from the fixture")
    files["out/threat_drafts/index.json"] = {
        "schema": "dmb_threat_draft_index_v1", "draft_ids": [draft_id], "archived_draft_ids": [],
    }
    root.mkdir(mode=0o700)
    for name, record in files.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x") as stream:
            json.dump(record, stream)
    return f"{draft['name']} Saved mechanics · draft {draft['version']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pins = json.loads(Path(__file__).with_name("source-pins.json").read_text())
    print(stage(args.export, args.sha256, args.output, pins))


if __name__ == "__main__":
    main()
