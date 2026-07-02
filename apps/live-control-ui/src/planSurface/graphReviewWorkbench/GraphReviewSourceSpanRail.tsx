import type { GraphReviewSourceSpanDeltaIndex, GraphReviewSourceSpanDeltaPresentation } from "./graphReviewSourceSpanOverlayUtils";
import { statusLabelForSourceSpan } from "./graphReviewSourceSpanOverlayUtils";

interface GraphReviewSourceSpanRailProps {
  index: GraphReviewSourceSpanDeltaIndex;
  selectedSourceSpanId: string | null;
  onSelectSourceSpan: (sourceSpanId: string | null) => void;
}

function truncate(value: string | null | undefined, maxLength = 96): string {
  const text = value?.replace(/\s+/g, " ").trim();
  if (!text) return "No excerpt available.";
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

function rowSummary(presentation: GraphReviewSourceSpanDeltaPresentation): string {
  return presentation.primaryDelta?.summary ?? presentation.sourceSpanText ?? "No delta summary available.";
}

export function GraphReviewSourceSpanRail({
  index,
  selectedSourceSpanId,
  onSelectSourceSpan,
}: GraphReviewSourceSpanRailProps) {
  return (
    <aside className="graph-review-source-span-rail" aria-label="Source-span delta rail">
      <header>
        <div>
          <p className="plan-surface-kicker">Source-span delta rail</p>
          <h3>Paragraph overlays</h3>
        </div>
        {selectedSourceSpanId ? (
          <button type="button" className="graph-review-source-span-clear" onClick={() => onSelectSourceSpan(null)}>
            Clear source-span selection
          </button>
        ) : null}
      </header>
      <div className="graph-review-source-span-count-grid" aria-label="Source-span status counts">
        <span>Matched source spans: {index.countsByStatus.matched}</span>
        <span>Live-only source spans: {index.countsByStatus.live_only}</span>
        <span>Uncertain source spans: {index.countsByStatus.comparator_uncertain}</span>
        <span>Mixed source spans: {index.countsByStatus.mixed}</span>
        <span>Unclassified source spans: {index.countsByStatus.unclassified}</span>
      </div>
      <div className="graph-review-source-span-row-list">
        {index.orderedSpans.map((presentation) => (
          <button
            type="button"
            key={presentation.sourceSpanRefId}
            className="graph-review-source-span-row"
            data-selected={presentation.sourceSpanRefId === selectedSourceSpanId ? "true" : "false"}
            data-delta-status={presentation.status}
            onClick={() => onSelectSourceSpan(presentation.sourceSpanRefId)}
          >
            <span className="graph-review-source-span-status" data-delta-status={presentation.status}>
              {statusLabelForSourceSpan(presentation.status)}
            </span>
            <span className="graph-review-source-span-row-main">
              <strong>{presentation.sourceSpanRefId}</strong>
              {typeof presentation.sourceSpan?.ordinal === "number" ? <em>Ordinal {presentation.sourceSpan.ordinal}</em> : null}
              <span>{truncate(presentation.sourceSpanText)}</span>
              <small>{truncate(rowSummary(presentation), 120)}</small>
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
