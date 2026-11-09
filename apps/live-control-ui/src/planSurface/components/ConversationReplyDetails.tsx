import { useEffect, useRef, useState, type ReactNode } from 'react';

/** One disclosure for a reply. Saved text and independently owned actions never wait for it. */
export function ConversationReplyDetails({ id, open, onOpenChange, loaded, load, showSources = false, reviewLabel, children }: {
  id: string; open: boolean; onOpenChange: (open: boolean) => void; loaded: boolean;
  load: (signal: AbortSignal) => Promise<void>; showSources?: boolean; reviewLabel?: string; children: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  function inspect() {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true); setError(null);
    void load(controller.signal).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Reply details are unavailable.');
    }).finally(() => {
      if (!controller.signal.aborted) { request.current = null; setBusy(false); }
    });
  }

  useEffect(() => {
    if (loaded) setError(null);
    else if (open && !error) inspect();
  }, [open, loaded]);

  return <>
    {(showSources||reviewLabel) && !loaded && <button type="button" disabled={busy} onClick={inspect}>{reviewLabel??'Show citations'}</button>}
    {!open && busy && <p role="status">Loading reply sources…</p>}
    {!open && error && <p role="alert">{error}</p>}
    <details id={id} className="world-plan-agent-conversation__turn-details" open={open} onToggle={event => {
      const next = event.currentTarget.open;
      onOpenChange(next);
      if (next && !loaded && !busy && !error) inspect();
    }}>
    <summary>Details</summary>
    {open && <>
      {busy && <p role="status">Loading reply details…</p>}
      {error && <div><p role="alert">{error}</p><button type="button" onClick={inspect}>Retry details</button></div>}
    </>}
    {children}
  </details></>;
}
