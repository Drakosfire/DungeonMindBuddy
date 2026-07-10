// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
// Retained until PR007/PR008 removes preview/latest-ingest selectors from surface APIs.
import type { ReactNode } from "react";

import type { GraphReviewPrimaryLaneView, GraphReviewReferenceLaneView } from "./graphReviewReferenceLaneUtils";

export type GraphReviewTwoLaneLayoutMode = "single" | "split";

interface GraphReviewTwoLaneShellProps {
  primaryLane: GraphReviewPrimaryLaneView | null;
  referenceLane: GraphReviewReferenceLaneView;
  layoutMode: GraphReviewTwoLaneLayoutMode;
  onLayoutModeChange: (mode: GraphReviewTwoLaneLayoutMode) => void;
  primary: ReactNode;
  reference: ReactNode;
}

export function GraphReviewTwoLaneShell({
  primaryLane,
  referenceLane,
  layoutMode,
  onLayoutModeChange,
  primary,
  reference,
}: GraphReviewTwoLaneShellProps) {
  return (
    <div className="graph-review-two-lane-shell">
      <header className="graph-review-two-lane-header" aria-label="Lane comparison header">
        <div className="graph-review-two-lane-header-card">
          <p className="plan-surface-kicker">Primary live lane</p>
          <strong>{primaryLane?.label ?? "No live lane selected"}</strong>
          <span>{primaryLane ? primaryLane.manifestPath : "Select a run to populate the primary live lane."}</span>
        </div>
        <div className="graph-review-two-lane-header-card">
          <p className="plan-surface-kicker">Reference lane</p>
          <strong>{referenceLane.label}</strong>
          <span>Structured reference context · {referenceLane.sourceKind.replace(/_/g, " ")}</span>
        </div>
        <div className="graph-review-two-lane-mode-toggle" aria-label="Layout mode">
          <span>Layout</span>
          {(["single", "split"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              aria-pressed={layoutMode === mode}
              onClick={() => onLayoutModeChange(mode)}
            >
              {mode}
            </button>
          ))}
        </div>
      </header>
      <div className="graph-review-two-lane-body" data-layout-mode={layoutMode}>
        <div className="graph-review-two-lane-primary">{primary}</div>
        <aside className="graph-review-two-lane-reference" aria-label="Reference lane">
          {reference}
        </aside>
      </div>
    </div>
  );
}
