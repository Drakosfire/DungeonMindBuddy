import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BuddyActivity, activityObservations } from './BuddyActivity'
import { BuddyTurnInspection } from './BuddyTurnInspection'
import type { BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'
import type { AgentConversationTurnLifecycleV1 } from '../../api/types'

const binding = {worldId:'world',conversationId:'conversation',turnId:'turn'}
const trace = (observations: BuddyTurnContextTrace['observations']): BuddyTurnContextTrace => ({
  schema:'dmb_turn_context_trace_v1',world_id:'world',conversation_id:'conversation',turn_id:'turn',trace_id:'trace',
  attempt:1,started_at:'2026-10-24T00:00:00Z',closed_at:null,execution_start_sequence:0,
  terminal_status:null,capture_status:'recording',capture_failure_code:null,observations,
})
function mount(captured: BuddyTurnContextTrace, lifecycle: AgentConversationTurnLifecycleV1 = 'running') {
  const load=vi.fn().mockResolvedValue({schema:'dmb_agent_turn_context_trace_response_v1',world_id:'world',turn_id:'turn',attempts:[captured]})
  const loadPrompt=vi.fn()
  render(<BuddyTurnInspection {...binding} lifecycle={lifecycle} load={load} loadPrompt={loadPrompt}>
    <BuddyActivity {...binding} lifecycle={lifecycle} />
  </BuddyTurnInspection>)
  return {load,loadPrompt}
}
describe('live activity entrance',()=>{
  it('uses actual observed events and expands a light timeline without prompts',async()=>{
    const {load,loadPrompt}=mount(trace([{kind:'provider_call',sequence:0,elapsed_ms:1200,
      provider:'typesafe',model:'jev',outcome:'response_received'}]))
    await screen.findByText('A model response just landed.')
    expect(load).toHaveBeenCalledTimes(1)
    expect(screen.queryByText(/Attempt 1/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('A model response just landed.'))
    await screen.findByText(/Attempt 1/)
    expect(screen.getByText('1.2s')).toBeInTheDocument()
    expect(loadPrompt).not.toHaveBeenCalled()
    expect(screen.queryByText('Copy trace')).not.toBeInTheDocument()
  })
  it('does not fetch a completed trace until the quiet entry is opened',async()=>{
    const {load}=mount({...trace([]),terminal_status:'completed',closed_at:'2026-10-24T00:00:01Z',capture_status:'complete'},'completed')
    expect(load).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('How this reply came together'))
    await waitFor(()=>expect(load).toHaveBeenCalledTimes(1))
    await screen.findByText(/Attempt 1/)
  })
  it('keeps terminal failures in the same entry with the recorded error code',async()=>{
    mount({...trace([{kind:'failure',sequence:0,elapsed_ms:23700,phase:'delivery',code:'build_source_name_missing',stage:'context_acquisition'}]),terminal_status:'interrupted'},'interrupted')
    fireEvent.click(screen.getByText('Reply error report'))
    await screen.findByText(/build_source_name_missing/)
    expect(screen.getByText(/context_acquisition/)).toBeInTheDocument()
  })
})

it('updates the running line from a later recorded observation', async()=>{
  const initial=trace([{kind:'provider_call',sequence:0,elapsed_ms:0,provider:'typesafe',model:'jev',outcome:'authorized'}])
  const {load}=mount(initial)
  await screen.findByText('Model call cleared for takeoff…')
  load.mockResolvedValue({schema:'dmb_agent_turn_context_trace_response_v1',world_id:'world',turn_id:'turn',attempts:[trace([
    {kind:'context_snapshot',snapshot_kind:'provider_response',sequence:1,elapsed_ms:2000,stage:'after',materials:[]}
  ])]})
  await screen.findByText('Response captured for inspection.', {}, {timeout:3500})
  expect(load).toHaveBeenCalledTimes(2)
})

it.each([
  [null,'A captured snapshot of the notes.'],
  ['provider_response','Response captured for inspection.'],
  ['validated_answer','The reply is assembled.'],
] as const)('describes %s snapshots without inventing context changes',async(snapshot_kind,label)=>{
  mount(trace([{kind:'context_snapshot',snapshot_kind,stage:'after',sequence:0,elapsed_ms:1,materials:[]}]))
  await screen.findByText(label)
  expect(screen.queryByText('The working notes have been updated.')).not.toBeInTheDocument()
})
it('reports an observed saved-page read without claiming any page edit',async()=>{
  mount(trace([{kind:'context_decision',action:'retrieved',item_ids:['Households · saved revision 9'],reason_code:'question_relevance',
    policy_version:'selected_exact_related_authored_pages_v1',sequence:0,elapsed_ms:1}]))
  await screen.findByText('Another page joins the reading pile.')
})

const response = (sequence:number,id:string|null,extra:Record<string,unknown> = {}): BuddyTurnContextTrace['observations'][number] => ({
  kind:'provider_call',sequence,elapsed_ms:sequence*100,provider_attempt_id:id,provider:'typesafe',model:'jev',outcome:'response_received',...extra,
})
it('shows one arrival per identified call without changing raw evidence or regressing to a usage update',async()=>{
  const snapshot={kind:'context_snapshot' as const,snapshot_kind:'provider_response' as const,stage:'after' as const,sequence:2,elapsed_ms:200,materials:[]}
  const observations=[response(0,'first'),response(1,'second'),snapshot,response(3,'first',{input_tokens:100,output_tokens:12}),response(4,'second',{input_tokens:200})]
  const original=structuredClone(observations)
  const result=activityObservations(observations)
  expect(result.map(e=>e.sequence)).toEqual([0,1,2])
  expect(observations).toEqual(original)
  mount(trace(observations))
  await screen.findByText('Response captured for inspection.')
  fireEvent.click(screen.getByText('Response captured for inspection.'))
  await screen.findByText(/Attempt 1/)
  expect(screen.getAllByText('· A model response just landed.',{exact:false})).toHaveLength(2)
  expect(screen.getByText('0.0s')).toBeInTheDocument()
  expect(screen.queryByText('0.3s')).not.toBeInTheDocument()
})
it('preserves anonymous observations, different models, other outcomes and every failure',()=>{
  const failure={kind:'failure' as const,sequence:7,elapsed_ms:700,phase:'delivery',code:'test_failure'}
  const observations=[response(0,null),response(1,null),response(2,'same'),response(3,'same',{model:'writer'}),response(4,'same',{outcome:'failed'}),response(5,'same',{outcome:'unknown'}),response(6,'same'),failure]
  expect(activityObservations(observations).map(e=>e.sequence)).toEqual([0,1,2,3,4,5,7])
})
