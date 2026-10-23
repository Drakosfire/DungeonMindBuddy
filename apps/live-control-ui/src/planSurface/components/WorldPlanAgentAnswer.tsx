import { Fragment, memo, useMemo, type ReactNode } from "react";
import type { Root, RootContent } from "mdast";
import { parseMarkdownAst } from "../../tiptap/markdown/parseMarkdownAst";
import { classifyLinkUrl } from "../../markdownReader/markdownReaderUrlPolicy";
import "./WorldPlanAgentAnswer.css";
import {SourceCitation} from "./SourceCitation";

type MarkdownNode = Root | RootContent | { type: string; value?: string; children?: MarkdownNode[]; position?: { start: { offset?: number }; end: { offset?: number } } };

export type InlineAnswerCitation = { segmentIndex: number; label: string; title: string; onOpen: () => void; ariaLabel?: string; expanded?: boolean; controls?: string };

/** Conversation is read-only: editor round-trip admission must not flatten replies. */
function renderMarkdown(root: Root, source: string, allowedInternalLinks: ReadonlySet<string>, citations: readonly (InlineAnswerCitation & { offset: number })[]): ReactNode {
  const placed = new Set<number>();
  let suppressCitations = 0;
  function citation(index: number) {
    placed.add(index);
    const item = citations[index];
    return <SourceCitation key={`citation-${index}`} number={item.label} title={item.title}
      label={item.ariaLabel} expanded={item.expanded} controls={item.controls} onOpen={item.onOpen}/>;
  }
  function literal(node: MarkdownNode): string {
    const start = node.position?.start.offset;
    const end = node.position?.end.offset;
    return start !== undefined && end !== undefined ? source.slice(start, end) : "value" in node ? node.value ?? "" : "";
  }
  function children(node: MarkdownNode, inertCitations = false): ReactNode {
    if (inertCitations) suppressCitations += 1;
    try { return "children" in node ? node.children?.map((child, index) => render(child as MarkdownNode, index)) : null; }
    finally { if (inertCitations) suppressCitations -= 1; }
  }
  function render(node: MarkdownNode, key: number): ReactNode {
    if (suppressCitations) return renderNode(node, key);
    const start = node.position?.start.offset;
    const end = node.position?.end.offset;
    if (node.type === "text" && "value" in node && literal(node) === node.value && start !== undefined && end !== undefined) {
      const matching = citations.flatMap((item, index) => !placed.has(index) && item.offset > start && item.offset <= end ? [{ ...item, index }] : []);
      if (matching.length) {
        let cursor = 0;
        const pieces: ReactNode[] = [];
        for (const item of matching.sort((a, b) => a.offset - b.offset)) {
          const cut = item.offset - start;
          pieces.push(node.value!.slice(cursor, cut), citation(item.index));
          cursor = cut;
        }
        pieces.push(node.value!.slice(cursor));
        return <Fragment key={key}>{pieces}</Fragment>;
      }
    }
    const rendered = renderNode(node, key);
    const markers = node.type === "root" ? [] : citations.flatMap((item, index) => !placed.has(index) && item.offset === end ? [citation(index)] : []);
    return markers.length ? <Fragment key={key}>{rendered}{markers}</Fragment> : rendered;
  }
  function renderNode(node: MarkdownNode, key: number): ReactNode {
    switch (node.type) {
      case "root": return children(node);
      case "text": return "value" in node ? node.value : null;
      case "paragraph": return <p key={key}>{children(node)}</p>;
      case "strong": return <strong key={key}>{children(node)}</strong>;
      case "emphasis": return <em key={key}>{children(node)}</em>;
      case "delete": return <del key={key}>{children(node)}</del>;
      case "inlineCode": return <code key={key}>{"value" in node ? node.value : null}</code>;
      case "code": return <pre key={key}><code>{"value" in node ? node.value : null}</code></pre>;
      case "break": return <br key={key} />;
      case "thematicBreak": return <hr key={key} />;
      case "blockquote": return <blockquote key={key}>{children(node)}</blockquote>;
      case "heading": {
        const depth = "depth" in node ? node.depth : 2;
        const Tag = depth === 1 ? "h1" : depth === 2 ? "h2" : depth === 3 ? "h3" : depth === 4 ? "h4" : depth === 5 ? "h5" : "h6";
        return <Tag key={key}>{children(node)}</Tag>;
      }
      case "list": return "ordered" in node && node.ordered
        ? <ol key={key} start={node.start ?? undefined}>{children(node)}</ol>
        : <ul key={key}>{children(node)}</ul>;
      case "listItem": return <li key={key}>{"checked" in node && typeof node.checked === "boolean"
        ? <input type="checkbox" checked={node.checked} disabled aria-label={node.checked ? "Completed" : "Not completed"} /> : null}{children(node)}</li>;
      case "table": {
        if (!("children" in node)) return literal(node);
        const rows = node.children ?? [];
        const compact = new Set<number>();
        if (rows.length > 1 && rows[0]?.type === "tableRow") {
          const header = rows[0];
          header.children?.forEach((_, column) => {
            if (rows.slice(1).every(item => {
              const cell = item.type === "tableRow" && "children" in item ? item.children?.[column] : undefined;
              const text = cell && "children" in cell && cell.children?.length === 1
                && cell.children[0]?.type === "text" ? cell.children[0].value : "";
              return /^\d{1,3}(?:[–-]\d{1,3})?$/.test((text ?? "").trim());
            })) compact.add(column);
          });
        }
        const row = (item: MarkdownNode, index: number) => {
          const Cell = index === 0 ? "th" : "td";
          return <tr key={index}>{"children" in item && item.children?.map((cell, column) => (
            <Cell key={column} scope={index === 0 ? "col" : undefined} data-compact-column={compact.has(column) || undefined}
              style={{ textAlign: "align" in node ? node.align?.[column] ?? undefined : undefined }}>{children(cell as MarkdownNode)}
              {column === ("children" in item ? item.children!.length - 1 : -1)
                ? citations.flatMap((citationItem, citationIndex) => !placed.has(citationIndex)
                  && citationItem.offset === item.position?.end.offset ? [citation(citationIndex)] : []) : null}</Cell>
          ))}</tr>;
        };
        return <div key={key} className="world-plan-agent-answer__table"><table>
          <thead>{rows[0] ? row(rows[0] as MarkdownNode, 0) : null}</thead>
          <tbody>{rows.slice(1).map((item, index) => row(item as MarkdownNode, index + 1))}</tbody>
        </table></div>;
      }
      case "link": {
        if (!("url" in node)) return literal(node);
        if (node.url.startsWith("dmb-node:")) return <span key={key} className="graph-node-reference-pill recap-node-token" data-plan-card-reference="graph">{children(node)}</span>;
        const kind = classifyLinkUrl(node.url);
        return kind === "safe_external" || kind === "safe_mailto" || kind === "fragment" || (node.url.startsWith("/play?") && allowedInternalLinks.has(node.url))
          ? <a key={key} href={node.url.trim()} rel="noopener noreferrer">{children(node, true)}</a>
          : <span key={key}>{literal(node)}</span>;
      }
      // Raw HTML, embedded media, unresolved references and unknown extensions stay inert.
      default: return <span key={key} className="world-plan-agent-answer__literal">{literal(node)}</span>;
    }
  }
  const rendered = render(root, 0);
  return <>{rendered}{citations.map((_,i)=>!placed.has(i) ? citation(i) : null)}</>;
}

export const WorldPlanAgentAnswer = memo(function WorldPlanAgentAnswerView({ answer, className, allowedInternalLinks = [], displaySegments, inlineCitations = [] }: {
  answer: string;
  className?: string;
  /** Exact server-validated session citations; other relative links stay inert. */
  allowedInternalLinks?: readonly string[];
  /** Evidence boundaries are metadata; parse the whole answer to preserve Markdown blocks. */
  displaySegments?: readonly string[];
  inlineCitations?: readonly InlineAnswerCitation[];
}) {
  const root = useMemo(() => {
    try { return parseMarkdownAst(answer); } catch { return null; }
  }, [answer]);
  const content = useMemo(() => {
    const offsets: number[] = [];
    if (displaySegments?.join("\n") === answer) {
      let offset = 0;
      for (const text of displaySegments) { offsets.push(offset + text.trimEnd().length); offset += text.length + 1; }
    }
    const citations = inlineCitations.flatMap(item => Number.isInteger(item.segmentIndex) && offsets[item.segmentIndex] !== undefined
      ? [{ ...item, offset: offsets[item.segmentIndex] }] : []);
    return root ? renderMarkdown(root, answer, new Set(allowedInternalLinks), citations) : <p style={{ whiteSpace: "pre-wrap" }}>{answer}</p>;
  }, [root, answer, allowedInternalLinks, displaySegments, inlineCitations]);
  return <div className={["world-plan-agent-answer", className].filter(Boolean).join(" ")}>{content}</div>;
});
