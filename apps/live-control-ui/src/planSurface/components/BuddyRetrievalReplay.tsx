import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { BuddyReplayAssertion } from './BuddyReplayAssertion'
import { BuddyHistoricalSourcePassage } from './BuddyHistoricalSourcePassage'
import type { BuddyTraceObservation, BuddyTraceSourcePassage, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import './BuddyRetrievalReplay.css'

export type RetrievalStep = Extract<BuddyTraceObservation, { kind: 'graph_tool' }>

const labels = {
  search: 'Search the graph',
  object: 'Look up an object',
  neighborhood: 'Look up a neighborhood',
  support: 'Look up supporting evidence',
  observations: 'Read observations',
} satisfies Record<RetrievalStep['request']['operation'], string>

const previewSize = 12

function layoutTrail(steps: readonly RetrievalStep[]) {
  return steps.map((step, position) => ({
    step,
    position,
    y: position * 84 + 34,
    objects: step.result.nodes.slice(0, 3),
    relationships: step.result.relationships ?? [],
  }))
}

function keepStepVisible(pane: HTMLElement | null) {
  const active = pane?.querySelector('[data-replay-active]')
  if (!pane || !active) return
  const frame = pane.getBoundingClientRect()
  const row = active.getBoundingClientRect()
  if (row.top < frame.top) pane.scrollTop += row.top - frame.top
  else if (row.bottom > frame.bottom) pane.scrollTop += row.bottom - frame.bottom
}

const Trail = memo(function Trail({ rows, active, select }: {
  rows: ReturnType<typeof layoutTrail>
  active: number
  select: (position: number) => void
}) {
  const pane = useRef<HTMLDivElement>(null)
  useEffect(() => keepStepVisible(pane.current), [active, rows])
  return <div ref={pane} className="buddy-retrieval-replay__trail" aria-label="Recorded lookup trail">
    <svg viewBox={`0 0 580 ${rows.length * 84}`} role="group" aria-label="Operations and returned objects">
      {rows.map(({ step, position, y, objects, relationships }) => (
        <g key={step.sequence} className={active === position ? 'is-current' : undefined}
          data-replay-active={active === position ? true : undefined}>
          {objects.map((node, objectIndex) => {
            const x = 230 + objectIndex * 112
            return <g key={node.node_id}>
              <path d={`M 204 ${y} H ${x} V ${y + 17}`} />
              <rect x={x} y={y + 16} width="104" height="28" rx="7" />
              <title>{node.label}</title>
              <text x={x + 6} y={y + 34}>{node.label.length > 13 ? node.label.slice(0, 12) + '…' : node.label}</text>
            </g>
          })}
          {relationships.map(relationship => {
            const source = objects.findIndex(node => node.node_id === relationship.source_node_id)
            const target = objects.findIndex(node => node.node_id === relationship.target_node_id)
            if (source < 0 || target < 0 || source === target) return null
            const x1 = 282 + source * 112
            const x2 = 282 + target * 112
            const arrow = x2 - Math.sign(x2 - x1) * 5
            return <g key={relationship.relationship_id} className="buddy-retrieval-replay__relationship">
              <title>{`${objects[source].label} → ${objects[target].label}`}</title>
              <path d={`M ${x1} ${y + 44} V ${y + 47} H ${x2} V ${y + 44} M ${arrow} ${y + 42} L ${x2} ${y + 44} L ${arrow} ${y + 47}`} />
            </g>
          })}
          <g role="button" tabIndex={0} aria-pressed={active === position}
            aria-label={`Step ${position + 1}, ${labels[step.request.operation]}`}
            onClick={() => select(position)} onKeyDown={event => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                select(position)
              }
            }}>
            <rect x="8" y={y - 15} width="196" height="30" rx="7" />
            <text x="16" y={y + 4}>{position + 1}. {labels[step.request.operation]}</text>
          </g>
        </g>
      ))}
    </svg>
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
  const [expanded, setExpanded] = useState(false)
  const list = useRef<HTMLOListElement>(null)
  const passagesByEvidence = useMemo(() => indexPassages(trace), [trace])
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

  useEffect(() => keepStepVisible(list.current), [index, steps])

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
        <span role="status">Step {index + 1} of {steps.length}</span>
      </div>
      <div className="buddy-retrieval-replay__workspace">
        <section aria-label="Recorded lookup results">
          <Trail rows={rows} active={index} select={select} />
          <h5>{labels[step.request.operation]}</h5>
          <p>{total_counts.nodes} objects · {total_counts.relationships} relationships · {total_counts.claims} claims</p>
          {projection_status === 'limited' && <p>Some results were omitted from the saved trace.</p>}
          {relationship_ids.length > relationships.length && <p>Some relationship endpoints were unavailable in this trace.</p>}
          {relationships.length > 0 && <details>
            <summary>Returned relationships ({relationships.length})</summary>
            <ul>{relationships.map(relationship => <li key={relationship.relationship_id}>
              {nodes.find(node => node.node_id === relationship.source_node_id)?.label ?? relationship.source_node_id}
              {' → '}
              {nodes.find(node => node.node_id === relationship.target_node_id)?.label ?? relationship.target_node_id}
            </li>)}</ul>
          </details>}
          {nodes.length > 0 && <ul className="buddy-retrieval-replay__nodes">
            {(expanded ? nodes : nodes.slice(0, previewSize)).map(node => (
              <li key={node.node_id}><strong>{node.label}</strong> <span>{node.kind}</span></li>
            ))}
          </ul>}
          {nodes.length > previewSize && <button type="button" aria-expanded={expanded}
            onClick={() => setExpanded(value => !value)}>{expanded ? 'Show fewer objects' : `Show all ${nodes.length} recorded objects`}</button>}
          {trace && step.result.claim_ids.length > 0 && <details>
            <summary>Recorded assertions ({step.result.claim_ids.length})</summary>
            {step.result.claim_ids.map(assertionId => <BuddyReplayAssertion
              key={`${step.sequence}:${assertionId}`} trace={trace} step={step} assertionId={assertionId} />)}
          </details>}
          {trace && passages.length > 0 && <section aria-label="Captured source excerpts">
            {passages.map(passage => <BuddyHistoricalSourcePassage key={`${passage.source_read_event_id}:${passage.source_read_id}`}
              graphRevision={step.revision_pin} label={`Open excerpt · ${passage.source_name?.trim() || 'Captured source'}`}
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
            <li key={item.sequence} data-replay-active={position === index ? true : undefined}><button type="button" aria-current={position === index ? 'step' : undefined}
              onClick={() => select(position)}>{labels[item.request.operation]} · {item.result.outcome}</button></li>
          ))}
        </ol>
      </div>
    </section>
  )
}
