import {useEffect,useMemo,useState,useId} from 'react';
import {useOptionalSurfaceContext} from './contextHost/useSurfaceContext';
import type {Editor} from '@tiptap/core';
import {TextSelection} from '@tiptap/pm/state';
import './SurfaceSelectionActions.css';

export interface SurfaceTextCapture {editor_json:string;editor_sha256:string;selection_from:number;selection_to:number;selected_text:string}
export async function captureSurfaceTextSelection(editor:Editor, isCurrent:()=>boolean):Promise<SurfaceTextCapture>{
  const selection=editor.state.selection;
  if(!(selection instanceof TextSelection)||selection.empty||selection.$from.parent!==selection.$to.parent
    ||!['paragraph','heading'].includes(selection.$from.parent.type.name))throw new Error('Select text within one paragraph or heading.');
  let textOnly=true;selection.$from.parent.forEach(child=>{if(!child.isText)textOnly=false;});
  if(!textOnly)throw new Error('Choose a paragraph or heading containing text.');
  const editor_json=JSON.stringify(editor.getJSON());
  const selected_text=editor.state.doc.textBetween(selection.from,selection.to,'\n');
  if(!selected_text.trim())throw new Error('Select the name or passage for the new page.');
  const editor_sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(editor_json))),b=>b.toString(16).padStart(2,'0')).join('');
  if(!isCurrent()||editor.isDestroyed||JSON.stringify(editor.getJSON())!==editor_json
    ||editor.state.selection.from!==selection.from||editor.state.selection.to!==selection.to)
    throw new Error('The page or selection changed. Select the passage again.');
  return {editor_json,editor_sha256,selection_from:selection.from,selection_to:selection.to,selected_text};
}

/** Shared presentation: owning Surface adapters provide implemented actions and capture authority. */
export function SurfaceSelectionActions({editor,actions}:{editor:Editor|null;actions:readonly {id:string;label:string;invoke:()=>void}[]}){
  const [available,setAvailable]=useState(false),id=useId();
  const context=useOptionalSurfaceContext();
  const register=context?.registerContribution;
  useEffect(()=>{
    if(!editor){setAvailable(false);return;}
    const update=()=>setAvailable(!editor.isDestroyed&&editor.isEditable&&!editor.state.selection.empty);
    const retire=()=>setAvailable(false);
    editor.on('selectionUpdate',update);editor.on('update',update);editor.on('destroy',retire);
    update();return()=>{editor.off('selectionUpdate',update);editor.off('update',update);editor.off('destroy',retire);};
  },[editor]);
  const content=useMemo(()=>available&&actions.length?<div className="surface-selection-actions" role="toolbar" aria-label="Selected passage actions">
    {actions.map(action=><button key={action.id} type="button" onMouseDown={event=>event.preventDefault()} onClick={action.invoke}>{action.label}</button>)}
  </div>:null,[available,actions]);
  useEffect(()=>{
    if(!register||!editor||!content)return;
    return register({id:`selection-${id}`,order:45,surfaceIdentity:{surfaceId:'build',instanceKey:`selection-${id}`},content});
  },[register,editor,content,id]);
  return null;
}
