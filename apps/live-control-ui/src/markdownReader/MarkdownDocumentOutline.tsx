import type { Content, Root } from "mdast";
import { parseMarkdownAst } from "../tiptap/markdown/parseMarkdownAst";
import { stripLeadingYamlFrontmatter } from "../tiptap/markdown/stripLeadingYamlFrontmatter";
import { createHeadingIdRegistry, extractPlainTextFromPhrasing } from "./markdownReaderHeadingId";

/** Uses the same canonical parser and duplicate-anchor allocator as the reader. */
export function markdownDocumentHeadings(markdown: string, ast?: Root) {
  const ids = createHeadingIdRegistry();
  const headings: { id: string; text: string; depth: number }[] = [];
  function visit(node: Content) {
    if (node.type === "heading") {
      const text = extractPlainTextFromPhrasing(node.children);
      headings.push({ id: ids.allocate(node.children), text, depth: node.depth });
    } else if ("children" in node) for (const child of node.children) visit(child as Content);
  }
  for (const child of (ast ?? parseMarkdownAst(stripLeadingYamlFrontmatter(markdown).markdown)).children) visit(child);
  return headings;
}
