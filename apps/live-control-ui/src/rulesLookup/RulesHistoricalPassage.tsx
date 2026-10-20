import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { getHistoricalRulesPassage, getNativeGraphAccessGeneration, NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT } from '../api/liveApi';
import type { RulesHistoricalPassage, RulesPassageTarget } from '../api/rulesLookupTypes';
import { verifyHistoricalRulesPassage } from './rulesEvidence';
import { RulesPassageView } from './RulesPassageView';

/** Mounted only while open; exact target is keyed by the lightweight outer control. */
export default function RulesHistoricalPassageReader({ target, onClose }: { target: RulesPassageTarget; onClose: () => void }) {
  const [passage, setPassage] = useState<RulesHistoricalPassage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const retire = useRef<() => void>(() => {});
  useLayoutEffect(() => {
    const epoch = getNativeGraphAccessGeneration();
    const changed = () => { if (getNativeGraphAccessGeneration() !== epoch) { retire.current(); setPassage(null); setError('Access changed. Close and reopen this citation.'); } };
    window.addEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, changed);
    return () => window.removeEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, changed);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    const epoch = getNativeGraphAccessGeneration();
    let live = true;
    const current = () => live && !controller.signal.aborted;
    retire.current = () => { live = false; controller.abort(); };
    setPassage(null); setError(null);
    void Promise.resolve().then(() => getHistoricalRulesPassage(target, controller.signal)).then(value => verifyHistoricalRulesPassage(value, target)).then(value => {
      if (!current()) return;
      if (getNativeGraphAccessGeneration() !== epoch) { setError('Access changed. Close and reopen this citation.'); return; }
      setPassage(value);
    }).catch(reason => {
      if (current()) { setPassage(null); setError(getNativeGraphAccessGeneration() !== epoch ? 'Access changed. Close and reopen this citation.' : reason instanceof Error ? reason.message : 'Saved Rules excerpt unavailable.'); }
    });
    return () => { live = false; controller.abort(); };
  }, [target.worldId, target.conversationId, target.turnId, target.attempt, target.supportId, target.supportSha256, retry]);
  if (error) return <div><p role="alert">{error}</p><button type="button" onClick={() => setRetry(value => value + 1)}>Retry cited excerpt</button></div>;
  if (!passage) return <p role="status">Loading cited Rules excerpt…</p>;
  const support = passage.support;
  const page = support.printed_page === null ? `PDF page ${support.pdf_page_index + 1}` : `Page ${support.printed_page}`;
  return <RulesPassageView section={support.section} title={support.source_title} page={page}
    text={support.excerpt_text} attribution="Historical Rules evidence; separate from World facts and played events."
    sourceUri={support.source_uri} corpus={support.corpus_sha256} textSha256={support.excerpt_sha256} onClose={onClose} excerpt excerptIdentity={{ start: support.excerpt_start, end: support.excerpt_end, fullTextSha256: support.full_text_sha256 }} />;
}
