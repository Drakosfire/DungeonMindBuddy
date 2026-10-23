import { authenticatedApiFetch } from "../api/liveApi";
import type {
  AddGeneratedStatblockRequest,
  AddGeneratedStatblockResponse,
  CombatEncounterDraft,
  CombatEncounterRecord,
  CreateCombatEncounterRequest,
} from "./combatTypes";

async function fetchCombat(path: string, init?: RequestInit): Promise<Response> {
  return (await authenticatedApiFetch(path, init)).response;
}

async function readJson<T>(response: Response): Promise<T> {
  const body = await response.text();
  let parsed: unknown;
  try {
    parsed = body ? JSON.parse(body) : null;
  } catch {
    throw new Error(`Combat API returned invalid JSON (HTTP ${response.status}).`);
  }
  if (!response.ok) {
    const detail = typeof parsed === "object" && parsed !== null && "detail" in parsed
      ? (parsed as { detail?: unknown }).detail
      : null;
    throw new Error(typeof detail === "string" ? detail : `Combat API request failed (HTTP ${response.status}).`);
  }
  return parsed as T;
}

function scopedPath(worldId: string, path = ""): string {
  const query = new URLSearchParams({ world_id: worldId });
  return `/api/live/combat/encounters${path}?${query.toString()}`;
}

export async function listWorldCombatEncounters(worldId: string): Promise<CombatEncounterRecord[]> {
  return readJson<CombatEncounterRecord[]>(await fetchCombat(scopedPath(worldId)));
}

export async function createWorldCombatEncounter(
  worldId: string,
  request: CreateCombatEncounterRequest,
): Promise<CombatEncounterRecord> {
  return readJson<CombatEncounterRecord>(await fetchCombat(scopedPath(worldId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  }));
}

export async function getWorldCombatEncounter(
  worldId: string,
  encounterId: string,
): Promise<CombatEncounterRecord> {
  return readJson<CombatEncounterRecord>(await fetchCombat(scopedPath(worldId, `/${encodeURIComponent(encounterId)}`)));
}

export async function saveWorldCombatEncounter(
  worldId: string,
  encounterId: string,
  expectedRevision: number,
  draft: CombatEncounterDraft,
): Promise<CombatEncounterRecord> {
  return readJson<CombatEncounterRecord>(await fetchCombat(scopedPath(worldId, `/${encodeURIComponent(encounterId)}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expected_revision: expectedRevision, draft }),
  }));
}

export async function addGeneratedStatblockToEncounter(
  worldId: string,
  encounterId: string,
  artifactId: string,
  request: AddGeneratedStatblockRequest,
): Promise<AddGeneratedStatblockResponse> {
  const path = `/${encodeURIComponent(encounterId)}/statblocks/${encodeURIComponent(artifactId)}`;
  return readJson<AddGeneratedStatblockResponse>(await fetchCombat(scopedPath(worldId, path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  }));
}


export async function previewWorldCombatMechanics(worldId: string, selection: import('./combatTypes').CombatMechanicsSelection): Promise<import('./combatTypes').AssociatedCombatMechanicsSnapshot> {
  return readJson(await fetchCombat(scopedPath(worldId, '/world-mechanics/preview'), {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(selection),
  }));
}


export async function previewAcceptedCombatMechanics(worldId: string, selection: import('./combatTypes').AcceptedCombatMechanicsSelection): Promise<import('./combatTypes').AcceptedCombatMechanicsSnapshot> {
  return readJson(await fetchCombat(scopedPath(worldId, '/accepted-mechanics/preview'), {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(selection),
  }));
}

/** Page the existing saved-draft catalog; loading this list never reads DMS. */
export async function listAcceptedCombatMechanics(worldId: string, offset = 0): Promise<{
  choices: import('./combatTypes').AcceptedCombatMechanicsChoice[]; nextOffset: number | null;
}> {
  const query = new URLSearchParams({world_id: worldId, limit: '20', offset: String(offset)});
  const page = await readJson<{drafts: {schema: string; draft_id: string; version: number; world_id: string | null; name: string; workflow_state: string}[]; total: number; limit: number; offset: number}>(
    await fetchCombat(`/api/live/threat-drafts?${query}`));
  if (page.drafts.some(draft => draft.world_id !== worldId)) throw new Error('Saved mechanics belong to another World.');
  return {choices: page.drafts.filter(draft => draft.schema === 'dmb_threat_draft_summary_v2' && draft.workflow_state === 'mechanics_saved')
    .map(draft => ({draft_id: draft.draft_id, draft_version: draft.version, name: draft.name})),
    nextOffset: page.offset + page.limit < page.total ? page.offset + page.limit : null};
}

export async function previewSavedCombatMechanics(worldId:string,draftId:string,locator:import('./combatTypes').SavedCombatMechanicsSnapshot['locator']):Promise<import('./combatTypes').MechanicsAdoptionPreview> {
  return readJson(await fetchCombat(scopedPath(worldId,'/saved-mechanics/preview'),{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({draft_id:draftId,locator}),
  }));
}
export async function adoptCombatMechanics(worldId:string,encounterId:string,request:import('./combatTypes').AdoptMechanicsRequest,cancel=false):Promise<import('./combatTypes').MechanicsAdoptionOutcome> {
  return readJson(await fetchCombat(scopedPath(worldId,`/${encodeURIComponent(encounterId)}/mechanics-adoptions${cancel?':cancel':''}`),{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),
  }));
}
