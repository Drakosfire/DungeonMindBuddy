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

export const PLAN_DOGFOOD_CHECKLIST: PlanDogfoodChecklistItem[] = [
  {
    id: "open-plan",
    label: "Open /plan?dogfood=1 with the intended live session dir",
    description: "URL campaign/session params do not select the Plan session; live packet does.",
  },
  {
    id: "confirm-context",
    label: "Confirm header prep/memory sessions and Nav target path",
    description: "prepSession = liveSession + 1; target should be Session {prep} Prep.md",
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
    id: "graph-object-add",
    label: "Find a World Graph object (Edit → World Graph objects) and add it to the dogfood list",
  },
  {
    id: "graph-object-view",
    label: "View a dogfood card through the real GraphObjectCard path",
  },
  {
    id: "graph-object-traverse",
    label: "Traverse a related object and judge whether the card stays useful",
  },
  {
    id: "graph-object-remove",
    label: "Remove a card from the dogfood list (local only)",
  },
  {
    id: "ask-prep-memory",
    label: "Ask prep memory a real question for this prep session",
  },
  {
    id: "open-supporting-source",
    label: "Open a supporting corpus citation source from the answer",
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
