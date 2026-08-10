import { createWorkspaceDocument } from "../api/liveApi";
import type {
  CreateWorkspaceDocumentRequest,
  WorldbuildingAuthorityState,
  WorldbuildingVisibilityState,
  WorkspaceDocumentRecord,
} from "../api/types";

/**
 * Kind-parameterized intentional create intent.
 * Surfaces own suggestions/wording; this module owns legal request construction.
 */
export type WorkspaceDocumentCreateIntent =
  | {
      kind: "plan";
      campaignId: string;
      title: string;
      targetSession: number | null;
      targetRelpath: string | null;
    }
  | {
      kind: "runbook";
      campaignId: string;
      title: string;
      targetSession: number | null;
      targetRelpath: string | null;
    }
  | {
      kind: "worldbuilding_source";
      campaignId: string;
      title: string;
      documentClass: string;
      authorityState: WorldbuildingAuthorityState;
      visibilityState: WorldbuildingVisibilityState;
    };

export type WorkspaceDocumentCreationPhase =
  | "idle"
  | "creating"
  | "created"
  | "activating"
  | "activated"
  | "create_failed"
  | "activation_failed";

export interface WorkspaceDocumentCreationState {
  phase: WorkspaceDocumentCreationPhase;
  record: WorkspaceDocumentRecord | null;
  error: string | null;
  /** Monotonic create-intent epoch; bumps on each new create and on supersession. */
  intentEpoch: number;
}

export interface WorkspaceDocumentCreateResult {
  record: WorkspaceDocumentRecord;
  intentToken: number;
  /**
   * False when a newer navigation/create intent superseded this create during the POST.
   * Callers must not auto-activate a non-current result.
   */
  intentCurrent: boolean;
}

export interface WorkspaceDocumentActivateResult {
  record: WorkspaceDocumentRecord;
  applied: boolean;
}

export class WorkspaceDocumentCreationError extends Error {
  readonly code: "busy" | "create_failed" | "activation_failed" | "invalid_intent";

  constructor(code: WorkspaceDocumentCreationError["code"], message: string) {
    super(message);
    this.name = "WorkspaceDocumentCreationError";
    this.code = code;
  }
}

/** Map a kind-aware intent to the existing registry create request. */
export function createWorkspaceDocumentRequestFromIntent(
  intent: WorkspaceDocumentCreateIntent,
): CreateWorkspaceDocumentRequest {
  if (intent.kind === "worldbuilding_source") {
    return {
      title: intent.title,
      campaign_id: intent.campaignId,
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: intent.documentClass,
      authority_state: intent.authorityState,
      visibility_state: intent.visibilityState,
    };
  }

  return {
    title: intent.title,
    campaign_id: intent.campaignId,
    kind: intent.kind,
    target_session: intent.targetSession,
    target_relpath: intent.targetRelpath,
  };
}

export interface WorkspaceDocumentCreationDeps {
  create?: (request: CreateWorkspaceDocumentRequest) => Promise<WorkspaceDocumentRecord>;
}

/**
 * Shared intentional-create lifecycle with intent-epoch supersession.
 *
 * - One POST per successful create intent.
 * - After create succeeds, activation retry never POSTs again (while intent remains current).
 * - Concurrent create while busy is rejected (does not queue a second POST).
 * - {@link supersedePendingCreateIntent} / {@link reconcileActivatedDocument} invalidate
 *   auto-activation of a late POST and retire retained create state when another document
 *   becomes authoritative through normal navigation.
 */
export function createWorkspaceDocumentCreationController(
  deps: WorkspaceDocumentCreationDeps = {},
) {
  const createFn = deps.create ?? createWorkspaceDocument;
  let phase: WorkspaceDocumentCreationPhase = "idle";
  let record: WorkspaceDocumentRecord | null = null;
  let error: string | null = null;
  let inFlight = false;
  let intentEpoch = 0;
  /** Token of the create that currently owns retained created/activation_failed state. */
  let retainedIntentToken = 0;

  const snapshot = (): WorkspaceDocumentCreationState => ({
    phase,
    record,
    error,
    intentEpoch,
  });

  function clearRetainedCreateState(): void {
    phase = "idle";
    record = null;
    error = null;
    retainedIntentToken = 0;
  }

  /**
   * Invalidate any in-flight or retained create intent so a late POST cannot
   * auto-activate, and so a later distinct create POSTs fresh.
   */
  function supersedePendingCreateIntent(): void {
    intentEpoch += 1;
    if (inFlight) {
      // Create/activate completion observes the epoch mismatch.
      return;
    }
    if (phase === "created" || phase === "activation_failed" || phase === "activating") {
      clearRetainedCreateState();
    }
  }

  /**
   * Reconcile create-controller state after an exact document becomes authoritative
   * through any path (selector, history, or create activation).
   */
  function reconcileActivatedDocument(documentId: string): void {
    intentEpoch += 1;
    if (inFlight) {
      return;
    }
    if (record != null && record.document_id === documentId) {
      phase = "activated";
      error = null;
      retainedIntentToken = 0;
      return;
    }
    if (phase === "created" || phase === "activation_failed" || phase === "activating") {
      clearRetainedCreateState();
    }
  }

  async function create(
    intent: WorkspaceDocumentCreateIntent,
  ): Promise<WorkspaceDocumentCreateResult> {
    if (inFlight) {
      throw new WorkspaceDocumentCreationError(
        "busy",
        "A workspace document create is already in flight",
      );
    }
    // Created-but-not-activated for the *current* intent: never mint a replacement.
    if (
      record != null &&
      retainedIntentToken === intentEpoch &&
      (phase === "created" || phase === "activation_failed")
    ) {
      return {
        record,
        intentToken: retainedIntentToken,
        intentCurrent: true,
      };
    }

    const token = ++intentEpoch;
    retainedIntentToken = token;
    inFlight = true;
    phase = "creating";
    error = null;
    try {
      const request = createWorkspaceDocumentRequestFromIntent(intent);
      const created = await createFn(request);
      const intentCurrent = token === intentEpoch;
      if (!intentCurrent) {
        // Superseded during POST: registry/selector still discover the new record;
        // do not retain it for auto-activate or reuse-as-next-create.
        clearRetainedCreateState();
        return { record: created, intentToken: token, intentCurrent: false };
      }
      record = created;
      phase = "created";
      error = null;
      retainedIntentToken = token;
      return { record: created, intentToken: token, intentCurrent: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create workspace document";
      if (token === intentEpoch) {
        phase = "create_failed";
        error = message;
        record = null;
        retainedIntentToken = 0;
      } else {
        clearRetainedCreateState();
      }
      throw new WorkspaceDocumentCreationError("create_failed", message);
    } finally {
      inFlight = false;
    }
  }

  /**
   * Admit/activate an already-created record. Does not POST.
   * `activateExact` should resolve/admit the exact `documentId` and return whether
   * activation applied (false = superseded/stale; not an activation failure).
   */
  async function activate(
    activateExact: (created: WorkspaceDocumentRecord) => Promise<boolean>,
  ): Promise<WorkspaceDocumentActivateResult> {
    if (record == null) {
      throw new WorkspaceDocumentCreationError(
        "activation_failed",
        "No created workspace document is available to activate",
      );
    }
    if (inFlight) {
      throw new WorkspaceDocumentCreationError(
        "busy",
        "A workspace document create/activate is already in flight",
      );
    }

    const token = retainedIntentToken;
    if (token !== intentEpoch) {
      return { applied: false, record };
    }

    inFlight = true;
    phase = "activating";
    error = null;
    const exact = record;
    try {
      const applied = await activateExact(exact);
      if (token !== intentEpoch) {
        // Superseded while activating — do not claim activation or failure.
        if (phase === "activating") {
          clearRetainedCreateState();
        }
        return { applied: false, record: exact };
      }
      if (applied) {
        phase = "activated";
        error = null;
        retainedIntentToken = 0;
      } else {
        // Stale / superseded at the load layer — keep created record for retry.
        phase = "created";
      }
      return { applied, record: exact };
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to open created workspace document";
      if (token !== intentEpoch) {
        clearRetainedCreateState();
        return { applied: false, record: exact };
      }
      phase = "activation_failed";
      error = message;
      throw new WorkspaceDocumentCreationError("activation_failed", message);
    } finally {
      inFlight = false;
    }
  }

  /** Convenience: create once, then activate only while the create intent remains current. */
  async function createThenActivate(
    intent: WorkspaceDocumentCreateIntent,
    activateExact: (created: WorkspaceDocumentRecord) => Promise<boolean>,
  ): Promise<WorkspaceDocumentActivateResult> {
    const created = await create(intent);
    if (!created.intentCurrent) {
      return { applied: false, record: created.record };
    }
    return activate(activateExact);
  }

  function reset(): void {
    if (inFlight) {
      throw new WorkspaceDocumentCreationError(
        "busy",
        "Cannot reset while create/activate is in flight",
      );
    }
    intentEpoch += 1;
    clearRetainedCreateState();
  }

  return {
    getState: snapshot,
    create,
    activate,
    createThenActivate,
    supersedePendingCreateIntent,
    reconcileActivatedDocument,
    reset,
  };
}

export type WorkspaceDocumentCreationController = ReturnType<
  typeof createWorkspaceDocumentCreationController
>;
