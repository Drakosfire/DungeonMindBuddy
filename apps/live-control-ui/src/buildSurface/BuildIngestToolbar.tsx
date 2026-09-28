import { useBuildExtraction } from "./useBuildExtraction";
import { useBuildNativeWorldSourceEvidence } from "./useBuildNativeWorldSourceEvidence";

interface BuildIngestToolbarProps {
  documentId: string;
}

export function BuildIngestToolbar({ documentId }: BuildIngestToolbarProps) {
  const nativeSource = useBuildNativeWorldSourceEvidence(documentId);
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
        <p data-testid="build-native-source-status" aria-live="polite">
          {nativeSource.loading
            ? "Native World source: checking…"
            : nativeSource.status?.state === "admitted"
              ? "Native World source: admitted"
              : nativeSource.status?.state === "pending"
                ? "Source saved; native World admission pending"
                : "Native World source status unavailable"}
        </p>
        <div className="build-ingest-toolbar-actions">
          {nativeSource.status?.state === "pending" ? (
            <button
              type="button"
              data-testid="build-native-source-retry"
              onClick={() => void nativeSource.retry()}
              disabled={nativeSource.retrying || nativeSource.loading}
            >
              {nativeSource.retrying ? "Admitting…" : "Retry World admission"}
            </button>
          ) : null}
          <button
            type="button"
            data-testid="build-native-source-refresh"
            onClick={() => void nativeSource.reload()}
            disabled={nativeSource.loading || nativeSource.retrying}
          >
            Refresh World status
          </button>
        </div>
      </div>
      {nativeSource.status?.state === "admitted" ? (
        <p data-testid="build-native-source-evidence">
          World <code>{nativeSource.status.world_id}</code> · exact source revision {nativeSource.status.loaded_revision} · whole-document evidence
        </p>
      ) : null}
      {nativeSource.error ? (
        <p role="alert" data-testid="build-native-source-error">{nativeSource.error}</p>
      ) : null}
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
