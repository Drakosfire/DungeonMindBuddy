import {render,screen,waitFor,act,cleanup} from '@testing-library/react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {createBuildComposeBridge,type BuildComposeEditorState} from './buildComposeBridge';
import {BuildConstructionPreview} from './BuildConstructionPreview';
import type {BuildConstructionProgress} from '../api/buildConstructionStream';
let editor:Editor;
const scroll=vi.fn();
const priorScroll=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'scrollIntoView');
beforeEach(()=>{scroll.mockClear();Object.defineProperty(HTMLElement.prototype,'scrollIntoView',{value:scroll,configurable:true});Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Author page</p>'});document.body.append(editor.view.dom);});
afterEach(()=>{cleanup();editor.destroy();document.body.innerHTML='';if(priorScroll)Object.defineProperty(HTMLElement.prototype,'scrollIntoView',priorScroll);else delete (HTMLElement.prototype as any).scrollIntoView;});
it('grows outside the page JSON and retires when the author changes its basis',async()=>{
 const state:BuildComposeEditorState={editor,worldId:'world',documentId:'doc',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 const bridge=createBuildComposeBridge(()=>state,()=>undefined);const captured=await bridge.capture();const before=JSON.stringify(editor.getJSON());
 const progress={schema:'dmb_build_construction_v1',action_id:'action',reservation_sha256:'b'.repeat(64),conversation_id:'conversation',basis:captured.basis,
  origin:{client_turn_id:'client',durable_turn_id:'turn',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:'c'.repeat(64)},provider_attempt_id:'provider',sequence:1,status:'building',markdown:'| Name |\n| --- |\n| Nia |\n'} as BuildConstructionProgress;
 const view=render(<BuildConstructionPreview progress={progress} bridge={bridge} sourceKey="page"/>);
 await waitFor(()=>expect(screen.getByRole('cell',{name:'Nia'})).toBeTruthy());
 await waitFor(()=>expect(scroll).toHaveBeenCalledTimes(1));
 expect(scroll).toHaveBeenCalledWith({block:'center',behavior:'auto'});expect(JSON.stringify(editor.getJSON())).toBe(before);
 view.rerender(<BuildConstructionPreview progress={{...progress,sequence:2,markdown:progress.markdown+'| Jo |\n'}} bridge={bridge} sourceKey="page"/>);
 expect(screen.getByRole('cell',{name:'Jo'})).toBeTruthy();expect(scroll).toHaveBeenCalledTimes(1);expect(JSON.stringify(editor.getJSON())).toBe(before);
 act(()=>{editor.commands.insertContent('newer author text');state.draftGeneration++;});
 await waitFor(()=>expect(screen.queryByRole('table')).toBeNull());
 expect(JSON.stringify(editor.getJSON())).toContain('newer author text');
});

it('reveals received prose at its captured page location without taking composer focus',async()=>{
 const state:BuildComposeEditorState={editor,worldId:'world',documentId:'doc',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 const bridge=createBuildComposeBridge(()=>state,()=>undefined);const captured=await bridge.capture();const before=JSON.stringify(editor.getJSON());
 const composer=document.createElement('textarea');composer.value='A newer unsent message';document.body.append(composer);composer.focus();
 const progress={schema:'dmb_build_construction_v1',action_id:'action',reservation_sha256:'b'.repeat(64),conversation_id:'conversation',basis:captured.basis,
  origin:{client_turn_id:'client',durable_turn_id:'turn',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:'c'.repeat(64)},provider_attempt_id:'provider',sequence:1,status:'building',markdown:'# Workshop\n\nA small forge warms the room.\n'} as BuildConstructionProgress;
 const view=render(<BuildConstructionPreview progress={progress} bridge={bridge} sourceKey="page"/>);
 await screen.findByRole('heading',{name:'Workshop'});
 await waitFor(()=>expect(scroll).toHaveBeenCalledTimes(1));
 expect(document.activeElement).toBe(composer);expect(composer.value).toBe('A newer unsent message');
 expect(JSON.stringify(editor.getJSON())).toBe(before);
 view.rerender(<BuildConstructionPreview progress={{...progress,sequence:2,markdown:progress.markdown+'\n- Gather tools\n'}} bridge={bridge} sourceKey="page"/>);
 expect(screen.getByText('Gather tools')).toBeInTheDocument();expect(scroll).toHaveBeenCalledTimes(1);expect(document.activeElement).toBe(composer);
 view.rerender(<BuildConstructionPreview progress={{...progress,sequence:3,status:'incomplete'}} bridge={bridge} sourceKey="page"/>);
 expect(screen.getByRole('status')).toHaveTextContent('Incomplete');
 expect(JSON.stringify(editor.getJSON())).toBe(before);expect(composer.value).toBe('A newer unsent message');
});

it('grows inert typed plan rows at the captured location and retires on an editor change',async()=>{
 const state:BuildComposeEditorState={editor,worldId:'world',documentId:'doc',revision:1,contentSha256:'a'.repeat(64),visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
 const bridge=createBuildComposeBridge(()=>state,()=>undefined);const captured=await bridge.capture();const before=JSON.stringify(editor.getJSON());
 const composer=document.createElement('textarea');composer.value='Newer plan note';document.body.append(composer);composer.focus();
 const progress={schema:'dmb_build_plan_construction_v1' as const,placement_id:'placement',basis:captured.basis,
 world_id:'world',conversation_id:'conversation',client_turn_id:'client',durable_turn_id:'turn',turn_attempt:1,working_snapshot_sha256:'b'.repeat(64),provider_attempt_id:'provider',sequence:1,status:'building' as const,steps:[{text:'Discuss the lid.',kind:'discuss' as const}]};
 const view=render(<BuildConstructionPreview progress={progress} bridge={bridge} sourceKey="page"/>);
 await screen.findByRole('region',{name:'Plan construction'});expect(document.activeElement).toBe(composer);
 expect(JSON.stringify(editor.getJSON())).toBe(before);expect(screen.queryByRole('checkbox')).toBeNull();
 view.rerender(<BuildConstructionPreview progress={{...progress,sequence:2,steps:[...progress.steps,{text:'Prepare a check.',kind:'prepare_insertion'}]}} bridge={bridge} sourceKey="page"/>);
 expect(screen.getAllByRole('listitem')).toHaveLength(2);expect(document.activeElement).toBe(composer);
 act(()=>{editor.commands.insertContent('newer author text');state.draftGeneration++;});
 await waitFor(()=>expect(screen.queryByRole('region',{name:'Plan construction'})).toBeNull());
 expect(composer.value).toBe('Newer plan note');
});
