import {expect,it} from 'vitest';
import {exactRunCorrectionDigest} from './exactRunCorrectionIdentity';
it('matches the native canonical correction request digest',async()=>{
  const request={"parentRunId": "run-a", "parentCandidateSha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "corrections": [{"assertionId": "keeper", "evidenceIndex": 0, "quoteIndex": 0, "originalQuote": "bad quote", "replacementQuote": "keeper", "sourceSpanRefId": "span-a"}]};
  expect(await exactRunCorrectionDigest(request)).toBe('8c058401bfe60336bc9533bad544f8f021689872fd55ebecf0c01cbc19b19d35');
  expect(await exactRunCorrectionDigest({...request,corrections:[{...request.corrections[0],replacementQuote:'other'}]})).not.toBe('8c058401bfe60336bc9533bad544f8f021689872fd55ebecf0c01cbc19b19d35');
});

it('binds the complete frozen partition request to the native canonical digest',async()=>{
  const {worldbuildingEvidenceCorrectionDigest}=await import('./exactRunCorrectionIdentity');
  const q={"schema":"dmb_worldbuilding_evidence_correction_request_v2","parentRunId":"run","expectedParentRevision":7,"expectedParentStatus":"reviewable","worldId":"world","sourceArtifactId":"source","sourceSha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","spanIndexSha256":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","parentCandidateSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","corrections":[{"assertionId":"keepers","evidenceIndex":0,"expectedRefSha256":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","parts":[{"sourceSpanRefId":"road","quoteAssignments":[{"originalQuoteIndex":0,"replacementQuote":"Mara repairs the road."}]}]}]} as import('./types').WorldbuildingEvidenceCorrectionRequest;
  expect(await worldbuildingEvidenceCorrectionDigest(q)).toBe('88b620d32b51d6982bb44828472633a930cc9256fa3aca92640d02852f95b285');
  expect(await worldbuildingEvidenceCorrectionDigest({...q,expectedParentRevision:8})).not.toBe('88b620d32b51d6982bb44828472633a930cc9256fa3aca92640d02852f95b285');
});
