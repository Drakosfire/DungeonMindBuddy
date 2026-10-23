import {useEffect,useRef,useState} from 'react';
import {commitGraphObjectAuthoringWrite,postManagedWorldGraphProjection,prepareGraphObjectAuthoringWrite} from '../api/liveApi';
import {getWorldbuildingFrozenSpans} from '../api/extractPromoteApi';
import type {ExactRunReviewPackage,ExtractionRunRecord,GraphObjectAuthoringProposalPayload,GraphReviewHandoffPayload,WorkspaceDocumentRecord,WorldbuildingFrozenSpanCatalog,WorldGraphProjectionNodeView} from '../api/types';
import {verifyManagedWorldGraphProjectionResponse} from '../worldGraph/verifyManagedWorldGraphProjectionResponse';
import {useMarkdownCanvasSession} from '../markdownCanvas/MarkdownCanvasSession';
import {buildGraphObjectAuthoringProposal,buildGraphObjectAuthoringRelationshipProposal,buildObjectRefFromInspectedNode,
  createDefaultGraphObjectAuthoringFormState,createDefaultGraphObjectAuthoringRelationshipFormState,
  GRAPH_OBJECT_AUTHORING_KIND_OPTIONS,serializeGraphObjectAuthoringProposalForApi} from '../planSurface/graphReviewWorkbench/graphObjectAuthoringDraft';
import type {GraphAuthoringSelection} from '../planSurface/graphReviewWorkbench/graphAuthoringSelection';
import {validFrozenCatalog} from './WorldbuildingEvidenceCorrection';
import {knowledgeKey,readKnowledgeRecovery,selectionForFrozenText,type ManualKnowledgeRecovery,type ManualKnowledgeScope} from './buildManualKnowledge';

type Props={worldId:string;document:WorkspaceDocumentRecord;run:ExtractionRunRecord;handoff:GraphReviewHandoffPayload;
  review:ExactRunReviewPackage;sourceContentSha256:string;isScopeCurrent:()=>boolean};
const message=(e:unknown)=>e instanceof Error?e.message:'Manual knowledge could not be prepared.';

/** Build adapter only: shared proposal grammar and the governed prepare/confirm owner do the writing. */
export function BuildManualKnowledge(props:Props){
  const session=useMarkdownCanvasSession();
  const scope:ManualKnowledgeScope={worldId:props.worldId,documentId:props.document.document_id,
    revision:props.handoff.document_revision,hash:props.sourceContentSha256.replace(/^sha256:/,''),
    runId:props.run.run_id,artifactId:props.run.source_artifact_id};
  const key=knowledgeKey(scope),alive=useRef(true),busyRef=useRef(false),rawRef=useRef<string|null>(null);
  const [catalog,setCatalog]=useState<WorldbuildingFrozenSpanCatalog|null>(null);
  const [nodes,setNodes]=useState<WorldGraphProjectionNodeView[]>([]),[error,setError]=useState('');
  const [busy,setBusy]=useState(false),[reload,setReload]=useState(0);
  const [recovery,setRecovery]=useState<ManualKnowledgeRecovery|null>(()=>{
    try{const raw=localStorage.getItem(key);rawRef.current=raw;return readKnowledgeRecovery(raw,scope);}
    catch{return null;}
  });
  const [storageError]=useState(()=>{try{readKnowledgeRecovery(localStorage.getItem(key),scope);return '';}catch(e){return message(e);}});
  const [selection,setSelection]=useState<GraphAuthoringSelection|null>(null);
  const [mode,setMode]=useState('object'),[label,setLabel]=useState(''),[kind,setKind]=useState('npc'),[summary,setSummary]=useState('');
  const [source,setSource]=useState(''),[target,setTarget]=useState(''),[predicate,setPredicate]=useState('located_in');
  const current=useRef({session,props,scope,key});current.current={session,props,scope,key};
  function exact(){const c=current.current,s=c.session;
    return alive.current&&c.key===key&&c.props.isScopeCurrent()&&!s.dirty&&['ready_clean','committed'].includes(s.phase)
      &&s.record?.document_id===scope.documentId&&s.record.world_id===scope.worldId&&s.record.kind==='worldbuilding_source'
      &&s.snapshot?.loaded_revision===scope.revision&&s.snapshot.content_sha256?.replace(/^sha256:/,'')===scope.hash
      &&props.run.status==='reviewable'&&props.run.source_domain==='worldbuilding'
      &&props.handoff.extraction_run_id===scope.runId&&props.handoff.source_artifact_id===scope.artifactId
      &&props.handoff.document_id===scope.documentId;
  }
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  useEffect(()=>{let active=true;setCatalog(null);setNodes([]);setError('');
    void Promise.all([getWorldbuildingFrozenSpans(scope.runId),postManagedWorldGraphProjection({schema:'dmb_managed_world_graph_projection_request_v1',managedWorldId:scope.worldId})]).then(([spans,graph])=>{
      if(!active||!props.isScopeCurrent())return;
      const graphError=verifyManagedWorldGraphProjectionResponse({managedWorldId:scope.worldId,
        request:{schema:'dmb_world_graph_projection_request_v1',worldId:scope.worldId,campaignId:'',scopeMode:'world',focus:{kind:'none',sessionId:null},admissibility:'gm'},
        response:graph,revisionKind:'head'});
      if(!validFrozenCatalog(spans,props.review,props.run,scope.worldId)||graphError)throw new Error(graphError||'Frozen source does not match this review.');
      setCatalog(spans);setNodes(graph.projection.nodes);
    }).catch(e=>{if(active)setError(message(e));});return()=>{active=false;};
  },[key,reload]);
  async function store(next:ManualKnowledgeRecovery|null,requireCurrent=true){
    if(!navigator.locks)throw new Error('This browser cannot safely retain manual authoring across tabs. No request was sent.');
    await navigator.locks.request(key,()=>{
      if((requireCurrent&&!exact())||localStorage.getItem(key)!==rawRef.current)throw new Error('The source or saved authoring changed. Reopen this review; the request is retained.');
      const raw=next===null?null:JSON.stringify(next);
      readKnowledgeRecovery(raw,scope);
      if(raw===null)localStorage.removeItem(key);else localStorage.setItem(key,raw);
      if(localStorage.getItem(key)!==raw)throw new Error('The authoring request could not be retained. No request was sent.');
      rawRef.current=raw;
    });
    if(alive.current&&current.current.key===key)setRecovery(next);
  }
  function choose(text:string){try{if(!exact()||!catalog)throw new Error('Save the current document and open its matching extraction first.');
    const selected=selectionForFrozenText(scope,catalog,text);setSelection(selected);setLabel(selected.normalizedSelectedText);setError('');
  }catch(e){setError(message(e));}}
  async function prepare(){if(busyRef.current)return;busyRef.current=true;setBusy(true);setError('');
    try{if(!exact()||!catalog)throw new Error('Save the document and reopen its exact extraction.');
      let retained=recovery;
      if(!retained){if(!selection)throw new Error('Choose source text first.');
        const selected=selectionForFrozenText(scope,catalog,selection.selectedText);
        let proposal;
        if(mode==='object'){if(!label.trim())throw new Error('Give the object a name.');
          proposal=buildGraphObjectAuthoringProposal(selected,{...createDefaultGraphObjectAuthoringFormState(selected),label,kind,summary});
        }else{const from=nodes.find(n=>n.nodeId===source),to=nodes.find(n=>n.nodeId===target);
          if(!from||!to||source===target)throw new Error('Choose two different current World objects.');
          const ref=(n:WorldGraphProjectionNodeView)=>buildObjectRefFromInspectedNode({node_id:n.nodeId,label:n.label,kind:n.kind,role:n.role});
          proposal=buildGraphObjectAuthoringRelationshipProposal({...createDefaultGraphObjectAuthoringRelationshipFormState(),
            sourceObjectRef:ref(from),targetObjectRef:ref(to),relationshipType:predicate,summary},selected);
          if(!proposal)throw new Error('Choose a valid relationship.');
        }
        retained={schema:'dmb_build_manual_knowledge_v1',scope,request:{worldId:scope.worldId,campaignId:scope.worldId,sourceRunId:scope.runId,
          proposals:[serializeGraphObjectAuthoringProposalForApi(proposal) as unknown as GraphObjectAuthoringProposalPayload]},prepared:null,submitted:false,receipt:null};
        await store(retained);
      }
      if(retained.submitted||retained.receipt)throw new Error('Recover the retained confirmation instead of preparing another request.');
      if(!exact())throw new Error('The source changed before preview. The request is retained.');
      const result=await prepareGraphObjectAuthoringWrite(retained.request);
      if(result.expressibility!=='EXPRESSIBLE'||!result.confirm_token)throw new Error('This proposal cannot be published.');
      await store({...retained,prepared:result},false);
    }catch(e){if(alive.current)setError(message(e));}finally{busyRef.current=false;if(alive.current)setBusy(false);}
  }
  async function confirm(){if(busyRef.current||!recovery?.prepared||recovery.receipt)return;busyRef.current=true;setBusy(true);setError('');
    try{if(!exact())throw new Error('Save the document and reopen its exact extraction before confirming.');
      const retained={...recovery,submitted:true};await store(retained);
      if(!exact())throw new Error('The source changed before confirmation. The request is retained.');
      const result=await commitGraphObjectAuthoringWrite({...retained.request,confirmToken:retained.prepared!.confirm_token,currentOverlayToken:retained.prepared!.current_overlay_token});
      if(!result.committed)throw new Error('Publication was not acknowledged. The exact request is retained.');
      await store({...retained,receipt:result},false);if(alive.current&&props.isScopeCurrent())setReload(n=>n+1);
    }catch(e){if(alive.current)setError(message(e)+' The exact request is retained for retry.');}finally{busyRef.current=false;if(alive.current)setBusy(false);}
  }
  function nodeCaption(node:WorldGraphProjectionNodeView){
    const detail=[node.kind,node.role!==node.kind?node.role:null,node.summary].filter(Boolean).join(' · ');
    return node.label+(detail?' · '+detail:'')+(nodes.filter(n=>n.label===node.label).length>1?' · '+node.nodeId:'');
  }
  function endpointCaption(ref:Record<string,unknown>|null|undefined){
    const node=nodes.find(n=>n.nodeId===ref?.nodeId);
    return node?nodeCaption(node):String(ref?.label??'Unavailable object')+' · '+String(ref?.nodeId??'');
  }
  const ready=exact()&&!storageError&&!busy&&!!catalog;
  return <section aria-label="Author World knowledge" className="graph-object-authoring-surface">
    <h3>Author World knowledge</h3><p>Choose saved source text, declare an object or relationship, then review and confirm it.</p>
    {!exact()&&<p role="status">Save the document and reopen the extraction matching its current saved revision before authoring.</p>}
    {storageError&&<p role="alert">{storageError}</p>}{error&&<p role="alert">{error}</p>}
    {!catalog&&!error&&<p role="status">Reading frozen source passages…</p>}
    {!recovery&&<fieldset disabled={!ready}><legend>Source and assertion</legend>
      <button type="button" onClick={()=>{const editor=session.editor;choose(editor?editor.state.doc.textBetween(editor.state.selection.from,editor.state.selection.to,' '):'');}}>Use selected document text</button>
      <details><summary>Choose a saved passage</summary>{catalog?.spans.map(span=><div key={span.sourceSpanRefId}>
        <p>{span.paragraphText}</p><button type="button" onClick={()=>choose(span.paragraphText)}>Use passage · lines {span.startLine}–{span.endLine}</button></div>)}</details>
      {selection&&<blockquote>{selection.selectedText}</blockquote>}
      <label>Declare <select value={mode} onChange={e=>setMode(e.target.value)}><option value="object">Object</option><option value="relationship">Relationship</option></select></label>
      {mode==='object'?<><label>Name<input value={label} onChange={e=>setLabel(e.target.value)}/></label>
        <label>Kind<select value={kind} onChange={e=>setKind(e.target.value)}>{GRAPH_OBJECT_AUTHORING_KIND_OPTIONS.map(k=><option key={k}>{k}</option>)}</select></label></>
      :<><label>From<select value={source} onChange={e=>setSource(e.target.value)}><option value="">Choose object</option>{nodes.map(n=><option key={n.nodeId} value={n.nodeId}>{nodeCaption(n)}</option>)}</select></label>
        <label>Relationship<input value={predicate} onChange={e=>setPredicate(e.target.value)}/></label>
        <label>To<select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Choose object</option>{nodes.map(n=><option key={n.nodeId} value={n.nodeId}>{nodeCaption(n)}</option>)}</select></label></>}
      <label>Description<textarea value={summary} onChange={e=>setSummary(e.target.value)}/></label>
      <button type="button" disabled={!selection} onClick={()=>void prepare()}>Preview World change</button>
    </fieldset>}
    {recovery&&!recovery.receipt&&<><blockquote>{String(recovery.request.proposals[0].selection?.selectedText??'')}</blockquote>
      {recovery.prepared?<>{recovery.request.proposals[0].proposalKind==='relationship'&&<dl>
        <dt>From</dt><dd>{endpointCaption(recovery.request.proposals[0].sourceObjectRef)}</dd>
        <dt>Relationship</dt><dd>{recovery.request.proposals[0].relationshipType}</dd>
        <dt>To</dt><dd>{endpointCaption(recovery.request.proposals[0].targetObjectRef)}</dd></dl>}
        <ul>{recovery.prepared.assertions_preview.map(row=><li key={row.assertion_id}>{row.summary}</li>)}</ul>
        <p>Confirming publishes this reviewed assertion to the World. Your source document stays unchanged.</p>
        <button type="button" disabled={!ready} onClick={()=>void confirm()}>{recovery.submitted?'Retry exact confirmation':'Confirm World change'}</button></>
        :<button type="button" disabled={!ready} onClick={()=>void prepare()}>Retry exact preview</button>}
      {!recovery.submitted&&<button type="button" disabled={!ready} onClick={()=>void store(null).catch(e=>setError(message(e)))}>Edit proposal</button>}
    </>}
    {recovery?.receipt&&<><p role="status">World knowledge published. It is available for cited retrieval.</p>
      <button type="button" disabled={!ready} onClick={()=>void store(null).then(()=>{setSelection(null);setSummary('');}).catch(e=>setError(message(e)))}>Author another assertion</button></>}
  </section>;
}
