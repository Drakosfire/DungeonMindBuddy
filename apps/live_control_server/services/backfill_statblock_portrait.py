"""Operator backfill for one exact legacy published mechanics revision."""
import argparse
import os
from uuid import NAMESPACE_URL, UUID, uuid5

from application_state.mechanics_revisions.portraits import retain_portrait
from application_state.mechanics_revisions.types import PDF_REVIEW_PROVENANCE
from application_state.unit_of_work import unit_of_work

from .statblock_saved_revision import open_version


def backfill(root, *, world_id, draft_id, revision_id, review_dsn):
    packet = open_version(root, world_id=world_id, draft_id=str(draft_id), revision_id=revision_id)
    through = (packet["resource"].get("provenance") or {}).get("accepted_through") or {}
    source = through.get(PDF_REVIEW_PROVENANCE)
    if not isinstance(source, dict) or source.get("world_id") != world_id:
        raise ValueError("Saved revision has no exact World PDF provenance")
    review_id = UUID(source["review_id"])
    if uuid5(NAMESPACE_URL, f"dungeonbuddy:pdf-review:{world_id}:{review_id}") != draft_id:
        raise ValueError("Saved revision provenance belongs to a different draft")
    with unit_of_work(review_dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        row = conn.execute(
            """SELECT revision, payload FROM public.pdf_statblock_review
               WHERE world_id = %s AND review_id = %s""",
            (world_id, review_id),
        ).fetchone()
    if not row or row[0] != source["revision"] or row[1]["regions"] != source["regions"]:
        raise ValueError("Legacy review does not match the exact saved revision")
    portrait = (row[1].get("artwork") or {}).get("jpeg_base64")
    if not portrait:
        raise ValueError("Legacy review has no retained portrait")
    retain_portrait(world_id=world_id, draft_id=draft_id, revision_id=revision_id, jpeg_base64=portrait)


def main():
    from apps.live_control_server.routes.statblock_candidates import repo_root, statblock_data_root

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world_id")
    parser.add_argument("draft_id", type=UUID)
    parser.add_argument("revision_id")
    args = parser.parse_args()
    backfill(
        statblock_data_root(repo_root()), world_id=args.world_id, draft_id=args.draft_id,
        revision_id=args.revision_id, review_dsn=os.environ["DMB_APP_MIGRATION_DATABASE_URL"],
    )
    print("SAVED_STATBLOCK_PORTRAIT_BACKFILLED")


if __name__ == "__main__":
    main()
