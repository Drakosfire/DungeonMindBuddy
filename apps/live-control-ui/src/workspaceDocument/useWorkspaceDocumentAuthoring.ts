import { conflictCopiesKey, preserveConflictCopies, type WorkspaceConflictRecovery, type WorkspaceConflictReview } from "./workspaceConflictRecovery";
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
import { assertPersistedDraft, draftRecoveryIdentity, draftRecoveryKey, preserveDraftRecovery, readDraftRecovery, writeVerifiedLocalState, type WorkspaceDraftRecoveryReview } from "./workspaceDocumentRecovery";
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
  /** True while Save must wait for re-import/discard of a sealed source projection. */
  exportedMarkdownAuthoritative: boolean;
  /** In-memory local CAS fingerprint for canvas admission (not a second storage read). */
  localAdmission: WorkspaceDocumentLocalAdmission | null;
  statusLabel: string;
  saveDisabled: boolean;
  saveDisabledReason: string | null;
  conflictRecovery?: WorkspaceConflictRecovery;
  draftRecoveryAvailable: boolean;
  prepareDraftRecovery: () => WorkspaceDraftRecoveryReview;
  confirmDraftRecovery: (review: WorkspaceDraftRecoveryReview, mode?: "source" | "current" | "normalize") => void;
  restoreDraftRecovery: () => void;
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
  /**
   * Rebase TipTap from sealed `exported_markdown` and clear the authority bit
   * when the current parser can import that source without blocking diagnostics.
   * Required before Save while `exported_markdown_authoritative` is true.
   */
  reimportFromAuthoritativeMarkdown: () => void;
  reloadFromSnapshot: () => Promise<void>;
  discardLocalDraft: () => Promise<void>;
  /**
   * Adopt a successful metadata-only server mutation (e.g. title PATCH) without
   * remounting the editor or changing body/digest/dirty. Fail closed on identity
   * or revision invariant violations.
   */
  adoptMetadataUpdate: (args: {
    previousRevision: number;
    record: WorkspaceDocumentRecord;
  }) => AdoptMetadataUpdateResult;
}

export type AdoptMetadataUpdateResult =
  | { ok: true; record: WorkspaceDocumentRecord }
  | { ok: false; reason: string };

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
    exported_markdown_authoritative: false,
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
  const requestedDocument = useRef(args.documentId);
  requestedDocument.current = args.documentId;
  const [machine, setMachine] = useState<WorkspaceDocumentAuthoringMachineState>(
    initialAuthoringMachineState,
  );
  const phaseRef = useRef(machine.phase);
  phaseRef.current = machine.phase;
  const [snapshot, setSnapshot] = useState<WorkspaceDocumentSnapshot | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconcileLocalDraftResult | null>(null);
  const [localState, setLocalState] = useState<WorkspaceDocumentLocalState | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [recoveryVersion, setRecoveryVersion] = useState(0);
  const [documentKey, setDocumentKey] = useState(args.documentId);
  const [lastCommitReceipt, setLastCommitReceipt] = useState<TiptapMarkdownWriteCommitResponse | null>(null);
  const expectedRevisionRef = useRef<number | null>(null);
  const recoveryMounted = useRef(true);
  useEffect(() => {
    recoveryMounted.current = true;
    return () => { recoveryMounted.current = false; };
  }, []);
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
        snapshotRef.current = nextSnapshot;
        localStateRef.current = stored;
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
    // When editor JSON is outside the supported Markdown grammar, or the loaded
    // source already has blocking import diagnostics, preserve authoritative
    // snapshot markdown instead of a lossy TipTap serialization. Do not call the
    // serializer in that case: playable-identity failure is a throw, not a strip.
    const preservingAuthoritativeExport = serializationUnsafe || sourceHasBlockingImport;
    const exportedMarkdown = preservingAuthoritativeExport
      ? (sourceHasBlockingImport && snap ? snap.markdown : current.exported_markdown)
      : preserveLeadingYamlFrontmatter(
        snap?.markdown ?? current.exported_markdown,
        tiptapJsonToSemanticMarkdown(tiptapJson),
      );
    const matchesSnapshot =
      !serializationUnsafe
      && snap != null
      && exportedMarkdown === snap.markdown
      && current.base_revision === snap.loaded_revision
      && current.base_content_sha256 === snap.content_sha256;
    // Unsafe sources keep authoritative exported_markdown; TipTap may still hold
    // unsaved projection edits, so do not clear dirty just because export matches.
    const nextDirty = serializationUnsafe || sourceHasBlockingImport || !matchesSnapshot;
    const wasDirty = current.dirty;
    const now = new Date().toISOString();
    const next: WorkspaceDocumentLocalState = {
      ...current,
      tiptap_json: tiptapJson,
      exported_markdown: exportedMarkdown,
      // Seal authority in localStorage so a future parser upgrade cannot flip the
      // live diagnostics guard and re-derive from this TipTap projection.
      exported_markdown_authoritative: preservingAuthoritativeExport
        || current.exported_markdown_authoritative,
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

  const reimportFromAuthoritativeMarkdown = useCallback(() => {
    const current = localStateRef.current;
    if (!current?.exported_markdown_authoritative) return;
    if (hasBlockingMarkdownImportDiagnostics(current.exported_markdown)) {
      dispatch({
        type: "SAVE_FAILED",
        message:
          "Sealed source Markdown is still not safely representable by the rich editor. "
          + "Discard the local draft, or wait until that syntax is supported, before saving.",
      });
      return;
    }
    const imported = markdownToTiptapDoc(current.exported_markdown);
    const snap = snapshotRef.current;
    const editableBody = tiptapJsonToSemanticMarkdown(imported.doc);
    const exportedMarkdown = preserveLeadingYamlFrontmatter(current.exported_markdown, editableBody);
    const matchesSnapshot = snap != null
      && exportedMarkdown === snap.markdown
      && current.base_revision === snap.loaded_revision
      && current.base_content_sha256 === snap.content_sha256;
    const now = new Date().toISOString();
    const next: WorkspaceDocumentLocalState = {
      ...current,
      tiptap_json: imported.doc,
      exported_markdown: exportedMarkdown,
      exported_markdown_authoritative: false,
      dirty: !matchesSnapshot,
      updated_at: now,
      last_local_save_at: now,
    };
    writeWorkspaceDocumentLocalState(storage, next);
    localDirtyRef.current = next.dirty;
    localStateRef.current = next;
    setLocalState(next);
    setDocumentKey(
      `${current.document_id}:${current.base_revision}:${next.dirty ? "dirty" : "clean"}:reimport`,
    );
    dispatch({ type: "OPEN_READY", dirty: next.dirty });
  }, [dispatch, storage]);

  const conflictFence = useCallback(() => {
    const current = localStateRef.current;
    const saved = snapshotRef.current;
    if (!recoveryMounted.current || requestedDocument.current !== args.documentId || phaseRef.current !== "conflict" || !current || !saved
      || current.document_id !== args.documentId || saved.record.document_id !== args.documentId
      || current.surface !== args.surface || current.kind !== args.kind) {
      throw new Error("The document changed. Reopen the comparison before choosing a copy.");
    }
    assertPersistedDraft(storage, current);
    return JSON.stringify([current, saved]);
  }, [args.documentId, args.surface, args.kind, storage]);

  const prepareConflictRecovery = useCallback((): WorkspaceConflictReview => {
    const fence = conflictFence();
    return JSON.parse(JSON.stringify({ documentId: args.documentId, fence, local: localStateRef.current, saved: snapshotRef.current }));
  }, [args.documentId, conflictFence]);

  const resolveConflictRecovery = useCallback(async (review: WorkspaceConflictReview, choice: "local" | "saved") => {
    if (review.documentId !== args.documentId || review.fence !== conflictFence()) throw new Error("The copies changed. Reopen the comparison.");
    const generation = openGenerationRef.current;
    const fresh = await getWorkspaceDocumentSnapshot(args.documentId);
    if (generation !== openGenerationRef.current || review.fence !== conflictFence()
      || JSON.stringify(fresh) !== JSON.stringify(snapshotRef.current)) {
      throw new Error("The saved version or browser draft changed. Check the saved version again and reopen the comparison.");
    }
    const current = localStateRef.current!;
    const opened = openWorkspaceDocumentAuthoringState({ documentId: args.documentId, snapshot: fresh,
      stored: null, surface: args.surface, kind: args.kind, emptyMarkdownFallback });
    if (opened.status !== "ready" || !opened.localState) throw new Error("The saved document is no longer editable here. Both copies were kept.");
    // Preserve exact local JSON and sealed-source authority; existing save gates still apply.
    const replacement = choice === "saved" ? opened.localState : { ...current,
      base_revision: fresh.loaded_revision, base_content_sha256: fresh.content_sha256,
      dirty: true, updated_at: new Date().toISOString() };
    const protectedReview = { ...review, local: current, saved: fresh };
    preserveConflictCopies(storage, protectedReview);
    if (review.fence !== conflictFence()) throw new Error("The browser draft changed. Both copies were kept; reopen the comparison.");
    writeVerifiedLocalState(storage, replacement);
    expectedRevisionRef.current = fresh.loaded_revision;
    localStateRef.current = replacement; localDirtyRef.current = replacement.dirty;
    setLocalState(replacement); setReconciliation(null); setRecoveryVersion(value => value + 1);
    setDocumentKey(`${args.documentId}:${fresh.loaded_revision}:conflict-resolved:${Date.now()}`);
    phaseRef.current = replacement.dirty ? "ready_dirty" : "ready_clean";
    dispatch({ type: "OPEN_READY", dirty: replacement.dirty });
  }, [args.documentId, args.surface, args.kind, conflictFence, dispatch, emptyMarkdownFallback, storage]);

  const protectedConflictCopies = useMemo(() => {
    try { return storage.getItem(conflictCopiesKey(args.documentId)); } catch { return null; }
  }, [args.documentId, storage, recoveryVersion]);

  const recoveryFence = useCallback(() => {
    const current = localStateRef.current;
    const snap = snapshotRef.current;
    if (!current || !snap || !editor || current.document_id !== args.documentId
        || snap.record.document_id !== args.documentId || !isEditorInteractive(machine.phase)
        || isSaveDisabled(machine.phase) || current.base_revision !== snap.loaded_revision
        || current.base_content_sha256 !== snap.content_sha256) {
      throw new Error("The document changed or is not ready. Reopen recovery when it is ready.");
    }
    return JSON.stringify([current, editor.getJSON(), editorMutationGenerationRef.current,
      snap.loaded_revision, snap.content_sha256,
      assertPersistedDraft(storage, current)]);
  }, [args.documentId, editor, machine.phase, storage]);

  const currentPageRecovery = useCallback((allowSpacerNormalization = false) => {
    const current = localStateRef.current;
    const snap = snapshotRef.current;
    if (!current || !snap || !editor?.schema) throw new Error("The current page is still loading.");
    if (hasBlockingMarkdownImportDiagnostics(current.exported_markdown) || hasBlockingMarkdownImportDiagnostics(snap.markdown)) {
      throw new Error("The preserved source still contains unsupported Markdown. Keep both copies until it can be preserved safely.");
    }
    const doc = editor.getJSON();
    const issues = semanticMarkdownSerializationDiagnostics(doc);
    if (issues.length) throw new Error(issues[0].message);
    const markdown = preserveLeadingYamlFrontmatter(current.exported_markdown, tiptapJsonToSemanticMarkdown(doc));
    const imported = markdownToTiptapDoc(markdown);
    if (imported.diagnostics.some(issue => issue.level === "warning")) throw new Error("The current page cannot yet be reloaded without changes.");
    const normalized = editor.schema.nodeFromJSON(imported.doc).toJSON();
    const stable = (value: unknown): unknown => Array.isArray(value) ? value.map(stable)
      : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, stable(item)])) : value;
    const equal = (a: unknown, b: unknown) => JSON.stringify(stable(a)) === JSON.stringify(stable(b));
    if (equal(doc, normalized)) return { doc, markdown, removedSpacers: 0 };
    const isSpacer = (node: typeof doc) => node.type === "paragraph"
      && !node.content?.length && !node.marks?.length
      && Object.values(node.attrs ?? {}).every(value => value == null);
    const withoutSpacers = (value: typeof doc) => ({ ...value, content: value.content?.filter(node => !isSpacer(node)) });
    const removedSpacers = (doc.content?.filter(isSpacer).length ?? 0) - (normalized.content?.filter(isSpacer).length ?? 0);
    if (allowSpacerNormalization && removedSpacers > 0 && equal(withoutSpacers(doc), withoutSpacers(normalized))) {
      return { doc: normalized, markdown, removedSpacers };
    }
    throw new Error("Some current page structure would change on reload. Both copies remain protected.");
  }, [editor]);

  const prepareDraftRecovery = useCallback((): WorkspaceDraftRecoveryReview => {
    const current = localStateRef.current;
    if (!current?.exported_markdown_authoritative) throw new Error("This draft does not require source recovery.");
    const fence = recoveryFence();
    let currentPageIssue: string | null = null;
    let removedSpacers = 0;
    try { removedSpacers = currentPageRecovery(true).removedSpacers; } catch (reason) { currentPageIssue = reason instanceof Error ? reason.message : "The current page cannot be safely saved yet."; }
    return { documentId: args.documentId, fence, canKeepCurrent: currentPageIssue == null && removedSpacers === 0, currentPageIssue,
      canNormalizeCurrent: currentPageIssue == null && removedSpacers > 0, removedSpacers,
      canUsePreserved: !hasBlockingMarkdownImportDiagnostics(current.exported_markdown),
      preservedMarkdown: current.exported_markdown,
      editorText: editor?.getText?.() ?? "Preview unavailable. Your full editor data will be preserved." };
  }, [args.documentId, editor, recoveryFence, currentPageRecovery]);

  const confirmDraftRecovery = useCallback((review: WorkspaceDraftRecoveryReview, mode: "source" | "current" | "normalize" = "source") => {
    if (review.documentId !== args.documentId || review.fence !== recoveryFence()) {
      throw new Error("The draft changed after review. Review it again before replacing it.");
    }
    const current = localStateRef.current!;
    if (!current.exported_markdown_authoritative || hasBlockingMarkdownImportDiagnostics(current.exported_markdown)) {
      throw new Error("The preserved Markdown still cannot be safely imported. Both versions remain unchanged.");
    }
    const imported = markdownToTiptapDoc(current.exported_markdown);
    if (semanticMarkdownSerializationDiagnostics(imported.doc).length) throw new Error("The preserved source is still unsupported.");
    const kept = mode === "source" ? null : currentPageRecovery(mode === "normalize");
    const normalizedDoc = kept?.doc ?? (editor?.schema ? editor.schema.nodeFromJSON(imported.doc).toJSON() : imported.doc);
    const markdown = kept?.markdown ?? preserveLeadingYamlFrontmatter(current.exported_markdown, tiptapJsonToSemanticMarkdown(normalizedDoc));
    const original = JSON.parse(JSON.stringify({ ...current, tiptap_json: editor!.getJSON() })) as WorkspaceDocumentLocalState;
    const next: WorkspaceDocumentLocalState = { ...current, tiptap_json: normalizedDoc,
      exported_markdown: markdown, exported_markdown_authoritative: false,
      dirty: markdown !== snapshotRef.current!.markdown,
      updated_at: new Date().toISOString(), last_local_save_at: new Date().toISOString() };
    preserveDraftRecovery(storage, original, next);
    setRecoveryVersion(v => v + 1);
    assertPersistedDraft(storage, current);
    writeVerifiedLocalState(storage, next);
    localStateRef.current = next; localDirtyRef.current = next.dirty;
    setLocalState(next);
    setDocumentKey(`${current.document_id}:${current.base_revision}:recovery:${Date.now()}`);
    dispatch({ type: "OPEN_READY", dirty: next.dirty });
  }, [args.documentId, dispatch, editor, recoveryFence, storage, currentPageRecovery]);

  const restoreDraftRecovery = useCallback(() => {
    recoveryFence();
    const backup = readDraftRecovery(storage, args.documentId);
    const current = localStateRef.current;
    if (!backup || !current || !editor) throw new Error("No matching recovery copy is available.");
    const live = { ...current, tiptap_json: editor.getJSON() };
    if (draftRecoveryIdentity(live) !== draftRecoveryIdentity(backup.replacement)
        && draftRecoveryIdentity(live) !== draftRecoveryIdentity(backup.original)) {
      throw new Error("There are newer edits or a different source revision. Your edits and recovery copy have been kept; nothing was restored.");
    }
    assertPersistedDraft(storage, current);
    writeVerifiedLocalState(storage, backup.original);
    localStateRef.current = backup.original; localDirtyRef.current = backup.original.dirty;
    setLocalState(backup.original);
    // Original data is verified restored before removing its redundant checkpoint.
    try { storage.removeItem(draftRecoveryKey(args.documentId)); } catch { /* keep redundant recovery copy */ }
    setRecoveryVersion(v => v + 1);
    setDocumentKey(`${current.document_id}:${current.base_revision}:restore:${Date.now()}`);
    dispatch({ type: "OPEN_READY", dirty: backup.original.dirty });
  }, [args.documentId, dispatch, editor, recoveryFence, storage]);

  const draftRecoveryAvailable = useMemo(() => {
    try { return readDraftRecovery(storage, args.documentId) != null; } catch { return false; }
  }, [args.documentId, storage, recoveryVersion]);

  const saveMarkdown = useCallback(async () => {
    if (!editor || !snapshot || !localState) return;
    if (localState.exported_markdown_authoritative) {
      dispatch({
        type: "SAVE_FAILED",
        message:
          "Local editor content is a sealed projection of source Markdown. "
          + "Re-import from the sealed source (or discard the local draft) before saving.",
      });
      return;
    }
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
        const reason = [...(prepared.warnings ?? []), ...(prepared.diagnostics ?? [])].filter(Boolean).join(' ');
        dispatch({ type: "SAVE_FAILED", message: reason ? `Couldn’t save this page: ${reason}` : "The server could not prepare this save. Your draft is still here." });
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

  const adoptMetadataUpdate = useCallback((update: {
    previousRevision: number;
    record: WorkspaceDocumentRecord;
  }): AdoptMetadataUpdateResult => {
    const snap = snapshotRef.current;
    const current = localStateRef.current;
    if (!snap || !current) {
      return { ok: false, reason: "No admitted snapshot for metadata adoption." };
    }
    if (
      update.record.document_id !== args.documentId
      || update.record.document_id !== snap.record.document_id
      || update.record.document_id !== current.document_id
    ) {
      return { ok: false, reason: "Metadata response document identity mismatch." };
    }
    if (snap.loaded_revision !== update.previousRevision) {
      return {
        ok: false,
        reason: `Metadata adoption launched from revision ${update.previousRevision}, snapshot is ${snap.loaded_revision}.`,
      };
    }
    if (current.base_revision !== update.previousRevision) {
      return {
        ok: false,
        reason: `Metadata adoption launched from revision ${update.previousRevision}, local base is ${current.base_revision}.`,
      };
    }
    if (update.record.revision !== update.previousRevision + 1) {
      return {
        ok: false,
        reason: `Expected metadata successor revision ${update.previousRevision + 1}, got ${update.record.revision}.`,
      };
    }
    if (update.record.kind !== args.kind) {
      return { ok: false, reason: "Metadata response kind is not admissible for this session." };
    }
    if (update.record.status !== "active") {
      return { ok: false, reason: "Metadata response status is not admissible for this session." };
    }

    const now = new Date().toISOString();
    const nextSnapshot: WorkspaceDocumentSnapshot = {
      ...snap,
      record: update.record,
      loaded_revision: update.record.revision,
      // Body / digest / file identity deliberately unchanged.
      markdown: snap.markdown,
      content_sha256: snap.content_sha256,
      file_fingerprint: snap.file_fingerprint,
      file_exists: snap.file_exists,
    };
    const nextLocal: WorkspaceDocumentLocalState = {
      ...current,
      title: update.record.title,
      base_revision: update.record.revision,
      // Digest, dirty, TipTap JSON, exported markdown, and authority bit unchanged.
      base_content_sha256: current.base_content_sha256,
      dirty: current.dirty,
      tiptap_json: current.tiptap_json,
      exported_markdown: current.exported_markdown,
      exported_markdown_authoritative: current.exported_markdown_authoritative,
      updated_at: now,
      last_local_save_at: now,
    };

    expectedRevisionRef.current = update.record.revision;
    snapshotRef.current = nextSnapshot;
    localStateRef.current = nextLocal;
    localDirtyRef.current = nextLocal.dirty;
    setSnapshot(nextSnapshot);
    setLocalState(nextLocal);
    writeWorkspaceDocumentLocalState(storage, nextLocal);
    // documentKey intentionally unchanged — TipTap must not remount.
    return { ok: true, record: update.record };
  }, [args.documentId, args.kind, storage]);

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

  const saveDisabledReason = phase === "conflict" ? "The browser draft and saved version differ. Review conflicting copies before saving."
    : !editor ? "The editor is still loading."
    : !isEditorInteractive(phase) || isSaveDisabled(phase)
      ? "The document is not ready to save."
    : localState?.exported_markdown_authoritative
      ? (hasBlockingMarkdownImportDiagnostics(localState.exported_markdown)
        ? "The preserved source uses Markdown this editor cannot save yet. Review the protected copies for details."
        : "This local copy was protected after an earlier editing problem. Review it once to resume saving.")
    : (requireDirtyToSave && !dirty) ? "No unsaved changes."
    : canSave && !canSave() ? "This document is read-only or cannot be saved here."
    : null;
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
    exportedMarkdownAuthoritative: Boolean(localState?.exported_markdown_authoritative),
    localAdmission,
    statusLabel,
    saveDisabled: !editor
      || !isEditorInteractive(phase)
      || isSaveDisabled(phase)
      || (requireDirtyToSave && !dirty)
      || Boolean(localState?.exported_markdown_authoritative)
      || (canSave ? !canSave() : false),
    conflictRecovery: { prepare: prepareConflictRecovery, resolve: resolveConflictRecovery, protectedCopies: protectedConflictCopies },
    saveDisabledReason, draftRecoveryAvailable, prepareDraftRecovery, confirmDraftRecovery, restoreDraftRecovery,
    lastCommitReceipt,
    editor,
    setEditor: handleSetEditor,
    handleEditorUpdate,
    markDirty,
    saveMarkdown,
    reimportFromAuthoritativeMarkdown,
    reloadFromSnapshot,
    discardLocalDraft,
    adoptMetadataUpdate,
  };
}
