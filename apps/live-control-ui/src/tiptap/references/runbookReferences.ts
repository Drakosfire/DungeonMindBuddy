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

/** Validity boundary for `dmb-node:` link targets and `graph-node` typed refs. */
export function isValidGraphNodeId(nodeId: string): boolean {
  return GRAPH_NODE_ID_PATTERN.test(nodeId);
}

function normalizedString(value: unknown): string {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

/** Undo one CommonMark inline escape pass (`\*` → `*`, `\\` → `\`, …). */
function unescapeMarkdownInline(text: string): string {
  return text.replace(/\\([\\`*_{}[\]()#+.!|>~-])/g, "$1");
}

/**
 * Normalize label text that is already semantic (MDAST-decoded or TipTap attr
 * text). Never re-interprets the string as Markdown source.
 */
export function normalizeSemanticReferenceLabel(label: string): string {
  return normalizedString(label);
}

/**
 * Legacy repair for labels persisted as escaped Markdown source (runaway
 * backslash doubling across older save/load cycles). Strips one wrapping
 * emphasis pair after unescaping because those dirty attrs encoded emphasis
 * delimiters rather than literal asterisks/underscores.
 *
 * Do **not** call this on fresh parser-derived text: MDAST has already decoded
 * `\*\*` into literal `**`, and the serializer can preserve those characters
 * by re-escaping on export.
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

export type NormalizeRunbookReferenceOptions = {
  /**
   * `semantic` (default): treat `label` as already-decoded chip text.
   * `legacy`: run {@link healRunbookReferenceLabel} for dirty persisted attrs.
   */
  labelSource?: "semantic" | "legacy";
};

export function normalizeRunbookReferenceAttrs(
  input: Partial<RunbookReferenceAttrs>,
  options: NormalizeRunbookReferenceOptions = {},
): RunbookReferenceAttrs {
  const kind = input.kind === "action" ? "action" : "ref";
  const refType = normalizedString(input.refType);
  const refId = normalizedString(input.refId);
  const rawLabel = normalizeSemanticReferenceLabel(input.label ?? "") || refId;
  const labelSource = options.labelSource ?? "semantic";
  const label = (
    labelSource === "legacy"
      ? healRunbookReferenceLabel(rawLabel)
      : rawLabel
  ) || refId;

  return { kind, refType, refId, label };
}

/**
 * True when a persisted label still looks like escaped Markdown source
 * (legacy save/load runaway) rather than semantic chip text.
 */
export function looksLikeEscapedMarkdownLabel(label: string): boolean {
  return /\\[\\`*_{}[\]()#+.!|>~-]/.test(label);
}

/**
 * Heal a persisted opaque-reference label exactly once when it still carries
 * Markdown escapes. Already-semantic labels (including literal `**` / `__`)
 * pass through unchanged.
 */
export function hydratePersistedReferenceLabel(label: string): string {
  const semantic = normalizeSemanticReferenceLabel(label);
  if (!semantic || !looksLikeEscapedMarkdownLabel(semantic)) {
    return semantic;
  }
  return healRunbookReferenceLabel(semantic);
}

/**
 * Hydration boundary for persisted TipTap `runbookReference` attrs: heal
 * escaped legacy labels once, otherwise treat as semantic in-memory text.
 */
export function hydratePersistedRunbookReferenceAttrs(
  input: Partial<RunbookReferenceAttrs>,
): RunbookReferenceAttrs {
  const rawLabel = normalizeSemanticReferenceLabel(input.label ?? "");
  return normalizeRunbookReferenceAttrs(
    input,
    {
      labelSource: looksLikeEscapedMarkdownLabel(rawLabel) ? "legacy" : "semantic",
    },
  );
}

type TiptapJsonNode = {
  type?: string;
  attrs?: Record<string, unknown>;
  content?: TiptapJsonNode[];
  text?: string;
  marks?: unknown[];
  [key: string]: unknown;
};

function migratePersistedReferenceNode(node: TiptapJsonNode): TiptapJsonNode {
  const next: TiptapJsonNode = { ...node };
  if (Array.isArray(node.content)) {
    next.content = node.content.map(migratePersistedReferenceNode);
  }

  if (node.type === "runbookReference") {
    const hydrated = hydratePersistedRunbookReferenceAttrs(
      (node.attrs ?? {}) as Partial<RunbookReferenceAttrs>,
    );
    next.attrs = { ...hydrated };
    return next;
  }

  if (node.type === "graphNodeReference" && node.attrs) {
    const nodeId = typeof node.attrs.nodeId === "string" ? node.attrs.nodeId : "";
    const rawLabel = typeof node.attrs.label === "string" ? node.attrs.label : "";
    const label = hydratePersistedReferenceLabel(rawLabel) || nodeId;
    next.attrs = { ...node.attrs, nodeId, label };
    return next;
  }

  return next;
}

/**
 * Migrate persisted TipTap JSON at the load/hydration boundary so in-memory
 * reference labels are semantic. Idempotent for already-clean docs and for
 * fresh semantic labels that intentionally contain literal `**` / `__`.
 */
export function migratePersistedTiptapReferenceLabels<T>(doc: T): T {
  if (!doc || typeof doc !== "object") {
    return doc;
  }
  return migratePersistedReferenceNode(doc as TiptapJsonNode) as T;
}

function isValidRefId(refType: string, refId: string): boolean {
  if (refType === GRAPH_NODE_REF_TYPE) {
    return isValidGraphNodeId(refId);
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
