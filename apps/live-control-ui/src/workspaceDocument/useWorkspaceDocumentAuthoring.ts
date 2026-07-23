import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor } from "@tiptap/react";

import {
  commitTiptapMarkdownWrite,
  getWorkspaceDocumentSnapshot,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentRecord, WorkspaceDocumentSnapshot } from "../api/types";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import {
  buildInitialWorkspaceDocumentLocalState,
  readWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
  type WorkspaceDocumentLocalKind,
  type WorkspaceDocumentLocalSurface,
  type WorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { openWorkspaceDocumentAuthoringState } from "./openWorkspaceDocumentAuthoringState";
import type { ReconcileLocalDraftResult } from "./reconcileLocalDraft";

export type WorkspaceDocumentAuthoringStatus =
  | "idle"
  | "loading"
  | "ready"
  | "conflict"
  | "error"
  | "saving";

export interface UseWorkspaceDocumentAuthoringArgs {
  documentId: string;
  surface: WorkspaceDocumentLocalSurface;
  kind: WorkspaceDocumentLocalKind;
  storage?: Pick<Storage, "getItem" | "setItem">;
}

export interface WorkspaceDocumentAuthoringValue {
  status: WorkspaceDocumentAuthoringStatus;
  error: string | null;
  snapshot: WorkspaceDocumentSnapshot | null;
  record: WorkspaceDocumentRecord | null;
  reconciliation: ReconcileLocalDraftResult | null;
  editorContent: unknown;
  documentKey: string;
  dirty: boolean;
  statusLabel: string;
  saveDisabled: boolean;
  setEditor: (editor: Editor | null) => void;
  markDirty: () => void;
  saveMarkdown: () => Promise<void>;
  reloadFromSnapshot: () => Promise<void>;
  discardLocalDraft: () => void;
}

function statusLabelFor(args: {
  status: WorkspaceDocumentAuthoringStatus;
  dirty: boolean;
  contentStatus: WorkspaceDocumentContentStatus | null;
  conflictReason?: string;
  error?: string | null;
}): string {
  if (args.status === "loading") return "Loading document…";
  if (args.status === "saving") return "Saving…";
  if (args.status === "conflict") return args.conflictReason ?? "Conflict — reload or discard local draft.";
  if (args.status === "error") return args.error ?? "Unable to load document.";
  if (args.dirty) return "Unsaved local changes";
  if (args.contentStatus === "committed") return "Committed";
  return "Draft";
}

type WorkspaceDocumentContentStatus = WorkspaceDocumentRecord["content_status"];

export function useWorkspaceDocumentAuthoring(
  args: UseWorkspaceDocumentAuthoringArgs,
): WorkspaceDocumentAuthoringValue {
  const storage = args.storage ?? window.localStorage;
  const [status, setStatus] = useState<WorkspaceDocumentAuthoringStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<WorkspaceDocumentSnapshot | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconcileLocalDraftResult | null>(null);
  const [localState, setLocalState] = useState<WorkspaceDocumentLocalState | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [documentKey, setDocumentKey] = useState(args.documentId);
  const expectedRevisionRef = useRef<number | null>(null);

  const loadSnapshot = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const nextSnapshot = await getWorkspaceDocumentSnapshot(args.documentId);
      const stored = readWorkspaceDocumentLocalState(storage, args.documentId);
      const opened = openWorkspaceDocumentAuthoringState({
        snapshot: nextSnapshot,
        stored,
        surface: args.surface,
        kind: args.kind,
      });
      expectedRevisionRef.current = nextSnapshot.loaded_revision;
      setSnapshot(nextSnapshot);
      setReconciliation(opened.reconciliation);

      if (opened.status === "conflict") {
        setLocalState(stored);
        setDocumentKey(`${args.documentId}:conflict:${nextSnapshot.loaded_revision}`);
        setStatus("conflict");
        return;
      }
      if (opened.status === "reject" || !opened.localState) {
        setLocalState(null);
        setStatus("error");
        setError(opened.reconciliation.rejectReason ?? "Local draft was rejected.");
        return;
      }

      writeWorkspaceDocumentLocalState(storage, opened.localState);
      setLocalState(opened.localState);
      setDocumentKey(
        `${args.documentId}:${nextSnapshot.loaded_revision}:${opened.localState.dirty ? "dirty" : "clean"}`,
      );
      setStatus("ready");
    } catch (loadError) {
      setSnapshot(null);
      setReconciliation(null);
      setLocalState(null);
      setStatus("error");
      setError(loadError instanceof Error ? loadError.message : "Unable to load workspace document.");
    }
  }, [args.documentId, args.kind, args.surface, storage]);

  useEffect(() => {
    void loadSnapshot();
  }, [loadSnapshot]);

  const markDirty = useCallback(() => {
    setLocalState((current) => {
      if (!current || current.dirty) return current;
      const now = new Date().toISOString();
      const next = { ...current, dirty: true, updated_at: now, last_local_save_at: now };
      writeWorkspaceDocumentLocalState(storage, next);
      return next;
    });
  }, [storage]);

  const persistEditorState = useCallback((nextEditor: Editor) => {
    setLocalState((current) => {
      if (!current) return current;
      const now = new Date().toISOString();
      const tiptapJson = nextEditor.getJSON();
      const next: WorkspaceDocumentLocalState = {
        ...current,
        tiptap_json: tiptapJson,
        exported_markdown: tiptapJsonToSemanticMarkdown(tiptapJson),
        dirty: true,
        updated_at: now,
        last_local_save_at: now,
      };
      writeWorkspaceDocumentLocalState(storage, next);
      return next;
    });
  }, [storage]);

  const handleSetEditor = useCallback((nextEditor: Editor | null) => {
    setEditor(nextEditor);
  }, []);

  useEffect(() => {
    if (!editor) return;
    const onUpdate = () => {
      persistEditorState(editor);
    };
    editor.on("update", onUpdate);
    return () => {
      editor.off("update", onUpdate);
    };
  }, [editor, persistEditorState]);

  const saveMarkdown = useCallback(async () => {
    if (!editor || !snapshot || !localState) return;
    const markdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
    if (!markdown.trim()) {
      setError("Document is empty; add content before saving.");
      setStatus("error");
      return;
    }

    const expectedRevision = expectedRevisionRef.current ?? snapshot.loaded_revision;
    setStatus("saving");
    setError(null);
    try {
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: args.documentId,
        markdown,
        expected_revision: expectedRevision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token) {
        setStatus("ready");
        setError("Markdown save could not be prepared.");
        return;
      }

      const committed = await commitTiptapMarkdownWrite({
        document_id: args.documentId,
        markdown,
        writer_confirm_token: prepared.writer_confirm_token,
        expected_revision: expectedRevision,
      });

      const refreshed = await getWorkspaceDocumentSnapshot(args.documentId);
      expectedRevisionRef.current = refreshed.loaded_revision;
      const opened = openWorkspaceDocumentAuthoringState({
        snapshot: refreshed,
        stored: null,
        surface: args.surface,
        kind: args.kind,
      });
      if (!opened.localState) {
        setStatus("error");
        setError("Save succeeded but the refreshed snapshot could not be opened.");
        return;
      }
      const nextLocalState: WorkspaceDocumentLocalState = {
        ...opened.localState,
        title: committed.title,
        dirty: false,
      };
      writeWorkspaceDocumentLocalState(storage, nextLocalState);
      setSnapshot(refreshed);
      setReconciliation(opened.reconciliation);
      setLocalState(nextLocalState);
      setDocumentKey(`${args.documentId}:${refreshed.loaded_revision}:committed`);
      setStatus("ready");
    } catch (saveError) {
      setStatus("ready");
      setError(saveError instanceof Error ? saveError.message : "Markdown save failed.");
    }
  }, [args.documentId, args.kind, args.surface, editor, localState, snapshot, storage]);

  const discardLocalDraft = useCallback(() => {
    if (!snapshot) return;
    void loadSnapshot();
  }, [loadSnapshot, snapshot]);

  const dirty = localState?.dirty ?? false;
  const statusLabel = useMemo(
    () => statusLabelFor({
      status,
      dirty,
      contentStatus: snapshot?.record.content_status ?? null,
      conflictReason: reconciliation?.conflictReason,
      error,
    }),
    [dirty, error, reconciliation?.conflictReason, snapshot?.record.content_status, status],
  );

  return {
    status,
    error,
    snapshot,
    record: snapshot?.record ?? null,
    reconciliation,
    editorContent: localState?.tiptap_json ?? markdownToTiptapDoc(snapshot?.markdown ?? "").doc,
    documentKey,
    dirty,
    statusLabel,
    saveDisabled: !editor || status === "loading" || status === "saving" || status === "conflict",
    setEditor: handleSetEditor,
    markDirty,
    saveMarkdown,
    reloadFromSnapshot: loadSnapshot,
    discardLocalDraft,
  };
}
