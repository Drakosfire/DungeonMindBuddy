import type { WorkspaceDocumentSnapshot } from "../api/types";
import { hasBlockingMarkdownImportDiagnostics } from "../tiptap/markdown/markdownToTiptap";
import type { WorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";

export type ReconcileLocalDraftKind =
  | "none"
  | "clean-match"
  | "dirty-match"
  | "conflict"
  | "reject";

export interface ReconcileLocalDraftResult {
  kind: ReconcileLocalDraftKind;
  markdown: string;
  localState: WorkspaceDocumentLocalState | null;
  conflictReason?: string;
  rejectReason?: string;
}

function baseMatchesSnapshot(
  localState: WorkspaceDocumentLocalState,
  snapshot: WorkspaceDocumentSnapshot,
): boolean {
  return (
    localState.base_revision === snapshot.loaded_revision
    && localState.base_content_sha256 === snapshot.content_sha256
  );
}

function hasUnknownMigratedBase(localState: WorkspaceDocumentLocalState): boolean {
  return localState.base_revision === 0 && localState.base_content_sha256 === "";
}

export function reconcileLocalDraft(
  snapshot: WorkspaceDocumentSnapshot,
  localState: WorkspaceDocumentLocalState | null,
): ReconcileLocalDraftResult {
  if (localState === null) {
    return {
      kind: "none",
      markdown: snapshot.markdown,
      localState: null,
    };
  }

  if (localState.document_id !== snapshot.record.document_id) {
    return {
      kind: "reject",
      markdown: snapshot.markdown,
      localState: null,
      rejectReason: "Local draft document_id does not match the loaded snapshot.",
    };
  }

  if (localState.dirty) {
    if (hasUnknownMigratedBase(localState)) {
      return {
        kind: "conflict",
        markdown: snapshot.markdown,
        localState,
        conflictReason: "Local draft is dirty but lacks a trusted base revision fingerprint.",
      };
    }
    if (baseMatchesSnapshot(localState, snapshot)) {
      // Post-commit local drafts can remain dirty:true while Markdown already
      // matches the refreshed snapshot (Save succeeded; overlay flag stale).
      // Treat byte-identical body as clean so hard reload reopens clean —
      // except when the source is import-unsafe: exported_markdown is kept
      // authoritative while TipTap may still hold unsaved projection edits.
      if (
        localState.exported_markdown === snapshot.markdown
        && !hasBlockingMarkdownImportDiagnostics(snapshot.markdown)
      ) {
        return {
          kind: "clean-match",
          markdown: snapshot.markdown,
          localState,
        };
      }
      return {
        kind: "dirty-match",
        markdown: localState.exported_markdown,
        localState,
      };
    }
    return {
      kind: "conflict",
      markdown: snapshot.markdown,
      localState,
      conflictReason: "Server content changed while a dirty local draft was stored.",
    };
  }

  if (baseMatchesSnapshot(localState, snapshot) || hasUnknownMigratedBase(localState)) {
    return {
      kind: "clean-match",
      markdown: snapshot.markdown,
      localState,
    };
  }

  return {
    kind: "clean-match",
    markdown: snapshot.markdown,
    localState,
  };
}
