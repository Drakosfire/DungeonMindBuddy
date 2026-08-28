import type { SurfaceInteractionWorkObjectIdentity } from "../surfaceInteraction/types";
import type { PlanDocumentDescriptor } from "./types";

export const PLAN_LOCAL_DRAFT_WORK_KIND = "plan-local-draft" as const;

export const PLAN_SHELL_WORK_KIND = "plan-shell" as const;

export const PLAN_LOCAL_DRAFT_POINTER_PREFIX = "dmb.planLocalDraftPointer.";

export interface PlanShellIdentity {
  campaignId: string;
  liveSession: number;
  memorySession: number | null;
}

export interface PlanLocalDraft {
  localId: string;
  campaignId: string;
  title: string;
  targetSession: number | null;
  targetRelpath: null;
}

export type PlanAuthoringShellState =
  | { kind: "resolving"; shell: PlanShellIdentity; requestedDocumentId: string | null }
  | {
      kind: "blank_ready";
      draft: PlanLocalDraft;
      selectorListAvailable: boolean;
    }
  | {
      kind: "promoting";
      draft: PlanLocalDraft;
      retainedCreateId: string | null;
      selectorListAvailable: boolean;
    }
  | { kind: "durable_ready"; document: PlanDocumentDescriptor }
  | {
      kind: "load_error";
      shell: PlanShellIdentity;
      requestedDocumentId: string | null;
      message: string;
      localDraft?: PlanLocalDraft;
      inventoryUnavailable?: boolean;
    };

export interface PlanResolveOutcome {
  requestedDocumentId: string | null;
  resolvedDocument: PlanDocumentDescriptor | null;
  resolveError: Error | null;
  selectorListAvailable: boolean;
  selectorListEmpty: boolean;
}

export function planLocalDraftPointerKey(campaignId: string): string {
  return `${PLAN_LOCAL_DRAFT_POINTER_PREFIX}${campaignId}`;
}

export function formatPlanLocalDraftId(opaqueId: string): string {
  const trimmed = opaqueId.trim();
  if (trimmed.startsWith("local-plan:")) return trimmed;
  return `local-plan:${trimmed}`;
}

export function opaqueIdFromPlanLocalDraftId(localId: string): string {
  return localId.startsWith("local-plan:") ? localId.slice("local-plan:".length) : localId;
}

export function createOpaqueLocalDraftId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `draft-${Date.now()}`;
}

/** Retain one unpromoted local draft identity per campaign. */
export function resolveOrCreatePlanLocalDraftIdentity(
  campaignId: string,
  storage: Pick<Storage, "getItem" | "setItem">,
): string {
  const pointerKey = planLocalDraftPointerKey(campaignId);
  const existing = storage.getItem(pointerKey)?.trim();
  if (existing) {
    return formatPlanLocalDraftId(existing);
  }
  const opaque = createOpaqueLocalDraftId();
  storage.setItem(pointerKey, opaque);
  return formatPlanLocalDraftId(opaque);
}

export function clearPlanLocalDraftPointer(
  campaignId: string,
  storage: Pick<Storage, "removeItem">,
): void {
  storage.removeItem(planLocalDraftPointerKey(campaignId));
}

export function createPlanLocalDraftIdentity(
  campaignId: string,
  storage: Pick<Storage, "getItem" | "setItem">,
): string {
  return resolveOrCreatePlanLocalDraftIdentity(campaignId, storage);
}

export function createPlanLocalDraftMetadata(args: {
  campaignId: string;
  title: string;
  targetSession: number | null;
  localId?: string;
  storage?: Pick<Storage, "getItem" | "setItem">;
}): PlanLocalDraft {
  const storage = args.storage ?? (typeof localStorage !== "undefined" ? localStorage : undefined);
  const localId = args.localId
    ?? (storage
      ? resolveOrCreatePlanLocalDraftIdentity(args.campaignId, storage)
      : formatPlanLocalDraftId(createOpaqueLocalDraftId()));
  return {
    localId,
    campaignId: args.campaignId,
    title: args.title,
    targetSession: args.targetSession,
    targetRelpath: null,
  };
}

export function isNoActivePlanningDocumentsError(error: unknown): boolean {
  return error instanceof Error && error.name === "NoActivePlanningDocumentsError";
}

export function nextPlanShellState(args: {
  shell: PlanShellIdentity;
  outcome: PlanResolveOutcome;
  blankDraft: PlanLocalDraft | null;
}): PlanAuthoringShellState {
  const { shell, outcome, blankDraft } = args;
  const { requestedDocumentId, resolvedDocument, resolveError, selectorListAvailable, selectorListEmpty } =
    outcome;

  if (resolvedDocument) {
    return { kind: "durable_ready", document: resolvedDocument };
  }

  if (resolveError) {
    if (
      !requestedDocumentId
      && isNoActivePlanningDocumentsError(resolveError)
      && selectorListAvailable
      && selectorListEmpty
      && blankDraft
    ) {
      return {
        kind: "blank_ready",
        draft: blankDraft,
        selectorListAvailable: true,
      };
    }
    if (!requestedDocumentId && blankDraft && !selectorListAvailable) {
      return {
        kind: "load_error",
        shell,
        requestedDocumentId,
        message:
          "Active Plan inventory is unavailable; target session cannot be chosen safely.",
        localDraft: blankDraft,
        inventoryUnavailable: true,
      };
    }
    return {
      kind: "load_error",
      shell,
      requestedDocumentId,
      message: resolveError.message,
    };
  }

  if (!requestedDocumentId && selectorListAvailable && selectorListEmpty && blankDraft) {
    return {
      kind: "blank_ready",
      draft: blankDraft,
      selectorListAvailable: true,
    };
  }

  return {
    kind: "resolving",
    shell,
    requestedDocumentId,
  };
}

export function planShellWorkObject(
  state: PlanAuthoringShellState,
): SurfaceInteractionWorkObjectIdentity {
  switch (state.kind) {
    case "blank_ready":
      return { kind: PLAN_LOCAL_DRAFT_WORK_KIND, id: state.draft.localId };
    case "promoting":
      if (state.retainedCreateId) {
        return { kind: "document", id: state.retainedCreateId };
      }
      return { kind: PLAN_LOCAL_DRAFT_WORK_KIND, id: state.draft.localId };
    case "durable_ready":
      return { kind: "document", id: state.document.documentId };
    case "resolving":
      if (state.requestedDocumentId) {
        return { kind: "document", id: state.requestedDocumentId };
      }
      return { kind: PLAN_SHELL_WORK_KIND, id: `resolving:${state.shell.campaignId}` };
    case "load_error":
      if (state.localDraft && state.inventoryUnavailable) {
        return { kind: PLAN_LOCAL_DRAFT_WORK_KIND, id: state.localDraft.localId };
      }
      if (state.requestedDocumentId) {
        return { kind: "document", id: state.requestedDocumentId };
      }
      return { kind: PLAN_SHELL_WORK_KIND, id: `error:${state.shell.campaignId}` };
  }
}

export function planShellAgentDocumentId(state: PlanAuthoringShellState): string | null {
  if (state.kind === "durable_ready") {
    return state.document.documentId;
  }
  if (state.kind === "promoting" && state.retainedCreateId) {
    return state.retainedCreateId;
  }
  return null;
}

export function planShellCanvasDocumentId(state: PlanAuthoringShellState): string | null {
  if (state.kind === "durable_ready") {
    return state.document.documentId;
  }
  if (state.kind === "promoting" && state.retainedCreateId) {
    return state.retainedCreateId;
  }
  return null;
}

export function retainCreatedPlan(
  state: PlanAuthoringShellState,
  documentId: string,
): PlanAuthoringShellState {
  if (state.kind !== "blank_ready" && state.kind !== "promoting") {
    return state;
  }
  return {
    kind: "promoting",
    draft: state.draft,
    retainedCreateId: documentId,
    selectorListAvailable: state.selectorListAvailable,
  };
}

export function adoptCreatedPlanIdentity(
  record: PlanDocumentDescriptor,
): PlanAuthoringShellState {
  return { kind: "durable_ready", document: record };
}

export function blankSaveDisabledReason(state: PlanAuthoringShellState): string | null {
  if (state.kind === "blank_ready" || state.kind === "promoting") {
    if (!state.selectorListAvailable) {
      return "Active Plan inventory is unavailable; target session cannot be chosen safely.";
    }
    if (state.draft.targetSession == null) {
      return "No durable target session is available yet.";
    }
  }
  if (state.kind === "promoting" && !state.retainedCreateId) {
    return "Creating Plan…";
  }
  if (state.kind === "load_error") {
    if (state.inventoryUnavailable) {
      return "Active Plan inventory is unavailable; target session cannot be chosen safely.";
    }
    return "Document failed to load; retry or choose another document.";
  }
  if (state.kind === "resolving") {
    return "Document is still loading.";
  }
  return null;
}

export function planLocalDraftToDescriptor(draft: PlanLocalDraft): PlanDocumentDescriptor {
  return {
    documentId: draft.localId,
    title: draft.title,
    campaignId: draft.campaignId,
    targetSession: draft.targetSession,
    targetRelpath: draft.targetRelpath,
    storageKey: `dmb.workspaceDocument.${draft.localId}`,
    status: "active",
    contentStatus: "draft",
    revision: 0,
    kind: "plan",
    description: draft.targetSession != null
      ? `Session ${draft.targetSession} preparation board (local draft).`
      : "Local preparation draft.",
  };
}
