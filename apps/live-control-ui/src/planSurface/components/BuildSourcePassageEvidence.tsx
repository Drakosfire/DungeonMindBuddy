import {useLayoutEffect,useState} from 'react';
import {canonical} from '../../shared/sourcePassageProtocol';
import {SourceCitationEvidence} from './SourceCitationEvidence';
import {passageChoices,type PassageCompletion} from './sourceCitationReads';
export {isBuildSourceCompletion,isSurfaceSourceCompletion} from '../../shared/sourcePassageProtocol';

export function BuildSourcePassageEvidence({completion,worldId,turnId,segmentIndex,showClaimText=true}:{
  completion:PassageCompletion;worldId:string;turnId:string;segmentIndex?:number;showClaimText?:boolean;
}) {
  const [visible,setVisible]=useState(8);
  const identity=canonical([worldId,turnId,segmentIndex,completion]);
  useLayoutEffect(()=>{setVisible(8);},[identity]);
  const choices=passageChoices(completion,worldId,turnId,segmentIndex);
  return <section aria-label="Source passages">
    {!choices.length ? <p>No passage-backed claims were made in this answer.</p>:null}
    <SourceCitationEvidence identity={identity} statements={choices.slice(0,visible).map(c=>({
      text:showClaimText ? completion.answer_segments[c.segmentIndex!]?.text : undefined,
      choices:[c],
    }))}/>
    {visible<choices.length ? <button type="button" onClick={()=>setVisible(v=>v+8)}>Show more passages</button>:null}
  </section>;
}
