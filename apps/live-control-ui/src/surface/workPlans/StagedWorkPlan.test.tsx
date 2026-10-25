import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react';
import {webcrypto} from 'node:crypto';
import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../../tiptap/MarkdownEditorCore';
import {createBuildComposeBridge,type BuildComposeEditorState} from '../../buildSurface/buildComposeBridge';
import {tiptapJsonToSemanticMarkdown} from '../../tiptap/markdown/calloutMarkdown';
import {getWorkPlan,saveWorkPlan,continueWorkPlan,type WorkPlan} from '../../api/conversationWorkPlanApi';
import {getWorkspaceDocumentSnapshot} from '../../api/liveApi';
import {StagedWorkPlan} from './StagedWorkPlan';
import {placementDigest,stagePlacement,readPlacement,type PlacementLocks} from './workPlanPlacement';
import type {WorkPlanReference} from './workPlanReference';
vi.mock('../../api/conversationWorkPlanApi',()=>({getWorkPlan:vi.fn(),saveWorkPlan:vi.fn(),continueWorkPlan:vi.fn()}));
vi.mock('../../api/liveApi',()=>({getWorkspaceDocumentSnapshot:vi.fn()}));
const conversation='11111111-1111-4111-8111-111111111111',turnId='22222222-2222-4222-8222-222222222222';
let editor:Editor,state:BuildComposeEditorState,bridge:ReturnType<typeof createBuildComposeBridge>,ref:WorkPlanReference;
let plan:WorkPlan|null,savedMarkdown:string;const onVisible=vi.fn();
beforeEach(async()=>{
 vi.clearAllMocks();localStorage.clear();sessionStorage.clear();vi.stubGlobal('crypto',webcrypto);
 let queue=Promise.resolve();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,fn:()=>Promise<unknown>)=>{const result=queue.then(fn);queue=result.then(()=>undefined,()=>undefined);return result;}} as PlacementLocks});
 editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Author text.</p>'});document.body.append(editor.view.dom);
 savedMarkdown=tiptapJsonToSemanticMarkdown(editor.getJSON());
 state={editor,worldId:'world',documentId:'page',revision:1,contentSha256:await placementDigest(savedMarkdown),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 bridge=createBuildComposeBridge(()=>state,()=>{},async(_basis,afterEditor,afterDraft)=>{
  expect(await placementDigest(JSON.stringify(editor.getJSON()))).toBe(afterEditor);
  savedMarkdown=tiptapJsonToSemanticMarkdown(editor.getJSON());expect(await placementDigest(savedMarkdown)).toBe(afterDraft);state.revision++;state.contentSha256=await placementDigest(savedMarkdown);
 });
 ref={schema:'dmb_surface_work_plan_ref_v1',world_id:'world',document_id:'page',conversation_id:conversation,source_turn_id:turnId,source_answer_sha256:await placementDigest('A plan.'),title:'Work plan'};plan=null;
 vi.mocked(getWorkPlan).mockImplementation(async()=>plan);
 vi.mocked(saveWorkPlan).mockImplementation(async(_s,revision,steps)=>{expect(revision).toBe(0);plan={schema:'dmb_reviewed_work_plan_v1',world_id:'world',document_id:'page',conversation_id:conversation,source_turn_id:turnId,source_answer_sha256:ref.source_answer_sha256,revision:1,steps,dispatches:[],execution:[]};return plan;});
 vi.mocked(getWorkspaceDocumentSnapshot).mockImplementation(async()=>({record:{world_id:'world',document_id:'page',content_status:'committed',revision:state.revision},loaded_revision:state.revision,markdown:savedMarkdown,content_sha256:state.contentSha256}) as Awaited<ReturnType<typeof getWorkspaceDocumentSnapshot>>);
});
afterEach(()=>{cleanup();editor.destroy();editor.view.dom.remove();});
const props=()=>({worldId:'world',documentId:'page',conversationId:conversation,turnId,source:'A plan.',steps:[{text:'Read the chart.',kind:'discuss' as const},{text:'Write a scene.',kind:'prepare_insertion' as const}],bridge,pointerRevision:2,disabled:false,onVisible});
async function stage(){const captured=await bridge.capture();return stagePlacement(ref,captured.basis,2,props().steps.map(s=>({...s,step_id:crypto.randomUUID(),selected:true})));}
it('places editable checkboxes on the real editor and one Save persists the same review/reference without continuation',async()=>{
 await stage();render(<StagedWorkPlan {...props()}/>);
 const checkbox=await screen.findByRole('checkbox',{name:'Include step 2'});
 expect(editor.view.dom.contains(checkbox)).toBe(true);expect(onVisible).toHaveBeenCalled();
 fireEvent.click(checkbox);fireEvent.change(screen.getByRole('textbox',{name:'Plan step 1'}),{target:{value:'Read the named chart.'}});
 expect(saveWorkPlan).not.toHaveBeenCalled();expect(continueWorkPlan).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(screen.getByText('Plan on page.')).toBeInTheDocument());
 expect(plan!.steps.map(s=>[s.text,s.selected])).toEqual([['Read the named chart.',true],['Write a scene.',false]]);
 expect(savedMarkdown.match(/dmb-work-plan-v1/g)).toHaveLength(1);expect(savedMarkdown).toContain('Author text.');
 await waitFor(async()=>expect((await readPlacement(ref))?.phase).toBe('saved'));expect(continueWorkPlan).not.toHaveBeenCalled();
});
it('retains local row edits over reload without placing or executing anything',async()=>{
 await stage();const mounted=render(<StagedWorkPlan {...props()}/>);
 fireEvent.change(await screen.findByRole('textbox',{name:'Plan step 1'}),{target:{value:'Retained local edit.'}});mounted.unmount();
 render(<StagedWorkPlan {...props()}/>);expect(await screen.findByRole('textbox',{name:'Plan step 1'})).toHaveValue('Retained local edit.');
 expect(saveWorkPlan).not.toHaveBeenCalled();expect(continueWorkPlan).not.toHaveBeenCalled();expect(savedMarkdown).not.toContain('dmb-work-plan');
});
it('keeps archived or foreign-page plans compact and inert',async()=>{
 await stage();render(<StagedWorkPlan {...props()} disabled bridge={null}/>);
 await screen.findByText('Plan ready for page placement.');expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();expect(saveWorkPlan).not.toHaveBeenCalled();expect(onVisible).not.toHaveBeenCalled();
});
it('retires stale shared placement views instead of overwriting another tab',async()=>{
 await stage();render(<StagedWorkPlan {...props()}/>);await screen.findByRole('checkbox',{name:'Include step 1'});
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:'dmb:surface-work-plan-placement:v1:'+JSON.stringify([ref.world_id,ref.document_id,ref.conversation_id,ref.source_turn_id,ref.source_answer_sha256])})));
 await waitFor(()=>expect(screen.queryByRole('checkbox')).not.toBeInTheDocument());
 expect(screen.getByText(/changed in another tab/)).toBeInTheDocument();expect(saveWorkPlan).not.toHaveBeenCalled();
});
