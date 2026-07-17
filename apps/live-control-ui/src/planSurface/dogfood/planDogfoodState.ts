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
 * Operator measurement checklist for the accepted S1 slice only:
 * conversational latest-recap sensemaking (U1 / A1 / A2).
 * Board save/recovery, Tripod continuity, and creative authoring are out of scope.
 */
export const PLAN_DOGFOOD_CHECKLIST: PlanDogfoodChecklistItem[] = [
  {
    id: "open-s1-plan",
    label: "Open /plan?dogfood=1&campaign=longmont-c2&session=24",
    description:
      "Focus memory/graph on session-24 (latest admitted recap). Live packet may still be session-22.",
  },
  {
    id: "confirm-focus",
    label: "Confirm Ask focus / World Graph focus is session-24 (or the latest admitted recap)",
    description: "Dogfood panel snapshot should show session focus, not world-union.",
  },
  {
    id: "open-ask-hermes",
    label: "Open Ask DungeonBuddy on a fresh Hermes thread",
    description: "New Plan threads use Hermes by default. Do not switch to Live for this slice.",
  },
  {
    id: "ask-s1-question",
    label: 'Ask: "What changed after the latest ingested recap?"',
    description:
      "Use the populated pill or type it verbatim. Free-form text is the task; the pill is only a starting prompt.",
  },
  {
    id: "answer-names-boundary",
    label: "Answer names the latest admitted recap and the comparison boundary",
    description: "Expect session-24 vs graph head (typically session-23) at a pinned revision.",
  },
  {
    id: "answer-discloses-lag",
    label: "Lag + admitted recap appear in support, not the Hermes bubble",
    description:
      "Hermes chat = agent prose (or honest “no chat answer”). Separate panel: Latest-recap comparison support.",
  },
  {
    id: "answer-feels-sensemaking",
    label: "Hermes chat feels like co-GM sensemaking from Session 24, not a claim ledger",
    description: "Meaning first; lag/excerpt/IDs stay in support or inspection.",
  },
  {
    id: "inspect-grounding",
    label: "Inspect grounding: partial_coverage + admitted_recap_source_read",
    description:
      "Not no_admissible_claims, and not Hermes grounding contract error. World-head promote remains a separate open gap.",
  },
  {
    id: "optional-inspect-evidence",
    label: "(Optional) Open evidence / trace and confirm the lag story matches",
    description: "Supporting inspection only — do not require a full claim list.",
  },
  {
    id: "record-useful",
    label: "Record what felt useful as campaign sensemaking",
  },
  {
    id: "record-missing",
    label: "Record what still felt like a report, abstention, or missing co-GM move",
  },
];

/** Seeded into copied reports so operator feedback stays attached to the current slice. */
export const PLAN_DOGFOOD_SUGGESTED_FOLLOW_UPS: string[] = [
  "Ship UI/CLI to promote reviewed session extracts into World Graph head (Backlog READY).",
  "Phase 2: smallest CreativeOperationSession kernel (no domain generator yet).",
  "S2 later: Collect everything we know about this threat → clarify → draft statblock → promotion preview.",
  "Do not reopen the rejected empty-graph generic abstention path for S1.",
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
