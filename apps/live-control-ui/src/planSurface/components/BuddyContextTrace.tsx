import './BuddyContextTrace.css'

export interface BuddyTraceRoute {
  route_id: string
  world_id: string
  graph_revision: string
  node_id?: string | null
  anchor_id?: string | null
  evidence_ref_id?: string | null
  source_artifact_id?: string | null
  source_revision_id?: string | null
}

export interface BuddyTraceMaterial {
  item_id: string
  state: 'model_context' | 'retrieval_route'
  role?: 'user' | 'assistant' | 'source' | 'fact' | null
  text?: string | null
  route?: BuddyTraceRoute | null
}

interface Observation { sequence: number; elapsed_ms: number }
export type BuddyTraceObservation = Observation & (
  | { kind: 'context_snapshot'; stage: 'before' | 'after'; materials: BuddyTraceMaterial[] }
  | { kind: 'context_decision'; action: 'retrieved' | 'retained' | 'expanded' | 'compacted' | 'pruned'; item_ids: string[]; reason: string; policy_version: string }
  | { kind: 'graph_tool'; tool_name: string; arguments: Record<string, unknown>; result: Record<string, unknown>; outcome: 'returned' | 'denied' | 'failed'; execution_event_ids: string[]; duration_ms?: number | null }
  | { kind: 'provider_call'; provider_attempt_id?: string | null; provider: string; model: string; outcome: string; input_tokens?: number | null; output_tokens?: number | null; input_upper_bound?: number | null; input_estimator?: string | null; duration_ms?: number | null }
  | { kind: 'failure'; code: string; phase: string; message: string }
)

export interface BuddyTurnContextTrace {
  schema: 'dmb_turn_context_trace_v1'
  trace_id: string
  world_id: string
  conversation_id: string
  turn_id: string
  attempt: number
  started_at: string
  closed_at: string | null
  observations: BuddyTraceObservation[]
}

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

function sourcePassages(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(sourcePassages)
  if (!value || typeof value !== 'object') return []
  const object = value as Record<string, unknown>
  return [
    ...(typeof object.content === 'string' && object.content ? [object.content] : []),
    ...Object.entries(object).filter(([key]) => key !== 'content').flatMap(([, child]) => sourcePassages(child)),
  ]
}

function Materials({ materials }: { materials: BuddyTraceMaterial[] }) {
  const present = materials.filter(item => item.state === 'model_context')
  const routes = materials.filter(item => item.state === 'retrieval_route')
  return <div className="buddy-context-trace__context-columns">
    <section><h5>Present in model context</h5>{present.length === 0 ? <p>No captured material.</p> : present.map(item =>
      <details key={item.item_id}><summary>{item.role ?? 'Material'} · {item.item_id}</summary><p className="buddy-context-trace__prose">{item.text}</p></details>)}</section>
    <section><h5>Available through retained routes</h5>{routes.length === 0 ? <p>No captured routes.</p> : routes.map(item =>
      <details key={item.item_id}><summary>{item.route?.node_id ?? item.route?.anchor_id ?? item.item_id}</summary>
        <p>This handle can retrieve details. Its passage is not currently present in model context.</p>
        <JsonDetails label="Exact route" value={item.route} /></details>)}</section>
  </div>
}

function Event({ event }: { event: BuddyTraceObservation }) {
  switch (event.kind) {
    case 'context_snapshot': return <details><summary>Working context · {event.stage} this turn</summary><Materials materials={event.materials} /></details>
    case 'context_decision': return <><strong>{event.action}</strong><p>{event.reason}</p><JsonDetails label="Affected material and policy" value={{ items: event.item_ids, policy: event.policy_version }} /></>
    case 'graph_tool': return <details><summary>{names[event.tool_name] ?? event.tool_name} <span>{event.outcome}</span></summary>
      <JsonDetails label="Query and selectors" value={event.arguments} />
      {event.outcome === 'returned' && event.tool_name !== 'expand_graph_retrieval' && sourcePassages(event.result).map((passage, index) =>
        <details className="buddy-context-trace__source" key={index}><summary>Source passage {index + 1}</summary>
          <blockquote>{passage}</blockquote></details>)}
      <JsonDetails label="Captured result" value={event.result} />
      {event.outcome !== 'returned' && <p className="buddy-context-trace__failure">This result supplies no admitted evidence.</p>}</details>
    case 'provider_call': return <><strong>{event.model}</strong> <span>{event.outcome}</span>
      {(event.input_tokens != null || event.output_tokens != null) && <p>Provider-reported usage: {event.input_tokens == null ? 'input unavailable' : `${number(event.input_tokens)} input`} · {event.output_tokens == null ? 'output unavailable' : `${number(event.output_tokens)} output`}</p>}
      {event.input_upper_bound != null && <p className="buddy-context-trace__muted">Input ceiling: {number(event.input_upper_bound)} · conservative estimate, not actual token usage.</p>}
      {event.input_tokens == null && event.output_tokens == null && <p className="buddy-context-trace__muted">Actual token usage was not captured for this observation.</p>}</>
    case 'failure': return <><strong className="buddy-context-trace__failure">{event.message}</strong><p>{event.phase} · {event.code}</p></>
  }
}

export function BuddyContextTrace({ trace }: { trace: BuddyTurnContextTrace | null }) {
  if (!trace) return <p className="buddy-context-trace__muted">No execution trace was captured for this turn.</p>
  const last = trace.observations.at(-1)
  return <section className="buddy-context-trace" aria-label="Buddy context trace">
    <header><div><h4>How Buddy built this reply</h4><p>Observable execution · attempt {trace.attempt}</p></div>
      <span>{trace.closed_at ? 'Captured' : 'In progress'}{last ? ` · ${(last.elapsed_ms / 1000).toFixed(1)}s` : ''}</span></header>
    <ol>{trace.observations.map(event => <li key={event.sequence}>
      <span className="buddy-context-trace__time">{(event.elapsed_ms / 1000).toFixed(1)}s</span>
      <div><Event event={event} /></div></li>)}</ol>
  </section>
}
