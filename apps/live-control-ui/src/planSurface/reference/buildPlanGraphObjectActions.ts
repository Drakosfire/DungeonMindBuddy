import type { GraphObjectActionViewModel, GraphObjectCardViewModel } from "../../graphObjectCard";
import { buildPlanIngestHref } from "../config/planSessionDescriptor";
import type { PlanSessionDescriptor } from "../types";
import type { PlanReferenceResolution } from "./graphAwareReferenceResolver";

export interface BuildPlanGraphObjectActionsInput {
  resolution: PlanReferenceResolution;
  sessionDescriptor?: PlanSessionDescriptor;
  /** Opens the Plan statblock tool when grounded. Omit when unavailable. */
  onOpenStatblock?: () => void;
  /** Opens a Plan roll-table surface when grounded. Omit when unavailable. */
  onOpenRollTable?: () => void;
}

function normalizeKind(value: string | null | undefined): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/_/g, "-");
}

function isStatblockKind(value: string | null | undefined): boolean {
  return normalizeKind(value) === "statblock";
}

function isRollTableKind(value: string | null | undefined): boolean {
  return normalizeKind(value) === "roll-table";
}

function graphObjectFromResolution(
  resolution: PlanReferenceResolution,
): GraphObjectCardViewModel | null {
  return resolution.graphObject ?? null;
}

export function hasPlanSourceOrEvidence(
  model: Pick<GraphObjectCardViewModel, "evidence" | "sourceDomains" | "details"> | null | undefined,
): boolean {
  if (!model) return false;
  const evidenceCount = model.details?.evidenceCount ?? model.evidence?.length ?? 0;
  if (evidenceCount > 0) return true;
  if ((model.sourceDomains?.length ?? 0) > 0) return true;
  if ((model.details?.sourceDomains?.length ?? 0) > 0) return true;
  if (model.details?.sourceAnchorText) return true;
  if (model.evidence?.some((item) => item.sourceArtifactId || item.sourcePath || item.sourceDomain)) {
    return true;
  }
  return false;
}

function resolutionIndicatesStatblock(resolution: PlanReferenceResolution): boolean {
  if (isStatblockKind(resolution.refType)) return true;
  if (resolution.fallback?.source === "statblock-index") return true;
  if (isStatblockKind(resolution.fallback?.ref.refType)) return true;

  const model = graphObjectFromResolution(resolution);
  if (!model) return false;
  if (isStatblockKind(model.kind)) return true;
  return (model.relationships ?? []).some((relationship) => isStatblockKind(relationship.targetKind));
}

function resolutionIndicatesRollTable(resolution: PlanReferenceResolution): boolean {
  if (isRollTableKind(resolution.refType)) return true;
  if (resolution.fallback?.source === "roll-table-index") return true;
  if (isRollTableKind(resolution.fallback?.ref.refType)) return true;

  const model = graphObjectFromResolution(resolution);
  if (!model) return false;
  if (isRollTableKind(model.kind)) return true;
  return (model.relationships ?? []).some((relationship) => isRollTableKind(relationship.targetKind));
}

function ingestHrefFor(sessionDescriptor?: PlanSessionDescriptor): string {
  return sessionDescriptor ? buildPlanIngestHref(sessionDescriptor) : "/ingest";
}

/**
 * Plan-safe actions for graph-backed (and fallback) object cards.
 *
 * Order: source/evidence → grounded tools → /ingest review.
 * Actions are omitted when behavior is not available — never fake-enabled.
 */
export function buildPlanGraphObjectActions({
  resolution,
  sessionDescriptor,
  onOpenStatblock,
  onOpenRollTable,
}: BuildPlanGraphObjectActionsInput): GraphObjectActionViewModel[] {
  const actions: GraphObjectActionViewModel[] = [];
  const ingestHref = ingestHrefFor(sessionDescriptor);
  const model = graphObjectFromResolution(resolution);

  if (resolution.kind === "graph-node" || resolution.kind === "corpus-index") {
    const sourceModel =
      model ??
      (resolution.kind === "corpus-index"
        ? {
            evidence: [],
            sourceDomains: [],
            details: {
              lines: resolution.fallback?.sourcePath
                ? [`Source path: ${resolution.fallback.sourcePath}`]
                : [],
              sourceAnchorText: null,
              evidenceCount: 0,
              sourceDomains: [],
            },
          }
        : null);

    const hasCorpusSourcePath = Boolean(resolution.fallback?.sourcePath);
    if (hasPlanSourceOrEvidence(sourceModel) || hasCorpusSourcePath) {
      actions.push({
        id: "open-source",
        label: "Inspect source/evidence",
        kind: "open-source",
        helpText: "Opens the card Details section for evidence and source context.",
      });
    }

    if (resolutionIndicatesStatblock(resolution) && onOpenStatblock) {
      actions.push({
        id: "open-statblock",
        label: "Open statblock tool",
        kind: "open-statblock",
        helpText: "Opens the Plan statblock tool. Does not load this object's specific statblock yet.",
        onClick: onOpenStatblock,
      });
    }

    if (resolutionIndicatesRollTable(resolution) && onOpenRollTable) {
      actions.push({
        id: "open-roll-table",
        label: "Open roll table tool",
        kind: "open-roll-table",
        helpText: "Opens the Plan roll-table tool. Does not load this object's specific table yet.",
        onClick: onOpenRollTable,
      });
    }
  }

  if (resolution.kind === "graph-node") {
    actions.push({
      id: "open-ingest",
      label: "Review memory in /ingest",
      kind: "open-ingest",
      href: ingestHref,
      helpText: "Open /ingest to review this object's memory.",
    });
  } else if (resolution.kind === "corpus-index") {
    actions.push({
      id: "open-ingest",
      label: "Review memory in /ingest",
      kind: "open-ingest",
      href: ingestHref,
      helpText: "Corpus fallback only — open /ingest to review or correct memory.",
    });
  } else if (resolution.kind === "unresolved" || resolution.kind === "error") {
    actions.push({
      id: "open-ingest",
      label: "Fix memory in /ingest",
      kind: "open-ingest",
      href: ingestHref,
      helpText: "Open /ingest to review aliases or identity.",
    });
  }

  return actions;
}
