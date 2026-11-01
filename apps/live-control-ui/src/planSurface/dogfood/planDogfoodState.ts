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

/** Operator notes for ordinary supported session QA, not a latest-source comparison. */
export const PLAN_DOGFOOD_CHECKLIST: PlanDogfoodChecklistItem[] = [
  {
    id: "supported-qa-open-plan",
    label: "Open the Plan for the World and session you want to inspect",
    description: "Record the selected World, campaign, session focus and Graph revision below.",
  },
  {
    id: "supported-qa-ask",
    label: 'Ask: "What does the selected session say happened?"',
    description: "Use a fresh conversation and inspect which material actually supports the reply.",
  },
  {
    id: "supported-qa-inspect-citations",
    label: "Open the citations and check that they support the answer",
    description: "An empty Graph or unavailable source may require an honest evidence gap.",
  },
  {
    id: "supported-qa-check-boundaries",
    label: "Check that the answer qualifies unproven freshness and comparison boundaries",
    description: "Retrieved facts alone do not prove latestness, a complete comparison, or that nothing changed.",
  },
  {
    id: "supported-qa-record-useful",
    label: "Record what was useful and what evidence or capability was missing",
  },
];

/** Seeded into copied reports so feedback stays attached to the current capability. */
export const PLAN_DOGFOOD_SUGGESTED_FOLLOW_UPS: string[] = [
  "Complete explicit review and native Graph publication for selected extraction candidates.",
  "Keep supported facts separate from unproven latest-source or complete-comparison claims.",
];

export function dogfoodModeFromLocation(location: Location = window.location): boolean {
  return new URLSearchParams(location.search).get("dogfood") === "1";
}

export function planDogfoodStorageKey(sessionDescriptor: PlanSessionDescriptor): string {
  return [
    "dmb.planDogfood",
    sessionDescriptor.campaignId,
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
