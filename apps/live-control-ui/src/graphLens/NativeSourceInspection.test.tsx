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
function body(s=item()):NativeSourceBody{return {schema:'dmb_native_source_body_v1',scope,section_catalog:{selector_policy:'markdown_sections_v1',sections:[{section_id:'a'.repeat(64),label:'Full source',line_start:1,line_end:1,char_start:0,char_end:26}]},source:{status:'available',source_artifact_id:s.source_artifact.source_artifact_id,source_revision_id:s.source_revision.source_revision_id,body_text:'Exact retained source text',body_sha256:s.source_revision.content_sha256,evidence_ref_id:s.evidence_ref_ids[0],source_authority_epoch:1}};}
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

function passageBody(s=item()):NativeSourceBody {
 const result=body(s);
 // Astral Unicode makes UTF-16 slicing observably different from native offsets.
 result.source.body_text='# Same\r\n🌿 first\r\n# Same\r\nSecond passage\r\n';
 result.section_catalog!.sections=[
  {section_id:'a'.repeat(64),label:'Same',line_start:1,line_end:2,char_start:0,char_end:17},
  {section_id:'b'.repeat(64),label:'Same',line_start:3,line_end:4,char_start:17,char_end:41},
 ];
 return result;
}
it('opens exact native passages without reparsing headings or fetching another body',async()=>{
 const packet=passageBody();vi.mocked(readNativeSource).mockResolvedValue(packet);
 render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 const picker=await screen.findByRole('combobox',{name:'Read passage'});
 expect(screen.getByRole('option',{name:'Same · lines 1–2'})).toBeInTheDocument();
 expect(screen.getByRole('option',{name:'Same · lines 3–4'})).toBeInTheDocument();
 fireEvent.change(picker,{target:{value:'b'.repeat(64)}});
 expect(screen.getByText('# Same\r\nSecond passage\r\n',{exact:true,normalizer:v=>v})).toBeVisible();
 expect(screen.queryByText(/🌿 first/)).not.toBeInTheDocument();
 expect(screen.getByText('Lines 3–4 of this saved source.')).toBeVisible();
 expect(screen.getByText('Section: '+'b'.repeat(64))).toBeInTheDocument();
 fireEvent.change(picker,{target:{value:'a'.repeat(64)}});
 expect(screen.getByText('# Same\r\n🌿 first\r\n',{exact:true,normalizer:v=>v})).toBeVisible();
 fireEvent.change(picker,{target:{value:''}});
 expect(screen.getByText(packet.source.body_text,{exact:true,normalizer:v=>v})).toBeVisible();
 expect(readNativeSource).toHaveBeenCalledTimes(1);
});
it('does not present whole-body exposure as a smaller passage',async()=>{
 render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 await screen.findByText('This source has no smaller sections.');
 expect(screen.getByRole('combobox',{name:'Read passage'})).toHaveValue('');
 expect(screen.queryByRole('option',{name:/Full source · lines/})).not.toBeInTheDocument();
});
it.each(['missing','overlap','duplicate','utf16','line-mismatch','line-overflow'] as const)('rejects %s passage descriptors without showing text',async problem=>{
 const packet=passageBody();
 if(problem==='missing')delete (packet as Partial<NativeSourceBody>).section_catalog;
 else if(problem==='overlap')packet.section_catalog!.sections[1].char_start=16;
 else if(problem==='duplicate')packet.section_catalog!.sections[1].section_id='a'.repeat(64);
 else if(problem==='line-mismatch')packet.section_catalog!.sections[0].line_end=1;
 else if(problem==='line-overflow')packet.section_catalog!.sections[1].line_end=400;
 else packet.section_catalog!.sections[1].char_end=packet.source.body_text.length;
 vi.mocked(readNativeSource).mockResolvedValue(packet);
 render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 expect(await screen.findByRole('alert')).toHaveTextContent('exact source passages are unavailable');
 expect(screen.queryByText(/🌿 first/)).not.toBeInTheDocument();
});
it('resets the passage on a different source and on refresh',async()=>{
 const other=item(9);vi.mocked(getNativeSourceCatalog).mockResolvedValue(catalog([item(),other]));
 vi.mocked(readNativeSource).mockImplementation(async(_scope,selected)=>passageBody(selected.source_artifact_id===other.source_artifact.source_artifact_id?other:item()));
 render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 fireEvent.change(await screen.findByRole('combobox',{name:'Read passage'}),{target:{value:'b'.repeat(64)}});
 fireEvent.click(screen.getByRole('button',{name:/Session 9 recap/}));
 expect(await screen.findByRole('combobox',{name:'Read passage'})).toHaveValue('');
 fireEvent.change(screen.getByRole('combobox',{name:'Read passage'}),{target:{value:'b'.repeat(64)}});
 fireEvent.click(screen.getByRole('button',{name:'Refresh sources'}));
 expect(await screen.findByText('Choose a source to read its saved text.')).toBeVisible();
 expect(screen.queryByRole('combobox',{name:'Read passage'})).not.toBeInTheDocument();
});

it('keeps an admitted whitespace-only source readable with explicitly absent sections',async()=>{
 const packet=body();packet.source.body_text=' \r\n\t';packet.section_catalog=null;
 vi.mocked(readNativeSource).mockResolvedValue(packet);
 render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 await screen.findByText('This source has no smaller sections.');
 expect(screen.getByRole('article',{name:'Selected source'}).textContent).toContain(packet.source.body_text);
 expect(screen.getByRole('combobox',{name:'Read passage'})).toHaveValue('');
});
it('uses native line boundaries for all splitlines separators, not just LF',async()=>{
 const packet=passageBody();packet.source.body_text='abc\u0085def\u2028ghi\x1c';
 packet.section_catalog!.sections=[
  {section_id:'a'.repeat(64),label:'First',line_start:1,line_end:1,char_start:0,char_end:4},
  {section_id:'b'.repeat(64),label:'Rest',line_start:2,line_end:3,char_start:4,char_end:12},
 ];
 vi.mocked(readNativeSource).mockResolvedValue(packet);
 render(<NativeSourceInspection worldId="w"/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 fireEvent.change(await screen.findByRole('combobox',{name:'Read passage'}),{target:{value:'b'.repeat(64)}});
 expect(screen.getByText('def\u2028ghi\x1c',{exact:true,normalizer:v=>v})).toBeVisible();
});

it('includes the exact opened source or native section as unread author input',async()=>{
 const packet=passageBody(),choose=vi.fn();vi.mocked(readNativeSource).mockResolvedValue(packet);
 render(<NativeSourceInspection worldId="w" onChoose={choose}/>);fireEvent.click(await screen.findByRole('button',{name:/Session 8 recap/}));
 fireEvent.click(await screen.findByRole('button',{name:'Include source'}));
 expect(choose).toHaveBeenLastCalledWith({schema:'dmb_authored_source_reference_v1',managed_world_id:'w',native_world_id:'n',binding_version:1,knowledge_revision:'r1',source_artifact_id:'sc18',source_revision_id:'src18',evidence_ref_id:'ec18',content_sha256:'a'.repeat(64),selection_kind:'full_document',section_id:null,label:'Session 8 recap'});
 fireEvent.change(screen.getByRole('combobox',{name:'Read passage'}),{target:{value:'b'.repeat(64)}});
 fireEvent.click(screen.getByRole('button',{name:'Include passage'}));
 expect(choose).toHaveBeenLastCalledWith(expect.objectContaining({selection_kind:'section',section_id:'b'.repeat(64),source_revision_id:'src18'}));
 expect(readNativeSource).toHaveBeenCalledTimes(1);
});
