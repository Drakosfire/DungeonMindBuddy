import {
  validateLocalWorldPackageData,
  type LocalWorldId,
  type LocalWorldPackageData,
  type LocalWorldConflictCandidate,
} from "./localWorldRepository";

export const LOCAL_WORLD_NOTES_DOCUMENT_ID = "buddy-local-world-notes";
export const LOCAL_WORLD_NOTES_DOCUMENT_PATH = "documents/buddy-world-notes.md";
export const LOCAL_WORLD_NOTES_MEDIA_TYPE = "text/markdown";
export const LOCAL_WORLD_NOTES_HISTORY_DESCRIPTION = "buddy-local-world-notes:edited";
export const LOCAL_WORLD_NOTES_MAX_BYTES = 1024 * 1024;

export interface PendingWorldNotesDraft {
  readonly value: string;
  readonly token: symbol;
}

const pendingWorldNotesDrafts = new Map<LocalWorldId, PendingWorldNotesDraft>();

export function getPendingWorldNotesDraft(worldId: LocalWorldId): PendingWorldNotesDraft | undefined {
  return pendingWorldNotesDrafts.get(worldId);
}

export function setPendingWorldNotesDraft(worldId: LocalWorldId, value: string, savedValue: string): PendingWorldNotesDraft | undefined {
  if (value === savedValue) pendingWorldNotesDrafts.delete(worldId);
  else pendingWorldNotesDrafts.set(worldId, { value, token: Symbol("local-world-notes-draft") });
  return pendingWorldNotesDrafts.get(worldId);
}

export function clearPendingWorldNotesDraft(worldId: LocalWorldId, expectedToken?: symbol): void {
  const current = pendingWorldNotesDrafts.get(worldId);
  if (!current || (expectedToken !== undefined && current.token !== expectedToken)) return;
  pendingWorldNotesDrafts.delete(worldId);
}

export function hasPendingWorldNotesDrafts(): boolean {
  return pendingWorldNotesDrafts.size > 0;
}

export type WorldNotesRead =
  | { readonly status: "found"; readonly markdown: string; readonly documentExists: boolean }
  | { readonly status: "error"; readonly message: string };

export function encodeWorldNotes(markdown: string): { readonly bytes: readonly number[] } | { readonly error: string } {
  if (!isWellFormedUnicode(markdown)) return { error: "World notes contain invalid Unicode and were not saved." };
  const bytes = new TextEncoder().encode(markdown);
  if (bytes.byteLength > LOCAL_WORLD_NOTES_MAX_BYTES) {
    return { error: "World notes exceed the 1 MiB local document limit." };
  }
  return { bytes: Array.from(bytes) };
}

export function readWorldNotesPackageData(data: LocalWorldPackageData, worldId: LocalWorldId): WorldNotesRead {
  const invalid = validateLocalWorldPackageData(data, worldId);
  if (invalid) return { status: "error", message: invalid };
  const matches = data.documents.filter((reference) =>
    reference.id === LOCAL_WORLD_NOTES_DOCUMENT_ID || reference.path === LOCAL_WORLD_NOTES_DOCUMENT_PATH,
  );
  if (matches.length === 0) return { status: "found", markdown: "", documentExists: false };
  if (matches.length !== 1) return { status: "error", message: "The local World notes document collides with another package member." };
  const reference = matches[0];
  if (reference.id !== LOCAL_WORLD_NOTES_DOCUMENT_ID
    || reference.status !== "bundled"
    || reference.path !== LOCAL_WORLD_NOTES_DOCUMENT_PATH
    || reference.mediaType !== LOCAL_WORLD_NOTES_MEDIA_TYPE
    || reference.locator !== null) {
    return { status: "error", message: "An imported document occupies the reserved World notes identity; it was left unchanged." };
  }
  const bytes = data.bundledMembers[LOCAL_WORLD_NOTES_DOCUMENT_PATH];
  if (!bytes || bytes.length > LOCAL_WORLD_NOTES_MAX_BYTES) {
    return { status: "error", message: "The stored World notes member is missing or exceeds the 1 MiB limit." };
  }
  try {
    return { status: "found", markdown: new TextDecoder("utf-8", { fatal: true }).decode(Uint8Array.from(bytes)), documentExists: true };
  } catch {
    return { status: "error", message: "The stored World notes are not valid UTF-8; the original bytes were preserved." };
  }
}

export function writeWorldNotesPackageData(
  data: LocalWorldPackageData,
  worldId: LocalWorldId,
  markdownBytes: readonly number[],
): { readonly status: "written"; readonly data: LocalWorldPackageData } | { readonly status: "error"; readonly message: string } {
  if (markdownBytes.length > LOCAL_WORLD_NOTES_MAX_BYTES) return { status: "error", message: "World notes exceed the 1 MiB local document limit." };
  const invalid = validateLocalWorldPackageData(data, worldId);
  if (invalid) return { status: "error", message: invalid };
  const prior = readWorldNotesPackageData(data, worldId);
  if (prior.status === "error") return prior;
  const collidingReferences = data.documents.filter((reference) =>
    reference.id === LOCAL_WORLD_NOTES_DOCUMENT_ID || reference.path === LOCAL_WORLD_NOTES_DOCUMENT_PATH,
  );
  if (collidingReferences.length > 1) return { status: "error", message: "The local World notes document collides with another package member." };
  const documents = data.documents.filter((reference) =>
    reference.id !== LOCAL_WORLD_NOTES_DOCUMENT_ID && reference.path !== LOCAL_WORLD_NOTES_DOCUMENT_PATH,
  );
  documents.push({
    id: LOCAL_WORLD_NOTES_DOCUMENT_ID,
    status: "bundled",
    path: LOCAL_WORLD_NOTES_DOCUMENT_PATH,
    mediaType: LOCAL_WORLD_NOTES_MEDIA_TYPE,
    locator: null,
  });
  const bundledMembers: Record<string, readonly number[]> = {};
  for (const [path, bytes] of Object.entries(data.bundledMembers)) bundledMembers[path] = Array.from(bytes);
  bundledMembers[LOCAL_WORLD_NOTES_DOCUMENT_PATH] = Array.from(markdownBytes);
  const next: LocalWorldPackageData = {
    ...data,
    localWorldId: worldId,
    documents,
    assets: data.assets.map((reference) => ({ ...reference })),
    bundledMembers,
  };
  const nextInvalid = validateLocalWorldPackageData(next, worldId);
  return nextInvalid
    ? { status: "error", message: nextInvalid }
    : { status: "written", data: next };
}

export function emptyLocalWorldPackageData(worldId: LocalWorldId): LocalWorldPackageData {
  return {
    localWorldId: worldId,
    documents: [],
    assets: [],
    bundledMembers: {},
    fidelity: {
      localRecord: "preserved",
      sourceMetadata: "not-represented-by-local-record",
      profileMetadata: "not-represented-by-local-record",
    },
    creatorProfileAssumptions: { creator: "not-recorded", profile: "not-recorded" },
  };
}

export function isWorldNotesConflict(candidate: LocalWorldConflictCandidate): boolean {
  return candidate.edit.classification === "buddy-local-only"
    && candidate.edit.description === LOCAL_WORLD_NOTES_HISTORY_DESCRIPTION
    && candidate.proposedPackageData !== undefined
    && candidate.proposedPackageData.localWorldId === candidate.worldId;
}

function isWellFormedUnicode(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) return false;
  }
  return true;
}
