"""Resume exact, World-owned canonical deletion and local payload cleanup."""

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from application_state.errors import ApplicationStateConflictError
from application_state.mechanics_revisions import purge
from apps.live_control_server.integrations.dungeonmind_statblocks.client import build_statblock_v1_client
from apps.live_control_server.services.statblock_acceptance_reconciliation import remove_purged_acceptance
from apps.live_control_server.services.statblock_saved_revision import plan_statblock_purge
from apps.live_control_server.services.threat_draft_store import (
    ensure_statblock_purge_fence,
    locked_statblock_purge_owner,
)


def delete_saved_statblock(
    root: Path,
    *,
    world_id: str,
    draft_id: UUID,
    expected_version: int,
    authorize: Callable[[], object],
) -> None:
    authorize()
    receipt = purge.find_receipt(world_id=world_id, draft_id=draft_id)
    if receipt is not None:
        target, complete = receipt
        if target.draft_version != expected_version:
            raise ApplicationStateConflictError("Saved statblock changed before deletion")
        if complete:
            return
        authorize()
        ensure_statblock_purge_fence(
            root, world_id=target.world_id, draft_id=str(target.draft_id),
            expected_version=target.draft_version, statblock_id=target.statblock_id,
        )
    else:
        plan = plan_statblock_purge(
            root, world_id=world_id, draft_id=str(draft_id), expected_version=expected_version,
        )
        tip = plan.lineage[-1]
        target = purge.PurgeTarget(
            tip.statblock_id, plan.world_id, UUID(plan.draft_id), plan.draft_version, tip.revision_id,
        )
        authorize()
        with locked_statblock_purge_owner(
            root, world_id=target.world_id, draft_id=str(target.draft_id),
            expected_version=target.draft_version, statblock_id=target.statblock_id,
        ) as persist_fence:
            def authorize_and_fence() -> None:
                authorize()
                persist_fence()

            if purge.claim(target, authorize=authorize_and_fence):
                return

    authorize()
    client = build_statblock_v1_client()
    try:
        client.purge_statblock_revisions(target.statblock_id, target.expected_revision_id)
    finally:
        client.close()

    authorize()
    remove_purged_acceptance(
        root, world_id=target.world_id, draft_id=str(target.draft_id),
        expected_version=target.draft_version, statblock_id=target.statblock_id,
    )
    purge.settle_after_cleanup(target, authorize=authorize)
