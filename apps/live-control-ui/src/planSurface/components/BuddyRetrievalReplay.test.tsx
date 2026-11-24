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

function openReplayDetails() {
  const button = screen.queryByRole('button', { name: 'Show replay details' })
  if (button) fireEvent.click(button)
}

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
    expect(screen.getByRole('list', { name: 'Recorded retrieval steps' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
  openReplayDetails()
    expect(screen.getByRole('list', { name: 'Recorded retrieval steps' })).toBeVisible()
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
  openReplayDetails()
    const reopenedSteps = screen.getByRole('list', { name: 'Recorded retrieval steps' })
    expect(within(reopenedSteps).getAllByRole('button')[1]).toHaveAttribute('aria-current', 'step')
    fireEvent.keyDown(first, { key: 'Enter' })
    expect(screen.getByRole('dialog', { name: 'Replay node details' })).toBeVisible()
    expect(within(reopenedSteps).getAllByRole('button')[1]).toHaveAttribute('aria-current', 'step')
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
  openReplayDetails()
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
  openReplayDetails()
  fireEvent.click(screen.getByText('Recorded assertions (426)'))
  expect(screen.getAllByText(/^Open recorded assertion/)).toHaveLength(20)
  fireEvent.change(screen.getByLabelText('Assertion range'), { target: { value: '21' } })
  expect(screen.getAllByText(/^Open recorded assertion/)).toHaveLength(6)
  expect(screen.getByText('Open recorded assertion 426')).toBeInTheDocument()
  expect(screen.queryByText('Open recorded assertion 1')).not.toBeInTheDocument()
})

it('marks only the recorded writer evidence step as playback advances', () => {
  const steps = [lookup(4, 'Caelynn'), lookup(8, 'Mossglade')]
  const trace = { observations: steps, writer_evidence_sequences: [8] } as BuddyTurnContextTrace
  render(<BuddyRetrievalReplay steps={steps} trace={trace} />)
  fireEvent.click(screen.getByRole("button", { name: "Expand" }))
  openReplayDetails()
  const list = screen.getByRole('list', { name: 'Recorded retrieval steps' })
  expect(within(list).getAllByRole('button', { name: /Writer evidence/ })).toHaveLength(1)
  expect(screen.queryByText('Evidence sent to the answer writer')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  expect(screen.getByText('Evidence sent to the answer writer')).toBeInTheDocument()
})

it('scrolls the step list to a selected offscreen step without moving focus', () => {
  render(<BuddyRetrievalReplay steps={Array.from({ length: 10 }, (_, index) => lookup(index + 1, `Object ${index}`))} />)
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
  openReplayDetails()
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
  openReplayDetails()
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
  openReplayDetails()
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
  openReplayDetails()
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Recorded assertions (1)'))
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Open recorded assertion 1'))
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
  render(<BuddyRetrievalReplay steps={[...replaySteps(trace), lookup(5, 'After pruning')]} trace={trace} />)
  const trail = screen.getByRole('group', { name: 'Recorded graph nodes' })
  const seed = within(trail).getByRole('button', { name: 'Caelynn' })
  const position = seed.getAttribute('transform')
  const next = screen.getByRole('button', { name: 'Next step' })
  expect(within(trail).getAllByRole('button')).toHaveLength(1)
  expect(trail.querySelectorAll('line')).toHaveLength(0)
  fireEvent.click(next)
  expect(within(trail).getByRole('button', { name: 'Mossglade' })).toBeInTheDocument()
  expect(within(screen.getByRole('list', { name: 'Recorded retrieval steps' }))
    .getByRole('button', { name: 'Caelynn → Mossglade' })).toHaveAttribute('aria-current', 'step')
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
  fireEvent.click(next)
  expect(screen.getByRole('status')).toHaveTextContent('Step 6 of 6')
  expect(within(trail).getByRole('button', { name: 'Unnamed object' })).toHaveAttribute('data-visit', 'pruned')
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

it.each([
  ['Caelynn', 'original', true],
  ['Mossglade', 'original', false],
  ['Caelynn', 'later', false],
] as const)('grounds the node overview in the retained subject %s and revision %s', async (subject, revision, visible) => {
  setNativeGraphAccessToken('synthetic-replay-reader')
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    if (!String(input).includes('assertion_id=')) return new Response(null, { status: 404 })
    return Response.json({
      schema: 'dmb_replay_native_assertion_v1', world_id: 'elderwyld', turn_id: 'turn', trace_id: 'trace',
      sequence: 1, revision_id: revision,
      assertion: {
        assertion_id: 'claim:1', subject_entity_id: subject, predicate: 'dungeonbuddy:summary',
        value: { kind: 'literal', value: 'The recorded qualifier took place at the arena.' },
      },
      excerpts: [{ evidence_ref_id: 'source:1', text: 'Exact historical excerpt.' }],
    })
  })
  try {
    const trace = {
      trace_id: 'trace', world_id: 'elderwyld', turn_id: 'turn', observations: [],
      native_assertion_steps: [{
        sequence: 1, revision_id: 'original', assertion_ids: ['claim:1', 'claim:other'],
        assertion_ids_by_subject: { Caelynn: ['claim:1'], Mossglade: ['claim:other'] },
        subject_ids: ['Caelynn', 'Mossglade'], subject_labels: { Caelynn: 'Caelynn', Mossglade: 'Mossglade' },
        unavailable_count: 0, writer_evidence: true,
      }],
    } as BuddyTurnContextTrace
    render(<BuddyRetrievalReplay steps={replaySteps(trace)} trace={trace} />)
    fireEvent.click(screen.getByRole('button', { name: 'Caelynn' }))
    const overview = within(screen.getByRole('region', { name: 'What Buddy learned' }))
    if (visible) {
      expect(await overview.findByText('The recorded qualifier took place at the arena.', { selector: 'div > p' })).toBeVisible()
      fireEvent.click(overview.getByText('Open exact evidence'))
      expect(overview.getByText('Exact historical excerpt.')).toBeVisible()
    } else {
      expect(await overview.findByText('Recorded evidence is unavailable.')).toBeVisible()
      expect(overview.queryByText('The recorded qualifier took place at the arena.')).not.toBeInTheDocument()
    }
    expect(fetch.mock.calls.filter(([input]) => String(input).includes('assertion_id='))).toHaveLength(1)
    expect(fetch.mock.calls.some(([input]) => String(input).includes('claim%3Aother'))).toBe(false)
  } finally {
    cleanup()
    fetch.mockRestore()
    setNativeGraphAccessToken(null)
  }
})

it('uses the same playback position when popping out and returning to the conversation', () => {
  render(<BuddyRetrievalReplay steps={[lookup(1, 'Caelynn'), lookup(2, 'Mossglade')]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  fireEvent.click(screen.getByRole('button', { name: 'Pop out replay' }))
  const dialog = within(screen.getByRole('dialog', { name: 'Expanded retrieval replay' }))
  expect(dialog.getByRole('status')).toHaveTextContent('Step 2 of 2')
  expect(dialog.getByRole('list', { name: 'Recorded retrieval steps' })).toBeVisible()
  expect(screen.getAllByRole('group', { name: 'Recorded graph nodes' })).toHaveLength(1)
  fireEvent.click(dialog.getByRole('button', { name: 'Previous step' }))
  fireEvent.click(dialog.getByRole('button', { name: 'Return to conversation' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Step 1 of 2')
})

it('dismisses only the node dialog on Escape and restores focus inside the pop-out', () => {
  render(<BuddyRetrievalReplay steps={[lookup(1, 'Caelynn')]} />)
  fireEvent.click(screen.getByRole('button', { name: 'Pop out replay' }))
  const popout = screen.getByRole('dialog', { name: 'Expanded retrieval replay' })
  const node = within(popout).getByRole('button', { name: 'Caelynn' })
  fireEvent.keyDown(node, { key: 'Enter' })
  const details = within(popout).getByRole('dialog', { name: 'Replay node details' })
  within(details).getByRole('button', { name: 'Close node details' }).focus()
  fireEvent(details, new Event('cancel', { bubbles: true, cancelable: true }))
  expect(screen.queryByRole('dialog', { name: 'Replay node details' })).not.toBeInTheDocument()
  expect(popout).toBeVisible()
  expect(node).toHaveFocus()
  expect(within(popout).getByRole('status')).toHaveTextContent('Step 1 of 1')
  fireEvent(popout, new Event('cancel', { bubbles: true, cancelable: true }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

it('replaces a numbered alias with a recorded name from the same revision', () => {
  const alias = lookup(1, 'Caelynn')
  const named = lookup(2, 'Caelynn')
  alias.revision_pin = named.revision_pin = 'saved'
  alias.result.nodes[0].label = 'Unnamed object 26'
  render(<BuddyRetrievalReplay steps={[alias, named]} />)
  expect(screen.getByRole('button', { name: 'Caelynn', exact: true })).toBeVisible()
  expect(screen.queryByRole('button', { name: /Unnamed object/ })).not.toBeInTheDocument()
})

it('places the animation before the compact playback controls', () => {
  render(<BuddyRetrievalReplay steps={[lookup(1, 'Caelynn'), lookup(2, 'Mossglade')]} />)
  const graph = screen.getByRole('group', { name: 'Recorded graph nodes' })
  const play = screen.getByRole('button', { name: 'Play' })
  expect(graph.compareDocumentPosition(play) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(play).toHaveTextContent('▶')
  expect(screen.getByRole('button', { name: 'Pop out replay' })).toHaveTextContent('↗')
})

it('resolves discovery-only historical names across bounded pages', async () => {
  setNativeGraphAccessToken('synthetic-replay-reader')
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const path = String(input)
    if (!path.includes('/identities')) return new Response(null, { status: 404 })
    return Response.json({
      world_id: 'elderwyld', turn_id: 'turn', trace_id: 'trace',
      identities: path.includes('offset=128')
        ? [{ node_id: 'place', label: 'Stormspire Academy', kind: 'location' }]
        : [],
      next_offset: path.includes('offset=128') ? null : 128,
    })
  })
  try {
    const trace = {
      trace_id: 'trace', world_id: 'elderwyld', turn_id: 'turn', observations: [],
      native_discovery_replay: {
        revision_id: 'saved', seed_ids: ['seed'], labels: { seed: 'Caelynn', place: 'Unnamed object 129' },
        hops: [{ relationship_id: 'hop', from_node_id: 'seed', to_node_id: 'place' }],
      },
    } as BuddyTurnContextTrace
    render(<BuddyRetrievalReplay steps={replaySteps(trace)} trace={trace} />)
    fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
    expect(await screen.findByRole('button', { name: 'Stormspire Academy', exact: true })).toBeVisible()
    expect(fetch.mock.calls.filter(([input]) => String(input).includes('/identities'))).toHaveLength(2)
    fireEvent.keyDown(screen.getByRole('button', { name: 'Stormspire Academy', exact: true }), { key: 'Enter' })
    expect(within(screen.getByRole('dialog', { name: 'Replay node details' }))
      .getByRole('heading', { name: 'Stormspire Academy' })).toBeVisible()
  } finally {
    cleanup()
    fetch.mockRestore()
    setNativeGraphAccessToken(null)
  }
})
