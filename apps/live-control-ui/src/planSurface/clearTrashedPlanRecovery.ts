export type TrashedPlanCacheBasis = {document_id:string; revision:number; title:string; markdown:string; edit_generation:number};
/** Retire only the unchanged clean cache after the server confirms Trash. */
export function clearTrashedPlanRecovery(worldId: string, expected: TrashedPlanCacheBasis): boolean {
  const key=`dmb:world-plan-local-draft:v2:${worldId}`;
  try {
    const raw=localStorage.getItem(key);
    if (!raw) return false;
    const draft=JSON.parse(raw);
    if (draft?.schema_version !== "dmb_plan_promotion_recovery_v2" || draft.scope_mode !== "world" || draft.world_id !== worldId
      || draft.document_id !== expected.document_id || draft.revision !== expected.revision || draft.title !== expected.title
      || draft.markdown !== expected.markdown || (draft.edit_generation ?? 0) !== expected.edit_generation
      || draft.pending_write || draft.create_uncertain || draft.uncertain_create_draft) return false;
    if (localStorage.getItem(key)!==raw) return false;
    localStorage.removeItem(key);
    return true;
  } catch { return false; }
}
