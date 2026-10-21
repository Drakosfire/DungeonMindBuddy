import {expect,it} from 'vitest';
import {exactRunCorrectionDigest} from './exactRunCorrectionIdentity';
it('matches the native canonical correction request digest',async()=>{
  const request={"parentRunId": "run-a", "parentCandidateSha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "corrections": [{"assertionId": "keeper", "evidenceIndex": 0, "quoteIndex": 0, "originalQuote": "bad quote", "replacementQuote": "keeper", "sourceSpanRefId": "span-a"}]};
  expect(await exactRunCorrectionDigest(request)).toBe('8c058401bfe60336bc9533bad544f8f021689872fd55ebecf0c01cbc19b19d35');
  expect(await exactRunCorrectionDigest({...request,corrections:[{...request.corrections[0],replacementQuote:'other'}]})).not.toBe('8c058401bfe60336bc9533bad544f8f021689872fd55ebecf0c01cbc19b19d35');
});
