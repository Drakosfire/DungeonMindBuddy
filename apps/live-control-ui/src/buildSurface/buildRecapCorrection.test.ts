import {expect,it} from 'vitest';
import {assertRecapQuoteChild,recapQuoteReviewBasis} from './buildRecapCorrection';
import {recapRun,recapReview,quoteReceipt} from './buildRecapCorrection.testSupport';
function parent(){const p=structuredClone(recapRun);p.run_id='parent-run';p.components!.candidate_graph.sha256=quoteReceipt.parentCandidateSha256;return p;}
it('joins current exact Recap child to immutable source/index and held semantic basis',()=>{
  expect(()=>assertRecapQuoteChild(parent(),quoteReceipt,recapRun)).not.toThrow();
  expect(recapQuoteReviewBasis(recapRun,recapReview)).toMatchObject({revision:3,state:'held'});
});
it.each(['source','index','session','world','basis','derivation','state'] as const)('refuses foreign corrected child %s',field=>{
  const child=structuredClone(recapRun);
  if(field==='source')child.components!.source_artifact.uri='different.md';
  if(field==='index')child.components!.source_span_index.sha256='f'.repeat(64);
  if(field==='session')child.session_id='session-31';
  if(field==='world')(child.lineage!.world_campaign_ingest_context as Record<string,unknown>).managed_world_id='other';
  if(field==='basis')(child.lineage!.semantic_disposition as Record<string,unknown>).basis_sha256='e'.repeat(64);
  if(field==='state')(child.lineage!.semantic_disposition as Record<string,unknown>).state='unknown';
  if(field==='derivation')child.lineage!.derivation='other';
  expect(()=>assertRecapQuoteChild(parent(),quoteReceipt,child)).toThrow('corrected Recap child');
});
