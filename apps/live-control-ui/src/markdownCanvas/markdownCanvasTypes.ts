import type { ReactNode } from "react";
import type { Editor, JSONContent } from "@tiptap/react";

import type {
  TiptapMarkdownWriteCommitResponse,
  WorkspaceDocumentRecord,
  WorkspaceDocumentSnapshot,
} from "../api/types";
import type {
  WorkspaceDocumentLocalKind,
  WorkspaceDocumentLocalSurface,
} from "../tiptap/state/tiptapLocalState";
import type { WorkspaceDocumentAuthoringPhase } from "../workspaceDocument/workspaceDocumentAuthoringMachine";
import type { ReconcileLocalDraftResult } from "../workspaceDocument/reconcileLocalDraft";

/** Policies a tool may request against the current canvas document authority. */
export type DocumentAdmissionPolicy = "loaded" | "editable" | "committed_clean";

/**
 * Neutral admission failure codes. Surface plugins map these to product copy.
 * Intentionally excludes extract-run identity, SourceArtifact, profile, and handoff fields.
 */
export type DocumentAdmissionFailureCode =
  | "document_missing"
  | "document_identity_mismatch"
  | "document_not_loaded"
  | "document_not_editable"
  | "authority_mismatch"
  | "document_dirty"
  | "document_not_committed"
  | "revision_mismatch"
  | "digest_mismatch"
  | "document_not_ready";

/**
 * Immutable document authority admitted under a named policy.
 * Intentionally excludes extract-run identity, SourceArtifact, profile, and handoff fields.
 */
export interface AdmittedDocumentEnvelope {
  documentId: string;
  revision: number;
  contentSha256: string;
  contentStatus: "draft" | "committed";
  documentKind: WorkspaceDocumentLocalKind;
  surfaceId: WorkspaceDocumentLocalSurface;
}

export interface CanvasDocumentState {
  documentId: string;
  phase: WorkspaceDocumentAuthoringPhase;
  record: WorkspaceDocumentRecord | null;
  snapshot: WorkspaceDocumentSnapshot | null;
  dirty: boolean;
  error: string | null;
}

export interface DocumentCommandSpec {
  id: string;
  conflictsWith: readonly string[];
  admission: DocumentAdmissionPolicy | "none";
  invalidateOnDocumentChange?: boolean;
}

export interface DocumentCommandExecuteContext {
  envelope: AdmittedDocumentEnvelope | null;
  signal: AbortSignal;
  documentId: string;
}

export type DocumentCommandFailureCode =
  | "duplicate_command"
  | "conflict"
  | "admission_failed"
  | "invalidated"
  | "aborted"
  | "execute_failed";

export type DocumentCommandResult<T> =
  | { ok: true; value: T }
  | {
    ok: false;
    reason: string;
    code: DocumentCommandFailureCode;
    /** Present when code === admission_failed. Stable machine code for plugin translation. */
    admissionCode?: DocumentAdmissionFailureCode;
    /** Optional neutral detail accompanying admissionCode (e.g. revision inequality). */
    admissionDetail?: string;
  };

export interface ActiveDocumentCommand {
  id: string;
  documentId: string;
  startedAt: number;
}

export type AdmissionLookupResult =
  | { ok: true; envelope: AdmittedDocumentEnvelope }
  | {
    ok: false;
    code: DocumentAdmissionFailureCode;
    /** Optional neutral detail (e.g. revision numbers); never product/surface marketing copy. */
    detail?: string;
  };

export interface MarkdownCanvasSessionValue extends CanvasDocumentState {
  statusLabel: string;
  reconciliation: ReconcileLocalDraftResult | null;
  editorContent: unknown;
  documentKey: string;
  saveDisabled: boolean;
  lastCommitReceipt: TiptapMarkdownWriteCommitResponse | null;
  activeCommand: ActiveDocumentCommand | null;
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
  getAdmittedDocument: (policy: DocumentAdmissionPolicy) => AdmittedDocumentEnvelope | null;
  lookupAdmission: (policy: DocumentAdmissionPolicy) => AdmissionLookupResult;
  runDocumentCommand: <T>(
    spec: DocumentCommandSpec,
    execute: (ctx: DocumentCommandExecuteContext) => Promise<T>,
  ) => Promise<DocumentCommandResult<T>>;
}

export interface MarkdownCanvasSessionProviderProps {
  documentId: string;
  surface: WorkspaceDocumentLocalSurface;
  kind: WorkspaceDocumentLocalKind;
  children: ReactNode;
  storage?: Pick<Storage, "getItem" | "setItem" | "removeItem">;
  emptyMarkdownFallback?: unknown;
  requireDirtyToSave?: boolean;
  canSave?: () => boolean;
  /**
   * Command IDs that mutually conflict with document.save.
   * Declared by the consuming surface/plugin; the session never invents product command names.
   */
  saveConflictsWith?: readonly string[];
}

/** Generic document-save command id owned by the canvas session. */
export const DOCUMENT_SAVE_COMMAND_ID = "document.save";
