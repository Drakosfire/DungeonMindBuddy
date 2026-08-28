import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";

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
import {
  buildInitialWorkspaceDocumentLocalState,
  finalizePromotedWorkspaceDocumentLocalState,
  migrateWorkspaceDocumentLocalStateId,
  readWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
  type WorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { verifyCommitReceiptAgainstSnapshot } from "../workspaceDocument/verifyCommitReceiptAgainstSnapshot";
import {
  createWorkspaceDocumentCreationController,
  WorkspaceDocumentCreationError,
  type WorkspaceDocumentCreationController,
} from "../workspaceDocument/workspaceDocumentCreation";
import { workspaceRecordToPlanDocumentDescriptor } from "./config/planSessionDescriptor";
import { createStarterContentForPlanDocument } from "./config/planSessionDescriptor";
import {
  clearPlanLocalDraftPointer,
  validatePlanCreateResponse,
  validatePlanPostCommitSnapshotAdmission,
  validatePlanPromotionSnapshotAdmission,
  type PlanLocalDraft,
} from "./planBlankAuthoringState";
import type { PlanSessionDescriptor } from "./types";

export interface UsePlanBlankAuthoringArgs {
  draft: PlanLocalDraft;
  sessionDescriptor: PlanSessionDescriptor;
  selectorListAvailable: boolean;
  retainedCreateId: string | null;
  createController?: WorkspaceDocumentCreationController;
  onPromoted: (document: ReturnType<typeof workspaceRecordToPlanDocumentDescriptor>) => void;
  onPromotionStateChange?: (args: {
    promoting: boolean;
    retainedCreateId: string | null;
    error: string | null;
  }) => void;
}

export interface PlanBlankAuthoringValue {
  editorContent: JSONContent;
  documentKey: string;
  statusLabel: string;
  saveDisabled: boolean;
  saveDisabledReason: string | null;
  saveBusy: boolean;
  promotionError: string | null;
  setEditor: (editor: Editor | null) => void;
  handleEditorUpdate: (
    json: JSONContent,
    editor: Editor,
    meta: { programmatic: boolean },
  ) => void;
  saveMarkdown: () => Promise<void>;
}

function adoptDocumentUrl(documentId: string): void {
  if (typeof window === "undefined") return;
  const search = new URLSearchParams(window.location.search);
  search.set("documentId", documentId);
  window.history.replaceState({}, "", `${window.location.pathname}?${search.toString()}`);
}

function persistDirtyEditorBytes(
  storage: Pick<Storage, "getItem" | "setItem" | "removeItem">,
  documentId: string,
  args: {
    tiptapJson: unknown;
    markdown: string;
    fallback: WorkspaceDocumentLocalState;
  },
): WorkspaceDocumentLocalState {
  const now = new Date().toISOString();
  const existing = readWorkspaceDocumentLocalState(storage, documentId) ?? args.fallback;
  const next: WorkspaceDocumentLocalState = {
    ...existing,
    document_id: documentId,
    tiptap_json: args.tiptapJson,
    exported_markdown: args.markdown,
    dirty: true,
    updated_at: now,
    last_local_save_at: now,
  };
  writeWorkspaceDocumentLocalState(storage, next);
  return next;
}

function mirrorLocalStateToDurableId(args: {
  storage: Pick<Storage, "getItem" | "setItem" | "removeItem">;
  localDraftId: string;
  durableId: string;
  snapshot: WorkspaceDocumentSnapshot;
  record: WorkspaceDocumentRecord;
  tiptapJson: unknown;
  markdown: string;
  fallback: WorkspaceDocumentLocalState;
}): WorkspaceDocumentLocalState {
  const { storage, localDraftId, durableId, snapshot, record } = args;
  if (localDraftId !== durableId) {
    migrateWorkspaceDocumentLocalStateId(storage, localDraftId, durableId, {
      title: record.title,
      campaign_id: record.campaign_id,
      target_session: record.target_session,
      base_revision: snapshot.loaded_revision,
      base_content_sha256: snapshot.content_sha256,
    });
  } else {
    const existing = readWorkspaceDocumentLocalState(storage, durableId) ?? args.fallback;
    writeWorkspaceDocumentLocalState(storage, {
      ...existing,
      document_id: durableId,
      title: record.title,
      campaign_id: record.campaign_id,
      target_session: record.target_session,
      base_revision: snapshot.loaded_revision,
      base_content_sha256: snapshot.content_sha256,
      dirty: true,
      updated_at: new Date().toISOString(),
      last_local_save_at: new Date().toISOString(),
    });
  }
  return persistDirtyEditorBytes(storage, durableId, {
    tiptapJson: args.tiptapJson,
    markdown: args.markdown,
    fallback: args.fallback,
  });
}

function applyCommitReceiptBaseRetainingEditorContent(args: {
  receipt: TiptapMarkdownWriteCommitResponse;
  current: WorkspaceDocumentLocalState;
}): WorkspaceDocumentLocalState {
  const now = new Date().toISOString();
  const committedRevision = Number.isInteger(args.receipt.committed_revision)
    ? args.receipt.committed_revision
    : args.current.base_revision;
  const committedContentSha256 =
    typeof args.receipt.normalized_content_sha256 === "string"
      && args.receipt.normalized_content_sha256.trim()
      ? args.receipt.normalized_content_sha256
      : args.current.base_content_sha256;
  return {
    ...args.current,
    base_revision: committedRevision,
    base_content_sha256: committedContentSha256,
    dirty: true,
    updated_at: now,
    last_local_save_at: now,
  };
}

export function usePlanBlankAuthoring(args: UsePlanBlankAuthoringArgs): PlanBlankAuthoringValue {
  const {
    draft,
    sessionDescriptor,
    selectorListAvailable,
    retainedCreateId,
    onPromoted,
    onPromotionStateChange,
  } = args;
  const createControllerRef = useRef(args.createController ?? createWorkspaceDocumentCreationController());
  const editorRef = useRef<Editor | null>(null);
  const [promotionError, setPromotionError] = useState<string | null>(null);
  const [saveBusy, setSaveBusy] = useState(false);
  const [contentRevision, setContentRevision] = useState(0);

  const activeDocumentKey = retainedCreateId ?? draft.localId;

  const buildFallbackLocalState = useCallback((): WorkspaceDocumentLocalState => {
    return buildInitialWorkspaceDocumentLocalState({
      documentId: activeDocumentKey,
      title: draft.title,
      campaignId: draft.campaignId,
      kind: "plan",
      targetSession: draft.targetSession,
      surface: "plan",
      baseRevision: 0,
      baseContentSha256: "",
      starterContent: createStarterContentForPlanDocument(sessionDescriptor),
    });
  }, [
    activeDocumentKey,
    draft.campaignId,
    draft.targetSession,
    draft.title,
    sessionDescriptor,
  ]);

  const localState = useMemo(() => {
    const durable = readWorkspaceDocumentLocalState(localStorage, activeDocumentKey);
    if (durable) return durable;
    if (activeDocumentKey !== draft.localId) {
      const fromLocal = readWorkspaceDocumentLocalState(localStorage, draft.localId);
      if (fromLocal) return fromLocal;
    }
    return buildFallbackLocalState();
  }, [activeDocumentKey, buildFallbackLocalState, contentRevision, draft.localId]);

  useEffect(() => {
    const existing = readWorkspaceDocumentLocalState(localStorage, activeDocumentKey);
    if (!existing) {
      writeWorkspaceDocumentLocalState(localStorage, localState);
    }
  }, [activeDocumentKey, localState]);

  const saveDisabledReason = useMemo(() => {
    if (!selectorListAvailable) {
      return "Active Plan inventory is unavailable; target session cannot be chosen safely.";
    }
    if (draft.targetSession == null) {
      return "No durable target session is available yet.";
    }
    return null;
  }, [draft.targetSession, selectorListAvailable]);

  const setEditor = useCallback((editor: Editor | null) => {
    editorRef.current = editor;
  }, []);

  const bumpContentRevision = useCallback(() => {
    setContentRevision((value) => value + 1);
  }, []);

  const handleEditorUpdate = useCallback(
    (json: JSONContent, _editor: Editor, meta: { programmatic: boolean }) => {
      if (meta.programmatic) return;
      const next = {
        ...localState,
        document_id: activeDocumentKey,
        tiptap_json: json,
        exported_markdown: tiptapJsonToSemanticMarkdown(json),
        dirty: true,
        updated_at: new Date().toISOString(),
        last_local_save_at: new Date().toISOString(),
      };
      writeWorkspaceDocumentLocalState(localStorage, next);
      bumpContentRevision();
    },
    [activeDocumentKey, bumpContentRevision, localState],
  );

  const saveMarkdown = useCallback(async () => {
    if (saveDisabledReason) {
      throw new Error(saveDisabledReason);
    }
    const editor = editorRef.current;
    if (!editor) {
      throw new Error("Editor is not ready.");
    }
    const markdown = tiptapJsonToSemanticMarkdown(editor.getJSON());
    const tiptapJson = editor.getJSON();
    const fallback = buildFallbackLocalState();
    persistDirtyEditorBytes(localStorage, activeDocumentKey, {
      tiptapJson,
      markdown,
      fallback,
    });
    bumpContentRevision();

    setSaveBusy(true);
    setPromotionError(null);
    onPromotionStateChange?.({
      promoting: true,
      retainedCreateId,
      error: null,
    });

    const controller = createControllerRef.current;
    let record: WorkspaceDocumentRecord;
    const retained = controller.getState().record;
    if (retained != null && (retainedCreateId == null || retained.document_id === retainedCreateId)) {
      record = retained;
    } else {
      try {
        const created = await controller.create({
          kind: "plan",
          campaignId: draft.campaignId,
          title: draft.title,
          targetSession: draft.targetSession as number,
        });
        if (!created.intentCurrent) {
          setSaveBusy(false);
          onPromotionStateChange?.({ promoting: false, retainedCreateId: null, error: null });
          return;
        }
        record = created.record;
      } catch (error) {
        const message =
          error instanceof WorkspaceDocumentCreationError
            ? error.message
            : error instanceof Error
              ? error.message
              : "Failed to create planning document";
        setPromotionError(message);
        onPromotionStateChange?.({ promoting: false, retainedCreateId: null, error: message });
        setSaveBusy(false);
        return;
      }
    }

    const createValidationError = validatePlanCreateResponse(record, draft);
    if (createValidationError) {
      const durableId =
        record != null && typeof record.document_id === "string"
          ? record.document_id.trim()
          : "";
      if (durableId) {
        adoptDocumentUrl(durableId);
        persistDirtyEditorBytes(localStorage, durableId, {
          tiptapJson,
          markdown,
          fallback,
        });
      }
      bumpContentRevision();
      setPromotionError(createValidationError);
      onPromotionStateChange?.(
        durableId
          ? {
              promoting: true,
              retainedCreateId: durableId,
              error: createValidationError,
            }
          : { promoting: false, retainedCreateId: null, error: createValidationError },
      );
      setSaveBusy(false);
      return;
    }

    if (retainedCreateId == null || retainedCreateId !== record.document_id) {
      adoptDocumentUrl(record.document_id);
      onPromotionStateChange?.({
        promoting: true,
        retainedCreateId: record.document_id,
        error: null,
      });
    }

    let admittedSnapshot: WorkspaceDocumentSnapshot;
    try {
      admittedSnapshot = await getWorkspaceDocumentSnapshot(record.document_id);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Plan promotion snapshot could not be loaded.";
      persistDirtyEditorBytes(localStorage, record.document_id, {
        tiptapJson,
        markdown,
        fallback,
      });
      bumpContentRevision();
      setPromotionError(message);
      onPromotionStateChange?.({
        promoting: true,
        retainedCreateId: record.document_id,
        error: message,
      });
      setSaveBusy(false);
      return;
    }

    const admissionError = validatePlanPromotionSnapshotAdmission(admittedSnapshot, record, draft);
    if (admissionError) {
      persistDirtyEditorBytes(localStorage, record.document_id, {
        tiptapJson,
        markdown,
        fallback,
      });
      bumpContentRevision();
      setPromotionError(admissionError);
      onPromotionStateChange?.({
        promoting: true,
        retainedCreateId: record.document_id,
        error: admissionError,
      });
      setSaveBusy(false);
      return;
    }

    mirrorLocalStateToDurableId({
      storage: localStorage,
      localDraftId: draft.localId,
      durableId: record.document_id,
      snapshot: admittedSnapshot,
      record,
      tiptapJson,
      markdown,
      fallback,
    });
    bumpContentRevision();

    try {
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: record.document_id,
        markdown,
        expected_revision: admittedSnapshot.loaded_revision,
      });
      if (prepared.document_id !== record.document_id) {
        throw new Error("Markdown prepare receipt document_id does not match promoted document.");
      }
      if (!prepared.writer_ok || !prepared.writer_confirm_token) {
        throw new Error("Markdown save could not be prepared.");
      }
      const committed = await commitTiptapMarkdownWrite({
        document_id: record.document_id,
        markdown,
        writer_confirm_token: prepared.writer_confirm_token,
        expected_revision: admittedSnapshot.loaded_revision,
      });

      if (!committed.writer_ok) {
        throw new Error("Markdown save was not committed.");
      }
      if (committed.document_id !== record.document_id) {
        throw new Error("Commit receipt document_id does not match promoted document.");
      }

      if (
        typeof committed.file_fingerprint !== "string"
        || !committed.file_fingerprint.trim()
      ) {
        const retainedLocal = readWorkspaceDocumentLocalState(localStorage, record.document_id);
        if (retainedLocal) {
          writeWorkspaceDocumentLocalState(
            localStorage,
            applyCommitReceiptBaseRetainingEditorContent({
              receipt: committed,
              current: retainedLocal,
            }),
          );
          bumpContentRevision();
        }
        const message = "Commit receipt is missing file_fingerprint after successful write.";
        setPromotionError(message);
        onPromotionStateChange?.({
          promoting: true,
          retainedCreateId: record.document_id,
          error: message,
        });
        setSaveBusy(false);
        return;
      }

      let refreshedSnapshot: WorkspaceDocumentSnapshot;
      try {
        refreshedSnapshot = await getWorkspaceDocumentSnapshot(record.document_id);
      } catch (error) {
        const retainedLocal = readWorkspaceDocumentLocalState(localStorage, record.document_id);
        if (retainedLocal) {
          writeWorkspaceDocumentLocalState(
            localStorage,
            applyCommitReceiptBaseRetainingEditorContent({
              receipt: committed,
              current: retainedLocal,
            }),
          );
          bumpContentRevision();
        }
        const message =
          error instanceof Error
            ? error.message
            : "Commit succeeded; snapshot verification failed.";
        setPromotionError(message);
        onPromotionStateChange?.({
          promoting: true,
          retainedCreateId: record.document_id,
          error: message,
        });
        setSaveBusy(false);
        return;
      }

      const postCommitRecord = committed.committed_record;
      const postCommitAdmissionError = validatePlanPostCommitSnapshotAdmission(
        refreshedSnapshot,
        postCommitRecord,
        draft,
      );
      if (postCommitAdmissionError) {
        const retainedLocal = readWorkspaceDocumentLocalState(localStorage, record.document_id);
        if (retainedLocal) {
          writeWorkspaceDocumentLocalState(
            localStorage,
            applyCommitReceiptBaseRetainingEditorContent({
              receipt: committed,
              current: retainedLocal,
            }),
          );
          bumpContentRevision();
        }
        setPromotionError(postCommitAdmissionError);
        onPromotionStateChange?.({
          promoting: true,
          retainedCreateId: record.document_id,
          error: postCommitAdmissionError,
        });
        setSaveBusy(false);
        return;
      }

      const verification = verifyCommitReceiptAgainstSnapshot(committed, refreshedSnapshot);
      if (!verification.ok) {
        const retainedLocal = readWorkspaceDocumentLocalState(localStorage, record.document_id);
        if (retainedLocal) {
          writeWorkspaceDocumentLocalState(
            localStorage,
            applyCommitReceiptBaseRetainingEditorContent({
              receipt: committed,
              current: retainedLocal,
            }),
          );
          bumpContentRevision();
        }
        setPromotionError(verification.reason);
        onPromotionStateChange?.({
          promoting: true,
          retainedCreateId: record.document_id,
          error: verification.reason,
        });
        setSaveBusy(false);
        return;
      }

      finalizePromotedWorkspaceDocumentLocalState(
        localStorage,
        draft.localId,
        record.document_id,
        {
          committedRevision: refreshedSnapshot.loaded_revision,
          normalizedContentSha256: refreshedSnapshot.content_sha256,
          title: refreshedSnapshot.record.title,
          campaignId: refreshedSnapshot.record.campaign_id,
          targetSession: refreshedSnapshot.record.target_session,
          kind: "plan",
          surface: "plan",
          tiptapJson,
          markdown,
        },
      );
      clearPlanLocalDraftPointer(draft.campaignId, localStorage);
      bumpContentRevision();

      setPromotionError(null);
      onPromotionStateChange?.({
        promoting: false,
        retainedCreateId: record.document_id,
        error: null,
      });
      onPromoted(workspaceRecordToPlanDocumentDescriptor(refreshedSnapshot.record));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save planning document";
      persistDirtyEditorBytes(localStorage, record.document_id, {
        tiptapJson,
        markdown,
        fallback,
      });
      bumpContentRevision();
      setPromotionError(message);
      onPromotionStateChange?.({
        promoting: true,
        retainedCreateId: record.document_id,
        error: message,
      });
      setSaveBusy(false);
      return;
    }

    setSaveBusy(false);
  }, [
    activeDocumentKey,
    buildFallbackLocalState,
    bumpContentRevision,
    draft,
    onPromoted,
    onPromotionStateChange,
    retainedCreateId,
    saveDisabledReason,
  ]);

  const statusLabel = useMemo(() => {
    if (saveBusy && !retainedCreateId) return "Creating Plan…";
    if (saveBusy) return "Saving to Markdown…";
    if (promotionError && retainedCreateId) return "Save failed — retry";
    if (retainedCreateId) return "Plan created · save pending";
    return "Local draft · not yet saved to Markdown";
  }, [promotionError, retainedCreateId, saveBusy]);

  return {
    editorContent: localState.tiptap_json as JSONContent,
    documentKey: activeDocumentKey,
    statusLabel,
    saveDisabled: saveDisabledReason != null || saveBusy,
    saveDisabledReason,
    saveBusy,
    promotionError,
    setEditor,
    handleEditorUpdate,
    saveMarkdown,
  };
}
