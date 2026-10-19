import { authenticatedApiFetch, LiveApiError } from "../api/liveApi";

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
