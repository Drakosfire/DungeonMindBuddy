import type { PlanSessionDescriptor } from "../types";

export interface PlanDogfoodChecklistItem {
  id: string;
  label: string;
  description?: string;
}

export interface PlanDogfoodState {
  checked: Record<string, boolean>;
  notes: string;
  updatedAt: string | null;
}

/**
 * Operator measurement checklist for the current Plan prep loop.
 * Rung 5 focus: board + markdown recovery, then Hermes same-thread continuity.
 * World Graph object search/dogfood-list steps stay out of this checklist —
 * the Plan main page is the board + dogfood panel, not a graph browser.
 */
export const PLAN_DOGFOOD_CHECKLIST: PlanDogfoodChecklistItem[] = [
  {
    id: "open-plan",
    label: "Open /plan?dogfood=1 with the intended live session dir",
    description:
      "Live packet still drives liveSession; set ?session=N (and optional ?prepSession=N) for memory/graph focus and board target.",
  },
  {
    id: "confirm-context",
    label: "Confirm prep board title / target path (URL session + prepSession if set)",
    description:
      "Without ?session=, Ask DungeonBuddy uses world-union focus. prepSession defaults to live+1 unless ?prepSession= is set. Board title lives on the working board, not a second header.",
  },
  {
    id: "observe-board-source",
    label: "Record whether the board is scaffold, local draft, or full corpus prep",
    description: "Corpus hydrate on load is not shipped; scaffold/local draft is expected.",
  },
  {
    id: "protect-existing-prep",
    label: "If Session Prep.md already has content, paste it before Save",
    description: "Saving scaffold would overwrite the durable prep file.",
  },
  { id: "add-real-notes", label: "Edit the board with real prep notes for this session" },
  { id: "use-reference-chip", label: "Add or use at least one reference chip" },
  { id: "save-markdown", label: "Save to Markdown and confirm the target file updated" },
  {
    id: "reload-tab",
    label: "Reload the tab and confirm the local draft remains",
    description: "This proves localStorage recovery, not corpus re-read.",
  },
  {
    id: "optional-clear-local-proof",
    label: "(Optional) Clear Plan canvas localStorage, reload, confirm scaffold returns",
    description: "Falsifies corpus hydrate; skip if you do not want to re-paste content.",
  },
  { id: "stop-server", label: "Stop the dev server" },
  { id: "restart-server", label: "Restart the dev server" },
  {
    id: "reopen-plan",
    label: "Reopen /plan and confirm local draft recovery",
  },
  {
    id: "inspect-card",
    label: "Click a reference chip and inspect the selected-object card",
  },
  { id: "source-preview", label: "Use Show source preview from the card when available" },
  {
    id: "hermes-tools-trace",
    label: "Open Ask DungeonBuddy → inspect graph evidence and trace",
    description: "Fresh Plan threads use the Hermes graph agent; Live remains a compatibility path for persisted threads.",
  },
  {
    id: "hermes-turn-1-tripod",
    label: "Ask Turn 1: What do we know about Tripod Null-Calf at the North Gate?",
    description: "Confirm hermes_graph_agent, graph tool ran, grounding/citations agree.",
  },
  {
    id: "hermes-turn-2-same-thread",
    label: "Same thread, ask Turn 2: What is it connected to that should affect my prep?",
    description: "Pronoun continuity only; facts must come from a fresh graph lookup.",
  },
  {
    id: "hermes-network-history",
    label:
      "Inspect Turn 2 Network: conversation_history is prior Q/A only; no hermes_session_id or manifest_path",
    description: "History must not carry citations, traces, revisions, or source bodies.",
  },
  {
    id: "hermes-fresh-graph",
    label:
      "Confirm Turn 2 resolves “it”, runs fresh graph tools, and cites only Turn 2 anchors",
    description: "Conversationally continuous, factually fresh — not a resumed Hermes session.",
  },
  {
    id: "hermes-thread-isolation",
    label: "New empty Thread B: ask the Turn 2 follow-up alone; confirm Thread A history is absent",
    description: "No Thread A prose or citations may leak into Thread B requests.",
  },
  {
    id: "hermes-no-session-persist",
    label:
      "Inspect agent-interaction localStorage: no hermes_session_id or conversation_history fields",
    description: "Outbound history is reconstructed from visible Q/A; Rung 6 owns durable sessions.",
  },
  {
    id: "open-graph-evidence",
    label: "Open a supporting World Graph citation/evidence card from the Hermes answer",
    description: "Prefer graph-anchor evidence over legacy path citations for Hermes turns.",
  },
  {
    id: "record-useful",
    label: "Record what felt useful for writing Session Prep",
  },
  {
    id: "record-confusing",
    label: "Record what felt confusing, stale, scaffold-y, or missing (especially load)",
  },
];

/** Seeded into copied reports so operator feedback stays attached to the current slice. */
export const PLAN_DOGFOOD_SUGGESTED_FOLLOW_UPS: string[] = [
  "Remove World Graph search from the Plan toolbar / main page — keep the surface as dogfood checklist + markdown working board.",
  "Ship corpus hydrate on load so scaffold cannot clobber an existing Session Prep.md.",
  "After Rung 5 acceptance: Rung 6 durable Hermes session / reload lifecycle (not prose replay).",
];

export function dogfoodModeFromLocation(location: Location = window.location): boolean {
  return new URLSearchParams(location.search).get("dogfood") === "1";
}

export function planDogfoodStorageKey(sessionDescriptor: PlanSessionDescriptor): string {
  return [
    "dmb.planDogfood",
    sessionDescriptor.campaignId,
    sessionDescriptor.prepSession,
    sessionDescriptor.planningDocument.documentId,
  ].join(".");
}

export function createEmptyPlanDogfoodState(): PlanDogfoodState {
  return {
    checked: {},
    notes: "",
    updatedAt: null,
  };
}

export function loadPlanDogfoodState(
  storage: Storage,
  sessionDescriptor: PlanSessionDescriptor,
): PlanDogfoodState {
  const key = planDogfoodStorageKey(sessionDescriptor);
  const raw = storage.getItem(key);
  if (!raw) {
    return createEmptyPlanDogfoodState();
  }
  try {
    const parsed = JSON.parse(raw) as Partial<PlanDogfoodState>;
    return {
      checked: parsed.checked ?? {},
      notes: parsed.notes ?? "",
      updatedAt: parsed.updatedAt ?? null,
    };
  } catch {
    return createEmptyPlanDogfoodState();
  }
}

export function savePlanDogfoodState(
  storage: Storage,
  sessionDescriptor: PlanSessionDescriptor,
  state: PlanDogfoodState,
): void {
  const key = planDogfoodStorageKey(sessionDescriptor);
  storage.setItem(key, JSON.stringify(state));
}

export function clearPlanDogfoodState(
  storage: Storage,
  sessionDescriptor: PlanSessionDescriptor,
): void {
  storage.removeItem(planDogfoodStorageKey(sessionDescriptor));
}

export function togglePlanDogfoodChecklistItem(
  state: PlanDogfoodState,
  itemId: string,
  checked: boolean,
): PlanDogfoodState {
  return {
    ...state,
    checked: { ...state.checked, [itemId]: checked },
    updatedAt: new Date().toISOString(),
  };
}

export function updatePlanDogfoodNotes(
  state: PlanDogfoodState,
  notes: string,
): PlanDogfoodState {
  return {
    ...state,
    notes,
    updatedAt: new Date().toISOString(),
  };
}
