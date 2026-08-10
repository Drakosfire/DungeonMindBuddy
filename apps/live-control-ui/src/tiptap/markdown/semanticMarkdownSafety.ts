export interface SemanticMarkdownSerializationDiagnostic {
  level: "warning";
  message: string;
  nodeType?: string;
}

type JsonNode = {
  type?: unknown;
  attrs?: Record<string, unknown> | null;
  content?: unknown;
  marks?: unknown;
};

type JsonMark = {
  type?: unknown;
  attrs?: Record<string, unknown> | null;
};

const INLINE_NODE_TYPES = new Set(["text", "runbookReference", "graphNodeReference"]);
const CALLOUT_CHILD_TYPES = new Set([
  "paragraph",
  "heading",
  "horizontalRule",
  "bulletList",
  "orderedList",
  "table",
]);
const LIST_ITEM_CHILD_TYPES = new Set([
  "paragraph",
  "bulletList",
  "orderedList",
  "callout",
  "decisionConsequence",
  // Tables stay out: markdownAdmission.visitTable blocks list-item tables.
]);
const DECISION_CONSEQUENCE_CHILD_TYPES = new Set(["decisionPane", "consequencePane"]);
const PANE_CHILD_TYPES = new Set([
  "paragraph",
  "heading",
  "horizontalRule",
  "bulletList",
  "orderedList",
  "table",
  // Matches visitPaneBlockquote admitting supported callouts inside panes.
  "callout",
]);
const SUPPORTED_MARK_TYPES = new Set(["bold", "italic", "strike", "code"]);

function asNode(value: unknown): JsonNode | null {
  return value !== null && typeof value === "object" ? (value as JsonNode) : null;
}

function childNodes(node: JsonNode): JsonNode[] {
  if (!Array.isArray(node.content)) return [];
  return node.content.map(asNode).filter((child): child is JsonNode => child !== null);
}

function marks(node: JsonNode): JsonMark[] {
  if (!Array.isArray(node.marks)) return [];
  return node.marks.map(asNode).filter((mark): mark is JsonMark => mark !== null);
}

function warning(message: string, nodeType?: string): SemanticMarkdownSerializationDiagnostic {
  return { level: "warning", message, ...(nodeType ? { nodeType } : {}) };
}

function hasNonDefaultTableSpan(attrs: Record<string, unknown> | null | undefined): boolean {
  if (!attrs) return false;
  const colspan = attrs.colspan;
  const rowspan = attrs.rowspan;
  const colwidth = attrs.colwidth;
  return (
    (colspan !== undefined && colspan !== null && colspan !== 1)
    || (rowspan !== undefined && rowspan !== null && rowspan !== 1)
    || (colwidth !== undefined && colwidth !== null)
  );
}

/**
 * Validate the TipTap document against the exact semantic Markdown grammar
 * implemented by calloutMarkdown.ts + markdownToTiptap.ts.
 */
export function semanticMarkdownSerializationDiagnostics(
  document: unknown,
): SemanticMarkdownSerializationDiagnostic[] {
  const diagnostics: SemanticMarkdownSerializationDiagnostic[] = [];
  const root = asNode(document);
  if (!root) return [warning("Editor document is not valid TipTap JSON.")];

  const visit = (node: JsonNode, parentType: string | null): void => {
    const type = typeof node.type === "string" ? node.type : "unknown";
    const children = childNodes(node);

    switch (type) {
      case "doc":
        for (const child of children) visit(child, type);
        return;
      case "paragraph":
      case "heading":
        for (const child of children) {
          const childType = typeof child.type === "string" ? child.type : "unknown";
          if (!INLINE_NODE_TYPES.has(childType)) {
            diagnostics.push(warning(
              `${type} contains ${childType}, which semantic Markdown cannot round-trip safely.`,
              childType,
            ));
          }
          visit(child, type);
        }
        return;
      case "text":
        for (const mark of marks(node)) {
          const markType = typeof mark.type === "string" ? mark.type : "unknown";
          if (!SUPPORTED_MARK_TYPES.has(markType)) {
            diagnostics.push(warning(
              `Text mark ${markType} is not supported by the semantic Markdown editor.`,
              type,
            ));
          }
        }
        return;
      case "runbookReference":
      case "graphNodeReference":
      case "horizontalRule":
        return;
      case "bulletList":
      case "orderedList":
        for (const child of children) {
          if (child.type !== "listItem") {
            diagnostics.push(warning(`${type} contains a non-listItem child.`, String(child.type)));
          }
          visit(child, type);
        }
        return;
      case "listItem": {
        for (const child of children) {
          const childType = typeof child.type === "string" ? child.type : "unknown";
          if (!LIST_ITEM_CHILD_TYPES.has(childType)) {
            diagnostics.push(warning(
              `List item child ${childType} is not supported by semantic Markdown.`,
              childType,
            ));
          }
        }
        if (children.length === 0) {
          diagnostics.push(warning("List items must contain at least one supported block.", type));
        }
        for (const child of children) visit(child, type);
        return;
      }
      case "callout":
        if (parentType === "callout") {
          diagnostics.push(warning("Nested callouts are not supported by the current Markdown importer.", type));
        }
        for (const child of children) {
          const childType = typeof child.type === "string" ? child.type : "unknown";
          if (!CALLOUT_CHILD_TYPES.has(childType)) {
            diagnostics.push(warning(
              `Callout child ${childType} is not supported by semantic Markdown.`,
              childType,
            ));
          }
          visit(child, type);
        }
        return;
      case "decisionConsequence":
        if (parentType === "callout" || parentType === "decisionConsequence") {
          diagnostics.push(warning("Nested Decision/Consequence blocks are not supported.", type));
        }
        if (children.length !== 2) {
          diagnostics.push(warning("Decision/Consequence blocks must contain exactly two panes.", type));
        }
        if (children[0]?.type !== "decisionPane" || children[1]?.type !== "consequencePane") {
          diagnostics.push(warning("Decision/Consequence panes must be ordered Decision then Consequence.", type));
        }
        for (const child of children) {
          const childType = typeof child.type === "string" ? child.type : "unknown";
          if (!DECISION_CONSEQUENCE_CHILD_TYPES.has(childType)) {
            diagnostics.push(warning(
              `Decision/Consequence child ${childType} is not supported by semantic Markdown.`,
              childType,
            ));
          }
          visit(child, type);
        }
        return;
      case "decisionPane":
      case "consequencePane":
        if (parentType !== "decisionConsequence") {
          diagnostics.push(warning(`${type} must live inside a Decision/Consequence block.`, type));
        }
        for (const child of children) {
          const childType = typeof child.type === "string" ? child.type : "unknown";
          if (!PANE_CHILD_TYPES.has(childType)) {
            diagnostics.push(warning(
              `${type} child ${childType} is not supported by semantic Markdown.`,
              childType,
            ));
          }
          visit(child, type);
        }
        return;
      case "table": {
        const widths = children.map((row) => childNodes(row).length);
        if (widths.length > 1 && widths.some((width) => width !== widths[0])) {
          diagnostics.push(warning("Table rows must have equal widths for safe Markdown serialization.", type));
        }
        for (const child of children) {
          if (child.type !== "tableRow") {
            diagnostics.push(warning("Table contains a non-tableRow child.", String(child.type)));
          }
          visit(child, type);
        }
        return;
      }
      case "tableRow":
        for (const child of children) {
          if (child.type !== "tableHeader" && child.type !== "tableCell") {
            diagnostics.push(warning("Table row contains an unsupported child.", String(child.type)));
          }
          visit(child, type);
        }
        return;
      case "tableHeader":
      case "tableCell":
        if (hasNonDefaultTableSpan(node.attrs)) {
          diagnostics.push(warning("Merged or width-constrained table cells are not represented in GFM Markdown.", type));
        }
        if (children.length !== 1 || children[0]?.type !== "paragraph") {
          diagnostics.push(warning("Table cells must contain exactly one paragraph for safe GFM serialization.", type));
        }
        for (const child of children) visit(child, type);
        return;
      case "hardBreak":
        diagnostics.push(warning("Hard breaks are not represented losslessly by the current Markdown serializer.", type));
        return;
      default:
        diagnostics.push(warning(
          `TipTap node ${type} is not supported by semantic Markdown and would be flattened or replaced.`,
          type,
        ));
        return;
    }
  };

  visit(root, null);
  return diagnostics;
}
