import {SourceCitationEvidence} from './SourceCitationEvidence';
import {passageChoices,type PassageCompletion} from './sourceCitationReads';
import {savedSectionChoices,type SavedSectionEvidenceProps} from './BuildSavedSectionEvidence';
import {canonical} from '../../shared/sourcePassageProtocol';

/** Ordinary answer and citations share one disclosure owner; diagnostics are optional. */
export function SourceCitedAnswer({answer,completion,worldId,turnId,saved}:{answer:string;completion:PassageCompletion;worldId:string;turnId:string;saved?:Omit<SavedSectionEvidenceProps,'segments'|'worldId'|'turnId'>}){
  const choices=[...passageChoices(completion,worldId,turnId),...(saved ? savedSectionChoices({...saved,worldId,turnId,segments:completion.answer_segments}) : [])]
    .sort((a,b)=>(a.segmentIndex??0)-(b.segmentIndex??0)).map((c,index)=>({...c,number:index+1}));
  return <SourceCitationEvidence identity={canonical([worldId,turnId,answer,completion,saved])} answer={answer}
    displaySegments={completion.answer_segments.map(s=>s.text)} statements={[{choices}]}/>;
}
