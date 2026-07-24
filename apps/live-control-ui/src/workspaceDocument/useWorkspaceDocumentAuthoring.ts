import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/react";

import {
  commitTiptapMarkdownWrite,
  getWorkspaceDocumentSnapshot,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type {
  TiptapMarkdownWriteCommitResponse,
  WorkspaceDocumentRecord,
  WorkspaceDocumentSnapshot,
} from "../api/types";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import {
  buildInitialWorkspaceDocumentLocalState,
  clearWorkspaceDocumentLocalState,
  readWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
  type WorkspaceDocumentLocalKind,
  type WorkspaceDocumentLocalSurface,
  type WorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { openWorkspaceDocumentAuthoringState } from "./openWorkspaceDocumentAuthoringState";
import type { ReconcileLocalDraftResult } from "./reconcileLocalDraft";
import { verifyCommitReceiptAgainstSnapshot } from "./verifyCommitReceiptAgainstSnapshot";
import {
  initialAuthoringMachineState,
  isEditorInteractive,
  isSaveDisabled,
  reduceAuthoringMachine,
  statusLabelForPhase,
  type WorkspaceDocumentAuthoringMachineState,
  type WorkspaceDocumentAuthoringPhase,
} from "./workspaceDocumentAuthoringMachine";

export type WorkspaceDocumentAuthoringStatus = WorkspaceDocumentAuthoringPhase;

export interface UseWorkspaceDocumentAuthoringArgs {
  documentId: string;
  surface: WorkspaceDocumentLocalSurface;
  kind: WorkspaceDocumentLocalKind;
  storage?: Pick<Storage, "getItem" | "setItem" | "removeItem">;
  /** Starter TipTap JSON when snapshot markdown is empty (Plan/runbook drafts). */
  emptyMarkdownFallback?: unknown;
  /** When false, allow save even if local state is not dirty (Plan legacy UX). Default true. */
  requireDirtyToSave?: boolean;
  /** Optional extra save gate (e.g. Plan durable target path). */
  canSave?: () => boolean;
}

export interface WorkspaceDocumentAuthoringValue {
  status: WorkspaceDocumentAuthoringStatus;
  phase: WorkspaceDocumentAuthoringPhase;
  error: string | null;
  snapshot: WorkspaceDocumentSnapshot | null;
  record: WorkspaceDocumentRecord | null;
  reconciliation: ReconcileLocalDraftResult | null;
  editorContent: unknown;
  documentKey: string;
  dirty: boolean;
  statusLabel: string;
  saveDisabled: boolean;
  lastCommitReceipt: TiptapMarkdownWriteCommitResponse | null;
  setEditor: (editor: Editor | null) => void;
  handleEditorUpdate: (
    json: JSONContent,
    editor: Editor,
    meta: { programmatic: boolean },
  ) => void;
  markDirty: () => void;
  saveMarkdown: () => Promise<void>;
  reloadFromSnapshot: () => Promise<void>;
  discardLocalDraft: () => Promise<void>;
}

const ACCEPTED_RECORD_PHASES = new Set<WorkspaceDocumentAuthoringPhase>([
  "ready_clean",
  "ready_dirty",
  "preparing",
  "committing",
  "committed",
  "committed_verification_pending",
  "conflict",
  "save_error",
]);

function applyCommitReceiptToLocalState(args: {
  receipt: TiptapMarkdownWriteCommitResponse;
  surface: WorkspaceDocumentLocalSurface;
  kind: WorkspaceDocumentLocalKind;
  tiptapJson: unknown;
  markdown: string;
}): WorkspaceDocumentLocalState {
  const now = new Date().toISOString();
  const record = args.receipt.committed_record;
  return {
    ...buildInitialWorkspaceDocumentLocalState({
      documentId: record.document_id,
      title: record.title,
      campaignId: record.campaign_id,
      kind: args.kind,
      targetSession: record.target_session,
      surface: args.surface,
      baseRevision: args.receipt.committed_revision,
      baseContentSha256: args.receipt.normalized_content_sha256,
      starterContent: args.tiptapJson,
      now,
    }),
    tiptap_json: args.tiptapJson,
    exported_markdown: args.markdown,
    dirty: false,
    updated_at: now,
    last_local_save_at: now,
  };
}

export function useWorkspaceDocumentAuthoring(
  args: UseWorkspaceDocumentAuthoringArgs,
): WorkspaceDocumentAuthoringValue {
  const storage = args.storage ?? window.localStorage;
  const [machine, setMachine] = useState<WorkspaceDocumentAuthoringMachineState>(
    initialAuthoringMachineState,
  );
  const [snapshot, setSnapshot] = useState<WorkspaceDocumentSnapshot | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconcileLocalDraftResult | null>(null);
  const [localState, setLocalState] = useState<WorkspaceDocumentLocalState | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [documentKey, setDocumentKey] = useState(args.documentId);
  const [lastCommitReceipt, setLastCommitReceipt] = useState<TiptapMarkdownWriteCommitResponse | null>(null);
  const expectedRevisionRef = useRef<number | null>(null);
  const verificationReceiptRef = useRef<TiptapMarkdownWriteCommitResponse | null>(null);
  const localDirtyRef = useRef(false);
  const requireDirtyToSave = args.requireDirtyToSave !== false;
  const emptyMarkdownFallback = args.emptyMarkdownFallback;
  const canSave = args.canSave;

  const dispatch = useCallback((event: Parameters<typeof reduceAuthoringMachine>[1]) => {
    setMachine((current) => reduceAuthoringMachine(current, event));
  }, []);

  useEffect(() => {
    localDirtyRef.current = localState?.dirty ?? false;
  }, [localState?.dirty]);

  const openFromSnapshot = useCallback(async (options?: { clearLocalFirst?: boolean }) => {
    dispatch({ type: options?.clearLocalFirst ? "DISCARD_STARTED" : "OPEN_STARTED" });
    try {
      if (options?.clearLocalFirst) {
        clearWorkspaceDocumentLocalState(storage, args.documentId);
      }
      const nextSnapshot = await getWorkspaceDocumentSnapshot(args.documentId);
      const stored = options?.clearLocalFirst
        ? null
        : readWorkspaceDocumentLocalState(storage, args.documentId);
      const opened = openWorkspaceDocumentAuthoringState({
        documentId: args.documentId,
        snapshot: nextSnapshot,
        stored,
        surface: args.surface,
        kind: args.kind,
        emptyMarkdownFallback,
      });
      setReconciliation(opened.reconciliation);

      if (opened.status === "conflict") {
        expectedRevisionRef.current = nextSnapshot.loaded_revision;
        setSnapshot(nextSnapshot);
        setLocalState(stored);
        setDocumentKey(`${args.documentId}:conflict:${nextSnapshot.loaded_revision}`);
        dispatch({
          type: "OPEN_CONFLICT",
          reason: opened.reconciliation.conflictReason ?? "Local draft conflicts with server content.",
        });
        return;
      }

      if (opened.status === "reject" || !opened.localState) {
        expectedRevisionRef.current = null;
        setSnapshot(null);
        setLocalState(null);
        dispatch({
          type: "OPEN_FAILED",
          message: opened.reconciliation.rejectReason ?? "Local draft was rejected.",
        });
        return;
      }

      expectedRevisionRef.current = nextSnapshot.loaded_revision;
      setSnapshot(nextSnapshot);
      writeWorkspaceDocumentLocalState(storage, opened.localState);
      setLocalState(opened.localState);
      setDocumentKey(
        `${args.documentId}:${nextSnapshot.loaded_revision}:${opened.localState.dirty ? "dirty" : "clean"}`,
      );
      dispatch({ type: "OPEN_READY", dirty: opened.localState.dirty });
    } catch (loadError) {
      expectedRevisionRef.current = null;
      setSnapshot(null);
      setReconciliation(null);
      setLocalState(null);
      dispatch({
        type: "OPEN_FAILED",
        message: loadError instanceof Error ? loadError.message : "Unable to load workspace document.",
      });
    }
  }, [args.documentId, args.kind, args.surface, dispatch, emptyMarkdownFallback, storage]);

  useEffect(() => {
    void openFromSnapshot();
  }, [openFromSnapshot]);

  const markDirty = useCallback(() => {
    setLocalState((current) => {
      if (!current || current.dirty) return current;
      const now = new Date().toISOString();
      const next = { ...current, dirty: true, updated_at: now, last_local_save_at: now };
      writeWorkspaceDocumentLocalState(storage, next);
      localDirtyRef.current = true;
      return next;
    });
    dispatch({ type: "EDIT" });
  }, [dispatch, storage]);

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
      localDirtyRef.current = true;
      return next;
    });
    dispatch({ type: "EDIT" });
  }, [dispatch, storage]);

  const handleSetEditor = useCallback((nextEditor: Editor | null) => {
    setEditor(nextEditor);
  }, []);

  const handleEditorUpdate = useCallback((
    _json: JSONContent,
    nextEditor: Editor,
    meta: { programmatic: boolean },
  ) => {
    if (meta.programmatic) return;
    persistEditorState(nextEditor);
  }, [persistEditorState]);

  const saveMarkdown = useCallback(async () => {
    if (!editor || !snapshot || !localState) return;
    const markdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
    if (!markdown.trim()) {
      dispatch({ type: "SAVE_FAILED", message: "Document is empty; add content before saving." });
      return;
    }

    const expectedRevision = expectedRevisionRef.current ?? snapshot.loaded_revision;
    const tiptapJson = editor.getJSON();
    try {
      dispatch({ type: "PREPARE_STARTED" });
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: args.documentId,
        markdown,
        expected_revision: expectedRevision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token) {
        dispatch({ type: "SAVE_FAILED", message: "Markdown save could not be prepared." });
        return;
      }

      dispatch({ type: "COMMIT_STARTED" });
      const committed = await commitTiptapMarkdownWrite({
        document_id: args.documentId,
        markdown,
        writer_confirm_token: prepared.writer_confirm_token,
        expected_revision: expectedRevision,
      });
      setLastCommitReceipt(committed);
      verificationReceiptRef.current = committed;

      // Commit receipt is authoritative — advance local base before any verification GET.
      dispatch({ type: "COMMIT_SUCCEEDED" });
      expectedRevisionRef.current = committed.committed_revision;
      const receiptLocal = applyCommitReceiptToLocalState({
        receipt: committed,
        surface: args.surface,
        kind: args.kind,
        tiptapJson,
        markdown,
      });
      writeWorkspaceDocumentLocalState(storage, receiptLocal);
      setLocalState(receiptLocal);
      localDirtyRef.current = false;
      setSnapshot((current) => {
        if (!current) return current;
        return {
          ...current,
          record: committed.committed_record,
          markdown,
          content_sha256: committed.normalized_content_sha256,
          file_fingerprint: committed.file_fingerprint ?? current.file_fingerprint,
          file_exists: true,
          loaded_revision: committed.committed_revision,
        };
      });
      setDocumentKey(`${args.documentId}:${committed.committed_revision}:committed`);

      dispatch({ type: "VERIFICATION_STARTED" });
      try {
        const refreshed = await getWorkspaceDocumentSnapshot(args.documentId);
        const receiptForVerification = verificationReceiptRef.current ?? committed;
        const verification = verifyCommitReceiptAgainstSnapshot(receiptForVerification, refreshed);
        if (!verification.ok) {
          dispatch({ type: "VERIFICATION_MISMATCH", reason: verification.reason });
          return;
        }
        dispatch({ type: "VERIFICATION_SUCCEEDED", dirty: localDirtyRef.current });
        expectedRevisionRef.current = receiptForVerification.committed_revision;
      } catch (verifyError) {
        dispatch({
          type: "VERIFICATION_FAILED",
          message: verifyError instanceof Error
            ? verifyError.message
            : "Commit succeeded; snapshot verification failed.",
        });
      }
    } catch (saveError) {
      dispatch({
        type: "SAVE_FAILED",
        message: saveError instanceof Error ? saveError.message : "Markdown save failed.",
      });
    }
  }, [args.documentId, args.kind, args.surface, dispatch, editor, localState, snapshot, storage]);

  const discardLocalDraft = useCallback(async () => {
    await openFromSnapshot({ clearLocalFirst: true });
  }, [openFromSnapshot]);

  const reloadFromSnapshot = useCallback(async () => {
    // Preserve local draft; reopen may re-enter conflict intentionally.
    dispatch({ type: "RELOAD_STARTED" });
    await openFromSnapshot();
  }, [dispatch, openFromSnapshot]);

  const dirty = localState?.dirty ?? false;
  const phase = machine.phase;
  const statusLabel = useMemo(
    () => statusLabelForPhase({
      phase,
      contentStatus: snapshot?.record.content_status ?? null,
      conflictReason: machine.conflictReason ?? reconciliation?.conflictReason,
      error: machine.error,
    }),
    [machine.conflictReason, machine.error, phase, reconciliation?.conflictReason, snapshot?.record.content_status],
  );

  const record = useMemo(() => {
    if (!ACCEPTED_RECORD_PHASES.has(phase)) return null;
    if (!snapshot || !localState) return null;
    return snapshot.record;
  }, [localState, phase, snapshot]);

  const legacyStatus: WorkspaceDocumentAuthoringStatus = phase;

  return {
    status: legacyStatus,
    phase,
    error: machine.error,
    snapshot,
    record,
    reconciliation,
    editorContent: localState?.tiptap_json ?? markdownToTiptapDoc(snapshot?.markdown ?? "").doc,
    documentKey,
    dirty,
    statusLabel,
    saveDisabled: !editor
      || !isEditorInteractive(phase)
      || isSaveDisabled(phase)
      || (requireDirtyToSave && !dirty)
      || (canSave ? !canSave() : false),
    lastCommitReceipt,
    setEditor: handleSetEditor,
    handleEditorUpdate,
    markDirty,
    saveMarkdown,
    reloadFromSnapshot,
    discardLocalDraft,
  };
}
