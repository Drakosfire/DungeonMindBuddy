interface GraphReviewWorkbenchHeaderProps {
  loaded: boolean;
  sessionLabel: string | null;
  onOpenLoad: () => void;
  graphAuthoringEnabled?: boolean;
  onGraphAuthoringToggle?: () => void;
}

export function GraphReviewWorkbenchHeader({
  loaded,
  sessionLabel,
  onOpenLoad,
  graphAuthoringEnabled = false,
  onGraphAuthoringToggle,
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
        {loaded && onGraphAuthoringToggle ? (
          <button
            type="button"
            className={`graph-review-workbench-header-button graph-review-author-graph-button${
              graphAuthoringEnabled ? " is-active" : ""
            }`}
            aria-pressed={graphAuthoringEnabled}
            data-testid="graph-authoring-mode-toggle"
            onClick={onGraphAuthoringToggle}
          >
            <span className="graph-review-author-graph-button-icon" aria-hidden="true">
              ✦
            </span>
            <span>
              {graphAuthoringEnabled ? "Authoring memory…" : "Author graph objects"}
            </span>
          </button>
        ) : null}
      </div>
    </header>
  );
}
