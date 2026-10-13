import './BuddyContextTrace.css'
import { BuddyHistoricalSourcePassage } from './BuddyHistoricalSourcePassage'
import type { BuddyTraceMaterial, BuddyTraceObservation, BuddyTraceSourcePassage, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
export type { BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'

const names: Record<string, string> = {
  expand_graph_retrieval: 'Explore World graph',
  read_graph_source: 'Read supporting source',
  read_related_recap_context: 'Read surrounding recap',
}
const number = (value: number) => value.toLocaleString()

function JsonDetails({ label, value }: { label: string; value: unknown }) {
  return <details className="buddy-context-trace__payload"><summary>{label}</summary>
    <pre>{JSON.stringify(value, null, 2)}</pre></details>
}

function Passage({ passage }: { passage: BuddyTraceSourcePassage }) {
  return <details className="buddy-context-trace__source"><summary>{passage.source_artifact_id}{passage.line_start == null ? '' : ` · lines ${passage.line_start}–${passage.line_end}`} · {passage.outcome}</summary>
    <blockquote>{passage.text}</blockquote><p>Exact passage read during this attempt. Historical observation; it does not grant new evidence authority.</p>
    <JsonDetails label="Pinned source reference" value={{ world: passage.world_id, graph_revision: passage.graph_revision, anchor: passage.anchor_id,
      evidence: passage.evidence_ref_id, source_revision: passage.source_revision_id, content_sha256: passage.content_sha256, returned_chars: passage.returned_chars }} />
  </details>
}

function Materials({ materials, passages }: { materials: BuddyTraceMaterial[]; passages: BuddyTraceSourcePassage[] }) {
  const present = materials.filter(item => item.state === 'model_context')
  const routes = materials.filter(item => item.state === 'retrieval_route')
  return <div className="buddy-context-trace__context-columns">
    <section><h5>Present in model context</h5>{present.length === 0 ? <p>No captured material.</p> : present.map(item =>
      <details key={item.item_id}><summary>{item.role} · {item.item_id}</summary>{item.role === 'source'
        ? item.historical_source_reads?.length
          ? item.historical_source_reads.map(reference => <BuddyHistoricalSourcePassage key={`${reference.trace_id}:${reference.source_read_id}`} reference={reference} />)
          : capturedMaterials(item, passages).length > 0
          ? capturedMaterials(item, passages).map(passage => <Passage key={passage.source_read_id} passage={passage} />)
          : <p>Referenced source passage was not captured in this attempt.</p>
        : <p className="buddy-context-trace__prose">{item.text}</p>}</details>)}</section>
    <section><h5>Available through retained routes</h5>{routes.length === 0 ? <p>No captured routes.</p> : routes.map(item =>
      <details key={item.item_id}><summary>{item.route?.node_id ?? item.route?.anchor_id ?? item.item_id}</summary>
        <p>This handle can retrieve details. Its passage is not currently present in model context.</p>
        <JsonDetails label="Exact route" value={item.route} /></details>)}</section>
  </div>
}

function capturedMaterials(material: BuddyTraceMaterial, passages: BuddyTraceSourcePassage[]): BuddyTraceSourcePassage[] {
  if (!material.source_reads?.length) return []
  const matches = material.source_reads.map(reference => passages.filter(passage =>
    passage.source_read_event_id === material.source_read_event_id
    && passage.source_read_id === reference.source_read_id
    && passage.content_sha256 === reference.content_sha256))
  return matches.every(items => items.length === 1) ? matches.flat() : []
}

const reasons: Record<string, string> = {
  question_relevance: 'Relevant to this question', followup_detail_needed: 'More detail needed for the follow-up', coverage_gap: 'Evidence coverage was incomplete',
  context_budget: 'Compacted for the context budget', duplicate: 'Duplicate material', superseded: 'Superseded by newer material',
  route_preserved: 'Recoverable route preserved', retrieval_sufficient: 'Retrieved evidence was sufficient', unavailable: 'Material unavailable',
}
function Event({ event, passages }: { event: BuddyTraceObservation; passages: BuddyTraceSourcePassage[] }) {
  switch (event.kind) {
    case 'context_snapshot': return <details><summary>Working context · {event.stage} this turn</summary><Materials materials={event.materials} passages={passages.filter(passage => passage.sequence < event.sequence)} /></details>
    case 'context_decision': return <><strong>{event.action}</strong><p>{reasons[event.reason_code] ?? event.reason_code}</p><JsonDetails label="Affected material and policy" value={{ items: event.item_ids, policy: event.policy_version }} /></>
    case 'graph_tool': return <details><summary>{names[event.tool_name]} · {event.request.operation} <span>{event.result.outcome}</span></summary>
      {event.request.operation === 'search' && <p>Search: {event.request.query_text}</p>}
      <JsonDetails label="Query and selectors" value={event.request} />
      <p>Graph coverage: {event.result.coverage_status}. {event.result.returned_counts.nodes} nodes · {event.result.returned_counts.relationships} relationships · {event.result.returned_counts.claims} claims · {event.result.returned_counts.evidence_refs} evidence references.</p>
      {event.result.projection_status === 'limited' && <p role="note">Trace result projection is limited: {event.result.omission_codes.join(', ')}. Total returned by retrieval: {event.result.total_counts.nodes} nodes · {event.result.total_counts.relationships} relationships · {event.result.total_counts.claims} claims · {event.result.total_counts.evidence_refs} evidence references.</p>}
      {event.result.nodes.length > 0 && <ul>{event.result.nodes.map(node => <li key={node.node_id}>{node.label} · {node.kind}</li>)}</ul>}
      <JsonDetails label="Captured result" value={event.result} />
      {['denied', 'unavailable'].includes(event.result.outcome) && <p className="buddy-context-trace__failure">This result supplies no admitted evidence.</p>}</details>
    case 'source_passage': return <Passage passage={event} />
    case 'provider_call': return <><strong>{event.model}</strong> <span>{event.outcome}</span>
      {(event.input_tokens != null || event.output_tokens != null) && <p>Provider-reported usage: {event.input_tokens == null ? 'input unavailable' : `${number(event.input_tokens)} input`} · {event.output_tokens == null ? 'output unavailable' : `${number(event.output_tokens)} output`}</p>}
      {event.input_upper_bound != null && <p className="buddy-context-trace__muted">Input ceiling: {number(event.input_upper_bound)} · conservative estimate, not actual token usage.</p>}
      {event.input_tokens == null && event.output_tokens == null && <p className="buddy-context-trace__muted">Actual token usage was not captured for this observation.</p>}</>
    case 'failure': return <><strong className="buddy-context-trace__failure">Execution failed</strong><p>{event.phase} · {event.code}</p></>
  }
}

export function BuddyContextTrace({ trace }: { trace: BuddyTurnContextTrace | null }) {
  if (!trace) return <p className="buddy-context-trace__muted">No execution trace was captured for this turn.</p>
  const last = trace.observations.at(-1)
  const passages = trace.observations.filter((event): event is BuddyTraceSourcePassage => event.kind === 'source_passage')
  return <section className="buddy-context-trace" aria-label="Buddy context trace">
    <header><div><h4>How Buddy built this reply</h4><p>Observable execution · attempt {trace.attempt}</p></div>
      <span>{trace.capture_status === 'incomplete' ? 'Incomplete capture' : trace.closed_at ? 'Captured' : 'In progress'}{last ? ` · ${(last.elapsed_ms / 1000).toFixed(1)}s` : ''}</span></header>
    {trace.capture_status === 'incomplete' && <p role="alert" className="buddy-context-trace__failure">Some execution evidence is missing. {trace.capture_failure_code}</p>}
    <ol>{trace.observations.map(event => <li key={event.sequence}>
      <span className="buddy-context-trace__time">{(event.elapsed_ms / 1000).toFixed(1)}s</span>
      <div><Event event={event} passages={passages} /></div></li>)}</ol>
  </section>
}
