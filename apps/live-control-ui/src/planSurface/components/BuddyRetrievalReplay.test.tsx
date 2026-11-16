import { setNativeGraphAccessToken } from '../../api/liveApi'
import type { BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { BuddyRetrievalReplay, replaySteps, type RetrievalStep } from './BuddyRetrievalReplay'

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
    const trail = screen.getByRole('group', { name: 'Operations and returned objects' })
    const steps = screen.getByRole('list', { name: 'Recorded retrieval steps' })
    const first = within(trail).getByRole('button', { name: /^Step 1,/ })
    const second = within(trail).getByRole('button', { name: /^Step 2,/ })
    expect(first).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    act(() => vi.advanceTimersByTime(2000))
    expect(first).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Play' }))
    act(() => vi.advanceTimersByTime(1000))
    expect(second).toHaveAttribute('aria-pressed', 'true')
    expect(within(steps).getAllByRole('button')[1]).toHaveAttribute('aria-current', 'step')
    fireEvent.keyDown(first, { key: 'Enter' })
    expect(within(steps).getAllByRole('button')[0]).toHaveAttribute('aria-current', 'step')
  } finally {
    vi.useRealTimers()
  }
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
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  expect(screen.getByRole('heading', { name: 'Read native assertions' })).toBeInTheDocument()
  expect(screen.getByText('Evidence sent to the answer writer')).toBeInTheDocument()
})

it('keeps the last assertion in a dense batch reachable with bounded controls', () => {
  const step = lookup(4, 'Caelynn')
  step.result.claim_ids = Array.from({ length: 426 }, (_, index) => `claim:${index + 1}`)
  const trace = { observations: [step] } as BuddyTurnContextTrace
  render(<BuddyRetrievalReplay trace={trace} steps={[step]} />)
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
  const list = screen.getByRole('list', { name: 'Recorded retrieval steps' })
  expect(within(list).getAllByRole('button', { name: /Writer evidence/ })).toHaveLength(1)
  expect(screen.queryByText('Evidence sent to the answer writer')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Next step' }))
  expect(screen.getByText('Evidence sent to the answer writer')).toBeInTheDocument()
})

it('scrolls both panes to a selected offscreen step without moving focus', () => {
  render(<BuddyRetrievalReplay steps={Array.from({ length: 10 }, (_, index) => lookup(index + 1, `Object ${index}`))} />)
  const trail = screen.getByRole('group', { name: 'Operations and returned objects' })
  const pane = trail.parentElement!
  const list = screen.getByRole('list', { name: 'Recorded retrieval steps' })
  const last = within(list).getAllByRole('button').at(-1)!
  const trailRow = within(trail).getByRole('button', { name: /^Step 10,/ }).parentElement!
  const bounds = (top: number, height: number) => new DOMRect(0, top, 200, height)
  vi.spyOn(pane, 'getBoundingClientRect').mockReturnValue(bounds(0, 200))
  vi.spyOn(list, 'getBoundingClientRect').mockReturnValue(bounds(0, 200))
  vi.spyOn(trailRow, 'getBoundingClientRect').mockReturnValue(bounds(750, 68))
  vi.spyOn(last.parentElement!, 'getBoundingClientRect').mockReturnValue(bounds(315, 34))
  last.focus()
  fireEvent.click(last)
  expect(pane.scrollTop).toBe(618)
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
  expect(screen.getByText('Returned relationships (1)')).toBeInTheDocument()
  expect(screen.getAllByText('Caelynn → Mossglade')).toHaveLength(2)
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
