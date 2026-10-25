import {useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
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
  const [position,setPosition]=useState<{left:number;top:number}|null>(null);
  useEffect(()=>{
    if(!editor)return;
    const update=()=>{
      if(editor.isDestroyed||!editor.isEditable||editor.state.selection.empty){setPosition(null);return;}
      try{
        const rect=editor.view.coordsAtPos(editor.state.selection.from);
        if(rect.bottom<0||rect.top>window.innerHeight){setPosition(null);return;}
        setPosition({left:Math.max(8,Math.min(rect.left,window.innerWidth-210)),top:Math.max(8,Math.min(rect.bottom+6,window.innerHeight-48))});
      }catch{setPosition(null);}
    };
    editor.on('selectionUpdate',update);editor.on('update',update);
    window.addEventListener('scroll',update,true);window.addEventListener('resize',update);
    update();return()=>{editor.off('selectionUpdate',update);editor.off('update',update);
      window.removeEventListener('scroll',update,true);window.removeEventListener('resize',update);};
  },[editor]);
  if(!position||!actions.length)return null;
  return createPortal(<div className="surface-selection-actions" role="toolbar" aria-label="Selected passage actions" style={position}>
    {actions.map(action=><button key={action.id} type="button" onMouseDown={event=>event.preventDefault()} onClick={action.invoke}>{action.label}</button>)}
  </div>,document.body);
}
