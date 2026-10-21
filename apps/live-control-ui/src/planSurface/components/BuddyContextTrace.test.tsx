import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BuddyContextTrace, type BuddyTurnContextTrace } from './BuddyContextTrace'
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
    source_artifact_id:'Session source', source_revision_id:'source-rev', line_start:1, line_end:2,
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
    expect(screen.getByText('Present in model context')).toBeInTheDocument()
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
