import type { LiveQueryResponse, PlanSessionDescriptor } from "../../api/types";

export const PREP_MEMORY_PROMPTS = [
  "What changed after the latest ingested recap?",
  "What unresolved threads matter for prep?",
  "Which NPCs are relevant next session?",
  "What threats should I have ready?",
  "What sources support this?",
] as const;

export function prepMemoryLabel(sessionDescriptor: PlanSessionDescriptor): string {
  return `Memory through Session ${sessionDescriptor.memorySession} · preparing Session ${sessionDescriptor.prepSession}`;
}

export function hasGrounding(answer: LiveQueryResponse): boolean {
  return Boolean(
    answer.context_packet?.admitted_evidence?.length
    || answer.citations?.length,
  );
}

export function answerHeading(answer: LiveQueryResponse): string {
  return hasGrounding(answer) ? "Grounded answer" : "Ungrounded draft";
}
