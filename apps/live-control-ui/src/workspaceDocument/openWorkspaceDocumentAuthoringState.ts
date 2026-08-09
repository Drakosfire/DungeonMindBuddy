import type { WorkspaceDocumentSnapshot } from "../api/types";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { hasBlockingMarkdownImportDiagnostics, markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { semanticMarkdownSerializationDiagnostics } from "../tiptap/markdown/semanticMarkdownSafety";
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
  snapshotMarkdown: string;
  emptyMarkdownFallback?: unknown;
}): { tiptapJson: unknown; exportedMarkdown: string; dirty: boolean } {
  const { reconciliation, snapshotMarkdown } = args;

  if (reconciliation.kind === "dirty-match" && reconciliation.localState) {
    const localState = reconciliation.localState;
    if (hasBlockingMarkdownImportDiagnostics(snapshotMarkdown)) {
      // Keep local TipTap projection edits; save admission still uses the
      // authoritative unsafe snapshot markdown (fail closed on durable write).
      return {
        tiptapJson: localState.tiptap_json,
        exportedMarkdown: snapshotMarkdown,
        dirty: true,
      };
    }
    // Parser upgrades should rehydrate from Markdown when that Markdown is a
    // lossless representation. If the local TipTap draft contains a structure
    // this serializer cannot represent, keep the richer local JSON instead of
    // destroying an unsaved edit during reload.
    if (semanticMarkdownSerializationDiagnostics(localState.tiptap_json).length > 0) {
      return {
        tiptapJson: localState.tiptap_json,
        exportedMarkdown: localState.exported_markdown,
        dirty: true,
      };
    }
    return {
      tiptapJson: markdownToTiptapDoc(localState.exported_markdown).doc,
      exportedMarkdown: localState.exported_markdown,
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
    snapshotMarkdown: args.snapshot.markdown,
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
