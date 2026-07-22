import { useEffect } from "react";

import type { AppChromeTools } from "../chrome/AppChrome";
import {
  defaultMarkdownDocumentAdapter,
  exportMarkdownWithAdapter,
  importMarkdownWithAdapter,
  type MarkdownDocumentAdapter,
} from "./MarkdownDocumentAdapter";
import { MarkdownEditorCore, type MarkdownEditorCoreProps } from "./MarkdownEditorCore";
import {
  toAppChromeTools,
  type MarkdownEditorToolbarModel,
} from "./MarkdownEditorToolbar";

export type MarkdownEditorProps = MarkdownEditorCoreProps & {
  toolbar?: MarkdownEditorToolbarModel;
  onToolbarChange?: (tools: AppChromeTools | null) => void;
};

export function MarkdownEditor({
  toolbar,
  onToolbarChange,
  ...coreProps
}: MarkdownEditorProps) {
  useEffect(() => {
    if (!toolbar || !onToolbarChange) return;
    onToolbarChange(toAppChromeTools(toolbar));
    return () => onToolbarChange(null);
  }, [onToolbarChange, toolbar]);

  return <MarkdownEditorCore {...coreProps} />;
}

export {
  defaultMarkdownDocumentAdapter,
  exportMarkdownWithAdapter,
  importMarkdownWithAdapter,
};
export type { MarkdownDocumentAdapter };
export { MarkdownEditorCore } from "./MarkdownEditorCore";
export type { MarkdownEditorCoreProps } from "./MarkdownEditorCore";
export {
  MarkdownEditorToolbar,
  toAppChromeTools,
} from "./MarkdownEditorToolbar";
export type {
  MarkdownEditorToolAction,
  MarkdownEditorToolSection,
  MarkdownEditorToolbarModel,
} from "./MarkdownEditorToolbar";
