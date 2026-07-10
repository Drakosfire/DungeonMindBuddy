import type { TiptapMarkdownWriteCommitResponse } from "../../api/types";

export type PlanMarkdownSaveStatus = "idle" | "dirty" | "saving" | "committed" | "error";

export interface PlanMarkdownSaveState {
  status: PlanMarkdownSaveStatus;
  committed?: TiptapMarkdownWriteCommitResponse;
  error?: string;
  lastCommittedAt?: string;
  warnings?: string[];
  diagnostics?: string[];
}

export function planMarkdownSaveStatusLabel(state: PlanMarkdownSaveState): string {
  switch (state.status) {
    case "idle":
      return "Local draft · not yet saved to Markdown";
    case "dirty":
      return "Local changes since last Markdown save";
    case "saving":
      return "Saving to Markdown…";
    case "committed":
      return "Saved to Markdown · local edits may diverge after further changes";
    case "error":
      return state.error ?? "Markdown save failed";
    default:
      return "Local draft · not yet saved to Markdown";
  }
}
