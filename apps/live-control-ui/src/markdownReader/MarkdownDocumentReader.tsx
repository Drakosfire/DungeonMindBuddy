import { useEffect, useMemo, useRef, type ReactNode } from "react";
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
import { splitLeadingYamlFrontmatter, stripLeadingYamlFrontmatter } from "../tiptap/markdown/stripLeadingYamlFrontmatter";
import { createHeadingIdRegistry, type HeadingIdRegistry } from "./markdownReaderHeadingId";
import { classifyImageUrl, classifyLinkUrl } from "./markdownReaderUrlPolicy";

export interface MarkdownSourceLineTarget {
  /** 1-based full saved-source line (includes YAML frontmatter). */
  startLine: number;
  /** 1-based full saved-source line (includes YAML frontmatter). */
  endLine: number;
  /** Scroll/highlight identity — scroll runs once per distinct key. */
  targetKey: string;
}

export interface MarkdownDocumentReaderProps {
  /** Exact saved Markdown (may include leading YAML frontmatter). */
  markdown: string;
  className?: string;
  /** When set, highlight rendered blocks intersecting the full-source line range. */
  sourceLineTarget?: MarkdownSourceLineTarget | null;
}

type DefinitionMap = Map<string, Definition>;

type RenderContext = {
  bodyMarkdown: string;
  definitions: DefinitionMap;
  headingIds: HeadingIdRegistry;
  highlightKeys: ReadonlySet<string> | null;
};

function countNewlines(text: string): number {
  let count = 0;
  for (let index = 0; index < text.length; index += 1) {
    if (text[index] === "\n") count += 1;
  }
  return count;
}

function frontmatterLineOffset(fullMarkdown: string): number {
  const split = splitLeadingYamlFrontmatter(fullMarkdown);
  if (!split.removedLength) return 0;
  return countNewlines(fullMarkdown.slice(0, split.removedLength));
}

function isHighlightableBlock(node: RootContent | Content): boolean {
  switch (node.type) {
    case "paragraph":
    case "heading":
    case "blockquote":
    case "code":
    case "list":
    case "table":
    case "html":
    case "listItem":
      return true;
    default:
      return false;
  }
}

type PositionedBlock = {
  key: string;
  startFull: number;
  endFull: number;
};

function collectIntersectingBlocks(
  nodes: Array<RootContent | Content>,
  keyPrefix: string,
  lineOffset: number,
  targetStart: number,
  targetEnd: number,
  out: PositionedBlock[],
): void {
  for (let index = 0; index < nodes.length; index += 1) {
    const node = nodes[index];
    const key = `${keyPrefix}.${index}`;
    const startLine = node.position?.start?.line;
    const endLine = node.position?.end?.line;
    if (typeof startLine === "number" && typeof endLine === "number") {
      const startFull = startLine + lineOffset;
      const endFull = endLine + lineOffset;
      if (startFull <= targetEnd && endFull >= targetStart && isHighlightableBlock(node)) {
        out.push({ key, startFull, endFull });
      }
    }
    if ("children" in node && Array.isArray(node.children)) {
      collectIntersectingBlocks(
        node.children as Array<RootContent | Content>,
        key,
        lineOffset,
        targetStart,
        targetEnd,
        out,
      );
    }
  }
}

function minimalHighlightKeys(blocks: PositionedBlock[]): ReadonlySet<string> {
  const keys = new Set<string>();
  for (const block of blocks) {
    const span = block.endFull - block.startFull;
    const hasSmallerDescendant = blocks.some(
      (other) =>
        other.key !== block.key
        && other.startFull >= block.startFull
        && other.endFull <= block.endFull
        && other.endFull - other.startFull < span,
    );
    if (!hasSmallerDescendant) {
      keys.add(block.key);
    }
  }
  return keys;
}

function resolveHighlightKeys(
  ast: Root,
  fullMarkdown: string,
  target: MarkdownSourceLineTarget | null | undefined,
): ReadonlySet<string> | null {
  if (!target) return null;
  const lineOffset = frontmatterLineOffset(fullMarkdown);
  const blocks: PositionedBlock[] = [];
  collectIntersectingBlocks(
    ast.children,
    "root",
    lineOffset,
    target.startLine,
    target.endLine,
    blocks,
  );
  if (blocks.length === 0) return new Set();
  return minimalHighlightKeys(blocks);
}

function highlightClass(key: string, ctx: RenderContext): string | undefined {
  if (!ctx.highlightKeys?.has(key)) return undefined;
  return "markdown-reader-source-highlight";
}

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
      <pre
        key={key}
        className={["markdown-reader-fallback", "markdown-reader-fallback--source", highlightClass(key, ctx)].filter(Boolean).join(" ")}
        data-node-type={node.type}
        data-source-block={highlightClass(key, ctx) ? "true" : undefined}
      >
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
  const highlight = highlightClass(key, ctx);
  return (
    <li
      key={key}
      className={[
        checked === null || checked === undefined ? undefined : "markdown-reader-task-item",
        highlight,
      ].filter(Boolean).join(" ") || undefined}
      data-checked={checked === null || checked === undefined ? undefined : String(checked)}
      data-source-block={highlight ? "true" : undefined}
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
  const highlight = highlightClass(key, ctx);
  if (node.ordered) {
    return (
      <ol
        key={key}
        start={node.start ?? undefined}
        className={highlight}
        data-source-block={highlight ? "true" : undefined}
      >
        {items}
      </ol>
    );
  }
  return (
    <ul key={key} className={highlight} data-source-block={highlight ? "true" : undefined}>
      {items}
    </ul>
  );
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
  const highlight = highlightClass(key, ctx);
  return (
    <div
      key={key}
      className={["markdown-reader-table-wrap", highlight].filter(Boolean).join(" ")}
      data-source-block={highlight ? "true" : undefined}
    >
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
    case "paragraph": {
      const highlight = highlightClass(key, ctx);
      return (
        <p key={key} className={highlight} data-source-block={highlight ? "true" : undefined}>
          {renderPhrasing(node.children, ctx, key)}
        </p>
      );
    }
    case "heading": {
      const depth = Math.min(6, Math.max(1, node.depth)) as 1 | 2 | 3 | 4 | 5 | 6;
      const Tag = `h${depth}` as const;
      const id = ctx.headingIds.allocate(node.children);
      const highlight = highlightClass(key, ctx);
      return (
        <Tag key={key} id={id} className={highlight} data-source-block={highlight ? "true" : undefined}>
          {renderPhrasing(node.children, ctx, key)}
        </Tag>
      );
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
    case "blockquote": {
      const highlight = highlightClass(key, ctx);
      return (
        <blockquote key={key} className={highlight} data-source-block={highlight ? "true" : undefined}>
          {renderChildren(node.children, ctx, key)}
        </blockquote>
      );
    }
    case "code": {
      const highlight = highlightClass(key, ctx);
      return (
        <pre
          key={key}
          className={["markdown-reader-code", highlight].filter(Boolean).join(" ")}
          data-source-block={highlight ? "true" : undefined}
        >
          <code className={node.lang ? `language-${node.lang}` : undefined}>{node.value}</code>
        </pre>
      );
    }
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
    case "html": {
      const highlight = highlightClass(key, ctx);
      return (
        <pre
          key={key}
          className={["markdown-reader-html-literal", highlight].filter(Boolean).join(" ")}
          data-testid="markdown-reader-html-literal"
          data-source-block={highlight ? "true" : undefined}
        >
          {node.value}
        </pre>
      );
    }
    case "definition":
      return null;
    case "yaml":
      return null;
    default:
      return unknownFallback(node, ctx, key);
  }
}

/**
 * Read-only semantic React document from exact Markdown via the canonical MDAST parser.
 * Does not use TipTap. Never executes raw HTML. Never writes source.
 */
export function MarkdownDocumentReader({
  markdown,
  className,
  sourceLineTarget = null,
}: MarkdownDocumentReaderProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const scrolledTargetKeyRef = useRef<string | null>(null);

  const bodyMarkdown = useMemo(
    () => stripLeadingYamlFrontmatter(markdown).markdown,
    [markdown],
  );
  const ast = useMemo(() => parseMarkdownAst(bodyMarkdown), [bodyMarkdown]);
  const definitions = useMemo(() => collectDefinitions(ast), [ast]);
  const highlightKeys = useMemo(
    () => resolveHighlightKeys(ast, markdown, sourceLineTarget),
    [ast, markdown, sourceLineTarget],
  );

  const showNoHighlightMessage =
    sourceLineTarget != null && highlightKeys != null && highlightKeys.size === 0;

  useEffect(() => {
    if (!sourceLineTarget || !highlightKeys || highlightKeys.size === 0) return;
    if (scrolledTargetKeyRef.current === sourceLineTarget.targetKey) return;
    const first = containerRef.current?.querySelector("[data-source-block='true']");
    if (first instanceof HTMLElement && typeof first.scrollIntoView === "function") {
      first.scrollIntoView({ block: "center" });
      scrolledTargetKeyRef.current = sourceLineTarget.targetKey;
    }
  }, [sourceLineTarget, highlightKeys, markdown]);

  const ctx: RenderContext = {
    bodyMarkdown,
    definitions,
    headingIds: createHeadingIdRegistry(),
    highlightKeys,
  };

  return (
    <div
      ref={containerRef}
      className={["markdown-document-reader", className].filter(Boolean).join(" ")}
      data-testid="markdown-document-reader"
    >
      {showNoHighlightMessage ? (
        <p
          className="markdown-reader-source-no-highlight"
          role="status"
          data-testid="markdown-reader-source-no-highlight"
        >
          Exact passage could not be highlighted.
        </p>
      ) : null}
      {ast.children.map((child, index) => renderNode(child, ctx, `root.${index}`))}
    </div>
  );
}
