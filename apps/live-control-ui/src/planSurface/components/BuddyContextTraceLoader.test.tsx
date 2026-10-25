import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { BuddyTurnContextTrace, WorldAgentTurnContextTraceResponse } from '../../api/buddyContextTraceTypes'
import { BuddyContextTraceLoader as TraceView } from './BuddyContextTraceLoader'
import { BuddyTurnInspection } from './BuddyTurnInspection'
import type { ComponentProps } from 'react'
import type { getWorldAgentTurnContextTrace, getWorldAgentTurnPrompt } from '../../api/liveApi'

function BuddyContextTraceLoader({ load, loadPrompt, running, ...props }: ComponentProps<typeof TraceView> & { load?: typeof getWorldAgentTurnContextTrace; loadPrompt?: typeof getWorldAgentTurnPrompt; running?: boolean }) {
  return <BuddyTurnInspection {...props} load={load} loadPrompt={loadPrompt} lifecycle={running ? "running" : "completed"}><TraceView {...props} /></BuddyTurnInspection>
}

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
  afterEach(() => vi.useRealTimers())
  it('fetches only while enabled, then reuses the exact captured response', async () => {
    const load=vi.fn().mockResolvedValue(response([{...trace(), closed_at:'2026-10-13T00:00:01Z', terminal_status:'completed', capture_status:'complete'}]))
    const view=render(<BuddyContextTraceLoader {...props} enabled={false} load={load} />)
    expect(load).not.toHaveBeenCalled()
    view.rerender(<BuddyContextTraceLoader {...props} enabled load={load} />)
    await screen.findByText('How Buddy built this reply')
    expect(load).toHaveBeenCalledWith('world','turn',expect.any(AbortSignal))
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
  it('updates a recording trace in place and stops polling when the owning turn ends', async () => {
    vi.useFakeTimers()
    const finished = {...trace(), closed_at:'2026-10-13T00:00:01Z', terminal_status:'completed' as const,
      capture_status:'complete' as const, observations:[{kind:'provider_call' as const, sequence:0, elapsed_ms:1,
        provider:'openai-api', model:'actual-model', outcome:'response_received' as const, input_tokens:42, output_tokens:7}]}
    const load=vi.fn().mockResolvedValueOnce(response([trace()])).mockResolvedValue(response([finished]))
    const view=render(<BuddyContextTraceLoader {...props} enabled running load={load} />)
    await act(async()=>{})
    const header=screen.getByText('How Buddy built this reply')
    await act(async()=>vi.advanceTimersByTimeAsync(2000))
    expect(screen.getByText('How Buddy built this reply')).toBe(header)
    expect(screen.getByText('actual-model')).toBeInTheDocument()
    view.rerender(<BuddyContextTraceLoader {...props} enabled load={load} />)
    await act(async()=>{})
    expect(load).toHaveBeenCalledTimes(3)
    await act(async()=>vi.advanceTimersByTimeAsync(10000))
    expect(load).toHaveBeenCalledTimes(3)
  })
  it('preserves captured observations when an update fails and retries only the trace read', async () => {
    vi.useFakeTimers()
    const load=vi.fn().mockResolvedValueOnce(response([trace()])).mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValue(response([{...trace(),closed_at:'2026-10-13T00:00:01Z',terminal_status:'failed'}]))
    render(<BuddyContextTraceLoader {...props} enabled running load={load} />)
    await act(async()=>{})
    const header=screen.getByText('How Buddy built this reply')
    await act(async()=>vi.advanceTimersByTimeAsync(2000))
    expect(screen.getByText('How Buddy built this reply')).toBe(header)
    expect(screen.getByRole('alert')).toHaveTextContent('The message will not be resent')
    await act(async()=>vi.advanceTimersByTimeAsync(10000))
    expect(load).toHaveBeenCalledTimes(2)
    await act(async()=>screen.getByText('Retry trace read').click())
    expect(load).toHaveBeenCalledTimes(3)
    expect(screen.queryByText('Execution trace is unavailable. The message will not be resent.')).not.toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('The specific cause was not recorded')
  })
  it('cancels recording-trace updates when Debug closes', async () => {
    vi.useFakeTimers()
    const load=vi.fn().mockResolvedValue(response([trace()]))
    const view=render(<BuddyContextTraceLoader {...props} enabled running load={load} />)
    await act(async()=>{})
    view.rerender(<BuddyContextTraceLoader {...props} enabled={false} running load={load} />)
    await act(async()=>vi.advanceTimersByTimeAsync(10000))
    expect(load).toHaveBeenCalledTimes(1)
  })
  it('finds capture that starts after the first read of a newly running turn', async () => {
    vi.useFakeTimers()
    const load=vi.fn().mockResolvedValueOnce(response()).mockResolvedValue(response([trace()]))
    render(<BuddyContextTraceLoader {...props} enabled running load={load} />)
    await act(async()=>{})
    expect(screen.getByText('Trace capture has not started yet.')).toBeInTheDocument()
    await act(async()=>vi.advanceTimersByTimeAsync(2000))
    expect(screen.getByText('How Buddy built this reply')).toBeInTheDocument()
    expect(load).toHaveBeenCalledTimes(2)
  })
  it('shows an ended turn with an unclosed capture as incomplete without background polling', async () => {
    vi.useFakeTimers()
    const saved=trace(), load=vi.fn().mockResolvedValue(response([saved]))
    const view=render(<BuddyContextTraceLoader {...props} enabled load={load} />)
    await act(async()=>{})
    expect(screen.getByText('Incomplete capture')).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('The turn has ended')
    expect(saved.closed_at).toBeNull()
    await act(async()=>vi.advanceTimersByTimeAsync(10000))
    expect(load).toHaveBeenCalledTimes(1)
    view.rerender(<BuddyContextTraceLoader {...props} enabled={false} load={load} />)
    view.rerender(<BuddyContextTraceLoader {...props} enabled load={load} />)
    await act(async()=>{})
    expect(load).toHaveBeenCalledTimes(2)
  })

})

it("opens a failed turn's exact captured request within Debug only on demand", async () => {
  const reference = {kind:'prompt_reference' as const,sequence:0,elapsed_ms:0,provider_attempt_id:'call',
    evidence_id:'evidence',provider:'openai',model:'model',api_mode:'responses',serializer_version:'fixture',
    payload_sha256:'a'.repeat(64),payload_utf8_bytes:18}
  const captured = {...trace(),closed_at:'2026-10-13T00:00:01Z',terminal_status:'failed' as const,
    capture_status:'complete' as const,observations:[reference]}
  const loadPrompt=vi.fn().mockResolvedValue({schema:'dmb_agent_prompt_evidence_v1',world_id:'world',
    conversation_id:'conversation',turn_id:'turn',trace_id:'trace',attempt:1,reference,
    payload_json:JSON.stringify({model:'model',input:'Exact image direction request'})})
  render(<BuddyContextTraceLoader {...props} enabled load={vi.fn().mockResolvedValue(response([captured]))} loadPrompt={loadPrompt} />)
  const control = await screen.findByText('Working context · composed input prompt · model', {selector:'summary'})
  expect(loadPrompt).not.toHaveBeenCalled()
  fireEvent.click(control)
  await screen.findByRole('heading',{name:'Full composed request'})
  expect(loadPrompt).toHaveBeenCalledTimes(1)
  expect(loadPrompt).toHaveBeenCalledWith('world','turn','trace','call',expect.any(AbortSignal))
  expect(screen.getByLabelText('Captured request')).toHaveTextContent('Exact image direction request')
})

it.each([false,true])('reads only the selected input and previous capture on demand; missing previous=%s', async missing => {
  const refs=['one','two','three'].map((id,sequence)=>({kind:'prompt_reference' as const,sequence,elapsed_ms:sequence,
    provider_attempt_id:id,evidence_id:id,provider:'typesafe',model:id,api_mode:'decision',serializer_version:'fixture',
    payload_sha256:'a'.repeat(64),payload_utf8_bytes:18}))
  const captured={...trace(),observations:refs,closed_at:'2026-10-13T00:00:01Z',capture_status:'complete' as const}
  const loadPrompt=vi.fn().mockImplementation(async (_world,_turn,_trace,id) => {
    if(missing && id==='two') throw new Error('missing previous')
    return {schema:'dmb_agent_prompt_evidence_v1',world_id:'world',conversation_id:'conversation',turn_id:'turn',trace_id:'trace',attempt:1,
      reference:refs.find(ref=>ref.provider_attempt_id===id),payload_json:JSON.stringify({input:id})}
  })
  render(<BuddyContextTraceLoader {...props} enabled load={vi.fn().mockResolvedValue(response([captured]))} loadPrompt={loadPrompt} />)
  const control=await screen.findByText('Working context · composed input prompt · three',{selector:'summary'})
  expect(loadPrompt).not.toHaveBeenCalled()
  fireEvent.click(control)
  await screen.findByRole('heading',{name:'Full composed request'})
  expect(loadPrompt.mock.calls.map(call=>call[3])).toEqual(['three','two'])
  expect(screen.getByLabelText('Captured request')).toHaveTextContent('three')
  if(missing) {
    expect(screen.getByText(/previous captured input is unavailable/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Changes since previous model call')).not.toBeInTheDocument()
  } else {
    expect(screen.getByLabelText('Changes since previous model call')).toHaveTextContent('Changed · input')
  }
})

it('retries an initial pre-admission trace miss while genuinely running', async()=>{
  vi.useFakeTimers()
  const load=vi.fn().mockRejectedValueOnce(new Error('not captured yet')).mockResolvedValue(response([trace()]))
  const view=render(<BuddyContextTraceLoader {...props} enabled running load={load}/>)
  await act(async()=>{})
  expect(load).toHaveBeenCalledTimes(1)
  await act(async()=>vi.advanceTimersByTimeAsync(2000))
  expect(load).toHaveBeenCalledTimes(2)
  expect(screen.getByText('How Buddy built this reply')).toBeInTheDocument()
  view.unmount();await act(async()=>vi.advanceTimersByTimeAsync(10000))
  expect(load).toHaveBeenCalledTimes(2)
  vi.useRealTimers()
})
