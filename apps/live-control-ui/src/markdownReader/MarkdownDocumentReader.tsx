import { useMemo, type ReactNode } from "react";
import type {
  Content,
  Definition,
  Image,
  ImageReference,
  Link,
  LinkReference,
  List,
  ListItem,
  PhrasingContent,
  Root,
  RootContent,
  Table,
  TableCell,
  TableRow,
} from "mdast";

import { parseMarkdownAst } from "../tiptap/markdown/parseMarkdownAst";
import { stripLeadingYamlFrontmatter } from "../tiptap/markdown/stripLeadingYamlFrontmatter";
import { classifyImageUrl, classifyLinkUrl } from "./markdownReaderUrlPolicy";

export interface MarkdownDocumentReaderProps {
  /** Exact saved Markdown (may include leading YAML frontmatter). */
  markdown: string;
  className?: string;
}

type DefinitionMap = Map<string, Definition>;

type RenderContext = {
  bodyMarkdown: string;
  definitions: DefinitionMap;
};

function collectDefinitions(root: Root): DefinitionMap {
  const definitions: DefinitionMap = new Map();
  for (const child of root.children) {
    if (child.type === "definition") {
      definitions.set(child.identifier.toLowerCase(), child);
    }
  }
  return definitions;
}

function sourceSlice(node: { position?: { start?: { offset?: number }; end?: { offset?: number } } }, body: string): string | null {
  const start = node.position?.start?.offset;
  const end = node.position?.end?.offset;
  if (typeof start !== "number" || typeof end !== "number") return null;
  if (start < 0 || end < start || end > body.length) return null;
  return body.slice(start, end);
}

function unknownFallback(node: { type: string; position?: { start?: { offset?: number }; end?: { offset?: number } } }, ctx: RenderContext, key: string): ReactNode {
  const slice = sourceSlice(node, ctx.bodyMarkdown);
  if (slice != null && slice.length > 0) {
    return (
      <pre key={key} className="markdown-reader-fallback markdown-reader-fallback--source" data-node-type={node.type}>
        {slice}
      </pre>
    );
  }
  return (
    <p key={key} className="markdown-reader-fallback markdown-reader-fallback--unknown" data-node-type={node.type}>
      Unsupported presentation construct: {node.type}
    </p>
  );
}

function renderChildren(nodes: Content[] | PhrasingContent[] | undefined, ctx: RenderContext, keyPrefix: string): ReactNode[] {
  if (!nodes?.length) return [];
  return nodes.map((child, index) => renderNode(child, ctx, `${keyPrefix}.${index}`));
}

function renderPhrasing(nodes: PhrasingContent[] | undefined, ctx: RenderContext, keyPrefix: string): ReactNode[] {
  return renderChildren(nodes, ctx, keyPrefix);
}

function resolveReference(node: LinkReference | ImageReference, ctx: RenderContext): Definition | null {
  return ctx.definitions.get(node.identifier.toLowerCase()) ?? null;
}

function renderSafeLink(args: {
  url: string;
  title?: string | null;
  children: ReactNode;
  key: string;
}): ReactNode {
  const kind = classifyLinkUrl(args.url);
  if (kind === "safe_external" || kind === "safe_mailto" || kind === "fragment") {
    const isExternal = kind === "safe_external";
    return (
      <a
        key={args.key}
        href={args.url}
        title={args.title ?? undefined}
        {...(isExternal ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      >
        {args.children}
      </a>
    );
  }
  // relative_visible / unsafe — visible text, never an executable/navigating anchor
  return (
    <span
      key={args.key}
      className={
        kind === "relative_visible"
          ? "markdown-reader-link markdown-reader-link--relative"
          : "markdown-reader-link markdown-reader-link--unsafe"
      }
      title={args.title ?? args.url}
      data-link-kind={kind}
    >
      {args.children}
    </span>
  );
}

function renderImage(node: Image, key: string): ReactNode {
  const alt = node.alt ?? "";
  const kind = classifyImageUrl(node.url);
  if (kind === "safe_http") {
    return (
      <img
        key={key}
        className="markdown-reader-image"
        src={node.url}
        alt={alt}
        title={node.title ?? undefined}
        loading="lazy"
      />
    );
  }
  return (
    <span
      key={key}
      className="markdown-reader-unresolved-media"
      data-testid="markdown-reader-unresolved-media"
      data-image-kind={kind}
      title={node.url}
    >
      {alt ? `[Image: ${alt}]` : "[Image]"}
      <span className="markdown-reader-unresolved-media__ref"> ({node.url})</span>
    </span>
  );
}

function renderLink(node: Link, ctx: RenderContext, key: string): ReactNode {
  return renderSafeLink({
    url: node.url,
    title: node.title,
    children: renderPhrasing(node.children, ctx, key),
    key,
  });
}

function renderLinkReference(node: LinkReference, ctx: RenderContext, key: string): ReactNode {
  const definition = resolveReference(node, ctx);
  const label = renderPhrasing(node.children, ctx, key);
  if (!definition) {
    return (
      <span key={key} className="markdown-reader-link markdown-reader-link--unresolved">
        {label}
      </span>
    );
  }
  return renderSafeLink({
    url: definition.url,
    title: definition.title,
    children: label,
    key,
  });
}

function renderImageReference(node: ImageReference, ctx: RenderContext, key: string): ReactNode {
  const definition = resolveReference(node, ctx);
  const alt = node.alt ?? "";
  if (!definition) {
    return (
      <span key={key} className="markdown-reader-unresolved-media" data-testid="markdown-reader-unresolved-media">
        {alt ? `[Image: ${alt}]` : "[Image]"}
        <span className="markdown-reader-unresolved-media__ref"> (unresolved reference)</span>
      </span>
    );
  }
  return renderImage(
    {
      type: "image",
      url: definition.url,
      title: definition.title,
      alt,
    },
    key,
  );
}

function renderListItem(node: ListItem, ctx: RenderContext, key: string): ReactNode {
  const checked = node.checked;
  return (
    <li
      key={key}
      className={checked === null || checked === undefined ? undefined : "markdown-reader-task-item"}
      data-checked={checked === null || checked === undefined ? undefined : String(checked)}
    >
      {checked === true || checked === false ? (
        <span className="markdown-reader-task-marker" aria-hidden="true">
          {checked ? "☑ " : "☐ "}
        </span>
      ) : null}
      {renderChildren(node.children as Content[], ctx, key)}
    </li>
  );
}

function renderList(node: List, ctx: RenderContext, key: string): ReactNode {
  const items = (node.children ?? []).map((item, index) =>
    renderListItem(item, ctx, `${key}.${index}`),
  );
  if (node.ordered) {
    return (
      <ol key={key} start={node.start ?? undefined}>
        {items}
      </ol>
    );
  }
  return <ul key={key}>{items}</ul>;
}

function renderTableCell(node: TableCell, ctx: RenderContext, key: string, header: boolean): ReactNode {
  const Tag = header ? "th" : "td";
  return (
    <Tag key={key}>
      {renderPhrasing(node.children, ctx, key)}
    </Tag>
  );
}

function renderTableRow(node: TableRow, ctx: RenderContext, key: string, header: boolean): ReactNode {
  return (
    <tr key={key}>
      {(node.children ?? []).map((cell, index) =>
        renderTableCell(cell, ctx, `${key}.${index}`, header),
      )}
    </tr>
  );
}

function renderTable(node: Table, ctx: RenderContext, key: string): ReactNode {
  const rows = node.children ?? [];
  const [head, ...body] = rows;
  return (
    <div key={key} className="markdown-reader-table-wrap">
      <table>
        {head ? <thead>{renderTableRow(head, ctx, `${key}.head`, true)}</thead> : null}
        {body.length > 0 ? (
          <tbody>
            {body.map((row, index) => renderTableRow(row, ctx, `${key}.body.${index}`, false))}
          </tbody>
        ) : null}
      </table>
    </div>
  );
}

function renderNode(node: RootContent | Content | PhrasingContent, ctx: RenderContext, key: string): ReactNode {
  switch (node.type) {
    case "text":
      return <span key={key}>{node.value}</span>;
    case "paragraph":
      return <p key={key}>{renderPhrasing(node.children, ctx, key)}</p>;
    case "heading": {
      const depth = Math.min(6, Math.max(1, node.depth)) as 1 | 2 | 3 | 4 | 5 | 6;
      const Tag = `h${depth}` as const;
      return <Tag key={key}>{renderPhrasing(node.children, ctx, key)}</Tag>;
    }
    case "emphasis":
      return <em key={key}>{renderPhrasing(node.children, ctx, key)}</em>;
    case "strong":
      return <strong key={key}>{renderPhrasing(node.children, ctx, key)}</strong>;
    case "delete":
      return <del key={key}>{renderPhrasing(node.children, ctx, key)}</del>;
    case "inlineCode":
      return <code key={key}>{node.value}</code>;
    case "break":
      return <br key={key} />;
    case "thematicBreak":
      return <hr key={key} />;
    case "blockquote":
      return <blockquote key={key}>{renderChildren(node.children, ctx, key)}</blockquote>;
    case "code":
      return (
        <pre key={key} className="markdown-reader-code">
          <code className={node.lang ? `language-${node.lang}` : undefined}>{node.value}</code>
        </pre>
      );
    case "list":
      return renderList(node, ctx, key);
    case "listItem":
      return renderListItem(node, ctx, key);
    case "table":
      return renderTable(node, ctx, key);
    case "tableRow":
      return renderTableRow(node, ctx, key, false);
    case "tableCell":
      return renderTableCell(node, ctx, key, false);
    case "link":
      return renderLink(node, ctx, key);
    case "linkReference":
      return renderLinkReference(node, ctx, key);
    case "image":
      return renderImage(node, key);
    case "imageReference":
      return renderImageReference(node, ctx, key);
    case "html":
      return (
        <pre
          key={key}
          className="markdown-reader-html-literal"
          data-testid="markdown-reader-html-literal"
        >
          {node.value}
        </pre>
      );
    case "definition":
      // Definitions are consumed by reference resolution; omit from prose.
      return null;
    case "yaml":
      // Frontmatter is stripped before parse; if present, omit from prose.
      return null;
    default:
      return unknownFallback(node, ctx, key);
  }
}

/**
 * Read-only semantic React document from exact Markdown via the canonical MDAST parser.
 * Does not use TipTap. Never executes raw HTML. Never writes source.
 */
export function MarkdownDocumentReader({ markdown, className }: MarkdownDocumentReaderProps) {
  const bodyMarkdown = useMemo(
    () => stripLeadingYamlFrontmatter(markdown).markdown,
    [markdown],
  );
  const ast = useMemo(() => parseMarkdownAst(bodyMarkdown), [bodyMarkdown]);
  const definitions = useMemo(() => collectDefinitions(ast), [ast]);
  const ctx = useMemo<RenderContext>(
    () => ({ bodyMarkdown, definitions }),
    [bodyMarkdown, definitions],
  );

  return (
    <div
      className={["markdown-document-reader", className].filter(Boolean).join(" ")}
      data-testid="markdown-document-reader"
    >
      {ast.children.map((child, index) => renderNode(child, ctx, `root.${index}`))}
    </div>
  );
}
