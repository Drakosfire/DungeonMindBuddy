import {useState} from 'react';
import type {ExactRunReviewPackage, ExtractionRunRecord, WorldbuildingFrozenSpanCatalog,
  WorldbuildingEvidenceCorrectionRequest} from '../api/types';

export function validFrozenCatalog(c:WorldbuildingFrozenSpanCatalog,r:ExactRunReviewPackage,run:ExtractionRunRecord,worldId:string) {
  const hex=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
  return !!c&&c.schema==='dmb_worldbuilding_frozen_span_catalog_v1'&&c.parentRunId===run.run_id
    &&c.parentRevision===(run as ExtractionRunRecord & {revision?:unknown}).revision&&c.parentStatus==='reviewable'&&run.status==='reviewable'
    &&c.worldId===worldId&&c.sourceArtifactId===r.sourceArtifactId&&c.sourceArtifactId===run.source_artifact_id
    &&c.parentCandidateSha256===run.components?.candidate_graph?.sha256?.replace(/^sha256:/,'')
    &&c.sourceSha256===r.sourceRevisionId.replace(/^sha256:/,'')&&hex(c.spanIndexSha256)
    &&c.spanIndexSha256===run.components?.source_span_index?.sha256?.replace(/^sha256:/,'')
    &&Array.isArray(c.spans)&&c.spans.length>0&&new Set(c.spans.map(s=>s.sourceSpanRefId)).size===c.spans.length
    &&c.spans.every(s=>typeof s.sourceSpanRefId==='string'&&s.sourceSpanRefId.length>0&&typeof s.paragraphText==='string'
      &&Number.isSafeInteger(s.startLine)&&Number.isSafeInteger(s.endLine)&&s.startLine>=1&&s.endLine>=s.startLine)
    &&Array.isArray(c.evidenceRefs)&&new Set(c.evidenceRefs.map(e=>JSON.stringify([e.assertionId,e.evidenceIndex]))).size===c.evidenceRefs.length
    &&c.evidenceRefs.every(e=>hex(e.refSha256)&&Number.isSafeInteger(e.evidenceIndex)&&e.evidenceIndex>=0
      &&r.assertions.some(a=>a.assertionId===e.assertionId&&a.evidence[e.evidenceIndex]));
}

export function validWorldbuildingCorrection(value:unknown,c:WorldbuildingFrozenSpanCatalog|null,r:ExactRunReviewPackage): value is WorldbuildingEvidenceCorrectionRequest {
  if(!c||!value||typeof value!=='object')return false;
  const q=value as WorldbuildingEvidenceCorrectionRequest;
  if(q.schema!=='dmb_worldbuilding_evidence_correction_request_v2'||q.parentRunId!==c.parentRunId
    ||q.expectedParentRevision!==c.parentRevision||q.expectedParentStatus!==c.parentStatus||q.worldId!==c.worldId
    ||q.sourceArtifactId!==c.sourceArtifactId||q.sourceSha256!==c.sourceSha256||q.spanIndexSha256!==c.spanIndexSha256
    ||q.parentCandidateSha256!==c.parentCandidateSha256||!Array.isArray(q.corrections)||!q.corrections.length)return false;
  const seen=new Set<string>();
  return q.corrections.every(change=>{
    if(!change||typeof change.assertionId!=='string'||!Number.isSafeInteger(change.evidenceIndex)||change.evidenceIndex<0)return false;
    const key=JSON.stringify([change.assertionId,change.evidenceIndex]);
    const old=r.assertions.find(a=>a.assertionId===change.assertionId)?.evidence[change.evidenceIndex];
    const pre=c.evidenceRefs.find(e=>e.assertionId===change.assertionId&&e.evidenceIndex===change.evidenceIndex);
    if(seen.has(key)||!old||!pre||pre.refSha256!==change.expectedRefSha256||!Array.isArray(change.parts)||!change.parts.length)return false;
    seen.add(key);const indices=new Set<number>(),order:number[]=[];
    for(const part of change.parts){
      if(!part||!c.spans.some(s=>s.sourceSpanRefId===part.sourceSpanRefId)
        ||!Array.isArray(part.quoteAssignments)||!part.quoteAssignments.length)return false;
      for(const a of part.quoteAssignments){
        if(!a||!Number.isSafeInteger(a.originalQuoteIndex)||a.originalQuoteIndex<0||a.originalQuoteIndex>=old.anchorQuotes.length
          ||indices.has(a.originalQuoteIndex)||typeof a.replacementQuote!=='string'||!a.replacementQuote.trim()
          ||a.replacementQuote!==a.replacementQuote.trim())return false;
        indices.add(a.originalQuoteIndex);order.push(a.originalQuoteIndex);
      }
    }
    return indices.size===old.anchorQuotes.length&&order.every((value,index)=>value===index);
  });
}

type Props={review:ExactRunReviewPackage;catalog:WorldbuildingFrozenSpanCatalog;busy:boolean;
  recovery:WorldbuildingEvidenceCorrectionRequest|null;hasRecovery:boolean;error:string|null;
  onSubmit:(request:WorldbuildingEvidenceCorrectionRequest)=>void;onRetry:()=>void;onAbandon:()=>void};
export function WorldbuildingEvidenceCorrection({review,catalog,busy,recovery,hasRecovery,error,onSubmit,onRetry,onAbandon}:Props){
  const targets=review.assertions.flatMap(a=>a.evidence.flatMap((e,i)=>e.invalidAnchorQuotes?.length
    ?[{a,e,i,key:JSON.stringify([a.assertionId,i])}]:[]));
  const [choices,setChoices]=useState<Record<string,{span:string;quote:string}>>({});
  const [preview,setPreview]=useState(false);
  function choose(key:string,span:string,quote:string){setChoices(old=>({...old,[key]:{span,quote}}));setPreview(false);}
  const corrections=targets.map(t=>{
    const parts:{sourceSpanRefId:string;quoteAssignments:{originalQuoteIndex:number;replacementQuote:string}[]}[]=[];
    t.e.anchorQuotes.forEach((quote,j)=>{
      const pick=choices[JSON.stringify([t.key,j])]??{span:t.e.sourceSpanRefId,quote:t.e.invalidAnchorQuotes?.includes(quote)?'':quote};
      const assignment={originalQuoteIndex:j,replacementQuote:pick.quote.trim()};
      if(parts.at(-1)?.sourceSpanRefId===pick.span)parts[parts.length-1].quoteAssignments.push(assignment);
      else parts.push({sourceSpanRefId:pick.span,quoteAssignments:[assignment]});
    });
    return {assertionId:t.a.assertionId,evidenceIndex:t.i,expectedRefSha256:catalog.evidenceRefs.find(e=>e.assertionId===t.a.assertionId&&e.evidenceIndex===t.i)?.refSha256??'',
      parts};
  });
  const request:WorldbuildingEvidenceCorrectionRequest={schema:'dmb_worldbuilding_evidence_correction_request_v2',parentRunId:catalog.parentRunId,
    expectedParentRevision:catalog.parentRevision,expectedParentStatus:catalog.parentStatus,worldId:catalog.worldId,
    sourceArtifactId:catalog.sourceArtifactId,sourceSha256:catalog.sourceSha256,spanIndexSha256:catalog.spanIndexSha256,
    parentCandidateSha256:catalog.parentCandidateSha256,corrections};
  if(!targets.length)return null;
  return <section aria-label="Correct source evidence"><h3>Correct source evidence</h3>
    <p>Choose each quote’s paragraph from this extraction’s saved source. Every original quote stays represented. Corrections create a separate, unpublished candidate for review.</p>
    {targets.map(t=><fieldset key={t.key} disabled={busy||hasRecovery}><legend>{t.a.label}</legend>
      {t.e.anchorQuotes.map((quote,j)=>{
        const key=JSON.stringify([t.key,j]);const pick=choices[key]??{span:t.e.sourceSpanRefId,quote:t.e.invalidAnchorQuotes?.includes(quote)?'':quote};
        const selected=catalog.spans.find(s=>s.sourceSpanRefId===pick.span);
        return <div key={j}><p>Original quote {j+1}: “{quote}”</p>
          <label>Source paragraph<select aria-label={`Source paragraph for ${t.a.label} quote ${j+1}`} value={pick.span}
            onChange={e=>choose(key,e.target.value,pick.quote)}>{catalog.spans.map(s=><option key={s.sourceSpanRefId} value={s.sourceSpanRefId}>
              Lines {s.startLine}–{s.endLine}: {s.paragraphText.slice(0,100)}</option>)}</select></label>
          <details><summary>Read selected paragraph</summary><p>{selected?.paragraphText}</p></details>
          <label>Exact quote<input aria-label={`Literal replacement for ${t.a.label} quote ${j+1}`} value={pick.quote}
            onChange={e=>choose(key,pick.span,e.target.value)}/></label></div>;
      })}</fieldset>)}
    {error&&<p role="alert">{error}</p>}
    {hasRecovery?<section aria-label="Saved evidence correction recovery"><p>A correction request is retained. Retry it to recover its child; no new request will replace it.</p>
      {recovery&&<><ul>{recovery.corrections.map(change=><li key={JSON.stringify([change.assertionId,change.evidenceIndex])}>
        {review.assertions.find(a=>a.assertionId===change.assertionId)?.label}{change.parts.map((part,index)=><div key={index}>
          Lines {catalog.spans.find(s=>s.sourceSpanRefId===part.sourceSpanRefId)?.startLine}–{catalog.spans.find(s=>s.sourceSpanRefId===part.sourceSpanRefId)?.endLine}
          {part.quoteAssignments.map(a=><p key={a.originalQuoteIndex}>Quote {a.originalQuoteIndex+1}: “{a.replacementQuote}”</p>)}
        </div>)}</li>)}</ul>
      <button disabled={busy} onClick={onRetry}>Retry saved evidence corrections</button>
      <button disabled={busy} onClick={onAbandon}>Abandon saved request</button></>}</section>:<>
      {preview&&<section aria-label="Preview evidence corrections">{corrections.map((c,i)=><div key={i}><h4>{targets[i].a.label}</h4>{c.parts.map((part,index)=><div key={index}>
        <p>Lines {catalog.spans.find(s=>s.sourceSpanRefId===part.sourceSpanRefId)?.startLine}–{catalog.spans.find(s=>s.sourceSpanRefId===part.sourceSpanRefId)?.endLine}</p>
        {part.quoteAssignments.map(a=><p key={a.originalQuoteIndex}>Quote {a.originalQuoteIndex+1}: “{a.replacementQuote}”</p>)}</div>)}</div>)}</section>}
      <button disabled={busy||!validWorldbuildingCorrection(request,catalog,review)} onClick={()=>preview?onSubmit(request):setPreview(true)}>
        {busy?'Checking corrections…':preview?'Create reviewed child candidate':'Preview evidence corrections'}</button></>}
  </section>;
}
