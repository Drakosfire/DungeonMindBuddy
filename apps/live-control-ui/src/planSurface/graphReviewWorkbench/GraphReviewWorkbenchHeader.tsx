import { GraphReviewWorkbenchActivity } from "./GraphReviewWorkbenchActivity";
import type { GraphReviewActivity } from "./graphReviewActivity";

interface GraphReviewWorkbenchHeaderProps {
  loaded: boolean;
  sessionLabel: string | null;
  onOpenLoad: () => void;
  activity?: GraphReviewActivity | null;
  /** World Graph authority — floating green Memory pill beside Load recap. */
  inMemory?: boolean;
}

/**
 * Compact session chrome: context + activity + Memory sit beside Load recap.
 * Sticky so it floats above the prose while scrolling.
 */
export function GraphReviewWorkbenchHeader({
  loaded,
  sessionLabel,
  onOpenLoad,
  activity = null,
  inMemory = false,
}: GraphReviewWorkbenchHeaderProps) {
  return (
    <header className="graph-review-workbench-header graph-review-workbench-header--compact">
      <div
        className="graph-review-workbench-header-actions"
        aria-label="Graph review session controls"
      >
        {loaded && sessionLabel ? (
          <span
            className="graph-review-workbench-session-label"
            data-testid="graph-review-session-label"
            title={sessionLabel}
          >
            {sessionLabel}
          </span>
        ) : null}
        <GraphReviewWorkbenchActivity activity={activity} />
        {inMemory ? (
          <span
            className="graph-review-memory-indicator"
            data-testid="graph-review-memory-indicator"
            title="This session is in World Graph memory"
            role="status"
          >
            Memory
          </span>
        ) : null}
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
