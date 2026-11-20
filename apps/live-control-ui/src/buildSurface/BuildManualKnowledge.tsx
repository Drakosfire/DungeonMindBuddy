import {useEffect,useRef,useState} from 'react';
import {commitGraphObjectAuthoringWrite} from '../api/liveApi';
import type {ExactRunReviewPackage,ExtractionRunRecord,GraphReviewHandoffPayload,WorkspaceDocumentRecord,WorldbuildingFrozenSpanCatalog} from '../api/types';
import {useMarkdownCanvasSession} from '../markdownCanvas/MarkdownCanvasSession';
import {readKnowledgeRecovery} from './buildManualKnowledge';
import {NativeManualKnowledge,type FreshManualSource} from './NativeManualKnowledge';
import {archive,discover,legacyTransaction,type LegacyLocated,type Located,type Scope} from './nativeManualKnowledgeRecovery';

type Props={worldId:string;document:WorkspaceDocumentRecord;run:ExtractionRunRecord;handoff:GraphReviewHandoffPayload;
  review?:ExactRunReviewPackage|null;sourceContentSha256:string;isScopeCurrent:()=>boolean;
  frozenCatalog?:WorldbuildingFrozenSpanCatalog|null;onBusyChange?:(busy:boolean)=>void};
const message=(e:unknown)=>e instanceof Error?e.message:'Saved manual authoring could not be read.';

/** Recovery routing never reinterprets classic packets as native requests. */
export function BuildManualKnowledge(props:Props){
  return <ScopedManualKnowledge key={JSON.stringify([props.worldId,props.document.document_id])} {...props}/>;
}
function ScopedManualKnowledge(props:Props){
  const session=useMarkdownCanvasSession();
  const scope:Scope={worldId:props.worldId,documentId:props.document.document_id};
  const scopeKey=JSON.stringify(scope),alive=useRef(true),busyRef=useRef(false),current=useRef({props,session,scopeKey});
  current.current={props,session,scopeKey};
  const [state,setState]=useState(()=>{try{return {...discover(scope),error:''};}catch(e){return {native:null,legacy:null,error:message(e)};}});
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  function isCurrent(){return alive.current&&current.current.scopeKey===scopeKey&&current.current.props.isScopeCurrent();}
  function refresh(){try{setState({...discover(scope),error:''});}catch(e){setState({native:null,legacy:null,error:message(e)});}}
  useEffect(()=>{alive.current=true;const changed=()=>refresh();window.addEventListener('storage',changed);
    return()=>{alive.current=false;window.removeEventListener('storage',changed);};},[scopeKey]);
  function getFresh():FreshManualSource{
    const c=current.current,p=c.props,s=c.session;
    if(!isCurrent()||s.dirty||!['ready_clean','committed'].includes(s.phase)||s.record?.document_id!==scope.documentId
      ||s.record.world_id!==scope.worldId||s.record.kind!=='worldbuilding_source'||!s.snapshot
      ||s.snapshot.loaded_revision!==p.handoff.document_revision||p.handoff.document_id!==scope.documentId
      ||p.handoff.extraction_run_id!==p.run.run_id||p.handoff.source_artifact_id!==p.run.source_artifact_id
      ||p.run.source_domain!=='worldbuilding'||p.run.status!=='reviewable'||typeof p.run.revision!=='number'||!Number.isSafeInteger(p.run.revision)||p.run.revision<1
      ||s.snapshot.content_sha256.replace(/^sha256:/,'')!==p.sourceContentSha256.replace(/^sha256:/,''))
      throw new Error('Save the source and reopen its exact extraction before fresh authoring. Saved recovery remains available.');
    return {selector:{schema:'dmb_native_manual_context_v1',managedWorldId:scope.worldId,documentId:scope.documentId,
      documentRevision:p.handoff.document_revision,bodySha256:p.sourceContentSha256.replace(/^sha256:/,''),runId:p.run.run_id,runRevision:p.run.revision},
      markdown:s.snapshot.markdown};
  }
  async function legacyRetry(located:LegacyLocated){
    if(busyRef.current)return;busyRef.current=true;setBusy(true);props.onBusyChange?.(true);setError('');
    try{if(!isCurrent()||!located.value.submitted||!located.value.prepared||located.value.receipt)throw new Error('Only the original submitted classic packet may be retried.');
      await legacyTransaction(scope,located,async()=>{
        if(!isCurrent())throw new Error('The selected World changed.');
        const old=located.value;
        const receipt=await commitGraphObjectAuthoringWrite({...old.request,confirmToken:old.prepared!.confirm_token!,currentOverlayToken:old.prepared!.current_overlay_token});
        if(!isCurrent())throw new Error('The original result is retained for recovery in its World.');
        const next={...old,receipt};const raw=JSON.stringify(next);readKnowledgeRecovery(raw,old.scope);
        if(localStorage.getItem(located.key)!==located.raw)throw new Error('Another tab changed this classic record.');
        localStorage.setItem(located.key,raw);if(localStorage.getItem(located.key)!==raw)throw new Error('The original result could not be retained.');
      });refresh();
    }catch(e){if(alive.current)setError(message(e)+' The exact classic packet is retained.');}
    finally{busyRef.current=false;if(alive.current)setBusy(false);props.onBusyChange?.(false);}
  }
  async function archiveLegacy(located:LegacyLocated){
    if(busyRef.current)return;busyRef.current=true;setBusy(true);setError('');
    try{if(!isCurrent())throw new Error('Select the original World/document.');await archive(scope,located);refresh();}
    catch(e){setError(message(e));}finally{busyRef.current=false;setBusy(false);}
  }
  if(state.error)return <section aria-label="Author World knowledge"><h3>Author World knowledge</h3><p role="alert">{state.error}</p><p>All saved bytes are retained. Fresh authoring is blocked.</p></section>;
  if(state.legacy){const l=state.legacy;
    return <section aria-label="Author World knowledge"><h3>Retained classic manual review</h3>
      <p>This original classic protocol is transitional. It will not be converted to native authoring.</p>{error&&<p role="alert">{error}</p>}
      <blockquote>{String(l.value.request.proposals[0].selection?.selectedText??'')}</blockquote>
      {l.value.receipt?<><p role="status">Original classic confirmation acknowledged.</p><button disabled={busy} onClick={()=>void archiveLegacy(l)}>Retain receipt and open native authoring</button></>:
        l.value.submitted?<><p>An earlier classic request may have committed. Only its original confirmation can be retried.</p><button disabled={busy} onClick={()=>void legacyRetry(l)}>Retry original classic confirmation</button></>:
        <><p>This old review was not submitted. No classic preparation or confirmation will be sent.</p><button disabled={busy} onClick={()=>void archiveLegacy(l)}>Archive unsubmitted classic review and refresh</button></>}
    </section>;
  }
  return <NativeManualKnowledge key={scopeKey} scope={scope} initial={state.native} getFresh={getFresh} isCurrent={isCurrent}
    getSelectedText={()=>{const e=current.current.session.editor;return e?e.state.doc.textBetween(e.state.selection.from,e.state.selection.to,' '):'';}}
    onBusyChange={props.onBusyChange} onRetained={(native:Located|null)=>setState({native,legacy:null,error:''})}/>;
}
