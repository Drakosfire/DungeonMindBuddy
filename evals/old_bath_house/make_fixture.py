"""Compose a run manifest from the pinned source and scoped fixture exports."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from .isolation import source_fixture_digest
from .restore_app import media_rows, revision_lineage


def read(path):
    body = path.read_bytes()
    return json.loads(body), sha256(body).hexdigest()


def build(pins, *, exports, origin, state, isolation):
    rows, rows_digest = read(exports / "old-bath-house-app-rows.json")
    assets_path = exports / "old-bath-house-assets.json"
    assets, assets_digest = read(assets_path)
    lineage_path = exports / "meatling-lineage.json"
    _, lineage_digest = read(lineage_path)
    _, acceptance_digest = read(exports / "meatling-draft.json")
    _, binding_digest = read(exports / "elderwyld-world-binding.json")
    media = media_rows(assets_path, assets_digest, pins)
    revision_lineage(lineage_path, lineage_digest, pins)
    fixture_digest = source_fixture_digest(pins, {
        "app_rows": rows_digest, "assets": assets_digest, "meatling_lineage": lineage_digest,
        "meatling_acceptance": acceptance_digest, "world_binding": binding_digest,
    })
    doc, = rows["content.work_object"]
    if doc["work_object_id"] != pins["documentId"] or doc["world_id"] != pins["worldId"]:
        raise ValueError("Plan export differs from the source pin")
    revision, = (row for row in rows["content.work_revision"]
                 if row["work_revision_id"] == doc["current_revision_id"])
    plan_pin = {key: revision[key] for key in ("revision_n", "work_revision_id", "content_sha256")}
    boss = dict(pins["boss"])
    boss_asset, = (row for row in media["media.asset"] if row["asset_id"] == boss["assetId"])
    provenance = boss_asset["provenance"]
    prompt = provenance.get("prompt") or provenance.get("prompt_text")
    if not prompt:
        raise ValueError("Saved boss portrait is missing the library prompt")
    boss["libraryLabel"] = prompt + " · Saved"

    minion = dict(pins["minion"])
    draft_export, _ = read(exports / "meatling-draft.json")
    draft = draft_export[f"out/threat_drafts/{minion['draftId']}.json"]
    minion["savedMechanicsLabel"] = f"{draft['name']} Saved mechanics · draft {draft['version']}"
    minion_revision, = (row for row in assets["revisions"] if row["revision_id"] == minion["locator"]["revision_id"])
    minion["assetBindings"] = minion_revision["asset_bindings"]
    return dict(
        pins, schema="dmb_old_bath_house_benchmark_v1", sourceFixtureDigest=fixture_digest,
        planPin=plan_pin, boss=boss, minion=minion, origin=origin,
        runtime_state=str(state.resolve(strict=True)), isolation=isolation,
    )


def with_live_grounding(data, grounding, grounding_sha256, core_head):
    from .live_sources import live_manifest, read_grounding

    read_grounding(grounding, grounding_sha256)
    live = live_manifest(core_head)
    digest = source_fixture_digest(live, {
        "pinned_assets": data["sourceFixtureDigest"],
        "grounding": grounding_sha256,
        "portrait_handoff": "preview_then_bind_saved_portrait",
    })
    return dict(data, live=live, sourceFixtureDigest=digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", required=True, type=Path)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--isolation", required=True, type=Path)
    parser.add_argument("--live-grounding", type=Path)
    parser.add_argument("--live-grounding-sha256")
    parser.add_argument("--live-core-head")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    pins, _ = read(Path(__file__).with_name("source-pins.json"))
    isolation, _ = read(args.isolation)
    data = build(pins, exports=args.exports, origin=args.origin, state=args.state, isolation=isolation)
    live_args = (args.live_grounding, args.live_grounding_sha256, args.live_core_head)
    if any(live_args):
        if not all(live_args):
            parser.error("Live manifest requires grounding export, its SHA-256 and the Graph head")
        data = with_live_grounding(data, *live_args)
    body = json.dumps(data, sort_keys=True, indent=2).encode() + b"\n"
    with args.output.open("xb") as stream:
        stream.write(body)
    print(sha256(body).hexdigest())


if __name__ == "__main__":
    main()
