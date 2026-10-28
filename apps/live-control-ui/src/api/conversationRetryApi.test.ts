import {beforeEach,expect,it,vi} from 'vitest';
import {decodeRetryContext} from './conversationRetryApi';
import {webcrypto} from 'node:crypto';
import {readDiscussionRetryInput} from './conversationRetryApi';
import {authenticatedApiFetch} from './liveApi';
import {canonical} from '../shared/sourcePassageProtocol';
vi.mock('./liveApi',async original=>({...await original<typeof import('./liveApi')>(),authenticatedApiFetch:vi.fn()}));
const cid='11111111-1111-4111-8111-111111111111',tid='22222222-2222-4222-8222-222222222222';
const hash=async(text:string)=>Buffer.from(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode(text))).toString('hex');
async function body(){const snapshot={schema:'dmb_build_draft_snapshot_v1',world_id:'world',document_id:'original-page',registry_revision:2,content_sha256:'a'.repeat(64),visibility:'internal',draft_markdown:'Original unsaved café draft',draft_sha256:await hash('Original unsaved café draft'),editor_sha256:'b'.repeat(64),draft_generation:3};return {schema:'dmb_build_retained_discussion_retry_input_v1',world_id:'world',conversation_id:cid,turn_id:tid,revision:4,pointer_revision:1,surface_instance_id:'original-editor',message:'Who runs the shop?',snapshot,snapshot_sha256:await hash(canonical(snapshot)),authored_references:null};}
function response(value:unknown){vi.mocked(authenticatedApiFetch).mockResolvedValue({response:Response.json(value)} as Awaited<ReturnType<typeof authenticatedApiFetch>>);}
beforeEach(()=>{vi.clearAllMocks();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});});
it('reads and verifies original retained Unicode draft without write authority',async()=>{const value=await body();response(value);expect(await readDiscussionRetryInput('world',cid,tid,4)).toEqual(value);expect(vi.mocked(authenticatedApiFetch).mock.calls[0][1]).toEqual({cache:'no-store'});});
it.each(['world','conversation','turn','revision','snapshot','draft','extra','write'])('refuses mismatched retained context: %s',async change=>{const value:any=await body();if(change==='world')value.world_id='foreign';if(change==='conversation')value.conversation_id=tid;if(change==='turn')value.turn_id=cid;if(change==='revision')value.revision=5;if(change==='snapshot')value.snapshot.editor_sha256='f'.repeat(64);if(change==='draft')value.snapshot.draft_markdown='Changed';if(change==='extra')value.execute=true;if(change==='write')value.build_write_capability={};response(value);await expect(readDiscussionRetryInput('world',cid,tid,4)).rejects.toThrow();});

const lineageCid='10000000-0000-4000-8000-000000000001',id='20000000-0000-4000-8000-000000000001';
const context=()=>({world_id:'world',conversation_id:lineageCid,turn_id:id,revision:3,root_id:id,predecessor_id:null,successor_id:null,ordinal:0,eligible:true,reason:'ready'});
it('admits exact root context',()=>{expect(decodeRetryContext(context(),'world',lineageCid,id)).toEqual(context());});
it.each([{world_id:'foreign'},{conversation_id:id},{turn_id:lineageCid},{root_id:lineageCid},{revision:0},{ordinal:1},{predecessor_id:id},{successor_id:id},{eligible:false},{reason:'not_terminal'},{extra:true}])('rejects changed owner/inconsistent lineage %j',change=>{expect(()=>decodeRetryContext({...context(),...change},'world',lineageCid,id)).toThrow();});

const refs={schema:'dmb_authored_graph_references_v1' as const,references:[{schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:'world',native_world_id:'native',binding_version:1,graph_revision:'rev-a',node_id:'box',label:'Cedar box'}]};
it('retains the exact V2 retry snapshot separately from current composer selections',()=>{
 const saved={...context(),schema:'dmb_turn_retry_context_row_v2',authored_references:refs};expect(decodeRetryContext(saved,'world',lineageCid,id)).toEqual(saved);
});
it.each(['foreign','missing','unknown'])('refuses a %s V2 retry reference snapshot',kind=>{
 const saved={...context(),schema:'dmb_turn_retry_context_row_v2',authored_references:kind==='missing'?null:kind==='unknown'?{...refs,extra:true}:{...refs,references:[{...refs.references[0],managed_world_id:'foreign'}]}};
 expect(()=>decodeRetryContext(saved,'world',lineageCid,id)).toThrow();
});
