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
}): { ok: true; envelope: AdmittedDocumentEnvelope } | { ok: false; reason: string } {
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
    return { ok: false, reason: "Open and save this Build source before extraction." };
  }
  if (record.document_id !== documentId) {
    return { ok: false, reason: "Snapshot does not belong to the selected document." };
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
      return { ok: false, reason: "Document is not loaded." };
    }
    return { ok: true, envelope: { ...baseEnvelope } };
  }

  if (policy === "editable") {
    if (!isEditorInteractive(phase)) {
      return { ok: false, reason: "Document is not editable in the current phase." };
    }
    return { ok: true, envelope: { ...baseEnvelope } };
  }

  // committed_clean
  if (localDocumentId == null) {
    return { ok: false, reason: "Open and save this Build source before extraction." };
  }
  if (localDocumentId !== documentId || localSurface !== surface) {
    return { ok: false, reason: "Local draft does not belong to this Build document." };
  }
  if (dirty) {
    return { ok: false, reason: "Save and commit local changes before extraction." };
  }
  if (record.content_status !== "committed") {
    return { ok: false, reason: "Source must be committed before extraction." };
  }
  if (localBaseRevision == null || localBaseContentSha256 == null) {
    return { ok: false, reason: "Open and save this Build source before extraction." };
  }
  if (localBaseRevision !== snapshot.loaded_revision) {
    return {
      ok: false,
      reason: `Local base revision ${localBaseRevision} does not match snapshot revision ${snapshot.loaded_revision}.`,
    };
  }
  if (localBaseContentSha256 !== snapshot.content_sha256) {
    return {
      ok: false,
      reason: "Local base content hash does not match the authoritative snapshot digest.",
    };
  }
  if (phase === "conflict" || phase === "load_error" || phase === "loading" || phase === "unloaded") {
    return { ok: false, reason: "Document is not ready for extraction." };
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
  } = props;

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
    (policy: DocumentAdmissionPolicy) => admitDocument({
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
        conflictsWith: ["build.extract"],
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
  }, [authoring, runDocumentCommand]);

  const value = useMemo<MarkdownCanvasSessionValue>(
    () => ({
      documentId,
      phase: authoring.phase,
      record: authoring.record,
      snapshot: authoring.snapshot,
      dirty: authoring.dirty,
      error: authoring.error,
      statusLabel: authoring.statusLabel,
      reconciliation: authoring.reconciliation,
      editorContent: authoring.editorContent,
      documentKey: authoring.documentKey,
      saveDisabled: authoring.saveDisabled || activeCommand?.id === "build.extract",
      lastCommitReceipt: authoring.lastCommitReceipt,
      activeCommand,
      setEditor: authoring.setEditor,
      handleEditorUpdate: authoring.handleEditorUpdate,
      markDirty: authoring.markDirty,
      saveMarkdown,
      reloadFromSnapshot: authoring.reloadFromSnapshot,
      discardLocalDraft: authoring.discardLocalDraft,
      getAdmittedDocument,
      runDocumentCommand,
    }),
    [
      activeCommand,
      authoring,
      documentId,
      getAdmittedDocument,
      runDocumentCommand,
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
