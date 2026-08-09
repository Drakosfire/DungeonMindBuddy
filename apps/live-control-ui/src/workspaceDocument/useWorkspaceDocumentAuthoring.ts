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
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { hasBlockingMarkdownImportDiagnostics, markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { semanticMarkdownSerializationDiagnostics } from "../tiptap/markdown/semanticMarkdownSafety";
import { preserveLeadingYamlFrontmatter } from "../tiptap/markdown/stripLeadingYamlFrontmatter";
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

export interface WorkspaceDocumentLocalAdmission {
  documentId: string;
  surface: WorkspaceDocumentLocalSurface;
  kind: WorkspaceDocumentLocalKind;
  dirty: boolean;
  baseRevision: number;
  baseContentSha256: string;
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
  /** In-memory local CAS fingerprint for canvas admission (not a second storage read). */
  localAdmission: WorkspaceDocumentLocalAdmission | null;
  statusLabel: string;
  saveDisabled: boolean;
  lastCommitReceipt: TiptapMarkdownWriteCommitResponse | null;
  editor: Editor | null;
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

/** Advance the CAS base from a receipt while retaining editor content that landed during save. */
function applyCommitReceiptBaseRetainingEditorContent(args: {
  receipt: TiptapMarkdownWriteCommitResponse;
  current: WorkspaceDocumentLocalState;
}): WorkspaceDocumentLocalState {
  const now = new Date().toISOString();
  return {
    ...args.current,
    base_revision: args.receipt.committed_revision,
    base_content_sha256: args.receipt.normalized_content_sha256,
    dirty: true,
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
  /** Monotonic generation so stale verification completions cannot clobber newer saves. */
  const verificationGenerationRef = useRef(0);
  /** Monotonic generation so a newer save supersedes an older save's prepare/commit/apply path. */
  const saveGenerationRef = useRef(0);
  /** Monotonic generation so superseded open/reload completions cannot clobber a newer document. */
  const openGenerationRef = useRef(0);
  /** Monotonic generation of non-programmatic editor mutations (detects edits during prepare/commit). */
  const editorMutationGenerationRef = useRef(0);
  const localDirtyRef = useRef(false);
  const snapshotRef = useRef<WorkspaceDocumentSnapshot | null>(null);
  const localStateRef = useRef<WorkspaceDocumentLocalState | null>(null);
  const requireDirtyToSave = args.requireDirtyToSave !== false;
  const emptyMarkdownFallback = args.emptyMarkdownFallback;
  const canSave = args.canSave;

  const dispatch = useCallback((event: Parameters<typeof reduceAuthoringMachine>[1]) => {
    setMachine((current) => reduceAuthoringMachine(current, event));
  }, []);

  useEffect(() => {
    localDirtyRef.current = localState?.dirty ?? false;
  }, [localState?.dirty]);

  useEffect(() => {
    snapshotRef.current = snapshot;
  }, [snapshot]);

  useEffect(() => {
    localStateRef.current = localState;
  }, [localState]);

  const openFromSnapshot = useCallback(async (options?: { clearLocalFirst?: boolean }) => {
    dispatch({ type: options?.clearLocalFirst ? "DISCARD_STARTED" : "OPEN_STARTED" });
    saveGenerationRef.current += 1;
    verificationGenerationRef.current += 1;
    const openGeneration = ++openGenerationRef.current;
    setLastCommitReceipt(null);
    try {
      if (options?.clearLocalFirst) {
        clearWorkspaceDocumentLocalState(storage, args.documentId);
      }
      const nextSnapshot = await getWorkspaceDocumentSnapshot(args.documentId);
      if (openGeneration !== openGenerationRef.current) return;
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
      snapshotRef.current = nextSnapshot;
      writeWorkspaceDocumentLocalState(storage, opened.localState);
      localStateRef.current = opened.localState;
      setLocalState(opened.localState);
      setDocumentKey(
        `${args.documentId}:${nextSnapshot.loaded_revision}:${opened.localState.dirty ? "dirty" : "clean"}`,
      );
      dispatch({ type: "OPEN_READY", dirty: opened.localState.dirty });
    } catch (loadError) {
      if (openGeneration !== openGenerationRef.current) return;
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
    const current = localStateRef.current;
    if (!current) return;
    const tiptapJson = nextEditor.getJSON();
    const serializationUnsafe = semanticMarkdownSerializationDiagnostics(tiptapJson).length > 0;
    const snap = snapshotRef.current;
    const sourceHasBlockingImport = snap != null && hasBlockingMarkdownImportDiagnostics(snap.markdown);
    const editableBody = tiptapJsonToSemanticMarkdown(tiptapJson);
    // When editor JSON is outside the supported Markdown grammar, or the loaded
    // source already has blocking import diagnostics, preserve authoritative
    // snapshot markdown instead of a lossy TipTap serialization.
    const exportedMarkdown = serializationUnsafe || sourceHasBlockingImport
      ? (sourceHasBlockingImport && snap ? snap.markdown : current.exported_markdown)
      : preserveLeadingYamlFrontmatter(
        snap?.markdown ?? current.exported_markdown,
        editableBody,
      );
    const matchesSnapshot =
      !serializationUnsafe
      && snap != null
      && exportedMarkdown === snap.markdown
      && current.base_revision === snap.loaded_revision
      && current.base_content_sha256 === snap.content_sha256;
    const nextDirty = serializationUnsafe || !matchesSnapshot;
    const wasDirty = current.dirty;
    const now = new Date().toISOString();
    const next: WorkspaceDocumentLocalState = {
      ...current,
      tiptap_json: tiptapJson,
      exported_markdown: exportedMarkdown,
      dirty: nextDirty,
      updated_at: now,
      last_local_save_at: now,
    };
    writeWorkspaceDocumentLocalState(storage, next);
    localDirtyRef.current = nextDirty;
    localStateRef.current = next;
    setLocalState(next);
    if (nextDirty) {
      dispatch({ type: "EDIT" });
    } else if (wasDirty) {
      dispatch({ type: "OPEN_READY", dirty: false });
    }
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
    editorMutationGenerationRef.current += 1;
    persistEditorState(nextEditor);
  }, [persistEditorState]);

  const saveMarkdown = useCallback(async () => {
    if (!editor || !snapshot || !localState) return;
    if (hasBlockingMarkdownImportDiagnostics(snapshot.markdown)) {
      dispatch({
        type: "SAVE_FAILED",
        message: "This source contains Markdown the rich editor cannot round-trip safely. Save is blocked until that syntax is supported.",
      });
      return;
    }

    const tiptapJson = editor.getJSON();
    const serializationDiagnostics = semanticMarkdownSerializationDiagnostics(tiptapJson);
    if (serializationDiagnostics.length > 0) {
      dispatch({
        type: "SAVE_FAILED",
        message: `This edit cannot be represented safely as Markdown. ${serializationDiagnostics[0].message}`,
      });
      return;
    }

    const editableBody = tiptapJsonToSemanticMarkdown(tiptapJson);
    const markdown = preserveLeadingYamlFrontmatter(snapshot.markdown, editableBody);
    if (!editableBody.trim()) {
      dispatch({ type: "SAVE_FAILED", message: "Document is empty; add content before saving." });
      return;
    }

    const expectedRevision = expectedRevisionRef.current ?? snapshot.loaded_revision;
    const saveGeneration = ++saveGenerationRef.current;
    const mutationGenerationAtSaveStart = editorMutationGenerationRef.current;
    verificationGenerationRef.current += 1;

    try {
      dispatch({ type: "PREPARE_STARTED" });
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: args.documentId,
        markdown,
        expected_revision: expectedRevision,
      });
      if (saveGeneration !== saveGenerationRef.current) return;
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
      if (saveGeneration !== saveGenerationRef.current) return;
      setLastCommitReceipt(committed);
      const receiptForThisSave = committed;
      const verificationGeneration = ++verificationGenerationRef.current;
      const editedDuringSave =
        editorMutationGenerationRef.current !== mutationGenerationAtSaveStart;

      dispatch({ type: "COMMIT_SUCCEEDED" });
      expectedRevisionRef.current = committed.committed_revision;
      if (editedDuringSave) {
        setLocalState((current) => {
          if (!current) {
            const fallback = applyCommitReceiptToLocalState({
              receipt: committed,
              surface: args.surface,
              kind: args.kind,
              tiptapJson,
              markdown,
            });
            const next = { ...fallback, dirty: true };
            writeWorkspaceDocumentLocalState(storage, next);
            localDirtyRef.current = true;
            return next;
          }
          const next = applyCommitReceiptBaseRetainingEditorContent({
            receipt: committed,
            current,
          });
          writeWorkspaceDocumentLocalState(storage, next);
          localDirtyRef.current = true;
          return next;
        });
      } else {
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
      }

      if (committed.writer_ok && (committed.file_fingerprint == null || committed.file_fingerprint === "")) {
        setSnapshot(null);
        if (!editedDuringSave) {
          setDocumentKey(`${args.documentId}:${committed.committed_revision}:receipt-unverified`);
        }
        dispatch({
          type: "VERIFICATION_MISMATCH",
          reason: "Commit receipt is missing file_fingerprint after successful write.",
        });
        return;
      }

      setSnapshot((current) => {
        if (!current) return current;
        const nextSnapshot: WorkspaceDocumentSnapshot = {
          ...current,
          record: committed.committed_record,
          markdown,
          content_sha256: committed.normalized_content_sha256,
          file_fingerprint: committed.file_fingerprint as string,
          file_exists: true,
          loaded_revision: committed.committed_revision,
        };
        snapshotRef.current = nextSnapshot;
        return nextSnapshot;
      });
      if (!editedDuringSave) {
        setDocumentKey(`${args.documentId}:${committed.committed_revision}:committed`);
      }

      dispatch({ type: "VERIFICATION_STARTED" });
      try {
        const refreshed = await getWorkspaceDocumentSnapshot(args.documentId);
        if (
          saveGeneration !== saveGenerationRef.current
          || verificationGeneration !== verificationGenerationRef.current
        ) {
          return;
        }
        const verification = verifyCommitReceiptAgainstSnapshot(receiptForThisSave, refreshed);
        if (!verification.ok) {
          dispatch({ type: "VERIFICATION_MISMATCH", reason: verification.reason });
          return;
        }
        dispatch({ type: "VERIFICATION_SUCCEEDED", dirty: localDirtyRef.current });
        expectedRevisionRef.current = receiptForThisSave.committed_revision;
      } catch (verifyError) {
        if (
          saveGeneration !== saveGenerationRef.current
          || verificationGeneration !== verificationGenerationRef.current
        ) {
          return;
        }
        dispatch({
          type: "VERIFICATION_FAILED",
          message: verifyError instanceof Error
            ? verifyError.message
            : "Commit succeeded; snapshot verification failed.",
          dirty: localDirtyRef.current,
        });
      }
    } catch (saveError) {
      if (saveGeneration !== saveGenerationRef.current) return;
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
    dispatch({ type: "RELOAD_STARTED" });
    await openFromSnapshot();
  }, [dispatch, openFromSnapshot]);

  const dirty = localState?.dirty ?? false;
  const localAdmission = useMemo<WorkspaceDocumentLocalAdmission | null>(() => {
    if (!localState) return null;
    return {
      documentId: localState.document_id,
      surface: localState.surface,
      kind: localState.kind,
      dirty: localState.dirty,
      baseRevision: localState.base_revision,
      baseContentSha256: localState.base_content_sha256,
    };
  }, [localState]);
  const phase = machine.phase;
  const statusLabel = useMemo(
    () => statusLabelForPhase({
      phase,
      contentStatus: snapshot?.record.content_status ?? null,
      conflictReason: machine.conflictReason ?? reconciliation?.conflictReason,
      error: machine.error,
      verificationStatus: machine.verificationStatus,
    }),
    [
      machine.conflictReason,
      machine.error,
      machine.verificationStatus,
      phase,
      reconciliation?.conflictReason,
      snapshot?.record.content_status,
    ],
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
    localAdmission,
    statusLabel,
    saveDisabled: !editor
      || !isEditorInteractive(phase)
      || isSaveDisabled(phase)
      || (requireDirtyToSave && !dirty)
      || (canSave ? !canSave() : false),
    lastCommitReceipt,
    editor,
    setEditor: handleSetEditor,
    handleEditorUpdate,
    markDirty,
    saveMarkdown,
    reloadFromSnapshot,
    discardLocalDraft,
  };
}
