import type { JSONContent } from '@tiptap/core';

/** The shared named-table format: an unmarked, plain-text H2 before its table. */
export function isPlainTableCaption(node: JSONContent | null | undefined): boolean {
  if (node?.type !== 'heading' || node.attrs?.level !== 2) return false;
  if (Object.entries(node.attrs).some(([key, value]) => key !== 'level' && value != null)) return false;
  const inline = node.content ?? [];
  return inline.every(child => child.type === 'text' && !(child.marks?.length) && typeof child.text === 'string')
    && inline.map(child => child.text).join('').trim().length > 0;
}

export function isTableCaptionAt(content: readonly JSONContent[], index: number): boolean {
  return content[index + 1]?.type === 'table' && isPlainTableCaption(content[index]);
}
