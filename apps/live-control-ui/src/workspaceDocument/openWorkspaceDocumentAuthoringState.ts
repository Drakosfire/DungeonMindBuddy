import type { WorkspaceDocumentSnapshot } from "../api/types";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import {
  buildInitialWorkspaceDocumentLocalState,
  type WorkspaceDocumentLocalKind,
  type WorkspaceDocumentLocalSurface,
  type WorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { reconcileLocalDraft, type ReconcileLocalDraftResult } from "./reconcileLocalDraft";

export interface OpenWorkspaceDocumentAuthoringArgs {
  snapshot: WorkspaceDocumentSnapshot;
  stored: WorkspaceDocumentLocalState | null;
  surface: WorkspaceDocumentLocalSurface;
  kind: WorkspaceDocumentLocalKind;
  /** Used when snapshot markdown is empty (typical draft with no file yet). */
  emptyMarkdownFallback?: unknown;
}

export interface OpenWorkspaceDocumentAuthoringResult {
  reconciliation: ReconcileLocalDraftResult;
  localState: WorkspaceDocumentLocalState | null;
  status: "ready" | "conflict" | "reject";
}

function chooseEditorContent(args: {
  reconciliation: ReconcileLocalDraftResult;
  emptyMarkdownFallback?: unknown;
}): { tiptapJson: unknown; exportedMarkdown: string; dirty: boolean } {
  const { reconciliation } = args;
  const snapshotMarkdown = reconciliation.markdown;

  if (reconciliation.kind === "dirty-match" && reconciliation.localState) {
    return {
      tiptapJson: reconciliation.localState.tiptap_json,
      exportedMarkdown: reconciliation.localState.exported_markdown,
      dirty: true,
    };
  }

  if (snapshotMarkdown.trim()) {
    const tiptapJson = markdownToTiptapDoc(snapshotMarkdown).doc;
    return {
      tiptapJson,
      exportedMarkdown: snapshotMarkdown,
      dirty: false,
    };
  }

  // Empty server file: keep an existing clean local draft when present.
  if (reconciliation.localState) {
    return {
      tiptapJson: reconciliation.localState.tiptap_json,
      exportedMarkdown: reconciliation.localState.exported_markdown,
      dirty: false,
    };
  }

  const tiptapJson = args.emptyMarkdownFallback ?? markdownToTiptapDoc("").doc;
  return {
    tiptapJson,
    exportedMarkdown: tiptapJsonToSemanticMarkdown(tiptapJson),
    dirty: false,
  };
}

export function openWorkspaceDocumentAuthoringState(
  args: OpenWorkspaceDocumentAuthoringArgs,
): OpenWorkspaceDocumentAuthoringResult {
  const reconciliation = reconcileLocalDraft(args.snapshot, args.stored);

  if (reconciliation.kind === "conflict") {
    return { reconciliation, localState: args.stored, status: "conflict" };
  }
  if (reconciliation.kind === "reject") {
    return { reconciliation, localState: null, status: "reject" };
  }

  const chosen = chooseEditorContent({
    reconciliation,
    emptyMarkdownFallback: args.emptyMarkdownFallback,
  });
  const now = new Date().toISOString();
  const localState: WorkspaceDocumentLocalState = {
    ...buildInitialWorkspaceDocumentLocalState({
      documentId: args.snapshot.record.document_id,
      title: args.snapshot.record.title,
      campaignId: args.snapshot.record.campaign_id,
      kind: args.kind,
      targetSession: args.snapshot.record.target_session,
      surface: args.surface,
      baseRevision: args.snapshot.loaded_revision,
      baseContentSha256: args.snapshot.content_sha256,
      starterContent: chosen.tiptapJson,
      now,
    }),
    tiptap_json: chosen.tiptapJson,
    exported_markdown: chosen.exportedMarkdown,
    dirty: chosen.dirty,
    updated_at: now,
    last_local_save_at: now,
  };

  return { reconciliation, localState, status: "ready" };
}
