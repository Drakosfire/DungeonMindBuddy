import { useEffect, useMemo, useRef, type ReactNode } from "react";
import type { AnyExtension, Content, Editor, JSONContent } from "@tiptap/core";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import { CalloutNode } from "./extensions/CalloutNode";
import { PLAN_TABLE_EXTENSIONS } from "./extensions/planTableExtensions";
import { RunbookReferenceNode } from "./extensions/RunbookReferenceNode";

export const DEFAULT_MARKDOWN_EDITOR_EXTENSIONS: AnyExtension[] = [
  StarterKit,
  CalloutNode,
  ...PLAN_TABLE_EXTENSIONS,
  RunbookReferenceNode,
];

const NO_EXTRA_EXTENSIONS: AnyExtension[] = [];

export function useMarkdownEditorExtensions(extra: AnyExtension[] = NO_EXTRA_EXTENSIONS): AnyExtension[] {
  return useMemo(
    () => (extra.length === 0 ? DEFAULT_MARKDOWN_EDITOR_EXTENSIONS : [...DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, ...extra]),
    [extra],
  );
}

export type MarkdownEditorUpdateMeta = {
  programmatic: boolean;
};

export type MarkdownEditorCoreProps = {
  content: Content;
  editable?: boolean;
  /** Full override of the default StarterKit/callout/reference extension set. */
  baseExtensions?: AnyExtension[];
  /** Additional extensions appended after baseExtensions. */
  extensions?: AnyExtension[];
  /**
   * Stable identity for the document currently loaded into the editor.
   * TipTap does not treat `content` as a controlled prop; change this key when
   * the caller intentionally replaces the whole document (import/reset/load).
   */
  documentKey?: string | number;
  onUpdate?: (json: JSONContent, editor: Editor, meta: MarkdownEditorUpdateMeta) => void;
  onEditorChange?: (editor: Editor | null) => void;
  className?: string;
  dataTestId?: string;
  children?: (editor: Editor) => ReactNode;
};

export function MarkdownEditorCore({
  content,
  editable = true,
  baseExtensions = DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
  extensions = NO_EXTRA_EXTENSIONS,
  documentKey = "default",
  onUpdate,
  onEditorChange,
  className,
  dataTestId,
  children,
}: MarkdownEditorCoreProps) {
  const resolvedExtensions = useMemo(
    () => (extensions.length === 0 ? baseExtensions : [...baseExtensions, ...extensions]),
    [baseExtensions, extensions],
  );
  // Only the synchronous create/hydration update (if TipTap emits one) is
  // programmatic. Arm during render when documentKey changes (not in a later
  // effect) so a post-paint re-arm cannot suppress the first real user edit.
  const hydrationPendingRef = useRef(true);
  const documentKeyRef = useRef(documentKey);
  if (documentKeyRef.current !== documentKey) {
    documentKeyRef.current = documentKey;
    hydrationPendingRef.current = true;
  }

  const editor = useEditor(
    {
      extensions: resolvedExtensions,
      content,
      editable,
      onUpdate: ({ editor: nextEditor }) => {
        const programmatic = hydrationPendingRef.current;
        if (hydrationPendingRef.current) {
          hydrationPendingRef.current = false;
        }
        onUpdate?.(nextEditor.getJSON(), nextEditor, { programmatic });
      },
    },
    [documentKey],
  );

  useEffect(() => {
    if (!editor) return;
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        hydrationPendingRef.current = false;
      }
    });
    return () => {
      cancelled = true;
    };
  }, [editor]);

  useEffect(() => {
    onEditorChange?.(editor);
    return () => onEditorChange?.(null);
  }, [editor, onEditorChange]);

  useEffect(() => {
    editor?.setEditable(editable);
  }, [editable, editor]);

  if (!editor) {
    return (
      <div className={className} data-testid={dataTestId} data-markdown-editor-status="initializing" />
    );
  }

  return (
    <div className={className} data-testid={dataTestId} data-markdown-editor-status="ready">
      {children ? children(editor) : <EditorContent editor={editor} />}
    </div>
  );
}
