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
import { assertSurfaceAuthority } from "./surfaceAuthority";

export interface OpenWorkspaceDocumentAuthoringArgs {
  documentId: string;
  snapshot: WorkspaceDocumentSnapshot;
  stored: WorkspaceDocumentLocalState | null;
  surface: WorkspaceDocumentLocalSurface;
  kind: WorkspaceDocumentLocalKind;
  /** Used when snapshot markdown is empty (typical draft with no file yet). */
  emptyMarkdownFallback?: unknown;
  allowDiscarded?: boolean;
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
    // Re-parse from exported Markdown so importer upgrades (callouts, tables,
    // marks) apply on reload. Stale tiptap_json from an older parser must not
    // silently win when base revision still matches (no conflict banner).
    const exportedMarkdown = reconciliation.localState.exported_markdown;
    return {
      tiptapJson: markdownToTiptapDoc(exportedMarkdown).doc,
      exportedMarkdown,
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
  const authority = assertSurfaceAuthority({
    requestedDocumentId: args.documentId,
    requestedKind: args.kind,
    surface: args.surface,
    record: args.snapshot.record,
    loadedRevision: args.snapshot.loaded_revision,
    allowDiscarded: args.allowDiscarded,
  });
  if (!authority.ok) {
    return {
      reconciliation: {
        kind: "reject",
        markdown: args.snapshot.markdown,
        localState: null,
        rejectReason: authority.rejectReason,
      },
      localState: null,
      status: "reject",
    };
  }

  const authoritativeKind = authority.authoritativeKind ?? args.kind;
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
      kind: authoritativeKind,
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
