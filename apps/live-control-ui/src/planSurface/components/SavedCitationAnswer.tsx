import {isSessionSummary} from '../../shared/surfaceEvidenceProtocol';
import {sessionSummaryMarkdown} from '../../shared/sessionEvidenceCitation';
import type {SavedCitationPreview} from '../../api/savedCitationPreview';
import {canonical,isRelatedPageClaim} from '../../shared/sourcePassageProtocol';
import {WorldPlanAgentAnswer} from './WorldPlanAgentAnswer';
import {SourceCitationEvidence} from './SourceCitationEvidence';
import {nativeChoices,nativeSavedChoices,relatedPageChoice} from './sourceCitationReads';

/** Retained display metadata; executable work and admission stay in full history. */
export function SavedCitationAnswer({preview,answer,worldId,turnId}:{preview:SavedCitationPreview;answer:string;worldId:string;turnId:string}) {
  if(preview?.status!=='ready'||preview.answer_segments.map(s=>s.text).join('\n')!==answer)return <WorldPlanAgentAnswer answer={answer}/>;
  let next=0;
  const displaySegments:string[]=[],targets:string[]=[];
  const statements=preview.answer_segments.map((segment,index)=>{
    if(isSessionSummary(segment)) {
      const summary=sessionSummaryMarkdown(segment,worldId,next+1);
      next=summary.nextNumber-1;displaySegments.push(summary.text);targets.push(...summary.targets);
      return {text:summary.text,choices:[]};
    }
    displaySegments.push(segment.text);
    return {text:segment.text,choices:[
    ...nativeChoices(preview,worldId,turnId,index),
    ...(isRelatedPageClaim(segment,worldId)?[relatedPageChoice(segment,worldId,turnId,index)]:[]),
    ...(preview.source_basis?nativeSavedChoices(preview,preview.source_basis,worldId,turnId,index):[]),
  ].map(choice=>({...choice,segmentIndex:index,number:++next}))};});
  return <SourceCitationEvidence identity={canonical([worldId,turnId,preview])} statements={statements}
    answer={displaySegments.join("\n")} displaySegments={displaySegments} allowedInternalLinks={targets}/>;
}
