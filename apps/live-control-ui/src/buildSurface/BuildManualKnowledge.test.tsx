import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {BuildManualKnowledge} from './BuildManualKnowledge';
import * as api from '../api/liveApi';
import {knowledgeKey,type ManualKnowledgeScope,type ManualKnowledgeRecovery} from './buildManualKnowledge';
const state=vi.hoisted(()=>({session:{} as any,current:true,fresh:vi.fn(),failure:vi.fn(),native:vi.fn()}));
vi.mock('../markdownCanvas/MarkdownCanvasSession',()=>({useMarkdownCanvasSession:()=>state.session}));
vi.mock('../api/liveApi',async original=>({...await original<typeof import('../api/liveApi')>(),prepareGraphObjectAuthoringWrite:vi.fn(),commitGraphObjectAuthoringWrite:vi.fn()}));
// Dispatcher boundary double. Real native form/wire/journal behavior is exercised
// separately in NativeManualKnowledge, nativeManualKnowledgeApi and recovery tests.
vi.mock('./NativeManualKnowledge',()=>({NativeManualKnowledge:(props:any)=>{state.native(props);return <section aria-label="Native dispatcher destination"><button onClick={()=>{try{state.fresh(props.getFresh());}catch(e){state.failure(e);}}}>Probe committed source</button></section>;}}));
const hash='b'.repeat(64);
const props:any={worldId:'world-a',document:{document_id:'doc-a',world_id:'world-a',kind:'worldbuilding_source'},
 run:{run_id:'run-a',source_artifact_id:'source-a',source_domain:'worldbuilding',status:'reviewable',revision:7},
 handoff:{document_id:'doc-a',document_revision:2,extraction_run_id:'run-a',source_artifact_id:'source-a'},
 sourceContentSha256:hash,review:null,isScopeCurrent:()=>state.current};
const scope:ManualKnowledgeScope={worldId:'world-a',documentId:'doc-a',revision:2,hash,runId:'run-a',artifactId:'source-a'};
function legacy(submitted=true):ManualKnowledgeRecovery{return {schema:'dmb_build_manual_knowledge_v1',scope:{...scope},
 request:{worldId:scope.worldId,campaignId:scope.worldId,sourceRunId:scope.runId,proposals:[{localProposalId:'one',proposalKind:'object',objectRef:{label:'Mara',kind:'npc'},selection:{sourceArtifactId:scope.artifactId,sourceArtifactSha256:hash,sourceSpanRefId:'original-span',selectedText:'Mara keeps the bell.'}}]} as any,
 prepared:{prepared:true,campaign_id:scope.worldId,world_id:'native-a',source_artifact_id:scope.artifactId,confirm_token:'original-signed-token',expressibility:'EXPRESSIBLE',authority_operation_id:'op-a',current_overlay_token:'overlay-a',assertions_preview:[{assertion_id:'assert-a',summary:'Create Mara'}]} as any,
 submitted,receipt:null};}
const receipt:any={committed:true,campaign_id:scope.worldId,world_id:'native-a',operation_id:'op-a',published_revision_id:'rev:b'};
function retain(value=legacy()){const key=knowledgeKey(value.scope),raw=JSON.stringify(value);localStorage.setItem(key,raw);return {key,raw,value};}
beforeEach(()=>{vi.clearAllMocks();localStorage.clear();state.current=true;state.session={phase:'ready_clean',dirty:false,record:props.document,
 snapshot:{loaded_revision:2,content_sha256:hash,markdown:'Mara keeps the bell.'},editor:null};
 Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,fn:()=>unknown)=>Promise.resolve(fn())}});
 vi.mocked(api.commitGraphObjectAuthoringWrite).mockResolvedValue(receipt);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('routes fresh work to vNext without classic preparation or candidate/review dependence',()=>{
 render(<BuildManualKnowledge {...props}/>);fireEvent.click(screen.getByRole('button',{name:'Probe committed source'}));
 expect(state.fresh).toHaveBeenCalledWith({selector:{schema:'dmb_native_manual_context_v1',managedWorldId:'world-a',documentId:'doc-a',documentRevision:2,bodySha256:hash,runId:'run-a',runRevision:7},markdown:'Mara keeps the bell.'});
 expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it.each(['dirty','revision','hash','world','phase','run','not-current'])('refuses fresh %s context at the dispatcher boundary',change=>{
 if(change==='dirty')state.session.dirty=true;if(change==='revision')state.session.snapshot.loaded_revision=3;
 if(change==='hash')state.session.snapshot.content_sha256='c'.repeat(64);if(change==='world')state.session.record={...props.document,world_id:'foreign'};
 if(change==='phase')state.session.phase='conflict';if(change==='not-current')state.current=false;
 const selected=change==='run'?{...props,run:{...props.run,run_id:'foreign-run'}}:props;
 render(<BuildManualKnowledge {...selected}/>);fireEvent.click(screen.getByRole('button',{name:'Probe committed source'}));
 expect(state.failure).toHaveBeenCalled();expect(state.fresh).not.toHaveBeenCalled();expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('discovers submitted classic recovery before mutable source, run, editor or review readiness',async()=>{
 const old=retain();state.session={phase:'conflict',dirty:true,record:null,snapshot:null,editor:null};
 render(<BuildManualKnowledge {...props} run={{...props.run,run_id:'later-run',revision:90}} handoff={{...props.handoff,document_revision:99}}/>);
 expect(screen.getByRole('button',{name:'Retry original classic confirmation'})).toBeEnabled();expect(state.native).not.toHaveBeenCalled();
 expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Retry original classic confirmation'}));
 await screen.findByText('Original classic confirmation acknowledged.');
 expect(api.commitGraphObjectAuthoringWrite).toHaveBeenCalledExactlyOnceWith({...old.value.request,confirmToken:'original-signed-token',currentOverlayToken:'overlay-a'});
 expect(JSON.parse(localStorage.getItem(old.key)!).receipt).toEqual(receipt);expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it.each(['lost response','later auth refusal','later deterministic refusal'])('retains original submitted classic bytes after %s',async reason=>{
 const old=retain();vi.mocked(api.commitGraphObjectAuthoringWrite).mockRejectedValue(new Error(reason));render(<BuildManualKnowledge {...props}/>);
 fireEvent.click(screen.getByRole('button',{name:'Retry original classic confirmation'}));await screen.findByRole('alert');
 expect(localStorage.getItem(old.key)).toBe(old.raw);expect(screen.queryByRole('button',{name:/Archive unsubmitted/})).not.toBeInTheDocument();
 expect(state.native).not.toHaveBeenCalled();expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('never dispatches an unsubmitted classic review and archives only after an explicit action',async()=>{
 const old=retain(legacy(false));render(<BuildManualKnowledge {...props}/>);expect(api.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
 expect(screen.queryByRole('button',{name:'Retry original classic confirmation'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Archive unsubmitted classic review and refresh'}));await screen.findByRole('region',{name:'Native dispatcher destination'});
 expect(localStorage.getItem(old.key)).toBeNull();expect(Object.values(localStorage)).toContain(old.raw);expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
});
it('preserves the active classic record if archival storage fails',async()=>{
 const old=retain(legacy(false));const set=Storage.prototype.setItem;vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(key,raw){if(key.includes(':retained:'))throw new Error('quota');return set.call(this,key,raw);});
 render(<BuildManualKnowledge {...props}/>);fireEvent.click(screen.getByRole('button',{name:'Archive unsubmitted classic review and refresh'}));await screen.findByText('quota');expect(localStorage.getItem(old.key)).toBe(old.raw);expect(state.native).not.toHaveBeenCalled();
});
it('blocks corrupt original data without dispatch or a fresh native fallback',()=>{
 const key=knowledgeKey(scope);localStorage.setItem(key,'{broken');render(<BuildManualKnowledge {...props}/>);expect(screen.getByRole('alert')).toBeInTheDocument();expect(state.native).not.toHaveBeenCalled();expect(localStorage.getItem(key)).toBe('{broken');
});
it('detects a competing-tab record before retry and never sends the superseded packet',async()=>{
 const old=retain();render(<BuildManualKnowledge {...props}/>);localStorage.setItem(old.key,'different original bytes');fireEvent.click(screen.getByRole('button',{name:'Retry original classic confirmation'}));await screen.findByRole('alert');expect(api.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();expect(localStorage.getItem(old.key)).toBe('different original bytes');
});
it('preserves the submitted packet after a late acknowledgement following unmount',async()=>{
 const old=retain();let finish!:(r:any)=>void;vi.mocked(api.commitGraphObjectAuthoringWrite).mockReturnValue(new Promise(resolve=>{finish=resolve;}));
 const view=render(<BuildManualKnowledge {...props}/>);fireEvent.click(screen.getByRole('button',{name:'Retry original classic confirmation'}));await waitFor(()=>expect(api.commitGraphObjectAuthoringWrite).toHaveBeenCalledTimes(1));view.unmount();await act(async()=>finish(receipt));expect(localStorage.getItem(old.key)).toBe(old.raw);
 render(<BuildManualKnowledge {...props}/>);expect(screen.getByRole('button',{name:'Retry original classic confirmation'})).toBeEnabled();
});
it('isolates World/document changes and reacts to storage-event corruption',()=>{
 const view=render(<BuildManualKnowledge {...props}/>);retain();act(()=>window.dispatchEvent(new StorageEvent('storage')));expect(screen.getByRole('button',{name:'Retry original classic confirmation'})).toBeInTheDocument();
 view.rerender(<BuildManualKnowledge {...props} worldId="world-b" document={{...props.document,world_id:'world-b',document_id:'doc-b'}}/>);expect(screen.getByRole('region',{name:'Native dispatcher destination'})).toBeInTheDocument();
});
