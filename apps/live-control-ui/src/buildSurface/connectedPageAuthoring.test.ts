import {claimSurfaceConversationRequest,acceptSurfaceConversationRequest,cancelSurfaceConversationRequest} from '../agentInteraction/surfaceConversationRequests';
import {Editor} from '@tiptap/core';
import {webcrypto} from 'node:crypto';
import {afterEach,expect,it,vi} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {createBuildComposeBridge} from './buildComposeBridge';
import {prepareConnectedPageScaffold,readConnectedPageRecovery,retainConnectedPageRequest,connectedPageRecoveryKey,connectedPageBuildOutMessage,queueConnectedPageBuildOut} from './connectedPageAuthoring';
vi.stubGlobal('crypto',webcrypto);
afterEach(()=>{sessionStorage.clear();window.history.replaceState({},'', '/');cancelSurfaceConversationRequest('connected-page:11111111-1111-4111-8111-111111111111');});
it('selects only starter sections while preserving relationship and origin content',async()=>{
 const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<h1>Forge</h1><p>Brin owns Forge.</p><h2>At a glance</h2><p>Write here</p><h2>Origin</h2><p>Source passage</p>'});
 try{
  const current={editor,worldId:'world-a',documentId:'new-page',revision:2,contentSha256:'a'.repeat(64),visibility:'internal' as const,draftGeneration:0,selectionGeneration:0,canEdit:true};
  const bridge=createBuildComposeBridge(()=>current,()=>{}),before=editor.getJSON();
  await prepareConnectedPageScaffold({bridge,source:{worldId:'world-a',documentId:'new-page',revision:2,contentSha256:'a'.repeat(64),dirty:false}},
   {intent:{world_id:'world-a'},initial_source:{documentId:'new-page',revision:2,contentSha256:'a'.repeat(64)}} as any);
  const selection=editor.state.doc.textBetween(editor.state.selection.from,editor.state.selection.to,'\n');
  expect(selection).toContain('At a glance');expect(selection).toContain('Write here');expect(selection).not.toContain('Brin owns');expect(selection).not.toContain('Source passage');expect(editor.getJSON()).toEqual(before);
  const captured=await bridge.capture();const proposal=await bridge.prepareProposal(captured,'## Workshop\n\nUseful new writing.');bridge.applyPrepared(proposal);
  const result=tiptapJsonToSemanticMarkdown(editor.getJSON());expect(result).toContain('Brin owns Forge.');expect(result).toContain('## Origin');expect(result).toContain('Source passage');expect(result).toContain('## Workshop');expect(result).not.toContain('Write here');
  await expect(prepareConnectedPageScaffold({bridge,source:{worldId:'world-a',documentId:'new-page',revision:3,dirty:true}},
   {intent:{world_id:'world-a'},initial_source:{documentId:'new-page',revision:2,contentSha256:'a'.repeat(64)}} as any)).rejects.toThrow('changed');
 }finally{editor.destroy();}
});
it('preserves malformed recovery bytes and refuses to overwrite them',()=>{
 const key=connectedPageRecoveryKey('world-a','source');sessionStorage.setItem(key,'broken-json');
 expect(()=>readConnectedPageRecovery('world-a','source')).toThrow();expect(sessionStorage.getItem(key)).toBe('broken-json');
 expect(()=>retainConnectedPageRequest({world_id:'world-a',origin:{document_id:'source'}} as any)).toThrow();expect(sessionStorage.getItem(key)).toBe('broken-json');
});

it('carries the author brief and exact origin into an explicitly creative buildout request',()=>{
 const message=connectedPageBuildOutMessage({intent:{title:'Forge',origin:{selected_text:'The bell signals when the gate opens.'},instructions:'Preserve this condition; do not make Brin react.'}} as any);
 expect(message).toContain('Original selected passage: The bell signals when the gate opens.');
 expect(message).toContain('Author’s brief: Preserve this condition; do not make Brin react.');
 expect(message).toContain('Keep the existing relationship declarations and Origin section.');
 expect(message).toContain('propose concrete new details');expect(message).toContain('Keep outcomes conditional and unplayed.');
});


const operation=()=>({operation_id:'11111111-1111-4111-8111-111111111111',phase:'complete',
 page:{document_id:'22222222-2222-4222-8222-222222222222'},
 intent:{world_id:'world-a',title:'Forge',origin:{selected_text:'Forge repairs lanterns.'},instructions:'Keep outcomes unplayed.'},
 initial_source:{documentId:'22222222-2222-4222-8222-222222222222',revision:2,contentSha256:'a'.repeat(64)}} as any);

it.each(['campaign=world-a','world=world-a&campaign=world-a'])('queues the exact saved page for %s with stable retry IDs',async query=>{
 const op=operation(),accepted=vi.fn(),id='connected-page:'+op.operation_id;
 window.history.replaceState({},'', '/build?documentId='+op.page.document_id+'&'+query);
 queueConnectedPageBuildOut(op,accepted);
 const first=claimSurfaceConversationRequest(id)!;
 expect(first.worldId).toBe('world-a');expect(first.objectId).toBe(op.page.document_id);
 expect(first.message).toContain('Develop this saved page');expect(first.isCurrent()).toBe(true);
 expect(accepted).not.toHaveBeenCalled();
 acceptSurfaceConversationRequest(id);expect(accepted).toHaveBeenCalledOnce();
 queueConnectedPageBuildOut(op);const retry=claimSurfaceConversationRequest(id)!;
 expect(retry.clientThreadId).toBe(first.clientThreadId);expect(retry.turnId).toBe(first.turnId);
});

it.each(['/build?world=other&documentId=22222222-2222-4222-8222-222222222222',
 '/build?campaign=world-a&documentId=other','/play?documentId=22222222-2222-4222-8222-222222222222'])('refuses a changed destination %s before queueing',url=>{
 window.history.replaceState({},'',url);
 expect(()=>queueConnectedPageBuildOut(operation())).toThrow('destination changed');
 expect(claimSurfaceConversationRequest('connected-page:'+operation().operation_id)).toBeNull();
});

it.each(['world','page','revision','digest','dirty'])('keeps the actual compose boundary closed for a changed %s',async change=>{
 const op=operation(),editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<h1>Forge</h1><h2>At a glance</h2><p>Starter</p><h2>Origin</h2><p>Quote</p>'});
 const current={editor,worldId:'world-a',documentId:op.page.document_id,revision:2,contentSha256:'a'.repeat(64),visibility:'internal' as const,draftGeneration:0,selectionGeneration:0,canEdit:true};
 const source={worldId:current.worldId,documentId:current.documentId,revision:2,contentSha256:current.contentSha256,dirty:false};
 if(change==='world')source.worldId='other';if(change==='page')source.documentId='other';
 if(change==='revision')source.revision=3;if(change==='digest')source.contentSha256='b'.repeat(64);if(change==='dirty')source.dirty=true;
 try{const before=editor.getJSON();await expect(prepareConnectedPageScaffold({bridge:createBuildComposeBridge(()=>current,()=>{}),source},op)).rejects.toThrow('changed');expect(editor.getJSON()).toEqual(before);}
 finally{editor.destroy();}
});
