import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";

export const WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA = "dmb_workspace_document_local_state_v2" as const;

export interface WorkspaceDocumentLocalState {
  schema_version: typeof WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA;
  document_id: string;
  title: string;
  campaign_id: string;
  kind: "plan" | "runbook";
  target_session: number | null;
  surface: "plan" | "runbook";
  tiptap_json: unknown;
  exported_markdown: string;
  dirty: boolean;
  created_at: string;
  updated_at: string;
  last_local_save_at: string;
}

/** @deprecated Use WorkspaceDocumentLocalState */
export type TiptapWorkingBoardState = WorkspaceDocumentLocalState;

export function workspaceDocumentStorageKey(documentId: string): string {
  return `dmb.workspaceDocument.${documentId}`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function buildInitialWorkspaceDocumentLocalState(args: {
  documentId: string;
  title: string;
  campaignId: string;
  kind: "plan" | "runbook";
  targetSession: number | null;
  surface: "plan" | "runbook";
  starterContent: unknown;
  now?: string;
}): WorkspaceDocumentLocalState {
  const now = args.now ?? new Date().toISOString();
  return {
    schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
    document_id: args.documentId,
    title: args.title,
    campaign_id: args.campaignId,
    kind: args.kind,
    target_session: args.targetSession,
    surface: args.surface,
    tiptap_json: args.starterContent,
    exported_markdown: tiptapJsonToSemanticMarkdown(args.starterContent),
    dirty: false,
    created_at: now,
    updated_at: now,
    last_local_save_at: now,
  };
}

/** @deprecated Use buildInitialWorkspaceDocumentLocalState */
export function buildInitialWorkingBoardState(
  descriptor: {
    documentId: string;
    title: string;
    campaignId: string;
    kind?: "plan" | "runbook";
    targetSession?: number | null;
    session?: number;
    starterContent: unknown;
  },
  now = new Date().toISOString(),
): WorkspaceDocumentLocalState {
  return buildInitialWorkspaceDocumentLocalState({
    documentId: descriptor.documentId,
    title: descriptor.title,
    campaignId: descriptor.campaignId,
    kind: descriptor.kind ?? "runbook",
    targetSession: descriptor.targetSession ?? descriptor.session ?? null,
    surface: descriptor.kind ?? "runbook",
    starterContent: descriptor.starterContent,
    now,
  });
}

export function isWorkspaceDocumentLocalState(value: unknown): value is WorkspaceDocumentLocalState {
  if (!isObject(value)) return false;

  return (
    value.schema_version === WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA
    && typeof value.document_id === "string"
    && typeof value.title === "string"
    && typeof value.campaign_id === "string"
    && (value.kind === "plan" || value.kind === "runbook")
    && (value.target_session === null || typeof value.target_session === "number")
    && (value.surface === "plan" || value.surface === "runbook")
    && isObject(value.tiptap_json)
    && typeof value.exported_markdown === "string"
    && typeof value.dirty === "boolean"
    && typeof value.created_at === "string"
    && typeof value.updated_at === "string"
    && typeof value.last_local_save_at === "string"
  );
}

/** @deprecated Use isWorkspaceDocumentLocalState */
export const isTiptapWorkingBoardState = isWorkspaceDocumentLocalState;

function deriveWorkspaceDocumentMarkdown(
  state: WorkspaceDocumentLocalState,
): WorkspaceDocumentLocalState {
  return {
    ...state,
    exported_markdown: tiptapJsonToSemanticMarkdown(state.tiptap_json),
  };
}

export function readWorkspaceDocumentLocalState(
  storage: Pick<Storage, "getItem">,
  documentId: string,
): WorkspaceDocumentLocalState | null {
  try {
    const stored = storage.getItem(workspaceDocumentStorageKey(documentId));
    if (stored === null) return null;
    const parsed: unknown = JSON.parse(stored);
    if (!isWorkspaceDocumentLocalState(parsed)) return null;
    if (parsed.document_id !== documentId) return null;
    return deriveWorkspaceDocumentMarkdown(parsed);
  } catch {
    return null;
  }
}

/** @deprecated Use readWorkspaceDocumentLocalState */
export function readTiptapWorkingBoardState(
  storage: Pick<Storage, "getItem">,
  descriptor: { documentId: string },
): WorkspaceDocumentLocalState | null {
  return readWorkspaceDocumentLocalState(storage, descriptor.documentId);
}

export function writeWorkspaceDocumentLocalState(
  storage: Pick<Storage, "setItem">,
  state: WorkspaceDocumentLocalState,
): void {
  storage.setItem(workspaceDocumentStorageKey(state.document_id), JSON.stringify(state));
}

/** @deprecated Use writeWorkspaceDocumentLocalState */
export function writeTiptapWorkingBoardState(
  storage: Pick<Storage, "setItem">,
  _descriptor: { documentId: string },
  state: WorkspaceDocumentLocalState,
): void {
  writeWorkspaceDocumentLocalState(storage, state);
}

export function clearWorkspaceDocumentLocalState(
  storage: Pick<Storage, "removeItem">,
  documentId: string,
): void {
  storage.removeItem(workspaceDocumentStorageKey(documentId));
}

/** @deprecated Use clearWorkspaceDocumentLocalState */
export function clearTiptapWorkingBoardState(
  storage: Pick<Storage, "removeItem">,
  descriptor: { documentId: string },
): void {
  clearWorkspaceDocumentLocalState(storage, descriptor.documentId);
}
