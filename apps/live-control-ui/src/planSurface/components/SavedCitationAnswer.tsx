import type {SavedCitationPreview} from '../../api/savedCitationPreview';
import {canonical} from '../../shared/sourcePassageProtocol';
import {WorldPlanAgentAnswer} from './WorldPlanAgentAnswer';
import {SourceCitationEvidence} from './SourceCitationEvidence';
import {nativeChoices,nativeSavedChoices} from './sourceCitationReads';

/** Retained display metadata; executable work and admission stay in full history. */
export function SavedCitationAnswer({preview,answer,worldId,turnId}:{preview:SavedCitationPreview;answer:string;worldId:string;turnId:string}) {
  if(preview?.status!=='ready')return <WorldPlanAgentAnswer answer={answer}/>;
  let next=0;
  const statements=preview.answer_segments.map((segment,index)=>({text:segment.text,choices:[
    ...nativeChoices(preview,worldId,turnId,index),
    ...(preview.source_basis?nativeSavedChoices(preview,preview.source_basis,worldId,turnId,index):[]),
  ].map(choice=>({...choice,segmentIndex:index,number:++next}))}));
  return <SourceCitationEvidence identity={canonical([worldId,turnId,preview])} statements={statements}
    answer={answer} displaySegments={preview.answer_segments.map(s=>s.text)}/>;
}
