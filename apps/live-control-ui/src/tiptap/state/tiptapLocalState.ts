import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";

export const TIPTAP_WORKING_BOARD_KEY =
  "dmb:tiptap-working-board:longmont-c2:session-23:north-gate-callout-spike";

export const initialCalloutContent = {
  type: "doc",
  content: [
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "North-gate opening spike" }],
    },
    {
      type: "callout",
      attrs: { kind: "read-aloud" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "The southern road gives way to the dark wall of Mireward." }] }],
    },
    {
      type: "callout",
      attrs: { kind: "gm-note" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "Lysandro is the human accelerant." }] }],
    },
    {
      type: "callout",
      attrs: { kind: "rules" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "Track Gate, Civilians, and Cure Line as visible pressures." }] }],
    },
    {
      type: "callout",
      attrs: { kind: "warning" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "The meat flank is 3–8 minutes behind the refugees." }] }],
    },
  ],
};

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

export function buildInitialWorkingBoardState(now = new Date().toISOString()): TiptapWorkingBoardState {
  return {
    schema_version: "dmb_tiptap_working_board_state_v1",
    document_id: "north-gate-callout-spike",
    title: "North-gate callout spike",
    campaign_id: "longmont-c2",
    session: 23,
    surface: "tiptap-callout-spike",
    tiptap_json: initialCalloutContent,
    exported_markdown: tiptapJsonToSemanticMarkdown(initialCalloutContent),
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

export function readTiptapWorkingBoardState(
  storage: Pick<Storage, "getItem">,
): TiptapWorkingBoardState | null {
  try {
    const stored = storage.getItem(TIPTAP_WORKING_BOARD_KEY);
    if (stored === null) return null;
    const parsed: unknown = JSON.parse(stored);
    return isTiptapWorkingBoardState(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function writeTiptapWorkingBoardState(
  storage: Pick<Storage, "setItem">,
  state: TiptapWorkingBoardState,
): void {
  storage.setItem(TIPTAP_WORKING_BOARD_KEY, JSON.stringify(state));
}

export function clearTiptapWorkingBoardState(
  storage: Pick<Storage, "removeItem">,
): void {
  storage.removeItem(TIPTAP_WORKING_BOARD_KEY);
}
