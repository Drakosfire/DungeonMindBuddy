import type { Content } from "@tiptap/core";
import type { WorkspaceDocumentRecord } from "../api/types";

export const BUILD_LOCAL_DRAFT_SCHEMA = "dmb_build_source_local_draft_v1" as const;

export interface BuildLocalDraft {
  schema_version: typeof BUILD_LOCAL_DRAFT_SCHEMA;
  document_id: string;
  revision: number;
  tiptap_json: Content;
  dirty: boolean;
  updated_at: string;
}

export function buildLocalDraftStorageKey(documentId: string): string {
  return `dmb.buildSource.${documentId}`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function isBuildLocalDraft(value: unknown): value is BuildLocalDraft {
  return (
    isObject(value)
    && value.schema_version === BUILD_LOCAL_DRAFT_SCHEMA
    && typeof value.document_id === "string"
    && typeof value.revision === "number"
    && isObject(value.tiptap_json)
    && typeof value.dirty === "boolean"
    && typeof value.updated_at === "string"
  );
}

export function readBuildLocalDraft(
  storage: Pick<Storage, "getItem">,
  documentId: string,
): BuildLocalDraft | null {
  try {
    const raw = storage.getItem(buildLocalDraftStorageKey(documentId));
    if (raw === null) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!isBuildLocalDraft(parsed) || parsed.document_id !== documentId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeBuildLocalDraft(
  storage: Pick<Storage, "setItem">,
  draft: BuildLocalDraft,
): void {
  storage.setItem(buildLocalDraftStorageKey(draft.document_id), JSON.stringify(draft));
}

export function buildDraftFromRecord(
  record: WorkspaceDocumentRecord,
  content: Content,
  dirty: boolean,
  now = new Date().toISOString(),
): BuildLocalDraft {
  return {
    schema_version: BUILD_LOCAL_DRAFT_SCHEMA,
    document_id: record.document_id,
    revision: record.revision,
    tiptap_json: content,
    dirty,
    updated_at: now,
  };
}
