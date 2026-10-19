import { authenticatedApiFetch, LiveApiError, listWorkspaceDocuments, getWorkspaceDocumentSnapshot, discardWorkspaceDocument, restoreWorkspaceDocument } from "../api/liveApi";

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { response } = await authenticatedApiFetch(path, { ...init, cache: "no-store" });
  let body: unknown;
  try { body = await response.json(); } catch { throw new LiveApiError("Trash response was not JSON. Reload to check its state.", response.status); }
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null && "detail" in body ? body.detail : null;
    throw new LiveApiError(typeof detail === "string" ? detail : "Trash could not be updated. Reload to check its state.", response.status);
  }
  return body as T;
}

export type WorkspaceTrashTarget = {
  kind: "document" | "session";
  id: string;
  title: string;
  surface: "build" | "plan" | "play";
  revision: number;
  content_revision?: number;
};
export type WorkspaceTrashItem = WorkspaceTrashTarget & { status: "active" | "trashed"; updated_at: string };
function admittedItem(value: unknown): value is WorkspaceTrashItem {
  if (!value || typeof value !== "object") return false;
  const item = value as WorkspaceTrashItem;
  return (item.kind === "document" || item.kind === "session") && typeof item.id === "string" && item.id.length > 0
    && typeof item.title === "string" && ["build", "plan", "play"].includes(item.surface)
    && ["active", "trashed"].includes(item.status) && Number.isInteger(item.revision) && item.revision > 0
    && typeof item.updated_at === "string" && (item.kind !== "session" || Number.isInteger(item.content_revision) && item.content_revision! >= 0);
}
export async function listWorkspaceTrash(worldId: string): Promise<WorkspaceTrashItem[]> {
  const response = await apiFetch<{ world_id: string; items: WorkspaceTrashItem[] }>(
    `/api/live/world-workspace/trash?world_id=${encodeURIComponent(worldId)}`,
  );
  if (response.world_id !== worldId || !Array.isArray(response.items) || !response.items.every(item => admittedItem(item) && item.status === "trashed")) throw new Error("Trash inventory does not match this World.");
  return response.items;
}
export async function changeWorkspaceTrash(worldId: string, target: WorkspaceTrashTarget, action: "trash" | "restore"): Promise<WorkspaceTrashItem> {
  const family = target.kind === "session" ? "sessions" : "documents";
  const result = await apiFetch<WorkspaceTrashItem>(
    `/api/live/world-workspace/${family}/${encodeURIComponent(target.id)}/${action}?world_id=${encodeURIComponent(worldId)}`,
    { method: "POST", body: JSON.stringify({ expected_revision: target.revision,
      ...(target.kind === "session" ? { expected_content_revision: target.content_revision } : {}) }) },
  );
  if (!admittedItem(result) || result.id !== target.id || result.kind !== target.kind || result.status !== (action === "trash" ? "trashed" : "active")) {
    throw new Error("The lifecycle response does not match the selected item. Reload to check its state.");
  }
  return result;
}

/** Campaign plans retain their existing ownership; never infer a World from campaign names. */
function campaignPlanItem(record: import("../api/types").WorkspaceDocumentRecord, campaignId: string): WorkspaceTrashItem {
  if (record.kind !== "plan" || record.world_id || record.campaign_id !== campaignId || !["active", "discarded"].includes(record.status)) throw new Error("Plan does not belong to this campaign.");
  const item: WorkspaceTrashItem = {kind:"document",id:record.document_id,title:record.title,surface:"plan",revision:record.revision,
    status:record.status === "discarded" ? "trashed" : "active",updated_at:record.updated_at};
  if (!admittedItem(item)) throw new Error("Campaign Plan lifecycle response is invalid.");
  return item;
}
export async function listCampaignPlanTrash(campaignId: string): Promise<WorkspaceTrashItem[]> {
  const result = await listWorkspaceDocuments({campaign_id:campaignId,kind:"plan",status:"discarded"});
  return result.records.map(record => { const item=campaignPlanItem(record,campaignId); if(item.status!=="trashed")throw new Error("Campaign Trash inventory changed. Reload it.");return item; });
}
export async function changeCampaignPlanTrash(campaignId: string, target: WorkspaceTrashTarget, action: "trash" | "restore"): Promise<WorkspaceTrashItem> {
  if(target.kind!=="document" || target.surface!=="plan") throw new Error("Only campaign Plans can use this Trash.");
  const snapshot=await getWorkspaceDocumentSnapshot(target.id);
  const current=campaignPlanItem(snapshot.record,campaignId);
  if(current.id!==target.id || current.revision!==target.revision || current.status!==(action==="trash"?"active":"trashed")) throw new Error("The Plan changed. Reload before trying again.");
  const record=await (action==="trash"?discardWorkspaceDocument:restoreWorkspaceDocument)(target.id,{expected_revision:target.revision});
  const result=campaignPlanItem(record,campaignId);
  if(result.id!==target.id || result.status!==(action==="trash"?"trashed":"active")) throw new Error("The lifecycle response does not match this Plan. Reload to check its state.");
  return result;
}
