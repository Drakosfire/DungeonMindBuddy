import { useMemo } from "react";
import type { Content } from "mdast";
import { parseMarkdownAst } from "../tiptap/markdown/parseMarkdownAst";
import { stripLeadingYamlFrontmatter } from "../tiptap/markdown/stripLeadingYamlFrontmatter";
import { createHeadingIdRegistry, extractPlainTextFromPhrasing } from "./markdownReaderHeadingId";

/** Uses the same canonical parser and duplicate-anchor allocator as the reader. */
export function markdownDocumentHeadings(markdown: string) {
  const ids = createHeadingIdRegistry();
  const headings: { id: string; text: string; depth: number }[] = [];
  function visit(node: Content) {
    if (node.type === "heading") {
      const text = extractPlainTextFromPhrasing(node.children);
      headings.push({ id: ids.allocate(node.children), text, depth: node.depth });
    } else if ("children" in node) for (const child of node.children) visit(child as Content);
  }
  for (const child of parseMarkdownAst(stripLeadingYamlFrontmatter(markdown).markdown).children) visit(child);
  return headings;
}

export function MarkdownDocumentOutline({ markdown }: { markdown: string }) {
  const headings = useMemo(() => markdownDocumentHeadings(markdown), [markdown]);
  const minimumDepth = Math.min(...headings.map(heading => heading.depth));
  return <nav className="markdown-document-outline" aria-label="On this page">
    {headings.length ? <ol>{headings.map(heading => <li key={heading.id}
      style={{ paddingInlineStart: `${Math.min(heading.depth - minimumDepth, 2) * 0.75}rem` }}>
      <a href={`#${heading.id}`}>{heading.text || "Untitled section"}</a>
    </li>)}</ol> : <p>No headings in this document.</p>}
  </nav>;
}
