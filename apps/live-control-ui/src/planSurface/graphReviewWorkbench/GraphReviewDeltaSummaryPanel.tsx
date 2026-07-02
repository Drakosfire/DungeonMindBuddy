import type { GraphReviewDeltaIndex } from "./graphReviewDeltaTypes";

interface GraphReviewDeltaSummaryPanelProps {
  deltaIndex: GraphReviewDeltaIndex;
  compareReady: boolean;
  projectionReady: boolean;
  onSelectEvidenceDelta?: (deltaId: string) => void;
  selectedEvidenceDeltaId?: string | null;
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function GraphReviewDeltaSummaryPanel({
  deltaIndex,
  compareReady,
  projectionReady,
  onSelectEvidenceDelta,
  selectedEvidenceDeltaId = null,
}: GraphReviewDeltaSummaryPanelProps) {
  const sampleDeltas = deltaIndex.deltas.slice(0, 25);

  return (
    <section className="graph-review-delta-summary-panel" aria-label="Contextual delta model">
      <header>
        <p className="plan-surface-kicker">Contextual delta model</p>
        <h3>Delta summary</h3>
        <p className="graph-review-delta-note">
          Delta statuses are model-only in this PR. Inline pill overlays come next.
        </p>
      </header>

      {!compareReady ? (
        <p className="graph-review-delta-note">
          Comparison has not loaded yet, so contextual deltas are unavailable.
        </p>
      ) : null}
      {!projectionReady ? (
        <p className="graph-review-delta-note">
          Live projection has not loaded yet. Deltas can still be object-level, but source-span anchoring may be incomplete.
        </p>
      ) : null}

      <div className="graph-review-delta-count-grid" aria-label="Delta counts">
        <div className="graph-review-delta-count-card"><span>Matched</span><strong>{deltaIndex.countsByStatus.matched}</strong></div>
        <div className="graph-review-delta-count-card"><span>Gold-only</span><strong>{deltaIndex.countsByStatus.gold_only}</strong></div>
        <div className="graph-review-delta-count-card"><span>Live-only</span><strong>{deltaIndex.countsByStatus.live_only}</strong></div>
        <div className="graph-review-delta-count-card"><span>Uncertain</span><strong>{deltaIndex.countsByStatus.comparator_uncertain}</strong></div>
      </div>

      {deltaIndex.warnings.length ? (
        <ul className="graph-review-delta-note">
          {deltaIndex.warnings.map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      ) : null}

      {sampleDeltas.length ? (
        <ol className="graph-review-delta-list" aria-label="Delta sample rows">
          {sampleDeltas.map((delta) => (
            <li className="graph-review-delta-row" key={delta.deltaId} data-selected-evidence={delta.deltaId === selectedEvidenceDeltaId ? "true" : "false"}>
              <span className="graph-review-delta-status">{statusLabel(delta.status)}</span>
              <span>{delta.objectKind}</span>
              <span>{delta.label || delta.summary}</span>
              <span>{delta.primarySourceSpanRefId ? `span: ${delta.primarySourceSpanRefId}` : "no live source span"}</span>
              {onSelectEvidenceDelta ? (
                <button className="graph-review-evidence-inspect-button" type="button" onClick={() => onSelectEvidenceDelta(delta.deltaId)}>
                  Inspect evidence
                </button>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="graph-review-delta-note">No contextual deltas to show yet.</p>
      )}
    </section>
  );
}
