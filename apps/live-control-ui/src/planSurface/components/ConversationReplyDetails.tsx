import './BuddyEvidence.css';
import { createContext, useContext, useEffect, useId, useRef, useState, type ReactNode } from 'react';

export type TraceTab = 'evidence' | 'crawler' | 'timeline' | 'prompt' | 'diagnostics';
export const TraceTabContext = createContext<TraceTab | null>(null);
export function TraceEvidence({ children }: { children: ReactNode }) {
  const tab = useContext(TraceTabContext);
  return <div hidden={tab !== null && tab !== 'evidence'}>{children}</div>;
}
export function TraceDiagnostics({ children }: { children: ReactNode }) {
  const tab = useContext(TraceTabContext);
  return <div hidden={tab !== null && tab !== 'diagnostics'}>{children}</div>;
}

/** One disclosure for a reply. Saved text and independently owned actions never wait for it. */
export function ConversationReplyDetails({ id, open, onOpenChange, loaded, load, showSources = false, reviewLabel, children }: {
  id: string; open: boolean; onOpenChange: (open: boolean) => void; loaded: boolean;
  load: (signal: AbortSignal) => Promise<void>; showSources?: boolean; reviewLabel?: string; children: ReactNode;
}) {
  const [tab, setTab] = useState<TraceTab>('evidence');
  const tabs: [TraceTab, string][] = [['evidence', 'Evidence'], ['crawler', 'Graph crawler'], ['timeline', 'Execution timeline'], ['prompt', 'Prompt'], ['diagnostics', 'Diagnostics']];
  const tabId = useId();
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
    <summary>Trace</summary>
    <div role="tablist" aria-label="Trace sections" className="buddy-context-trace__tabs">
      {tabs.map(([key, label], index) => <button key={key} type="button" role="tab"
        id={`${tabId}-${key}`} aria-controls={`${tabId}-panel`} aria-selected={tab === key}
        tabIndex={tab === key ? 0 : -1} onClick={() => setTab(key)}
        onKeyDown={event => {
          const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length
            : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length
              : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1;
          if (next >= 0) {
            event.preventDefault();
            setTab(tabs[next][0]);
            event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
          }
        }}>{label}</button>)}
    </div>
    <TraceTabContext.Provider value={tab}>
      <div role="tabpanel" id={`${tabId}-panel`} aria-labelledby={`${tabId}-${tab}`}>{children}</div>
    </TraceTabContext.Provider>
    {open && busy && <p role="status">Loading reply details…</p>}
    {open && error && <div>
      <p role="alert">{error}</p><button type="button" onClick={inspect}>Retry details</button>
    </div>}
  </details></>;
}
