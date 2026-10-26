import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { BuddyContextTrace, type BuddyTurnContextTrace } from './BuddyContextTrace'
import {buddyTraceText} from './buddyTraceText'
import type { BuddyTraceGraphResult, BuddyTraceSourcePassage } from '../../api/buddyContextTraceTypes'

function trace(observations: BuddyTurnContextTrace['observations']): BuddyTurnContextTrace {
  return { schema: 'dmb_turn_context_trace_v1', trace_id: 'trace', world_id: 'world',
    conversation_id: 'conversation', turn_id: 'turn', attempt: 1,
    started_at: '2026-10-13T00:00:00Z', closed_at: '2026-10-13T00:00:01Z',
    execution_start_sequence: 0, terminal_status: 'completed', capture_status: 'complete', capture_failure_code: null, observations }
}

function passage(text: string): BuddyTraceSourcePassage {
  return {kind:'source_passage', sequence:0, elapsed_ms:2, source_read_event_id:'read-event', read_call_id:'call',
    world_id:'world', graph_revision:'rev', source_read_id:'read', anchor_id:'anchor', evidence_ref_id:'evidence',
    source_artifact_id:'artifact:opaque', source_name:'Session source', source_revision_id:'source-rev', line_start:1, line_end:2,
    outcome:'enough', returned_chars:text.length, content_sha256:'a'.repeat(64), text}
}
const emptyResult: BuddyTraceGraphResult = {outcome:'denied', graph_revision:'rev', coverage_status:'incomplete', projection_status:'complete',
  nodes:[], relationship_ids:[], claim_ids:[], evidence_ref_ids:[], returned_counts:{nodes:0, relationships:0, claims:0, evidence_refs:0},
  total_counts:{nodes:0, relationships:0, claims:0, evidence_refs:0}, omission_codes:[]}

describe('Buddy context trace', () => {
  it('describes structural history retention without inventing a semantic relevance decision', () => {
    render(<BuddyContextTrace ownerActive={true} trace={trace([{kind:'context_decision', sequence:0, elapsed_ms:1,
      action:'retained', item_ids:['message:1'], reason_code:'question_relevance', policy_version:'conversation_routes_v1'}])} />)
    expect(screen.getByText('Visible conversation history retained for follow-ups.')).toBeInTheDocument()
    expect(screen.queryByText('Relevant to this question')).not.toBeInTheDocument()
  })
  it('distinguishes a capture gap from a failed agent execution', () => {
    render(<BuddyContextTrace ownerActive={true} trace={trace([{kind:'failure', sequence:0, elapsed_ms:1,
      phase:'trace_capture', code:'recap_context_capture_unavailable'}])} />)
    expect(screen.getByText('Trace capture incomplete')).toBeInTheDocument()
    expect(screen.queryByText('Execution failed')).not.toBeInTheDocument()
  })
  it('labels absent historical evidence honestly', () => {
    render(<BuddyContextTrace ownerActive={true} trace={null} />)
    expect(screen.getByText('No execution trace was captured for this turn.')).toBeInTheDocument()
  })
  it('labels current reuse separately and preserves original read provenance', () => {
    const reused = { ...passage('A retained exact passage.'), kind: 'source_passage_reuse' as const,
      origin_turn_id: 'original-turn', origin_attempt: 1, origin_read_event_id: 'original-read', origin_provider_attempt_id: 'original-provider' }
    render(<BuddyContextTrace ownerActive={true} trace={trace([reused])} />)
    expect(screen.getByText(/Session source.*reused/)).toBeInTheDocument()
    expect(screen.getByText('Exact retained passage admitted for reuse in this attempt. Original read provenance is preserved.')).toBeInTheDocument()
    expect(screen.queryByText('Exact passage read during this attempt. Historical observation; it does not grant new evidence authority.')).not.toBeInTheDocument()
    expect(screen.getByText(/original-turn/)).toBeInTheDocument()
  })
  it('distinguishes estimates from actual model usage', () => {
    render(<BuddyContextTrace ownerActive={true} trace={trace([{kind:'provider_call', sequence:0, elapsed_ms:0,
      provider:'openai-api', model:'model', outcome:'authorized', input_upper_bound:67797,
      input_estimator:'upper_bound'}])} />)
    expect(screen.getByText(/conservative estimate, not actual token usage/)).toBeInTheDocument()
    expect(screen.getByText(/Actual token usage was not captured/)).toBeInTheDocument()
    expect(screen.queryByText(/Provider-reported usage/)).not.toBeInTheDocument()
  })
  it('identifies actual usage by provider call and displays measured duration', () => {
    render(<BuddyContextTrace ownerActive={false} trace={trace([{kind:'provider_call', sequence:0, elapsed_ms:64000,
      provider_attempt_id:'exact-call-id', provider:'openai-api', model:'same-model', outcome:'response_received',
      input_tokens:42, output_tokens:7, duration_ms:1234}])} />)
    expect(screen.getByText('Provider call exact-call-id')).toBeInTheDocument()
    expect(screen.getByText('Provider duration: 1.23s')).toBeInTheDocument()
    expect(screen.getByText('Provider-reported usage: 42 input · 7 output')).toBeInTheDocument()
    expect(screen.queryByText(/Input ceiling/)).not.toBeInTheDocument()
  })
  it('keeps a retained route distinct from context prose', () => {
    render(<BuddyContextTrace ownerActive={true} trace={trace([{kind:'context_snapshot', stage:'after', sequence:0,
      elapsed_ms:1, materials:[{item_id:'source', state:'retrieval_route', role:'source', source_reads:[],
        route:{route_id:'source', world_id:'world', graph_revision:'rev', anchor_id:'anchor'}}]}])} />)
    fireEvent.click(screen.getByText('Working context · after this turn'))
    expect(screen.getByText('Captured material')).toBeInTheDocument()
    expect(screen.getByText('Available through retained routes')).toBeInTheDocument()
    expect(screen.getByText(/passage is not currently present/)).toBeInTheDocument()
  })
  it('identifies denied graph queries as non-evidence', () => {
    render(<BuddyContextTrace ownerActive={true} trace={trace([{kind:'graph_tool', sequence:0, elapsed_ms:2,
      tool_name:'expand_graph_retrieval', request:{operation:'search', query_text:'Mirathorn', seed_node_ids:[]},
      execution_event_id:'event', request_arguments_sha256:'a'.repeat(64), result_packet_sha256:'b'.repeat(64), scope_mode:'world', campaign_id:null, revision_pin:'rev', result:emptyResult}])} />)
    fireEvent.click(screen.getByText('Explore World graph · search'))
    fireEvent.click(screen.getByText('Captured result'))
    expect(screen.getByText(/This result supplies no admitted evidence/)).toBeInTheDocument()
    expect(screen.getByText('Search: Mirathorn')).toBeInTheDocument()
  })
  it('opens complete admitted passages as readable prose', () => {
    const text='Mirathorn source passage. '.repeat(300)
    render(<BuddyContextTrace ownerActive={true} trace={trace([passage(text)])} />)
    fireEvent.click(screen.getByText('Session source · lines 1–2 · enough'))
    expect(screen.getByText(text.trim()).tagName).toBe('BLOCKQUOTE')
    expect(screen.getByText(/Historical observation/)).toBeInTheDocument()
  })
  it('shows incomplete capture separately from a completed turn', () => {
    render(<BuddyContextTrace ownerActive={true} trace={{...trace([]), capture_status:'incomplete', capture_failure_code:'trace_cap_exceeded'}} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Some execution evidence is missing. trace_cap_exceeded')
    expect(screen.getByText('Incomplete capture')).toBeInTheDocument()
  })
  it('distinguishes limited trace projection from retrieval coverage', () => {
    render(<BuddyContextTrace ownerActive={true} trace={trace([{kind:'graph_tool', sequence:0, elapsed_ms:2,
      tool_name:'expand_graph_retrieval', request:{operation:'neighborhood', seed_node_ids:['city'], depth:2},
      execution_event_id:'event', request_arguments_sha256:'a'.repeat(64), result_packet_sha256:'b'.repeat(64), scope_mode:'world', campaign_id:null, revision_pin:'rev',
      result:{...emptyResult, outcome:'partial', projection_status:'limited', nodes:[{node_id:'city', label:'Mirathorn', kind:'location'}],
        returned_counts:{...emptyResult.returned_counts, nodes:1}, total_counts:{...emptyResult.total_counts, nodes:4}, omission_codes:['trace_node_limit']}}])} />)
    fireEvent.click(screen.getByText('Explore World graph · neighborhood'))
    expect(screen.getByText(/Graph coverage: incomplete/)).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('trace_node_limit')
    expect(screen.getByRole('note')).toHaveTextContent('4 nodes')
    expect(screen.getByText('Mirathorn · location')).toBeInTheDocument()
  })
  it('identifies a missing captured source snapshot in model context', () => {
    render(<BuddyContextTrace ownerActive={true} trace={trace([{kind:'context_snapshot', stage:'before', sequence:0, elapsed_ms:0,
      materials:[{item_id:'source', state:'model_context', role:'source', source_read_event_id:'missing', source_reads:[]}]}])} />)
    fireEvent.click(screen.getByText('Working context · before this turn'))
    fireEvent.click(screen.getByText('source · source'))
    expect(screen.getByText('Referenced source passage was not captured in this attempt.')).toBeInTheDocument()
  })
  it.each(['matching', 'wrong digest', 'future passage'])('binds context source material to an exact earlier capture: %s', (mode) => {
    const captured = passage('Actual captured passage')
    const snapshot = {kind:'context_snapshot' as const, stage:'after' as const, sequence:1, elapsed_ms:3,
      materials:[{item_id:'selected-source', state:'model_context' as const, role:'source' as const, source_read_event_id:'read-event',
        source_reads:[{source_read_id:'read', content_sha256:mode === 'wrong digest' ? 'b'.repeat(64) : captured.content_sha256}]}]}
    if (mode === 'future passage') captured.sequence = 2
    render(<BuddyContextTrace ownerActive={true} trace={trace([captured, snapshot])} />)
    fireEvent.click(screen.getByText('Working context · after this turn'))
    const context = screen.getByText('source · selected-source').closest('details')!
    fireEvent.click(screen.getByText('source · selected-source'))
    if (mode === 'matching') {
      expect(context.textContent).toContain('Actual captured passage')
    } else {
      expect(context.textContent).toContain('Referenced source passage was not captured')
      expect(context.textContent).not.toContain('Actual captured passage')
    }
  })
})

 it('names an unavailable source honestly without using its artifact ID as the title',()=>{
   const row=passage('Exact source text');delete row.source_name;
   render(<BuddyContextTrace ownerActive={true} trace={trace([row])}/>);
   const summary=screen.getByText('Source name unavailable · lines 1–2 · enough');
   expect(summary).not.toHaveTextContent('artifact:opaque');
   fireEvent.click(summary);fireEvent.click(screen.getByText('Pinned source reference'));
   expect(screen.getByText(/"source_artifact": "artifact:opaque"/)).toBeInTheDocument();
 });

describe('provider response reconciliation', () => {
  const response = (sequence: number, fields = {}) => ({kind:'provider_call' as const, sequence, elapsed_ms:sequence * 1000,
    provider_attempt_id:'call-a', provider:'openai-api', model:'writer', outcome:'response_received' as const, ...fields})
  it('enriches the original response with late measured usage without moving it after intervening work', () => {
    render(<BuddyContextTrace ownerActive={false} trace={trace([
      response(0), {kind:'failure',sequence:1,elapsed_ms:1000,phase:'delivery',code:'interrupted'},
      response(2,{input_tokens:0,output_tokens:7,duration_ms:1234}),
    ])} />)
    expect(screen.getAllByText('response_received')).toHaveLength(1)
    expect(screen.getByText('Provider-reported usage: 0 input · 7 output')).toBeInTheDocument()
    expect(screen.queryByText('Actual token usage was not captured for this observation.')).not.toBeInTheDocument()
    expect(screen.getByText('Same provider call · usage updated at 2.0s')).toBeInTheDocument()
    const rows=screen.getAllByRole('listitem')
    expect(rows[0]).toHaveTextContent('Provider duration: 1.23s')
    expect(rows[1]).toHaveTextContent('Execution failed')
    fireEvent.click(screen.getByText('Call lifecycle and usage updates'))
    expect(screen.getByText(/"sequence": 2/)).toBeInTheDocument()
  })
  it.each([
    {provider_attempt_id:'call-b'}, {provider_attempt_id:null}, {model:'other-writer'}, {provider:'other-provider'},
    {outcome:'failed'}, {input_tokens:43}, {duration_ms:999},
  ])('keeps distinct, unidentified, conflicting or different lifecycle observations separate: %j', fields => {
    render(<BuddyContextTrace ownerActive={false} trace={trace([
      response(0,{input_tokens:42,duration_ms:1234}), response(1,fields),
    ])} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.queryByText('Call lifecycle and usage updates')).not.toBeInTheDocument()
  })
  it('preserves authorization separately and does not double count repeated usage', () => {
    render(<BuddyContextTrace ownerActive={false} trace={trace([
      {...response(0),outcome:'authorized'}, response(1), response(2,{input_tokens:42}),response(3,{input_tokens:42}),
    ])} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText('authorized')).toBeInTheDocument()
    expect(screen.getAllByText('response_received')).toHaveLength(1)
    expect(screen.getByText('Provider-reported usage: 42 input · output unavailable')).toBeInTheDocument()
  })
})

it('calls out material additions, removals and changes without treating routes as prompt prose', () => {
  const item=(item_id:string,text:string)=>({item_id,text,state:'model_context' as const,role:'user' as const,source_reads:[]})
  render(<BuddyContextTrace ownerActive={false} trace={trace([
    {kind:'context_snapshot',stage:'before',snapshot_kind:'compaction_input',comparison_id:'pair',sequence:0,elapsed_ms:0,materials:[item('old','Old'),item('same','Before')]},
    {kind:'context_snapshot',stage:'after',snapshot_kind:'compaction_output',comparison_id:'pair',sequence:1,elapsed_ms:1,materials:[item('same','After'),item('new','New')]},
  ])} />)
  fireEvent.click(screen.getByText('Working context · after compaction'))
  expect(screen.getByLabelText('Context changes')).toHaveTextContent('Removed · old')
  expect(screen.getByLabelText('Context changes')).toHaveTextContent('Changed · same')
  expect(screen.getByLabelText('Context changes')).toHaveTextContent('Added · new')
})
it('shows a small list-rate cost and never prices unknown models as free', () => {
  render(<BuddyContextTrace ownerActive={false} trace={trace([
    {kind:'provider_call',sequence:0,elapsed_ms:0,provider:'typesafe',model:'jev-1.14.0',outcome:'response_received',input_tokens:6689,output_tokens:88},
    {kind:'provider_call',sequence:1,elapsed_ms:1,provider:'other',model:'unknown',outcome:'response_received',input_tokens:2,output_tokens:3},
  ])} />)
  expect(screen.getByText(/Estimated cost: \$0.000281 USD/)).toBeInTheDocument()
  expect(screen.getByText(/Estimated cost unavailable/)).toBeInTheDocument()
})

it('opens an honest error report for a historical interruption without a cause', () => {
  render(<BuddyContextTrace ownerActive={false} trace={{...trace([]), terminal_status:'interrupted'}} />)
  expect(screen.getByText('Reply error report')).toBeInTheDocument()
  expect(screen.getByRole('alert')).toHaveTextContent('The specific cause was not recorded')
  expect(screen.getByText('Execution timeline').closest('details')).not.toHaveAttribute('open')
})

it('leads with safe durable exception metadata without pretending capture is success', () => {
  render(<BuddyContextTrace ownerActive={false} trace={{...trace([{kind:'failure', sequence:0, elapsed_ms:23000,
    code:'build_execution_exception', phase:'delivery', stage:'controller_prepare', exception_type:'RuntimeError',
    cause_type:'ValueError', diagnostic_id:'private-diagnostic-id', diagnostic_sha256:'a'.repeat(64)}]), terminal_status:'interrupted'}} />)
  expect(screen.getByRole('alert')).toHaveTextContent('Stage: controller_prepare')
  expect(screen.getByRole('alert')).toHaveTextContent('caused by ValueError')
  expect(screen.getByRole('alert')).toHaveTextContent('private-diagnostic-id')
  expect(screen.queryByText('How Buddy built this reply')).not.toBeInTheDocument()
})

it('explains the reproduced source-name failure using a fixed public description', () => {
  render(<BuddyContextTrace ownerActive={false} trace={{...trace([{kind:'failure', sequence:0, elapsed_ms:23000,
    code:'build_source_name_missing', phase:'delivery', stage:'context_acquisition', exception_type:'ValueError',
    cause_type:'ValueError', diagnostic_id:'private-diagnostic-id', diagnostic_sha256:'a'.repeat(64)}]), terminal_status:'interrupted'}} />)
  expect(screen.getByRole('alert')).toHaveTextContent('A retrieved passage has no verified source name.')
})


describe('copy captured trace', () => {
  it('copies the selected attempt and complete record with the timeline collapsed', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      const captured = {...trace([passage('A source excerpt with ``` fences.'),
        {kind:'failure' as const,sequence:1,elapsed_ms:23700,phase:'delivery',code:'build_source_name_missing',stage:'context_acquisition'}]), terminal_status:'interrupted' as const, attempt:2}
      render(<BuddyContextTrace ownerActive={false} trace={captured} />)
      expect(screen.getByText('Execution timeline').closest('details')).not.toHaveAttribute('open')
      fireEvent.click(screen.getByRole('button', {name:'Copy trace',exact:true}))
      await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Trace copied.'))
      const copied = writeText.mock.calls[0][0] as string
      expect(copied).toContain('Attempt: 2')
      expect(copied).toContain('Reply status: interrupted')
      expect(copied).toContain('23.7s · Execution failed · build_source_name_missing')
      expect(copied).toContain('Stage: context_acquisition')
      const record = copied.split('Private exception diagnostic files are not included.\n\n')[1]
      expect(JSON.parse(record.split('\n').map(line => line.slice(4)).join('\n'))).toEqual(captured)
      expect(copied).not.toContain('Message DungeonBuddy')
      expect(copied).not.toContain('Refresh trace')
    } finally { vi.unstubAllGlobals() }
  })
  it('reports clipboard rejection and allows another click', async () => {
    const writeText = vi.fn().mockRejectedValueOnce(new Error('denied')).mockResolvedValueOnce(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    try {
      render(<BuddyContextTrace ownerActive={false} trace={trace([])} />)
      fireEvent.click(screen.getByRole('button', {name:'Copy trace',exact:true}))
      await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Couldn’t copy'))
      expect(screen.queryByText('Trace copied.')).not.toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', {name:'Copy trace',exact:true}))
      await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Trace copied.'))
    } finally { vi.unstubAllGlobals() }
  })
})

it('never infers question or source removal from a response-only snapshot', () => {
  render(<BuddyContextTrace ownerActive={false} trace={trace([
    {kind:'context_snapshot',snapshot_kind:'provider_input',stage:'before',sequence:0,elapsed_ms:0,
      materials:[{item_id:'current-question',state:'model_context',role:'user',text:'Read Edge.'}]},
    {kind:'context_snapshot',snapshot_kind:'provider_response',stage:'after',sequence:1,elapsed_ms:1,
      materials:[{item_id:'unvalidated-answer',state:'model_context',role:'assistant',text:'Returned plan'}]},
  ])} />)
  fireEvent.click(screen.getByText('Provider response · unvalidated'))
  expect(screen.queryByLabelText('Context changes')).not.toBeInTheDocument()
  expect(screen.getByText(/not an inventory of what the provider received/)).toBeInTheDocument()
  expect(screen.getByRole('heading',{name:'Returned response'})).toBeInTheDocument()
  fireEvent.click(screen.getByText('assistant · unvalidated-answer'))
  expect(screen.getByText('Returned plan')).toBeInTheDocument()
})
it('compares successive prepared inputs across an interleaved response', () => {
  render(<BuddyContextTrace ownerActive={false} trace={trace([
    {kind:'context_snapshot',snapshot_kind:'provider_input',stage:'before',sequence:0,elapsed_ms:0,
      materials:[{item_id:'question',state:'model_context',role:'user',text:'Same question'}]},
    {kind:'context_snapshot',snapshot_kind:'provider_response',stage:'after',sequence:1,elapsed_ms:1,
      materials:[{item_id:'response',state:'model_context',role:'assistant',text:'Decision'}]},
    {kind:'context_snapshot',snapshot_kind:'provider_input',stage:'before',sequence:2,elapsed_ms:2,
      materials:[{item_id:'question',state:'model_context',role:'user',text:'Same question'},
        {item_id:'source',state:'model_context',role:'source',text:'New passage'}]},
  ])} />)
  fireEvent.click(screen.getAllByText('Working context · prepared input')[1])
  expect(screen.getByLabelText('Context changes')).toHaveTextContent('Added · source')
  expect(screen.getByLabelText('Context changes')).not.toHaveTextContent('response')
  expect(screen.getByLabelText('Context changes')).not.toHaveTextContent('Removed')
})
it('retains untyped historical inventories without inventing comparisons', () => {
  render(<BuddyContextTrace ownerActive={false} trace={trace([
    {kind:'context_snapshot',stage:'before',sequence:0,elapsed_ms:0,materials:[]},
    {kind:'context_snapshot',stage:'after',sequence:1,elapsed_ms:1,materials:[]},
  ])} />)
  fireEvent.click(screen.getByText('Working context · after this turn'))
  expect(screen.getAllByText(/historical snapshot did not record its purpose/)).toHaveLength(2)
  expect(screen.queryByLabelText('Context changes')).not.toBeInTheDocument()
})
it('does not compare unrelated compaction pairs', () => {
  render(<BuddyContextTrace ownerActive={false} trace={trace([
    {kind:'context_snapshot',snapshot_kind:'compaction_input',comparison_id:'one',stage:'before',sequence:0,elapsed_ms:0,materials:[]},
    {kind:'context_snapshot',snapshot_kind:'compaction_output',comparison_id:'two',stage:'after',sequence:1,elapsed_ms:1,materials:[]},
  ])} />)
  fireEvent.click(screen.getByText('Working context · after compaction'))
  expect(screen.queryByLabelText('Context changes')).not.toBeInTheDocument()
})

it('copies response meaning without relabeling it as an input inventory', () => {
  expect(buddyTraceText(trace([{kind:'context_snapshot',snapshot_kind:'provider_response',stage:'after',sequence:0,elapsed_ms:0,materials:[]}]))).toContain('Provider response · unvalidated · 0 captured material items')
})

it.each(['read','read_partial','source_gap'] as const)('renders and copies the exact authored acquisition state: %s',outcome=>{
 const event={kind:'authored_graph_reference_v1' as const,sequence:0,elapsed_ms:2,execution_event:{kind:'build_authored_reference_read_v1' as const,event_id:'recorded-event',sequence:8,capture_event_id:'capture',authorization_event_id:'authorization',node_id:'cedar-box',operation_event_ids:['object-read'],source_read_event_ids:['source-read'],returned_node_ids:['cedar-box'],outcome}};
 const captured=trace([event]);render(<BuddyContextTrace ownerActive trace={captured}/>);
 expect(screen.getByText(outcome==='read'?'Graph reference · read':outcome==='read_partial'?'Graph reference · partial read':'Graph reference · source gap')).toBeInTheDocument();
 expect(screen.getByText(/This status does not establish a claim/)).toBeInTheDocument();
 const copied=buddyTraceText(captured);expect(copied).toContain('Recorded APP event: recorded-event · cedar-box');expect(copied).toContain('source-read');expect(copied).toContain(outcome);
});
it('keeps selected unread references and prepared writer input distinct from provider transmission',()=>{
 const selected={kind:'authored_graph_reference_v1' as const,sequence:0,elapsed_ms:0,execution_event:{kind:'build_authored_references_captured_v1' as const,event_id:'selected',sequence:1,references:{schema:'dmb_authored_graph_references_v1' as const,references:[{schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:'world',native_world_id:'native',binding_version:1,graph_revision:'selected-revision',node_id:'cedar-box',label:'Cedar box'}]},read_graph_revision:'current-revision',turn_id:'turn',conversation_id:'conversation',attempt:1,submitted_intent_fingerprint:'a'.repeat(64)}};
 const prepared={kind:'authored_graph_reference_v1' as const,sequence:1,elapsed_ms:2,execution_event:{kind:'build_authored_provider_inclusion_v1' as const,event_id:'prepared',sequence:9,capture_event_id:'selected',references_sha256:'a'.repeat(64),source_read_event_ids:['source'],provider_attempt_id:'writer-attempt',envelope_sha256:'b'.repeat(64),material_sha256:'c'.repeat(64)}};
 const captured=trace([selected,prepared]);render(<BuddyContextTrace ownerActive trace={captured}/>);
 expect(screen.getByText('Graph references · selected, unread')).toBeInTheDocument();expect(screen.getByText('Graph references · prepared writer input')).toBeInTheDocument();expect(screen.getByText(/See provider lifecycle records for transmission and response/)).toBeInTheDocument();
 expect(buddyTraceText(captured)).toContain('writer-attempt');expect(buddyTraceText(captured)).toContain('current-revision');expect(screen.queryByText('response_received')).toBeNull();
});
