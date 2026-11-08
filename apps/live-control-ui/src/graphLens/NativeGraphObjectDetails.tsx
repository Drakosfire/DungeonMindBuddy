import {sameInspectionPin,type NativeAssertion,type NativeGraphEntity} from '../api/nativeGraphInspection';
import {inspectNativeGraph} from '../api/liveApi';
import {SourceCitationEvidence,type CitationChoice} from '../planSurface/components/SourceCitationEvidence';
import {NativeObjectStatblock} from './NativeObjectStatblock';

export function NativeGraphObjectDetails({detail,entityId,label,labels=new Map<string,string>([[entityId,label]]),inlineHost,onInlineOpened}:{detail:NativeGraphEntity;entityId:string;label:string;labels?:Map<string,string>;inlineHost?:HTMLElement;onInlineOpened?:()=>void}) {
 return <>
  <h3>{label}</h3>
  {!detail.entity.found?<p>This object is unavailable in the selected revision.</p>:<>
   <NativeObjectStatblock key={JSON.stringify([detail.scope,entityId])} pin={detail.scope} entityId={entityId} inlineHost={inlineHost} onInlineOpened={onInlineOpened}/>
   {detail.entity.completeness.status!=='complete'?<p role="status">Some records are unavailable.</p>:null}
   {!detail.entity.assertions.length?<p>No admitted records for this object in this view.</p>:null}
   {detail.entity.assertions.map(a=><NativeRecord key={`${entityId}:${a.assertion_id}`} assertion={a} detail={detail} labels={labels}/>)}
  </>}
 </>;
}

function valueText(a:NativeAssertion,labels:Map<string,string>):string {
 const v=a.value;
 return v.kind==='entity_ref' ? labels.get(v.entity_id)??v.entity_id
  :v.kind==='term_ref' ? v.term :typeof v.value==='string' ? v.value :JSON.stringify(v.value);
}
function NativeRecord({assertion:a,detail,labels}:{assertion:NativeAssertion;detail:NativeGraphEntity;labels:Map<string,string>}) {
 const choices:CitationChoice[]=detail.entity.evidence.filter(e=>a.metadata.evidence_ref_ids.includes(e.evidence_ref_id)&&e.evidence_role==='support')
  .map((e,i)=>({key:e.evidence_ref_id,number:i+1,title:'Supporting source · exact excerpt',label:'Read supporting source',kind:'passage',load:async()=>{
   const packet=await inspectNativeGraph(detail.scope,{kind:'source',assertion_id:a.assertion_id,evidence_ref_id:e.evidence_ref_id});
   if(packet.schema!=='dmb_native_graph_source_v1'||!sameInspectionPin(packet.scope,detail.scope))throw new Error('Source unavailable');
   return packet.source.text;
  }}));
 const text=`${labels.get(a.subject_entity_id)??a.subject_entity_id} · ${a.predicate.split(':').at(-1)!.replaceAll('_',' ')}: ${valueText(a,labels)}`;
 return <section aria-label="Reviewed Graph record">
  <p>{a.metadata.claim_mode.replace('dungeonbuddy.claim:','')} · {a.metadata.epistemic_basis} · {a.metadata.standing}</p>
  <SourceCitationEvidence identity={`${detail.scope.managed_world_id}:${detail.scope.revision_id}:${a.assertion_id}`}
   statements={[{text,choices}]}/>
  <details><summary>Record qualifications</summary><pre>{JSON.stringify(a.metadata,null,2)}</pre></details>
 </section>;
}
