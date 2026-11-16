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
