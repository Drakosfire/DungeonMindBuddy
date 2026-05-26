import { FormEvent, useState } from "react";

import { postLiveQuery } from "../../api/liveApi";
import type { LiveQueryResponse } from "../../api/types";

interface ChatModuleProps {
  campaignId: string;
  session: number;
  onQuerySuccess: (response: LiveQueryResponse) => void | Promise<void>;
}

export function ChatModule({ campaignId, session, onQuerySuccess }: ChatModuleProps) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<LiveQueryResponse | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await postLiveQuery(trimmed, campaignId, session);
      setLastResponse(response);
      setText("");
      await onQuerySuccess(response);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Query failed");
    } finally {
      setLoading(false);
    }
  }

  const latencyMode = lastResponse?.classification.latency_mode;
  const eventType = lastResponse?.classification.event_type;
  const isContextLookup = latencyMode === "context_lookup";

  return (
    <div className="module-panel chat-module" data-module-id="chat">
      <h2 className="module-title">Chat</h2>
      <form className="chat-form" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="live-query-input">
          Live query
        </label>
        <textarea
          id="live-query-input"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Weather 7. Caelynn Nature 19."
          rows={3}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !text.trim()}>
          {loading ? "Sending…" : "Send"}
        </button>
      </form>
      {error ? <p className="module-error">{error}</p> : null}
      {lastResponse ? (
        <div className={`chat-response ${isContextLookup ? "context-lookup" : "fast-live"}`}>
          <p className="chat-answer">{lastResponse.answer}</p>
          <p className="chat-badges">
            <span className="badge latency-badge">{latencyMode}</span>
            <span className="badge event-badge">{eventType}</span>
          </p>
          {lastResponse.next_suggestions.length > 0 ? (
            <ul className="chat-suggestions">
              {lastResponse.next_suggestions.map((suggestion) => (
                <li key={suggestion}>{suggestion}</li>
              ))}
            </ul>
          ) : null}
          {isContextLookup && Object.keys(lastResponse.provenance).length > 0 ? (
            <details className="chat-provenance">
              <summary>Provenance</summary>
              <pre>{JSON.stringify(lastResponse.provenance, null, 2)}</pre>
            </details>
          ) : null}
          {isContextLookup && Object.keys(lastResponse.diagnostics).length > 0 ? (
            <details className="chat-diagnostics">
              <summary>Diagnostics</summary>
              <pre>{JSON.stringify(lastResponse.diagnostics, null, 2)}</pre>
            </details>
          ) : null}
        </div>
      ) : (
        <p className="module-muted">Submit a live turn to see answer and classification.</p>
      )}
    </div>
  );
}
