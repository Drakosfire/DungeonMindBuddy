import {it,expect} from 'vitest';
import {decodeRetryContext} from './conversationRetryApi';
const cid='10000000-0000-4000-8000-000000000001',id='20000000-0000-4000-8000-000000000001';
const context=()=>({world_id:'world',conversation_id:cid,turn_id:id,revision:3,root_id:id,predecessor_id:null,successor_id:null,ordinal:0,eligible:true,reason:'ready'});
it('admits exact root context',()=>{expect(decodeRetryContext(context(),'world',cid,id)).toEqual(context());});
it.each([{world_id:'foreign'},{conversation_id:id},{turn_id:cid},{root_id:cid},{revision:0},{ordinal:1},{predecessor_id:id},{successor_id:id},{eligible:false},{reason:'not_terminal'},{extra:true}])('rejects changed owner/inconsistent lineage %j',change=>{expect(()=>decodeRetryContext({...context(),...change},'world',cid,id)).toThrow();});
