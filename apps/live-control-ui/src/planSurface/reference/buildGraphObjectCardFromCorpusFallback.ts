import type { GraphObjectCardViewModel } from "../../graphObjectCard";
import type { GraphReferenceResolution } from "../../graphReference/types";
import {
  buildSelectedObjectCardModel,
  selectedObjectKindLabel,
} from "../selectedObject/selectedObjectCardModel";
import type { ReferenceResolution } from "./referenceResolver";

/**
 * Adapts a corpus-index fallback into the forward GraphObjectCard shape.
 * Corpus data is visibly fallback — not authoritative graph memory.
 */
export function buildGraphObjectCardFromCorpusFallback(
  resolution: GraphReferenceResolution,
): GraphObjectCardViewModel | null {
  const fallback = resolution.kind === "resolved_corpus_fallback" ? resolution.fallback : null;
  if (!fallback || fallback.status !== "resolved") {
    return null;
  }

  const referenceResolution: ReferenceResolution = {
    status: fallback.status,
    ref: fallback.ref,
    message: fallback.message,
    source: fallback.source,
    item: fallback.item,
    sourcePath: fallback.sourcePath,
  };

  const selected = buildSelectedObjectCardModel(referenceResolution);
  const metadata = selected.metadata;
  const detailLines = [
    ...selected.primaryFields.map((field) => `${field.label}: ${field.value}`),
    ...selected.secondaryFields.map((field) => `${field.label}: ${field.value}`),
  ];

  if (selected.sourcePath) {
    detailLines.push(`Source path: ${selected.sourcePath}`);
  }

  return {
    id: metadata ? `${metadata.refType}:${metadata.refId}` : resolution.locator,
    label: selected.title,
    kind: selected.kind === "unknown" ? resolution.reference?.refType ?? undefined : selected.kind,
    typeBadgeLabel: selected.subtitle ?? selectedObjectKindLabel(selected.kind),
    secondaryRoleLabel: null,
    summary: selected.summary,
    gameSummary: selected.summary,
    whyItMattersNow: null,
    relationships: [],
    evidence: [],
    sourceDomains: [],
    visibilityLabel: null,
    freshnessLabel: "Corpus index fallback",
    details: {
      sourceDomains: [],
      evidenceCount: 0,
      lines: detailLines,
    },
    actions: [],
  };
}
