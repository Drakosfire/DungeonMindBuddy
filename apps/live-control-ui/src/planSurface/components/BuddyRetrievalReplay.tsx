import { GraphCircleGlyph } from '../../localWorld/worldGraphCanvas/GraphCircleGlyph'
import { graphTypeColor } from '../../localWorld/worldGraphCanvas/graphTypeStyles'
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { BuddyReplayAssertion } from './BuddyReplayAssertion'
import { BuddyHistoricalSourcePassage } from './BuddyHistoricalSourcePassage'
import type { BuddyTraceObservation, BuddyTraceSourcePassage, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import './BuddyRetrievalReplay.css'

type GraphStep = Extract<BuddyTraceObservation, { kind: 'graph_tool' }>
export type RetrievalStep = Pick<GraphStep, 'sequence' | 'revision_pin' | 'request' | 'result'>
  & Partial<Pick<GraphStep, 'scope_mode' | 'campaign_id'>>
  & { native?: true; writerEvidence?: boolean }

export function replaySteps(trace: BuddyTurnContextTrace): RetrievalStep[] {
  const graph = trace.observations.filter(event => event.kind === 'graph_tool')
  const native = (trace.native_assertion_steps ?? []).map((step): RetrievalStep => {
    const counts = { nodes: step.subject_ids.length, relationships: 0, claims: step.assertion_ids.length, evidence_refs: 0 }
    return {
      native: true, writerEvidence: step.writer_evidence, sequence: step.sequence, revision_pin: step.revision_id,
      request: { operation: 'support', target_node_id: step.subject_ids[0] ?? '' },
      result: {
        outcome: step.unavailable_count ? 'partial' : 'enough', graph_revision: step.revision_id,
        coverage_status: step.unavailable_count ? 'incomplete' : 'complete',
        projection_status: step.unavailable_count ? 'limited' : 'complete',
        nodes: step.subject_ids.map(id => ({ node_id: id, label: id, kind: 'object' })),
        claim_ids: step.assertion_ids, relationship_ids: [], evidence_ref_ids: [],
        returned_counts: counts, total_counts: { ...counts, claims: counts.claims + step.unavailable_count },
        omission_codes: [],
      },
    }
  })
  if (!native.length) return graph
  const order = (step: RetrievalStep) => step.native
    ? step.sequence : trace.graph_replay_order?.[step.sequence] ?? Number.MAX_SAFE_INTEGER
  return [...graph, ...native].sort((left, right) => order(left) - order(right))
}

const stepKey = (step: RetrievalStep) => `${step.native ? 'native' : 'graph'}:${step.sequence}`
const stepLabel = (step: RetrievalStep) => step.native ? 'Read native assertions' : labels[step.request.operation]

const labels = {
  search: 'Search the graph',
  object: 'Look up an object',
  neighborhood: 'Look up a neighborhood',
  support: 'Look up supporting evidence',
  observations: 'Read observations',
} satisfies Record<RetrievalStep['request']['operation'], string>

const previewSize = 12
const assertionPageSize = 20

function RecordedAssertions({ trace, step }: { trace: BuddyTurnContextTrace; step: RetrievalStep }) {
  const [page, setPage] = useState(0)
  const assertions = step.result.claim_ids
  const start = page * assertionPageSize
  const end = Math.min(start + assertionPageSize, assertions.length)
  return <details>
    <summary>Recorded assertions ({assertions.length})</summary>
    {assertions.length > assertionPageSize && <label>
      Assertion range{' '}
      <select value={page} onChange={event => setPage(Number(event.target.value))}>
        {Array.from({ length: Math.ceil(assertions.length / assertionPageSize) }, (_, index) =>
          <option key={index} value={index}>
            {index * assertionPageSize + 1}–{Math.min((index + 1) * assertionPageSize, assertions.length)}
          </option>)}
      </select>
    </label>}
    {assertions.slice(start, end).map(assertionId => <BuddyReplayAssertion
      key={assertionId} trace={trace} step={step} assertionId={assertionId} />)}
  </details>
}

function displayNodeName(node: RetrievalStep['result']['nodes'][number]) {
  return /^(ent|entity|asrt):/i.test(node.label) ? 'Unnamed object' : node.label
}

function layoutTrail(steps: readonly RetrievalStep[]) {
  const objects = new Map<string, { node: RetrievalStep['result']['nodes'][number]; visits: number[]; x: number; y: number }>()
  for (const [position, step] of steps.entries()) {
    for (const node of step.result.nodes) {
      const existing = objects.get(node.node_id)
      if (existing) {
        existing.visits.push(position)
      } else {
        objects.set(node.node_id, { node, visits: [position], x: 0, y: 0 })
      }
    }
  }
  const columns = Math.max(1, Math.ceil(Math.sqrt(objects.size * 1.65)))
  let offset = 0
  for (const object of objects.values()) {
    object.x = 44 + (offset % columns) * 88
    object.y = 44 + Math.floor(offset / columns) * 88
    offset += 1
  }
  return { objects, width: columns * 88, height: Math.max(88, Math.ceil(objects.size / columns) * 88) }
}

function keepStepVisible(pane: HTMLElement | null) {
  const active = pane?.querySelector('[data-replay-active]')
  if (!pane || !active) return
  const frame = pane.getBoundingClientRect()
  const row = active.getBoundingClientRect()
  if (row.top < frame.top) pane.scrollTop += row.top - frame.top
  else if (row.bottom > frame.bottom) pane.scrollTop += row.bottom - frame.bottom
}

const Trail = memo(function Trail({ layout, active, wide, select }: {
  layout: ReturnType<typeof layoutTrail>
  active: number
  wide: boolean
  select: (position: number) => void
}) {
  return <div className="buddy-retrieval-replay__canvas">
    <svg viewBox={`0 0 ${layout.width} ${layout.height}`} role="group" aria-label="Recorded graph nodes">
      {[...layout.objects.values()].map(({ node, visits, x, y }) => {
        const current = visits.includes(active)
        const position = visits[0]
        const name = displayNodeName(node)
        const state = current ? 'current' : position < active ? 'visited' : 'upcoming'
        return <g key={node.node_id} transform={`translate(${x} ${y})`}
          data-visit={state} role="button" tabIndex={wide || current ? 0 : -1}
          aria-label={name} aria-pressed={current}
          onClick={() => select(position)} onKeyDown={event => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              select(position)
            }
          }}>
          <title>{name}</title>
          <g style={{ color: graphTypeColor(node.kind) }}>
            <GraphCircleGlyph center={0} radius={24} kind={node.kind} name="" showLabels={false} fullCorpus />
          </g>
          {(wide || current) && <text className="buddy-retrieval-replay__label" y="39" textAnchor="middle">
            {name.length > 14 ? `${name.slice(0, 13)}…` : name}
          </text>}
        </g>
      })}
    </svg>
    {layout.objects.size === 0 && <p>This lookup retained no graph nodes.</p>}
  </div>
})


function indexPassages(trace: BuddyTurnContextTrace | undefined) {
  const index = new Map<string, BuddyTraceSourcePassage[]>()
  for (const event of trace?.observations ?? []) {
    if (event.kind !== 'source_passage' || event.world_id !== trace?.world_id) continue
    const key = JSON.stringify([event.graph_revision, event.evidence_ref_id])
    const matches = index.get(key)
    if (matches) matches.push(event)
    else index.set(key, [event])
  }
  return index
}

export function BuddyRetrievalReplay({ steps, trace }: { steps: readonly RetrievalStep[]; trace?: BuddyTurnContextTrace }) {
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [wide, setWide] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const list = useRef<HTMLOListElement>(null)
  const passagesByEvidence = useMemo(() => indexPassages(trace), [trace])
  const writerObservations = useMemo(() => new Set(trace?.writer_evidence_sequences ?? []), [trace?.writer_evidence_sequences])
  const rows = useMemo(() => layoutTrail(steps), [steps])
  const step = steps[index]
  const last = index + 1 >= steps.length

  useEffect(() => {
    if (!playing || last) return
    const timer = window.setTimeout(() => {
      setExpanded(false)
      setIndex(index + 1)
      if (index + 2 === steps.length) setPlaying(false)
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [index, last, playing, steps.length])

  useEffect(() => keepStepVisible(list.current), [index, steps, wide])

  const select = useCallback((next: number) => {
    setPlaying(false)
    setExpanded(false)
    setIndex(next)
  }, [])

  if (!step) return <p>No graph lookup steps were retained for this attempt.</p>

  const { nodes, relationship_ids, relationships = [], total_counts, projection_status, evidence_ref_ids } = step.result
  const passages = evidence_ref_ids.flatMap(id => passagesByEvidence.get(JSON.stringify([step.revision_pin, id])) ?? [])
  return (
    <section className="buddy-retrieval-replay" aria-label="Retrieval replay">
      <div className="buddy-retrieval-replay__controls">
        <button type="button" disabled={playing || steps.length < 2} onClick={() => {
          if (last) select(0)
          setPlaying(true)
        }}>Play</button>
        <button type="button" disabled={!playing} onClick={() => setPlaying(false)}>Pause</button>
        <button type="button" disabled={index === 0} onClick={() => select(index - 1)}>Previous step</button>
        <button type="button" disabled={last} onClick={() => select(index + 1)}>Next step</button>
        <button type="button" aria-expanded={wide} onClick={() => setWide(value => !value)}>{wide ? 'Collapse' : 'Expand'}</button>
        <span role="status">Step {index + 1} of {steps.length}</span>
      </div>
      {wide && trace && trace.writer_evidence_sequences == null && !steps.some(item => item.writerEvidence) && <p>Writer evidence was unavailable for this attempt.</p>}
      <p className="buddy-retrieval-replay__caption">
        {nodes.length === 1 ? displayNodeName(nodes[0]) : nodes.length ? `${nodes.length} objects` : stepLabel(step)}
      </p>
      <div data-wide={wide}>
        <Trail layout={rows} active={index} wide={wide} select={select} />
      </div>
      <div className="buddy-retrieval-replay__workspace" hidden={!wide}>
        <section aria-label="Recorded lookup results">
          <h5>{stepLabel(step)}</h5>
          {(step.native ? step.writerEvidence : writerObservations.has(step.sequence)) && <p><strong>Evidence sent to the answer writer</strong></p>}
          <p>{total_counts.nodes} objects · {total_counts.relationships} relationships · {total_counts.claims} claims</p>
          {projection_status === 'limited' && <p>Some results were omitted from the saved trace.</p>}
          {relationship_ids.length > relationships.length && <p>Some relationship endpoints were unavailable in this trace.</p>}
          {relationships.length > 0 && <details>
            <summary>Returned relationships ({relationships.length})</summary>
            <ul>{relationships.map(relationship => <li key={relationship.relationship_id}>
              {nodes.find(node => node.node_id === relationship.source_node_id)?.label ?? "Unnamed object"}
              {' → '}
              {nodes.find(node => node.node_id === relationship.target_node_id)?.label ?? "Unnamed object"}
            </li>)}</ul>
          </details>}
          {nodes.length > 0 && <ul className="buddy-retrieval-replay__nodes">
            {(expanded ? nodes : nodes.slice(0, previewSize)).map(node => (
              <li key={node.node_id}><strong>{displayNodeName(node)}</strong> <span>{node.kind}</span></li>
            ))}
          </ul>}
          {nodes.length > previewSize && <button type="button" aria-expanded={expanded}
            onClick={() => setExpanded(value => !value)}>{expanded ? 'Show fewer objects' : `Show all ${nodes.length} recorded objects`}</button>}
          {trace && step.result.claim_ids.length > 0 &&
            <RecordedAssertions key={stepKey(step)} trace={trace} step={step} />}
          {trace && passages.length > 0 && <section aria-label="Captured source excerpts">
            {passages.map(passage => <BuddyHistoricalSourcePassage key={`${passage.source_read_event_id}:${passage.source_read_id}`}
              graphRevision={step.revision_pin} label={`Open excerpt · ${passage.source_name?.trim() || 'Captured source'}${writerObservations.has(passage.sequence) ? ' · Writer evidence' : ''}`}
              reference={{
                schema: 'dmb_trace_historical_source_ref_v1', world_id: trace.world_id,
                conversation_id: trace.conversation_id, turn_id: trace.turn_id, attempt: trace.attempt,
                trace_id: trace.trace_id, source_read_event_id: passage.source_read_event_id,
                source_read_id: passage.source_read_id, content_sha256: passage.content_sha256,
              }} />)}
          </section>}
          {trace && evidence_ref_ids.length > 0 && passages.length === 0 && <p>No matching source excerpt was captured for this lookup.</p>}
        </section>
        <ol ref={list} className="buddy-retrieval-replay__steps" aria-label="Recorded retrieval steps">
          {steps.map((item, position) => (
            <li key={stepKey(item)} data-replay-active={position === index ? true : undefined}><button type="button" aria-current={position === index ? 'step' : undefined}
              onClick={() => select(position)}>{stepLabel(item)} · {item.result.outcome}
              {(item.native ? item.writerEvidence : writerObservations.has(item.sequence)) && <strong> · Writer evidence</strong>}</button></li>
          ))}
        </ol>
      </div>
    </section>
  )
}
