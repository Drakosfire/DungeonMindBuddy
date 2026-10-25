import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {useOptionalMarkdownCanvasSession} from '../markdownCanvas/MarkdownCanvasSession';
import {getGraphObjectAuthoringKinds,postManagedWorldGraphProjection,prepareGraphObjectAuthoringWrite,commitGraphObjectAuthoringWrite} from '../api/liveApi';
import {verifyManagedWorldGraphProjectionResponse} from '../worldGraph/verifyManagedWorldGraphProjectionResponse';
import {graphDocumentRelationshipRequest} from '../api/graphDocumentRelationshipApi';
import type {WorldGraphProjectionNodeView} from '../api/types';
import {relationshipKey,readRelationshipReview,type RelationshipReview,type RelationshipSeed} from './buildRelationshipRecovery';
const message=(e:unknown)=>e instanceof Error?e.message:'Relationship review could not finish.';
export function BuildRelationshipReview({worldId,documentId,seed,onConsumed}:{worldId:string;documentId:string;seed:RelationshipSeed|null;onConsumed:()=>void}){
 const session=useOptionalMarkdownCanvasSession(),sessionRef=useRef(session);sessionRef.current=session;
 const key=relationshipKey(worldId,documentId),alive=useRef(true),busyRef=useRef(false),dialog=useRef<HTMLDialogElement>(null);
 const [initial]=useState(()=>{try{const raw=localStorage.getItem(key);return {raw,value:readRelationshipReview(raw,worldId,documentId),error:''};}catch(e){return {raw:null,value:null,error:message(e)};}});
 const rawRef=useRef(initial.raw),valueRef=useRef(initial.value);
 const [value,setValue]=useState(initial.value),[error,setError]=useState(initial.error),[open,setOpen]=useState(false),[busy,setBusy]=useState(false);
 const [nodes,setNodes]=useState<WorldGraphProjectionNodeView[]>([]),[kinds,setKinds]=useState<string[]>([]),[loaded,setLoaded]=useState(false);
 const exact=()=>{const s=sessionRef.current,i=valueRef.current?.intent;return alive.current&&!!i&&s?.record?.world_id===worldId&&s.record.document_id===documentId&&!s.dirty&&!s.activeCommand&&s.snapshot?.loaded_revision===i.document_source.revision&&s.snapshot.content_sha256===i.document_source.contentSha256;};
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 async function persist(change:(previous:RelationshipReview|null)=>RelationshipReview|null){
  if(initial.error)throw new Error(initial.error);
  if(!navigator.locks)throw new Error('This browser cannot retain a safe review across tabs. Nothing was sent.');
  await navigator.locks.request(key,()=>{
   if(!alive.current||sessionRef.current?.record?.world_id!==worldId||sessionRef.current?.record?.document_id!==documentId||localStorage.getItem(key)!==rawRef.current)throw new Error('This review changed or its page closed. Reload the page to reopen the retained review; nothing was overwritten.');
   const next=change(valueRef.current),raw=next?JSON.stringify(next):null;readRelationshipReview(raw,worldId,documentId);
   if(raw===null)localStorage.removeItem(key);else localStorage.setItem(key,raw);
   if(localStorage.getItem(key)!==raw)throw new Error('The exact review could not be retained. Nothing was sent.');
   rawRef.current=raw;valueRef.current=next;setValue(next);
  });
 }
 useEffect(()=>{if(!seed)return;if(seed.document_source.documentId!==documentId){onConsumed();return;}setOpen(true);if(!valueRef.current&&!initial.error){void persist(()=>({schema:'dmb_saved_relationship_review_v1',intent:{world_id:worldId,...seed,source:{node_id:null,label:'',kind:'npc'},target:{node_id:null,label:'',kind:'npc'},predicate:'',label:'',context:''},request:null,prepared:null,submitted:false,receipt:null})).catch(e=>setError(message(e)));}onConsumed();},[seed]);
 useEffect(()=>{if(open&&dialog.current&&!dialog.current.open)dialog.current.showModal();},[open]);
 useEffect(()=>{if(!open)return;let active=true;setLoaded(false);setNodes([]);setKinds([]);
  void Promise.all([postManagedWorldGraphProjection({schema:'dmb_managed_world_graph_projection_request_v1',managedWorldId:worldId}),getGraphObjectAuthoringKinds()]).then(([graph,catalog])=>{
   if(!active)return;
   const invalid=verifyManagedWorldGraphProjectionResponse({managedWorldId:worldId,request:{schema:'dmb_world_graph_projection_request_v1',worldId,campaignId:'',scopeMode:'world',focus:{kind:'none',sessionId:null},admissibility:'gm'},response:graph,revisionKind:'head'});
   if(invalid||!catalog.objectKinds.length)throw new Error(invalid||'World object kinds are unavailable.');setNodes(graph.projection.nodes);setKinds(catalog.objectKinds);setLoaded(true);
  }).catch(e=>{if(active)setError(message(e));});return()=>{active=false;};
 },[open,worldId]);
 function edit(change:(v:RelationshipReview)=>RelationshipReview){if(busyRef.current||valueRef.current?.request)return;void persist(v=>v?change(v):v).catch(e=>{if(alive.current)setError(message(e));});}
 async function preview(){if(busyRef.current)return;busyRef.current=true;setBusy(true);setError('');
  try{await persist(p=>p);if(!exact())throw new Error('Save the page and select its current saved passage before previewing.');let v=valueRef.current!;
   if(!v.request){const request=await graphDocumentRelationshipRequest(v.intent);if(!exact())throw new Error('The page changed while preparing review. Nothing was published.');await persist(p=>p?{...p,request}:p);v=valueRef.current!;}
   if(v.submitted)throw new Error('Recover the exact confirmation instead of preparing another.');
   const prepared=await prepareGraphObjectAuthoringWrite(v.request!);if(!alive.current)return;
   if(!prepared.prepared||prepared.campaign_id!==worldId||!prepared.world_id||!prepared.authority_operation_id||prepared.expressibility!=='EXPRESSIBLE'||!prepared.confirm_token)throw new Error('This relationship cannot be published. Review its predicate and identities.');
   await persist(p=>p?{...p,prepared}:p);
  }catch(e){if(alive.current)setError(message(e));}finally{busyRef.current=false;if(alive.current)setBusy(false);}
 }
 async function confirm(){if(busyRef.current||!valueRef.current?.prepared||valueRef.current.receipt)return;busyRef.current=true;setBusy(true);setError('');
  try{let v=valueRef.current;if(!v.submitted&&!exact())throw new Error('The source changed. Review the current saved page before confirming.');
   await persist(p=>p?{...p,submitted:true}:p);v=valueRef.current!;
   const receipt=await commitGraphObjectAuthoringWrite({...v.request!,confirmToken:v.prepared!.confirm_token!,currentOverlayToken:v.prepared!.current_overlay_token});
   if(!receipt.committed||receipt.campaign_id!==worldId||receipt.world_id!==v.prepared!.world_id||receipt.operation_id!==v.prepared!.authority_operation_id||!receipt.published_revision_id)throw new Error('Publication was not acknowledged. Retry only the retained confirmation.');
   if(alive.current)await persist(p=>p?{...p,receipt}:p);
  }catch(e){if(alive.current)setError(message(e)+' The exact request is retained.');}finally{busyRef.current=false;if(alive.current)setBusy(false);}
 }
 const endpoint=(side:'source'|'target')=>{const e=value!.intent[side];return <fieldset><legend>{side==='source'?'From':'To'}</legend>
  <label>{side} identity<select value={e.node_id??'__new__'} onChange={event=>{const n=nodes.find(n=>n.nodeId===event.target.value);edit(v=>({...v,intent:{...v.intent,[side]:n?{node_id:n.nodeId,label:n.label,kind:n.kind}:{node_id:null,label:'',kind:'npc'}}}));}}><option value="__new__">Create a new identity</option>{nodes.map(n=><option key={n.nodeId} value={n.nodeId}>{n.label} · {n.kind} · {n.nodeId}</option>)}</select></label>
  {!e.node_id&&<><label>{side} name<input value={e.label} onChange={event=>{const label=event.target.value;edit(v=>({...v,intent:{...v.intent,[side]:{...v.intent[side],label}}}));}}/></label>
  <label>{side} kind<select value={e.kind} onChange={event=>{const kind=event.target.value;edit(v=>({...v,intent:{...v.intent,[side]:{...v.intent[side],kind}}}));}}>{kinds.map(k=><option key={k} value={k}>{k}</option>)}</select></label></>}
 </fieldset>;};
 return <>{!open&&value&&<aside className="connected-page-recovery"><button type="button" onClick={()=>setOpen(true)}>Resume relationship review</button></aside>}
 {!open&&error&&<p role="alert">{error}</p>}
 {open&&createPortal(<dialog ref={dialog} className="connected-page-dialog" aria-label="Review relationship" onCancel={()=>setOpen(false)} onClose={()=>setOpen(false)}><header><h2>Relationship</h2><button type="button" aria-label="Close relationship review" onClick={()=>setOpen(false)}>×</button></header>
 {error&&<p role="alert">{error}</p>}{value&&<>
 {!value.request?<fieldset disabled={busy||!loaded||!!initial.error}><legend>Saved passage and relationship</legend>
 <label>Supporting passage<textarea value={value.intent.quote} onChange={event=>{const quote=event.target.value;edit(v=>({...v,intent:{...v.intent,quote}}));}}/></label>
 {endpoint('source')}{endpoint('target')}
 {(['predicate','label','context'] as const).map(field=><label key={field}>{field==='predicate'?'Relationship type':field==='label'?'Readable relationship':'Context, including when'}<textarea value={value.intent[field]} onChange={event=>{const text=event.target.value;edit(v=>({...v,intent:{...v.intent,[field]:text}}));}}/></label>)}
 <p>Describe the relationship in this passage. Include past or conditional context explicitly. Confirming will publish this author-reviewed assertion to the World.</p>
 <button type="button" onClick={()=>void preview()}>Preview relationship</button></fieldset>:<>
 <blockquote>{value.intent.quote}</blockquote><p>{value.intent.source.label} → {value.intent.label} ({value.intent.predicate}) → {value.intent.target.label}</p><p>Saved relationship label: {value.intent.label} — {value.intent.context}</p>
 {value.prepared?.assertions_preview.map(row=><p key={row.assertion_id}>{row.summary}</p>)}
 {value.receipt?<p role="status">Relationship published to the World.</p>:value.prepared?<button type="button" disabled={busy||!!initial.error} onClick={()=>void confirm()}>{value.submitted?'Retry exact confirmation':'Confirm relationship'}</button>:<button type="button" disabled={busy||!!initial.error} onClick={()=>void preview()}>Retry exact preview</button>}
 </>}
 {!value.submitted&&value.request&&<button type="button" disabled={busy||!loaded} onClick={()=>void persist(p=>p?{...p,request:null,prepared:null}:p).catch(e=>setError(message(e)))}>Edit relationship</button>}
 {!value.submitted&&<button type="button" disabled={busy||!!initial.error} onClick={()=>void persist(()=>null).then(()=>setOpen(false)).catch(e=>setError(message(e)))}>Discard review</button>}
 {value.receipt&&<button type="button" disabled={busy} onClick={()=>void persist(()=>null).then(()=>setOpen(false)).catch(e=>setError(message(e)))}>Done</button>}
 </>}
 </dialog>,document.body)}</>;
}
