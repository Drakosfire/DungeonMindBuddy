import {it,expect} from 'vitest';
import {decodeRetryContext} from './conversationRetryApi';
const cid='10000000-0000-4000-8000-000000000001',id='20000000-0000-4000-8000-000000000001';
const context=()=>({world_id:'world',conversation_id:cid,turn_id:id,revision:3,root_id:id,predecessor_id:null,successor_id:null,ordinal:0,eligible:true,reason:'ready'});
it('admits exact root context',()=>{expect(decodeRetryContext(context(),'world',cid,id)).toEqual(context());});
it.each([{world_id:'foreign'},{conversation_id:id},{turn_id:cid},{root_id:cid},{revision:0},{ordinal:1},{predecessor_id:id},{successor_id:id},{eligible:false},{reason:'not_terminal'},{extra:true}])('rejects changed owner/inconsistent lineage %j',change=>{expect(()=>decodeRetryContext({...context(),...change},'world',cid,id)).toThrow();});

const refs={schema:'dmb_authored_graph_references_v1' as const,references:[{schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:'world',native_world_id:'native',binding_version:1,graph_revision:'rev-a',node_id:'box',label:'Cedar box'}]};
it('retains the exact V2 retry snapshot separately from current composer selections',()=>{
 const saved={...context(),schema:'dmb_turn_retry_context_row_v2',authored_references:refs};expect(decodeRetryContext(saved,'world',cid,id)).toEqual(saved);
});
it.each(['foreign','missing','unknown'])('refuses a %s V2 retry reference snapshot',kind=>{
 const saved={...context(),schema:'dmb_turn_retry_context_row_v2',authored_references:kind==='missing'?null:kind==='unknown'?{...refs,extra:true}:{...refs,references:[{...refs.references[0],managed_world_id:'foreign'}]}};
 expect(()=>decodeRetryContext(saved,'world',cid,id)).toThrow();
});
