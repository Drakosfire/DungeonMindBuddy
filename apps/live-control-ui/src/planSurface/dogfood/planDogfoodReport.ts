import type { PlanSessionDescriptor } from "../types";
import type { PlanDogfoodChecklistItem, PlanDogfoodState } from "./planDogfoodState";

export function buildPlanDogfoodReport(args: {
  sessionDescriptor: PlanSessionDescriptor;
  checklist: PlanDogfoodChecklistItem[];
  state: PlanDogfoodState;
  saveStatusLabel: string;
  generatedAt: string;
}): string {
  const { sessionDescriptor, checklist, state, saveStatusLabel, generatedAt } = args;
  const { planningDocument } = sessionDescriptor;

  const checklistLines = checklist.map((item) => {
    const mark = state.checked[item.id] ? "x" : " ";
    return `- [${mark}] ${item.label}`;
  });

  const notesBlock = state.notes.trim() || "_No notes recorded._";
  const followUps = "- ";

  return [
    "# /plan Dogfood Report",
    "",
    `Campaign: ${sessionDescriptor.campaignLabel}`,
    `Prep session: ${sessionDescriptor.prepSession}`,
    `Memory session: ${sessionDescriptor.memorySession}`,
    `Document: ${planningDocument.title}`,
    `Target path: ${planningDocument.targetRelpath}`,
    `Save status: ${saveStatusLabel}`,
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
