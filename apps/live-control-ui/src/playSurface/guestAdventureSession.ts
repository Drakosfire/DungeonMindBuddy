import {getWorldOwnedPlanCommittedRevision, listWorldOwnedPlans, putWorldPlayRun} from '../api/liveApi';
import {assertSessionOutcome, previewSession} from '../combat/runEncountersApi';
import type {AnyPlayRunRecord} from '../api/types';

/** Open or create the one guest-owned session. The session credential identifies its World. */
export async function guestAdventureSession(worldId:string, runs:AnyPlayRunRecord[], isCurrent:()=>boolean):Promise<string|null> {
  const match = /^guest-([0-9a-f]{32})$/.exec(worldId);
  if (!match) return null;
  const inventory = await listWorldOwnedPlans(worldId);
  if (!isCurrent() || inventory.world_id !== worldId) return null;
  const plans = inventory.records.filter(p => p.world_id === worldId && p.campaign_id === null && p.kind === 'plan'
    && p.status === 'active' && p.title === "Sizzek's Apprentice");
  if (plans.length !== 1) return null;
  const plan = plans[0];
  const existing = runs.filter(r => r.schema_version === 'dmb_world_play_run_record_v2'
    && r.world_id === worldId && r.playable_artifact_id === plan.document_id)
    .sort((a,b) => b.updated_at.localeCompare(a.updated_at))[0];
  if (existing) return existing.run_id;
  const committed = await getWorldOwnedPlanCommittedRevision(plan.document_id);
  if (!isCurrent()) return null;
  if (committed.world_id !== worldId || committed.document_id !== plan.document_id || committed.kind !== 'plan'
      || committed.status !== 'active' || committed.has_divergent_working_copy) throw new Error('The prepared Plan is not ready to play.');
  const source = {playable_artifact_id: committed.document_id, expected_playable_revision: committed.revision_n,
    expected_playable_work_revision_id: committed.work_revision_id, expected_playable_content_sha256: committed.content_sha256};
  const preview = await previewSession(worldId, source, 'scene:contract');
  if (!isCurrent()) return null;
  const request = preview.request;
  if (request.schema_version !== 'dmb_world_session_create_v1' || request.entry_scene_id !== 'scene:contract'
      || request.playable_artifact_id !== source.playable_artifact_id || request.expected_playable_revision !== source.expected_playable_revision
      || request.expected_playable_work_revision_id !== source.expected_playable_work_revision_id
      || request.expected_playable_content_sha256 !== source.expected_playable_content_sha256) throw new Error('The prepared session did not match the Plan.');
  const hex = match[1];
  const runId = `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  const result = await putWorldPlayRun(runId, worldId, request);
  assertSessionOutcome(result, worldId, runId, request);
  return isCurrent() ? runId : null;
}
