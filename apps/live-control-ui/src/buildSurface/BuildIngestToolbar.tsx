import { useProjection } from "../planSurface/projection/projectionContext";
import { BuildExactRunSummary } from "./BuildExactRunSummary";
import { useBuildExtraction } from "./useBuildExtraction";

interface BuildIngestToolbarProps {
  documentId: string;
}

export function BuildIngestToolbar({ documentId }: BuildIngestToolbarProps) {
  const { openTool } = useProjection();
  const {
    statusLabel,
    error,
    canLaunch,
    canRefresh,
    canOpenGraphReview,
    canInspectRun,
    launching,
    handoff,
    run,
    pinnedRevision,
    pinnedDigest,
    runDiagnostics,
    launch,
    refresh,
  } = useBuildExtraction({ documentId });

  return (
    <section className="build-ingest-toolbar" data-testid="build-ingest-toolbar" aria-label="Build extraction">
      <div className="build-ingest-toolbar-row">
        <p data-testid="build-extraction-status">{statusLabel}</p>
        <div className="build-ingest-toolbar-actions">
          <button
            type="button"
            data-testid="build-extract-button"
            onClick={() => {
              void launch();
            }}
            disabled={!canLaunch}
          >
            {launching ? "Extracting…" : "Extract"}
          </button>
          <button
            type="button"
            data-testid="build-extraction-refresh"
            onClick={() => {
              void refresh();
            }}
            disabled={!canRefresh}
          >
            Refresh run
          </button>
          {canInspectRun ? (
            <button
              type="button"
              data-testid="build-inspect-run"
              onClick={() => openTool("build-extraction-run-inspector")}
            >
              Inspect run
            </button>
          ) : null}
          {canOpenGraphReview && handoff ? (
            <a
              className="build-ingest-toolbar-secondary-link"
              data-testid="build-open-graph-review"
              href={handoff.href}
            >
              Open full Graph Review
            </a>
          ) : (
            <span data-testid="build-open-graph-review-disabled">Open full Graph Review</span>
          )}
        </div>
      </div>
      {run ? (
        <BuildExactRunSummary
          run={run}
          pinnedRevision={pinnedRevision}
          pinnedDigest={pinnedDigest}
          error={error}
          runDiagnostics={runDiagnostics}
        />
      ) : error ? (
        <p role="alert" data-testid="build-extraction-error">{error}</p>
      ) : null}
    </section>
  );
}
