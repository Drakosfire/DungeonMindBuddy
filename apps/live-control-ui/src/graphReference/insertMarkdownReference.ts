import type { Editor } from "@tiptap/core";

import type { GraphProjectionNodeView } from "../api/types";
import { runbookReferenceFromGraphNode } from "../planSurface/reference/runbookReferenceFromGraphNode";
import type { RunbookReferenceAttrs } from "../tiptap/references/runbookReferences";

/** Insert a markdown reference chip into a TipTap editor (surface-neutral name). */
export function insertMarkdownReference(
  editor: Editor | null | undefined,
  attrs: RunbookReferenceAttrs,
): void {
  editor?.chain().focus().insertRunbookReference(attrs).run();
}

/** Build reference attrs from a World Graph projection node. */
export function markdownReferenceFromGraphNode(
  node: GraphProjectionNodeView,
): RunbookReferenceAttrs {
  return runbookReferenceFromGraphNode(node);
}
