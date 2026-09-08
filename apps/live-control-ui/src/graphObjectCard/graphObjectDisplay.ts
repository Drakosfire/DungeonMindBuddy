import type { GraphProjectionNodeView } from "../api/types";
import type { GraphObjectRelationshipViewModel } from "./types";

const PLACEHOLDER_NODE_SUMMARIES = new Set([
  "deterministic party context anchor",
]);

/** Default related-object list cap for Plan/default GraphObjectCard rows. */
export const MAX_DEFAULT_RELATIONSHIP_ROWS = 8;

function titleCaseGraphToken(value: string): string {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

export function formatGraphObjectType(
  kind?: string | null,
  role?: string | null,
): string {
  const values = [kind, role]
    .map((value) => value?.trim())
    .filter((value): value is string => Boolean(value));
  const uniqueValues = [...new Set(values)];
  return uniqueValues.join(" / ") || "Graph object";
}

export function graphObjectTypeBadgeLabel(
  kind?: string | null,
  role?: string | null,
): string {
  const primary = kind?.trim() || role?.trim();
  return primary ? titleCaseGraphToken(primary) : "Object";
}

export function graphObjectSecondaryRoleLabel(
  kind?: string | null,
  role?: string | null,
): string | null {
  const normalizedKind = kind?.trim().toLowerCase();
  const normalizedRole = role?.trim().toLowerCase();
  if (!normalizedRole || normalizedRole === normalizedKind) return null;
  return titleCaseGraphToken(role!.trim());
}

export function isPlaceholderNodeSummary(summary: string | null | undefined): boolean {
  const normalized = summary?.trim().toLowerCase();
  if (!normalized) return false;
  return PLACEHOLDER_NODE_SUMMARIES.has(normalized);
}

export function displayAliasesForNode(node: Pick<GraphProjectionNodeView, "label" | "aliases">): string[] {
  const label = node.label.trim().toLowerCase();
  return node.aliases.filter((alias) => alias.trim() && alias.trim().toLowerCase() !== label);
}

export function primaryGameSummaryForNode(
  node: Pick<GraphProjectionNodeView, "summary">,
): string | null {
  const summary = node.summary?.trim();
  if (summary && !isPlaceholderNodeSummary(summary)) return summary;
  return null;
}

const VISIBILITY_FRIENDLY_COPY: Record<string, string> = {
  gm_private: "GM private",
  gm: "GM private",
  table_known: "Table known",
  table: "Table",
  player_visible: "Player visible",
  player: "Player",
  character_specific: "Character-specific",
  character: "Character",
  hidden_until_revealed: "Hidden until revealed",
};

export function friendlyVisibilityCopy(visibility: string): string {
  const key = visibility.trim().toLowerCase();
  return VISIBILITY_FRIENDLY_COPY[key] ?? visibility;
}

/** Turn graph predicates like `located_in` into GM-readable `located in`. */
export function humanizeRelationshipPredicate(predicate: string | null | undefined): string | null {
  const trimmed = predicate?.trim();
  if (!trimmed) return null;
  return trimmed.replace(/_/g, " ").replace(/\s+/g, " ").trim();
}

/** Stative predicates read as “X is associated with Y”, not “Y · associated with”. */
const STATIVE_PREDICATE_HEAD =
  /^(associated|located|allied|related|connected|affiliated|bound|based|stationed|known)\b/i;

/**
 * Subject–predicate–object clause for the selected graph object.
 * `Orik` + `associated_with` + `Brin` → `Orik is associated with Brin`.
 */
export function relationshipSentence(
  subjectLabel: string,
  predicate: string | null | undefined,
  objectLabel: string,
): string {
  const subject = subjectLabel.trim();
  const object = objectLabel.trim();
  const human = humanizeRelationshipPredicate(predicate);
  if (!subject) {
    return human ? (object ? `${human} ${object}` : human) : object;
  }
  if (!human) {
    return object ? `${subject} · ${object}` : subject;
  }
  const verbPhrase = STATIVE_PREDICATE_HEAD.test(human) ? `is ${human}` : human;
  return object ? `${subject} ${verbPhrase} ${object}` : `${subject} ${verbPhrase}`;
}

const NON_PLANNING_EVIDENCE_ROLES = new Set([
  "support",
  "mention",
  "focus",
  "primary",
  "secondary",
  "context",
  "anchor",
  "evidence",
  "related",
  "background",
]);

/** Drop evidence-role tokens that leaked into Why-now slots (`support`, `mention`). */
export function planningGlanceWhyNow(text: string | null | undefined): string | null {
  const trimmed = text?.trim();
  if (!trimmed) return null;
  const normalized = trimmed.toLowerCase().replace(/_/g, " ");
  if (NON_PLANNING_EVIDENCE_ROLES.has(normalized)) return null;
  return trimmed;
}

/** Compact campaign stamp from ids like `longmont-c1` → `C1`. */
export function formatCampaignScopeCompact(
  campaignScope: string | null | undefined,
): string | null {
  const trimmed = campaignScope?.trim();
  if (!trimmed) return null;
  const longmont = trimmed.match(/^longmont-c(\d+)$/i);
  if (longmont) return `C${longmont[1]}`;
  const bare = trimmed.match(/^c(\d+)$/i);
  if (bare) return `C${bare[1]}`;
  return trimmed;
}

/** Compact session stamp from ids like `session-2` → `S2`. */
export function relationshipSessionStamp(
  sessionIds: string[] | null | undefined,
  campaignScope?: string | null,
): string | null {
  let session: string | null = null;
  if (sessionIds?.length) {
    const numbered = sessionIds
      .map((sessionId) => {
        const match = sessionId.trim().match(/(\d+)\s*$/);
        return match ? Number(match[1]) : null;
      })
      .filter((value): value is number => value != null && Number.isFinite(value));
    if (numbered.length) {
      session = `S${Math.min(...numbered)}`;
    } else {
      const first = sessionIds[0]?.trim();
      session = first || null;
    }
  }
  const campaign = formatCampaignScopeCompact(campaignScope);
  if (campaign && session) return `${campaign} · ${session}`;
  return session ?? campaign;
}

function primarySessionSortKey(sessionIds: string[] | null | undefined): number {
  if (!sessionIds?.length) return Number.POSITIVE_INFINITY;
  const numbered = sessionIds
    .map((sessionId) => {
      const match = sessionId.trim().match(/(\d+)\s*$/);
      return match ? Number(match[1]) : null;
    })
    .filter((value): value is number => value != null && Number.isFinite(value));
  if (!numbered.length) return Number.POSITIVE_INFINITY;
  return Math.min(...numbered);
}

/**
 * Chronological related rows for Plan card: oldest session first, keep distinct
 * edges (same target with different predicates stays visible), then cap.
 */
export function selectDefaultRelationshipRows(
  relationships: GraphObjectRelationshipViewModel[],
  maxRows: number = MAX_DEFAULT_RELATIONSHIP_ROWS,
): { rows: GraphObjectRelationshipViewModel[]; omittedCount: number } {
  const sorted = [...relationships].sort((left, right) => {
    const sessionDelta =
      primarySessionSortKey(left.sessionIds) - primarySessionSortKey(right.sessionIds);
    if (sessionDelta !== 0) return sessionDelta;
    const labelDelta = left.label.localeCompare(right.label);
    if (labelDelta !== 0) return labelDelta;
    return left.id.localeCompare(right.id);
  });
  const rows = sorted.slice(0, maxRows);
  return { rows, omittedCount: Math.max(0, sorted.length - rows.length) };
}

/** Aria / button label: `C1 · S2 · Subject is associated with Object` (no foreign summary). */
export function relationshipRowPrimaryCopy(
  relationship: GraphObjectRelationshipViewModel,
  subjectLabel: string,
): string {
  const sentence = relationshipSentence(subjectLabel, relationship.predicate, relationship.label);
  const session = relationshipSessionStamp(relationship.sessionIds, relationship.campaignScope);
  return session ? `${session} · ${sentence}` : sentence;
}
