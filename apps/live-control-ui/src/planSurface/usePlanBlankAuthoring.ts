import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";

import {
  commitTiptapMarkdownWrite,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import {
  buildInitialWorkspaceDocumentLocalState,
  finalizePromotedWorkspaceDocumentLocalState,
  readWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import {
  createWorkspaceDocumentCreationController,
  WorkspaceDocumentCreationError,
  type WorkspaceDocumentCreationController,
} from "../workspaceDocument/workspaceDocumentCreation";
import { workspaceRecordToPlanDocumentDescriptor } from "./config/planSessionDescriptor";
import { createStarterContentForPlanDocument } from "./config/planSessionDescriptor";
import {
  clearPlanLocalDraftPointer,
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

function durablePathGate(record: WorkspaceDocumentRecord): string | null {
  const relpath = record.target_relpath?.trim() ?? "";
  if (!relpath || relpath === "TBD durable planning path") {
    return "Plan durable target path is unavailable; body commit blocked.";
  }
  return null;
}

function adoptDocumentUrl(documentId: string): void {
  if (typeof window === "undefined") return;
  const search = new URLSearchParams(window.location.search);
  search.set("documentId", documentId);
  window.history.replaceState({}, "", `${window.location.pathname}?${search.toString()}`);
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

  const localState = useMemo(() => {
    const existing = readWorkspaceDocumentLocalState(localStorage, draft.localId);
    if (existing) return existing;
    return buildInitialWorkspaceDocumentLocalState({
      documentId: draft.localId,
      title: draft.title,
      campaignId: draft.campaignId,
      kind: "plan",
      targetSession: draft.targetSession,
      surface: "plan",
      baseRevision: 0,
      baseContentSha256: "",
      starterContent: createStarterContentForPlanDocument(sessionDescriptor),
    });
  }, [contentRevision, draft.campaignId, draft.localId, draft.targetSession, draft.title, sessionDescriptor]);

  useEffect(() => {
    const existing = readWorkspaceDocumentLocalState(localStorage, draft.localId);
    if (!existing) {
      writeWorkspaceDocumentLocalState(localStorage, localState);
    }
  }, [draft.localId, localState]);

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

  const handleEditorUpdate = useCallback(
    (json: JSONContent, _editor: Editor, meta: { programmatic: boolean }) => {
      if (meta.programmatic) return;
      const next = {
        ...localState,
        tiptap_json: json,
        exported_markdown: tiptapJsonToSemanticMarkdown(json),
        dirty: true,
        updated_at: new Date().toISOString(),
        last_local_save_at: new Date().toISOString(),
      };
      writeWorkspaceDocumentLocalState(localStorage, next);
      setContentRevision((value) => value + 1);
    },
    [localState],
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
    writeWorkspaceDocumentLocalState(localStorage, {
      ...localState,
      tiptap_json: tiptapJson,
      exported_markdown: markdown,
      dirty: true,
      updated_at: new Date().toISOString(),
      last_local_save_at: new Date().toISOString(),
    });

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
        onPromotionStateChange?.({
          promoting: true,
          retainedCreateId: record.document_id,
          error: null,
        });
        adoptDocumentUrl(record.document_id);
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

    if (retainedCreateId == null || retainedCreateId !== record.document_id) {
      adoptDocumentUrl(record.document_id);
      onPromotionStateChange?.({
        promoting: true,
        retainedCreateId: record.document_id,
        error: null,
      });
    }

    const pathError = durablePathGate(record);
    if (pathError) {
      setPromotionError(pathError);
      onPromotionStateChange?.({
        promoting: true,
        retainedCreateId: record.document_id,
        error: pathError,
      });
      setSaveBusy(false);
      return;
    }

    try {
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: record.document_id,
        markdown,
        expected_revision: record.revision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token) {
        throw new Error("Markdown save could not be prepared.");
      }
      const committed = await commitTiptapMarkdownWrite({
        document_id: record.document_id,
        markdown,
        writer_confirm_token: prepared.writer_confirm_token,
        expected_revision: record.revision,
      });

      finalizePromotedWorkspaceDocumentLocalState(
        localStorage,
        draft.localId,
        record.document_id,
        {
          committedRevision: committed.committed_revision,
          normalizedContentSha256: committed.normalized_content_sha256,
          title: committed.committed_record.title,
          campaignId: committed.committed_record.campaign_id,
          targetSession: committed.committed_record.target_session,
          kind: "plan",
          surface: "plan",
          tiptapJson,
          markdown,
        },
      );
      clearPlanLocalDraftPointer(draft.campaignId, localStorage);

      setPromotionError(null);
      onPromotionStateChange?.({
        promoting: false,
        retainedCreateId: record.document_id,
        error: null,
      });
      onPromoted(workspaceRecordToPlanDocumentDescriptor(committed.committed_record));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save planning document";
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
    draft.campaignId,
    draft.localId,
    draft.targetSession,
    draft.title,
    localState,
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
    documentKey: draft.localId,
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
