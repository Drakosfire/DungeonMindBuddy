import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BuddyContextTrace, type BuddyTurnContextTrace } from './BuddyContextTrace'

function trace(observations: BuddyTurnContextTrace['observations']): BuddyTurnContextTrace {
  return { schema: 'dmb_turn_context_trace_v1', trace_id: 'trace', world_id: 'world',
    conversation_id: 'conversation', turn_id: 'turn', attempt: 1,
    started_at: '2026-10-13T00:00:00Z', closed_at: '2026-10-13T00:00:01Z', observations }
}

describe('Buddy context trace', () => {
  it('labels absent historical evidence honestly', () => {
    render(<BuddyContextTrace trace={null} />)
    expect(screen.getByText('No execution trace was captured for this turn.')).toBeInTheDocument()
  })
  it('distinguishes estimates from actual model usage', () => {
    render(<BuddyContextTrace trace={trace([{kind:'provider_call', sequence:0, elapsed_ms:0,
      provider:'openai-api', model:'model', outcome:'authorized', input_upper_bound:67797,
      input_estimator:'upper_bound'}])} />)
    expect(screen.getByText(/conservative estimate, not actual token usage/)).toBeInTheDocument()
    expect(screen.getByText(/Actual token usage was not captured/)).toBeInTheDocument()
    expect(screen.queryByText(/Provider-reported usage/)).not.toBeInTheDocument()
  })
  it('keeps a retained route distinct from context prose', () => {
    render(<BuddyContextTrace trace={trace([{kind:'context_snapshot', stage:'after', sequence:0,
      elapsed_ms:1, materials:[{item_id:'source', state:'retrieval_route',
        route:{route_id:'source', world_id:'world', graph_revision:'rev', anchor_id:'anchor'}}]}])} />)
    fireEvent.click(screen.getByText('Working context · after this turn'))
    expect(screen.getByText('Present in model context')).toBeInTheDocument()
    expect(screen.getByText('Available through retained routes')).toBeInTheDocument()
    expect(screen.getByText(/passage is not currently present/)).toBeInTheDocument()
  })
  it('preserves the full result and identifies denied reads as non-evidence', () => {
    const passage='Full source passage. '.repeat(1000)
    render(<BuddyContextTrace trace={trace([{kind:'graph_tool', sequence:0, elapsed_ms:2,
      tool_name:'read_graph_source', arguments:{anchorIds:['anchor']},
      result:{content:passage, code:'source_anchor_not_admitted'}, outcome:'denied', execution_event_ids:[]}])} />)
    fireEvent.click(screen.getByText('Read supporting source'))
    fireEvent.click(screen.getByText('Complete returned result'))
    expect(screen.getByText(/This result supplies no admitted evidence/)).toBeInTheDocument()
    expect(screen.getByText(/"content":/).textContent).toContain(passage)
  })
  it('opens complete admitted passages as readable prose', () => {
    const passage='Mirathorn source passage. '.repeat(1000)
    render(<BuddyContextTrace trace={trace([{kind:'graph_tool', sequence:0, elapsed_ms:2,
      tool_name:'read_graph_source', arguments:{anchorIds:['anchor']},
      result:{reads:[{result:{content:passage}}]}, outcome:'returned', execution_event_ids:['read']}])} />)
    fireEvent.click(screen.getByText('Read supporting source'))
    fireEvent.click(screen.getByText('Source passage 1'))
    expect(screen.getByText(passage.trim()).tagName).toBe('BLOCKQUOTE')
  })
})
