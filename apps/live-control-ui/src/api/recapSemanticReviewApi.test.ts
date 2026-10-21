import {afterEach,expect,it,vi} from 'vitest';
import * as live from './liveApi';
import {decideRecapSemantics,type RecapSemanticDecisionRequest} from './recapSemanticReviewApi';
import {decisionReceipt,basisHash} from '../buildSurface/buildRecapCorrection.testSupport';
const request:RecapSemanticDecisionRequest={schema:'dmb_recap_semantic_decision_request_v1',expectedRevision:3,
  candidateSha256:decisionReceipt.candidateSha256,decision:'accepted',reviewDecisionRef:decisionReceipt.reviewDecisionRef};
afterEach(()=>vi.restoreAllMocks());
it('posts only the current explicit decision contract through authenticated API',async()=>{
  const fetch=vi.spyOn(live,'authenticatedApiFetch').mockResolvedValue({response:new Response(JSON.stringify(decisionReceipt),{status:200})} as any);
  expect(await decideRecapSemantics('child-run',request,basisHash)).toEqual(decisionReceipt);
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/api/live/extract-promote/runs/child-run/semantic-disposition',
    {method:'POST',body:JSON.stringify(request)});
  expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).not.toHaveProperty('reviewerId');
});
it.each(['runId','candidateSha256','basisSha256','revision','reviewDecisionRef','state','reviewerId','decidedAt'])(
  'refuses foreign decision receipt %s',async field=>{
    const value={...decisionReceipt,[field]:field==='revision'?20:field==='reviewerId'?'':'foreign'};
    vi.spyOn(live,'authenticatedApiFetch').mockResolvedValue({response:new Response(JSON.stringify(value),{status:200})} as any);
    await expect(decideRecapSemantics('child-run',request,basisHash)).rejects.toThrow('receipt');
  });
it('retains typed conflict status without retrying the semantic write',async()=>{
  const fetch=vi.spyOn(live,'authenticatedApiFetch').mockResolvedValue({response:new Response(JSON.stringify({code:'recap_semantic_decision_conflict',message:'Decision changed'}),{status:409})} as any);
  await expect(decideRecapSemantics('child-run',request,basisHash)).rejects.toMatchObject({code:'recap_semantic_decision_conflict',status:409});
  expect(fetch).toHaveBeenCalledOnce();
});
