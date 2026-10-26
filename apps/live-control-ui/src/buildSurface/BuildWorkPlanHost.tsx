import {useEffect,useMemo,useRef,type ReactNode} from 'react';
import {useWorldAgentConversationState} from '../agentInteraction/WorldAgentConversation';
import {useAgentInteraction} from '../agentInteraction/useAgentInteraction';
import {queueSurfaceConversationRequest} from '../agentInteraction/surfaceConversationRequests';
import type {MarkdownCanvasSessionValue} from '../markdownCanvas/MarkdownCanvasSession';
import type {BuildComposeBridge} from './buildComposeBridge';
import {WorkPlanHostProvider,type WorkPlanHost} from '../surface/workPlans/WorkPlanHost';

/** Build supplies an admitted host; the shared object owns no Build transport. */
export function BuildWorkPlanHost({session,bridge,children}:{session:MarkdownCanvasSessionValue;bridge:BuildComposeBridge;children:ReactNode}){
  const registry=useWorldAgentConversationState(),agent=useAgentInteraction();
  const worldId=session.record?.world_id??'',documentId=session.documentId;
  const editable=session.lookupAdmission('editable').ok&&!session.activeCommand;
  const clean=session.lookupAdmission('committed_clean').ok&&!session.activeCommand&&!registry?.pendingTurn;
  const fence=[worldId,documentId,session.editor,session.snapshot,registry?.history?.conversation_id,registry?.history?.active_conversation_id,registry?.history?.pointer_revision,editable,clean];
  const lifecycle=useRef({fence,epoch:0});if(fence.some((value,i)=>value!==lifecycle.current.fence[i]))lifecycle.current={fence,epoch:lifecycle.current.epoch+1};
  const current=useRef({session,registry,epoch:lifecycle.current.epoch});current.current={session,registry,epoch:lifecycle.current.epoch};
  useEffect(()=>()=>{current.current={...current.current,epoch:-1};},[]);
  const host=useMemo<WorkPlanHost>(()=>({
    worldId,documentId,editable,canContinue:clean,
    beginContinuation:plan=>{
      const start=current.current,snapshot=start.session.snapshot,editor=start.session.editor,pointer=start.registry?.history;
      if(!snapshot||!editor||!pointer||plan.world_id!==worldId||plan.document_id!==documentId
       ||pointer.conversation_id!==plan.conversation_id||pointer.active_conversation_id!==plan.conversation_id
       ||!start.session.lookupAdmission('committed_clean').ok||start.session.activeCommand||start.registry?.pendingTurn)
       throw new Error('Save and open the original page and active conversation before continuing.');
      return()=>{const now=current.current;return now.epoch===start.epoch&&now.session.editor===editor&&now.session.snapshot===snapshot
       &&now.session.record?.world_id===worldId&&now.session.documentId===documentId&&now.session.lookupAdmission('committed_clean').ok
       &&!now.session.activeCommand&&!now.registry?.pendingTurn&&now.registry?.history?.conversation_id===plan.conversation_id
       &&now.registry.history.active_conversation_id===plan.conversation_id&&now.registry.history.pointer_revision===pointer.pointer_revision;};
    },
    busy:!!registry?.pendingTurn,conversationId:registry?.history?.conversation_id??null,
    activeConversationId:registry?.history?.active_conversation_id??null,
    onContinue:(plan,dispatch,reference)=>{
      const start=current.current,snapshot=start.session.snapshot,editor=start.session.editor,pointer=start.registry?.history;
      if(plan.world_id!==worldId||plan.document_id!==documentId||!snapshot||!editor||!pointer
        ||pointer.conversation_id!==plan.conversation_id||pointer.active_conversation_id!==plan.conversation_id
        ||!start.session.lookupAdmission('committed_clean').ok||start.session.activeCommand||start.registry?.pendingTurn)
        throw new Error('Open the original editable page and active conversation to continue this plan.');
      const isCurrent=()=>{
        const now=current.current;
        return now.epoch===start.epoch&&now.session.record?.world_id===worldId&&now.session.documentId===documentId&&now.session.editor===editor
          &&now.session.snapshot===snapshot&&now.session.lookupAdmission('committed_clean').ok&&!now.session.activeCommand&&!now.registry?.pendingTurn&&now.registry?.history?.conversation_id===plan.conversation_id
          &&now.registry.history.active_conversation_id===plan.conversation_id&&now.registry.history.pointer_revision===pointer.pointer_revision;
      };
      const step=plan.steps.find(item=>item.step_id===dispatch.step_id);
      if(!step)throw new Error('The continuation has no matching reviewed step.');
      queueSurfaceConversationRequest({id:'reviewed-plan:'+dispatch.client_turn_id,worldId,surfaceId:'build',objectId:documentId,
        message:dispatch.message,clientThreadId:dispatch.client_thread_id,turnId:dispatch.client_turn_id,
        ...(reference?{reviewedStep:reference,reviewedKind:step.kind}:{}),...(dispatch.authored_references?{authoredReferences:dispatch.authored_references}:{}),isCurrent});
      agent.setPaneOpen(true);
    },
    openReply:turnId=>{
      const before=current.current;
      if(!before.registry?.history?.turns.some(turn=>turn.turn_id===turnId))return;
      const conversation=before.registry.history.conversation_id;agent.setPaneOpen(true);
      requestAnimationFrame(()=>{
        if(current.current.session.documentId!==documentId||current.current.registry?.history?.conversation_id!==conversation)return;
        const messages=current.current.registry?.build?.value.presentationHosts?.messages;
        const turn=messages?.querySelector<HTMLElement>('[data-turn-id="'+CSS.escape(turnId)+'"]');
        turn?.scrollIntoView({block:'start'});turn?.focus({preventScroll:true});
      });
    },
  }),[worldId,documentId,editable,clean,lifecycle.current.epoch,session.phase,session.activeCommand,registry?.pendingTurn,registry?.history?.conversation_id,registry?.history?.active_conversation_id,bridge]);
  return <WorkPlanHostProvider host={host}>{children}</WorkPlanHostProvider>;
}
