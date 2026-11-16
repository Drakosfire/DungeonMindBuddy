import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { BuddyTraceObservation } from '../../api/buddyContextTraceTypes'
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
      {rows.map(({ step, position, y, objects }) => (
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

export function BuddyRetrievalReplay({ steps }: { steps: readonly RetrievalStep[] }) {
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const list = useRef<HTMLOListElement>(null)
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

  const { nodes, relationship_ids, total_counts, projection_status } = step.result
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
          {relationship_ids.length > 0 && <p>Relationship endpoints were unavailable in this trace.</p>}
          {nodes.length > 0 && <ul className="buddy-retrieval-replay__nodes">
            {(expanded ? nodes : nodes.slice(0, previewSize)).map(node => (
              <li key={node.node_id}><strong>{node.label}</strong> <span>{node.kind}</span></li>
            ))}
          </ul>}
          {nodes.length > previewSize && <button type="button" aria-expanded={expanded}
            onClick={() => setExpanded(value => !value)}>{expanded ? 'Show fewer objects' : `Show all ${nodes.length} recorded objects`}</button>}
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
