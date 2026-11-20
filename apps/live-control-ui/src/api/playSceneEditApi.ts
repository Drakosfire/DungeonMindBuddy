import { authenticatedApiFetch, LiveApiError } from "./liveApi";
import type { WorldPlayContentBasis } from "./types";
import type { PlayRunContentOrigin } from "../playSurface/playRunContentTypes";

export interface PlaySceneEditRequest {
  schema_version: "dmb_play_scene_edit_request_v1";
  run_revision: number; content_basis: WorldPlayContentBasis; scene_id: string; instruction: string;
}
export interface PlaySceneEditRecord {
  schema_version: "dmb_play_scene_edit_proposal_v1";
  world_id: string; run_id: string; proposal_id: string; instruction: string;
  status: "pending" | "ready" | "failed"; failure_code: string | null; created_at: string; updated_at: string;
  basis: { run_revision: number; scene_id: string; content_basis: WorldPlayContentBasis;
    scene_note_sha256: string | null; origin: PlayRunContentOrigin };
  result: { schema_version: "dmb_play_scene_edit_result_v1"; before_markdown: string; replacement_markdown: string; candidate_markdown: string; candidate_sha256: string;
    body_start_utf8: number; body_end_utf8: number; summary: string; assumptions: string[];
    model: string; model_observed: boolean; model_latency_ms: number; wall_latency_ms: number } | null;
}
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const hash = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
const uuid = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(v);
export function validatePlaySceneEdit(value: unknown, worldId: string, runId: string): PlaySceneEditRecord {
  if (!object(value) || value.schema_version !== "dmb_play_scene_edit_proposal_v1" || value.world_id !== worldId || value.run_id !== runId
    || !uuid(value.proposal_id) || typeof value.instruction !== "string" || !["pending", "ready", "failed"].includes(String(value.status))
    || !object(value.basis) || !Number.isSafeInteger(value.basis.run_revision) || Number(value.basis.run_revision) < 1
    || typeof value.basis.scene_id !== "string" || !/^scene:[a-z0-9][a-z0-9._-]{0,127}$/.test(value.basis.scene_id)
    || !object(value.basis.content_basis) || !Number.isSafeInteger(value.basis.content_basis.edition_revision)
    || Number(value.basis.content_basis.edition_revision) < 0 || !hash(value.basis.content_basis.content_sha256)
    || (value.basis.content_basis.edition_revision === 0 ? value.basis.content_basis.edition_revision_id !== null : !uuid(value.basis.content_basis.edition_revision_id))
    || !object(value.basis.origin) || !uuid(value.basis.origin.playable_artifact_id) || !uuid(value.basis.origin.playable_work_revision_id)
    || !hash(value.basis.origin.playable_content_sha256) || !Number.isSafeInteger(value.basis.origin.playable_revision)
    || Number(value.basis.origin.playable_revision) < 1
    || (value.basis.scene_note_sha256 !== null && !hash(value.basis.scene_note_sha256))) throw new TypeError("Scene proposal has an invalid target or saved basis.");
  if (value.status === "ready") {
    const r = value.result;
    if (!object(r) || r.schema_version !== "dmb_play_scene_edit_result_v1" || !hash(r.candidate_sha256) || ![r.before_markdown, r.replacement_markdown, r.candidate_markdown, r.summary, r.model].every(x => typeof x === "string")
      || !Number.isSafeInteger(r.body_start_utf8) || !Number.isSafeInteger(r.body_end_utf8) || Number(r.body_start_utf8) < 0 || Number(r.body_end_utf8) < Number(r.body_start_utf8)
      || !Array.isArray(r.assumptions) || !r.assumptions.every(x => typeof x === "string")) throw new TypeError("Scene proposal has no valid review result.");
  } else if (value.result !== null) throw new TypeError("Unfinished scene proposal contains a result.");
  return value as unknown as PlaySceneEditRecord;
}
function path(world: string, run: string, id?: string) {
  return `/api/live/world-play-runs/v2/${encodeURIComponent(run)}/content/proposals${id ? `/${encodeURIComponent(id)}` : ""}?world_id=${encodeURIComponent(world)}`;
}
async function call(path: string, init: RequestInit = {}) {
  const { response } = await authenticatedApiFetch(path, { ...init, cache: "no-store" });
  let body: unknown;
  try { body = await response.json(); } catch { throw new LiveApiError("Scene proposal response was not JSON.", response.status); }
  if (!response.ok) throw new LiveApiError(object(body) && typeof body.detail === "string" ? body.detail : "Scene proposal could not be loaded.", response.status);
  return body;
}
export async function listPlaySceneEdits(world: string, run: string): Promise<PlaySceneEditRecord[]> {
  const body = await call(path(world, run));
  if (!object(body) || !Array.isArray(body.proposals) || body.proposals.length > 20) throw new TypeError("Scene proposal list is invalid.");
  return body.proposals.map(item => validatePlaySceneEdit(item, world, run));
}
export async function proposePlaySceneEdit(world: string, run: string, id: string, request: PlaySceneEditRequest) {
  return validatePlaySceneEdit(await call(path(world, run, id), { method: "POST", body: JSON.stringify(request) }), world, run);
}
