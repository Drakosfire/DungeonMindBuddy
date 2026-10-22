import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createHash, webcrypto } from 'node:crypto';
import { BuildSavedSectionEvidence, isSavedSectionTargets } from './components/BuildSavedSectionEvidence';
import { getAgentSavedSection } from '../api/liveApi';
import type { SavedBuildSectionTargetV1, SavedBuildSectionReadV1 } from '../api/types';
vi.mock('../api/liveApi', () => ({getAgentSavedSection: vi.fn()}));
const load=vi.mocked(getAgentSavedSection);
const id='11111111-1111-4111-8111-111111111111';
const other='22222222-2222-4222-8222-222222222222';
const hash=(s:string)=>createHash('sha256').update(s).digest('hex');
const text='Float goats **walk on water**. 🐐';
const segments=[{kind:'saved_source_claim', text:'An authored fact.', content_sha256:'a'.repeat(64)}];
const basis={world_id:'world',document_id:'document',registry_revision:2,content_sha256:'a'.repeat(64),visibility:'internal' as const};
function target():SavedBuildSectionTargetV1 {return {schema:'dmb_saved_build_section_target_v1',kind:'saved_build_section',world_id:'world',turn_id:id,segment_index:0,section_event_id:id,section_read_id:id,source_basis:basis,source_class:'saved_authored_source_not_played_truth',line_start:10,line_end:10,excerpt_sha256:hash(text),text_sha256:hash(segments[0]!.text)};}
function response(t=target()):SavedBuildSectionReadV1 {return {schema:'dmb_saved_build_section_read_v1',target:t,content:text};}
const props=()=>({targets:[target()],basis,segments,worldId:'world',turnId:id});
beforeEach(()=>{vi.stubGlobal('crypto',webcrypto);load.mockReset();});
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();});
describe('saved-source evidence',()=>{
 it('opens exact authored Markdown without treating it as Graph evidence',async()=>{
  load.mockResolvedValue(response());render(<BuildSavedSectionEvidence sourceName={null} {...props()} />);
  expect(load).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Read saved lines 10–10'}));
  expect(await screen.findByText('walk on water')).toBeInTheDocument();
  expect(screen.getByLabelText('Saved-source evidence')).toHaveTextContent('authored worldbuilding');
  expect(load).toHaveBeenCalledWith(target());
 });
 it.each(['content','target','extra'])('refuses changed %s without substituting newer source',async(which)=>{
  const r=response();if(which==='content')r.content='newer text';
  if(which==='target')r.target={...r.target,section_read_id:other};
  if(which==='extra')Object.assign(r,{graph_authority:true});
  load.mockResolvedValue(r);render(<BuildSavedSectionEvidence sourceName={null} {...props()} />);
  fireEvent.click(screen.getByRole('button',{name:/Read saved lines/}));
  expect(await screen.findByText(/No newer text has been substituted/)).toBeInTheDocument();
 });
 it('rejects claim-text mismatch before sending a read',async()=>{
  render(<BuildSavedSectionEvidence sourceName={null} {...props()} segments={[{...segments[0]!,text:'another claim'}]} />);
  fireEvent.click(screen.getByRole('button',{name:/Read saved lines/}));
  expect(await screen.findByText(/No newer text has been substituted/)).toBeInTheDocument();expect(load).not.toHaveBeenCalled();
 });
 it('discards a late read across World/turn identity changes',async()=>{
  let resolve!:(r:SavedBuildSectionReadV1)=>void;load.mockImplementation(()=>new Promise(r=>{resolve=r;}));
  const {rerender}=render(<BuildSavedSectionEvidence sourceName={null} {...props()} />);
  fireEvent.click(screen.getByRole('button',{name:/Read saved lines/}));await waitFor(()=>expect(load).toHaveBeenCalled());
  rerender(<BuildSavedSectionEvidence sourceName={null} {...props()} turnId={other} />);
  await act(async()=>resolve(response()));expect(screen.queryByLabelText('Opened saved-source section')).toBeNull();
 });
 it('exposes all distinct section choices',()=>{
  const targets=Array.from({length:10},(_,i)=>({...target(),section_event_id:`${String(i).padStart(8,'0')}-1111-4111-8111-111111111111`}));
  render(<BuildSavedSectionEvidence sourceName={null} {...props()} targets={targets} />);
  expect(screen.getAllByRole('button',{name:/Read saved lines/})).toHaveLength(8);
  fireEvent.click(screen.getByRole('button',{name:'Show more saved sections'}));
  expect(screen.getAllByRole('button',{name:/Read saved lines/})).toHaveLength(10);
 });
 it('rejects duplicate, foreign, unbound or unclassified targets',()=>{
  const c={answer_segments:segments};const t=target();
  expect(isSavedSectionTargets([t],basis,c)).toBe(true);
  expect(isSavedSectionTargets([t,t],basis,c)).toBe(false);
  for(const change of [{world_id:'foreign'},{source_class:'played_truth'},{segment_index:1},{source_basis:{...basis,registry_revision:3}},{line_end:2}])expect(isSavedSectionTargets([{...t,...change}],basis,c)).toBe(false);
 });
});

it('uses the actual authenticated evidence GET without a body or redirect',async()=>{
 const api=await vi.importActual<typeof import('../api/liveApi')>('../api/liveApi');
 api.setNativeGraphAccessToken('synthetic-section-token');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(response()));
 await api.getAgentSavedSection(target());
 const [url,init]=fetch.mock.calls[0]!;
 expect(String(url)).toContain(`/conversation/turns/${id}/saved-sections/0/${id}`);
 expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer synthetic-section-token');
 expect(init?.redirect).toBe('error');expect(init?.body).toBeUndefined();
 expect(init?.credentials).toBe('same-origin');expect(fetch).toHaveBeenCalledTimes(1);
 api.setNativeGraphAccessToken(null);
});


it('names the source without changing the historical request or eagerly reading it',async()=>{
 load.mockResolvedValue(response());
 render(<BuildSavedSectionEvidence {...props()} sourceName="A Named Adventure" />);
 expect(screen.getByLabelText('Saved-source evidence')).toHaveTextContent('A Named Adventure · authored worldbuilding');
 expect(load).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Read A Named Adventure · lines 10–10'}));
 expect(await screen.findByText('walk on water')).toBeInTheDocument();
 expect(load).toHaveBeenCalledExactlyOnceWith(target());
});
it('renders source metadata as plain text',()=>{
 render(<BuildSavedSectionEvidence {...props()} sourceName={'<img src=x onerror=alert(1)>'} />);
 expect(screen.getByLabelText('Saved-source evidence')).toHaveTextContent('<img src=x onerror=alert(1)>');
 expect(document.querySelector('img')).toBeNull();
});
