import type { Editor } from "@tiptap/core";

const heldEditors = new WeakSet<Editor>();

export const requiresManualSave = (editor: Editor | null | undefined) => !!editor && heldEditors.has(editor);
export const requireManualSave = (editor: Editor) => { heldEditors.add(editor); };
export const releaseManualSave = (editor: Editor) => { heldEditors.delete(editor); };
