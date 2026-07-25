import { GraphReviewWorkbenchActivity } from "./GraphReviewWorkbenchActivity";
import type { GraphReviewActivity } from "./graphReviewActivity";

interface GraphReviewExactRunSummary {
  extractionRunId: string;
  sourceDomain: string;
  status: string;
  sourceArtifactId: string;
  profileId: string | null;
  campaignId: string | null;
  sessionId: string | null;
  documentId: string | null;
  revision: number | null;
  reviewable: boolean;
  promotable?: boolean;
}

interface GraphReviewWorkbenchHeaderProps {
  loaded: boolean;
  sessionLabel: string | null;
  onOpenLoad: () => void;
  activity?: GraphReviewActivity | null;
  /** World Graph authority — floating green Memory pill beside Load recap. */
  inMemory?: boolean;
  exactRun?: GraphReviewExactRunSummary | null;
}

/**
 * Session chrome: recap context + exact-run banner, activity strip, and Memory pill beside Load recap.
 */
export function GraphReviewWorkbenchHeader({
  loaded,
  sessionLabel,
  onOpenLoad,
  activity = null,
  inMemory = false,
  exactRun = null,
}: GraphReviewWorkbenchHeaderProps) {
  const scopeLabel = exactRun
    ? exactRun.sessionId
      ? `campaign ${exactRun.campaignId ?? "—"} · session ${exactRun.sessionId}`
      : exactRun.campaignId
        ? `campaign ${exactRun.campaignId} · no session`
        : "world / source authority · no session"
    : null;

  return (
    <header className="graph-review-workbench-header graph-review-workbench-header--unified">
      <div className="graph-review-workbench-header-copy">
        <p className="plan-surface-kicker">Prose-first review tool</p>
        <h2>Graph Review Workbench</h2>
        {exactRun ? (
          <div
            className="graph-review-exact-run-banner"
            data-testid="graph-review-exact-run-banner"
          >
            <p>
              Exact run <code>{exactRun.extractionRunId}</code>
              {" · "}
              {exactRun.sourceDomain}
              {" · "}
              {exactRun.status}
              {exactRun.reviewable ? " · reviewable" : " · not reviewable"}
            </p>
            <p>
              Source <code>{exactRun.sourceArtifactId}</code>
              {exactRun.profileId ? ` · ${exactRun.profileId}` : ""}
              {exactRun.documentId
                ? ` · doc ${exactRun.documentId}${exactRun.revision != null ? ` r${exactRun.revision}` : ""}`
                : ""}
            </p>
            <p data-testid="graph-review-exact-run-scope">{scopeLabel}</p>
          </div>
        ) : null}
      </div>
      <div
        className="graph-review-workbench-header-actions"
        aria-label="Graph review session controls"
      >
        {exactRun ? (
          <span className="graph-review-workbench-session-label">Exact run loaded</span>
        ) : loaded && sessionLabel ? (
          <span
            className="graph-review-workbench-session-label"
            data-testid="graph-review-session-label"
            title={sessionLabel}
          >
            {sessionLabel}
          </span>
        ) : (
          <span className="graph-review-workbench-session-label graph-review-workbench-session-label--empty">
            No session loaded
          </span>
        )}
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
