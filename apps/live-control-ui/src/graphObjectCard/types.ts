export type GraphObjectCardMode = "plan" | "review";

export type GraphObjectActionKind =
  | "open-source"
  | "open-ingest"
  | "open-statblock"
  | "open-roll-table"
  | "add-to-combat"
  | "custom";

export interface GraphObjectRelationshipViewModel {
  id: string;
  label: string;
  predicate?: string | null;
  direction?: "incoming" | "outgoing" | "related" | null;
  summary?: string | null;
  targetId?: string | null;
  targetKind?: string | null;
  evidenceRefIds?: string[];
  sourceDomains?: string[];
  anchoredToFocusSession?: boolean;
  sessionIds?: string[];
  /** Effective campaign tenancy for this relationship (null = world-universal). */
  campaignScope?: string | null;
  sourceExcerpt?: string | null;
  sourceExcerptIsFullParagraph?: boolean;
  sourceExcerptHighlightSpans?: Array<{ start: number; end: number }>;
}

export interface GraphObjectEvidenceViewModel {
  id: string;
  label?: string | null;
  sourceArtifactId?: string | null;
  sourceSpanRefId?: string | null;
  sourceDomain?: string | null;
  sourcePath?: string | null;
  excerpt?: string | null;
  canOpenSource?: boolean;
  /** Hint only; server revalidates highlight eligibility on navigation. */
  canHighlightSpan?: boolean;
}

export interface GraphObjectActionViewModel {
  id: string;
  label: string;
  kind: GraphObjectActionKind;
  disabled?: boolean;
  helpText?: string;
  href?: string;
  onClick?: () => void;
}

export interface GraphObjectDetailsViewModel {
  visibilityLabel?: string | null;
  sourceDomains?: string[];
  evidenceCount?: number;
  sourceAnchorText?: string | null;
  nodeId?: string | null;
  /** Free-form plan-safe detail lines; review-only fields stay out of this model. */
  lines?: string[];
}

export interface GraphObjectCardViewModel {
  id: string;
  label: string;
  kind?: string;
  role?: string | null;
  typeBadgeLabel: string;
  secondaryRoleLabel?: string | null;
  aliases?: string[];
  summary?: string | null;
  gameSummary?: string | null;
  whyItMattersNow?: string | null;
  /** Effective campaign tenancy for the selected object (null = world-universal). */
  campaignScope?: string | null;
  /** Compact display label such as `C1` when campaignScope is set. */
  campaignLabel?: string | null;
  relationships?: GraphObjectRelationshipViewModel[];
  evidence?: GraphObjectEvidenceViewModel[];
  sourceDomains?: string[];
  visibilityLabel?: string | null;
  freshnessLabel?: string | null;
  details?: GraphObjectDetailsViewModel | null;
  actions?: GraphObjectActionViewModel[];
}
