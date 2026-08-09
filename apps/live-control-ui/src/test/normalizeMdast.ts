/**
 * Test-only MDAST normalization (handoff §19).
 *
 * Raw parser ASTs carry source positions and parser metadata that are not
 * part of DungeonBuddy's admitted semantic model. This helper reduces a
 * parsed tree to its semantic shape so tests can assert
 *
 *   source → AST → TipTap → semantic Markdown → AST
 *
 * equivalence without byte-for-byte demands the contract intentionally does
 * not make (canonicalization is allowed; semantics must survive).
 *
 * Test-only on purpose: do not promote this into production architecture
 * unless production genuinely needs it.
 */
import type { Root, RootContent } from "mdast";

type NormalizedNode = {
  type: string;
  value?: string;
  url?: string;
  title?: string | null;
  alt?: string | null;
  identifier?: string;
  depth?: number;
  ordered?: boolean | null;
  start?: number | null;
  checked?: boolean | null;
  align?: Array<string | null>;
  children?: NormalizedNode[];
};

const SEMANTIC_KEYS = [
  "value",
  "url",
  "title",
  "alt",
  "identifier",
  "depth",
  "ordered",
  "start",
  "checked",
  "align",
] as const;

function normalizeNode(node: Root | RootContent): NormalizedNode {
  const normalized: NormalizedNode = { type: node.type };
  const record = node as unknown as Record<string, unknown>;
  for (const key of SEMANTIC_KEYS) {
    if (key in record && record[key] !== undefined) {
      (normalized as Record<string, unknown>)[key] = record[key];
    }
  }
  if ("children" in node && Array.isArray(node.children)) {
    normalized.children = (node.children as RootContent[]).map(normalizeNode);
  }
  return normalized;
}

/** Normalize a parsed MDAST tree to DungeonBuddy's admitted semantic shape. */
export function normalizeMdast(root: Root): NormalizedNode {
  return normalizeNode(root);
}
