import { authenticatedApiFetch, LiveApiError } from "./liveApi";
import { validatePlayRunContent } from "../playSurface/playRunEffectiveContent";
import type { PlayRunContent } from "../playSurface/playRunContentTypes";

export async function getWorldPlayRunContent(runId: string, worldId: string): Promise<PlayRunContent> {
  const { response } = await authenticatedApiFetch(`/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/content?world_id=${encodeURIComponent(worldId)}`, { cache: "no-store" });
  let body: unknown;
  try { body = await response.json(); }
  catch { throw new LiveApiError("Session content response was not JSON.", response.status); }
  if (!response.ok) {
    const detail = typeof body === "object" && body !== null && "detail" in body ? body.detail : null;
    throw new LiveApiError(typeof detail === "string" ? detail : "Session content could not be loaded.", response.status);
  }
  try { return await validatePlayRunContent(body, { runId, worldId }); }
  catch (error) { throw new LiveApiError(error instanceof Error ? error.message : "Invalid session content.", 0); }
}
