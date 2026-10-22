import type { ExactRunEvidenceQuoteCorrection } from "./types";

// Match exact_run_evidence_correction._canonical_bytes and its sorted target list.
export async function exactRunCorrectionDigest(request: {parentRunId: string; parentCandidateSha256: string; corrections: ExactRunEvidenceQuoteCorrection[]}): Promise<string> {
  const compareIds = (a: string, b: string) => {
    const left = Array.from(a, c => c.codePointAt(0)!), right = Array.from(b, c => c.codePointAt(0)!);
    for (let i = 0; i < Math.min(left.length, right.length); i++) if (left[i] !== right[i]) return left[i] - right[i];
    return left.length - right.length;
  };
  const corrections = [...request.corrections].sort((a, b) => compareIds(a.assertionId, b.assertionId)
    || a.evidenceIndex - b.evidenceIndex || a.quoteIndex - b.quoteIndex).map(item => ({
      assertionId: item.assertionId, evidenceIndex: item.evidenceIndex, originalQuote: item.originalQuote,
      quoteIndex: item.quoteIndex, replacementQuote: item.replacementQuote, sourceSpanRefId: item.sourceSpanRefId,
    }));
  const canonical = JSON.stringify({ corrections, parentCandidateSha256: request.parentCandidateSha256, parentRunId: request.parentRunId }) + "\n";
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}


export async function worldbuildingEvidenceCorrectionDigest(request: import('./types').WorldbuildingEvidenceCorrectionRequest): Promise<string> {
  const compare = (a: string, b: string) => {
    const x=Array.from(a,c=>c.codePointAt(0)!), y=Array.from(b,c=>c.codePointAt(0)!);
    for(let i=0;i<Math.min(x.length,y.length);i++) if(x[i]!==y[i]) return x[i]-y[i];
    return x.length-y.length;
  };
  const sorted = {...request, corrections:[...request.corrections].sort((a,b)=>compare(a.assertionId,b.assertionId)||a.evidenceIndex-b.evidenceIndex)};
  function canonical(value: unknown): unknown {
    if(Array.isArray(value))return value.map(canonical);
    if(value!==null&&typeof value==='object')return Object.fromEntries(Object.entries(value).sort(([a],[b])=>compare(a,b)).map(([k,v])=>[k,canonical(v)]));
    return value;
  }
  const bytes=new TextEncoder().encode(JSON.stringify(canonical(sorted))+"\n");
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
}
