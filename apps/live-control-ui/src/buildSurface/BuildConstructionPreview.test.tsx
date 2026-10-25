import {render,screen,waitFor,act,cleanup} from '@testing-library/react';
import {beforeEach,afterEach,it,expect} from 'vitest';
import {webcrypto} from 'node:crypto';
import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {createBuildComposeBridge,type BuildComposeEditorState} from './buildComposeBridge';
import {BuildConstructionPreview} from './BuildConstructionPreview';
import type {BuildConstructionProgress} from '../api/buildConstructionStream';
let editor:Editor;
beforeEach(()=>{Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Author page</p>'});document.body.append(editor.view.dom);});
afterEach(()=>{cleanup();editor.destroy();document.body.innerHTML='';});
it('grows outside the page JSON and retires when the author changes its basis',async()=>{
 const state:BuildComposeEditorState={editor,worldId:'world',documentId:'doc',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 const bridge=createBuildComposeBridge(()=>state,()=>undefined);const captured=await bridge.capture();const before=JSON.stringify(editor.getJSON());
 const progress={schema:'dmb_build_construction_v1',action_id:'action',reservation_sha256:'b'.repeat(64),conversation_id:'conversation',basis:captured.basis,
  origin:{client_turn_id:'client',durable_turn_id:'turn',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:'c'.repeat(64)},provider_attempt_id:'provider',sequence:1,status:'building',markdown:'| Name |\n| --- |\n| Nia |\n'} as BuildConstructionProgress;
 const view=render(<BuildConstructionPreview progress={progress} bridge={bridge} sourceKey="page"/>);
 await waitFor(()=>expect(screen.getByRole('cell',{name:'Nia'})).toBeTruthy());expect(JSON.stringify(editor.getJSON())).toBe(before);
 view.rerender(<BuildConstructionPreview progress={{...progress,sequence:2,markdown:progress.markdown+'| Jo |\n'}} bridge={bridge} sourceKey="page"/>);
 expect(screen.getByRole('cell',{name:'Jo'})).toBeTruthy();expect(JSON.stringify(editor.getJSON())).toBe(before);
 act(()=>{editor.commands.insertContent('newer author text');state.draftGeneration++;});
 await waitFor(()=>expect(screen.queryByRole('table')).toBeNull());
 expect(JSON.stringify(editor.getJSON())).toContain('newer author text');
});
