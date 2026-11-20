import {useEffect} from 'react';
import {useAgentInteraction} from '../agentInteraction/useAgentInteraction';
import type {SurfaceInteractionToolContribution,SurfaceInteractionProjectionDescriptor} from '../surfaceInteraction/types';
import {deferredComponent} from '../ui/deferredComponent';
import type {WorldPlayRunRecordV2} from '../api/types';

export type PreparedTablesBinding={run:WorldPlayRunRecordV2;blocked:boolean;onHeld:(held:boolean)=>void;onRun:(run:WorldPlayRunRecordV2)=>void};
export const TABLE_BINDING_ID='prepared-tables-run';
export const TABLE_TOOL:SurfaceInteractionToolContribution={id:'prepared-tables',label:'Prepared tables',
  placement:{groupId:'table',groupLabel:'At the table',groupOrder:20,itemOrder:10},
  availability:{status:'enabled'},activation:{kind:'projection',projectionId:'prepared-tables'}};
export const TABLE_PROJECTION:SurfaceInteractionProjectionDescriptor={id:'prepared-tables',kind:'tool',preferredSize:'wide',bindingIds:[TABLE_BINDING_ID]};
const DeferredTables=deferredComponent(()=>import('./PreparedTablesTool').then(module=>({default:module.PreparedTablesTool})),'Prepared tables');
export function usePreparedTablesProjection(){
  const {registerProjectionCatalog}=useAgentInteraction();
  useEffect(()=>registerProjectionCatalog({projectionId:TABLE_TOOL.id,surfaceId:'play',kind:'tool',preferredSize:'wide',requiredBindingIds:[TABLE_BINDING_ID],render:({bindings})=>{
    const binding=bindings[TABLE_BINDING_ID] as PreparedTablesBinding;
    return <DeferredTables key={JSON.stringify([binding.run.world_id,binding.run.run_id])} {...binding}/>;
  }}),[registerProjectionCatalog]);
}
export const pendingTableKey=(world:string,run:string)=>`dmb.prepared-table-command.${JSON.stringify([world,run])}`;
