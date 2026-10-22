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


export async function previewWorldCombatMechanics(worldId: string, selection: import('./combatTypes').CombatMechanicsSelection): Promise<import('./combatTypes').CombatMechanicsSnapshot> {
  return readJson(await fetchCombat(scopedPath(worldId, '/world-mechanics/preview'), {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(selection),
  }));
}
