import './BuddyContextTrace.css'
import { useState } from 'react'
import { CapturedPrompt } from './BuddyPromptInspector'
import { traceCostEstimate } from './traceCostEstimate'
import { BuddyHistoricalSourcePassage } from './BuddyHistoricalSourcePassage'
import type { BuddyTraceMaterial, BuddyTraceObservation, BuddyTraceSourcePassage, BuddyTracePromptReference, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
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
  return <details className="buddy-context-trace__source"><summary>{passage.source_name?.trim() || 'Source name unavailable'}{passage.line_start == null ? '' : ` · lines ${passage.line_start}–${passage.line_end}`} · {passage.kind === 'source_passage_reuse' ? 'reused' : passage.outcome}</summary>
    <blockquote>{passage.text}</blockquote><p>{passage.kind === 'source_passage_reuse' ? 'Exact retained passage admitted for reuse in this attempt. Original read provenance is preserved.' : 'Exact passage read during this attempt. Historical observation; it does not grant new evidence authority.'}</p>
    <JsonDetails label="Pinned source reference" value={{ world: passage.world_id, graph_revision: passage.graph_revision, anchor: passage.anchor_id, source_artifact: passage.source_artifact_id,
      evidence: passage.evidence_ref_id, source_revision: passage.source_revision_id, content_sha256: passage.content_sha256, returned_chars: passage.returned_chars, origin_turn: passage.origin_turn_id, origin_attempt: passage.origin_attempt, origin_read_event: passage.origin_read_event_id, origin_provider_attempt: passage.origin_provider_attempt_id }} />
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

function InlinePrompt({ trace, reference }: { trace: BuddyTurnContextTrace; reference: BuddyTracePromptReference }) {
  const [open, setOpen] = useState(false)
  const previous = trace.observations.filter((item): item is BuddyTracePromptReference =>
    item.kind === 'prompt_reference' && item.sequence < reference.sequence).at(-1)
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Working context · composed input prompt · {reference.model}</summary>
    <p>Exact captured input for this model call. Capture does not prove the provider received it.</p>
    {!previous && <p>First captured input in this attempt.</p>}
    {open && <CapturedPrompt trace={trace} reference={reference} previousReference={previous} />}
  </details>
}

function ContextSnapshot({ event, trace, passages }: { event: Extract<BuddyTraceObservation, {kind: 'context_snapshot'}>; trace: BuddyTurnContextTrace; passages: BuddyTraceSourcePassage[] }) {
  const previous = trace.observations.filter((item): item is typeof event => item.kind === 'context_snapshot' && item.sequence < event.sequence).at(-1)
  const changes = previous ? [...new Set([...previous.materials.map(item => item.item_id), ...event.materials.map(item => item.item_id)])].flatMap(id => {
    const before = previous.materials.find(item => item.item_id === id)
    const now = event.materials.find(item => item.item_id === id)
    if (JSON.stringify(before) === JSON.stringify(now)) return []
    return [{ id, label: !before ? 'Added' : !now ? 'Removed' : 'Changed' }]
  }) : []
  return <details><summary>Working context · {event.stage} this turn</summary>
    <p className="buddy-context-trace__muted">Captured material inventory. When captured, the composed input includes the exact instructions and request envelope.</p>
    {previous && <div aria-label="Context changes">{changes.length ? changes.map(change =>
      <p key={change.id} className={`buddy-prompt__change--${change.label.toLowerCase()}`}>{change.label} · {change.id}</p>) : <p>No material changes since the previous snapshot.</p>}</div>}
    <Materials materials={event.materials} passages={passages.filter(passage => passage.sequence < event.sequence)} />
  </details>
}

const reasons: Record<string, string> = {
  question_relevance: 'Relevant to this question', followup_detail_needed: 'More detail needed for the follow-up', coverage_gap: 'Evidence coverage was incomplete',
  context_budget: 'Compacted for the context budget', duplicate: 'Duplicate material', superseded: 'Superseded by newer material',
  route_preserved: 'Recoverable route preserved', retrieval_sufficient: 'Retrieved evidence was sufficient', unavailable: 'Material unavailable',
}
function Event({ event, passages, trace }: { event: BuddyTraceObservation; passages: BuddyTraceSourcePassage[]; trace: BuddyTurnContextTrace }) {
  switch (event.kind) {
    case 'context_snapshot': return <ContextSnapshot event={event} trace={trace} passages={passages} />
    case 'context_decision': return <><strong>{event.action}</strong><p>{event.action === 'retained' && event.policy_version === 'conversation_routes_v1'
      ? 'Visible conversation history retained for follow-ups.'
      : reasons[event.reason_code] ?? event.reason_code}</p><JsonDetails label="Affected material and policy" value={{ items: event.item_ids, policy: event.policy_version }} /></>
    case 'graph_tool': return <details><summary>{names[event.tool_name]} · {event.request.operation} <span>{event.result.outcome}</span></summary>
      {event.request.operation === 'search' && <p>Search: {event.request.query_text}</p>}
      <JsonDetails label="Query and selectors" value={event.request} />
      <p>Graph coverage: {event.result.coverage_status}. {event.result.returned_counts.nodes} nodes · {event.result.returned_counts.relationships} relationships · {event.result.returned_counts.claims} claims · {event.result.returned_counts.evidence_refs} evidence references.</p>
      {event.result.projection_status === 'limited' && <p role="note">Trace result projection is limited: {event.result.omission_codes.join(', ')}. Total returned by retrieval: {event.result.total_counts.nodes} nodes · {event.result.total_counts.relationships} relationships · {event.result.total_counts.claims} claims · {event.result.total_counts.evidence_refs} evidence references.</p>}
      {event.result.nodes.length > 0 && <ul>{event.result.nodes.map(node => <li key={node.node_id}>{node.label} · {node.kind}</li>)}</ul>}
      <JsonDetails label="Captured result" value={event.result} />
      {['denied', 'unavailable'].includes(event.result.outcome) && <p className="buddy-context-trace__failure">This result supplies no admitted evidence.</p>}</details>
    case 'source_passage_reuse':
    case 'source_passage': return <Passage passage={event} />
    case 'provider_call': return <><strong>{event.model}</strong> <span>{event.outcome}</span>
      <p className="buddy-context-trace__muted">{event.provider_attempt_id ? `Provider call ${event.provider_attempt_id}` : 'Provider call identity was not captured.'}</p>
      {event.duration_ms != null && <p>Provider duration: {(event.duration_ms / 1000).toFixed(2)}s</p>}
      {(event.input_tokens != null || event.output_tokens != null) && <p>Provider-reported usage: {event.input_tokens == null ? 'input unavailable' : `${number(event.input_tokens)} input`} · {event.output_tokens == null ? 'output unavailable' : `${number(event.output_tokens)} output`}</p>}
      {(event.input_tokens != null || event.output_tokens != null) && (traceCostEstimate(event) == null
        ? <p className="buddy-context-trace__muted">Estimated cost unavailable · known model pricing and reported input usage required.</p>
        : <p>Estimated cost: ${traceCostEstimate(event)!.toFixed(6)} USD <span className="buddy-context-trace__muted">· list rate, not billed cost</span></p>)}
      {traceCostEstimate(event) != null && <details><summary>Cost estimate basis</summary><p>Reported input × $0.042 per million tokens; output free. Rates checked Oct 24, 2026. Excludes account discounts, taxes and gateway adjustments.</p><a href="https://ai-gateway.vercel.sh/v1/models" target="_blank" rel="noreferrer">Gateway price catalog</a> · <a href="https://docs.typesafe.ai/models" target="_blank" rel="noreferrer">TypeSafe model pricing</a></details>}
      {event.input_upper_bound != null && <p className="buddy-context-trace__muted">Input ceiling: {number(event.input_upper_bound)} · conservative estimate, not actual token usage.</p>}
      {event.input_tokens == null && event.output_tokens == null && <p className="buddy-context-trace__muted">Actual token usage was not captured for this observation.</p>}</>
    case 'prompt_reference': return <InlinePrompt key={`${trace.world_id}:${trace.conversation_id}:${trace.turn_id}:${trace.trace_id}:${trace.attempt}:${event.evidence_id}:${event.payload_sha256}`} trace={trace} reference={event} />
    case 'failure': return <><strong className="buddy-context-trace__failure">{event.phase === 'trace_capture' ? 'Trace capture incomplete' : 'Execution failed'}</strong><p>{event.phase} · {event.code}</p></>
  }
}

type TraceRow = { event: BuddyTraceObservation; observations: BuddyTraceObservation[] }

/** Presentation only: immutable lifecycle and usage observations remain inspectable. */
function traceRows(observations: BuddyTraceObservation[]): TraceRow[] {
  const rows: TraceRow[] = []
  const responses = new Map<string, number>()
  const measured = ['input_tokens', 'output_tokens', 'duration_ms'] as const
  for (const event of observations) {
    if (event.kind !== 'provider_call' || event.outcome !== 'response_received' || !event.provider_attempt_id) {
      rows.push({ event, observations: [event] })
      continue
    }
    const key = JSON.stringify([event.provider_attempt_id, event.provider, event.model])
    const index = responses.get(key)
    const row = index == null ? undefined : rows[index]
    const previous = row?.event
    if (row && previous?.kind === 'provider_call'
      && measured.every(field => previous[field] == null || event[field] == null || previous[field] === event[field])) {
      const merged = { ...previous }
      for (const field of measured) merged[field] = previous[field] ?? event[field]
      row.event = merged
      row.observations.push(event)
    } else {
      responses.set(key, rows.length)
      rows.push({ event, observations: [event] })
    }
  }
  return rows
}

export function BuddyContextTrace({ trace, ownerActive }: { trace: BuddyTurnContextTrace | null; ownerActive: boolean }) {
  if (!trace) return <p className="buddy-context-trace__muted">No execution trace was captured for this turn.</p>
  const failed = trace.terminal_status === 'failed' || trace.terminal_status === 'interrupted'
  const failures = trace.observations.filter((event): event is Extract<BuddyTraceObservation, {kind: 'failure'}> => event.kind === 'failure' && event.phase !== 'trace_capture')
  const failure = [...failures].reverse().find(event => event.diagnostic_id) ?? failures.at(-1)
  const rows = traceRows(trace.observations)
  const last = trace.observations.at(-1)
  const passages = trace.observations.filter((event): event is BuddyTraceSourcePassage => event.kind === 'source_passage' || event.kind === 'source_passage_reuse')
  return <section className="buddy-context-trace" aria-label="Buddy context trace">
    <header><div><h4>{failed ? 'Reply error report' : 'How Buddy built this reply'}</h4><p>Observable execution · attempt {trace.attempt}</p></div>
      <span>{trace.capture_status === 'incomplete' || (!ownerActive && !trace.closed_at) ? 'Incomplete capture' : trace.closed_at ? 'Captured' : 'In progress'}{last ? ` · Trace window ${(last.elapsed_ms / 1000).toFixed(1)}s` : ''}</span></header>
    {failed && <section role="alert" className="buddy-context-trace__error-report" aria-label="Reply failure">
      <h5>This attempt stopped before completing a reply.</h5>
      {failure ? <><p>{failure.code === 'build_source_name_missing' ? 'A retrieved passage has no verified source name. Buddy stopped while assembling source context.' : 'Recorded failure:'} <code>{failure.code}</code></p><p>Stage: {failure.stage ?? failure.phase}</p>
        {failure.exception_type && <p>Exception: {failure.exception_type}{failure.cause_type && failure.cause_type !== failure.exception_type ? ` · caused by ${failure.cause_type}` : ''}</p>}
        {failure.diagnostic_id ? <><p>Private diagnostic: <code>{failure.diagnostic_id}</code></p><p>Exception diagnostic details were retained privately; they are not source evidence or an accepted answer.</p></>
          : <p>No private exception diagnostic was recorded for this attempt.</p>}</>
        : <p>The specific cause was not recorded for this attempt. The timeline shows recorded activity, not an explanation of why it stopped.</p>}
      <p>Trace capture status is separate from whether the reply succeeded.</p>
    </section>}
    {trace.capture_status === 'incomplete' && <p role="alert" className="buddy-context-trace__failure">Some execution evidence is missing. {trace.capture_failure_code}</p>}
    <details open={!failed}><summary>Execution timeline</summary><ol>{rows.map(({ event, observations }) => <li key={event.sequence}>
      <span className="buddy-context-trace__time">{(event.elapsed_ms / 1000).toFixed(1)}s</span>
      <div><Event event={event} passages={passages} trace={trace} />
        {observations.length > 1 && <><p className="buddy-context-trace__muted">Same provider call · usage updated at {(observations.at(-1)!.elapsed_ms / 1000).toFixed(1)}s</p>
          <JsonDetails label="Call lifecycle and usage updates" value={observations} /></>}
      </div></li>)}</ol></details>
  </section>
}
