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
 * Shared intentional-create lifecycle with a single in-flight latch.
 *
 * - One POST per successful create intent.
 * - After create succeeds, activation retry never POSTs again.
 * - Concurrent create while busy is rejected (does not queue a second POST).
 */
export function createWorkspaceDocumentCreationController(
  deps: WorkspaceDocumentCreationDeps = {},
) {
  const createFn = deps.create ?? createWorkspaceDocument;
  let phase: WorkspaceDocumentCreationPhase = "idle";
  let record: WorkspaceDocumentRecord | null = null;
  let error: string | null = null;
  let inFlight = false;

  const snapshot = (): WorkspaceDocumentCreationState => ({
    phase,
    record,
    error,
  });

  async function create(
    intent: WorkspaceDocumentCreateIntent,
  ): Promise<WorkspaceDocumentRecord> {
    if (inFlight) {
      throw new WorkspaceDocumentCreationError(
        "busy",
        "A workspace document create is already in flight",
      );
    }
    // Created-but-not-activated: never mint a replacement document.
    if (record != null && (phase === "created" || phase === "activation_failed" || phase === "activating")) {
      return record;
    }

    inFlight = true;
    phase = "creating";
    error = null;
    try {
      const request = createWorkspaceDocumentRequestFromIntent(intent);
      const created = await createFn(request);
      record = created;
      phase = "created";
      error = null;
      return created;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create workspace document";
      phase = "create_failed";
      error = message;
      throw new WorkspaceDocumentCreationError("create_failed", message);
    } finally {
      inFlight = false;
    }
  }

  /**
   * Admit/activate an already-created record. Does not POST.
   * `activate` should resolve/admit the exact `documentId` and return whether
   * activation applied (false = superseded/stale; not an activation failure).
   */
  async function activate(
    activateExact: (created: WorkspaceDocumentRecord) => Promise<boolean>,
  ): Promise<{ applied: boolean; record: WorkspaceDocumentRecord }> {
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

    inFlight = true;
    phase = "activating";
    error = null;
    const exact = record;
    try {
      const applied = await activateExact(exact);
      if (applied) {
        phase = "activated";
        error = null;
      } else {
        // Stale / superseded — keep created record; do not claim activation failure.
        phase = "created";
      }
      return { applied, record: exact };
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to open created workspace document";
      phase = "activation_failed";
      error = message;
      throw new WorkspaceDocumentCreationError("activation_failed", message);
    } finally {
      inFlight = false;
    }
  }

  /** Convenience: create once, then activate. Activation retry uses {@link activate}. */
  async function createThenActivate(
    intent: WorkspaceDocumentCreateIntent,
    activateExact: (created: WorkspaceDocumentRecord) => Promise<boolean>,
  ): Promise<{ applied: boolean; record: WorkspaceDocumentRecord }> {
    const created = await create(intent);
    return activate(activateExact);
  }

  function reset(): void {
    if (inFlight) {
      throw new WorkspaceDocumentCreationError(
        "busy",
        "Cannot reset while create/activate is in flight",
      );
    }
    phase = "idle";
    record = null;
    error = null;
  }

  return {
    getState: snapshot,
    create,
    activate,
    createThenActivate,
    reset,
  };
}

export type WorkspaceDocumentCreationController = ReturnType<
  typeof createWorkspaceDocumentCreationController
>;
