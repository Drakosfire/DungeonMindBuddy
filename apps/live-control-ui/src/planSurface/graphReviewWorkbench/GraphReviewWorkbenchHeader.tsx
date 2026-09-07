import {
  formatHumanExactRunLoadLabel,
  formatMachineExactRunScopeLabel,
} from "./graphReviewWorkbenchUtils";

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
  readOnly?: boolean;
  worldId?: string | null;
  graphId?: string | null;
  inspectOnlyReason?: string | null;
}

interface GraphReviewWorkbenchHeaderProps {
  loaded: boolean;
  sessionLabel: string | null;
  onOpenLoad: () => void;
  loadDisabled?: boolean;
  loadDisabledReason?: string | null;
  exactRun?: GraphReviewExactRunSummary | null;
}

export function GraphReviewWorkbenchHeader({
  loaded,
  sessionLabel,
  onOpenLoad,
  loadDisabled = false,
  loadDisabledReason = null,
  exactRun = null,
}: GraphReviewWorkbenchHeaderProps) {
  const scopeLabel = exactRun
    ? formatMachineExactRunScopeLabel({
        campaignId: exactRun.campaignId,
        sessionId: exactRun.sessionId,
      })
    : null;
  const compactLabel = exactRun
    ? formatHumanExactRunLoadLabel({
        campaignId: exactRun.campaignId,
        sessionId: exactRun.sessionId,
      })
    : loaded && sessionLabel
      ? sessionLabel
      : null;

  return (
    <header className="graph-review-workbench-header graph-review-workbench-header--unified">
      <div className="graph-review-workbench-header-copy">
        <p className="plan-surface-kicker">Prose-first review tool</p>
        <h2>Graph Review Workbench</h2>
        {exactRun ? (
          <details
            className="graph-review-advanced-details"
            data-testid="graph-review-exact-run-banner"
          >
            <summary>Advanced details</summary>
            <dl className="graph-review-lane-meta">
              <div>
                <dt>Run</dt>
                <dd>
                  <code>{exactRun.extractionRunId}</code>
                </dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>
                  <code>{exactRun.sourceArtifactId}</code>
                  {exactRun.profileId ? ` · ${exactRun.profileId}` : ""}
                  {exactRun.documentId
                    ? ` · doc ${exactRun.documentId}${exactRun.revision != null ? ` r${exactRun.revision}` : ""}`
                    : ""}
                </dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  {exactRun.sourceDomain}
                  {" · "}
                  {exactRun.status}
                  {exactRun.reviewable ? " · reviewable" : " · not reviewable"}
                </dd>
              </div>
            </dl>
            <p data-testid="graph-review-exact-run-scope">{scopeLabel}</p>
            <p data-testid="graph-review-historical-recap-meta">
              {exactRun.sourceArtifactId}
              {exactRun.campaignId ? ` · ${exactRun.campaignId}` : ""}
              {exactRun.sessionId ? ` · ${exactRun.sessionId}` : ""}
              {" · status "}
              {exactRun.status}
              {exactRun.worldId ? ` · World ${exactRun.worldId}` : ""}
              {exactRun.graphId ? ` · graph ${exactRun.graphId}` : ""}
            </p>
            <p className="graph-review-advanced-details-note">
              Bound to exact ExtractionRun <code>{exactRun.extractionRunId}</code>. Prepare uses
              runId-only server resolution; no latest-run fallback.
            </p>
            {exactRun.inspectOnlyReason ? (
              <p data-testid="graph-review-exact-run-not-promotable">
                {exactRun.inspectOnlyReason}
              </p>
            ) : null}
          </details>
        ) : null}
      </div>
      <div
        className="graph-review-workbench-header-actions"
        aria-label="Graph review session controls"
      >
        {compactLabel ? (
          <span className="graph-review-workbench-session-label">{compactLabel}</span>
        ) : (
          <span className="graph-review-workbench-session-label graph-review-workbench-session-label--empty">
            No session loaded
          </span>
        )}
        {exactRun?.readOnly ? (
          <span className="graph-review-read-only-chip">Read-only</span>
        ) : null}
        <button
          type="button"
          className="graph-review-workbench-header-button graph-review-load-recap-button"
          data-testid="graph-review-load-recap"
          disabled={loadDisabled}
          title={loadDisabled ? (loadDisabledReason ?? "Load recap unavailable") : undefined}
          onClick={onOpenLoad}
        >
          Load recap
        </button>
      </div>
    </header>
  );
}
