import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { BuddyHistoricalSourceReference, BuddyTurnContextTrace, WorldAgentTurnContextTraceResponse } from '../../api/buddyContextTraceTypes'
import { BuddyHistoricalSourcePassage } from './BuddyHistoricalSourcePassage'

const reference: BuddyHistoricalSourceReference = {schema:'dmb_trace_historical_source_ref_v1', world_id:'world',
  conversation_id:'conversation', turn_id:'prior-turn', attempt:1, trace_id:'prior-trace',
  source_read_event_id:'read-event', source_read_id:'read', content_sha256:'a'.repeat(64)}
const prior: BuddyTurnContextTrace = {schema:'dmb_turn_context_trace_v1', trace_id:'prior-trace', world_id:'world',
  turn_id:'prior-turn', conversation_id:'conversation', attempt:1, execution_start_sequence:0,
  started_at:'2026-10-13T00:00:00Z', closed_at:'2026-10-13T00:00:01Z', terminal_status:'completed', capture_status:'complete', capture_failure_code:null,
  observations:[{kind:'source_passage', sequence:0, elapsed_ms:1, source_read_event_id:'read-event', read_call_id:'call',
    world_id:'world', graph_revision:'revision', source_read_id:'read', anchor_id:'anchor', evidence_ref_id:'evidence',
    source_artifact_id:'Session 20', source_revision_id:'source-revision', line_start:1, line_end:2,
    outcome:'enough', returned_chars:24, content_sha256:'a'.repeat(64), text:'Frank and Sara are here.'}]}
function response(trace=prior): WorldAgentTurnContextTraceResponse {
  return {schema:'dmb_agent_turn_context_trace_response_v1',world_id:'world',turn_id:'prior-turn',attempts:[trace]}
}
describe('historical source memory inspection',()=>{
  it('loads only on expansion and shows the exact earlier passage as historical memory',async()=>{
    const load=vi.fn().mockResolvedValue(response())
    render(<BuddyHistoricalSourcePassage reference={reference} load={load}/>)
    expect(load).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Source memory from an earlier turn'))
    expect(await screen.findByText('Frank and Sara are here.')).toBeInTheDocument()
    expect(load).toHaveBeenCalledWith('world','prior-turn')
    expect(screen.getByText(/grants no current-turn citation authority/)).toBeInTheDocument()
  })
  it.each(['conversation_id','trace_id','attempt'] as const)('rejects a mismatched prior %s',async(field)=>{
    const changed={...prior,[field]:field==='attempt'?2:'foreign'}
    render(<BuddyHistoricalSourcePassage reference={reference} load={vi.fn().mockResolvedValue(response(changed))}/>)
    fireEvent.click(screen.getByText('Source memory from an earlier turn'))
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable')
    expect(screen.queryByText('Frank and Sara are here.')).not.toBeInTheDocument()
  })
  it('rejects a changed digest rather than showing similar source prose',async()=>{
    render(<BuddyHistoricalSourcePassage reference={{...reference,content_sha256:'b'.repeat(64)}} load={vi.fn().mockResolvedValue(response())}/>)
    fireEvent.click(screen.getByText('Source memory from an earlier turn'))
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable')
    expect(screen.queryByText('Frank and Sara are here.')).not.toBeInTheDocument()
  })
})
