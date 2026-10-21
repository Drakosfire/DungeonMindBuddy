import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { webcrypto, createHash } from 'node:crypto'
import type { BuddyHistoricalSourceReference, BuddyHistoricalSourcePassageResponse } from '../../api/buddyContextTraceTypes'
import { setNativeGraphAccessToken } from '../../api/liveApi'
import { startReadWave } from '../../api/inFlightReads'
import { BuddyHistoricalSourcePassage } from './BuddyHistoricalSourcePassage'

const text = 'Frank and Sara 🦉 are here.'
const hash = createHash('sha256').update(text).digest('hex')
const reference: BuddyHistoricalSourceReference = {schema:'dmb_trace_historical_source_ref_v1', world_id:'world',
  conversation_id:'conversation', turn_id:'prior-turn', attempt:1, trace_id:'prior-trace',
  source_read_event_id:'read-event', source_read_id:'read/a ?&=', content_sha256:hash}
function response(): BuddyHistoricalSourcePassageResponse {
  return {schema:'dmb_agent_historical_source_passage_v1',reference:{...reference},passage:{kind:'source_passage', sequence:0,elapsed_ms:1,
    source_read_event_id:'read-event',read_call_id:'call',world_id:'world',graph_revision:'revision',source_read_id:reference.source_read_id,
    anchor_id:'anchor',evidence_ref_id:'evidence',source_artifact_id:'artifact:opaque',source_name:'Longmont C2 · Session 20',source_revision_id:'revision',line_start:1,line_end:2,
    outcome:'enough',returned_chars:[...text].length,content_sha256:hash,text}}
}
function deferred<T>() { let resolve!: (value:T)=>void;const promise=new Promise<T>(r=>{resolve=r});return {promise,resolve} }
function toggle() {fireEvent.click(screen.getByText('Source memory from an earlier turn'))}
beforeEach(()=>vi.stubGlobal('crypto',webcrypto))
afterEach(()=>{cleanup();setNativeGraphAccessToken(null);vi.restoreAllMocks();vi.unstubAllGlobals()})
describe('historical source memory inspection',()=>{
  it('reads one exact passage only on expansion, retains within its wave and never posts a turn',async()=>{
    const load=vi.fn().mockResolvedValue(response())
    render(<BuddyHistoricalSourcePassage reference={reference} load={load}/>); expect(load).not.toHaveBeenCalled()
    toggle();expect(await screen.findByText(text)).toBeInTheDocument()
    expect(load).toHaveBeenCalledWith(reference,expect.any(AbortSignal))
    expect(screen.getByText(/grants no current-turn citation authority/)).toBeInTheDocument()
    expect(screen.getByText('Longmont C2 · Session 20')).toBeInTheDocument()
    expect(screen.getByText('Lines 1–2')).toBeInTheDocument()
    expect(screen.getByText('Pinned source reference')).toBeInTheDocument()
    expect(screen.queryByText('artifact:opaque')).not.toBeInTheDocument()
    toggle();toggle();expect(load).toHaveBeenCalledTimes(1)
  })
  it('uses the exact default API without reading full trace or provider prompts',async()=>{
    setNativeGraphAccessToken('synthetic-passage-reader')
    const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(response()))
    render(<BuddyHistoricalSourcePassage reference={reference}/>);toggle();expect(await screen.findByText(text)).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(String(fetch.mock.calls[0][0])).toContain('/context-trace/prior-trace/source-passages/read-event?')
    expect(fetch.mock.calls[0][1]?.method??'GET').toBe('GET')
  })
  it.each(['schema','world_id','conversation_id','turn_id','trace_id','attempt','source_read_event_id','source_read_id','content_sha256'] as const)('rejects changed reference %s',async(field)=>{
    const data=response();data.reference={...data.reference,[field]:field==='attempt'?2:'foreign'}
    render(<BuddyHistoricalSourcePassage reference={reference} load={vi.fn().mockResolvedValue(data)}/>);toggle()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable');expect(screen.queryByText(text)).not.toBeInTheDocument()
  })
  it.each(['text','returned_chars','world_id','source_read_event_id','source_read_id','content_sha256','kind'] as const)('rejects corrupt passage %s',async(field)=>{
    const data=response();data.passage={...data.passage,[field]:field==='returned_chars'?99:'changed'}
    render(<BuddyHistoricalSourcePassage reference={reference} load={vi.fn().mockResolvedValue(data)}/>);toggle()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable');expect(screen.queryByText(text)).not.toBeInTheDocument()
  })
  it('hides already-visible bytes on read/access wave and explicitly retries denied reads',async()=>{
    const load=vi.fn().mockResolvedValueOnce(response()).mockRejectedValueOnce(new Error('denied')).mockResolvedValue(response())
    render(<BuddyHistoricalSourcePassage reference={reference} load={load}/>);toggle();await screen.findByText(text)
    act(()=>startReadWave());expect(screen.queryByText(text)).not.toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable')
    fireEvent.click(screen.getByRole('button',{name:'Retry passage read'}));expect(await screen.findByText(text)).toBeInTheDocument()
    expect(load).toHaveBeenCalledTimes(3)
  })
  it('cancels collapse and rejects an abandoned completion after World/conversation ABA',async()=>{
    const first=deferred<BuddyHistoricalSourcePassageResponse>();const last=deferred<BuddyHistoricalSourcePassageResponse>()
    const load=vi.fn().mockReturnValueOnce(first.promise).mockReturnValue(last.promise)
    const view=render(<BuddyHistoricalSourcePassage reference={reference} load={load}/>);toggle();await waitFor(()=>expect(load).toHaveBeenCalledTimes(1))
    const signal=load.mock.calls[0][1] as AbortSignal
    view.rerender(<BuddyHistoricalSourcePassage reference={{...reference,world_id:'other',conversation_id:'other'}} load={load}/>);
    expect(signal.aborted).toBe(true)
    view.rerender(<BuddyHistoricalSourcePassage reference={reference} load={load}/>);
    await act(async()=>first.resolve(response()));expect(screen.queryByText(text)).not.toBeInTheDocument()
    toggle();await waitFor(()=>expect((load.mock.calls.at(-1)?.[1] as AbortSignal).aborted).toBe(true))
  })
  it('fences digest completion after access retirement',async()=>{
    const gate=deferred<ArrayBuffer>();vi.stubGlobal('crypto',{subtle:{digest:vi.fn().mockReturnValue(gate.promise)}})
    const load=vi.fn().mockResolvedValueOnce(response()).mockReturnValue(new Promise(()=>{}))
    render(<BuddyHistoricalSourcePassage reference={reference} load={load}/>);toggle();await waitFor(()=>expect(crypto.subtle.digest).toHaveBeenCalled())
    act(()=>startReadWave());await act(async()=>gate.resolve(Uint8Array.from(Buffer.from(hash,'hex')).buffer))
    expect(screen.queryByText(text)).not.toBeInTheDocument()
  })
})

 it('does not invent a source name when the captured read has none',async()=>{
   const data=response();delete data.passage.source_name;
   const load=vi.fn().mockResolvedValue(data);
   render(<BuddyHistoricalSourcePassage reference={reference} load={load}/>);toggle();
   expect(await screen.findByText('Source name unavailable')).toBeInTheDocument();
   expect(load).toHaveBeenCalledOnce();expect(screen.queryByText('artifact:opaque')).not.toBeInTheDocument();
 });
 it('rejects malformed display metadata without showing source bytes',async()=>{
   const data=response();Object.assign(data.passage,{source_name:42});
   render(<BuddyHistoricalSourcePassage reference={reference} load={vi.fn().mockResolvedValue(data)}/>);toggle();
   expect(await screen.findByRole('alert')).toHaveTextContent('unavailable');
   expect(screen.queryByText(text)).not.toBeInTheDocument();
 });
