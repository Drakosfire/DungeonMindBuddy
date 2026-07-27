import type { ExtractionRunRecord } from "../api/types";

export interface BuildExactRunSummaryProps {
  run: ExtractionRunRecord;
  pinnedRevision: number | null;
  pinnedDigest: string | null;
  error: string | null;
  runDiagnostics: string[];
}

export function BuildExactRunSummary({
  run,
  pinnedRevision,
  pinnedDigest,
  error,
  runDiagnostics,
}: BuildExactRunSummaryProps) {
  const runLevelDiagnostics = [
    ...(run.diagnostics?.messages ?? []),
    ...(run.diagnostics?.errors ?? []),
    ...runDiagnostics,
  ];

  return (
    <div className="build-exact-run-summary" data-testid="build-exact-run-summary">
      <p data-testid="build-extraction-run-id">
        Exact run: <code>{run.run_id}</code>
        {" · "}
        <span data-testid="build-extraction-run-status">{run.status}</span>
      </p>
      {pinnedRevision != null ? (
        <p data-testid="build-extraction-pinned-revision">
          Pinned source revision: <code>{pinnedRevision}</code>
        </p>
      ) : null}
      {pinnedDigest ? (
        <p data-testid="build-extraction-pinned-digest">
          Content digest: <code>{pinnedDigest}</code>
        </p>
      ) : null}
      {error ? (
        <p role="alert" data-testid="build-extraction-error">{error}</p>
      ) : null}
      {runLevelDiagnostics.length > 0 ? (
        <ul data-testid="build-extraction-diagnostics">
          {runLevelDiagnostics.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
