import {Editor} from '@tiptap/core';
import {webcrypto} from 'node:crypto';
import {afterEach,expect,it,vi} from 'vitest';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import {createBuildComposeBridge} from './buildComposeBridge';
import {prepareConnectedPageScaffold,readConnectedPageRecovery,retainConnectedPageRequest,connectedPageRecoveryKey} from './connectedPageAuthoring';
vi.stubGlobal('crypto',webcrypto);
afterEach(()=>sessionStorage.clear());
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
