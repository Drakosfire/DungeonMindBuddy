export const SESSION_SCHEMA = "dmb_threat_publication_workbench_session_v1" as const;

export const THREAT_PUBLICATION_SESSION_PREFIX = "dmb.statblock.threat-publication.v1:";

export type ThreatPublicationSessionStage =
  | "operation"
  | "identity"
  | "proposal"
  | "commit";

const STAGES: readonly ThreatPublicationSessionStage[] = [
  "operation",
  "identity",
  "proposal",
  "commit",
];

export interface ThreatPublicationWorkbenchSessionV1 {
  schema: typeof SESSION_SCHEMA;
  draft_id: string;
  draft_version: number;
  operation_id: string;
  resolution_id: string | null;
  proposal_id: string | null;
  commit_id: string | null;
  stage: ThreatPublicationSessionStage;
  updated_at: string;
}


let corruptStorageWarned = false;

function warnCorruptStorageOnce(message: string): void {
  if (corruptStorageWarned) return;
  corruptStorageWarned = true;
  console.warn(message);
}

export function threatPublicationSessionKey(draftId: string): string {
  return `${THREAT_PUBLICATION_SESSION_PREFIX}${draftId.trim()}`;
}

function isNullableId(value: unknown): value is string | null {
  return value === null || (typeof value === "string" && value.length > 0);
}

function isStage(value: unknown): value is ThreatPublicationSessionStage {
  return typeof value === "string" && (STAGES as readonly string[]).includes(value);
}

function validateSessionRecord(
  value: unknown,
  expectedDraftId?: string,
): ThreatPublicationWorkbenchSessionV1 | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;

  const record = value as Record<string, unknown>;
  if (record.schema !== SESSION_SCHEMA) return null;

  if (typeof record.draft_id !== "string" || !record.draft_id.trim()) return null;
  if (expectedDraftId != null && record.draft_id.trim() !== expectedDraftId.trim()) {
    return null;
  }

  if (
    typeof record.draft_version !== "number" ||
    !Number.isFinite(record.draft_version) ||
    record.draft_version < 1
  ) {
    return null;
  }

  if (typeof record.operation_id !== "string" || !record.operation_id.trim()) return null;
  if (!isNullableId(record.resolution_id)) return null;
  if (!isNullableId(record.proposal_id)) return null;
  if (!isNullableId(record.commit_id)) return null;
  if (!isStage(record.stage)) return null;
  if (typeof record.updated_at !== "string" || !record.updated_at.trim()) return null;

  return {
    schema: SESSION_SCHEMA,
    draft_id: record.draft_id.trim(),
    draft_version: record.draft_version,
    operation_id: record.operation_id.trim(),
    resolution_id: record.resolution_id,
    proposal_id: record.proposal_id,
    commit_id: record.commit_id,
    stage: record.stage,
    updated_at: record.updated_at.trim(),
  };
}

function toPointerOnlySession(
  session: ThreatPublicationWorkbenchSessionV1,
): ThreatPublicationWorkbenchSessionV1 {
  return {
    schema: SESSION_SCHEMA,
    draft_id: session.draft_id.trim(),
    draft_version: session.draft_version,
    operation_id: session.operation_id.trim(),
    resolution_id: session.resolution_id,
    proposal_id: session.proposal_id,
    commit_id: session.commit_id,
    stage: session.stage,
    updated_at: session.updated_at.trim(),
  };
}

export function parseThreatPublicationSession(
  raw: unknown,
): ThreatPublicationWorkbenchSessionV1 | null {
  return validateSessionRecord(raw);
}

export function assertSessionMatchesDraft(
  session: ThreatPublicationWorkbenchSessionV1,
  draftId: string,
  draftVersion?: number,
): boolean {
  if (session.draft_id.trim() !== draftId.trim()) return false;
  if (draftVersion != null && session.draft_version !== draftVersion) return false;
  return true;
}

function resolveStorage(storage?: Storage): Storage | null {
  if (storage != null) return storage;
  if (typeof window === "undefined" || typeof window.sessionStorage === "undefined") {
    return null;
  }
  return window.sessionStorage;
}

export function readThreatPublicationSession(
  draftId: string,
  storage?: Storage,
): ThreatPublicationWorkbenchSessionV1 | null {
  const resolved = resolveStorage(storage);
  if (!resolved) return null;

  try {
    const raw = resolved.getItem(threatPublicationSessionKey(draftId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    const session = validateSessionRecord(parsed, draftId);
    if (!session) {
      warnCorruptStorageOnce(
        `[ThreatPublicationSession] Ignoring corrupt session pointer for draft ${draftId.trim()}.`,
      );
    }
    return session;
  } catch {
    warnCorruptStorageOnce(
      `[ThreatPublicationSession] Ignoring unreadable session pointer for draft ${draftId.trim()}.`,
    );
    return null;
  }
}

export function writeThreatPublicationSession(
  session: ThreatPublicationWorkbenchSessionV1,
  storage?: Storage,
): void {
  const resolved = resolveStorage(storage);
  if (!resolved) return;

  const validated = validateSessionRecord(session, session.draft_id);
  if (!validated) return;

  const pointer = toPointerOnlySession(validated);
  try {
    resolved.setItem(
      threatPublicationSessionKey(pointer.draft_id),
      JSON.stringify(pointer),
    );
  } catch {
    // Fail closed without throwing when storage is unavailable or quota is exceeded.
  }
}

export function clearThreatPublicationSession(draftId: string, storage?: Storage): void {
  const resolved = resolveStorage(storage);
  if (!resolved) return;

  try {
    resolved.removeItem(threatPublicationSessionKey(draftId));
  } catch {
    // Fail closed without throwing when storage is unavailable.
  }
}
