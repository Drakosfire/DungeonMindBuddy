import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";

export const TIPTAP_WORKING_BOARD_KEY =
  "dmb:tiptap-working-board:longmont-c2:session-23:north-gate-session-runbook";

export const initialCalloutContent = {
  type: "doc",
  content: [
    {
      type: "heading",
      attrs: { level: 1 },
      content: [{ type: "text", text: "C2S23 North Gate Session Runbook" }],
    },
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "At-table intent" }],
    },
    {
      type: "paragraph",
      content: [
        { type: "text", text: "This runbook opens at " },
        {
          type: "runbookReference",
          attrs: { kind: "ref", refType: "location", refId: "north-reach-gate", label: "North Reach Gate" },
        },
        { type: "text", text: ". Keep the table on immediate choices: who gets through, who is left outside, and whether panic becomes violence." },
      ],
    },
    {
      type: "callout",
      attrs: { kind: "read-aloud" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "The southern road buckles into a wall of bodies, wagons, and wet gray fog. Bells hammer behind the gate while the refugee line surges toward any hand that looks like authority." }] }],
    },
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "Opening frame" }],
    },
    {
      type: "callout",
      attrs: { kind: "gm-note" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "Keep this scene about triage: gate safety, civilian crush, and whether Lysandro weaponizes panic. Do not solve the whole siege here." }] }],
    },
    {
      type: "paragraph",
      content: [
        { type: "text", text: "If the party turns toward the argument, foreground " },
        {
          type: "runbookReference",
          attrs: { kind: "ref", refType: "npc", refId: "lysandro-ironveil", label: "Lysandro Ironveil" },
        },
        { type: "text", text: " and let him demand that " },
        {
          type: "runbookReference",
          attrs: { kind: "ref", refType: "location", refId: "north-reach-gate", label: "North Reach Gate" },
        },
        { type: "text", text: " close before the infected can reach the line." },
      ],
    },
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "First five minutes" }],
    },
    {
      type: "bulletList",
      content: [
        { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "Ask which PC takes the gate, the crowd, and the cure line." }] }] },
        { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "Show one infected refugee as a person before the threat becomes a mass." }] }] },
        { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If the line breaks, roll or choose from " }, { type: "runbookReference", attrs: { kind: "ref", refType: "roll-table", refId: "gate-dilemma-d12", label: "Gate Dilemma d12" } }, { type: "text", text: "." }] }] },
      ],
    },
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "Pressure clocks" }],
    },
    {
      type: "callout",
      attrs: { kind: "rules" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "Use visible pressures instead of hidden timers: Gate, Civilians, Cure Line. Advance one whenever the table stalls or chooses a costly success." }] }],
    },
    {
      type: "callout",
      attrs: { kind: "warning" },
      content: [{ type: "paragraph", content: [{ type: "text", text: "The meat flank is minutes behind the refugees. Do not let the opening become a static council debate." }] }],
    },
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "Decision fork" }],
    },
    {
      type: "bulletList",
      content: [
        { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If they talk, make Lysandro name a specific cost for keeping the gate open." }] }] },
        { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If they fight, bring in the " }, { type: "runbookReference", attrs: { kind: "ref", refType: "statblock", refId: "sewer-meat-creature", label: "Sewer Meat Creature" } }, { type: "text", text: " and pivot toward " }, { type: "runbookReference", attrs: { kind: "action", refType: "combat", refId: "north-gate-combat", label: "North Gate Combat" }, }, { type: "text", text: "." }] }] },
        { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If they flee or split, cut between the gate lever, the crush, and the first scream behind the wagons." }] }] },
      ],
    },
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "Reference chips" }],
    },
    {
      type: "paragraph",
      content: [
        { type: "text", text: "Use " },
        { type: "runbookReference", attrs: { kind: "ref", refType: "citation", refId: "c2s22-ending", label: "Session 22 ending" } },
        { type: "text", text: " as a placeholder for continuity; citation resolution is not live yet." },
      ],
    },
    {
      type: "heading",
      attrs: { level: 2 },
      content: [{ type: "text", text: "Hard boundaries" }],
    },
    {
      type: "paragraph",
      content: [{ type: "text", text: "This runbook is table prep only. It should not write canon, launch combat, execute rolls, or mutate operational state." }],
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
    document_id: "north-gate-session-runbook",
    title: "North Gate Session Runbook",
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
): TiptapWorkingBoardState | null {
  try {
    const stored = storage.getItem(TIPTAP_WORKING_BOARD_KEY);
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
  state: TiptapWorkingBoardState,
): void {
  storage.setItem(TIPTAP_WORKING_BOARD_KEY, JSON.stringify(state));
}

export function clearTiptapWorkingBoardState(
  storage: Pick<Storage, "removeItem">,
): void {
  storage.removeItem(TIPTAP_WORKING_BOARD_KEY);
}
