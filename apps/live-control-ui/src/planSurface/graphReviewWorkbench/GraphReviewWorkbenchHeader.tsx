interface GraphReviewWorkbenchHeaderProps {
  loaded: boolean;
  sessionLabel: string | null;
  onOpenLoad: () => void;
}

export function GraphReviewWorkbenchHeader({
  loaded,
  sessionLabel,
  onOpenLoad,
}: GraphReviewWorkbenchHeaderProps) {
  return (
    <header className="graph-review-workbench-header graph-review-workbench-header--unified">
      <div className="graph-review-workbench-header-copy">
        <p className="plan-surface-kicker">Prose-first review tool</p>
        <h2>Graph Review Workbench</h2>
      </div>
      <div
        className="graph-review-workbench-header-actions"
        aria-label="Graph review session controls"
      >
        {loaded && sessionLabel ? (
          <span className="graph-review-workbench-session-label">{sessionLabel}</span>
        ) : (
          <span className="graph-review-workbench-session-label graph-review-workbench-session-label--empty">
            No session loaded
          </span>
        )}
        <button
          type="button"
          className="graph-review-workbench-header-button graph-review-load-recap-button"
          onClick={onOpenLoad}
        >
          Load recap
        </button>
      </div>
    </header>
  );
}
