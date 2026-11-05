import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {NativeSourceInspection} from './NativeSourceInspection';
import {getNativeSourceCatalog,readNativeSource} from '../api/liveApi';
import type {NativeSourceCatalog,NativeSourceMetadata,NativeSourceBody} from '../api/nativeSourceInspection';
vi.mock('../api/liveApi',()=>({getNativeSourceCatalog:vi.fn(),readNativeSource:vi.fn()}));
vi.mock('../planSurface/components/WorldPlanAgentAnswer',()=>({WorldPlanAgentAnswer:({answer}:{answer:string})=><p>{answer}</p>}));
const scope={managed_world_id:'w',native_world_id:'n',binding_version:1,revision_id:'r1',scope_mode:'world' as const,campaign_id:null};
function item(n=8,campaign='c1',kind:'recap'|'worldbuilding'='recap'):NativeSourceMetadata{return {
 source_artifact:{source_artifact_id:`s${campaign}${n}${kind==='worldbuilding'?'-worldbuilding':''}`,source_classification:'dungeonbuddy.source:session_recap'},
 source_revision:{source_revision_id:`sr${campaign}${n}${kind==='worldbuilding'?'-worldbuilding':''}`,content_sha256:'a'.repeat(64)},evidence_ref_ids:[`e${campaign}${n}`],origin:null,
 navigation:{label:kind==='recap'?`Session ${n} recap`:`Worldbuilding ${n}`,kind,campaign_id:campaign,session_id:`session-${n}`,status:'available',metadata_revision:'m1',origin_matches_current_metadata:true}};}
function catalog(sources=[item()]):NativeSourceCatalog{return {schema:'dmb_native_source_catalog_v1',scope,catalogue:{space_id:'n',revision_id:'r1',source_authority_epoch:1,sources,complete:true},navigation_complete:true};}
function body(s=item()):NativeSourceBody{return {schema:'dmb_native_source_body_v1',scope,source:{status:'available',source_artifact_id:s.source_artifact.source_artifact_id,source_revision_id:s.source_revision.source_revision_id,body_text:'Exact retained source text',body_sha256:s.source_revision.content_sha256,evidence_ref_id:s.evidence_ref_ids[0],source_authority_epoch:1}};}
beforeEach(()=>{vi.mocked(getNativeSourceCatalog).mockReset().mockResolvedValue(catalog());vi.mocked(readNativeSource).mockReset().mockResolvedValue(body());});
afterEach(cleanup);
it('loads metadata only, then explicitly opens the exact pinned source',async()=>{
 render(<NativeSourceInspection worldId="w"/>);
 const source=await screen.findByRole('button',{name:/Session 8 recap/});
 expect(readNativeSource).not.toHaveBeenCalled();fireEvent.click(source);
 expect(await screen.findByText('Exact retained source text')).toBeVisible();
 expect(readNativeSource).toHaveBeenCalledWith(scope,{source_artifact_id:'sc18',source_revision_id:'src18',evidence_ref_id:'ec18'},expect.any(AbortSignal));
});
it('searches all returned sources and combines type, campaign and session filters',async()=>{
 vi.mocked(getNativeSourceCatalog).mockResolvedValue(catalog([...Array.from({length:60},(_,i)=>item(i+1)),item(8,'c2'),item(8,'c2','worldbuilding')]));
 render(<NativeSourceInspection worldId="w"/>);await screen.findByText('62 matching sources');
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'Session 60'}});expect(screen.getByRole('button',{name:/Session 60 recap/})).toBeVisible();
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:''}});
 fireEvent.change(screen.getByLabelText('Type'),{target:{value:'worldbuilding'}});
 fireEvent.change(screen.getByLabelText('Campaign'),{target:{value:'c2'}});
 fireEvent.change(screen.getByLabelText('Session'),{target:{value:'session-8'}});
 expect(screen.getByText('1 matching sources')).toBeVisible();expect(screen.getByRole('button',{name:/Worldbuilding 8/})).toBeVisible();
 expect(readNativeSource).not.toHaveBeenCalled();
});
it('keeps unnamed sources readable and reports incomplete label/filter coverage',async()=>{
 const s=item();s.navigation.label=null;s.navigation.status='unavailable';const c=catalog([s]);c.navigation_complete=false;c.catalogue.complete=false;
 vi.mocked(getNativeSourceCatalog).mockResolvedValue(c);render(<NativeSourceInspection worldId="w"/>);
 fireEvent.click(await screen.findByRole('button',{name:/Unnamed source/}));
 expect(screen.getByText(/filtered results may omit them/)).toBeVisible();expect(screen.getByText(/Partial source view/)).toBeVisible();
 expect(await screen.findByText('Exact retained source text')).toBeVisible();
});
it.each(['scope','digest','revision','evidence'] as const)('refuses substituted %s in a source reply',async field=>{
 const b=body();if(field==='scope')b.scope={...scope,binding_version:2};else if(field==='digest')b.source.body_sha256='b'.repeat(64);else if(field==='revision')b.source.source_revision_id='newer';else b.source.evidence_ref_id='other';
 vi.mocked(readNativeSource).mockResolvedValue(b);render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 expect(await screen.findByRole('alert')).toHaveTextContent('exact source is unavailable');expect(screen.queryByText('Exact retained source text')).not.toBeInTheDocument();
});
it('can retry the same selected source after an opening failure',async()=>{
 vi.mocked(readNativeSource).mockRejectedValueOnce(new Error('Opening failed')).mockResolvedValue(body());
 render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));await screen.findByRole('alert');
 fireEvent.click(screen.getByRole('button',{name:/Session 8 recap/}));expect(await screen.findByText('Exact retained source text')).toBeVisible();expect(readNativeSource).toHaveBeenCalledTimes(2);
});
it('discards late source reads when the World changes',async()=>{
 let resolve!:(v:NativeSourceBody)=>void;vi.mocked(readNativeSource).mockReturnValue(new Promise(r=>{resolve=r;}));
 const view=render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 vi.mocked(getNativeSourceCatalog).mockResolvedValue({...catalog([]),scope:{...scope,managed_world_id:'other'}});view.rerender(<NativeSourceInspection worldId="other"/>);
 await screen.findByText('0 matching sources');await act(async()=>resolve(body()));expect(screen.queryByText('Exact retained source text')).not.toBeInTheDocument();
});
it('preserves native source selection when current page metadata is newer',async()=>{
 const s=item();s.navigation.origin_matches_current_metadata=false;vi.mocked(getNativeSourceCatalog).mockResolvedValue(catalog([s]));render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 expect(screen.getByText(/Current page name/)).toBeVisible();await waitFor(()=>expect(readNativeSource).toHaveBeenCalledWith(scope,expect.objectContaining({source_revision_id:'src18'}),expect.any(AbortSignal)));
});

it('reports a catalogue lacking navigation metadata instead of crashing',async()=>{
 const c=catalog();delete (c.catalogue.sources[0] as Partial<NativeSourceMetadata>).navigation;
 vi.mocked(getNativeSourceCatalog).mockResolvedValue(c);render(<NativeSourceInspection worldId="w"/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('navigation metadata is unavailable');
 expect(readNativeSource).not.toHaveBeenCalled();
});
