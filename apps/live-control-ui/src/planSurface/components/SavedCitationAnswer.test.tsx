import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {SavedCitationAnswer} from './SavedCitationAnswer';
import {readSavedCitationPreview} from '../../api/savedCitationPreview';
import {savedCitationPreviewFixture} from '../../testSupport/savedCitationPreviewFixture';
import * as api from '../../api/liveApi';
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('renders saved markers without detail or source reads and opens one exact native GET',async()=>{
  const {preview,answer,body,citation}=await savedCitationPreviewFixture();
  const source=vi.spyOn(api,'getAgentNativeBodyExcerpt').mockResolvedValue({schema:'dmb_agent_native_body_excerpt_read_v2',world_id:'world',turn_id:'turn',citation_index:0,citation,content:body,display_label:'Bridge recap'});
  const details=vi.spyOn(api,'getWorldAgentConversationHistory');
  render(<SavedCitationAnswer preview={preview} answer={answer} worldId="world" turnId="turn"/>);
  expect(screen.getByText(answer)).toBeInTheDocument();expect(source).not.toHaveBeenCalled();expect(details).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Read source · Full document'}));
  expect(await screen.findByText(body)).toBeInTheDocument();expect(source).toHaveBeenCalledExactlyOnceWith('world','turn',0);expect(details).not.toHaveBeenCalled();
});

it.each(['owner','citation','hash'])('retains the existing source %s check',async change=>{
  const {preview,answer,body,citation}=await savedCitationPreviewFixture();
  vi.spyOn(api,'getAgentNativeBodyExcerpt').mockResolvedValue({schema:'dmb_agent_native_body_excerpt_read_v2',world_id:change==='owner'?'other':'world',turn_id:'turn',citation_index:0,
    citation:change==='citation'?{...citation,native_source_revision_id:'newer'}:citation,content:change==='hash'?'Replacement text':body,display_label:null});
  render(<SavedCitationAnswer preview={preview} answer={answer} worldId="world" turnId="turn"/>);
  fireEvent.click(screen.getByRole('button',{name:'Read source · Full document'}));
  expect(await screen.findByText(/exact cited section is unavailable/)).toBeInTheDocument();expect(screen.queryByText('Replacement text')).toBeNull();
});

it('discards delayed old-turn source text when the displayed owner changes',async()=>{
  const {preview,answer,body,citation}=await savedCitationPreviewFixture();
  let resolve!:(v:Awaited<ReturnType<typeof api.getAgentNativeBodyExcerpt>>)=>void;
  vi.spyOn(api,'getAgentNativeBodyExcerpt').mockReturnValue(new Promise(r=>{resolve=r;}));
  const view=render(<SavedCitationAnswer preview={preview} answer={answer} worldId="world" turnId="old"/>);
  fireEvent.click(screen.getByRole('button',{name:'Read source · Full document'}));
  view.rerender(<SavedCitationAnswer preview={preview} answer={answer} worldId="world" turnId="new"/>);
  resolve({schema:'dmb_agent_native_body_excerpt_read_v2',world_id:'world',turn_id:'old',citation_index:0,citation,content:body,display_label:null});
  await waitFor(()=>expect(screen.queryByRole('region',{name:'Opened source section'})).toBeNull());expect(screen.queryByText(body)).toBeNull();
});

it('preserves family indexes when display segment order differs from the citation array',async()=>{
  const {preview,answer,body,citation}=await savedCitationPreviewFixture();
  preview.answer_segments.push({kind:'source_passage_claim',text:'The second claim.'});
  preview.native_body_citations.unshift({...citation,segment_index:1,read_event_id:'33333333-3333-4333-8333-333333333333'});
  const source=vi.spyOn(api,'getAgentNativeBodyExcerpt').mockResolvedValue({schema:'dmb_agent_native_body_excerpt_read_v2',world_id:'world',turn_id:'turn',citation_index:1,citation,content:body,display_label:null});
  render(<SavedCitationAnswer preview={preview} answer={answer+'\nThe second claim.'} worldId="world" turnId="turn"/>);
  fireEvent.click(screen.getAllByRole('button',{name:'Read source · Full document'})[0]!);
  expect(await screen.findByText(body)).toBeInTheDocument();expect(source).toHaveBeenCalledExactlyOnceWith('world','turn',1);
});

it.each(['text','index','duplicate','surface','execution','missing'])('shows text with details fallback for a malformed %s preview',async change=>{
  const {preview,answer}=await savedCitationPreviewFixture();const raw=structuredClone(preview);
  if(change==='text')raw.answer_segments[0]!.text='Different text';
  if(change==='index')raw.native_body_citations[0]!.segment_index=8;
  if(change==='duplicate')raw.native_body_citations.push(raw.native_body_citations[0]!);
  if(change==='surface')raw.surface_id='play';
  if(change==='execution')Object.assign(raw,{execution:{claimability:'completed'}});
  if(change==='missing')raw.native_body_citations=[];
  const parsed=readSavedCitationPreview(raw,'world','plan',answer);expect(parsed?.status).toBe('details_required');
  render(<SavedCitationAnswer preview={parsed} answer={answer} worldId="world" turnId="turn"/>);
  expect(screen.getByText(answer)).toBeInTheDocument();expect(screen.queryByRole('button',{name:/Read source/})).toBeNull();
});
