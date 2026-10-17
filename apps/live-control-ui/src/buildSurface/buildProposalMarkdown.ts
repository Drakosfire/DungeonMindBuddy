import { parseMarkdownAst } from '../tiptap/markdown/parseMarkdownAst';

/** The page editor retains table content but not column alignment. Keep the original receipt intact. */
export function buildProposalMarkdown(markdown: string) {
  const lines = markdown.split('\n');
  let alignmentAdjusted = false;
  for (const node of parseMarkdownAst(markdown).children) {
    if (node.type !== 'table' || !node.align?.some(Boolean) || !node.position) continue;
    const delimiter = node.position.start.line; // zero-based line after the header
    lines[delimiter] = lines[delimiter]!.replace(/:/g, '');
    alignmentAdjusted = true;
  }
  return { markdown: lines.join('\n'), alignmentAdjusted };
}
