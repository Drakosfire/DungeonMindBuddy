import type { GraphReviewReferenceLaneView } from "./graphReviewReferenceLaneUtils";

interface GraphReviewReferenceLanePanelProps { referenceLane: GraphReviewReferenceLaneView; }

function titleForKind(kind: GraphReviewReferenceLaneView["kind"]): string {
  if (kind === "gold_reference") return "Gold fixture reference";
  if (kind === "manual_variant_reference") return "Manual variant reference";
  return "Empty reference";
}

export function GraphReviewReferenceLanePanel({ referenceLane }: GraphReviewReferenceLanePanelProps) {
  return (
    <section className="graph-review-reference-lane-panel" aria-label="Reference lane summary">
      <header>
        <p className="plan-surface-kicker">Reference lane</p>
        <h3>{titleForKind(referenceLane.kind)}</h3>
        <p>{referenceLane.label}</p>
      </header>
      <div className="graph-review-reference-lane-card">
        <p>This side is structured reference context, not projected source text.</p>
        <dl className="graph-review-lane-meta">
          <div><dt>Kind</dt><dd>{referenceLane.kind}</dd></div>
          <div><dt>Source kind</dt><dd>{referenceLane.sourceKind}</dd></div>
          <div><dt>Status</dt><dd>{referenceLane.status}</dd></div>
        </dl>
      </div>
      {referenceLane.kind === "empty_reference" ? (
        <p className="graph-review-reference-lane-warning">No reference lane selected yet. Select a gold session or manual review variant to populate reference context.</p>
      ) : null}
      {referenceLane.warnings.map((warning) => (
        <p key={warning} className="graph-review-reference-lane-warning" role="status">{warning}</p>
      ))}
      {referenceLane.summaryItems.length ? (
        <dl className="graph-review-reference-lane-summary">
          {referenceLane.summaryItems.map((item) => (
            <div key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      <p className="graph-review-reference-lane-note">{referenceLane.note}</p>
      <p className="graph-review-reference-lane-note">Gold/live deltas remain the correctness model. Label-based navigation remains on the primary live lane.</p>
    </section>
  );
}
