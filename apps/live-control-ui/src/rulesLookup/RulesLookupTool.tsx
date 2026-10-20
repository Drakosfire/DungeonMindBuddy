import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, getNativeGraphAccessGeneration, getRulesCatalog, getRulesPassage, queryRulesEvidence } from '../api/liveApi';
import type { RulesCatalog, RulesHit, RulesLookupPacket, RulesPassage } from '../api/rulesLookupTypes';

const digest = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export function rulesPageLabel(item: { printed_page: number | null; pdf_page_index: number }) {
  return item.printed_page === null ? `PDF page ${item.pdf_page_index + 1}` : `Page ${item.printed_page}`;
}
function validatePacket(packet: RulesLookupPacket, corpus: string) {
  if (packet.schema !== 'dmb_rules_lookup_packet_v1' || packet.corpus !== corpus || !digest(packet.query_id)
    || packet.coverage_status !== 'limited' || !Array.isArray(packet.hits) || packet.hits.length > 4
    || !['evidence', 'no_evidence'].includes(packet.status) || (packet.status === 'evidence') !== (packet.hits.length > 0)
    || typeof packet.coverage !== 'string' || packet.coverage.length > 1000
    || new Set(packet.hits.map(hit => hit.citation_id)).size !== packet.hits.length
    || packet.hits.some(hit => hit.corpus !== corpus || hit.ruleset_id !== packet.ruleset_id || !digest(hit.citation_id)
      || !digest(hit.unit_id) || !digest(hit.text_sha256) || !digest(hit.source_sha256) || !digest(hit.page_fingerprint)
      || typeof hit.section !== 'string' || hit.section.length > 500 || typeof hit.source_title !== 'string' || hit.source_title.length > 500
      || !Number.isSafeInteger(hit.pdf_page_index) || hit.pdf_page_index < 0
      || (hit.printed_page !== null && (!Number.isSafeInteger(hit.printed_page) || hit.printed_page < 1))
      || typeof hit.source_uri !== 'string' || !/^https:\/\/[^\s]+$/.test(hit.source_uri) || hit.source_uri.length > 1000
      || hit.excerpt_start !== 0 || typeof hit.excerpt !== 'string' || hit.excerpt_end !== hit.excerpt.length || typeof hit.excerpt_complete !== 'boolean'
      || hit.excerpt.length > 1400)) {
    throw new Error('The rules evidence did not match this source.');
  }
}
export default function RulesLookupTool() {
  const [catalog, setCatalog] = useState<RulesCatalog | null>(null);
  const [corpus, setCorpus] = useState('');
  const [question, setQuestion] = useState('');
  const [packet, setPacket] = useState<RulesLookupPacket | null>(null);
  const [passage, setPassage] = useState<RulesPassage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const accessEpoch = useRef(getNativeGraphAccessGeneration());
  function retire() { generation.current++; request.current?.abort(); request.current = null; }
  function begin() {
    retire(); const controller = new AbortController(); request.current = controller; setBusy(true); setError(null);
    const epoch = getNativeGraphAccessGeneration(), current = generation.current;
    return { controller, current: () => !controller.signal.aborted && generation.current === current && epoch === getNativeGraphAccessGeneration() };
  }
  useEffect(() => {
    const action = begin();
    void getRulesCatalog(action.controller.signal).then(value => {
      if (!action.current()) return;
      if (value.schema !== 'dmb_rules_catalog_v1' || !Array.isArray(value.sources) || value.sources.length > 8
        || new Set(value.sources.map(item => item.corpus)).size !== value.sources.length
        || value.sources.some(item => !digest(item.corpus) || typeof item.available !== 'boolean'
          || (item.available && (typeof item.title !== 'string' || item.title.length > 500
            || typeof item.coverage !== 'string' || item.coverage.length > 1000
            || typeof item.ruleset_id !== 'string' || !/^[a-z0-9_]{1,80}$/.test(item.ruleset_id)
            || !Number.isSafeInteger(item.unit_count) || item.unit_count! < 1 || item.unit_count! > 10000)))) throw new Error('The rules source catalog is invalid.');
      setCatalog(value); setCorpus(value.sources.find(item => item.available)?.corpus ?? '');
    }).catch(reason => { if (action.current()) setError(reason instanceof Error ? reason.message : 'Rules sources unavailable.'); })
      .finally(() => { if (action.current()) setBusy(false); });
    return retire;
  }, [retry]);
  // Access loss retires visible private evidence immediately, not only on the next request.
  useLayoutEffect(() => {
    const changed = () => { const next = getNativeGraphAccessGeneration(); if (next === accessEpoch.current) return; accessEpoch.current = next; retire(); setCatalog(null); setCorpus(''); setPacket(null); setPassage(null); setBusy(false); setError('Access changed. Reload rules sources.'); };
    window.addEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, changed);
    changed();
    return () => window.removeEventListener(NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT, changed);
  }, []);
  async function search() {
    const action = begin(); setPacket(null); setPassage(null);
    try {
      const value = await queryRulesEvidence(corpus, question.trim(), action.controller.signal);
      if (!action.current()) return;
      validatePacket(value, corpus); setPacket(value);
    } catch (reason) { if (action.current()) setError(reason instanceof Error ? reason.message : 'Rules lookup failed.'); }
    finally { if (action.current()) setBusy(false); }
  }
  async function inspect(hit: RulesHit) {
    const action = begin(); setPassage(null);
    try {
      const value = await getRulesPassage(hit.corpus, hit.citation_id, action.controller.signal);
      if (!action.current()) return;
      if (value.schema !== 'dmb_rules_passage_v1' || value.corpus !== hit.corpus || value.citation_id !== hit.citation_id
        || ['ruleset_id','unit_id','text_sha256','section','source_title','source_uri','source_sha256','page_fingerprint','pdf_page_index','printed_page']
          .some(key => value[key as keyof RulesPassage] !== hit[key as keyof RulesHit])
        || typeof value.attribution !== 'string' || value.attribution.length > 2000 || typeof value.text !== 'string' || value.text.length > 8192)
        throw new Error('This exact rules passage could not be verified.');
      const actual = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value.text))))
        .map(byte => byte.toString(16).padStart(2, '0')).join('');
      if (!action.current()) return;
      if (actual !== hit.text_sha256) throw new Error('This exact rules passage could not be verified.');
      setPassage(value);
    } catch (reason) { if (action.current()) setError(reason instanceof Error ? reason.message : 'Rules passage unavailable.'); }
    finally { if (action.current()) setBusy(false); }
  }
  const selected = catalog?.sources.find(item => item.corpus === corpus);
  return <section aria-label="Rules lookup">
    <h2>Rules Lookup</h2>
    <p>Find source text to support a ruling.</p>
    {error && <p role="alert">{error}</p>}
    {!catalog && !busy && <button type="button" onClick={() => setRetry(value => value + 1)}>Reload rules sources</button>}
    {catalog && <>
      <label>Rules source <select value={corpus} onChange={event => { retire(); setCorpus(event.target.value); setPacket(null); setPassage(null); setError(null); setBusy(false); }}>
        {!corpus && <option value="">No available sources</option>}
        {catalog.sources.map(item => <option key={item.corpus} value={item.corpus} disabled={!item.available}>{item.title ?? 'Source unavailable'}</option>)}
      </select></label>
      <p>{selected?.coverage ?? 'No rules source is available.'}</p>
      <form onSubmit={event => { event.preventDefault(); if (corpus && question.trim() && !busy) void search(); }}>
        <label>Rules question <textarea value={question} maxLength={800} onChange={event => { retire(); setQuestion(event.target.value); setPacket(null); setPassage(null); setError(null); setBusy(false); }} /></label>
        <button type="submit" disabled={busy || !corpus || !question.trim()}>Look up rules</button>
      </form>
    </>}
    {busy && <p role="status">Reading rules evidence…</p>}
    {packet?.status === 'no_evidence' && <p role="status">No matching evidence in this source set. This does not establish that no rule exists.</p>}
    {packet?.hits.map(hit => <article key={hit.citation_id}>
      <h3>{hit.section}</h3><p>{hit.source_title} · {rulesPageLabel(hit)}</p>
      <blockquote style={{ whiteSpace: 'pre-wrap' }}>{hit.excerpt}</blockquote>
      {!hit.excerpt_complete && <p>Excerpt; open the passage for full text.</p>}
      <button type="button" disabled={busy} onClick={() => void inspect(hit)}>Inspect cited passage</button>
    </article>)}
    {passage && <section aria-label="Cited rules passage"><h3>{passage.section}</h3>
      <p>{passage.source_title} · {rulesPageLabel(passage)}</p>
      <p style={{ whiteSpace: 'pre-wrap' }}>{passage.text}</p>
      <p>{passage.attribution}</p>
      <details><summary>Source identity</summary><p>Source: {passage.source_uri}</p><p>Corpus: {passage.corpus}</p><p>Passage SHA-256: {passage.text_sha256}</p></details>
      <button type="button" onClick={() => setPassage(null)}>Close cited passage</button>
    </section>}
  </section>;
}
