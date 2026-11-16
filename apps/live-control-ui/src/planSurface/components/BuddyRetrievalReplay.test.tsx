import type { BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { BuddyRetrievalReplay, type RetrievalStep } from './BuddyRetrievalReplay'

function lookup(sequence: number, label: string): RetrievalStep {
  return {
    sequence,
    request: { operation: 'object' },
    result: {
      nodes: [{ node_id: label, label, kind: 'person' }],
      relationship_ids: [],
      evidence_ref_ids: [],
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
