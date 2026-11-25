import { displayClassification } from "../../nativeGraphDemo/nativeGraphPresentation"
import { ReplayNodeFinding } from "./ReplayNodeFinding"
import { NodeOverview } from "../../graphLens/NodeOverview"
import { GraphNodeViewer } from "../../graphLens/GraphNodeViewer"
import { getWorldAgentReplayIdentities } from '../../api/liveApi'
import { GraphCircleGlyph } from '../../localWorld/worldGraphCanvas/GraphCircleGlyph'
import { graphTypeColor } from '../../localWorld/worldGraphCanvas/graphTypeStyles'
import { memo, useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { BuddyReplayAssertion } from './BuddyReplayAssertion'
import { BuddyHistoricalSourcePassage } from './BuddyHistoricalSourcePassage'
import type { BuddyTraceObservation, BuddyTraceSourcePassage, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import './BuddyRetrievalReplay.css'

type GraphStep = Extract<BuddyTraceObservation, { kind: 'graph_tool' }>
export type RetrievalStep = Pick<GraphStep, 'sequence' | 'revision_pin' | 'request' | 'result'>
  & Partial<Pick<GraphStep, 'scope_mode' | 'campaign_id'>>
  & {
    native?: true
    assertionIdsBySubject?: Readonly<Record<string, readonly string[]>>
    writerEvidence?: boolean
    frame?: string
    hop?: { relationship_id: string; from_node_id: string; to_node_id: string }
    pruning?: { reason: string; total: number; ids: string[] }
  }

export function replaySteps(trace: BuddyTurnContextTrace): RetrievalStep[] {
  const graph = trace.observations.filter(event => event.kind === 'graph_tool')
  const native = (trace.native_assertion_steps ?? []).map((step): RetrievalStep => {
    const counts = { nodes: step.subject_ids.length, relationships: 0, claims: step.assertion_ids.length, evidence_refs: 0 }
    return {
      native: true, assertionIdsBySubject: step.assertion_ids_by_subject, writerEvidence: step.writer_evidence, sequence: step.sequence, revision_pin: step.revision_id,
      request: { operation: 'support', target_node_id: step.subject_ids[0] ?? '' },
      result: {
        outcome: step.unavailable_count ? 'partial' : 'enough', graph_revision: step.revision_id,
        coverage_status: step.unavailable_count ? 'incomplete' : 'complete',
        projection_status: step.unavailable_count ? 'limited' : 'complete',
        nodes: step.subject_ids.map(id => ({
          node_id: id, label: step.subject_labels?.[id] ?? 'Unnamed object', kind: step.subject_kinds?.[id] ?? 'object',
        })),
        claim_ids: step.assertion_ids, relationship_ids: [], evidence_ref_ids: [],
        returned_counts: counts, total_counts: { ...counts, claims: counts.claims + step.unavailable_count },
        omission_codes: [],
      },
    }
  })
  const exclusions = (trace.retrieval_exclusion_steps ?? []).filter(step => step.total > 0)
    .map((step): RetrievalStep => {
      const nodes = step.candidates.map(candidate => ({
        node_id: candidate.handle.startsWith('node:') ? candidate.handle.slice(5) : candidate.handle,
        label: candidate.label, kind: candidate.kind,
      }))
      const counts = { nodes: nodes.length, relationships: 0, claims: 0, evidence_refs: 0 }
      return {
        sequence: step.sequence, frame: 'Candidate pruning', revision_pin: '',
        request: { operation: 'search', query_text: '', seed_node_ids: [] },
        pruning: { reason: 'JEV excluded this candidate during relevance selection', total: step.total, ids: nodes.map(node => node.node_id) },
        result: {
          outcome: 'enough', graph_revision: '', coverage_status: 'complete', projection_status: 'complete',
          nodes, relationship_ids: [], claim_ids: [], evidence_ref_ids: [],
          returned_counts: counts, total_counts: counts, omission_codes: [],
        },
      }
    })
  const order = (step: RetrievalStep) => step.native || step.pruning
    ? step.sequence : trace.graph_replay_order?.[step.sequence] ?? (native.length ? Number.MAX_SAFE_INTEGER : step.sequence)
  const steps = [...graph, ...native, ...exclusions].sort((left, right) => order(left) - order(right))
    .flatMap(neighborhoodFrames)
  const discovery = trace.native_discovery_replay
  if (!discovery?.hops.length) return steps

  const discoveryFrame = (frame: string, ids: readonly string[], hop?: RetrievalStep['hop']): RetrievalStep => {
    const nodes = ids.map(id => ({ node_id: id, label: discovery.labels[id] ?? 'Unnamed object', kind: 'object' }))
    const counts = { nodes: nodes.length, relationships: 0, claims: 0, evidence_refs: 0 }
    return {
      sequence: -1, frame, hop, revision_pin: discovery.revision_id,
      request: { operation: 'search', query_text: '', seed_node_ids: [] },
      result: {
        outcome: 'enough', graph_revision: discovery.revision_id, coverage_status: 'complete',
        projection_status: 'complete', nodes, relationship_ids: [], claim_ids: [], evidence_ref_ids: [],
        returned_counts: counts, total_counts: counts, omission_codes: [],
      },
    }
  }
  return [
    discoveryFrame('Starting nodes', discovery.seed_ids),
    ...discovery.hops.map((hop, index) => discoveryFrame(
      `Native discovery hop ${index + 1}`, [hop.from_node_id, hop.to_node_id], hop,
    )),
    ...steps,
  ]
}

function neighborhoodFrames(step: RetrievalStep): RetrievalStep[] {
  const readableStep = (item: RetrievalStep, position: number) => {
    if (item.hop) {
      const label = labelForStep(position)
      return `${label(item.hop.from_node_id) ?? 'Unnamed object'} → ${label(item.hop.to_node_id) ?? 'Unnamed object'}`
    }
    if (item.pruning) return `Exclude ${item.pruning.total} ${item.pruning.total === 1 ? 'candidate' : 'candidates'}`
    if (item.native) return item.writerEvidence ? 'Read Graph evidence for the answer writer' : 'Read Graph evidence'
    if (item.request.operation === 'search' && item.request.query_text.trim()) return `Search for “${item.request.query_text.trim()}”`
    return stepLabel(item)
  }
  const replay = step.result.neighborhood_replay
  if (!replay || step.request.operation !== 'neighborhood') return [step]
  const nodes = new Map(step.result.nodes.map(node => [node.node_id, node]))
  const frameResult = { ...step.result, claim_ids: [], evidence_ref_ids: [],
    relationship_ids: [], relationships: [], discovery_relationship_ids: [] }
  const seeds = new Set(step.request.seed_node_ids)
  const frames: RetrievalStep[] = [{
    ...step, frame: 'Starting nodes',
    result: { ...frameResult, nodes: step.result.nodes.filter(node => seeds.has(node.node_id)) },
  }]
  for (const [index, hop] of replay.hops.entries()) {
    const endpoints = [nodes.get(hop.from_node_id), nodes.get(hop.to_node_id)]
      .filter((node): node is ReplayIdentity => node !== undefined)
    if (endpoints.length !== 2) continue
    frames.push({ ...step, frame: `Hop ${index + 1}`, hop, result: { ...frameResult, nodes: endpoints } })
  }
  frames.push({
    ...step, frame: 'Neighborhood results',
    result: { ...step.result, discovery_relationship_ids: [] },
  })
  if (replay.object_limit_pruned_count > 0) {
    const pruned = replay.object_limit_pruned_ids.map(id => ({ node_id: id, label: 'Unnamed object', kind: 'object' }))
    frames.push({
      ...step, frame: 'Object limit pruning',
      pruning: { reason: 'Dropped by the neighborhood object limit', total: replay.object_limit_pruned_count, ids: replay.object_limit_pruned_ids },
      result: { ...frameResult, nodes: pruned },
    })
  }
  return frames
}

const stepKey = (step: RetrievalStep) => `${step.native ? 'native' : 'graph'}:${step.sequence}:${step.frame ?? ''}`
const showsLookupResult = (step: RetrievalStep) => !step.frame || step.frame === 'Neighborhood results'
const stepLabel = (step: RetrievalStep) => step.frame ?? (step.native ? 'Read native assertions' : labels[step.request.operation])

const labels = {
  search: 'Search the graph',
  object: 'Look up an object',
  neighborhood: 'Look up a neighborhood',
  support: 'Look up supporting evidence',
  observations: 'Read observations',
} satisfies Record<RetrievalStep['request']['operation'], string>

const previewSize = 12
const assertionPageSize = 20

function RecordedAssertions({ trace, step, labelFor }: { trace: BuddyTurnContextTrace; step: RetrievalStep; labelFor?: (id: string) => string | undefined }) {
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
    {assertions.slice(start, end).map((assertionId, position) => <BuddyReplayAssertion
      key={assertionId} trace={trace} step={step} assertionId={assertionId} labelFor={labelFor} number={start + position + 1} />)}
  </details>
}

function replayLabelScope(step: RetrievalStep) {
  return JSON.stringify([step.revision_pin, step.scope_mode, step.campaign_id])
}

function hasRecordedName(label?: string): label is string {
  return Boolean(label?.trim() && !/^(?:(?:ent|entity|asrt):|Unnamed object(?: \d+)?$)/i.test(label))
}

function displayNodeName(node: RetrievalStep['result']['nodes'][number]) {
  const recordedNames = /^Multiple recorded names \(object \d+\): (.+)$/.exec(node.label)
  if (recordedNames) {
    try {
      const names: unknown = JSON.parse(recordedNames[1])
      if (Array.isArray(names) && names.every(name => typeof name === 'string' && name.trim())) {
        return names.slice(0, 2).join(' / ') + (names.length > 2 ? ` (+${names.length - 2} more)` : '')
      }
    } catch {
      return 'Object with multiple recorded names'
    }
    return 'Object with multiple recorded names'
  }
  return hasRecordedName(node.label) ? node.label : 'Unnamed object'
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
  const edgesByStep = steps.map(({ result, hop }) => {
    if (hop) {
      const from = objects.get(hop.from_node_id)
      const to = objects.get(hop.to_node_id)
      return from && to ? [{ id: hop.relationship_id, from, to, directed: true }] : []
    }
    const discovery = new Set(result.discovery_relationship_ids)
    return (result.relationships ?? []).flatMap(edge => {
      if (!discovery.has(edge.relationship_id)) return []
      const from = objects.get(edge.source_node_id)
      const to = objects.get(edge.target_node_id)
      return from && to ? [{ id: edge.relationship_id, from, to, directed: false }] : []
    })
  })
  const columns = Math.max(1, Math.ceil(Math.sqrt(objects.size * 1.65)))
  let offset = 0
  for (const object of objects.values()) {
    object.x = 44 + (offset % columns) * 88
    object.y = 44 + Math.floor(offset / columns) * 88
    offset += 1
  }
  return { objects, edgesByStep, width: columns * 88, height: Math.max(88, Math.ceil(objects.size / columns) * 88) }
}

function keepStepVisible(pane: HTMLElement | null) {
  const active = pane?.querySelector('[data-replay-active]')
  if (!pane || !active) return
  const frame = pane.getBoundingClientRect()
  const row = active.getBoundingClientRect()
  if (row.top < frame.top) pane.scrollTop += row.top - frame.top
  else if (row.bottom > frame.bottom) pane.scrollTop += row.bottom - frame.bottom
}

type ReplayIdentity = RetrievalStep['result']['nodes'][number]
const emptyIdentities: ReadonlyMap<string, ReplayIdentity> = new Map()

const Trail = memo(function Trail({ layout, active, wide, select, resolve, pruned, reveal, inspect, inspectedId }: {
  layout: ReturnType<typeof layoutTrail>
  active: number
  wide: boolean
  select: (position: number) => void
  resolve: (node: ReplayIdentity, position: number) => ReplayIdentity
  pruned?: readonly string[]
  reveal: boolean
  inspect: (id: string, trigger: SVGGElement) => void
  inspectedId: string | null
}) {
  const arrow = useId()
  return <div className="buddy-retrieval-replay__canvas">
    <svg viewBox={`0 0 ${layout.width} ${layout.height}`} role="group" aria-label="Recorded graph nodes">
      <defs><marker id={arrow} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#a76a23" />
      </marker></defs>
      {layout.edgesByStep.slice(0, active + 1).flatMap((edges, position) =>
        edges.filter(edge => position === active || edge.directed).map(({ id, from, to, directed }) => {
          const dx = to.x - from.x
          const dy = to.y - from.y
          const distance = Math.hypot(dx, dy)
          const inset = directed && distance > 0 ? 26 / distance : 0
          return <line key={`${position}:${id}`} className="buddy-retrieval-replay__hop" aria-hidden="true"
            opacity={position === active ? 1 : 0.24} markerEnd={directed ? `url(#${arrow})` : undefined}
            x1={from.x} y1={from.y} x2={to.x - dx * inset} y2={to.y - dy * inset} />
        }))}
      {[...layout.objects.values()].map(({ node, visits, x, y }) => {
        const current = visits.includes(active)
        const position = visits[0]
        const presentation = resolve(node, current ? active : position)
        const name = displayNodeName(presentation)
        if (reveal && position > active) return null
        const state = pruned?.includes(node.node_id) ? 'pruned' : current ? 'current' : position < active ? 'visited' : 'upcoming'
        const selectVisit = (trigger: SVGGElement) => {
          inspect(node.node_id, trigger)
          if (!current) select(visits.find(visit => visit > active) ?? visits.at(-1)!)
        }
        return <g key={node.node_id} transform={`translate(${x} ${y})`}
          data-visit={state} data-inspected={inspectedId === node.node_id || undefined} role="button" tabIndex={wide || current ? 0 : -1}
          aria-label={name} aria-pressed={current}
          aria-haspopup="dialog" onClick={event => selectVisit(event.currentTarget)} onKeyDown={event => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              selectVisit(event.currentTarget)
            }
          }}>
          <title>{name}</title>
          <g style={{ color: graphTypeColor(presentation.kind) }}>
            <GraphCircleGlyph center={0} radius={24} kind={presentation.kind} name="" showLabels={false} fullCorpus />
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
  const [inspectedId, setInspectedId] = useState<string | null>(null)
  const nodeDialog = useRef<HTMLDialogElement>(null)
  const inspectedTrigger = useRef<SVGGElement>(null)
  const dismissNode = () => {
    nodeDialog.current?.close()
    setInspectedId(null)
    inspectedTrigger.current?.focus()
  }
  const inspect = useCallback((id: string, trigger: SVGGElement) => {
    inspectedTrigger.current = trigger
    trigger.focus()
    setPlaying(false)
    setInspectedId(id)
  }, [])
  const [identityResult, setIdentityResult] = useState<{
    trace: BuddyTurnContextTrace
    identities: ReadonlyMap<string, ReplayIdentity>
  }>()
  const identities = identityResult?.trace === trace ? identityResult?.identities ?? emptyIdentities : emptyIdentities
  const [wide, setWide] = useState(false)
  const [poppedOut, setPoppedOut] = useState(false)
  const popoutDialog = useRef<HTMLDialogElement>(null)
  const popoutTrigger = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!poppedOut) return
    const dialog = popoutDialog.current
    dialog?.showModal()
    return () => { if (dialog?.open) dialog.close() }
  }, [poppedOut])
  const restoreInline = () => {
    popoutDialog.current?.close()
    setPoppedOut(false)
    requestAnimationFrame(() => popoutTrigger.current?.focus())
  }
  const spacious = wide || poppedOut
  const [expanded, setExpanded] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const list = useRef<HTMLOListElement>(null)
  const passagesByEvidence = useMemo(() => indexPassages(trace), [trace])
  const writerObservations = useMemo(() => new Set(trace?.writer_evidence_sequences ?? []), [trace?.writer_evidence_sequences])
  const rows = useMemo(() => layoutTrail(steps), [steps])
  const nativeBySequence = useMemo(() => new Map(
    trace?.native_assertion_steps?.map(step => [step.sequence, step]),
  ), [trace])
  const namesByScope = useMemo(() => {
    const labels = new Map<string, Map<string, string>>()
    for (const frame of steps) {
      if (!frame.revision_pin) continue
      const key = replayLabelScope(frame)
      let byId = labels.get(key)
      if (!byId) labels.set(key, byId = new Map())
      for (const node of frame.result.nodes) {
        const label = displayNodeName(node)
        if (label !== 'Unnamed object' && !byId.has(node.node_id)) byId.set(node.node_id, label)
      }
    }
    return labels
  }, [steps])
  const resolve = useCallback((node: ReplayIdentity, position: number): ReplayIdentity => {
    const step = steps[position]
    const saved = step?.native ? nativeBySequence.get(step.sequence) : undefined
    const nativeRevision = saved?.revision_id ?? (step?.sequence === -1 ? trace?.native_discovery_replay?.revision_id : undefined)
    const fallback = nativeRevision && nativeRevision === step?.revision_pin ? identities.get(node.node_id) : undefined
    const savedLabel = saved?.subject_labels?.[node.node_id]
    return {
      ...node,
      label: hasRecordedName(savedLabel) ? savedLabel : hasRecordedName(node.label) ? node.label
        : (step && namesByScope.get(replayLabelScope(step))?.get(node.node_id)) ?? fallback?.label ?? node.label,
      kind: saved?.subject_kinds?.[node.node_id] ?? fallback?.kind ?? node.kind,
    }
  }, [identities, namesByScope, nativeBySequence, steps, trace])
  const labelForStep = (position: number) => (id: string) => {
    const frame = steps[position]
    const node = frame.result.nodes.find(record => record.node_id === id)
    if (node) {
      const label = displayNodeName(resolve(node, position))
      if (label !== 'Unnamed object') return label
    }
    const saved = frame.native ? nativeBySequence.get(frame.sequence) : undefined
    const relatedLabel = saved?.revision_id === frame.revision_pin && saved && Object.hasOwn(saved.related_labels ?? {}, id)
      ? saved.related_labels?.[id] : undefined
    if (hasRecordedName(relatedLabel)) return relatedLabel
    const recordedLabel = namesByScope.get(replayLabelScope(frame))?.get(id)
    if (recordedLabel) return recordedLabel
    const nativeRevision = saved?.revision_id ?? (frame.sequence === -1 ? trace?.native_discovery_replay?.revision_id : undefined)
    const historicalLabel = nativeRevision === frame.revision_pin ? identities.get(id)?.label : undefined
    return hasRecordedName(historicalLabel) ? historicalLabel : undefined
  }
  const step = steps[index]
  const last = index + 1 >= steps.length

  useEffect(() => {
    const missingSubjects = trace?.native_assertion_steps?.some(step => step.subject_ids.some(id =>
      !hasRecordedName(step.subject_labels?.[id]) || !step.subject_kinds?.[id]))
    const discovery = trace?.native_discovery_replay
    const missingDiscovery = discovery && [
      ...discovery.seed_ids,
      ...discovery.hops.flatMap(hop => [hop.from_node_id, hop.to_node_id]),
    ].some(id => !hasRecordedName(discovery.labels[id]))
    if (!trace || (!missingSubjects && !missingDiscovery)) return
    const controller = new AbortController()
    const { world_id, turn_id, trace_id } = trace
    void (async () => {
      const collected = new Map<string, ReplayIdentity>()
      let offset = 0
      while (!controller.signal.aborted) {
        const result = await getWorldAgentReplayIdentities(world_id, turn_id, trace_id, controller.signal, offset)
        if (controller.signal.aborted || result.world_id !== world_id
            || result.turn_id !== turn_id || result.trace_id !== trace_id) return
        for (const item of result.identities) {
          if (rows.objects.has(item.node_id)) collected.set(item.node_id, item)
        }
        setIdentityResult({ trace, identities: new Map(collected) })
        if (result.next_offset == null) break
        if (!Number.isSafeInteger(result.next_offset) || result.next_offset <= offset) {
          throw new Error('Replay name page did not advance')
        }
        offset = result.next_offset
      }
    })().catch(() => { /* Recorded labels remain available if a historical name read fails. */ })
    return () => controller.abort()
  }, [trace, rows])

  useEffect(() => {
    if (!playing || last) return
    const timer = window.setTimeout(() => {
      setExpanded(false)
      setIndex(index + 1)
      if (index + 2 === steps.length) setPlaying(false)
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [index, last, playing, steps.length])

  useEffect(() => keepStepVisible(list.current), [index, steps, spacious, showDetails])

  const select = useCallback((next: number) => {
    setPlaying(false)
    setExpanded(false)
    setIndex(next)
  }, [])

  const inspected = inspectedId === null ? undefined : rows.objects.get(inspectedId)
  const showNodeDialog = Boolean(inspected && inspected.visits[0] <= index)
  useEffect(() => {
    const dialog = nodeDialog.current
    if (!showNodeDialog || !dialog) return
    dialog.showModal()
    return () => { if (dialog.open) dialog.close() }
  }, [showNodeDialog])
  if (!step) return <p>No graph lookup steps were retained for this attempt.</p>

  const inspectedNode = inspected ? resolve(inspected.node, inspected.visits.includes(index) ? index : inspected.visits[0]) : undefined
  const inspectedHops = inspectedId === null ? [] : steps.slice(0, index + 1)
    .flatMap((item, position) => {
      if (!item.hop || ![item.hop.from_node_id, item.hop.to_node_id].includes(inspectedId)) return []
      const label = (id: string) => {
        const node = item.result.nodes.find(record => record.node_id === id)
        return node ? displayNodeName(resolve(node, position)) : 'Unnamed object'
      }
      return [{ position, from: label(item.hop.from_node_id), to: label(item.hop.to_node_id) }]
    })
  const inspectedVisits = inspected?.visits.filter(position => position <= index) ?? []
  const inspectedReads = inspectedId === null ? [] : inspectedVisits.flatMap(position => {
    const read = steps[position]
    const ids = read.assertionIdsBySubject?.[inspectedId]
    return ids?.length ? [{ position, read, ids }] : []
  })
  const seenFindings = new Set<string>()
  const findings = [...inspectedReads]
    .sort((a, b) => Number(Boolean(b.read.writerEvidence)) - Number(Boolean(a.read.writerEvidence)))
    .flatMap(({ read, ids, position }) => ids.slice(0, 3).flatMap(assertionId => {
      const key = JSON.stringify([read.sequence, read.revision_pin, read.scope_mode, read.campaign_id, assertionId])
      if (seenFindings.has(key)) return []
      seenFindings.add(key)
      return [{ assertionId, read, position }]
    }))
    .slice(0, 3)
  const inspectedPruning = inspectedVisits.filter(position =>
    inspectedId !== null && steps[position].pruning?.ids.includes(inspectedId))
  const { nodes: recordedNodes, relationship_ids, relationships = [], total_counts, projection_status } = step.result
  const nodes = recordedNodes.map(node => resolve(node, index))
  const renderStepEvidence = (recordedStep: RetrievalStep) => {
    const { evidence_ref_ids: refs } = recordedStep.result
    if (!trace || refs.length === 0) return null
    const passages = refs.flatMap(id => passagesByEvidence.get(JSON.stringify([recordedStep.revision_pin, id])) ?? [])
    return <>
      {passages.length > 0 && <section aria-label="Captured source excerpts">
        {passages.map(passage => <BuddyHistoricalSourcePassage key={`${passage.source_read_event_id}:${passage.source_read_id}`}
          graphRevision={recordedStep.revision_pin} label={`Open excerpt · ${passage.source_name?.trim() || 'Captured source'}${writerObservations.has(passage.sequence) ? ' · Writer evidence' : ''}`}
          reference={{
            schema: 'dmb_trace_historical_source_ref_v1', world_id: trace.world_id,
            conversation_id: trace.conversation_id, turn_id: trace.turn_id, attempt: trace.attempt,
            trace_id: trace.trace_id, source_read_event_id: passage.source_read_event_id,
            source_read_id: passage.source_read_id, content_sha256: passage.content_sha256,
          }} />)}
      </section>}
      {passages.length === 0 && <p>No matching source excerpt was captured for this lookup.</p>}
    </>
  }
  const replay = (
    <section className="buddy-retrieval-replay" aria-label="Retrieval replay">
      <div data-wide={spacious}>
        <Trail layout={rows} active={index} wide={spacious} select={select} resolve={resolve} pruned={step.pruning?.ids} inspect={inspect} inspectedId={inspectedId} reveal={steps.some(item => item.hop || item.pruning)} />
      </div>
      <div className="buddy-retrieval-replay__controls">
        <button type="button" aria-label="Play" title="Play" disabled={playing || steps.length < 2} onClick={() => {
          if (last) select(0)
          setPlaying(true)
        }}><span aria-hidden="true">▶</span></button>
        <button type="button" aria-label="Pause" title="Pause" disabled={!playing} onClick={() => setPlaying(false)}><span aria-hidden="true">Ⅱ</span></button>
        <button type="button" aria-label="Previous step" title="Previous step" disabled={index === 0} onClick={() => select(index - 1)}><span aria-hidden="true">⏮</span></button>
        <button type="button" aria-label="Next step" title="Next step" disabled={last} onClick={() => select(index + 1)}><span aria-hidden="true">⏭</span></button>
        {!poppedOut && <button type="button" aria-expanded={wide} aria-label={wide ? "Collapse" : "Expand"} title={wide ? "Collapse" : "Expand"} onClick={() => setWide(value => !value)}><span aria-hidden="true">{wide ? "−" : "+"}</span></button>}
        {poppedOut
          ? <button type="button" autoFocus aria-label="Return to conversation" title="Return to conversation" onClick={restoreInline}><span aria-hidden="true">↙</span></button>
          : <button ref={popoutTrigger} type="button" aria-haspopup="dialog" aria-label="Pop out replay" title="Pop out replay" onClick={() => setPoppedOut(true)}><span aria-hidden="true">↗</span></button>}
        <span role="status">Step {index + 1} of {steps.length}</span>
      </div>
      {wide && trace && trace.writer_evidence_sequences == null && !steps.some(item => item.writerEvidence) && <p>Writer evidence was unavailable for this attempt.</p>}
      <p className="buddy-retrieval-replay__caption">
        {nodes.length === 1 ? displayNodeName(nodes[0]) : nodes.length ? `${nodes.length} objects` : stepLabel(step)}
      </p>
      {showNodeDialog && inspected && inspectedNode && <dialog ref={nodeDialog}
        className="buddy-retrieval-replay__node-details" aria-label="Replay node details"
        onCancel={event => { event.preventDefault(); event.stopPropagation(); dismissNode() }}
        onKeyDown={event => { if (event.key === 'Escape') event.stopPropagation() }}>
        <GraphNodeViewer dialog label={displayNodeName(inspectedNode)} kind={inspectedNode.kind.includes(':')
          ? displayClassification([inspectedNode.kind]).replace(' (role unspecified)', '')
          : inspectedNode.kind}
          controls={<button type="button" autoFocus aria-label="Close node details" onClick={dismissNode}>×</button>}>
        {displayNodeName(inspectedNode) === 'Unnamed object' && <p>
          This replay has no usable recorded name for this node. Its name may be missing or unavailable
          in the recorded revision and visibility scope.
        </p>}
        <NodeOverview replay>
          {inspectedReads.length > 0 || inspectedHops.length > 0 || inspectedPruning.length > 0 ? <>
            {trace && findings.map(({ assertionId, read, position }) => <ReplayNodeFinding
              key={`${position}:${assertionId}`} trace={trace} step={read} assertionId={assertionId} nodeId={inspectedNode.node_id}
              nodeLabel={displayNodeName(inspectedNode)} labelFor={labelForStep(position)} />)}
            {trace && inspectedReads.map(({ position, read, ids }) => <div key={position}>
              <p>Buddy read {ids.length} {ids.length === 1 ? 'record' : 'records'} about this node in step {position + 1}.
                {read.writerEvidence && ' These records were passed to the answer writer.'}</p>
              <RecordedAssertions trace={trace} labelFor={labelForStep(position)} step={{ ...read, result: { ...read.result, claim_ids: [...ids] } }} />
            </div>)}
            {inspectedHops.map(({ position, from, to }) => <p key={position}>
              Buddy followed a recorded connection from {from} to {to}.
            </p>)}
            {inspectedPruning.map(position => <p key={position}>
              {steps[position].pruning?.reason}.
            </p>)}
          </> : undefined}
        </NodeOverview>
        <ul className="buddy-retrieval-replay__node-visits">{inspectedVisits.map(position => (
          <li key={position}><button type="button" onClick={() => { dismissNode(); select(position) }}>
            Step {position + 1} · {readableStep(steps[position], position)}
          </button>
          </li>
        ))}</ul>
        </GraphNodeViewer>
      </dialog>}
      {step.pruning && <p>{readableStep(step, index)}. {step.pruning.reason}.{step.pruning.total > nodes.length
        && ' The capture lists only some of the excluded candidates.'}</p>}
      {wide && trace && !steps.some(item => item.hop || item.result.neighborhood_replay) && <p>Directed traversal was unavailable for this attempt.</p>}
      {wide && trace && trace.retrieval_exclusion_steps == null && !steps.some(item => item.result.neighborhood_replay) && <p>Pruning decisions were unavailable for this attempt.</p>}
      {spacious && <button type="button" aria-expanded={showDetails}
        onClick={() => setShowDetails(value => !value)}>{showDetails ? 'Hide replay details' : 'Show replay details'}</button>}
      {spacious && showDetails && <div className="buddy-retrieval-replay__workspace">
        <section aria-label="Recorded lookup results">
          <h5>{readableStep(step, index)}</h5>
          {(showsLookupResult(step) && (step.native ? step.writerEvidence : writerObservations.has(step.sequence))) && <p><strong>Evidence sent to the answer writer</strong></p>}
          {showsLookupResult(step) && <p>{total_counts.nodes} objects · {total_counts.relationships} relationships · {total_counts.claims} claims</p>}
          {showsLookupResult(step) && projection_status === 'limited' && <p>Some results were omitted from the saved trace.</p>}
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
            <RecordedAssertions key={stepKey(step)} trace={trace} labelFor={labelForStep(index)} step={step} />}
          {renderStepEvidence(step)}
        </section>
        <ol ref={list} className="buddy-retrieval-replay__steps" aria-label="Recorded retrieval steps">
          {steps.map((item, position) => (
            <li key={stepKey(item)} data-replay-active={position === index ? true : undefined}><button type="button" aria-current={position === index ? 'step' : undefined}
              onClick={() => select(position)}>{readableStep(item, position)}
              {(showsLookupResult(item) && (item.native ? item.writerEvidence : writerObservations.has(item.sequence))) && <strong> · Writer evidence</strong>}</button></li>
          ))}
        </ol>
      </div>}
    </section>
  )
  return poppedOut ? <dialog ref={popoutDialog} className="buddy-retrieval-replay__popout"
    aria-label="Expanded retrieval replay" onCancel={event => {
      if (event.target !== event.currentTarget) return
      event.preventDefault()
      restoreInline()
    }}
    onKeyDown={event => { if (event.key === 'Escape') event.stopPropagation() }}>
    {replay}
  </dialog> : replay

}
