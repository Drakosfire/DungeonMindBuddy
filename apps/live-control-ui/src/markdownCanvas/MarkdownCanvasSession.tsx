import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";

import { useWorkspaceDocumentAuthoring } from "../workspaceDocument/useWorkspaceDocumentAuthoring";
import { isEditorInteractive } from "../workspaceDocument/workspaceDocumentAuthoringMachine";
import type {
  AdmissionLookupResult,
  AdmittedDocumentEnvelope,
  DocumentAdmissionPolicy,
  MarkdownCanvasSessionProviderProps,
  MarkdownCanvasSessionValue,
} from "./markdownCanvasTypes";
import { DOCUMENT_SAVE_COMMAND_ID } from "./markdownCanvasTypes";
import { useCanvasCommand } from "./useCanvasCommand";

const MarkdownCanvasSessionContext = createContext<MarkdownCanvasSessionValue | null>(null);

export function useMarkdownCanvasSession(): MarkdownCanvasSessionValue {
  const value = useContext(MarkdownCanvasSessionContext);
  if (!value) {
    throw new Error("useMarkdownCanvasSession requires MarkdownCanvasSessionProvider");
  }
  return value;
}

export function useOptionalMarkdownCanvasSession(): MarkdownCanvasSessionValue | null {
  return useContext(MarkdownCanvasSessionContext);
}

function admitDocument(args: {
  documentId: string;
  surface: MarkdownCanvasSessionProviderProps["surface"];
  kind: MarkdownCanvasSessionProviderProps["kind"];
  policy: DocumentAdmissionPolicy;
  phase: MarkdownCanvasSessionValue["phase"];
  dirty: boolean;
  snapshot: MarkdownCanvasSessionValue["snapshot"];
  record: MarkdownCanvasSessionValue["record"];
  localBaseRevision: number | null;
  localBaseContentSha256: string | null;
  localSurface: string | null;
  localDocumentId: string | null;
}): AdmissionLookupResult {
  const {
    documentId,
    surface,
    kind,
    policy,
    phase,
    dirty,
    snapshot,
    record,
    localBaseRevision,
    localBaseContentSha256,
    localSurface,
    localDocumentId,
  } = args;

  if (!snapshot || !record) {
    return { ok: false, code: "document_missing" };
  }
  if (record.document_id !== documentId) {
    return { ok: false, code: "document_identity_mismatch" };
  }

  const baseEnvelope = {
    documentId,
    revision: snapshot.loaded_revision,
    contentSha256: snapshot.content_sha256,
    contentStatus: record.content_status,
    documentKind: kind,
    surfaceId: surface,
  } as const;

  if (policy === "loaded") {
    if (phase === "unloaded" || phase === "loading" || phase === "load_error") {
      return { ok: false, code: "document_not_loaded" };
    }
    return { ok: true, envelope: { ...baseEnvelope } };
  }

  if (policy === "editable") {
    if (!isEditorInteractive(phase)) {
      return { ok: false, code: "document_not_editable" };
    }
    return { ok: true, envelope: { ...baseEnvelope } };
  }

  // committed_clean
  if (localDocumentId == null) {
    return { ok: false, code: "document_missing" };
  }
  if (localDocumentId !== documentId || localSurface !== surface) {
    return { ok: false, code: "authority_mismatch" };
  }
  if (dirty) {
    return { ok: false, code: "document_dirty" };
  }
  if (record.content_status !== "committed") {
    return { ok: false, code: "document_not_committed" };
  }
  if (localBaseRevision == null || localBaseContentSha256 == null) {
    return { ok: false, code: "document_missing" };
  }
  if (localBaseRevision !== snapshot.loaded_revision) {
    return {
      ok: false,
      code: "revision_mismatch",
      detail: `${localBaseRevision}!=${snapshot.loaded_revision}`,
    };
  }
  if (localBaseContentSha256 !== snapshot.content_sha256) {
    return { ok: false, code: "digest_mismatch" };
  }
  if (phase === "conflict" || phase === "load_error" || phase === "loading" || phase === "unloaded") {
    return { ok: false, code: "document_not_ready" };
  }

  return {
    ok: true,
    envelope: {
      documentId,
      revision: snapshot.loaded_revision,
      contentSha256: snapshot.content_sha256,
      contentStatus: "committed",
      documentKind: kind,
      surfaceId: surface,
    },
  };
}

export function MarkdownCanvasSessionProvider(props: MarkdownCanvasSessionProviderProps) {
  const {
    documentId,
    surface,
    kind,
    children,
    storage,
    emptyMarkdownFallback,
    requireDirtyToSave,
    canSave,
    saveConflictsWith = [],
  } = props;

  const saveConflicts = useMemo(
    () => [...saveConflictsWith],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [saveConflictsWith.join("\0")],
  );

  const authoring = useWorkspaceDocumentAuthoring({
    documentId,
    surface,
    kind,
    storage,
    emptyMarkdownFallback,
    requireDirtyToSave,
    canSave,
  });

  const lookupAdmission = useCallback(
    (policy: DocumentAdmissionPolicy): AdmissionLookupResult => admitDocument({
      documentId,
      surface,
      kind,
      policy,
      phase: authoring.phase,
      dirty: authoring.dirty,
      snapshot: authoring.snapshot,
      record: authoring.record,
      localBaseRevision: authoring.localAdmission?.baseRevision ?? null,
      localBaseContentSha256: authoring.localAdmission?.baseContentSha256 ?? null,
      localSurface: authoring.localAdmission?.surface ?? null,
      localDocumentId: authoring.localAdmission?.documentId ?? null,
    }),
    [
      authoring.dirty,
      authoring.localAdmission,
      authoring.phase,
      authoring.record,
      authoring.snapshot,
      documentId,
      kind,
      surface,
    ],
  );

  const getAdmittedDocument = useCallback(
    (policy: DocumentAdmissionPolicy): AdmittedDocumentEnvelope | null => {
      const result = lookupAdmission(policy);
      return result.ok ? result.envelope : null;
    },
    [lookupAdmission],
  );

  const { activeCommand, runDocumentCommand } = useCanvasCommand({
    documentId,
    lookupAdmission,
  });

  const saveMarkdown = useCallback(async () => {
    const result = await runDocumentCommand(
      {
        id: DOCUMENT_SAVE_COMMAND_ID,
        conflictsWith: saveConflicts,
        admission: "none",
        invalidateOnDocumentChange: true,
      },
      async ({ signal }) => {
        if (signal.aborted) throw new Error("Save aborted.");
        await authoring.saveMarkdown();
      },
    );
    if (!result.ok && result.code !== "duplicate_command" && result.code !== "conflict") {
      // Authoring already surfaces save errors on the session; conflict/duplicate are silent no-ops
      // matching prior disabled-button races. Other failures remain visible via authoring.error.
    }
  }, [authoring, runDocumentCommand, saveConflicts]);

  const saveBlockedByCommand = Boolean(
    activeCommand && saveConflicts.includes(activeCommand.id),
  );

  const value = useMemo<MarkdownCanvasSessionValue>(
    () => ({
      documentId,
      phase: authoring.phase,
      record: authoring.record,
      snapshot: authoring.snapshot,
      dirty: authoring.dirty,
      exportedMarkdownAuthoritative: authoring.exportedMarkdownAuthoritative,
      error: authoring.error,
      statusLabel: authoring.statusLabel,
      reconciliation: authoring.reconciliation,
      editorContent: authoring.editorContent,
      documentKey: authoring.documentKey,
      saveDisabled: authoring.saveDisabled || saveBlockedByCommand,
      lastCommitReceipt: authoring.lastCommitReceipt,
      activeCommand,
      editor: authoring.editor,
      setEditor: authoring.setEditor,
      handleEditorUpdate: authoring.handleEditorUpdate,
      markDirty: authoring.markDirty,
      saveMarkdown,
      reimportFromAuthoritativeMarkdown: authoring.reimportFromAuthoritativeMarkdown,
      reloadFromSnapshot: authoring.reloadFromSnapshot,
      discardLocalDraft: authoring.discardLocalDraft,
      getAdmittedDocument,
      lookupAdmission,
      runDocumentCommand,
    }),
    [
      activeCommand,
      authoring,
      documentId,
      getAdmittedDocument,
      lookupAdmission,
      runDocumentCommand,
      saveBlockedByCommand,
      saveMarkdown,
    ],
  );

  return (
    <MarkdownCanvasSessionContext.Provider value={value}>
      {children}
    </MarkdownCanvasSessionContext.Provider>
  );
}

/** Test/helper escape hatch: evaluate admission without React. */
export function evaluateAdmissionForTests(
  args: Parameters<typeof admitDocument>[0],
): AdmittedDocumentEnvelope | null {
  const result = admitDocument(args);
  return result.ok ? result.envelope : null;
}

export type { MarkdownCanvasSessionValue };
export type MarkdownCanvasSessionChildren = ReactNode;
