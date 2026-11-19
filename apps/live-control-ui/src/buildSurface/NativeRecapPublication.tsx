import {useEffect,useRef,useState} from 'react';
import type {ExactRunReviewPackage,ExtractionRunRecord} from '../api/types';
import {admitRecapSource,inspectRecapSource,resumeRecapSource,type NativeRecapSourceStatus} from '../api/nativeRecapSourceApi';
import {LiveApiError} from '../api/liveApi';
import {loadRecapSnapshot,readContext,prepareRecap,confirmRecap,extendEvidence,witnessFromLines,buildExtension,targetFor,
  type Snapshot,type Context,type Selection,type Metadata,type ReviewRecord,type ReviewField} from '../api/nativeRecapPublicationApi';
import type {ExactRunCandidateProjection} from '../api/exactRunCandidateProjectionApi';
import {readNativeRecovery,retain,verifyRecovery,archiveKnown,replaceAdmissionWithResume,type Located,type Operation} from './nativeRecapPublicationRecovery';

type Props={review:ExactRunReviewPackage;run:ExtractionRunRecord;worldId:string;onBusy:(busy:boolean)=>void};
const message=(e:unknown)=>e instanceof Error?e.message:'Native Recap is unavailable.';
function isDefinitivePrecommitRejection(error:unknown,operation:Operation|undefined):boolean{
  if(!(error instanceof LiveApiError)||error.status!==409)return false;
  if(operation?.stage==='confirmation')return ['candidate_parent_stale','candidate_source_authority_stale',
    'candidate_review_expired','native_recap_commit_stale'].includes(error.code??'');
  return operation?.stage==='extension'&&error.code==='knowledge_stale_parent_revision';
}

/** Recovery is mounted before any fresh-source or mutable-context read. */
export function NativeRecapPublication(props:Props){
  const [initial]=useState(()=>{try{return {saved:readNativeRecovery(props.worldId,props.run.run_id),error:null};}
    catch(e){return {saved:null,error:message(e)};}});
  const [pending,setPending]=useState<Located|null>(initial.saved),[error,setError]=useState<string|null>(initial.error);
  const [status,setStatus]=useState<NativeRecapSourceStatus|null>(null),[complete,setComplete]=useState(false),[busy,setBusy]=useState(false),[generation,setGeneration]=useState(0);
  const [definitive,setDefinitive]=useState(false);
  const alive=useRef(true),lock=useRef(false);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;props.onBusy(false);};},[props.onBusy]);
  async function execute(located:Located){
    await verifyRecovery(located);if(!alive.current)return;
    const {snapshot:s,operation:op}=located.value;
    if(op.stage==='confirmation'){
      await confirmRecap(s,op.packet);if(alive.current)setComplete(true);
      // Keep the exact request: a remount verifies its real receipt by replay.
      return;
    }
    if(op.stage==='extension'){
      await extendEvidence(s,op.request);
      await archiveKnown(located);
      if(alive.current){setPending(null);setGeneration(n=>n+1);}return;
    }
    const result=op.mode==='admit'?await admitRecapSource(op.target):await resumeRecapSource(op.target,op.previous);
    if(!alive.current)return;
    setStatus(result);
    if(result.state==='admitted'&&result.admission_committed&&result.opening.state==='verified'){
      await archiveKnown(located);if(alive.current){setPending(null);setGeneration(n=>n+1);}
    }
  }
  async function act(s?:Snapshot,op?:Operation){
    if(lock.current||complete||initial.error)return;
    lock.current=true;setBusy(true);props.onBusy(true);setError(null);setDefinitive(false);
    let attempted:Located|null=null;
    try{
      const located=s&&op?await retain(s,op):pending;
      attempted=located;
      if(!located)throw new Error('There is no retained request to recover.');
      if(!alive.current)return;setPending(located);await execute(located);
    }catch(e){if(alive.current){setError(message(e));setDefinitive(isDefinitivePrecommitRejection(e,attempted?.value.operation));}}
    finally{lock.current=false;if(alive.current)setBusy(false);props.onBusy(false);}
  }
  async function inspect(){
    if(lock.current||!pending||pending.value.operation.stage!=='admission')return;
    const op=pending.value.operation,previous=status??(op.mode==='resume'?op.previous:null);
    if(!previous)return;
    lock.current=true;setBusy(true);setError(null);
    try{const result=await inspectRecapSource(op.target,previous);if(alive.current)setStatus(result);}
    catch(e){if(alive.current)setError(message(e));}finally{lock.current=false;if(alive.current)setBusy(false);}
  }
  async function resume(){
    if(lock.current||!pending||pending.value.operation.stage!=='admission'||!status||status.admission_committed)return;
    // The APP owner has returned this real operation and command. Its deliberate
    // resume is a new explicit request; archive original exact bytes first.
    lock.current=true;setBusy(true);props.onBusy(true);setError(null);
    try{
      const target=pending.value.operation.target;
      const located=await replaceAdmissionWithResume(pending,{stage:'admission',mode:'resume',target,previous:status});
      if(!alive.current)return;setPending(located);await execute(located);
    }catch(e){if(alive.current)setError(message(e));}finally{lock.current=false;if(alive.current)setBusy(false);props.onBusy(false);}
  }
  async function setAside(){
    if(lock.current||!pending||!definitive)return;
    lock.current=true;
    try{await archiveKnown(pending);if(alive.current){setPending(null);setError(null);setGeneration(n=>n+1);setDefinitive(false);}}
    catch(e){if(alive.current)setError(message(e));}finally{lock.current=false;}
  }
  if(initial.error)return <p role="alert">{initial.error}</p>;
  if(pending)return <section aria-label="Saved native Recap request">
    <h3>Recover saved Recap {pending.value.operation.stage}</h3>
    <p>This request retains its original source and coordinates. No current candidate or head will replace it.</p>
    {complete?<p role="status">Native Recap publication confirmed.</p>:<button disabled={busy} onClick={()=>void act()}>Retry exact saved {pending.value.operation.stage}</button>}
    {pending.value.operation.stage==='admission'&&status&&<>
      <p role="status">Source admission: {status.state}; opening: {status.opening.state}. Facts are not published by admission.</p>
      <button disabled={busy} onClick={()=>void inspect()}>Inspect saved source operation</button>
      {!status.admission_committed&&['reserved','conflict','unknown'].includes(status.state)&&<button disabled={busy} onClick={()=>void resume()}>Resume exact source admission</button>}
    </>}
    {definitive&&<button disabled={busy} onClick={()=>void setAside()}>Archive rejected {pending.value.operation.stage} and review again</button>}
    {error&&<p role="alert">{error}</p>}
  </section>;
  return <>{error&&<p role="alert">{error}</p>}<FreshRecap key={generation} {...props} busy={busy} onOperation={act}/></>;
}

type Draft={action:Selection['action'];entity:string;fields:string[];evidence:string;epistemic:string;claim:string;standing:string;temporal:string;audience:string};
const empty=():Draft=>({action:'defer',entity:'',fields:[],evidence:'',epistemic:'',claim:'',standing:'',temporal:'',audience:'gm'});
const keyFor=(r:ReviewRecord)=>r.kind+':'+r.record_id;
const fieldKey=(f:ReviewField)=>f.field+(f.index===undefined?'':':'+f.index);
function metadata(d:Draft,sessionId:string):Metadata|null{
  if(!d.evidence||!d.epistemic||!d.claim||!d.standing||!d.temporal)return null;
  const temporal_scope:Metadata['temporal_scope']=d.temporal==='session'?{kind:'domain_ref',schema_term:'dungeonbuddy.time:fictional_anchor_v1',payload:{start:{session:Number(sessionId.slice(8))}}}:{kind:d.temporal};
  return {evidence_ref_ids:[d.evidence],visibility:{kind:'labels_any',labels:[`dungeonbuddy.visibility:${d.audience}`]},
    epistemic_basis:d.epistemic,claim_mode:d.claim,standing:d.standing,temporal_scope};
}
function FreshRecap({review,run,worldId,busy,onOperation,onBusy}:Props&{busy:boolean;onOperation:(s:Snapshot,op:Operation)=>Promise<void>}){
  const [loaded,setLoaded]=useState<{snapshot:Snapshot;projection:ExactRunCandidateProjection}|null>(null),[context,setContext]=useState<Context|null>(null);
  const [missing,setMissing]=useState(false),[error,setError]=useState<string|null>(null),[loading,setLoading]=useState(true);
  const [drafts,setDrafts]=useState<Record<string,Draft>>({}),[paragraph,setParagraph]=useState(''),[quote,setQuote]=useState('');
  const [prepared,setPrepared]=useState<import('../api/nativeRecapPublicationApi').Confirmation|null>(null),[working,setWorking]=useState(false),[held,setHeld]=useState<string|null>(null);
  const alive=useRef(true),lock=useRef(false);
  useEffect(()=>{
    alive.current=true;
    void(async()=>{
      try{
        if(!run.campaign_id||!run.session_id||!run.revision||!run.components?.candidate_graph?.sha256)throw new Error('Exact saved Recap coordinates are unavailable.');
        const joined=await loadRecapSnapshot(worldId,run.campaign_id,run.run_id,run.revision,run.components.candidate_graph.sha256,run.source_artifact_id,review.sourceRevisionId);
        if(!alive.current)return;setLoaded(joined);
        try{const c=await readContext(joined.snapshot);if(alive.current)setContext(c);}
        catch(e){if(e instanceof LiveApiError&&e.code==='candidate_source_not_admitted'){if(alive.current)setMissing(true);}else throw e;}
      }catch(e){if(alive.current)setError(message(e));}finally{if(alive.current)setLoading(false);}
    })();
    return()=>{alive.current=false;};
  },[worldId,run.run_id]);
  function update(r:ReviewRecord,change:Partial<Draft>){if(working||prepared||busy)return;setDrafts(v=>({...v,[keyFor(r)]:{...(v[keyFor(r)]??empty()),...change}}));}
  function selections():Selection[]{
    if(!loaded||!context)return [];
    const result:Selection[]=context.records.map(r=>{
      const d=drafts[keyFor(r)]??empty();
      if(d.action==='defer'||d.action==='reject')return {kind:r.kind,record_id:r.record_id,action:d.action};
      if(r.held_reason)throw new Error(r.held_reason);
      const m=metadata(d,loaded.snapshot.sessionId);
      if(r.kind==='node'||r.kind==='beat'){
        if(d.action==='use_existing'&&!d.entity.trim())throw new Error('An exact existing entity ID is required.');
        if(d.action==='create'&&!d.fields.length)throw new Error('Choose explicit facts for each created record.');
        if(d.fields.length&&!m)throw new Error('Choose source support and metadata explicitly.');
        return {kind:r.kind,record_id:r.record_id,action:d.action,...(d.action==='use_existing'?{entity_id:d.entity}:{}),
          facts:(r.selectable_facts??[]).filter(f=>d.fields.includes(fieldKey(f))).map(f=>({field:f.field,...(f.index===undefined?{}:{index:f.index}),metadata:m!}))};
      }
      if(!m)throw new Error('Choose relationship/placement support and metadata explicitly.');
      if(r.kind==='placement'&&(d.claim!=='dungeonbuddy.claim:observed_event'||d.temporal!=='session'))throw new Error('Placement requires an explicit observed event and its source-session temporal anchor.');
      return {kind:r.kind,record_id:r.record_id,action:'create',metadata:m};
    });
    const active=new Set(result.filter(r=>r.kind==='node'&&(r.action==='create'||r.action==='use_existing')).map(r=>r.record_id));
    for(const r of context.records){const d=drafts[keyFor(r)];if(d?.action!=='create')continue;
      if(r.kind==='edge'&&(!active.has(r.from_record_id??'')||!active.has(r.to_record_id??'')))throw new Error('Select both relationship endpoint identities explicitly.');
      if(r.kind==='placement'&&!active.has(r.record_id))throw new Error('Select the event identity before placement.');}
    return result;
  }
  async function prepare(){
    if(lock.current||!loaded||!context||prepared||busy)return;
    lock.current=true;setWorking(true);setError(null);setHeld(null);propsBusy(true);
    try{
      const chosen=selections();if(!chosen.some(r=>r.action==='create'||r.action==='use_existing'))throw new Error('All records are held. Choose explicit reviewed facts before preparing.');
      const result=await prepareRecap(loaded.snapshot,context,chosen);
      if(alive.current){if(result.status==='prepared')setPrepared(result.packet);else setHeld('The selected records remain held; no publication was prepared.');}
    }catch(e){if(alive.current)setError(message(e));}finally{lock.current=false;if(alive.current)setWorking(false);propsBusy(false);}
  }
  // Busy state also protects the parent document/review while preparing.
  function propsBusy(value:boolean){onBusy(value);}
  async function extend(){
    if(!loaded||!context||lock.current||busy)return;
    lock.current=true;setWorking(true);setError(null);
    try{
      const spans=loaded.projection.sourceSpans;
      const span=spans.find((_,i)=>String(i)===paragraph);
      if(!span)throw new Error('Choose a frozen source paragraph.');
      const witness=await witnessFromLines(loaded.snapshot,span.line_start??0,span.line_end??0,quote);
      const request=buildExtension(loaded.snapshot,context,witness,crypto.randomUUID(),new Date().toISOString());
      if(alive.current)await onOperation(loaded.snapshot,{stage:'extension',request});
    }catch(e){if(alive.current)setError(message(e));}finally{lock.current=false;if(alive.current)setWorking(false);}
  }
  if(loading)return <p role="status">Reading the exact saved Recap and source availability…</p>;
  if(!loaded)return <p role="alert">{error??'The exact source could not be verified.'}</p>;
  return <section aria-label="Native Recap publication"><h3>Review native Recap changes</h3>
    <p>Source availability, support evidence and fact publication are separate explicit steps. Nothing is admitted or published on opening this review.</p>
    {missing&&<><p>Source admission is missing or unverified. Recovering this exact source request will not accept its extracted facts.</p>
      <button disabled={busy||working} onClick={()=>void onOperation(loaded.snapshot,{stage:'admission',mode:'admit',target:targetFor(loaded.snapshot)})}>Admit or recover exact Recap source</button></>}
    {context&&!prepared&&<>
      <fieldset disabled={working||busy}><legend>Make selected source words available as support</legend>
        <p>A whole-body context interval is not support. Choose an explicit proper subrange, including for a one-line source. This does not establish that the words entail a claim.</p>
        <label>Frozen witness paragraph<select value={paragraph} onChange={e=>{setParagraph(e.target.value);setQuote('');}}><option value="">Choose paragraph</option>
          {loaded.projection.sourceSpans.map((span,i)=><option key={i} value={i}>{span.text_excerpt??`Lines ${span.line_start}–${span.line_end}`}</option>)}</select></label>
        <label>Exact witness text<input value={quote} onChange={e=>setQuote(e.target.value)}/></label>
        <button disabled={!quote||paragraph===''} onClick={()=>void extend()}>Extend exact support evidence</button>
      </fieldset>
      <p>Records not selected below stay held. Aliases, hints and narrative order are not automatically published. Choosing an order relationship or event placement is a separate explicit decision.</p>
      {context.records.map(r=>{
        const d=drafts[keyFor(r)]??empty();const editable=d.action==='create'||d.action==='use_existing';
        return <fieldset key={keyFor(r)} disabled={working||busy} aria-label={`Recap ${r.kind} ${r.record_id}`}>
          <legend>{String(r.candidate.label??r.candidate.title??r.relationship_type??r.record_id)} ({r.kind})</legend>
          {r.held_reason&&<p>Held: {r.held_reason}</p>}
          <label>{`Action for ${keyFor(r)}`}<select value={d.action} onChange={e=>update(r,{action:e.target.value as Draft['action']})}>
            <option value="defer">Hold</option><option value="reject">Reject</option>
            {!r.held_reason&&<option value="create">{r.kind==='placement'?'Place event explicitly':'Create selected facts'}</option>}
            {(r.kind==='node'||r.kind==='beat')&&<option value="use_existing">Use exact existing identity</option>}</select></label>
          {d.action==='use_existing'&&<label>{`Entity ID for ${keyFor(r)}`}<input value={d.entity} onChange={e=>update(r,{entity:e.target.value})}/></label>}
          {editable&&<>
            {(r.selectable_facts??[]).map(f=><label key={fieldKey(f)}><input type="checkbox" aria-label={`Fact ${keyFor(r)} ${fieldKey(f)}`} checked={d.fields.includes(fieldKey(f))}
              onChange={e=>update(r,{fields:e.target.checked?[...d.fields,fieldKey(f)]:d.fields.filter(x=>x!==fieldKey(f))})}/>{fieldKey(f)}: {String(f.value)}</label>)}
            <label>{`Support for ${keyFor(r)}`}<select value={d.evidence} onChange={e=>update(r,{evidence:e.target.value})}><option value="">Choose admitted support</option>
              {context.source_support.map(s=><option key={s.evidence_ref_id} value={s.evidence_ref_id}>{s.text}</option>)}</select></label>
            <p>These explicit metadata choices apply to the selected facts in this record.</p>
            <label>{`Epistemic basis for ${keyFor(r)}`}<select value={d.epistemic} onChange={e=>update(r,{epistemic:e.target.value})}><option value="">Choose basis</option><option value="asserted">Asserted</option><option value="inferred">Inferred</option></select></label>
            <label>{`Claim mode for ${keyFor(r)}`}<select value={d.claim} onChange={e=>update(r,{claim:e.target.value})}><option value="">Choose claim</option><option value="dungeonbuddy.claim:fact">Fact</option><option value="dungeonbuddy.claim:belief">Belief</option><option value="dungeonbuddy.claim:observed_event">Observed event</option></select></label>
            <label>{`Standing for ${keyFor(r)}`}<select value={d.standing} onChange={e=>update(r,{standing:e.target.value})}><option value="">Choose standing</option><option value="provisional">Provisional</option><option value="established">Established</option></select></label>
            <label>{`Temporal scope for ${keyFor(r)}`}<select value={d.temporal} onChange={e=>update(r,{temporal:e.target.value})}><option value="">Choose time</option><option value="unknown">Unknown</option><option value="session">Explicit source-session anchor</option><option value="timeless">Explicit timeless claim</option></select></label>
            <label>{`Audience for ${keyFor(r)}`}<select value={d.audience} onChange={e=>update(r,{audience:e.target.value})}><option value="gm">GM only</option><option value="player">Player-visible</option></select></label>
          </>}
        </fieldset>;
      })}
      <details><summary>Held and non-executable candidate information</summary>
        <p>{context.held_records.length} additional records held. Narrative beat order is not an authoritative chronology.</p>
        {context.records.filter(r=>Array.isArray(r.candidate.aliases)&&r.candidate.aliases.length).map(r=><p key={keyFor(r)}>Held aliases for {r.record_id}: {String(r.candidate.aliases)}</p>)}
      </details>
      <button disabled={working||busy} onClick={()=>void prepare()}>Prepare selected Recap facts</button>
    </>}
    {prepared&&<><p>Review prepared choices. Confirming publishes only this signed request; omitted records remain held.</p>
      <button disabled={busy||working} onClick={()=>void onOperation(loaded.snapshot,{stage:'confirmation',packet:prepared})}>Confirm native Recap publication</button></>}
    {held&&<p role="status">{held}</p>}{error&&<p role="alert">{error}</p>}
  </section>;
}
