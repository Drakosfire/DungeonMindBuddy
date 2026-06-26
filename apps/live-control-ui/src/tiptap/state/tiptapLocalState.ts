import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import type { TiptapRunbookDescriptor } from "../descriptors/tiptapRunbookDescriptors";
import {
  getTiptapRunbookDescriptor,
  northGateSessionRunbookStarterContent,
  tiptapRunbookStorageKey,
} from "../descriptors/tiptapRunbookDescriptors";

export const TIPTAP_WORKING_BOARD_KEY = tiptapRunbookStorageKey(getTiptapRunbookDescriptor());
export const initialCalloutContent = northGateSessionRunbookStarterContent;

export interface TiptapWorkingBoardState {
  schema_version: "dmb_tiptap_working_board_state_v1";
  document_id: string;
  title: string;
  campaign_id: string;
  session: number;
  surface: "tiptap-callout-spike";
  tiptap_json: unknown;
  exported_markdown: string;
  dirty: boolean;
  created_at: string;
  updated_at: string;
  last_local_save_at: string;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function buildInitialWorkingBoardState(
  descriptor: TiptapRunbookDescriptor,
  now = new Date().toISOString(),
): TiptapWorkingBoardState {
  return {
    schema_version: "dmb_tiptap_working_board_state_v1",
    document_id: descriptor.documentId,
    title: descriptor.title,
    campaign_id: descriptor.campaignId,
    session: descriptor.session,
    surface: "tiptap-callout-spike",
    tiptap_json: descriptor.starterContent,
    exported_markdown: tiptapJsonToSemanticMarkdown(descriptor.starterContent),
    dirty: false,
    created_at: now,
    updated_at: now,
    last_local_save_at: now,
  };
}

export function isTiptapWorkingBoardState(value: unknown): value is TiptapWorkingBoardState {
  if (!isObject(value)) return false;

  return (
    value.schema_version === "dmb_tiptap_working_board_state_v1"
    && typeof value.document_id === "string"
    && typeof value.title === "string"
    && typeof value.campaign_id === "string"
    && typeof value.session === "number"
    && value.surface === "tiptap-callout-spike"
    && isObject(value.tiptap_json)
    && typeof value.exported_markdown === "string"
    && typeof value.dirty === "boolean"
    && typeof value.created_at === "string"
    && typeof value.updated_at === "string"
    && typeof value.last_local_save_at === "string"
  );
}

function deriveWorkingBoardMarkdown(
  state: TiptapWorkingBoardState,
): TiptapWorkingBoardState {
  return {
    ...state,
    exported_markdown: tiptapJsonToSemanticMarkdown(state.tiptap_json),
  };
}

export function readTiptapWorkingBoardState(
  storage: Pick<Storage, "getItem">,
  descriptor: TiptapRunbookDescriptor,
): TiptapWorkingBoardState | null {
  try {
    const stored = storage.getItem(tiptapRunbookStorageKey(descriptor));
    if (stored === null) return null;
    const parsed: unknown = JSON.parse(stored);
    return isTiptapWorkingBoardState(parsed)
      ? deriveWorkingBoardMarkdown(parsed)
      : null;
  } catch {
    return null;
  }
}

export function writeTiptapWorkingBoardState(
  storage: Pick<Storage, "setItem">,
  descriptor: TiptapRunbookDescriptor,
  state: TiptapWorkingBoardState,
): void {
  storage.setItem(tiptapRunbookStorageKey(descriptor), JSON.stringify(state));
}

export function clearTiptapWorkingBoardState(
  storage: Pick<Storage, "removeItem">,
  descriptor: TiptapRunbookDescriptor,
): void {
  storage.removeItem(tiptapRunbookStorageKey(descriptor));
}
