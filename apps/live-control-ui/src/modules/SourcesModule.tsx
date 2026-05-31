import { CorpusIngestLadder } from "./CorpusIngestLadder";
import { corpusStatusHeadline, corpusStatusTone } from "./corpusIngestDisplay";
import { useCorpusIngestStatus } from "./useCorpusIngestStatus";

interface SourcesModuleProps {
  campaignId: string;
  session: number;
}

export function SourcesModule({ campaignId, session }: SourcesModuleProps) {
  const { result, loading, error, refresh, recapSession, liveSession } = useCorpusIngestStatus(
    campaignId,
    session,
  );
  const tone = corpusStatusTone(result);

  return (
    <div className="module-panel sources-module" data-module-id="sources">
      <div className="sources-header">
        <h2 className="module-title">Corpus &amp; sources</h2>
        <button type="button" className="sources-refresh" onClick={() => void refresh()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <p className="module-muted sources-context">
        Planning session <strong>{liveSession}</strong> · recap source session{" "}
        <strong>{recapSession}</strong>
      </p>

      {error ? <p className="module-error">{error}</p> : null}

      <div className={`corpus-status-banner corpus-status-${tone}`} role="status" aria-live="polite">
        <p className="corpus-status-headline">{corpusStatusHeadline(result)}</p>
        {result ? (
          <p className="corpus-status-detail">
            Pipeline status: <code>{result.status}</code>
          </p>
        ) : null}
      </div>

      {result ? (
        <>
          <CorpusIngestLadder result={result} />

          {result.warnings.length > 0 ? (
            <details className="sources-details">
              <summary>Warnings ({result.warnings.length})</summary>
              <ul>
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </details>
          ) : null}

          {result.next_actions.length > 0 && !result.states.includes("ready_for_planning_activation") ? (
            <details className="sources-details" open>
              <summary>Next actions</summary>
              <ul>
                {result.next_actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </details>
          ) : null}

          {result.errors.length > 0 ? (
            <details className="sources-details sources-details-error" open>
              <summary>Errors</summary>
              <ul>
                {result.errors.map((row) => (
                  <li key={row}>{row}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </>
      ) : loading ? (
        <p className="module-muted">Loading corpus status from disk…</p>
      ) : null}
    </div>
  );
}
