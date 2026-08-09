export const RUNBOOK_REF_TYPES = [
  "npc",
  "location",
  "statblock",
  "roll-table",
  "citation",
  "graph-node",
] as const;
export const RUNBOOK_ACTION_TYPES = ["combat"] as const;

export type RunbookRefKind = "ref" | "action";
export type RunbookRefType = (typeof RUNBOOK_REF_TYPES)[number];
export type RunbookActionType = (typeof RUNBOOK_ACTION_TYPES)[number];

export interface RunbookReferenceAttrs {
  kind: RunbookRefKind;
  refType: string;
  refId: string;
  label: string;
}

/** Corpus and action chip types use hyphenated slugs without colons. */
const TYPE_PATTERN = /^[a-z][a-z0-9-]*$/;
const CORPUS_ID_PATTERN = /^[a-z0-9][a-z0-9_-]*$/;
/**
 * Graph-native durable node IDs (e.g. `threat:tripod-null-calf`).
 * Colons are part of the identity and must round-trip through Markdown.
 */
const GRAPH_NODE_ID_PATTERN = /^[a-z0-9][a-z0-9_.:-]*$/i;

export const GRAPH_NODE_REF_TYPE: RunbookRefType = "graph-node";

function normalizedString(value: unknown): string {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

/** Undo one CommonMark inline escape pass (`\*` → `*`, `\\` → `\`, …). */
function unescapeMarkdownInline(text: string): string {
  return text.replace(/\\([\\`*_{}[\]()#+.!|>~-])/g, "$1");
}

/**
 * Heal labels that accumulated runaway backslash escapes across save/load
 * (e.g. `[\*\*Meat Mind\*\*]` → export → `\\\*\\\*…` → re-import without unescape).
 * Also strips a single wrapping `**…**` / `__…__` emphasis pair for chip display.
 */
export function healRunbookReferenceLabel(label: string): string {
  let current = normalizedString(label);
  for (let pass = 0; pass < 48; pass += 1) {
    const next = unescapeMarkdownInline(current);
    if (next === current) break;
    current = next;
  }
  const wrapped =
    current.match(/^\*\*(.+)\*\*$/)?.[1]
    ?? current.match(/^__(.+)__$/)?.[1];
  if (wrapped) {
    current = normalizedString(wrapped);
  }
  return current;
}

export function normalizeRunbookReferenceAttrs(
  input: Partial<RunbookReferenceAttrs>,
): RunbookReferenceAttrs {
  const kind = input.kind === "action" ? "action" : "ref";
  const refType = normalizedString(input.refType);
  const refId = normalizedString(input.refId);
  const label = healRunbookReferenceLabel(normalizedString(input.label) || refId) || refId;

  return { kind, refType, refId, label };
}

function isValidRefId(refType: string, refId: string): boolean {
  if (refType === GRAPH_NODE_REF_TYPE) {
    return GRAPH_NODE_ID_PATTERN.test(refId);
  }
  return CORPUS_ID_PATTERN.test(refId);
}

export function isSupportedRunbookReference(attrs: RunbookReferenceAttrs): boolean {
  if (!TYPE_PATTERN.test(attrs.refType) || !isValidRefId(attrs.refType, attrs.refId)) {
    return false;
  }
  return attrs.kind === "ref"
    ? RUNBOOK_REF_TYPES.includes(attrs.refType as RunbookRefType)
    : RUNBOOK_ACTION_TYPES.includes(attrs.refType as RunbookActionType);
}

export function runbookReferenceHref(attrs: RunbookReferenceAttrs): string | null {
  if (!isSupportedRunbookReference(attrs)) return null;
  return `#dmb-${attrs.kind}:${attrs.refType}:${attrs.refId}`;
}

export function runbookReferenceClasses(attrs: RunbookReferenceAttrs): string {
  return attrs.kind === "action"
    ? `md-ref-chip md-ref-chip-action md-ref-chip-action-${attrs.refType}`
    : `md-ref-chip md-ref-chip-${attrs.refType}`;
}
