import { useCallback, useState } from "react";
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
      if (current.status === "saving") {
        return current;
      }
      if (current.status === "idle") {
        return { status: "dirty" };
      }
      if (current.status === "committed" || current.status === "error") {
        return {
          status: "dirty",
          error: undefined,
          warnings: undefined,
          diagnostics: undefined,
        };
      }
      return current;
    });
  }, []);

  const saveMarkdown = useCallback(async () => {
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

    setState({ status: "saving", error: undefined, warnings: undefined, diagnostics: undefined });
    try {
      const prepared = await prepareTiptapMarkdownWrite({
        document_id: planningDocument.documentId,
        title: planningDocument.title,
        target_relpath: planningDocument.targetRelpath,
        markdown,
      });

      if (!prepared.writer_ok || !prepared.writer_confirm_token) {
        setState({
          status: "error",
          error: "Markdown save could not be prepared.",
          warnings: prepared.warnings,
          diagnostics: prepared.diagnostics,
        });
        return;
      }

      const committed = await commitTiptapMarkdownWrite({
        document_id: planningDocument.documentId,
        title: planningDocument.title,
        target_relpath: prepared.target_relpath,
        markdown,
        writer_confirm_token: prepared.writer_confirm_token,
      });

      setState({
        status: "committed",
        committed,
        lastCommittedAt: new Date().toISOString(),
        warnings: prepared.warnings,
        diagnostics: committed.diagnostics.length > 0 ? committed.diagnostics : prepared.diagnostics,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Markdown save failed.";
      setState({
        status: "error",
        error: message.toLowerCase().includes("stale")
          ? "The target file changed while saving. Try again."
          : message,
      });
    }
  }, [exportCurrentMarkdown, planningDocument.documentId, planningDocument.targetRelpath, planningDocument.title]);

  const statusLabel = planMarkdownSaveStatusLabel(state);
  const saveDisabled = !editor || !canSaveToTarget(planningDocument.targetRelpath) || state.status === "saving";

  return {
    state,
    statusLabel,
    saveDisabled,
    markDirty,
    saveMarkdown,
    exportCurrentMarkdown,
  };
}

export type { PlanMarkdownSaveState, PlanMarkdownSaveStatus };
