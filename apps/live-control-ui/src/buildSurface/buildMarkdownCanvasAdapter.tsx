import type { ReactNode } from "react";

import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import type { MarkdownCanvasSlots } from "../markdownCanvas/MarkdownCanvas";
import { useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";

const BUILD_EDITOR_THEME_CLASS = "md-theme-mireward-runbook";

/** Build-owned slot copy for the shared MarkdownCanvas (no footer Save — navbar owns write). */
export function useBuildMarkdownCanvasSlots(args?: {
  statusExtra?: ReactNode;
}): MarkdownCanvasSlots {
  const session = useMarkdownCanvasSession();
  const statusExtra = args?.statusExtra;
  const documentClass = session.record?.document_class?.trim() || null;
  const statusLine = documentClass
    ? `${session.statusLabel} · ${documentClass}`
    : session.statusLabel;

  return {
    title: session.record?.title ?? BUILD_SURFACE_LABEL,
    loadingMessage: "Loading worldbuilding source…",
    errorHeading: BUILD_SURFACE_LABEL,
    conflictHeading: BUILD_SURFACE_LABEL,
    className: "build-surface-shell",
    editorClassName: `build-surface-editor tiptap-spike-editor md-content ${BUILD_EDITOR_THEME_CLASS}`,
    editorMdTheme: "mireward-runbook",
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
        <p data-testid="build-document-status">{statusLine}</p>
        {statusExtra}
      </>
    ),
  };
}

export const BUILD_MARKDOWN_CANVAS = {
  surface: "build" as const,
  kind: "worldbuilding_source" as const,
};
