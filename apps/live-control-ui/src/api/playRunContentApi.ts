import { authenticatedApiFetch, LiveApiError } from "./liveApi";
import { validatePlayRunContent } from "../playSurface/playRunEffectiveContent";
import type { PlayRunContent, PlayRunContentCommitRequest } from "../playSurface/playRunContentTypes";

async function requestWorldRunContent(path: string, init: RequestInit = {}): Promise<unknown> {
  const { response } = await authenticatedApiFetch(path, { ...init, cache: "no-store" });
  let body: unknown;
  try { body = await response.json(); }
  catch { throw new LiveApiError("Session content response was not JSON.", response.status); }
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null && "detail" in body ? body.detail : null;
    throw new LiveApiError(typeof detail === "string" ? detail : "Session content could not be loaded.", response.status);
  }
  return body;
}

export async function getWorldPlayRunContent(runId: string, worldId: string): Promise<PlayRunContent> {
  const body = await requestWorldRunContent(`/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/content?world_id=${encodeURIComponent(worldId)}`);
  try { return await validatePlayRunContent(body, { runId, worldId }); }
  catch (error) { throw new LiveApiError(error instanceof Error ? error.message : "Invalid session content.", 0); }
}

export function getWorldPlayRunContentCommand(runId: string, worldId: string, commandId: string): Promise<unknown> {
  return requestWorldRunContent(`/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/content/commands/${encodeURIComponent(commandId)}?world_id=${encodeURIComponent(worldId)}`);
}

export function putWorldPlayRunContentCommand(runId: string, worldId: string, commandId: string, request: PlayRunContentCommitRequest): Promise<unknown> {
  return requestWorldRunContent(`/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/content/commands/${encodeURIComponent(commandId)}?world_id=${encodeURIComponent(worldId)}`, {
    method: "PUT",
    body: JSON.stringify(request),
  });
}
