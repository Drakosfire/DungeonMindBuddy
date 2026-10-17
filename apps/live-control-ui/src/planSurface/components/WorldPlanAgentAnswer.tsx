import { memo, useMemo, type ReactNode } from "react";
import type { Root, RootContent } from "mdast";
import { parseMarkdownAst } from "../../tiptap/markdown/parseMarkdownAst";
import { classifyLinkUrl } from "../../markdownReader/markdownReaderUrlPolicy";
import "./WorldPlanAgentAnswer.css";

type MarkdownNode = Root | RootContent | { type: string; value?: string; children?: MarkdownNode[]; position?: { start: { offset?: number }; end: { offset?: number } } };

/** Conversation is read-only: editor round-trip admission must not flatten replies. */
function renderMarkdown(root: Root, source: string): ReactNode {
  function literal(node: MarkdownNode): string {
    const start = node.position?.start.offset;
    const end = node.position?.end.offset;
    return start !== undefined && end !== undefined ? source.slice(start, end) : "value" in node ? node.value ?? "" : "";
  }
  function children(node: MarkdownNode): ReactNode {
    return "children" in node ? node.children?.map((child, index) => render(child as MarkdownNode, index)) : null;
  }
  function render(node: MarkdownNode, key: number): ReactNode {
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
        const row = (item: MarkdownNode, index: number) => {
          const Cell = index === 0 ? "th" : "td";
          return <tr key={index}>{"children" in item && item.children?.map((cell, column) => (
            <Cell key={column} scope={index === 0 ? "col" : undefined}
              style={{ textAlign: "align" in node ? node.align?.[column] ?? undefined : undefined }}>{children(cell as MarkdownNode)}</Cell>
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
        return kind === "safe_external" || kind === "safe_mailto" || kind === "fragment"
          ? <a key={key} href={node.url.trim()} rel="noopener noreferrer">{children(node)}</a>
          : <span key={key}>{literal(node)}</span>;
      }
      // Raw HTML, embedded media, unresolved references and unknown extensions stay inert.
      default: return <span key={key} className="world-plan-agent-answer__literal">{literal(node)}</span>;
    }
  }
  return render(root, 0);
}

export const WorldPlanAgentAnswer = memo(function WorldPlanAgentAnswerView({ answer, className }: {
  answer: string;
  className?: string;
  /** Evidence boundaries are metadata; parse the whole answer to preserve Markdown blocks. */
  displaySegments?: readonly string[];
}) {
  const content = useMemo(() => {
    try { return renderMarkdown(parseMarkdownAst(answer), answer); }
    catch { return <p style={{ whiteSpace: "pre-wrap" }}>{answer}</p>; }
  }, [answer]);
  return <div className={["world-plan-agent-answer", className].filter(Boolean).join(" ")}>{content}</div>;
}, (previous, next) => previous.answer === next.answer && previous.className === next.className);
