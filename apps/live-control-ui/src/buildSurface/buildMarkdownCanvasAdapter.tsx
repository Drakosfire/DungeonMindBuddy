import type { ReactNode } from "react";

import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";

/** Build-owned slot copy and Save action for the shared MarkdownCanvas. */
export function useBuildMarkdownCanvasSlots(args?: {
  statusExtra?: ReactNode;
  /** When shared Edit Host publishes Save, omit the duplicate footer button. */
  hideFooterSave?: boolean;
}): MarkdownCanvasSlots {
  const session = useMarkdownCanvasSession();
  const statusExtra = args?.statusExtra;
  const hideFooterSave = args?.hideFooterSave === true;

  return {
    title: session.record?.title ?? BUILD_SURFACE_LABEL,
    loadingMessage: "Loading worldbuilding source…",
    errorHeading: BUILD_SURFACE_LABEL,
    conflictHeading: BUILD_SURFACE_LABEL,
    className: "build-surface-shell",
    editorClassName: "build-surface-editor tiptap-spike-editor",
    dataTestId: "build-surface-shell",
    editorDataTestId: "build-markdown-editor",
    loadingTestId: "build-surface-loading",
    errorTestId: "build-surface-error",
    authorityErrorTestId: "build-authority-error",
    conflictTestId: "build-surface-conflict",
    saveErrorTestId: "build-save-error",
    hideDefaultStatus: true,
    statusExtra: (
      <>
        <p data-testid="build-document-status">{session.statusLabel}</p>
        <p data-testid="build-authoring-status">{session.statusLabel}</p>
        {session.record?.document_class ? (
          <p data-testid="build-document-class">{session.record.document_class}</p>
        ) : null}
        {statusExtra}
      </>
    ),
    actions: hideFooterSave ? undefined : (
      <button
        type="button"
        data-testid="build-save-button"
        disabled={session.saveDisabled}
        onClick={() => void session.saveMarkdown()}
      >
        Save
      </button>
    ),
  };
}

export const BUILD_MARKDOWN_CANVAS = {
  surface: "build" as const,
  kind: "worldbuilding_source" as const,
};
