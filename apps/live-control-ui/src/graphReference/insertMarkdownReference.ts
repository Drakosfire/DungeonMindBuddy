import type { Editor } from "@tiptap/core";

import type { RunbookReferenceAttrs } from "../tiptap/references/runbookReferences";

/** Insert a runbook reference chip into the active markdown editor. */
export function insertMarkdownReference(
  editor: Editor | null | undefined,
  attrs: RunbookReferenceAttrs,
): boolean {
  if (!editor) return false;
  editor.chain().focus().insertRunbookReference(attrs).run();
  return true;
}
