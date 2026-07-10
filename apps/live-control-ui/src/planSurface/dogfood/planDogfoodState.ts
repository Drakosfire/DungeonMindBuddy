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
  { id: "open-plan", label: "Open /plan for the intended campaign/session" },
  {
    id: "confirm-context",
    label: "Confirm the header shows expected prep and memory sessions",
  },
  { id: "add-real-notes", label: "Add real prep notes to the board" },
  { id: "use-reference-chip", label: "Add or use at least one reference chip" },
  { id: "save-markdown", label: "Save to Markdown" },
  {
    id: "reload-tab",
    label: "Reload the browser tab and confirm content remains",
  },
  { id: "stop-server", label: "Stop the dev server" },
  { id: "restart-server", label: "Restart the dev server" },
  {
    id: "reopen-plan",
    label: "Reopen /plan and confirm saved/recovered content",
  },
  {
    id: "inspect-card",
    label: "Click a reference chip and inspect the selected-object card",
  },
  { id: "source-preview", label: "Use Show source preview from the card" },
  {
    id: "graph-object-add",
    label: "Add at least one graph-projected object to the dogfood list",
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
  { id: "ask-prep-memory", label: "Ask prep memory a real question" },
  {
    id: "open-supporting-source",
    label: "Open a supporting source from the prep-memory answer",
  },
  { id: "record-useful", label: "Record what felt useful" },
  {
    id: "record-confusing",
    label: "Record what felt confusing, stale, too graph-y, or missing",
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
