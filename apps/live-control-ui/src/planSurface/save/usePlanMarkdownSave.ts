import { useCallback, useMemo, useState } from "react";
import type { Editor } from "@tiptap/react";

import { commitTiptapMarkdownWrite, prepareTiptapMarkdownWrite } from "../../api/liveApi";
import { tiptapJsonToSemanticMarkdown } from "../../tiptap/markdown/calloutMarkdown";
import type { PlanSessionDescriptor } from "../types";
import {
  planMarkdownSaveStatusLabel,
  type PlanMarkdownSaveState,
  type PlanMarkdownSaveStatus,
} from "./planMarkdownSaveTypes";

function canSaveToTarget(targetRelpath: string): boolean {
  return targetRelpath !== "TBD durable planning path";
}

export function usePlanMarkdownSave(args: {
  editor: Editor | null;
  sessionDescriptor: PlanSessionDescriptor;
}) {
  const { editor, sessionDescriptor } = args;
  const planningDocument = sessionDescriptor.planningDocument;
  const [state, setState] = useState<PlanMarkdownSaveState>({ status: "idle" });

  const exportCurrentMarkdown = useCallback((): string | null => {
    if (!editor) return null;
    return tiptapJsonToSemanticMarkdown(editor.getJSON());
  }, [editor]);

  const markDirty = useCallback(() => {
    setState((current) => {
      if (current.status === "committed") {
        return { ...current, status: "dirty", prepared: undefined, preparedMarkdown: undefined };
      }
      if (current.status === "preview_ready" || current.status === "preparing" || current.status === "committing") {
        return current;
      }
      if (current.status === "idle") {
        return { ...current, status: "dirty" };
      }
      return current;
    });
  }, []);

  const prepareSave = useCallback(async () => {
    const markdown = exportCurrentMarkdown();
    if (!markdown?.trim()) {
      setState({ status: "error", error: "Board is empty; add content before saving." });
      return;
    }
    if (!canSaveToTarget(planningDocument.targetRelpath)) {
      setState({
        status: "error",
        error: "Durable target path is not configured for this campaign yet.",
      });
      return;
    }

    setState({ status: "preparing" });
    try {
      const response = await prepareTiptapMarkdownWrite({
        document_id: planningDocument.documentId,
        title: planningDocument.title,
        target_relpath: planningDocument.targetRelpath,
        markdown,
      });
      setState({
        status: "preview_ready",
        prepared: response,
        preparedMarkdown: markdown,
      });
    } catch (error) {
      setState({
        status: "error",
        error: error instanceof Error ? error.message : "Markdown save preview failed.",
      });
    }
  }, [exportCurrentMarkdown, planningDocument.documentId, planningDocument.targetRelpath, planningDocument.title]);

  const canCommit = useMemo(() => {
    if (!state.prepared?.writer_ok || !state.prepared.writer_confirm_token || !state.preparedMarkdown) {
      return false;
    }
    const currentMarkdown = exportCurrentMarkdown();
    return (
      currentMarkdown === state.preparedMarkdown
      && state.prepared.target_relpath === planningDocument.targetRelpath
    );
  }, [exportCurrentMarkdown, planningDocument.targetRelpath, state.prepared, state.preparedMarkdown]);

  const commitSave = useCallback(async () => {
    if (!state.prepared?.writer_confirm_token || !state.preparedMarkdown || !canCommit) return;

    setState((current) => ({ ...current, status: "committing", error: undefined }));
    try {
      const response = await commitTiptapMarkdownWrite({
        document_id: planningDocument.documentId,
        title: planningDocument.title,
        target_relpath: state.prepared.target_relpath,
        markdown: state.preparedMarkdown,
        writer_confirm_token: state.prepared.writer_confirm_token,
      });
      setState({
        status: "committed",
        committed: response,
        lastCommittedAt: new Date().toISOString(),
        prepared: undefined,
        preparedMarkdown: undefined,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Markdown save commit failed.";
      const stale = message.toLowerCase().includes("stale");
      setState({
        status: "error",
        error: stale
          ? "The target file changed. Preview the save again."
          : message,
        prepared: stale ? undefined : state.prepared,
        preparedMarkdown: stale ? undefined : state.preparedMarkdown,
      });
    }
  }, [canCommit, planningDocument.documentId, planningDocument.title, state.prepared, state.preparedMarkdown]);

  const statusLabel = planMarkdownSaveStatusLabel(state);
  const saveDisabled = !editor || !canSaveToTarget(planningDocument.targetRelpath);

  return {
    state,
    statusLabel,
    saveDisabled,
    canCommit,
    markDirty,
    prepareSave,
    commitSave,
    exportCurrentMarkdown,
  };
}

export type { PlanMarkdownSaveState, PlanMarkdownSaveStatus };
