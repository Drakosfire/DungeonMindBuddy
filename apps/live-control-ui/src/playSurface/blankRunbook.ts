import {
  commitTiptapMarkdownWrite,
  createWorkspaceDocument,
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

export class BlankRunbookCreateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BlankRunbookCreateError";
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
  generateBeatId?: () => string;
}

export interface CreateBlankRunbookResult {
  record: WorkspaceDocumentRecord;
  beatId: string;
  markdown: string;
}

export async function createBlankRunbook(
  campaignId: string,
  deps: CreateBlankRunbookDeps = {},
): Promise<CreateBlankRunbookResult> {
  const cleanedCampaign = campaignId.trim();
  if (!cleanedCampaign) {
    throw new BlankRunbookCreateError("Campaign is required to create a Runbook.");
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
  const prepare = deps.prepare ?? prepareTiptapMarkdownWrite;
  const prepared = await prepare({
    document_id: created.record.document_id,
    markdown,
    expected_revision: created.record.revision,
  });
  if (!prepared.writer_ok || !prepared.writer_confirm_token) {
    throw new BlankRunbookCreateError("Blank Runbook prepare did not return a commit token.");
  }
  const commit = deps.commit ?? commitTiptapMarkdownWrite;
  const committed = await commit({
    document_id: created.record.document_id,
    markdown,
    writer_confirm_token: prepared.writer_confirm_token,
    expected_revision: created.record.revision,
  });
  return {
    record: committed.committed_record,
    beatId,
    markdown,
  };
}
