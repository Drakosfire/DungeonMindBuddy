import {useEffect,useLayoutEffect,useMemo,useSyncExternalStore} from 'react';
import {useAgentInteraction} from '../agentInteraction/useAgentInteraction';
import type {SurfaceInteractionToolContribution, SurfaceInteractionProjectionDescriptor} from '../surfaceInteraction/types';
import {deferredComponent} from '../ui/deferredComponent';
export const COMBAT_TOOL_ID='combat';
export const COMBAT_TOOL:SurfaceInteractionToolContribution={id:COMBAT_TOOL_ID,label:'Combat',
  placement:{groupId:'table',groupLabel:'At the table',groupOrder:20,itemOrder:0},
  availability:{status:'enabled'},activation:{kind:'projection',projectionId:COMBAT_TOOL_ID}};
export const COMBAT_PROJECTION:SurfaceInteractionProjectionDescriptor={id:COMBAT_TOOL_ID,kind:'tool',preferredSize:'wide',bindingIds:[]};
const DeferredCombat=deferredComponent(()=>import('../surface/modules/CombatRosterModule').then(module=>({default:module.CombatRosterModule})),'Combat');
const DeferredPlanEncounter=deferredComponent(()=>import('./PlanSceneEncounter').then(module=>({default:module.PlanSceneEncounter})),'Scene encounter');
type Context=import('./sceneTemplatesApi').PlanEncounterContext|import('./RunSceneEncounter').RunEncounterContext|null|undefined;
const DeferredRunEncounter=deferredComponent(()=>import('./RunSceneEncounter').then(module=>({default:module.RunSceneEncounter})),'Scene encounter');
function createContextStore(initial:Context){
 let value=initial;const listeners=new Set<()=>void>();
 return {get:()=>value,subscribe:(listener:()=>void)=>{listeners.add(listener);return()=>{listeners.delete(listener);};},
  set:(next:Context)=>{if(next!==value){value=next;listeners.forEach(listener=>listener());}}};
}
function CombatProjectionContent({store,surfaceId}:{store:ReturnType<typeof createContextStore>;surfaceId:string}){
 const context=useSyncExternalStore(store.subscribe,store.get);
 return surfaceId==='plan' ? context && 'documentId' in context ? <DeferredPlanEncounter key={`${context.worldId}:${context.documentId}:${context.sceneId}`} context={context}/> : <p>Choose a Plan scene to prepare its encounter.</p> : surfaceId==='play' ? context && 'runId' in context ? <DeferredRunEncounter key={`${context.worldId}:${context.runId}:${context.sceneId}`} context={context}/> : <p>Choose a session scene to open its encounter.</p> : <DeferredCombat/>;
}
export function useCombatProjection(surfaceId:string,enabled:boolean,context?:Context){
  const {registerProjectionCatalog}=useAgentInteraction();
  const store=useMemo(()=>createContextStore(context),[surfaceId]);
  useLayoutEffect(()=>{store.set(context);},[store,context]);
  useEffect(()=>{
    if(!enabled)return;
    return registerProjectionCatalog({projectionId:COMBAT_TOOL_ID,surfaceId,kind:'tool',preferredSize:'wide',requiredBindingIds:[],render:()=> <CombatProjectionContent store={store} surfaceId={surfaceId}/>});
  },[registerProjectionCatalog,surfaceId,enabled,store]);
}
