import { setNativeGraphAccessToken } from '../../api/liveApi'
import type { BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterAll, beforeAll, expect, it, vi } from 'vitest'
import { BuddyRetrievalReplay, replaySteps, type RetrievalStep } from './BuddyRetrievalReplay'

const dialogMethods = Object.getOwnPropertyDescriptors(HTMLDialogElement.prototype)
beforeAll(() => {
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: { configurable: true, value(this: HTMLDialogElement) { this.setAttribute('open', '') } },
    close: { configurable: true, value(this: HTMLDialogElement) { this.removeAttribute('open') } },
  })
})
afterAll(() => {
  for (const name of ['showModal', 'close']) {
    const original = dialogMethods[name]
    if (original) Object.defineProperty(HTMLDialogElement.prototype, name, original)
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name)
  }
})

function lookup(sequence: number, label: string): RetrievalStep {
  return {
    sequence,
    request: { operation: 'object' },
    result: {
      nodes: [{ node_id: label, label, kind: 'person' }],
      relationship_ids: [],
      evidence_ref_ids: [],
      claim_ids: [],
      total_counts: { nodes: 1, relationships: 0, claims: 0 },
      outcome: 'enough',
    },
  } as RetrievalStep
}

it('synchronizes the trail and step list, and cancels playback when paused', () => {
  vi.useFakeTimers()
  try {
    render(<BuddyRetrievalReplay steps={[lookup(4, 'Caelynn'), lookup(8, 'Mossglade')]} />)
    const trail = screen.getByRole('group', { name: 'Recorded graph nodes' })
    expect(screen.queryByRole('list', { name: 'Recorded retrieval steps' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
    const steps = screen.getByRole('list', { name: 'Recorded retrieval steps' })
    const first = within(trail).getByRole('button', { name: 'Caelynn' })
    const second = within(trail).getByRole('button', { name: 'Mossglade' })
    expect(first).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    act(() => vi.advanceTimersByTime(2000))
    expect(first).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    act(() => vi.advanceTimersByTime(1000))
    expect(second).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Collapse' }))
    expect(screen.getByRole('group', { name: 'Recorded graph nodes' })).toBe(trail)
    expect(screen.getByRole('status')).toHaveTextContent('Step 2 of 2')
    fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
    expect(within(steps).getAllByRole('button')[1]).toHaveAttribute('aria-current', 'step')
    fireEvent.keyDown(first, { key: 'Enter' })
    expect(within(steps).getAllByRole('button')[0]).toHaveAttribute('aria-current', 'step')
  } finally {
    vi.useRealTimers()
  }
})

it('keeps the current step when activating a node visited more than once', () => {
  render(<BuddyRetrievalReplay steps={[lookup(1, 'Caelynn'), lookup(2, 'Caelynn')]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  const node = screen.getByRole('button', { name: 'Caelynn' })
  fireEvent.keyDown(node, { key: 'Enter' })
  expect(screen.getByRole('status')).toHaveTextContent('Step 2 of 2')
})

it('interleaves native and legacy reads using ledger order', () => {
  const trace = {
    observations: [
      { ...lookup(0, 'Caelynn'), kind: 'graph_tool' },
      { ...lookup(1, 'Mossglade'), kind: 'graph_tool' },
    ],
    graph_replay_order: { 0: 3, 1: 9 },
    native_assertion_steps: [{
      sequence: 6, revision_id: 'revision-one', assertion_ids: ['claim:1'],
      subject_ids: ['Caelynn'], unavailable_count: 0, writer_evidence: true,
    }],
  } as BuddyTurnContextTrace
  const steps = replaySteps(trace)
  expect(steps.map(step => [step.sequence, Boolean(step.native)])).toEqual([[0, false], [6, true], [1, false]])
  render(<BuddyRetrievalReplay trace={trace} steps={steps} />)
  fireEvent.click(screen.getByRole("button", { name: "Expand" }))
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  expect(screen.getByRole('heading', { name: 'Read native assertions' })).toBeInTheDocument()
  expect(screen.getByText('Evidence sent to the answer writer')).toBeInTheDocument()
})

it('keeps the last assertion in a dense batch reachable with bounded controls', () => {
  const step = lookup(4, 'Caelynn')
  step.result.claim_ids = Array.from({ length: 426 }, (_, index) => `claim:${index + 1}`)
  const trace = { observations: [step] } as BuddyTurnContextTrace
  render(<BuddyRetrievalReplay trace={trace} steps={[step]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
  fireEvent.click(screen.getByText('Recorded assertions (426)'))
  expect(screen.getAllByText(/^Open assertion ·/)).toHaveLength(20)
  fireEvent.change(screen.getByLabelText('Assertion range'), { target: { value: '21' } })
  expect(screen.getAllByText(/^Open assertion ·/)).toHaveLength(6)
  expect(screen.getByText('Open assertion · claim:426')).toBeInTheDocument()
  expect(screen.queryByText('Open assertion · claim:1')).not.toBeInTheDocument()
})

it('marks only the recorded writer evidence step as playback advances', () => {
  const steps = [lookup(4, 'Caelynn'), lookup(8, 'Mossglade')]
  const trace = { observations: steps, writer_evidence_sequences: [8] } as BuddyTurnContextTrace
  render(<BuddyRetrievalReplay steps={steps} trace={trace} />)
  fireEvent.click(screen.getByRole("button", { name: "Expand" }))
  const list = screen.getByRole('list', { name: 'Recorded retrieval steps' })
  expect(within(list).getAllByRole('button', { name: /Writer evidence/ })).toHaveLength(1)
  expect(screen.queryByText('Evidence sent to the answer writer')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  expect(screen.getByText('Evidence sent to the answer writer')).toBeInTheDocument()
})

it('scrolls the step list to a selected offscreen step without moving focus', () => {
  render(<BuddyRetrievalReplay steps={Array.from({ length: 10 }, (_, index) => lookup(index + 1, `Object ${index}`))} />)
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
  const list = screen.getByRole('list', { name: 'Recorded retrieval steps' })
  const last = within(list).getAllByRole('button').at(-1)!
  const bounds = (top: number, height: number) => new DOMRect(0, top, 200, height)
  vi.spyOn(list, 'getBoundingClientRect').mockReturnValue(bounds(0, 200))
  vi.spyOn(last.parentElement!, 'getBoundingClientRect').mockReturnValue(bounds(315, 34))
  last.focus()
  fireEvent.click(last)
  expect(list.scrollTop).toBe(149)
  expect(last).toHaveFocus()
})

it('offers only captured passages matching the lookup evidence, World, and revision', () => {
  const step = lookup(1, 'Mossglade')
  step.revision_pin = 'revision-one'
  step.result.evidence_ref_ids = ['support-one']
  const source = {
    kind: 'source_passage', world_id: 'elderwyld', graph_revision: 'revision-one',
    evidence_ref_id: 'support-one', source_read_id: 'read-one', source_read_event_id: 'event-one',
    source_name: 'Session 1', content_sha256: 'digest', text: 'Captured text',
  }
  const trace = {
    trace_id: 'trace', world_id: 'elderwyld', conversation_id: 'conversation', turn_id: 'turn', attempt: 1,
    observations: [step, source,
      { ...source, source_name: 'Elsewhere', world_id: 'foreign' },
      { ...source, source_name: 'Later revision', graph_revision: 'revision-two' }],
  } as BuddyTurnContextTrace
  render(<BuddyRetrievalReplay steps={[step]} trace={trace} />)
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
  expect(screen.getByText('Open excerpt · Session 1')).toBeInTheDocument()
  expect(screen.queryByText(/Elsewhere|Later revision|Captured text/)).not.toBeInTheDocument()
})

it('shows returned relationship direction and preserves lookup-only older steps', () => {
  const current = lookup(1, 'Caelynn')
  const older = lookup(2, 'Previous result')
  current.result.nodes.push({ node_id: 'Mossglade', label: 'Mossglade', kind: 'event' })
  current.result.relationship_ids = ['edge:one']
  current.result.relationships = [{
    relationship_id: 'edge:one', source_node_id: 'Caelynn', target_node_id: 'Mossglade',
  }]
  older.result.relationship_ids = ['edge:older']
  render(<BuddyRetrievalReplay steps={[current, older]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
  expect(screen.getByText('Returned relationships (1)')).toBeInTheDocument()
  expect(screen.getByText('Caelynn → Mossglade')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  expect(screen.getByText('Some relationship endpoints were unavailable in this trace.')).toBeInTheDocument()
  expect(screen.queryByText('Returned relationships (1)')).not.toBeInTheDocument()
})

it('opens a recorded assertion lazily and rejects a different revision', async () => {
  setNativeGraphAccessToken('synthetic-replay-reader')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({
    schema: 'dmb_replay_assertion_v1', world_id: 'elderwyld', turn_id: 'turn', trace_id: 'trace',
    sequence: 1, scope: { managed_world_id: 'elderwyld', revision_id: 'later', scope_mode: 'world', campaign_id: null },
    assertion: { assertion_id: 'claim:1', subject_entity_id: 'Caelynn', predicate: 'name', value: 'Wrong revision' },
  }))
  try {
    const step = lookup(1, 'Caelynn')
    step.revision_pin = 'original'
    step.scope_mode = 'world'
    step.campaign_id = null
    step.result.claim_ids = ['claim:1']
    const trace = { trace_id: 'trace', world_id: 'elderwyld', turn_id: 'turn', observations: [step] } as BuddyTurnContextTrace
    render(<BuddyRetrievalReplay steps={[step]} trace={trace} />)
    fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Recorded assertions (1)'))
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Open assertion · claim:1'))
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable at the recorded revision')
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(String(fetch.mock.calls[0][0])).toContain('/steps/1/assertion?assertion_id=claim%3A1')
    expect(screen.queryByText(/Wrong revision/)).not.toBeInTheDocument()
  } finally {
    cleanup()
    fetch.mockRestore()
    setNativeGraphAccessToken(null)
  }
})

it('reveals recorded seeds, draws directed hops in order, and explains object-limit pruning', () => {
  const step = lookup(4, 'Caelynn')
  step.request = { operation: 'neighborhood', seed_node_ids: ['Caelynn'], depth: 2 }
  step.result.nodes.push({ node_id: 'Mossglade', label: 'Mossglade', kind: 'person' })
  step.result.nodes.push({ node_id: 'Arena', label: 'Arena', kind: 'location' })
  step.result.neighborhood_replay = {
    hops: [
      { relationship_id: 'first', from_node_id: 'Caelynn', to_node_id: 'Mossglade' },
      { relationship_id: 'second', from_node_id: 'Mossglade', to_node_id: 'Arena' },
    ],
    object_limit_pruned_ids: ['discarded'],
    object_limit_pruned_count: 1,
  }
  const trace = { observations: [{ ...step, kind: 'graph_tool' }] } as BuddyTurnContextTrace
  render(<BuddyRetrievalReplay steps={replaySteps(trace)} trace={trace} />)
  const trail = screen.getByRole('group', { name: 'Recorded graph nodes' })
  const seed = within(trail).getByRole('button', { name: 'Caelynn' })
  const position = seed.getAttribute('transform')
  const next = screen.getByRole('button', { name: 'Next step' })
  expect(within(trail).getAllByRole('button')).toHaveLength(1)
  expect(trail.querySelectorAll('line')).toHaveLength(0)
  fireEvent.click(next)
  expect(within(trail).getByRole('button', { name: 'Mossglade' })).toBeInTheDocument()
  const arrow = trail.querySelector('line')!
  expect(arrow).toHaveAttribute('marker-end')
  expect(arrow).toHaveAttribute('x1', '44')
  fireEvent.click(next)
  expect(trail.querySelectorAll('line')).toHaveLength(2)
  expect(arrow).toHaveAttribute('opacity', '0.24')
  fireEvent.click(next)
  fireEvent.click(next)
  expect(seed).toHaveAttribute('transform', position)
  expect(within(trail).getByRole('button', { name: 'Unnamed object' })).toHaveAttribute('data-visit', 'pruned')
  expect(screen.getByText('Dropped by the neighborhood object limit.')).toBeInTheDocument()
})

it('opens and closes contextual details for the selected replay node', () => {
  render(<BuddyRetrievalReplay steps={[lookup(4, 'Caelynn')]} />)
  expect(screen.queryByRole('dialog', { name: 'Replay node details' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Caelynn' }))
  const detail = screen.getByRole('dialog', { name: 'Replay node details' })
  expect(within(detail).getByRole('heading', { name: 'Caelynn' })).toBeInTheDocument()
  expect(within(detail).getByRole('button', { name: 'Step 1 · Look up an object' })).toBeInTheDocument()
  fireEvent.click(within(detail).getByRole('button', { name: 'Close node details' }))
  expect(detail).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Caelynn' }))
  fireEvent(screen.getByRole('dialog', { name: 'Replay node details' }), new Event('cancel', { cancelable: true }))
  expect(screen.queryByRole('dialog', { name: 'Replay node details' })).not.toBeInTheDocument()
})
