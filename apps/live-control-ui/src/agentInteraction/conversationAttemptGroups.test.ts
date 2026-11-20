import {it,expect} from 'vitest';
import type {WorldAgentConversationHistoryTurn} from '../api/types';
import {groupConversationAttempts} from './conversationAttemptGroups';
type Item={turn:WorldAgentConversationHistoryTurn}|{proposal:true};
const row=(n:number,root?:string,ordinal=0,successor:string|null=null):Item=>({turn:{turn_id:`turn-${n}`,sequence:n,lifecycle_status:'interrupted',user_text:'Same question',assistant_text:null,provenance:{world_id:'world',surface_id:'build',primary_work:{object_id:'page'}},
 ...(root?{retry_context:{world_id:'world',conversation_id:'conversation',turn_id:`turn-${n}`,revision:4,root_id:root,ordinal,predecessor_id:ordinal?'prior':null,successor_id:successor,eligible:!successor,reason:successor?'retried':'ready'}}:{}),} as WorldAgentConversationHistoryTurn});
const project=(rows:Item[])=>groupConversationAttempts(rows,x=>'turn' in x?x.turn:null,new Set([1]));
it('keeps equal independent questions separate',()=>{expect(project([row(1),row(2)])).toHaveLength(2);});
it('groups explicit lineage through proposal events and gaps without mutating rows',()=>{
 const rows=[row(1,'turn-1',0,'turn-8'),{proposal:true} as Item,row(8,'turn-1',1)],snapshot=JSON.stringify(rows);
 expect(project(rows)).toEqual([{item:rows[2],previous:[rows[0]],historical:false},{item:rows[1],previous:[]}]);expect(JSON.stringify(rows)).toBe(snapshot);
});
it('marks an ancestor historical when its successor is outside the page',()=>{expect(project([row(1,'turn-1',0,'turn-8')])[0].historical).toBe(true);});
it('keeps another root separate',()=>{expect(project([row(1,'turn-1',0,'turn-2'),row(2,'turn-1',1),row(3,'turn-3')])).toHaveLength(2);});
