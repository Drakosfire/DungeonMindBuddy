import { useBuildExtraction } from "./useBuildExtraction";

interface BuildIngestToolbarProps {
  documentId: string;
}

export function BuildIngestToolbar({ documentId }: BuildIngestToolbarProps) {
  const {
    statusLabel,
    error,
    canLaunch,
    canRefresh,
    canOpenGraphReview,
    launching,
    handoff,
    run,
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
          {canOpenGraphReview && handoff ? (
            <a
              data-testid="build-open-graph-review"
              href={handoff.href}
            >
              Open in Graph Review
            </a>
          ) : (
            <span data-testid="build-open-graph-review-disabled">Open in Graph Review</span>
          )}
        </div>
      </div>
      {run ? (
        <p data-testid="build-extraction-run-id">
          Exact run: <code>{run.run_id}</code>
        </p>
      ) : null}
      {error ? (
        <p role="alert" data-testid="build-extraction-error">{error}</p>
      ) : null}
    </section>
  );
}
