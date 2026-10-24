import {useEffect,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import type {Editor} from '@tiptap/core';
import {Plugin,PluginKey} from '@tiptap/pm/state';
import {Decoration,DecorationSet} from '@tiptap/pm/view';
import './SurfacePageProposal.css';

/** Inert page-adjacent review: widget DOM is never document content or undo history. */
export function SurfacePageProposal({editor,position,editorJson,children,onStale}: {
  editor:Editor;position:number;editorJson:string;children:ReactNode;onStale:()=>void;
}) {
  const [host,setHost]=useState<HTMLDivElement|null>(null);
  const stale=useRef(onStale);stale.current=onStale;
  useEffect(()=>{
    if(editor.isDestroyed)return;
    if(JSON.stringify(editor.getJSON())!==editorJson){stale.current();return;}
    const target=document.createElement('div');target.className='surface-page-proposal';target.contentEditable='false';
    target.setAttribute('role','region');target.setAttribute('aria-label','Proposed page change');target.tabIndex=-1;
    const snapshotDoc=editor.state.doc;
    const key=new PluginKey('surfacePageProposal');const widgetKey=crypto.randomUUID();let warned=false;
    editor.registerPlugin(new Plugin({key,props:{decorations(state){
      if(!state.doc.eq(snapshotDoc))return DecorationSet.empty;
      return DecorationSet.create(state.doc,[Decoration.widget(position,()=>target,{key:widgetKey,side:1,ignoreSelection:true,stopEvent:()=>true})]);
    }},view:()=>({update(view){
      if(!warned&&!view.state.doc.eq(snapshotDoc)){warned=true;queueMicrotask(()=>stale.current());}
    }})}));
    setHost(target);
    return ()=>{setHost(null);if(!editor.isDestroyed)editor.unregisterPlugin(key);};
  },[editor,position,editorJson]);
  return host?createPortal(children,host):null;
}

export function SurfaceProposalReview({markdown,onChange,preview,busy,error,onSave,onKeep,onDiscard}: {
  markdown:string;onChange:(text:string)=>void;preview:ReactNode;busy:boolean;error:string|null;
  onSave:()=>void;onKeep:()=>void;onDiscard:()=>void;
}) {
  const [editing,setEditing]=useState(false);
  return <section aria-label="Suggestion review" className="surface-proposal-review">
    <header><strong>Proposed change</strong><span>Review before keeping</span></header>
    {editing?<label>Suggestion Markdown<textarea value={markdown} onChange={event=>onChange(event.target.value)} disabled={busy} /></label>:<div className="surface-proposal-review__preview">{preview}</div>}
    <div className="surface-proposal-review__actions">
      <button type="button" disabled={busy} onClick={()=>setEditing(value=>!value)}>{editing?'Preview suggestion':'Edit suggestion'}</button>
      {editing?<button type="button" disabled={busy||!markdown.trim()} onClick={onSave}>Save suggestion</button>:null}
      <button type="button" disabled={busy||!markdown.trim()} onClick={onKeep}>Keep on page</button>
      <button type="button" disabled={busy} onClick={onDiscard}>Discard suggestion</button>
    </div>
    <small>Only Keep changes the page. The page’s existing save behavior then applies.</small>
    {error?<p role="alert">{error}</p>:null}
  </section>;
}
