import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {SurfaceWorkPlan} from './SurfaceWorkPlan';
import {WorkPlanHostProvider,type WorkPlanHost} from './WorkPlanHost';
import type {WorkPlanReference} from './workPlanReference';
import {getWorkPlan,saveWorkPlan,continueWorkPlan,type WorkPlan} from '../../api/conversationWorkPlanApi';
vi.mock('../../api/conversationWorkPlanApi',async original=>({...await original<typeof import('../../api/conversationWorkPlanApi')>(),getWorkPlan:vi.fn(),saveWorkPlan:vi.fn(),continueWorkPlan:vi.fn()}));
const ref:WorkPlanReference={schema:'dmb_surface_work_plan_ref_v1',world_id:'world',document_id:'page',conversation_id:'11111111-1111-4111-8111-111111111111',source_turn_id:'22222222-2222-4222-8222-222222222222',source_answer_sha256:'a'.repeat(64),title:'Workshop plan'};
const step='33333333-3333-4333-8333-333333333333';
const p:WorkPlan={schema:'dmb_reviewed_work_plan_v2',objective:'Prepare a useful workshop scene.',world_id:'world',document_id:'page',conversation_id:ref.conversation_id,source_turn_id:ref.source_turn_id,source_answer_sha256:ref.source_answer_sha256,revision:1,steps:[{step_id:step,text:'Read the chart.',kind:'discuss',selected:true}],execution:[],dispatches:[]};
const host=():WorkPlanHost=>({worldId:'world',documentId:'page',editable:true,busy:false,conversationId:ref.conversation_id,activeConversationId:ref.conversation_id,onContinue:vi.fn(),openReply:vi.fn()});
beforeEach(()=>{vi.clearAllMocks();sessionStorage.clear();vi.stubGlobal('crypto',webcrypto);vi.mocked(getWorkPlan).mockResolvedValue(p);});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('keeps foreign references inert, without a read or continuation',()=>{
 render(<WorkPlanHostProvider host={{...host(),documentId:'other'}}><SurfaceWorkPlan reference={ref}/></WorkPlanHostProvider>);
 expect(screen.getByText(/belongs to its original page/)).toBeInTheDocument();expect(getWorkPlan).not.toHaveBeenCalled();expect(continueWorkPlan).not.toHaveBeenCalled();
});
it('restores the existing plan by digest and edits selection without executing or saving automatically',async()=>{
 render(<WorkPlanHostProvider host={host()}><SurfaceWorkPlan reference={ref}/></WorkPlanHostProvider>);
 fireEvent.click(await screen.findByRole('checkbox',{name:'Include step 1'}));
 expect(getWorkPlan).toHaveBeenCalledWith(expect.objectContaining({documentId:'page',sourceSha256:ref.source_answer_sha256}));
 expect(continueWorkPlan).not.toHaveBeenCalled();expect(saveWorkPlan).not.toHaveBeenCalled();
 vi.mocked(saveWorkPlan).mockResolvedValue({...p,revision:2,steps:[{...p.steps[0],selected:false}]});
 fireEvent.click(screen.getByRole('button',{name:'Save',exact:true}));
 await waitFor(()=>expect(saveWorkPlan).toHaveBeenCalledWith(expect.anything(),1,[{...p.steps[0],selected:false}],'Prepare a useful workshop scene.'));
 expect(continueWorkPlan).not.toHaveBeenCalled();
});
it('lets archived source plans be inspected but not edited or silently resumed',async()=>{
 const own=host();render(<WorkPlanHostProvider host={{...own,activeConversationId:'other'}}><SurfaceWorkPlan reference={ref}/></WorkPlanHostProvider>);
 expect(await screen.findByRole('checkbox',{name:'Include step 1'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Continue step'})).toBeDisabled();expect(own.onContinue).not.toHaveBeenCalled();
});
it('shows an exact-turn affordance rather than a second plain-text result',async()=>{
 const own=host(),turn='44444444-4444-4444-8444-444444444444';
 vi.mocked(getWorkPlan).mockResolvedValue({...p,dispatches:[{command_id:step,step_id:step,client_thread_id:step,client_turn_id:turn,message:'Read the chart.'}],execution:[{command_id:step,step_id:step,status:'completed',turn_id:turn,attempt:1,result:{kind:'reply',text:'Copied result must not become an uncited second reply.'}}]});
 render(<WorkPlanHostProvider host={own}><SurfaceWorkPlan reference={ref}/></WorkPlanHostProvider>);
 fireEvent.click(await screen.findByRole('button',{name:'View reply'}));expect(own.openReply).toHaveBeenCalledWith(turn);
 expect(screen.queryByText('Copied result must not become an uncited second reply.')).not.toBeInTheDocument();
});

it('composes one editable title, move handle, plus, Save and menu in the object bar',async()=>{
 const changed=vi.fn();
 render(<WorkPlanHostProvider host={host()}><SurfaceWorkPlan reference={ref} onTitleChange={changed}
   moveHandle={<button aria-label="Move work plan">Move</button>}/></WorkPlanHostProvider>);
 await screen.findByRole('checkbox',{name:'Include step 1'});
 const bar=within(screen.getByLabelText('Plan toolbar'));
 expect(bar.getByRole('textbox',{name:'Plan title'})).toHaveValue('Workshop plan');
 expect(bar.getByRole('button',{name:'Move work plan'})).toBeInTheDocument();
 expect(bar.getByRole('button',{name:'Add step'})).toBeEnabled();
 expect(bar.getByRole('button',{name:'Save',exact:true})).toBeDisabled();
 expect(bar.getByLabelText('Plan options')).toBeInTheDocument();
 expect(screen.getAllByRole('button',{name:'Add step'})).toHaveLength(1);
 expect(screen.getAllByRole('button',{name:'Save',exact:true})).toHaveLength(1);
 const title=bar.getByRole('textbox',{name:'Plan title'});
 fireEvent.change(title,{target:{value:'Lantern plan'}});fireEvent.blur(title);
 expect(changed).toHaveBeenCalledWith('Lantern plan');expect(saveWorkPlan).not.toHaveBeenCalled();
 expect(continueWorkPlan).not.toHaveBeenCalled();
});
