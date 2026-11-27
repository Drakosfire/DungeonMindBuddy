import { useState } from 'react';
import {sessionSummaryMarkdown} from "../../shared/sessionEvidenceCitation";
import {SourceCitationEvidence} from './SourceCitationEvidence';
import {passageChoices,nativeChoices,nativeSavedChoices,nativeRecapChoices} from './sourceCitationReads';
import {canonical} from '../../shared/sourcePassageProtocol';
import type {SurfaceEvidenceCompletion,SurfaceNativeCompletionV1} from "../../api/types";
import {WorldPlanAgentAnswer} from "./WorldPlanAgentAnswer";


type Composition = {text:string;ranges:{domain:string;base_segment_index:number|null;text_start:number;text_end:number}[]};
/** Same visible authority and exact passage selector in Plan, Play and Rules compositions. */
export function SurfaceEvidenceAnswer({completion,composition,worldId,turnId,buildSourceBasis,nativeScope,citationsOnly=false}:{
  citationsOnly?:boolean;nativeScope?:import("../../api/nativeGraphInspection").InspectionPin;completion:SurfaceEvidenceCompletion|SurfaceNativeCompletionV1;composition?:Composition;worldId?:string|null;turnId?:string;buildSourceBasis?:import('../../api/types').WorldBuildGraphReceiptV1['source_basis'];
}) {
  const [citationsOpen, setCitationsOpen] = useState(false);
  // Number visible citations across this answer, independent of transport indexes.
  let nextNumber=0;
  const summaries=new Map<number,ReturnType<typeof sessionSummaryMarkdown>>();
  const choicesBySegment=completion.answer_segments.map((segment,index)=>{
    if(segment.kind==='session_summary' && worldId){
      const summary=sessionSummaryMarkdown(segment,worldId,nextNumber+1);summaries.set(index,summary);nextNumber=summary.nextNumber-1;
      return [];
    }
    return worldId && turnId ? [...passageChoices(completion,worldId,turnId,index),...('native_source_citations' in completion || 'native_body_citations' in completion
      ? nativeChoices(completion,worldId,turnId,index):[]),...(nativeScope?nativeRecapChoices(completion,nativeScope,index):[]),...(completion.schema==='dmb_surface_native_completion_v1'&&buildSourceBasis?nativeSavedChoices(completion,buildSourceBasis,worldId,turnId,index):[])].map(c=>({...c,number:++nextNumber})) : [];
  });
  const renderSegment=(s:(SurfaceEvidenceCompletion|SurfaceNativeCompletionV1)['answer_segments'][number],index:number,key:number) => {
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
    const graph=s.kind === 'graph_claim'||s.kind==='native_assertion_claim', source=s.kind === 'source_passage_claim',saved=s.kind==='saved_source_claim';
    const selected=('source_citations' in completion ? completion.source_citations : []).filter(c=>c.segment_index === index);
    return <section key={key} aria-label={graph ? 'World Graph fact' : source ? 'Source-supported statement' : saved?'Saved-page statement':s.kind === 'proposal' ? 'Proposed idea' : 'Evidence limitation'}>
      {graph ? <small>{s.kind==='native_assertion_claim'?'Reviewed World Graph':selected.length ? 'World Graph' : 'World Graph · source passage not opened'}</small> : null}
      {saved?<small>Saved authored page</small>:null}
      {s.kind === 'proposal' ? <small>Proposed idea</small> : null}
      {choicesBySegment[index]!.length ? <SourceCitationEvidence identity={canonical([completion,worldId,turnId,index])}
        statements={[{text:s.text,choices:choicesBySegment[index]!}]}/> : <WorldPlanAgentAnswer answer={s.text}/>}
      {!worldId || !turnId ? <>{selected.map((c,i)=><cite key={i}>{c.source_name}</cite>)}
        {'native_source_citations' in completion ? completion.native_source_citations.filter(c=>c.segment_index===index)
          .map((c,i)=><cite key={`native-${i}`}>{c.source_name} · {c.section_title}</cite>):null}
        {'native_body_citations' in completion ? completion.native_body_citations.filter(c=>c.segment_index===index)
          .map((c,i)=><cite key={`body-${i}`}>{c.source_name} · {c.section_title}</cite>):null}</>:null}
    </section>;
  };
  const chars=composition ? Array.from(composition.text) : [];
  const encounter = completion.schema === 'dmb_surface_native_completion_v1' && completion.surface_id === 'plan'
    ? completion.encounter_attachment_preview : undefined;
  const citationLabel = (index: number, title: string) => {
    const segment = completion.answer_segments[index];
    if (segment?.kind !== 'native_assertion_claim') return title;
    const standings = [...new Set(segment.qualifications.flatMap(item =>
      typeof item.standing === 'string' && ['provisional', 'established'].includes(item.standing)
        ? [item.standing] : []))];
    return standings.length ? `${title} · ${standings.join(' / ')}` : title;
  };
  if (citationsOnly) {
    const segments = completion.answer_segments.flatMap((_, index) =>
      choicesBySegment[index]?.length || summaries.get(index)?.targets.length ? [index] : []);
    return segments.length ? <details onToggle={event => setCitationsOpen(event.currentTarget.open)}>
      <summary>Cited in the reply</summary>
      {citationsOpen && <section aria-label="Cited in the reply">{segments.map(index =>
        summaries.has(index)
          ? <ul key={index}>{summaries.get(index)!.entries.map(entry =>
            <li key={entry.target}><a href={entry.target} title={entry.title}>{entry.number}. {entry.title}</a></li>)}</ul>
          : <SourceCitationEvidence key={index} identity={canonical([completion,worldId,turnId,index])} prefetchTitles
            statements={[{choices:choicesBySegment[index]!.map(choice => {
              const base=choice.title || choice.label;
              const labelled=citationLabel(index, base);
              return {...choice, buttonText: `${choice.number}. ${labelled}`, titleSuffix: labelled.slice(base.length)};
            })}]}/>)}</section>}
    </details> : null;
  }
  return <div aria-label="Evidence-grounded answer">{composition ? composition.ranges.map((r,i)=>
    r.domain === 'base' && r.base_segment_index !== null
      ? renderSegment(completion.answer_segments[r.base_segment_index]!,r.base_segment_index,i)
      : <section key={i} aria-label="Rules statement"><WorldPlanAgentAnswer answer={chars.slice(r.text_start,r.text_end).join('')}/></section>)
    : completion.answer_segments.map((s,i)=>renderSegment(s,i,i))}
    {worldId && encounter?.world_id === worldId && (
      <section aria-label="Proposed encounter attachment">
        <h3>{encounter.encounter_title} · revision {encounter.source_revision}</h3>
        <p>Prepare for {encounter.scene_title}</p>
        <ul aria-label="Combatants">{encounter.participants.map((name, index) => <li key={index}>{name}</li>)}</ul>
        {encounter.groups.length > 0 &&
          <ul aria-label="Groups">{encounter.groups.map((name, index) => <li key={index}>{name}</li>)}</ul>}
      </section>
    )}
  </div>;
}
