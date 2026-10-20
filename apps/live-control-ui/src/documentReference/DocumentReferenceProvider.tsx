import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode, type MouseEvent, type KeyboardEvent } from 'react';
import { PeekClaim } from '../surfaceInteraction/peekHost';
import { MarkdownDocumentReader } from '../markdownReader/MarkdownDocumentReader';
import { ReadOnlyBodyContent } from '../markdownReader/ReadOnlyBodyContent';
import { markdownToTiptapDoc } from '../tiptap/markdown/markdownToTiptap';
import { owningDocumentHref, parseDocumentReference, type ReferenceParse } from './documentReference';
import { resolveDocumentReference, type DocumentInspection } from './resolveDocumentReference';
import './documentReference.css';

type Entry = Exclude<ReferenceParse, { kind: 'other' }> & { scroll: number };
export function DocumentReferenceProvider({ children, worldId, sourceIdentity, enabled = true, load = resolveDocumentReference }: {
  children: ReactNode; worldId: string | null; sourceIdentity: string; enabled?: boolean;
  load?: typeof resolveDocumentReference;
}) {
  const [history, setHistory] = useState<Entry[]>([]);
  const [outcome, setOutcome] = useState<{ entry: Entry; data?: DocumentInspection; error?: string } | null>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const pane = useRef<HTMLElement | null>(null);
  const closeButton = useRef<HTMLButtonElement | null>(null);
  const generation = useRef(0);
  const sourceScroll = useRef<{ element: HTMLElement; top: number; left: number }[]>([]);
  const restoreOnClose = useRef(false);
  const active = history.at(-1);
  const close = useCallback(() => {
    generation.current += 1;
    restoreOnClose.current = true;
    setHistory([]); setOutcome(null);
    if (trigger.current?.isConnected) trigger.current.focus({ preventScroll: true });
    trigger.current = null;
  }, []);
  useLayoutEffect(() => {
    generation.current += 1; setHistory([]); setOutcome(null); trigger.current = null;
    sourceScroll.current = []; restoreOnClose.current = false;
  }, [worldId, sourceIdentity, enabled]);
  useLayoutEffect(() => {
    if (active || !restoreOnClose.current) return;
    for (const saved of sourceScroll.current) {
      if (saved.element.isConnected) { saved.element.scrollTop = saved.top; saved.element.scrollLeft = saved.left; }
    }
    sourceScroll.current = []; restoreOnClose.current = false;
  }, [active]);
  useEffect(() => {
    if (!active) return;
    const current = ++generation.current;
    setOutcome(null);
    if (active.kind === 'invalid') { setOutcome({ entry: active, error: active.message }); return; }
    if (!worldId) { setOutcome({ entry: active, error: 'Select a World to inspect this reference.' }); return; }
    void load(active.target, worldId).then(data => {
      if (generation.current === current) setOutcome({ entry: active, data });
    }).catch(error => {
      if (generation.current === current) setOutcome({ entry: active, error: error instanceof Error ? error.message : 'Saved document unavailable.' });
    });
    return () => { generation.current += 1; };
  }, [active, worldId, load]);
  useEffect(() => {
    if (!active) return;
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); }
    };
    document.addEventListener('keydown', escape, true);
    return () => document.removeEventListener('keydown', escape, true);
  }, [active, close]);
  useLayoutEffect(() => { if (pane.current && outcome?.entry === active) pane.current.scrollTop = active?.scroll ?? 0; }, [outcome, active]);
  const activate = (event: MouseEvent<HTMLDivElement> | KeyboardEvent<HTMLDivElement>) => {
    if (!enabled || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey
      || ('button' in event && event.button !== 0) || ('key' in event && event.key !== 'Enter')) return;
    const element = event.target instanceof Element ? event.target.closest('a[data-web-source-link],a[data-document-reference]') : null;
    if (!(element instanceof HTMLAnchorElement)) return;
    const parsed = parseDocumentReference(element.getAttribute('href') ?? '', window.location.origin);
    if (parsed.kind === 'other') return;
    event.preventDefault(); event.stopPropagation();
    generation.current += 1;
    if (!active) {
      trigger.current = element;
      sourceScroll.current = [];
      for (let ancestor: HTMLElement | null = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
        sourceScroll.current.push({ element: ancestor, top: ancestor.scrollTop, left: ancestor.scrollLeft });
      }
    }
    const scroll = pane.current?.scrollTop ?? 0;
    setHistory(items => [...items.slice(-15).map((item, index, kept) => index === kept.length - 1 ? { ...item, scroll } : item), { ...parsed, scroll: 0 }]);
    // Focus only on explicit activation, never on asynchronous response arrival.
    requestAnimationFrame(() => closeButton.current?.focus({ preventScroll: true }));
  };
  const data = outcome && outcome.entry === active ? outcome.data : undefined;
  const error = outcome && outcome.entry === active ? outcome.error : undefined;
  const imported = useMemo(() => data ? markdownToTiptapDoc(data.markdown) : null, [data]);
  return <div className="document-reference-capability" onClickCapture={activate} onKeyDownCapture={activate}>
    {children}
    <PeekClaim kind="document-reference" active={!!active} label="Document reference" onDismiss={close}>
      <section ref={pane} className="document-reference" aria-label="Document reference">
        <header>
          {history.length > 1 && <button type="button" onClick={() => { generation.current += 1; setHistory(items => items.slice(0, -1)); }}>← Previous reference</button>}
          <button ref={closeButton} type="button" onClick={close}>Close reference</button>
        </header>
        {error ? <p role="alert">{error}</p> : data ? <>
          <h2>{data.title}</h2><p>{data.revisionLabel}. Read only; local drafts are not shown.</p>
          {active?.kind === 'document' && active.target.heading && <p role="status">Showing the saved document. The link’s section hint is not resolved.</p>}
          {imported && imported.diagnostics.length === 0
            ? <ReadOnlyBodyContent content={imported.doc.content} />
            : <><p role="status">Some content uses source rendering.</p><MarkdownDocumentReader markdown={data.markdown} /></>}
          <details><summary>Source details</summary><p>SHA-256: {data.digest}</p></details>
          {active?.kind === 'document' && active.target.registryRevision === undefined && active.target.revisionN === undefined && !active.target.digest
            && <a href={owningDocumentHref(active.target)} target="_blank" rel="noopener noreferrer">Open owning surface in a new tab</a>}
        </> : <p role="status">Opening saved document…</p>}
      </section>
    </PeekClaim>
  </div>;
}
