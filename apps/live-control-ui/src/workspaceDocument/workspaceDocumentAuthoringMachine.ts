/**
 * Pure authoring lifecycle for one workspace-document UUID.
 * Surfaces adapt presentation; they do not invent parallel save/open transitions.
 */

export type WorkspaceDocumentAuthoringPhase =
  | "unloaded"
  | "loading"
  | "ready_clean"
  | "ready_dirty"
  | "preparing"
  | "committing"
  | "committed"
  | "committed_verification_pending"
  | "conflict"
  | "load_error"
  | "save_error";

export type WorkspaceDocumentAuthoringEvent =
  | { type: "OPEN_STARTED" }
  | { type: "OPEN_READY"; dirty: boolean }
  | { type: "OPEN_CONFLICT"; reason: string }
  | { type: "OPEN_FAILED"; message: string }
  | { type: "EDIT" }
  | { type: "PREPARE_STARTED" }
  | { type: "COMMIT_STARTED" }
  | { type: "COMMIT_SUCCEEDED" }
  | { type: "VERIFICATION_STARTED" }
  | { type: "VERIFICATION_SUCCEEDED"; dirty: boolean }
  | { type: "VERIFICATION_MISMATCH"; reason: string }
  | { type: "VERIFICATION_FAILED"; message: string }
  | { type: "SAVE_FAILED"; message: string }
  | { type: "DISCARD_STARTED" }
  | { type: "RELOAD_STARTED" }
  | { type: "CLEAR_ERROR" };

export interface WorkspaceDocumentAuthoringMachineState {
  phase: WorkspaceDocumentAuthoringPhase;
  error: string | null;
  conflictReason: string | null;
}

export function initialAuthoringMachineState(): WorkspaceDocumentAuthoringMachineState {
  return { phase: "unloaded", error: null, conflictReason: null };
}

export function reduceAuthoringMachine(
  state: WorkspaceDocumentAuthoringMachineState,
  event: WorkspaceDocumentAuthoringEvent,
): WorkspaceDocumentAuthoringMachineState {
  switch (event.type) {
    case "OPEN_STARTED":
    case "RELOAD_STARTED":
    case "DISCARD_STARTED":
      return { phase: "loading", error: null, conflictReason: null };
    case "OPEN_READY":
      return {
        phase: event.dirty ? "ready_dirty" : "ready_clean",
        error: null,
        conflictReason: null,
      };
    case "OPEN_CONFLICT":
      return { phase: "conflict", error: null, conflictReason: event.reason };
    case "OPEN_FAILED":
      return { phase: "load_error", error: event.message, conflictReason: null };
    case "EDIT":
      if (
        state.phase === "ready_clean"
        || state.phase === "committed"
        || state.phase === "save_error"
        || state.phase === "committed_verification_pending"
      ) {
        return { ...state, phase: "ready_dirty", error: state.phase === "save_error" ? state.error : null };
      }
      if (state.phase === "ready_dirty") return state;
      return state;
    case "PREPARE_STARTED":
      return { ...state, phase: "preparing", error: null };
    case "COMMIT_STARTED":
      return { ...state, phase: "committing", error: null };
    case "COMMIT_SUCCEEDED":
      return { phase: "committed", error: null, conflictReason: null };
    case "VERIFICATION_STARTED":
      return { phase: "committed_verification_pending", error: null, conflictReason: null };
    case "VERIFICATION_SUCCEEDED":
      return {
        phase: event.dirty ? "ready_dirty" : "ready_clean",
        error: null,
        conflictReason: null,
      };
    case "VERIFICATION_MISMATCH":
      return { phase: "conflict", error: null, conflictReason: event.reason };
    case "VERIFICATION_FAILED":
      // Commit already succeeded; keep committed truth and surface verification issue.
      return {
        phase: "committed_verification_pending",
        error: event.message,
        conflictReason: null,
      };
    case "SAVE_FAILED":
      return {
        phase: "save_error",
        error: event.message,
        conflictReason: state.conflictReason,
      };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

export function statusLabelForPhase(args: {
  phase: WorkspaceDocumentAuthoringPhase;
  contentStatus: "draft" | "committed" | null;
  conflictReason?: string | null;
  error?: string | null;
}): string {
  switch (args.phase) {
    case "unloaded":
    case "loading":
      return "Loading document…";
    case "preparing":
      return "Preparing save…";
    case "committing":
      return "Saving…";
    case "committed":
      return "Committed";
    case "committed_verification_pending":
      return args.error
        ? `Committed (verification pending: ${args.error})`
        : "Committed (verification pending)";
    case "conflict":
      return args.conflictReason ?? "Conflict — reload or discard local draft.";
    case "load_error":
      return args.error ?? "Unable to load document.";
    case "save_error":
      return args.error ?? "Save failed.";
    case "ready_dirty":
      return "Unsaved local changes";
    case "ready_clean":
      if (args.contentStatus === "committed") return "Committed";
      return "Draft";
    default:
      return "Draft";
  }
}

export function isEditorInteractive(phase: WorkspaceDocumentAuthoringPhase): boolean {
  return (
    phase === "ready_clean"
    || phase === "ready_dirty"
    || phase === "save_error"
    || phase === "committed"
    || phase === "committed_verification_pending"
  );
}

export function isSaveDisabled(phase: WorkspaceDocumentAuthoringPhase): boolean {
  return (
    phase === "unloaded"
    || phase === "loading"
    || phase === "preparing"
    || phase === "committing"
    || phase === "conflict"
    || phase === "load_error"
  );
}
