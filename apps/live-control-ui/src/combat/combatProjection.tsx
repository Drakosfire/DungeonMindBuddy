import {useEffect} from 'react';
import {useAgentInteraction} from '../agentInteraction/useAgentInteraction';
import type {SurfaceInteractionToolContribution, SurfaceInteractionProjectionDescriptor} from '../surfaceInteraction/types';
import {deferredComponent} from '../ui/deferredComponent';
export const COMBAT_TOOL_ID='combat';
export const COMBAT_TOOL:SurfaceInteractionToolContribution={id:COMBAT_TOOL_ID,label:'Combat',
  placement:{groupId:'table',groupLabel:'At the table',groupOrder:20,itemOrder:0},
  availability:{status:'enabled'},activation:{kind:'projection',projectionId:COMBAT_TOOL_ID}};
export const COMBAT_PROJECTION:SurfaceInteractionProjectionDescriptor={id:COMBAT_TOOL_ID,kind:'tool',preferredSize:'wide',bindingIds:[]};
const DeferredCombat=deferredComponent(()=>import('../surface/modules/CombatRosterModule').then(module=>({default:module.CombatRosterModule})),'Combat');
export function useCombatProjection(surfaceId:string,enabled:boolean){
  const {registerProjectionCatalog}=useAgentInteraction();
  useEffect(()=>{
    if(!enabled)return;
    return registerProjectionCatalog({projectionId:COMBAT_TOOL_ID,surfaceId,kind:'tool',preferredSize:'wide',requiredBindingIds:[],render:()=> <DeferredCombat/>});
  },[registerProjectionCatalog,surfaceId,enabled]);
}
