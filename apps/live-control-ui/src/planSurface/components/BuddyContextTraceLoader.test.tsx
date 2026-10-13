import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { BuddyTurnContextTrace, WorldAgentTurnContextTraceResponse } from '../../api/buddyContextTraceTypes'
import { BuddyContextTraceLoader } from './BuddyContextTraceLoader'

const props = { worldId:'world', turnId:'turn', conversationId:'conversation' }
function response(attempts: BuddyTurnContextTrace[] = []): WorldAgentTurnContextTraceResponse {
  return {schema:'dmb_agent_turn_context_trace_response_v1', world_id:'world', turn_id:'turn', attempts}
}
function trace(): BuddyTurnContextTrace {
  return {schema:'dmb_turn_context_trace_v1', trace_id:'trace', world_id:'world', turn_id:'turn', conversation_id:'conversation',
    attempt:1, execution_start_sequence:0, started_at:'2026-10-13T00:00:00Z', closed_at:null, terminal_status:null,
    capture_status:'recording', capture_failure_code:null, observations:[]}
}
describe('opt-in turn trace read', () => {
  it('fetches only while enabled, then reuses the exact captured response', async () => {
    const load=vi.fn().mockResolvedValue(response([trace()]))
    const view=render(<BuddyContextTraceLoader {...props} enabled={false} load={load} />)
    expect(load).not.toHaveBeenCalled()
    view.rerender(<BuddyContextTraceLoader {...props} enabled load={load} />)
    await screen.findByText('How Buddy built this reply')
    expect(load).toHaveBeenCalledWith('world','turn')
    view.rerender(<BuddyContextTraceLoader {...props} enabled={false} load={load} />)
    view.rerender(<BuddyContextTraceLoader {...props} enabled load={load} />)
    expect(load).toHaveBeenCalledTimes(1)
  })
  it('does not fabricate trace evidence for a historical turn', async () => {
    render(<BuddyContextTraceLoader {...props} enabled load={vi.fn().mockResolvedValue(response())} />)
    await screen.findByText('No execution trace was captured for this turn.')
  })
  it.each(['world_id','turn_id','conversation_id'])('rejects mismatched trace %s before displaying it', async field => {
    render(<BuddyContextTraceLoader {...props} enabled load={vi.fn().mockResolvedValue(response([{...trace(),[field]:'other'}]))} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Execution trace is unavailable')
    expect(screen.queryByText('How Buddy built this reply')).not.toBeInTheDocument()
  })
  it('discards a late response after the inspected turn changes', async () => {
    let resolve!: (value:WorldAgentTurnContextTraceResponse) => void
    const load=vi.fn().mockReturnValueOnce(new Promise(r=>{resolve=r})).mockResolvedValueOnce({...response(),turn_id:'new-turn'})
    const view=render(<BuddyContextTraceLoader {...props} enabled load={load} />)
    await waitFor(()=>expect(load).toHaveBeenCalledTimes(1))
    view.rerender(<BuddyContextTraceLoader {...props} turnId="new-turn" enabled load={load} />)
    await screen.findByText('No execution trace was captured for this turn.')
    await act(async()=>resolve(response([trace()])))
    expect(screen.queryByText('How Buddy built this reply')).not.toBeInTheDocument()
  })
})
