import type {
  TiptapMarkdownWriteCommitResponse,
  TiptapMarkdownWritePrepareResponse,
} from "../../api/types";

export type PlanMarkdownSaveStatus =
  | "idle"
  | "dirty"
  | "preparing"
  | "preview_ready"
  | "committing"
  | "committed"
  | "error";

export interface PlanMarkdownSaveState {
  status: PlanMarkdownSaveStatus;
  prepared?: TiptapMarkdownWritePrepareResponse;
  preparedMarkdown?: string;
  committed?: TiptapMarkdownWriteCommitResponse;
  error?: string;
  lastCommittedAt?: string;
}

export function planMarkdownSaveStatusLabel(state: PlanMarkdownSaveState): string {
  switch (state.status) {
    case "idle":
      return "Local draft · not yet saved to Markdown";
    case "dirty":
      return state.error ?? "Local changes since last Markdown save";
    case "preparing":
      return "Preparing Markdown save preview…";
    case "preview_ready":
      return "Preview ready · review diff before commit";
    case "committing":
      return "Committing Markdown save…";
    case "committed":
      return "Saved to Markdown · local edits may diverge after further changes";
    case "error":
      return state.error ?? "Markdown save failed";
    default:
      return "Local draft · not yet saved to Markdown";
  }
}
