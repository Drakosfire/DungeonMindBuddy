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
  it('uses actual observed events and expands the full timeline without prompts',async()=>{
    const {load,loadPrompt}=mount(trace([{kind:'provider_call',sequence:0,elapsed_ms:1200,
      provider:'typesafe',model:'jev',outcome:'response_received'}]))
    await screen.findByText('A response has arrived.')
    const activity=screen.getByRole('status').closest('details')!
    expect(activity).toHaveAttribute('data-running','true')
    expect(activity.querySelector('svg')).toHaveAttribute('aria-hidden','true')
    expect(activity.querySelector('svg')).toHaveAttribute('focusable','false')
    expect(activity.querySelectorAll('.buddy-activity__dot')).toHaveLength(3)
    expect(load).toHaveBeenCalledTimes(1)
    expect(screen.queryByText(/Observable execution · attempt 1/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('A response has arrived.'))
    await screen.findByText(/Observable execution · attempt 1/)
    expect(screen.getByText('1.2s')).toBeInTheDocument()
    expect(loadPrompt).not.toHaveBeenCalled()
    expect(screen.getByText('Copy trace')).toBeInTheDocument()
  })
  it('does not fetch a completed trace until the quiet entry is opened',async()=>{
    const {load}=mount({...trace([]),terminal_status:'completed',closed_at:'2026-10-24T00:00:01Z',capture_status:'complete'},'completed')
    expect(load).not.toHaveBeenCalled()
    const activity=screen.getByRole('status').closest('details')!
    expect(activity).toHaveAttribute('data-running','false')
    expect(activity.querySelector('svg')).toBeNull()
    fireEvent.click(screen.getByText('How this reply came together'))
    await waitFor(()=>expect(load).toHaveBeenCalledTimes(1))
    await screen.findByText(/Observable execution · attempt 1/)
  })
  it('keeps terminal failures in the same entry with the recorded error code',async()=>{
    mount({...trace([{kind:'failure',sequence:0,elapsed_ms:23700,phase:'delivery',code:'build_source_name_missing',stage:'context_acquisition'}]),terminal_status:'interrupted'},'interrupted')
    const activity=screen.getByRole('status').closest('details')!
    expect(activity).toHaveAttribute('data-running','false')
    expect(activity.querySelector('svg')).toBeNull()
    fireEvent.click(screen.getByText('Reply error report'))
    await screen.findAllByText(/build_source_name_missing/)
    expect(screen.getAllByText(/context_acquisition/).length).toBeGreaterThan(0)
  })
})

it('updates the running line from a later recorded observation', async()=>{
  const initial=trace([{kind:'provider_call',sequence:0,elapsed_ms:0,provider:'typesafe',model:'jev',outcome:'authorized'}])
  const {load}=mount(initial)
  await screen.findByText('Waiting for a response…')
  load.mockResolvedValue({schema:'dmb_agent_turn_context_trace_response_v1',world_id:'world',turn_id:'turn',attempts:[trace([
    {kind:'context_snapshot',snapshot_kind:'provider_response',sequence:1,elapsed_ms:2000,stage:'after',materials:[]}
  ])]})
  await screen.findByText('Checking the response…', {}, {timeout:3500})
  expect(load).toHaveBeenCalledTimes(2)
})

it.each([
  [null,'A captured snapshot of the notes.'],
  ['provider_response','Checking the response…'],
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
  await screen.findByText('Checking the response…')
  fireEvent.click(screen.getByText('Checking the response…'))
  await screen.findByText(/Observable execution · attempt 1/)
  expect(document.querySelectorAll('.buddy-context-trace > details > ol > li')).toHaveLength(3)
  expect(screen.getByText('0.0s')).toBeInTheDocument()
  expect(screen.getByText(/usage updated at 0.3s/)).toBeInTheDocument()
})
it('preserves anonymous observations, different models, other outcomes and every failure',()=>{
  const failure={kind:'failure' as const,sequence:7,elapsed_ms:700,phase:'delivery',code:'test_failure'}
  const observations=[response(0,null),response(1,null),response(2,'same'),response(3,'same',{model:'writer'}),response(4,'same',{outcome:'failed'}),response(5,'same',{outcome:'unknown'}),response(6,'same'),failure]
  expect(activityObservations(observations).map(e=>e.sequence)).toEqual([0,1,2,3,4,5,7])
})

it('shows the retained author action without claiming a model call',async()=>{
  mount(trace([{kind:'context_decision',action:'retained',item_ids:['Reviewed step · Prepare an insertion'],reason_code:'route_preserved',
    policy_version:'reviewed_author_action_v1',sequence:0,elapsed_ms:1}]))
  await screen.findByText('Following your reviewed step.')
  expect(screen.queryByText('A response has arrived.')).not.toBeInTheDocument()
})

it.each(['selected','authorized','read','read_partial','source_gap','prepared'] as const)('shows truthful authored-reference live activity: %s',async stage=>{
  const base={event_id:'app-event',sequence:2},capture_event_id='captured';
  let execution:import('../../api/buddyContextTraceTypes').BuddyAuthoredTraceEvent;
  if(stage==='selected')execution={...base,kind:'build_authored_references_captured_v1',references:{schema:'dmb_authored_graph_references_v1',references:[]},read_graph_revision:'revision',turn_id:'turn',conversation_id:'conversation',attempt:1,submitted_intent_fingerprint:'a'.repeat(64)};
  else if(stage==='authorized')execution={...base,kind:'build_authored_reference_authorized_v1',capture_event_id,node_id:'cedar-box',arguments_sha256:'a'.repeat(64)};
  else if(stage==='prepared')execution={...base,kind:'build_authored_provider_inclusion_v1',capture_event_id,references_sha256:'a'.repeat(64),source_read_event_ids:['source'],provider_attempt_id:'writer',envelope_sha256:'b'.repeat(64),material_sha256:'c'.repeat(64)};
  else execution={...base,kind:'build_authored_reference_read_v1',capture_event_id,authorization_event_id:'authorization',node_id:'cedar-box',operation_event_ids:['object-read'],source_read_event_ids:['source'],returned_node_ids:['cedar-box'],outcome:stage};
  const labels={selected:'Your Graph references are on the reading list.',authorized:'Opening the object you picked…',read:'Checked the object and its source receipts.',read_partial:'That object read came back incomplete.',source_gap:'The object is missing complete source support.',prepared:'Graph context packed for the writer.'};
  const {load,loadPrompt}=mount(trace([{kind:'authored_graph_reference_v1',sequence:0,elapsed_ms:1,execution_event:execution}]));
  await screen.findByText(labels[stage]);expect(load).toHaveBeenCalledTimes(1);expect(loadPrompt).not.toHaveBeenCalled();expect(screen.queryByText('A response has arrived.')).toBeNull();
  if(stage!=='read')expect(screen.queryByText(labels.read)).toBeNull();
});


it('opens every recorded event in the existing timeline, with no shortened activity list',async()=>{
  const observations=Array.from({length:18},(_,sequence)=>({kind:'failure' as const,phase:'tool',code:`recorded_${sequence}`,sequence,elapsed_ms:sequence*100}));
  const {loadPrompt}=mount(trace(observations));
  fireEvent.click(await screen.findByText('Hit a snag—open the report.'));
  const timeline=await screen.findByText('Execution timeline');
  expect(timeline.closest('details')).toHaveAttribute('open');
  expect(document.querySelectorAll('.buddy-context-trace > details > ol > li')).toHaveLength(18);
  expect(screen.getByText(/recorded_0$/)).toBeInTheDocument();expect(screen.getByText(/recorded_17$/)).toBeInTheDocument();
  expect(screen.queryByText('Prompts and technical details')).toBeNull();
  expect(document.querySelector('.buddy-activity__body > ol')).toBeNull();
  expect(loadPrompt).not.toHaveBeenCalled();
});

it('describes the actual Graph search without replacing it with a generic receipt update',async()=>{
  const graph:import('../../api/buddyContextTraceTypes').BuddyTraceObservation={kind:'graph_tool',sequence:0,elapsed_ms:1,
    tool_name:'expand_graph_retrieval',execution_event_id:'event',request_arguments_sha256:'a'.repeat(64),result_packet_sha256:'b'.repeat(64),
    scope_mode:'world',campaign_id:null,revision_pin:'revision',request:{operation:'search',query_text:'meat creatures in Session 20',seed_node_ids:[]},
    result:{outcome:'partial',graph_revision:'revision',coverage_status:'incomplete',projection_status:'limited',nodes:[],relationship_ids:[],claim_ids:[],evidence_ref_ids:[],returned_counts:{nodes:0,relationships:0,claims:0,evidence_refs:0},total_counts:{nodes:0,relationships:0,claims:0,evidence_refs:0},omission_codes:[]}};
  mount(trace([graph,{kind:'provider_call',sequence:1,elapsed_ms:2,provider:'typesafe',model:'jev',outcome:'response_received'}]));
  expect(await screen.findByText('Graph search: “meat creatures in Session 20” · partial.')).toBeInTheDocument();
  expect(screen.queryByText('A response has arrived.')).toBeNull();
});

it('keeps issued native source progress through generic model updates and adopts it in the timeline', async()=>{
  const {loadPrompt}=mount(trace([
    {kind:'context_decision',action:'expanded',item_ids:['native-body:selected'],reason_code:'question_relevance',
      policy_version:'native_source_section_read_progress_v1',sequence:0,elapsed_ms:1000},
    {kind:'provider_call',provider:'typesafe',model:'jev',outcome:'authorized',sequence:1,elapsed_ms:2000},
  ]))
  await screen.findByText('Reading selected source section…')
  fireEvent.click(screen.getByText('Reading selected source section…'))
  await waitFor(()=>expect(screen.getAllByText('Reading selected source section…')).toHaveLength(2))
  expect(loadPrompt).not.toHaveBeenCalled()
})

it.each([
  ['expanded','question_relevance','Searching retained source sections…'],
  ['retrieved','question_relevance','Retained source search completed.'],
  ['retained','unavailable','Retained source search was unavailable.'],
] as const)('renders the recorded native search outcome %s',async(action,reason_code,label)=>{
  mount(trace([{kind:'context_decision',action,reason_code,item_ids:['native-corpus-search:selected'],
    policy_version:'native_source_search_progress_v1',sequence:0,elapsed_ms:1000}]))
  await screen.findByText(label)
})

it('does not let native progress conceal a subsequent terminal failure',async()=>{
  mount({...trace([
    {kind:'context_decision',action:'expanded',item_ids:['native-body:selected'],reason_code:'question_relevance',
      policy_version:'native_source_section_read_progress_v1',sequence:0,elapsed_ms:1000},
    {kind:'failure',phase:'source_read',code:'native_source_unavailable',sequence:1,elapsed_ms:2000},
  ]),terminal_status:'interrupted'},'interrupted')
  fireEvent.click(screen.getByText('Reply error report'))
  await screen.findAllByText(/native_source_unavailable/)
})


it.each([
  ['source_search','expanded','question_relevance','What happened at the tower?','Searching sources for “What happened at the tower?”…'],
  ['source_search','retrieved','question_relevance','What happened at the tower?','Finished source search for “What happened at the tower?”.'],
  ['source_document_read','expanded','question_relevance','Session 8 recap · campaign: c1','Reading Session 8 recap · campaign: c1…'],
  ['source_section_read','retrieved','question_relevance','Session 8 recap · Arrival · lines 12–19','Read Session 8 recap · Arrival · lines 12–19.'],
  ['source_section_read','retained','unavailable','Session 8 recap · Arrival','Could not read complete support from Session 8 recap · Arrival.'],
] as const)('names issued native %s %s in activity and full timeline',async(operation,action,reason_code,label,expected)=>{
  mount(trace([{kind:'context_decision',action,reason_code,item_ids:['native:exact-selected-target',label],
    policy_version:`native_${operation}_progress_v2`,sequence:0,elapsed_ms:1000},
    {kind:'provider_call',provider:'typesafe',model:'jev',outcome:'authorized',sequence:1,elapsed_ms:2000}]))
  const status=await screen.findByText(expected)
  expect(status).toHaveAttribute('title',expected)
  fireEvent.click(status)
  await waitFor(()=>expect(screen.getAllByText(expected)).toHaveLength(2))
  expect(screen.getByText('Execution timeline').closest('details')).toHaveAttribute('open')
})


it('does not let a named source request conceal the terminal failure',async()=>{
  mount({...trace([
    {kind:'context_decision',action:'expanded',reason_code:'question_relevance',
      item_ids:['native:exact-selected-target','Session 8 recap · Arrival · lines 12–19'],
      policy_version:'native_source_section_read_progress_v2',sequence:0,elapsed_ms:1000},
    {kind:'failure',phase:'source_read',code:'native_source_unavailable',sequence:1,elapsed_ms:2000},
  ]),terminal_status:'interrupted'},'interrupted')
  fireEvent.click(screen.getByText('Reply error report'))
  await screen.findAllByText(/native_source_unavailable/)
  expect(screen.getByText('Reading Session 8 recap · Arrival · lines 12–19…')).toBeInTheDocument()
})


it('shows the captured writer response instead of an earlier retrieval, including its late usage',async()=>{
  const attempt='2c75f1da-9277-4dca-8cd2-e5b8e659bd97'
  const receipt='a'.repeat(64)
  const read={kind:'context_decision' as const,action:'expanded' as const,item_ids:['read','Session 20'],
    reason_code:'followup_detail_needed',policy_version:'native_source_document_read_progress_v2',sequence:0,elapsed_ms:0}
  const captured={kind:'context_snapshot' as const,snapshot_kind:'provider_response' as const,stage:'after' as const,sequence:1,elapsed_ms:1,materials:[{
    item_id:`unvalidated-provider-answer:${attempt}:${receipt}`,role:'assistant' as const,state:'model_context' as const,text:'{}',source_reads:[]}]}
  const {load}=mount(trace([read,captured]))
  await screen.findByText('Checking the response…')
  load.mockResolvedValue({schema:'dmb_agent_turn_context_trace_response_v1',world_id:'world',turn_id:'turn',attempts:[trace([read,captured,
    {kind:'provider_call',provider:'openai',model:'writer',provider_attempt_id:attempt,outcome:'response_received',sequence:2,elapsed_ms:2,output_tokens:100}])]})
  await waitFor(()=>expect(load).toHaveBeenCalledTimes(2),{timeout:3500})
  expect(screen.getByRole('status')).toHaveTextContent('Checking the response…')
  expect(screen.getByRole('status')).not.toHaveTextContent('Reading Session 20')
})


it.each(['unrelated_producer','new_source','validated','failure','late_failure_usage','late_validation_usage','new_call','ambiguous_capture'] as const)(
  'does not let recorded response progress conceal %s',async(kind)=>{
    const attempt='2c75f1da-9277-4dca-8cd2-e5b8e659bd97'
    const material={item_id:`unvalidated-provider-answer:${attempt}:${'a'.repeat(64)}`,
      role:'assistant' as const,state:'model_context' as const,text:'{}',source_reads:[]}
    const observations:BuddyTurnContextTrace['observations']=[
      {kind:'context_decision',action:'expanded',item_ids:['read','Session 20'],reason_code:'followup_detail_needed',
        policy_version:'native_source_document_read_progress_v2',sequence:0,elapsed_ms:0},
      {kind:'context_snapshot',snapshot_kind:'provider_response',stage:'after',sequence:1,elapsed_ms:1,
        materials:kind==='ambiguous_capture'?[material,material]:[material]}]
    let expected='Reading Session 20…'
    if(kind==='unrelated_producer'){
      observations.push({kind:'provider_call',provider:'openai',model:'other',outcome:'response_received',
        provider_attempt_id:'ac7b8ac8-792f-477a-8f5b-43a1ede922a3',sequence:2,elapsed_ms:2})
      expected='A response has arrived.'
    }else if(kind==='new_source'){
      observations.push({kind:'context_decision',action:'expanded',item_ids:['read','Session 21'],reason_code:'followup_detail_needed',
        policy_version:'native_source_document_read_progress_v2',sequence:2,elapsed_ms:2},
        {kind:'provider_call',provider:'openai',model:'writer',provider_attempt_id:attempt,outcome:'response_received',sequence:3,elapsed_ms:3})
      expected='Reading Session 21…'
    }else if(kind==='validated'||kind==='late_validation_usage'){
      observations.push({kind:'context_snapshot',snapshot_kind:'validated_answer',stage:'after',sequence:2,elapsed_ms:2,materials:[]})
      expected='The reply is assembled.'
    }else if(kind==='failure'||kind==='late_failure_usage'){
      observations.push({kind:'failure',phase:'delivery',code:'plan_writer_completion_rejected',sequence:2,elapsed_ms:2})
      expected='Hit a snag—open the report.'
    }
    if(kind==='late_failure_usage'||kind==='late_validation_usage')observations.push({kind:'provider_call',provider:'openai',model:'writer',
      provider_attempt_id:attempt,outcome:'response_received',sequence:3,elapsed_ms:3})
    if(kind==='new_call'){
      observations.push({kind:'provider_call',provider:'openai',model:'another',outcome:'authorized',sequence:2,elapsed_ms:2},
        {kind:'provider_call',provider:'openai',model:'writer',provider_attempt_id:attempt,outcome:'response_received',sequence:3,elapsed_ms:3})
      expected='Waiting for a response…'
    }
    mount(trace(observations))
    await screen.findByText(expected)
  })
