import { useEffect, useRef, useState } from "react";

import type { DurableSaveState } from "../components/DurableSaveStatus";
import type { MarkdownCanvasSessionValue } from "../markdownCanvas/MarkdownCanvasSession";
import { DOCUMENT_SAVE_COMMAND_ID } from "../markdownCanvas/markdownCanvasTypes";

const AUTOSAVE_DELAY_MS = 800;

export function buildSaveStateFor(session: MarkdownCanvasSessionValue): DurableSaveState {
  if (session.phase === "load_error" || session.phase === "conflict" || session.phase === "save_error" || session.error) {
    return "needs-attention";
  }
  if (session.phase === "unloaded" || session.phase === "loading" || !session.record || !session.snapshot) {
    return "checking";
  }
  if (session.activeCommand?.id === DOCUMENT_SAVE_COMMAND_ID || session.phase === "preparing" || session.phase === "committing") {
    return "saving";
  }
  if (session.dirty) {
    if (session.activeCommand) return "unsaved";
    return session.saveDisabled ? "needs-attention" : "unsaved";
  }
  if (session.phase === "committed_verification_pending") return "checking";
  return hasMatchingCommittedSnapshot(session) ? "saved" : "draft";
}

function hasMatchingCommittedSnapshot(session: MarkdownCanvasSessionValue): boolean {
  return Boolean(
    session.record?.content_status === "committed"
    && session.snapshot?.record.content_status === "committed"
    && session.record.document_id === session.documentId
    && session.snapshot.record.document_id === session.documentId
    && session.record.revision === session.snapshot.loaded_revision,
  );
}

function hasVerifiedBuildBasis(session: MarkdownCanvasSessionValue): boolean {
  return Boolean(
    session.record
    && session.snapshot
    && session.record.kind === "worldbuilding_source"
    && session.record.document_id === session.documentId
    && session.snapshot.record.document_id === session.documentId
    && session.snapshot.loaded_revision === session.record.revision
    && session.phase === "ready_dirty"
    && session.dirty
    && !session.saveDisabled
    && !session.error
    && !session.activeCommand
    && session.editor
    && !session.editor.isDestroyed,
  );
}

/** Debounced Build-only save orchestration over the shared authoring/CAS boundary. */
export function useBuildAutosave(session: MarkdownCanvasSessionValue): DurableSaveState {
  const latestSession = useRef(session);
  latestSession.current = session;
  const [editGeneration, setEditGeneration] = useState(0);

  useEffect(() => {
    const editor = session.editor;
    if (!editor || editor.isDestroyed) return;
    const onEditorUpdate = () => setEditGeneration(generation => generation + 1);
    editor.on("update", onEditorUpdate);
    return () => { editor.off("update", onEditorUpdate); };
  }, [session.documentId, session.documentKey, session.editor]);

  useEffect(() => {
    if (!hasVerifiedBuildBasis(session)) return;

    const scheduledDocumentId = session.documentId;
    const scheduledDocumentKey = session.documentKey;
    const scheduledEditor = session.editor;
    const timer = window.setTimeout(() => {
      const current = latestSession.current;
      if (
        current.documentId !== scheduledDocumentId
        || current.documentKey !== scheduledDocumentKey
        || current.editor !== scheduledEditor
        || !hasVerifiedBuildBasis(current)
      ) return;

      void current.saveMarkdown();
    }, AUTOSAVE_DELAY_MS);

    return () => window.clearTimeout(timer);
  }, [
    session.activeCommand,
    session.documentId,
    session.documentKey,
    session.dirty,
    editGeneration,
    session.editor,
    session.error,
    session.phase,
    session.record,
    session.saveDisabled,
    session.snapshot,
  ]);

  return buildSaveStateFor(session);
}

export function buildSavedAt(session: MarkdownCanvasSessionValue): string | null {
  if (!hasMatchingCommittedSnapshot(session)) return null;
  return session.snapshot?.record.updated_at ?? null;
}
