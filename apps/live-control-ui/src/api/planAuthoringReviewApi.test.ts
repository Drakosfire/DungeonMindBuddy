import {afterEach,expect,it,vi} from 'vitest';
import {createHash,webcrypto} from 'node:crypto';
import {canonical} from '../shared/sourcePassageProtocol';
const action='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const origin='b'.repeat(64),commandId='cccccccc-cccc-4ccc-8ccc-cccccccccccc';
function review(){return {schema:'dmb_plan_authoring_review_v1',world_id:'world-a',action_id:action,
  origin_sha256:origin,revision:1,state:'editing',markdown:'Proposed work',markdown_sha256:'d'.repeat(64),
  capture:{world_id:'world-a'},applications:[],last_command_id:commandId,last_command_sha256:'e'.repeat(64),updated_at:'2026-10-26T00:00:00Z'};}
async function modules(base=''){
  vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();
  const live=await import('./liveApi');live.setNativeGraphAccessToken('synthetic-plan-review-token');
  return {live,api:await import('./planAuthoringReviewApi')};
}
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
it('reads the exact proposal origin without opening or editing its review',async()=>{
  const {api}=await modules();
  const snapshot={schema:'dmb_plan_authoring_review_snapshot_v1',world_id:'world-a',action_id:action,origin_sha256:origin,review:null};
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(snapshot));
  expect(await api.readPlanAuthoringReview('world-a',action)).toEqual(snapshot);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][1]).toMatchObject({cache:'no-store',redirect:'error',credentials:'same-origin'});
  expect(fetch.mock.calls[0][1]?.body).toBeUndefined();
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-plan-review-token');
});
it('sends the caller-retained command once and verifies its acknowledgment',async()=>{
  const {api}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(review()));
  const command={operation:'open' as const,command_id:commandId,origin_sha256:origin,expected_revision:0};
  expect((await api.commandPlanAuthoringReview('world-a',action,command)).last_command_id).toBe(commandId);
  expect(fetch).toHaveBeenCalledTimes(1);expect(JSON.parse(fetch.mock.calls[0][1]?.body as string)).toEqual(command);
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-plan-review-token');
});
it.each(['world','origin','action','command'])('refuses a mismatched %s reply',async(field)=>{
  const {api}=await modules();const bad=review();
  if(field==='world')bad.world_id='other';if(field==='origin')bad.origin_sha256='0'.repeat(64);
  if(field==='action')bad.action_id='dddddddd-dddd-4ddd-8ddd-dddddddddddd';if(field==='command')bad.last_command_id='other';
  vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(bad));
  await expect(api.commandPlanAuthoringReview('world-a',action,{operation:'open',command_id:commandId,origin_sha256:origin,expected_revision:0})).rejects.toThrow();
});
it('refuses conflicts without automatically retrying',async()=>{
  const {api}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}, {status:409}));
  await expect(api.commandPlanAuthoringReview('world-a',action,{operation:'discard',command_id:commandId,origin_sha256:origin,expected_revision:4})).rejects.toThrow(/local copy is retained/);
  expect(fetch).toHaveBeenCalledTimes(1);
});
it('refuses a remote destination before transmitting credentials or working copies',async()=>{
  const {api}=await modules('https://outside.invalid');const fetch=vi.spyOn(globalThis,'fetch');
  await expect(api.commandPlanAuthoringReview('world-a',action,{operation:'save',command_id:commandId,origin_sha256:origin,expected_revision:1,markdown:'Private author draft'})).rejects.toThrow(/loopback/);
  expect(fetch).not.toHaveBeenCalled();
});
it('does not attach credentials to near-miss review paths',async()=>{
  const {live}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
  for(const suffix of ['review-extra','review/extra'])await live.authenticatedApiFetch(`/api/live/agent/worlds/world-a/plan-proposals/${action}/${suffix}`);
  await live.authenticatedApiFetch('/api/live/agent/worlds/world-a/plan-proposals/not-a-uuid/review');
  for(const call of fetch.mock.calls){expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false);expect(new Headers(call[1]?.headers).has('X-DMB-Graph-CSRF')).toBe(false);}
});


function authoredFixture(){
  const hash=(value:string)=>createHash('sha256').update(value).digest('hex');
  const capture={schema:'dmb_plan_authoring_capture_v1',idempotency_key:commandId,conversation_id:action,expected_pointer_revision:1,
    world_id:'world-a',document_id:'plan-a',base_revision:7,base_content_sha256:'f'.repeat(64),draft_markdown:'Original.\n',
    editor_json:JSON.stringify({type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'Original.'}]}]}),
    selection_json:JSON.stringify({type:'text',anchor:1,head:1}),from:1,to:1,draft_generation:2,selection_generation:3,
    target_kind:'insert_at_caret',selected_text:'',playable_target:null,draft_sha256:'',editor_sha256:'',selection_sha256:''};
  capture.draft_sha256=hash(capture.draft_markdown);capture.editor_sha256=hash(capture.editor_json);capture.selection_sha256=hash(capture.selection_json);
  const replacement='A possible visitor.\n';
  return {schema:'dmb_plan_authored_proposal_v1',capture,replacement_markdown:replacement,origin:{schema:'dmb_plan_jev_proposal_origin_v1',
    action_id:action,idempotency_key:commandId,action_request_fingerprint:'a'.repeat(64),action_fence:1,
    basis:{world_id:'world-a',document_id:'plan-a',object_revision:7,work_revision_id:commandId,revision_n:4,content_sha256:'f'.repeat(64)},
    conversation_id:action,turn_id:commandId,product_attempt:1,expected_pointer_revision:1,context_receipt_sha256:'b'.repeat(64),
    execution_policy_sha256:'c'.repeat(64),capture_sha256:hash(canonical(capture)),controller_attempt_id:action,selection_event_id:commandId,
    expected_turn_revision:2,writer_attempt_id:action,writer_envelope_sha256:'d'.repeat(64),raw_reply_sha256:'e'.repeat(64),
    evidence_event_ids:[],replacement_markdown_sha256:hash(replacement)}};
}
it('admits the complete generated Plan object only with exact captured and generated bytes',async()=>{
  const {api}=await modules();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
  const proposal=authoredFixture();expect(api.isPlanAuthoredProposal(proposal)).toBe(true);
  expect(await api.planProposalDigestsBound(proposal)).toBe(true);
  expect(await api.planProposalDigestsBound({...proposal,replacement_markdown:'Different generated work.'})).toBe(false);
  const changed=structuredClone(proposal);changed.capture.draft_markdown='Newer author draft.';
  expect(await api.planProposalDigestsBound(changed)).toBe(false);
});
it.each(['world','document','conversation','basis','range','unknown'])('refuses spliced %s authoring authority',async field=>{
  const {api}=await modules();const p=authoredFixture();
  if(field==='world')p.capture.world_id='other';if(field==='document')p.capture.document_id='other';
  if(field==='conversation')p.capture.conversation_id=commandId;if(field==='basis')p.origin.basis.object_revision=8;
  if(field==='range'){p.capture.from=2;p.capture.to=2;}
  if(field==='unknown')Object.assign(p.capture,{unrecognized_authority:true});
  expect(api.isPlanAuthoredProposal(p)).toBe(false);
});
it('exposes definite refusal status without retrying the retained command',async()=>{
  const {api}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}, {status:422}));
  await expect(api.commandPlanAuthoringReview('world-a',action,{operation:'open',command_id:commandId,origin_sha256:origin,expected_revision:0}))
    .rejects.toMatchObject({name:'PlanReviewRequestError',status:422});
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('admits structural capture with its original selection witness and exact resolved target digest',async()=>{
  const {api}=await modules();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
  const base=authoredFixture();
  const capture={...base.capture,schema:'dmb_plan_authoring_boundary_capture_v1',target_kind:'insert_at_boundary',
    root_boundary:1,from:11,to:11};
  const proposal={...base,capture,origin:{...base.origin,capture_sha256:createHash('sha256').update(canonical(capture)).digest('hex')}};
  expect(api.isPlanAuthoredProposal(proposal)).toBe(true);
  expect(await api.planProposalDigestsBound(proposal)).toBe(true);
  expect(api.isPlanAuthoredProposal({...proposal,capture:{...capture,root_boundary:-1}})).toBe(false);
  expect(api.isPlanAuthoredProposal({...proposal,capture:{...capture,to:12}})).toBe(false);
  expect(await api.planProposalDigestsBound({...proposal,capture:{...capture,root_boundary:0}})).toBe(false);
});
