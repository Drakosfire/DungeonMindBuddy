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


async function relatedFixture(surface:'build'|'plan'='plan') {
  const {preview}=await savedCitationPreviewFixture(surface);
  const body='Edge contains the old bath house.',answer='The saved Edge page describes the bath house.';
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(body));
  const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  const claim={kind:'related_page_claim' as const,text:answer,read_id:'33333333-3333-4333-8333-333333333333',
    page:{world_id:'world',document_id:'44444444-4444-4444-8444-444444444444',registry_revision:3,title:'Edge',visibility:'internal' as const,content_sha256:hash}};
  preview.answer_segments=[claim];preview.native_body_citations=[];
  const result={schema:'dmb_agent_related_page_read_v1' as const,world_id:'world',turn_id:'turn',read_id:claim.read_id,page:claim.page,markdown:body};
  return {preview,answer,body,claim,result};
}

it.each(['build','plan'] as const)('opens a saved authored citation on %s without Details',async surface=>{
  const {preview,answer,body,claim,result}=await relatedFixture(surface);
  const parsed=readSavedCitationPreview(preview,'world',surface,answer);
  expect(parsed?.status).toBe('ready');
  const source=vi.spyOn(api,'getAgentRelatedPage').mockResolvedValue(result);
  const details=vi.spyOn(api,'getWorldAgentConversationHistory');
  const view=render(<SavedCitationAnswer preview={parsed} answer={answer} worldId="world" turnId="turn"/>);
  expect(source).not.toHaveBeenCalled();expect(details).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Read Edge · saved revision 3'}));
  expect(await screen.findByText(body)).toBeInTheDocument();
  expect(source).toHaveBeenCalledExactlyOnceWith('world','turn',claim.read_id);
  expect(details).not.toHaveBeenCalled();
  view.unmount();
  render(<SavedCitationAnswer preview={parsed} answer={answer} worldId="world" turnId="turn"/>);
  expect(screen.getByRole('button',{name:'Read Edge · saved revision 3'})).toBeInTheDocument();
  expect(source).toHaveBeenCalledTimes(1);
});

it.each(['world','turn','read','page','hash'])('refuses a changed related-page %s binding',async change=>{
  const {preview,answer,result}=await relatedFixture();
  if(change==='world')result.world_id='foreign';
  if(change==='turn')result.turn_id='another-turn';
  if(change==='read')result.read_id='another-read';
  if(change==='page')result.page={...result.page,registry_revision:4};
  if(change==='hash')result.markdown='Changed source';
  vi.spyOn(api,'getAgentRelatedPage').mockResolvedValue(result);
  render(<SavedCitationAnswer preview={preview} answer={answer} worldId="world" turnId="turn"/>);
  fireEvent.click(screen.getByRole('button',{name:'Read Edge · saved revision 3'}));
  expect(await screen.findByText(/exact cited section is unavailable/)).toBeInTheDocument();
  expect(screen.queryByText('Changed source')).toBeNull();
});

it.each(['world','surface','read','digest','extra'])('rejects malformed saved-page preview %s before showing a marker',async change=>{
  const {preview,answer,claim}=await relatedFixture();
  if(change==='world')claim.page.world_id='foreign';
  if(change==='surface')preview.surface_id='play';
  if(change==='read')claim.read_id='invalid';
  if(change==='digest')claim.page.content_sha256='invalid';
  if(change==='extra')Object.assign(claim,{execution:{}});
  expect(readSavedCitationPreview(preview,'world',preview.surface_id,answer)?.status).toBe('details_required');
});


it('discards a delayed saved-page result after changing turns',async()=>{
  const {preview,answer,body,result}=await relatedFixture();
  let resolve!:(v:typeof result)=>void;
  vi.spyOn(api,'getAgentRelatedPage').mockReturnValue(new Promise(r=>{resolve=r;}));
  const view=render(<SavedCitationAnswer preview={preview} answer={answer} worldId="world" turnId="turn"/>);
  fireEvent.click(screen.getByRole('button',{name:'Read Edge · saved revision 3'}));
  view.rerender(<SavedCitationAnswer preview={preview} answer={answer} worldId="world" turnId="next"/>);
  resolve(result);
  await waitFor(()=>expect(screen.queryByRole('region',{name:'Opened source section'})).toBeNull());
  expect(screen.queryByText(body)).toBeNull();
});
