import "../tiptap/pageComposer/apiPresentation";
import { presentationFingerprint } from "../tiptap/pageComposer/presentation";
import type { WorkspaceDocumentSnapshot } from "../api/types";
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
    && (localState.base_page_presentation_sha256 ?? null) === (snapshot.page_presentation_sha256 ?? null)
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

  if (localState.dirty || localState.manual_save_required) {
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
      // except when exported_markdown is sealed authoritative while TipTap may
      // still hold unsaved projection edits (bit survives parser upgrades).
      if (
        localState.exported_markdown === snapshot.markdown
        && !localState.exported_markdown_authoritative
        && !localState.page_presentation_pending
        && presentationFingerprint(localState.page_presentation ?? null) === presentationFingerprint(snapshot.page_presentation ?? null)
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
