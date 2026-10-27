import {sessionSummaryMarkdown} from "../../shared/sessionEvidenceCitation";
import {SourceCitationEvidence} from './SourceCitationEvidence';
import {passageChoices,nativeChoices} from './sourceCitationReads';
import {canonical} from '../../shared/sourcePassageProtocol';
import type {SurfaceEvidenceCompletion} from "../../api/types";
import {WorldPlanAgentAnswer} from "./WorldPlanAgentAnswer";


type Composition = {text:string;ranges:{domain:string;base_segment_index:number|null;text_start:number;text_end:number}[]};
/** Same visible authority and exact passage selector in Plan, Play and Rules compositions. */
export function SurfaceEvidenceAnswer({completion,composition,worldId,turnId}:{
  completion:SurfaceEvidenceCompletion;composition?:Composition;worldId?:string|null;turnId?:string;
}) {
  // Number visible citations across this answer, independent of transport indexes.
  let nextNumber=0;
  const summaries=new Map<number,ReturnType<typeof sessionSummaryMarkdown>>();
  const choicesBySegment=completion.answer_segments.map((segment,index)=>{
    if(segment.kind==='session_summary' && worldId){
      const summary=sessionSummaryMarkdown(segment,worldId,nextNumber+1);summaries.set(index,summary);nextNumber=summary.nextNumber-1;
      return [];
    }
    return worldId && turnId ? [...passageChoices(completion,worldId,turnId,index),...('native_source_citations' in completion
      ? nativeChoices(completion,worldId,turnId,index):[])].map(c=>({...c,number:++nextNumber})) : [];
  });
  const renderSegment=(s:SurfaceEvidenceCompletion['answer_segments'][number],index:number,key:number) => {
    if(s.kind==='session_summary') {
      const summary=summaries.get(index);
      return <section key={key} aria-label="Saved session summary"><WorldPlanAgentAnswer answer={summary?.text??s.text} allowedInternalLinks={summary?.targets??[]}/></section>;
    }
    if(s.kind === 'authored_quote' || s.kind === 'authored_excerpt') {
      const sessionUrl=s.source_kind === 'session' && worldId
        ? `/play?${new URLSearchParams({world:worldId,run:s.object_id,evidence_revision:s.revision})}` : null;
      return <figure key={key}><figcaption>{sessionUrl
        ? <a href={sessionUrl}>{s.source_name}</a> : s.source_name} · quoted excerpt</figcaption>
        <blockquote><WorldPlanAgentAnswer answer={s.text}/></blockquote></figure>;
    }
    const graph=s.kind === 'graph_claim', source=s.kind === 'source_passage_claim';
    const selected=completion.source_citations.filter(c=>c.segment_index === index);
    return <section key={key} aria-label={graph ? 'World Graph fact' : source ? 'Source-supported statement' : s.kind === 'proposal' ? 'Proposed idea' : 'Evidence limitation'}>
      {graph ? <small>{selected.length ? 'World Graph' : 'World Graph · source passage not opened'}</small> : null}
      {s.kind === 'proposal' ? <small>Proposed idea</small> : null}
      {choicesBySegment[index]!.length ? <SourceCitationEvidence identity={canonical([completion,worldId,turnId,index])}
        statements={[{text:s.text,choices:choicesBySegment[index]!}]}/> : <WorldPlanAgentAnswer answer={s.text}/>}
      {!worldId || !turnId ? <>{selected.map((c,i)=><cite key={i}>{c.source_name}</cite>)}
        {'native_source_citations' in completion ? completion.native_source_citations.filter(c=>c.segment_index===index)
          .map((c,i)=><cite key={`native-${i}`}>{c.source_name} · {c.section_title}</cite>):null}</>:null}
    </section>;
  };
  const chars=composition ? Array.from(composition.text) : [];
  return <div aria-label="Evidence-grounded answer">{composition ? composition.ranges.map((r,i)=>
    r.domain === 'base' && r.base_segment_index !== null
      ? renderSegment(completion.answer_segments[r.base_segment_index]!,r.base_segment_index,i)
      : <section key={i} aria-label="Rules statement"><WorldPlanAgentAnswer answer={chars.slice(r.text_start,r.text_end).join('')}/></section>)
    : completion.answer_segments.map((s,i)=>renderSegment(s,i,i))}</div>;
}
