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
  /** Exact graph scope — all four null/absent = legacy; all four set = scoped; otherwise invalid. */
  graphWorldId?: string | null;
  graphCampaignId?: string | null;
  graphScopeMode?: "campaign" | "world" | null;
  graphRevisionId?: string | null;
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

const GRAPH_SCOPE_QUERY_KEYS = ["world", "campaign", "scope", "revision"] as const;
type GraphScopeQueryKey = (typeof GRAPH_SCOPE_QUERY_KEYS)[number];

function normalizedString(value: unknown): string {
  return typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
}

/** Opaque scope IDs: trim ends only; preserve internal whitespace and content. */
function trimmedOpaqueString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
}

function normalizedScopeMode(value: unknown): "campaign" | "world" | null {
  const trimmed = trimmedOpaqueString(value);
  return trimmed === "campaign" || trimmed === "world" ? trimmed : null;
}

function isScopeFieldAbsent(value: unknown): boolean {
  return value === null || value === undefined || value === "";
}

export function graphScopePresence(
  attrs: Partial<
    Pick<
      RunbookReferenceAttrs,
      "graphWorldId" | "graphCampaignId" | "graphScopeMode" | "graphRevisionId"
    >
  >,
): "none" | "complete" | "partial" {
  const fields = [
    attrs.graphWorldId,
    attrs.graphCampaignId,
    attrs.graphScopeMode,
    attrs.graphRevisionId,
  ];
  const populated = fields.filter((value) => !isScopeFieldAbsent(value));
  if (populated.length === 0) return "none";
  if (
    populated.length === 4
    && !isScopeFieldAbsent(attrs.graphWorldId)
    && !isScopeFieldAbsent(attrs.graphCampaignId)
    && !isScopeFieldAbsent(attrs.graphScopeMode)
    && !isScopeFieldAbsent(attrs.graphRevisionId)
  ) {
    return "complete";
  }
  return "partial";
}

export function normalizeRunbookReferenceAttrs(
  input: Partial<RunbookReferenceAttrs>,
): RunbookReferenceAttrs {
  const kind = input.kind === "action" ? "action" : "ref";
  const refType = normalizedString(input.refType);
  const refId = normalizedString(input.refId);
  const label = normalizedString(input.label) || refId;

  return {
    kind,
    refType,
    refId,
    label,
    graphWorldId: trimmedOpaqueString(input.graphWorldId),
    graphCampaignId: trimmedOpaqueString(input.graphCampaignId),
    graphScopeMode: normalizedScopeMode(input.graphScopeMode),
    graphRevisionId: trimmedOpaqueString(input.graphRevisionId),
  };
}

function isValidRefId(refType: string, refId: string): boolean {
  if (refType === GRAPH_NODE_REF_TYPE) {
    return GRAPH_NODE_ID_PATTERN.test(refId);
  }
  return CORPUS_ID_PATTERN.test(refId);
}

function hasIllegalGraphScope(attrs: RunbookReferenceAttrs): boolean {
  const presence = graphScopePresence(attrs);
  if (presence === "none") return false;
  if (attrs.kind !== "ref" || attrs.refType !== GRAPH_NODE_REF_TYPE) return true;
  return presence === "partial";
}

export function isSupportedRunbookReference(attrs: RunbookReferenceAttrs): boolean {
  if (!TYPE_PATTERN.test(attrs.refType) || !isValidRefId(attrs.refType, attrs.refId)) {
    return false;
  }
  if (hasIllegalGraphScope(attrs)) return false;
  return attrs.kind === "ref"
    ? RUNBOOK_REF_TYPES.includes(attrs.refType as RunbookRefType)
    : RUNBOOK_ACTION_TYPES.includes(attrs.refType as RunbookActionType);
}

/**
 * Percent-encode scope component values. encodeURIComponent leaves `()` unescaped,
 * which truncates Markdown link destinations that terminate at `)`.
 */
function encodeGraphScopeComponent(value: string): string {
  return encodeURIComponent(value).replace(/[()]/g, (char) =>
    `%${char.charCodeAt(0).toString(16).toUpperCase()}`
  );
}

function buildGraphScopeQuery(attrs: RunbookReferenceAttrs): string {
  return [
    `world=${encodeGraphScopeComponent(attrs.graphWorldId ?? "")}`,
    `campaign=${encodeGraphScopeComponent(attrs.graphCampaignId ?? "")}`,
    `scope=${encodeGraphScopeComponent(attrs.graphScopeMode ?? "")}`,
    `revision=${encodeGraphScopeComponent(attrs.graphRevisionId ?? "")}`,
  ].join("&");
}

/** Reject malformed percent-encoding before URLSearchParams' single decode pass. */
function hasMalformedPercentEncoding(raw: string): boolean {
  for (let index = 0; index < raw.length; index += 1) {
    if (raw[index] !== "%") continue;
    const hex = raw.slice(index + 1, index + 3);
    if (!/^[0-9A-Fa-f]{2}$/.test(hex)) return true;
    index += 2;
  }
  return false;
}

export function runbookReferenceHref(attrs: RunbookReferenceAttrs): string | null {
  if (!isSupportedRunbookReference(attrs)) return null;
  const base = `#dmb-${attrs.kind}:${attrs.refType}:${attrs.refId}`;
  if (graphScopePresence(attrs) !== "complete") return base;
  return `${base}?${buildGraphScopeQuery(attrs)}`;
}

export function runbookReferenceClasses(attrs: RunbookReferenceAttrs): string {
  return attrs.kind === "action"
    ? `md-ref-chip md-ref-chip-action md-ref-chip-action-${attrs.refType}`
    : `md-ref-chip md-ref-chip-${attrs.refType}`;
}

export type ParsedGraphScopeQuery = Pick<
  RunbookReferenceAttrs,
  "graphWorldId" | "graphCampaignId" | "graphScopeMode" | "graphRevisionId"
>;

export function parseGraphScopeQuery(query: string): ParsedGraphScopeQuery | null {
  if (!query.startsWith("?")) return null;

  const raw = query.slice(1);
  if (hasMalformedPercentEncoding(raw)) return null;

  // URLSearchParams performs the single decode pass; do not decode again.
  const params = new URLSearchParams(raw);
  const seen = new Map<string, string>();

  for (const [key, value] of params.entries()) {
    if (!GRAPH_SCOPE_QUERY_KEYS.includes(key as GraphScopeQueryKey)) return null;
    if (seen.has(key)) return null;
    seen.set(key, value);
  }

  if (seen.size === 0) return null;

  const world = seen.get("world");
  const campaign = seen.get("campaign");
  const scope = seen.get("scope");
  const revision = seen.get("revision");

  if (!world || !campaign || !scope || !revision) return null;
  if (seen.size !== GRAPH_SCOPE_QUERY_KEYS.length) return null;

  const graphScopeMode = normalizedScopeMode(scope);
  if (!graphScopeMode) return null;

  return {
    graphWorldId: world,
    graphCampaignId: campaign,
    graphScopeMode,
    graphRevisionId: revision,
  };
}
