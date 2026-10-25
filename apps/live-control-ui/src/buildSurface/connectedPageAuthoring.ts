import {validConnectedPageIntent,type ConnectedPageIntent,type ConnectedPageOperation,canonicalConnectedIntent} from '../api/connectedPageApi';
import {queueSurfaceConversationRequest} from '../agentInteraction/surfaceConversationRequests';
import type {BuildComposeBridge} from './buildComposeBridge';
import type {SavedWorldBuildConversationContext} from '../agentInteraction/WorldAgentConversation';
export const connectedPageRecoveryKey=(world:string,document:string)=>'dmb:connected-page:v1:'+JSON.stringify([world,document]);
const reviewRecoveryKey=(world:string,document:string)=>'dmb:connected-page-review:v1:'+JSON.stringify([world,document]);
export function readConnectedPageRecovery(world:string,document:string):ConnectedPageIntent|null{
  const review=sessionStorage.getItem(reviewRecoveryKey(world,document));
  if(review!==null){const v=JSON.parse(review);if(Object.keys(v).sort().join(',')!=='owner_document_id,request,schema'||v.schema!=='dmb_connected_page_review_request_v1'||v.owner_document_id!==document||!validConnectedPageIntent(v.request)||v.request.world_id!==world||!('kind' in v.request.origin))throw new Error('The saved page review is unreadable; its bytes were kept.');if(sessionStorage.getItem(connectedPageRecoveryKey(world,document))!==null)throw new Error('Multiple retained page requests need review; their bytes were kept.');return v.request;}

  const raw=sessionStorage.getItem(connectedPageRecoveryKey(world,document));
  if(raw===null)return null;
  const value=JSON.parse(raw);
  if(Object.keys(value).sort().join(',')!=='request,schema'||value.schema!=='dmb_connected_page_request_v1'
    ||!validConnectedPageIntent(value.request)||value.request.world_id!==world||value.request.origin.document_id!==document)
    throw new Error('The saved page request could not be read. Its bytes were kept.');
  return value.request;
}
export function retainConnectedPageRequest(request:ConnectedPageIntent,ownerDocument=request.origin.document_id){
  if('kind' in request.origin){const prior=readConnectedPageRecovery(request.world_id,ownerDocument);if(prior&&canonicalConnectedIntent(prior)!==canonicalConnectedIntent(request))throw new Error('Resolve the existing page request first.');
    const key=reviewRecoveryKey(request.world_id,ownerDocument),bytes=JSON.stringify({schema:'dmb_connected_page_review_request_v1',owner_document_id:ownerDocument,request});sessionStorage.setItem(key,bytes);if(sessionStorage.getItem(key)!==bytes)throw new Error('The exact page review could not be retained. Nothing was sent.');return;}

  const key=connectedPageRecoveryKey(request.world_id,request.origin.document_id);
  const prior=readConnectedPageRecovery(request.world_id,request.origin.document_id);
  if(prior&&canonicalConnectedIntent(prior)!==canonicalConnectedIntent(request))throw new Error('Resolve the saved page request before starting another.');
  const bytes=JSON.stringify({schema:'dmb_connected_page_request_v1',request});
  sessionStorage.setItem(key,bytes);
  if(sessionStorage.getItem(key)!==bytes)throw new Error('This tab could not retain the exact page request. Nothing was sent.');
}
export function clearConnectedPageRequest(request:ConnectedPageIntent,ownerDocument=request.origin.document_id){
  const prior=readConnectedPageRecovery(request.world_id,ownerDocument);
  if(!prior||canonicalConnectedIntent(prior)!==canonicalConnectedIntent(request))throw new Error('The retained page request changed.');
  sessionStorage.removeItem('kind' in request.origin?reviewRecoveryKey(request.world_id,ownerDocument):connectedPageRecoveryKey(request.world_id,request.origin.document_id));
}
export function connectedPageBuildOutMessage(operation:ConnectedPageOperation){
  return `Build out this new page, ${operation.intent.title}. Replace only the selected starter sections with useful, grounded page writing. Keep the existing relationship declarations and Origin section. Use established details and my decisions as anchors, then propose concrete new details that make this place useful at the table: its layout, visible activity and practical work. Give the new material one clear proposed-details heading or note; write directly within that scope without repeating qualifications. Include a useful table of possible encounters or unfinished jobs when appropriate. Keep outcomes conditional and unplayed. Preserve meaningful uncertainty and my explicit brief; do not invent past events or advance anyone’s reaction.\n\nOriginal selected passage: ${operation.intent.origin.selected_text}\n${operation.intent.instructions?'Author’s brief: '+operation.intent.instructions:''}`;
}
export async function prepareConnectedPageScaffold(context:unknown,operation:ConnectedPageOperation){
  const {bridge,source}=context as {bridge:BuildComposeBridge;source:SavedWorldBuildConversationContext};
  const basis=operation.initial_source;
  if(!bridge||!source||!basis||source.worldId!==operation.intent.world_id||source.documentId!==basis.documentId
    ||source.revision!==basis.revision||source.contentSha256!==basis.contentSha256||source.dirty)
    throw new Error('This page has changed since creation. Select where to continue and ask Buddy in conversation.');
  const captured=await bridge.capture();
  if(captured.basis.document_id!==basis.documentId||captured.basis.registry_revision!==basis.revision
    ||captured.basis.content_sha256!==basis.contentSha256)throw new Error('The authoring destination changed.');
  let from:number|null=null,to:number|null=null;
  captured.editor.state.doc.descendants((node,pos)=>{
    if(node.type.name==='heading'&&node.textContent==='At a glance'&&from===null)from=pos;
    if(node.type.name==='heading'&&node.textContent==='Origin'&&from!==null&&to===null)to=pos;
  });
  if(from===null||to===null||from>=to||JSON.stringify(captured.editor.getJSON())!==captured.editorJson)
    throw new Error('The starter sections changed. Select where to continue in conversation.');
  captured.editor.commands.setTextSelection({from:from+1,to:to-1});
}
export function queueConnectedPageBuildOut(operation:ConnectedPageOperation){
  if(operation.phase!=='complete'||!operation.page)throw new Error('Finish the page connections before building it out.');
  const world=operation.intent.world_id,document=operation.page.document_id;
  const isCurrent=()=>{
    const query=new URLSearchParams(window.location.search);
    return window.location.pathname==='/build'&&query.get('world')===world&&query.get('documentId')===document;
  };
  queueSurfaceConversationRequest({id:'connected-page:'+operation.operation_id,worldId:world,surfaceId:'build',objectId:document,
    message:connectedPageBuildOutMessage(operation),clientThreadId:crypto.randomUUID(),turnId:crypto.randomUUID(),isCurrent,
    prepare:context=>prepareConnectedPageScaffold(context,operation)});
}
