import { useEffect, useRef, useState } from 'react';

/** Persisted text is visible independently of receipt inspection. */
export function ConversationDetailsButton({ load }: { load: (signal: AbortSignal) => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  function inspect() {
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError(null);
    void load(controller.signal)
      .catch(reason => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Reply details are unavailable.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
  }

  return <>
    <button type="button" disabled={busy} onClick={inspect}>
      {busy ? 'Loading reply details…' : 'Sources and actions'}
    </button>
    {error && <p role="alert">{error}</p>}
  </>;
}
