import {useEffect,useRef,useState} from 'react';
import {getNativeAuthoringIdentities,getNativeGraphAccessGeneration,getNativeWorldSourceAdmissionStatus,admitNativeWorldSource,type NativeAuthoringIdentity} from '../api/liveApi';
import type {NativeWorldSourceAdmissionStatus} from '../api/types';
import {readManualContext,prepareManual,confirmManual,prepareProfile,confirmProfile,profileRequest,sha256,ManualApiError,clone,same} from '../api/nativeManualKnowledgeApi';
import type {ManualSelector,ManualContext,ManualRequest,ManualOperation,Witness,ProfileRequest,AdmissionTarget} from '../api/nativeManualKnowledgeTypes';
import {archive,dispatched,failed,freshRecovery,store,uncertain,verifyRecovery,type Located,type Scope} from './nativeManualKnowledgeRecovery';

export interface FreshManualSource {selector:ManualSelector;markdown:string}
export interface NativeManualProps {scope:Scope;initial:Located|null;getFresh:()=>FreshManualSource;
  isCurrent:()=>boolean;getSelectedText?:()=>string;onBusyChange?:(busy:boolean)=>void;onRetained:(value:Located|null)=>void}
const errorText=(e:unknown)=>e instanceof Error?e.message:'Manual authoring failed. The original request is retained.';

export function NativeManualKnowledge({scope,initial,getFresh,isCurrent,getSelectedText,onBusyChange,onRetained}:NativeManualProps){
  const [saved,setSaved]=useState(initial),[context,setContext]=useState<ManualContext|null>(null);
  const [fresh,setFresh]=useState<FreshManualSource|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [validated,setValidated]=useState(!initial);
  const [externalChanged,setExternalChanged]=useState(false),syncVersion=useRef(0);
  const [collision,setCollision]=useState(false);
  const [missing,setMissing]=useState(false),[admission,setAdmission]=useState<NativeWorldSourceAdmissionStatus|null>(null);
  const [mode,setMode]=useState<'object'|'relationship'>('object'),[kind,setKind]=useState('npc');
  const [name,setName]=useState(''),[role,setRole]=useState(''),[aliases,setAliases]=useState(''),[description,setDescription]=useState('');
  const [nodes,setNodes]=useState<NativeAuthoringIdentity[]>([]),[from,setFrom]=useState(''),[to,setTo]=useState(''),[predicate,setPredicate]=useState('located_in');
  const [span,setSpan]=useState(''),[quote,setQuote]=useState(''),[passagesOpen,setPassagesOpen]=useState(false);
  const identityCache=useRef<{key:string;rows:NativeAuthoringIdentity[]}|null>(null);
  const alive=useRef(true),working=useRef(false),savedRef=useRef(saved),loaded=useRef(false);
  const current=useRef({getFresh,isCurrent,onBusyChange,onRetained});current.current={getFresh,isCurrent,onBusyChange,onRetained};
  savedRef.current=saved;
  function active(){if(!alive.current||!current.current.isCurrent())throw new Error('The selected World/document changed. Recover the original saved request.');}
  async function action(fn:()=>Promise<void>){if(working.current)return;working.current=true;setBusy(true);setError('');current.current.onBusyChange?.(true);
    try{active();if(externalChanged)throw new Error('Another tab changed the active journal. The original packet is retained; fresh actions are blocked.');if(savedRef.current&&!validated)throw new Error('The retained record is invalid. Fresh authoring is blocked.');await fn();}catch(e){if(alive.current)setError(errorText(e));}finally{working.current=false;if(alive.current)setBusy(false);current.current.onBusyChange?.(false);}}
  function adopt(v:Located|null){savedRef.current=v;if(alive.current)setSaved(v);current.current.onRetained(v);}
  async function persist(value:Located['value'],previous:Located|null=savedRef.current){active();const next=await store(scope,value,previous);adopt(next);return next;}
  async function load(){
    active();if(savedRef.current)return;
    const snapshot=current.current.getFresh();
    if(await sha256(snapshot.markdown)!==snapshot.selector.bodySha256)throw new Error('The committed source bytes do not match this run.');
    active();setFresh(snapshot);
    try{const result=await readManualContext(snapshot.selector);active();
      const bytes=new TextEncoder().encode(snapshot.markdown);
      for(const w of result.spans){if(w.endByte>bytes.length||await sha256(bytes.slice(w.startByte,w.endByte))!==w.sliceSha256)throw new Error('Frozen source interval does not match the saved bytes.');
        new TextDecoder('utf-8',{fatal:true}).decode(bytes.slice(w.startByte,w.endByte));}
      active();setContext(result);setMissing(false);
      if(identityCache.current?.key!==identityKey(result)){identityCache.current=null;setNodes([]);}
      if(mode==='relationship')await identities(result);
    }catch(e){if(e instanceof ManualApiError&&e.code==='manual_source_not_admitted'){setMissing(true);setContext(null);}else throw e;}
  }
  useEffect(()=>{alive.current=true;if(!loaded.current){loaded.current=true;
    if(initial)void verifyRecovery(initial.value).then(()=>{if(alive.current)setValidated(true);}).catch(e=>{if(alive.current)setError(errorText(e));});
    else void action(load);}
    return()=>{alive.current=false;current.current.onBusyChange?.(false);};},[]);
  function identityKey(c:ManualContext){return JSON.stringify([scope.worldId,c.source.nativeWorldId,c.source.bindingVersion,c.parentRevisionId,c.sourceAuthorityEpoch,getNativeGraphAccessGeneration()]);}
  useEffect(()=>{
    if(initial?.raw===savedRef.current?.raw&&initial?.key===savedRef.current?.key)return;
    const old=savedRef.current;
    if(working.current||(old&&uncertain(old.value)&&(!initial||!same(old.value.operation,initial.value.operation)))){
      setExternalChanged(true);setError('Another tab changed or removed the original uncertain operation. Its original packet is retained; fresh authoring is blocked.');return;
    }
    const ticket=++syncVersion.current;
    setValidated(!initial);savedRef.current=initial;setSaved(initial);
    if(initial)void verifyRecovery(initial.value).then(()=>{if(alive.current&&ticket===syncVersion.current)setValidated(true);})
      .catch(e=>{if(alive.current&&ticket===syncVersion.current)setError(errorText(e));});
  },[initial?.raw,initial?.key]);
  async function identities(c=context){
    if(!c)return;const key=identityKey(c);
    if(identityCache.current?.key===key){setNodes(identityCache.current.rows);return;}
    const rows=await getNativeAuthoringIdentities(scope.worldId);active();
    if(key!==identityKey(c))throw new Error('Graph authorization changed during identity lookup.');
    identityCache.current={key,rows};setNodes(rows);
  }
  function choose(w:Witness){if(!fresh)return;const bytes=new TextEncoder().encode(fresh.markdown);setSpan(w.sourceSpanRefId);setQuote(new TextDecoder('utf-8',{fatal:true}).decode(bytes.slice(w.startByte,w.endByte)));}
  function selectEditor(){
    if(!fresh||!context)throw new Error('Read the exact saved source first.');
    const value=getSelectedText?.()??'';if(!value.trim())throw new Error('Select exact saved text or choose a frozen passage.');
    const bytes=new TextEncoder().encode(fresh.markdown);
    const matches=context.spans.filter(w=>{const t=new TextDecoder('utf-8',{fatal:true}).decode(bytes.slice(w.startByte,w.endByte));
      const at=t.indexOf(value);return at>=0&&t.indexOf(value,at+1)<0;});
    if(matches.length!==1)throw new Error('The editor text is not one exact frozen passage selection. Choose saved text explicitly.');
    setSpan(matches[0].sourceSpanRefId);setQuote(value);setName(value.trim());
  }
  function passage(w:Witness){if(!fresh)return '';return new TextDecoder('utf-8',{fatal:true}).decode(new TextEncoder().encode(fresh.markdown).slice(w.startByte,w.endByte));}
  function lines(w:Witness){if(!fresh)return '';const bytes=new TextEncoder().encode(fresh.markdown);
    return new TextDecoder().decode(bytes.slice(0,w.startByte)).split('\n').length+'–'+new TextDecoder().decode(bytes.slice(0,Math.max(w.startByte,w.endByte-1))).split('\n').length;}
  async function witness():Promise<Witness>{
    if(!fresh||!context)throw new Error('Read the exact committed source first.');
    const selected=context.spans.find(w=>w.sourceSpanRefId===span);if(!selected||!quote.trim())throw new Error('Choose one exact frozen source passage or subrange.');
    const bytes=new TextEncoder().encode(fresh.markdown),part=new TextDecoder('utf-8',{fatal:true}).decode(bytes.slice(selected.startByte,selected.endByte));
    const offset=part.indexOf(quote);if(offset<0||part.indexOf(quote,offset+1)>=0)throw new Error('The witness must occur exactly once inside the chosen frozen range.');
    const encoded=new TextEncoder().encode(quote);if(new TextDecoder('utf-8',{fatal:true}).decode(encoded)!==quote)throw new Error('Do not split a Unicode character.');
    const startByte=selected.startByte+new TextEncoder().encode(part.slice(0,offset)).length;
    return {sourceSpanRefId:selected.sourceSpanRefId,startByte,endByte:startByte+encoded.length,sliceSha256:await sha256(encoded)};
  }
  function operation():ManualOperation{
    if(!context)throw new Error('Read the source first.');
    if(mode==='object'){
      if(!name.trim()||!context.kinds[kind])throw new Error('Choose a supported kind and name.');
      const seen=new Set<string>();const values=aliases.split(/[,\n]+/).map(x=>x.trim()).filter(x=>{const k=x;if(!x||seen.has(k))return false;seen.add(k);return true;});
      return {kind:'object',objectKind:kind,name:name.trim(),role:role.trim()||null,aliases:values,description:description.trim()||null};
    }
    const a=nodes.find(n=>n.node_id===from&&n.selectable!==false),b=nodes.find(n=>n.node_id===to&&n.selectable!==false);
    if(!a||!b||a.node_id===b.node_id||!context.predicates[predicate])throw new Error('Choose two distinct authorized objects and a supported relationship.');
    return {kind:'relationship',source:{entityId:a.node_id,name:a.label,objectKind:a.kind},target:{entityId:b.node_id,name:b.label,objectKind:b.kind},predicate,label:null,description:description.trim()||null};
  }
  async function preview(){
    let located=savedRef.current;
    if(!located){const currentSource=current.current.getFresh();if(!fresh||!same(currentSource.selector,fresh.selector))throw new Error('The source changed. Explicitly refresh its review.');if(!context?.manualCapability)throw new Error('Explicitly adopt the reviewed manual capability first.');
      const request:ManualRequest={schema:'dmb_native_manual_prepare_v1',source:clone(context.source),operationId:crypto.randomUUID(),createdAt:new Date().toISOString(),
        expectedParentRevisionId:context.parentRevisionId,expectedSourceAuthorityEpoch:context.sourceAuthorityEpoch,witness:await witness(),operation:operation()};
      located=await persist(freshRecovery(scope,{stage:'manual',request,plan:null,witnessText:quote}),null);
    }
    if(located.value.submitted)throw new Error('Retry the original confirmation, never prepare another packet.');
    const op=located.value.operation;
    if(op.stage==='manual'){
      try{const plan=await prepareManual(op.request);active();await persist({...located.value,operation:{...op,plan}},located);}
      catch(e){if(e instanceof ManualApiError&&e.code==='manual_context_interval_collision'){setCollision(true);throw new Error('This exact interval is CONTEXT evidence. Explicitly choose another exact subrange; nothing was trimmed or published.');}throw e;}
    }else if(op.stage==='profile'){
      const plan=await prepareProfile(op.request);active();await persist({...located.value,operation:{...op,plan}},located);
    }
  }
  async function beginProfile(){if(!context||context.manualCapability)throw new Error('Read the current profile first.');
    const request:ProfileRequest=profileRequest(context);await persist(freshRecovery(scope,{stage:'profile',request,plan:null}),null);await preview();}
  async function submit(){
    const old=savedRef.current;if(!old)throw new Error('No saved operation.');await verifyRecovery(old.value);
    const op=old.value.operation;if(op.stage==='admission')throw new Error('Recover admission with a status read first.');
    if(!op.plan)throw new Error('Prepare and retain the signed review first.');
    const wasUncertain=uncertain(old.value);const marked=await persist(dispatched(old.value),old);
    try{const result=op.stage==='manual'?await confirmManual(op.plan):await confirmProfile(op.plan);active();
      await persist({...marked.value,receipt:result},marked);
    }catch(e){active();await persist(failed(marked.value,e instanceof ManualApiError&&e.verifiedZero,wasUncertain),marked);throw e;}
  }
  async function checkAdmission(){
    const retained=savedRef.current;
    const target=retained?.value.operation.stage==='admission'?retained.value.operation.target:
      fresh?{worldId:scope.worldId,documentId:scope.documentId,revision:fresh.selector.documentRevision,bodySha256:fresh.selector.bodySha256}:null;
    if(!target)throw new Error('Read the committed source selector first.');
    const status=await getNativeWorldSourceAdmissionStatus(target.documentId,target.revision);active();
    if(status.schema_version!=='dmb_native_world_source_admission_status_v1'||status.world_id!==target.worldId||status.document_id!==target.documentId||status.loaded_revision!==target.revision||status.body_sha256!==target.bodySha256)
      throw new Error('Source status belongs to another saved target. The original request is retained.');
    setAdmission(status);
    if(retained&&retained.value.operation.stage==='admission'&&status.state==='admitted')await persist({...retained.value,receipt:status},retained);
    else if(!retained&&status.state==='admitted')await load();
  }
  async function admit(){
    let located=savedRef.current;
    if(!located){if(!fresh||!admission)throw new Error('Check the exact saved source status first.');
      const target:AdmissionTarget={worldId:scope.worldId,documentId:scope.documentId,revision:fresh.selector.documentRevision,bodySha256:fresh.selector.bodySha256};
      located=await persist(freshRecovery(scope,{stage:'admission',target}),null);
    }
    if(located.value.operation.stage!=='admission')throw new Error('Another operation is retained.');
    const target=located.value.operation.target;
    if(located.value.submitted&&!admission)throw new Error('Check the retained admission status before retrying.');
    setAdmission(null); // Every dispatch consumes the matching status observation.
    const wasUncertain=uncertain(located.value),marked=await persist(dispatched(located.value),located);
    try{const status=await admitNativeWorldSource(target.documentId,target.revision,target.bodySha256);active();
      if(status.schema_version!=='dmb_native_world_source_admission_status_v1'||status.state!=='admitted'||status.world_id!==target.worldId||status.document_id!==target.documentId||status.loaded_revision!==target.revision||status.body_sha256!==target.bodySha256)
        throw new Error('Admission outcome is unverified. Keep the exact target.');
      await persist({...marked.value,receipt:status},marked);setAdmission(status);
    }catch(e){active();await persist(failed(marked.value,false,wasUncertain),marked);throw e;}
  }
  async function startAgain(){const old=savedRef.current;if(!old)return;await archive(scope,old);active();adopt(null);setContext(null);setAdmission(null);setQuote('');await load();}
  async function editUnsubmitted(){
    const old=savedRef.current;if(!old||old.value.submitted||old.value.operation.stage!=='manual')throw new Error('Only an unsubmitted original draft can be edited.');
    const draft=clone(old.value.operation);await archive(scope,old);active();adopt(null);setCollision(false);await load();
    setQuote(draft.witnessText);setSpan(draft.request.witness.sourceSpanRefId);
    const o=draft.request.operation;setMode(o.kind);setDescription(o.description??'');
    if(o.kind==='object'){setName(o.name);setKind(o.objectKind);setRole(o.role??'');setAliases(o.aliases.join('\n'));}
    else{setFrom(o.source.entityId);setTo(o.target.entityId);setPredicate(o.predicate);await identities();}
  }
  const op=saved?.value.operation;
  const label=(n:NativeAuthoringIdentity)=>n.label+' · '+n.kind+(nodes.filter(x=>x.label===n.label).length>1?' · '+n.node_id:'');
  const mapped=context?.predicates[predicate];const a=nodes.find(n=>n.node_id===from),b=nodes.find(n=>n.node_id===to);
  return <section aria-label="Native manual World knowledge"><h3>Author World knowledge</h3>
    <p>Review exact saved evidence, then explicitly confirm an object or directed relationship. Facts are World-scoped, GM-private, asserted and established; time is unknown. Descriptions are retained.</p>
    {error&&<p role="alert">{error}</p>}{externalChanged&&<p role="status">Cross-tab conflict: no fresh operation will be sent.</p>}{busy&&<p role="status">Checking the exact saved operation…</p>}
    {saved&&!validated?<p role="status">Retained operation is blocked until its original record is verified.</p>:saved?<><p>{op?.stage==='manual'?'Saved manual review':op?.stage==='profile'?'Explicit World capability adoption':'Saved source admission'}</p>
      {op?.stage==='manual'&&<><blockquote>{op.witnessText}</blockquote>{op.request.operation.kind==='object'?<dl>
        <dt>Name</dt><dd>{op.request.operation.name}</dd><dt>Kind</dt><dd>{op.request.operation.objectKind}</dd>
        <dt>Role</dt><dd>{op.request.operation.role||op.request.operation.objectKind}</dd><dt>Aliases</dt><dd>{(op.request.operation.aliases.length?op.request.operation.aliases:[op.request.operation.name]).join(', ')}</dd>
        <dt>Description</dt><dd>{op.request.operation.description||'None'}</dd></dl>:<dl>
        <dt>From</dt><dd>{op.request.operation.source.name+' · '+op.request.operation.source.objectKind}</dd><dt>Relationship</dt><dd>{op.request.operation.predicate}</dd>
        <dt>To</dt><dd>{op.request.operation.target.name+' · '+op.request.operation.target.objectKind}</dd><dt>Description</dt><dd>{op.request.operation.description||'None'}</dd>
        {op.request.operation.predicate==='belongs_to'&&<><dt>Will record</dt><dd>{op.request.operation.target.name+' owns '+op.request.operation.source.name+' (direction reversed)'}</dd></>}
      </dl>}</>}
      {op?.stage==='profile'&&<p>This explicitly adopts the reviewed manual relationship capability for this World. It does not change existing facts or source access.</p>}
      {saved.value.receipt?<><p role="status">{op?.stage==='manual'?'Native World knowledge publication confirmed.':op?.stage==='profile'?'World capability adoption confirmed.':'Saved source admission confirmed.'}</p>
        <button disabled={busy} onClick={()=>void action(startAgain)}>Continue with a fresh source review</button></>:
        op?.stage==='admission'?<><button disabled={busy} onClick={()=>void action(checkAdmission)}>Check original admission status</button>
          {admission&&<button disabled={busy} onClick={()=>void action(admit)}>Retry original source admission</button>}</>:
        op?.plan?<><p>The signed review is retained. Confirming publishes only this original packet.</p><button disabled={busy} onClick={()=>void action(submit)}>{saved.value.submitted?'Retry original confirmation':'Confirm '+(op.stage==='manual'?'World change':'World capability adoption')}</button></>:
        <button disabled={busy} onClick={()=>void action(preview)}>Retry original preview</button>}
      {collision&&!saved.value.submitted&&<button disabled={busy} onClick={()=>void action(editUnsubmitted)}>Retain original draft and edit exact witness</button>}
      {!saved.value.receipt&&!uncertain(saved.value)&&<button disabled={busy} onClick={()=>void action(startAgain)}>Set aside retained review and refresh</button>}
      {uncertain(saved.value)&&!saved.value.receipt&&<p role="status">An earlier outcome may have committed. Fresh authoring is blocked; retain and recover its original request.</p>}
    </>:context?.transitionRequired?<><p>This World needs explicit manual capability adoption before authoring.</p><button disabled={busy} onClick={()=>void action(beginProfile)}>Review World capability adoption</button></>:
    missing?<><p>This exact saved source is not yet admitted. No admission was performed.</p><button disabled={busy} onClick={()=>void action(checkAdmission)}>Check saved source status</button>
      {admission?.state==='pending'&&<button disabled={busy} onClick={()=>void action(admit)}>Admit this exact saved source</button>}</>:
    context?<fieldset disabled={busy||externalChanged}><legend>Source and assertion</legend>
      <button type="button" onClick={()=>void action(load)}>Refresh exact source context</button>
      <button type="button" onClick={()=>void action(async()=>selectEditor())}>Use selected document text</button>
      <details onToggle={e=>setPassagesOpen(e.currentTarget.open)}><summary>Choose a saved passage</summary>{passagesOpen&&context.spans.map(w=><div key={w.sourceSpanRefId}><p>{passage(w)}</p><button type="button" onClick={()=>choose(w)}>Use passage · lines {lines(w)}</button></div>)}</details>
      <label>Frozen passage<select value={span} onChange={e=>{const w=context.spans.find(w=>w.sourceSpanRefId===e.target.value);if(w)choose(w);}}><option value="">Choose a saved passage</option>{context.spans.map((w,i)=><option key={w.sourceSpanRefId} value={w.sourceSpanRefId}>Saved passage {i+1}</option>)}</select></label>
      <label>Exact witness or subrange<textarea value={quote} onChange={e=>setQuote(e.target.value)}/></label>
      <label>Declare<select value={mode} onChange={e=>{setMode(e.target.value as 'object'|'relationship');if(e.target.value==='relationship')void action(identities);}}><option value="object">Object</option><option value="relationship">Relationship</option></select></label>
      {mode==='object'?<><label>Name<input value={name} onChange={e=>setName(e.target.value)}/></label><label>Kind<select value={kind} onChange={e=>setKind(e.target.value)}>{Object.keys(context.kinds).map(k=><option key={k}>{k}</option>)}</select></label>
        <label>Role (blank defaults to kind)<input value={role} onChange={e=>setRole(e.target.value)}/></label><label>Aliases (comma or newline)<textarea value={aliases} onChange={e=>setAliases(e.target.value)}/></label></>:
      <><label>From<select value={from} onChange={e=>setFrom(e.target.value)}><option value="">Choose object</option>{nodes.map(n=><option key={n.node_id} value={n.node_id} disabled={n.selectable===false}>{label(n)}</option>)}</select></label>
        <label>Relationship<select value={predicate} onChange={e=>setPredicate(e.target.value)}>{Object.keys(context.predicates).map(k=><option key={k}>{k}</option>)}</select></label>
        <label>To<select value={to} onChange={e=>setTo(e.target.value)}><option value="">Choose object</option>{nodes.map(n=><option key={n.node_id} value={n.node_id} disabled={n.selectable===false}>{label(n)}</option>)}</select></label>
        {a&&b&&mapped&&<p>Will record: {mapped.reverseEndpoints?b.label:a.label} {mapped.term.split(':').pop()} {mapped.reverseEndpoints?a.label:b.label}{mapped.reverseEndpoints?' (direction reversed)':''}.</p>}</>}
      <label>Description<textarea value={description} onChange={e=>setDescription(e.target.value)}/></label><button onClick={()=>void action(preview)}>Preview World change</button>
    </fieldset>:!busy&&<button onClick={()=>void action(load)}>Read exact source context</button>}
  </section>;
}
