import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {BuildManualKnowledge} from './BuildManualKnowledge';
import * as api from '../api/liveApi';
import * as extract from '../api/extractPromoteApi';
import {knowledgeKey,type ManualKnowledgeScope} from './buildManualKnowledge';
const state=vi.hoisted(()=>({session:{} as any,current:true}));
vi.mock('../markdownCanvas/MarkdownCanvasSession',()=>({useMarkdownCanvasSession:()=>state.session}));
vi.mock('../api/liveApi',()=>({postManagedWorldGraphProjection:vi.fn(),prepareGraphObjectAuthoringWrite:vi.fn(),commitGraphObjectAuthoringWrite:vi.fn()}));
vi.mock('../api/extractPromoteApi',()=>({getWorldbuildingFrozenSpans:vi.fn()}));
const hash='b'.repeat(64),candidate='a'.repeat(64),index='e'.repeat(64);
const props:any={worldId:'world-a',document:{document_id:'doc-a',world_id:'world-a',kind:'worldbuilding_source'},
 run:{run_id:'run-a',source_artifact_id:'source-a',source_domain:'worldbuilding',status:'reviewable',revision:7,
 components:{candidate_graph:{sha256:candidate},source_span_index:{sha256:index}}},
 handoff:{document_id:'doc-a',document_revision:2,extraction_run_id:'run-a',source_artifact_id:'source-a'},
 sourceContentSha256:hash,review:{sourceArtifactId:'source-a',sourceRevisionId:'sha256:'+hash,assertions:[]},isScopeCurrent:()=>state.current};
const scope:ManualKnowledgeScope={worldId:'world-a',documentId:'doc-a',revision:2,hash,runId:'run-a',artifactId:'source-a'};
const catalog:any={schema:'dmb_worldbuilding_frozen_span_catalog_v1',parentRunId:'run-a',parentRevision:7,parentStatus:'reviewable',
 worldId:'world-a',sourceArtifactId:'source-a',sourceSha256:hash,spanIndexSha256:index,parentCandidateSha256:candidate,
 spans:[{sourceSpanRefId:'span-a',startLine:1,endLine:1,paragraphText:'Mara keeps the copper bell.'}],evidenceRefs:[]};
const prepared:any={prepared:true,campaign_id:'world-a',world_id:'native-a',source_artifact_id:'source-a',confirm_token:'signed-token',
 expressibility:'EXPRESSIBLE',authority_operation_id:'operation-a',current_overlay_token:'overlay-a',assertions_preview:[{assertion_id:'assert-a',summary:'Create Mara'}]};
const receipt:any={committed:true,campaign_id:'world-a',world_id:'native-a',operation_id:'operation-a',published_revision_id:'revision-b'};
afterEach(cleanup);
beforeEach(()=>{vi.resetAllMocks();localStorage.clear();state.current=true;
 state.session={phase:'ready_clean',dirty:false,record:props.document,snapshot:{loaded_revision:2,content_sha256:hash},
 editor:{state:{selection:{from:1,to:5},doc:{textBetween:()=> 'Mara'}}}};
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:async(_key:string,fn:()=>unknown)=>fn()}});
 vi.mocked(extract.getWorldbuildingFrozenSpans).mockResolvedValue(catalog);
 vi.mocked(api.postManagedWorldGraphProjection).mockResolvedValue({schema:'dmb_managed_world_graph_projection_v1',managedWorldId:'world-a',nativeWorldId:'native-a',bindingVersion:1,
 projection:{schema:'dmb_world_graph_projection_v1',snapshot:{worldId:'native-a',campaignId:'',scopeMode:'world',focus:{kind:'none',sessionId:null},admissibility:'gm',isHead:true,revisionId:'head-a',headRevisionId:'head-a'},nodes:[
 {nodeId:'mara',label:'Mara',kind:'npc',role:'keeper'},{nodeId:'quarry',label:'Quarry',kind:'location',role:'location'}]}} as any);
 vi.mocked(api.prepareGraphObjectAuthoringWrite).mockResolvedValue(prepared);
 vi.mocked(api.commitGraphObjectAuthoringWrite).mockResolvedValue(receipt);
});
async function stage(){await screen.findByRole('button',{name:'Use selected document text'});
 await waitFor(()=>expect(screen.getByRole('button',{name:'Use selected document text'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Use selected document text'}));
 fireEvent.change(screen.getByLabelText('Name'),{target:{value:'Mara'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview World change'}));
 await screen.findByRole('button',{name:'Confirm World change'});
}
it('previews exact frozen selection then explicitly confirms and retains receipt',async()=>{
 render(<BuildManualKnowledge {...props}/>);await stage();
 expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
 const request=vi.mocked(api.prepareGraphObjectAuthoringWrite).mock.calls[0][0];
 expect(request).toMatchObject({worldId:'world-a',campaignId:'world-a',sourceRunId:'run-a'});
 expect(request.proposals[0].selection).toMatchObject({selectedText:'Mara',sourceSpanRefId:'span-a',sourceArtifactId:'source-a',sourceArtifactSha256:hash});
 fireEvent.click(screen.getByRole('button',{name:'Confirm World change'}));
 await screen.findByText('World knowledge published. It is available for cited retrieval.');
 expect(api.commitGraphObjectAuthoringWrite).toHaveBeenCalledWith({...request,confirmToken:'signed-token',currentOverlayToken:'overlay-a'});
 expect(JSON.parse(localStorage.getItem(knowledgeKey(scope))!).receipt.operation_id).toBe('operation-a');
 await waitFor(()=>expect(api.postManagedWorldGraphProjection).toHaveBeenCalledTimes(2));
 expect(extract.getWorldbuildingFrozenSpans).toHaveBeenCalledTimes(1);
});
it('recovers an uncertain confirmation after remount with identical request and token',async()=>{
 vi.mocked(api.commitGraphObjectAuthoringWrite).mockRejectedValueOnce(new Error('Response lost'));
 const view=render(<BuildManualKnowledge {...props}/>);await stage();fireEvent.click(screen.getByRole('button',{name:'Confirm World change'}));
 await screen.findByRole('button',{name:'Retry exact confirmation'});await waitFor(()=>expect(screen.getByRole('button',{name:'Retry exact confirmation'})).toBeEnabled());
 const first=vi.mocked(api.commitGraphObjectAuthoringWrite).mock.calls[0][0];view.unmount();
 render(<BuildManualKnowledge {...props}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Retry exact confirmation'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Retry exact confirmation'}));await screen.findByText('World knowledge published. It is available for cited retrieval.');
 expect(vi.mocked(api.commitGraphObjectAuthoringWrite).mock.calls[1][0]).toEqual(first);
 expect(api.prepareGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1);
});
it.each(['dirty','revision','hash','world','phase'])('refuses %s context before preview',async(change)=>{
 if(change==='dirty')state.session.dirty=true;
 if(change==='revision')state.session.snapshot.loaded_revision=3;
 if(change==='hash')state.session.snapshot.content_sha256='c'.repeat(64);
 if(change==='world')state.session.record={...props.document,world_id:'foreign'};
 if(change==='phase')state.session.phase='conflict';
 render(<BuildManualKnowledge {...props}/>);await screen.findByText(/Save the document and reopen/);
 expect(screen.getByRole('button',{name:'Use selected document text'})).toBeDisabled();expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('retains a late acknowledgement in its original recovery record after unmount',async()=>{
 let finish!:(r:any)=>void;vi.mocked(api.commitGraphObjectAuthoringWrite).mockReturnValue(new Promise(resolve=>{finish=resolve;}));
 const view=render(<BuildManualKnowledge {...props}/>);await stage();fireEvent.click(screen.getByRole('button',{name:'Confirm World change'}));
 await waitFor(()=>expect(api.commitGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1));view.unmount();state.current=false;
 await act(async()=>finish(receipt));expect(JSON.parse(localStorage.getItem(knowledgeKey(scope))!).receipt).toEqual(receipt);
});
it('refuses competing-tab storage instead of replacing a pending request',async()=>{
 render(<BuildManualKnowledge {...props}/>);await stage();const foreign='{"held":"other tab"}';localStorage.setItem(knowledgeKey(scope),foreign);
 fireEvent.click(screen.getByRole('button',{name:'Confirm World change'}));await screen.findByText(/saved authoring changed/);
 expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(localStorage.getItem(knowledgeKey(scope))).toBe(foreign);
});
it('blocks corrupt persisted preparation without dispatch or crashing',async()=>{
 localStorage.setItem(knowledgeKey(scope),'{bad json');render(<BuildManualKnowledge {...props}/>);
 expect(screen.getByRole('alert')).toBeInTheDocument();expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('stages a relationship between exact current World nodes',async()=>{
 render(<BuildManualKnowledge {...props}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Use selected document text'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Use selected document text'}));fireEvent.change(screen.getByLabelText('Declare'),{target:{value:'relationship'}});
 fireEvent.change(screen.getByLabelText('From'),{target:{value:'mara'}});fireEvent.change(screen.getByLabelText('To'),{target:{value:'quarry'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview World change'}));await screen.findByRole('button',{name:'Confirm World change'});
 expect(vi.mocked(api.prepareGraphObjectAuthoringWrite).mock.calls[0][0].proposals[0]).toMatchObject({proposalKind:'relationship',
 sourceObjectRef:{nodeId:'mara'},targetObjectRef:{nodeId:'quarry'},relationshipType:'located_in'});
});

it('rejects contradictory native provenance before exposing endpoint nodes',async()=>{
 const response=await api.postManagedWorldGraphProjection({} as any);response.projection.snapshot.worldId='foreign-native';
 vi.mocked(api.postManagedWorldGraphProjection).mockResolvedValue(response);
 render(<BuildManualKnowledge {...props}/>);await screen.findByText(/does not match envelope world/);
 expect(screen.getByRole('button',{name:'Use selected document text'})).toBeDisabled();
 expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('distinguishes same-name endpoints in choices and retained directional preview',async()=>{
 const response=await api.postManagedWorldGraphProjection({} as any);
 response.projection.nodes=[{nodeId:'mara-east',label:'Mara',kind:'npc',role:'keeper',summary:'East gate keeper'},
 {nodeId:'mara-west',label:'Mara',kind:'npc',role:'keeper',summary:'West gate keeper'}] as any;
 vi.mocked(api.postManagedWorldGraphProjection).mockResolvedValue(response);
 render(<BuildManualKnowledge {...props}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Use selected document text'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Use selected document text'}));fireEvent.change(screen.getByLabelText('Declare'),{target:{value:'relationship'}});
 const from=screen.getByLabelText('From') as HTMLSelectElement,to=screen.getByLabelText('To') as HTMLSelectElement;
 expect([...from.options].map(o=>o.label)).toEqual(['Choose object','Mara · npc · keeper · East gate keeper · mara-east','Mara · npc · keeper · West gate keeper · mara-west']);
 fireEvent.change(from,{target:{value:'mara-west'}});fireEvent.change(to,{target:{value:'mara-east'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview World change'}));await screen.findByRole('button',{name:'Confirm World change'});
 const terms=[...screen.getByLabelText('Author World knowledge').querySelectorAll('dd')].map(n=>n.textContent);
 expect(terms).toEqual(['Mara · npc · keeper · West gate keeper · mara-west','located_in','Mara · npc · keeper · East gate keeper · mara-east']);
});

it('blocks a corrupted retained relationship before React rendering and preserves its exact bytes',async()=>{
 const view=render(<BuildManualKnowledge {...props}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Use selected document text'})).toBeEnabled());
 fireEvent.click(screen.getByRole('button',{name:'Use selected document text'}));fireEvent.change(screen.getByLabelText('Declare'),{target:{value:'relationship'}});
 fireEvent.change(screen.getByLabelText('From'),{target:{value:'mara'}});fireEvent.change(screen.getByLabelText('To'),{target:{value:'quarry'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview World change'}));await screen.findByRole('button',{name:'Confirm World change'});view.unmount();
 const saved=JSON.parse(localStorage.getItem(knowledgeKey(scope))!);saved.request.proposals[0].relationshipType={unexpected:'object'};
 const raw=JSON.stringify(saved);localStorage.setItem(knowledgeKey(scope),raw);
 render(<BuildManualKnowledge {...props}/>);expect(screen.getByRole('alert')).toHaveTextContent('Saved proposal fields are invalid');
 expect(localStorage.getItem(knowledgeKey(scope))).toBe(raw);expect(screen.queryByRole('button',{name:'Confirm World change'})).not.toBeInTheDocument();
 expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});

it('reuses the exact parent review catalog without a second source read',async()=>{
 render(<BuildManualKnowledge {...props} frozenCatalog={catalog}/>);
 await waitFor(()=>expect(screen.getByRole('button',{name:'Use selected document text'})).toBeEnabled());
 expect(extract.getWorldbuildingFrozenSpans).not.toHaveBeenCalled();
});

it('mounts the frozen paragraph list only when explicitly expanded',async()=>{
 render(<BuildManualKnowledge {...props}/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Use selected document text'})).toBeEnabled());
 expect(screen.queryByRole('button',{name:'Use passage · lines 1–1'})).not.toBeInTheDocument();
 const details=screen.getByText('Choose a saved passage').closest('details')!;
 details.open=true;fireEvent(details,new Event('toggle'));
 await screen.findByRole('button',{name:'Use passage · lines 1–1'});
});
