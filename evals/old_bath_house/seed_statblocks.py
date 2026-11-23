"""Seed exact saved revisions in a disposable statblock Firestore namespace."""

import argparse
import json
import os
import re
from hashlib import sha256
from pathlib import Path


def seed(path, digest, project, pins, lineage, *, original=None):
    endpoint = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
    if not re.fullmatch(r"127\.0\.0\.1:[0-9]+", endpoint):
        raise ValueError("Statblock seeding requires a loopback Firestore emulator")
    if not re.fullmatch(r"buddy-bath-fixture-[a-f0-9]{12}", project):
        raise ValueError("Statblock seeding requires a dedicated benchmark project")
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Scoped statblock export checksum differs")
    from google.auth.credentials import AnonymousCredentials
    from google.cloud.firestore import Client
    from statblocks_v1.domain.resources import StatblockResourceV1, StatblockRevisionResourceV1
    from statblocks_v1.infrastructure.firestore_repositories import STATBLOCKS_COLLECTION, _dump

    boss = pins["boss"]
    supplied = [*json.loads(data)["revisions"], lineage["original"]]
    if original is not None:
        supplied.append(original)
    revisions = {
        (row["statblock_id"], row["revision_id"]): StatblockRevisionResourceV1.model_validate(row)
        for row in supplied
    }
    expected = (
        boss["baseLocator"], boss["publishedPortraitLocator"],
        pins["minion"]["originalLocator"], pins["minion"]["locator"],
    )
    if original is not None:
        from .live_sources import ORIGINAL_MEAT_MIND

        original_pin = dict(zip(("statblock_id", "revision_id", "definition_digest"), ORIGINAL_MEAT_MIND))
        expected = (*expected, original_pin)
    if len(supplied) != len(expected) or len(revisions) != len(expected):
        raise ValueError("Unexpected revision inventory")
    for locator in expected:
        revision = revisions[locator["statblock_id"], locator["revision_id"]]
        if revision.definition_digest != locator["definition_digest"]:
            raise ValueError("Exact statblock digest differs")
    for locator, role in ((boss["publishedPortraitLocator"], "boss"), (pins["minion"]["locator"], "minion")):
        revision = revisions[locator["statblock_id"], locator["revision_id"]]
        urls = [value["asset"]["url"] for value in revision.model_dump(mode="json")["asset_bindings"]
                if value["role"] == "portrait"]
        if urls != [pins[role]["imageUrl"]]:
            raise ValueError("Exact statblock portrait differs")

    client = Client(project=project, credentials=AnonymousCredentials())
    batch = client.batch()
    collection = client.collection(STATBLOCKS_COLLECTION)
    heads = (boss["baseLocator"], pins["minion"]["locator"])
    if original is not None:
        heads = (*heads, original_pin)
    for locator in heads:
        revision = revisions[locator["statblock_id"], locator["revision_id"]]
        document = collection.document(revision.statblock_id)
        batch.create(document, _dump(StatblockResourceV1(
            statblock_id=revision.statblock_id, latest_revision_id=revision.revision_id,
            created_at=revision.created_at, created_by="old-bath-house-fixture",
        )))
    for (statblock_id, revision_id), revision in revisions.items():
        batch.create(collection.document(statblock_id).collection("revisions").document(revision_id), _dump(revision))
    batch.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--assets-sha256", required=True)
    parser.add_argument("--emulator-project", required=True)
    parser.add_argument("--lineage", type=Path, required=True)
    parser.add_argument("--lineage-sha256", required=True)
    parser.add_argument("--live-grounding", type=Path)
    parser.add_argument("--live-grounding-sha256")
    args = parser.parse_args()
    pins = json.loads(Path(__file__).with_name("source-pins.json").read_text())
    from .restore_app import revision_lineage

    lineage = revision_lineage(args.lineage, args.lineage_sha256, pins)
    if bool(args.live_grounding) != bool(args.live_grounding_sha256):
        parser.error("--live-grounding and --live-grounding-sha256 must be supplied together")
    original = None
    if args.live_grounding:
        from .live_sources import read_grounding

        original = read_grounding(args.live_grounding, args.live_grounding_sha256)["statblock_revision"]
    seed(args.assets, args.assets_sha256, args.emulator_project, pins, lineage, original=original)


if __name__ == "__main__":
    main()
