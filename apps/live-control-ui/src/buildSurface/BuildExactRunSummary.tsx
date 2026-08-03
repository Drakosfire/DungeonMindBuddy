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

  const hasPin = pinnedRevision != null || Boolean(pinnedDigest);
  const hasDiagnostics = runLevelDiagnostics.length > 0;
  if (!hasPin && !error && !hasDiagnostics) {
    return null;
  }

  return (
    <div className="build-exact-run-summary" data-testid="build-exact-run-summary">
      {hasPin ? (
        <p data-testid="build-extraction-pin">
          {pinnedRevision != null ? (
            <>
              Pinned rev <code data-testid="build-extraction-pinned-revision">{pinnedRevision}</code>
            </>
          ) : null}
          {pinnedRevision != null && pinnedDigest ? " · " : null}
          {pinnedDigest ? (
            <>
              digest <code data-testid="build-extraction-pinned-digest">{pinnedDigest}</code>
            </>
          ) : null}
        </p>
      ) : null}
      {error ? (
        <p role="alert" data-testid="build-extraction-error">{error}</p>
      ) : null}
      {hasDiagnostics ? (
        <ul data-testid="build-extraction-diagnostics">
          {runLevelDiagnostics.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
