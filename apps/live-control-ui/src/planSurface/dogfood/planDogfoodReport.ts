import type { PlanSessionDescriptor } from "../types";
import type { WorldGraphProjectionSnapshot } from "../../api/types";
import type { PlanDogfoodChecklistItem, PlanDogfoodState } from "./planDogfoodState";
import { PLAN_DOGFOOD_SUGGESTED_FOLLOW_UPS } from "./planDogfoodState";

export function buildPlanDogfoodReport(args: {
  sessionDescriptor: PlanSessionDescriptor;
  checklist: PlanDogfoodChecklistItem[];
  state: PlanDogfoodState;
  saveStatusLabel: string;
  graphSnapshot: WorldGraphProjectionSnapshot | null;
  generatedAt: string;
}): string {
  const { sessionDescriptor, checklist, state, saveStatusLabel, graphSnapshot, generatedAt } = args;
  const { planningDocument } = sessionDescriptor;

  const checklistLines = checklist.map((item) => {
    const mark = state.checked[item.id] ? "x" : " ";
    return `- [${mark}] ${item.label}`;
  });

  const notesBlock = state.notes.trim() || "_No notes recorded._";
  const followUps = PLAN_DOGFOOD_SUGGESTED_FOLLOW_UPS.map((item) => `- ${item}`).join("\n");

  return [
    "# /plan Dogfood Report",
    "",
    `Campaign: ${sessionDescriptor.campaignLabel}`,
    `Target session: ${planningDocument.targetSession ?? "unset"}`,
    `Memory session: ${sessionDescriptor.memorySession ?? "none (world union)"}`,
    `Document: ${planningDocument.title}`,
    `Target path: ${planningDocument.targetRelpath}`,
    `Save status: ${saveStatusLabel}`,
    `World Graph revision: ${graphSnapshot?.revisionId ?? "unavailable"}`,
    `World Graph head revision: ${graphSnapshot?.headRevisionId ?? "unavailable"}`,
    `World Graph focus: ${graphSnapshot?.focus.sessionId ?? "none"}`,
    `Generated at: ${generatedAt}`,
    "",
    "## Checklist",
    "",
    ...checklistLines,
    "",
    "## Notes",
    "",
    notesBlock,
    "",
    "## Suggested follow-ups",
    "",
    followUps,
    "",
  ].join("\n");
}
