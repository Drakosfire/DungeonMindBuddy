import {
  LiveApiError,
  commitTiptapMarkdownWrite,
  createWorkspaceDocument,
  getWorkspaceDocumentSnapshot,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import {
  createWorkspaceDocumentCreationController,
  type WorkspaceDocumentCreateIntent,
} from "../workspaceDocument/workspaceDocumentCreation";
import {
  formatPlayableElementMarker,
  generatePlayableElementId,
} from "../tiptap/playable/playableElementIdentity";

export const BLANK_RUNBOOK_TITLE = "Blank Runbook";
export const UNTITLED_BEAT_HEADING = "Untitled Beat";

export type BlankRunbookAttempt = {
  documentId: string;
  beatId: string;
  markdown: string;
  expectedRevision: number;
  campaignId: string;
};

export class BlankRunbookCreateError extends Error {
  readonly attempt: BlankRunbookAttempt | null;

  constructor(message: string, attempt: BlankRunbookAttempt | null = null) {
    super(message);
    this.name = "BlankRunbookCreateError";
    this.attempt = attempt;
  }
}

export function resolveBlankRunbookCampaignId(
  productCampaignId: string | null | undefined,
  explicitCampaignId: string | null | undefined,
): string | null {
  const product = productCampaignId?.trim() ?? "";
  if (product) return product;
  const explicit = explicitCampaignId?.trim() ?? "";
  return explicit || null;
}

/** World Graph lens is product context only when focus validation succeeded. */
export function campaignIdFromProductContext(
  world: {
    focusValidationStatus: string;
    lens: { focus: { campaignId: string } | null };
  } | null,
): string | null {
  if (world == null || world.focusValidationStatus !== "valid") return null;
  const id = world.lens.focus?.campaignId?.trim() ?? "";
  return id || null;
}

export function formatBlankRunbookMarkdown(beatId: string): string {
  const marker = formatPlayableElementMarker({
    kind: "beat",
    id: beatId,
    version: "v2",
    beatKind: "spine",
  });
  return `${marker}\n## ${UNTITLED_BEAT_HEADING}\n`;
}

export interface CreateBlankRunbookDeps {
  create?: typeof createWorkspaceDocument;
  prepare?: typeof prepareTiptapMarkdownWrite;
  commit?: typeof commitTiptapMarkdownWrite;
  getSnapshot?: typeof getWorkspaceDocumentSnapshot;
  generateBeatId?: () => string;
  attempt?: BlankRunbookAttempt | null;
  onAttemptRetained?: (attempt: BlankRunbookAttempt) => void;
}

export interface CreateBlankRunbookResult {
  record: WorkspaceDocumentRecord;
  beatId: string;
  markdown: string;
}

function errorStatus(error: unknown): number | null {
  return error instanceof LiveApiError ? error.status : null;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function throwWithAttempt(message: string, attempt: BlankRunbookAttempt): never {
  throw new BlankRunbookCreateError(message, attempt);
}

async function reconcileExactDocument(
  attempt: BlankRunbookAttempt,
  getSnapshot: typeof getWorkspaceDocumentSnapshot,
): Promise<CreateBlankRunbookResult | { status: "not_committed"; expectedRevision: number } | { status: "unknown" }> {
  try {
    const snapshot = await getSnapshot(attempt.documentId);
    if (snapshot.record.document_id !== attempt.documentId) {
      throwWithAttempt("Blank Runbook snapshot is not the retained document.", attempt);
    }
    if (snapshot.record.content_status === "committed") {
      if (snapshot.markdown !== attempt.markdown) {
        throwWithAttempt(
          "Committed Runbook does not match this blank create attempt.",
          attempt,
        );
      }
      return {
        record: snapshot.record,
        beatId: attempt.beatId,
        markdown: attempt.markdown,
      };
    }
    return { status: "not_committed", expectedRevision: snapshot.record.revision };
  } catch (error) {
    if (error instanceof BlankRunbookCreateError) throw error;
    return { status: "unknown" };
  }
}

async function prepareAndCommit(
  attempt: BlankRunbookAttempt,
  deps: CreateBlankRunbookDeps,
): Promise<CreateBlankRunbookResult> {
  const prepare = deps.prepare ?? prepareTiptapMarkdownWrite;
  const commit = deps.commit ?? commitTiptapMarkdownWrite;
  const getSnapshot = deps.getSnapshot ?? getWorkspaceDocumentSnapshot;

  let prepared;
  try {
    prepared = await prepare({
      document_id: attempt.documentId,
      markdown: attempt.markdown,
      expected_revision: attempt.expectedRevision,
    });
  } catch (error) {
    throwWithAttempt(
      errorMessage(error, "Blank Runbook prepare failed."),
      attempt,
    );
  }
  if (!prepared.writer_ok || !prepared.writer_confirm_token) {
    throwWithAttempt("Blank Runbook prepare did not return a commit token.", attempt);
  }

  try {
    const committed = await commit({
      document_id: attempt.documentId,
      markdown: attempt.markdown,
      writer_confirm_token: prepared.writer_confirm_token,
      expected_revision: attempt.expectedRevision,
    });
    return {
      record: committed.committed_record,
      beatId: attempt.beatId,
      markdown: attempt.markdown,
    };
  } catch (error) {
    const status = errorStatus(error);
    const certainFailure = status === 409 || status === 422 || status === 400;
    if (!certainFailure) {
      const reconciled = await reconcileExactDocument(attempt, getSnapshot);
      if ("record" in reconciled) return reconciled;
    }
    throwWithAttempt(
      `${errorMessage(error, "Blank Runbook commit could not be confirmed.")} Retry will keep document ${attempt.documentId}.`,
      attempt,
    );
  }
}

export async function createBlankRunbook(
  campaignId: string,
  deps: CreateBlankRunbookDeps = {},
): Promise<CreateBlankRunbookResult> {
  const retained = deps.attempt ?? null;
  const cleanedCampaign = (retained?.campaignId ?? campaignId).trim();
  if (!cleanedCampaign) {
    throw new BlankRunbookCreateError("Campaign is required to create a Runbook.");
  }

  if (retained) {
    deps.onAttemptRetained?.(retained);
    const getSnapshot = deps.getSnapshot ?? getWorkspaceDocumentSnapshot;
    const reconciled = await reconcileExactDocument(retained, getSnapshot);
    if ("record" in reconciled) return reconciled;
    const retryAttempt: BlankRunbookAttempt = {
      ...retained,
      expectedRevision: reconciled.status === "not_committed"
        ? reconciled.expectedRevision
        : retained.expectedRevision,
    };
    deps.onAttemptRetained?.(retryAttempt);
    return prepareAndCommit(retryAttempt, deps);
  }

  const beatId = deps.generateBeatId?.() ?? generatePlayableElementId("beat");
  const markdown = formatBlankRunbookMarkdown(beatId);
  const intent: WorkspaceDocumentCreateIntent = {
    kind: "runbook",
    campaignId: cleanedCampaign,
    title: BLANK_RUNBOOK_TITLE,
    targetSession: null,
    targetRelpath: null,
  };
  const controller = createWorkspaceDocumentCreationController({
    create: deps.create ?? createWorkspaceDocument,
  });
  const created = await controller.create(intent);
  const attempt: BlankRunbookAttempt = {
    documentId: created.record.document_id,
    beatId,
    markdown,
    expectedRevision: created.record.revision,
    campaignId: cleanedCampaign,
  };
  deps.onAttemptRetained?.(attempt);
  return prepareAndCommit(attempt, deps);
}
