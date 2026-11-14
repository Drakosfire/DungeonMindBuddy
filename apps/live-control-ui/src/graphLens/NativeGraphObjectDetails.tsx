import {type NativeAssertion,type NativeGraphEntity} from '../api/nativeGraphInspection';
import {nativeObjectEvidenceChoices} from './nativeObjectEvidence';
import {nativeObjectSubjectKey,projectNativeObject} from './nativeObjectProjection';
import {SourceCitationEvidence} from '../planSurface/components/SourceCitationEvidence';
import {NativeObjectStatblock} from './NativeObjectStatblock';

export function NativeGraphObjectDetails({detail,entityId,label,labels=new Map<string,string>([[entityId,label]]),inlineHost,onInlineOpened,entityOnly=false}:{detail:NativeGraphEntity;entityId:string;label:string;labels?:Map<string,string>;inlineHost?:HTMLElement;onInlineOpened?:()=>void;entityOnly?:boolean}) {
 const projection=projectNativeObject({kind:"admitted-native",entityId,pin:detail.scope},detail,labels);
 return <>
  <h3>{label}</h3>
  {!detail.entity.found?<p>This object is unavailable in the selected revision.</p>:<>
   {!entityOnly && detail.scope.scope_mode === "world" && <a href={"/build?" + new URLSearchParams({
    world: detail.scope.managed_world_id,
    nativeWorld: detail.scope.native_world_id,
    bindingVersion: String(detail.scope.binding_version),
    graphRevision: detail.scope.revision_id,
    graphNodeId: entityId,
   })}>Open object in Build</a>}
   {entityOnly?<p>Source excerpts and linked statblocks are not available in the hosted explorer yet.</p>:<NativeObjectStatblock key={JSON.stringify([detail.scope,entityId])} pin={detail.scope} entityId={entityId} inlineHost={inlineHost} onInlineOpened={onInlineOpened}/>}
   {detail.entity.completeness.status!=='complete'?<p role="status">Some records are unavailable.</p>:null}
   {!detail.entity.assertions.length?<p>No admitted records for this object in this view.</p>:null}
   {projection.records.map(a=><NativeRecord key={`${entityId}:${a.assertion_id}`} assertion={a} detail={detail} labels={labels} entityOnly={entityOnly}/>)}
  </>}
 </>;
}

function valueText(a:NativeAssertion,labels:Map<string,string>):string {
 const v=a.value;
 return v.kind==='entity_ref' ? labels.get(v.entity_id)??v.entity_id
  :v.kind==='term_ref' ? v.term :typeof v.value==='string' ? v.value :JSON.stringify(v.value);
}
function NativeRecord({assertion:a,detail,labels,entityOnly}:{assertion:NativeAssertion;detail:NativeGraphEntity;labels:Map<string,string>;entityOnly:boolean}) {
 const choices=nativeObjectEvidenceChoices(detail,[a],entityOnly);
 const text=`${labels.get(a.subject_entity_id)??a.subject_entity_id} · ${a.predicate.split(':').at(-1)!.replaceAll('_',' ')}: ${valueText(a,labels)}`;
 return <section aria-label="Reviewed Graph record">
  <p>{a.metadata.claim_mode.replace('dungeonbuddy.claim:','')} · {a.metadata.epistemic_basis} · {a.metadata.standing}</p>
  {entityOnly?<p>{text}</p>:<SourceCitationEvidence identity={JSON.stringify([nativeObjectSubjectKey({kind:"admitted-native",entityId:a.subject_entity_id,pin:detail.scope}),a.assertion_id])}
   statements={[{text,choices}]}/> }
  <details><summary>Record qualifications</summary><pre>{JSON.stringify(a.metadata,null,2)}</pre></details>
 </section>;
}
