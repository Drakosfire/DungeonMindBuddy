import type { GraphPreviewEvidenceRef } from "../../api/types";
import { buildHighlightSegments, lineRangeLabel, spanRefLabel } from "./graphPreviewUtils";

interface SourceExcerptPanelProps {
  evidence: GraphPreviewEvidenceRef;
}

export function SourceExcerptPanel({ evidence }: SourceExcerptPanelProps) {
  const paragraph = evidence.paragraph_text ?? "";
  const segments = buildHighlightSegments(paragraph, evidence.anchor_quote_matches);
  const hasHighlights = evidence.anchor_quote_matches.length > 0;
  const sourceLabel = spanRefLabel(evidence.source_span_ref_id) ?? evidence.label ?? "Evidence";

  return (
    <section className="graph-preview-source" aria-label="Source excerpt">
      <header className="graph-preview-source-header">
        <div>
          <p className="plan-surface-kicker">Source paragraph</p>
          <h4>{sourceLabel}</h4>
        </div>
        <span className="graph-preview-source-meta">
          {lineRangeLabel(evidence.line_start, evidence.line_end)}
        </span>
      </header>
      {paragraph ? (
        <p
          className={
            hasHighlights ? "graph-preview-excerpt graph-preview-excerpt-marked" : "graph-preview-excerpt"
          }
        >
          {segments.map((segment, index) =>
            segment.highlighted ? (
              <mark key={index} className="graph-preview-highlight">{segment.text}</mark>
            ) : (
              <span key={index}>{segment.text}</span>
            ),
          )}
        </p>
      ) : (
        <p className="plan-projection-empty">No paragraph text resolved for this evidence ref.</p>
      )}
    </section>
  );
}
