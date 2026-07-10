import type { GraphProjectionNodeView } from "../api/types";

const PLACEHOLDER_NODE_SUMMARIES = new Set([
  "deterministic party context anchor",
]);

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
