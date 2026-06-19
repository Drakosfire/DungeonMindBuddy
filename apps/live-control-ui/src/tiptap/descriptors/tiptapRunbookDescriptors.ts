import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";

export type TiptapRunbookThemeId = "command" | "plain" | "statblock";

export type TiptapRunbookDescriptor = {
  documentId: string;
  title: string;
  campaignId: string;
  session: number;
  targetRelpath: string;
  themeId: TiptapRunbookThemeId;
  description?: string;
  /** Local-only reset seed. Durable Markdown remains canon; descriptor starter content is not canon. */
  starterContent: unknown;
};

export const DEFAULT_TIPTAP_RUNBOOK_DOCUMENT_ID = "north-gate-session-runbook";

export const northGateSessionRunbookStarterContent = {
  type: "doc",
  content: [
    { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "C2S23 North Gate Session Runbook" }] },
    { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "At-table intent" }] },
    { type: "paragraph", content: [{ type: "text", text: "This runbook opens at " }, { type: "runbookReference", attrs: { kind: "ref", refType: "location", refId: "north-reach-gate", label: "North Reach Gate" } }, { type: "text", text: ". Keep the table on immediate choices: who gets through, who is left outside, and whether panic becomes violence." }] },
    { type: "callout", attrs: { kind: "read-aloud" }, content: [{ type: "paragraph", content: [{ type: "text", text: "The southern road buckles into a wall of bodies, wagons, and wet gray fog. Bells hammer behind the gate while the refugee line surges toward any hand that looks like authority." }] }] },
    { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Opening frame" }] },
    { type: "callout", attrs: { kind: "gm-note" }, content: [{ type: "paragraph", content: [{ type: "text", text: "Keep this scene about triage: gate safety, civilian crush, and whether Lysandro weaponizes panic. Do not solve the whole siege here." }] }] },
    { type: "paragraph", content: [{ type: "text", text: "If the party turns toward the argument, foreground " }, { type: "runbookReference", attrs: { kind: "ref", refType: "npc", refId: "lysandro-ironveil", label: "Lysandro Ironveil" } }, { type: "text", text: " and let him demand that " }, { type: "runbookReference", attrs: { kind: "ref", refType: "location", refId: "north-reach-gate", label: "North Reach Gate" } }, { type: "text", text: " close before the infected can reach the line." }] },
    { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "First five minutes" }] },
    { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "Ask which PC takes the gate, the crowd, and the cure line." }] }] }, { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "Show one infected refugee as a person before the threat becomes a mass." }] }] }, { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If the line breaks, roll or choose from " }, { type: "runbookReference", attrs: { kind: "ref", refType: "roll-table", refId: "gate-dilemma-d12", label: "Gate Dilemma d12" } }, { type: "text", text: "." }] }] }] },
    { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Pressure clocks" }] },
    { type: "callout", attrs: { kind: "rules" }, content: [{ type: "paragraph", content: [{ type: "text", text: "Use visible pressures instead of hidden timers: Gate, Civilians, Cure Line. Advance one whenever the table stalls or chooses a costly success." }] }] },
    { type: "callout", attrs: { kind: "warning" }, content: [{ type: "paragraph", content: [{ type: "text", text: "The meat flank is minutes behind the refugees. Do not let the opening become a static council debate." }] }] },
    { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Decision fork" }] },
    { type: "bulletList", content: [{ type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If they talk, make Lysandro name a specific cost for keeping the gate open." }] }] }, { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If they fight, bring in the " }, { type: "runbookReference", attrs: { kind: "ref", refType: "statblock", refId: "sewer-meat-creature", label: "Sewer Meat Creature" } }, { type: "text", text: " and pivot toward " }, { type: "runbookReference", attrs: { kind: "action", refType: "combat", refId: "north-gate-combat", label: "North Gate Combat" } }, { type: "text", text: "." }] }] }, { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "If they flee or split, cut between the gate lever, the crush, and the first scream behind the wagons." }] }] }] },
    { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Reference chips" }] },
    { type: "paragraph", content: [{ type: "text", text: "Use " }, { type: "runbookReference", attrs: { kind: "ref", refType: "citation", refId: "c2s22-ending", label: "Session 22 ending" } }, { type: "text", text: " as a placeholder for continuity; citation resolution is not live yet." }] },
    { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Hard boundaries" }] },
    { type: "paragraph", content: [{ type: "text", text: "This runbook is table prep only. It should not write canon, launch combat, execute rolls, or mutate operational state." }] },
  ],
};

export const northGateCalloutSpikeStarterContent = {
  type: "doc",
  content: [
    { type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "North Gate Callout Spike" }] },
    { type: "paragraph", content: [{ type: "text", text: "Small smoke-test document for descriptor-keyed local drafts." }] },
    { type: "callout", attrs: { kind: "gm-note" }, content: [{ type: "paragraph", content: [{ type: "text", text: "Use this lightweight document to verify target-path and localStorage isolation." }] }] },
  ],
};

export const TIPTAP_RUNBOOK_DESCRIPTORS: TiptapRunbookDescriptor[] = [
  { documentId: DEFAULT_TIPTAP_RUNBOOK_DOCUMENT_ID, title: "North Gate Session Runbook", campaignId: "longmont-c2", session: 23, targetRelpath: "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md", themeId: "command", description: "C2S23 table-facing North Gate opening runbook.", starterContent: northGateSessionRunbookStarterContent },
  { documentId: "north-gate-callout-spike", title: "North Gate Callout Spike", campaignId: "longmont-c2", session: 23, targetRelpath: "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-callout-spike.md", themeId: "command", description: "Small callout bridge smoke-test document.", starterContent: northGateCalloutSpikeStarterContent },
];

export function isKnownTiptapRunbookDocumentId(documentId: string): boolean {
  return TIPTAP_RUNBOOK_DESCRIPTORS.some((descriptor) => descriptor.documentId === documentId);
}

export function getTiptapRunbookDescriptor(documentId?: string | null): TiptapRunbookDescriptor {
  return TIPTAP_RUNBOOK_DESCRIPTORS.find((descriptor) => descriptor.documentId === documentId)
    ?? TIPTAP_RUNBOOK_DESCRIPTORS[0];
}

export function tiptapRunbookStorageKey(descriptor: TiptapRunbookDescriptor): string {
  return `dmb:tiptap-working-board:${descriptor.campaignId}:session-${descriptor.session}:${descriptor.documentId}`;
}

export function starterContentMarkdown(descriptor: TiptapRunbookDescriptor): string {
  return tiptapJsonToSemanticMarkdown(descriptor.starterContent);
}
