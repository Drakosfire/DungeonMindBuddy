import {useCallback,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import type {Editor} from '@tiptap/core';
import {Plugin,PluginKey} from '@tiptap/pm/state';
import {Decoration,DecorationSet} from '@tiptap/pm/view';
import {MarkdownEditorCore} from '../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import './SurfacePageProposal.css';

const proposalDragType='application/x-dmb-page-proposal';
/** Page-adjacent review DOM never enters the author's document or undo history. */
export function SurfacePageProposal({editor,position,editorJson,children,onStale,onMove,placementId,revealKey=0,busy=false}: {
  editor:Editor;position:number;editorJson:string;children:ReactNode;onStale:()=>void;
  onMove?:(position:number)=>void;placementId?:string;revealKey?:number;busy?:boolean;
}) {
  const [host,setHost]=useState<HTMLDivElement|null>(null);
  const current=useRef({position,onStale,onMove,busy});current.current={position,onStale,onMove,busy};
  useEffect(()=>{
    if(editor.isDestroyed)return;
    if(JSON.stringify(editor.getJSON())!==editorJson){current.current.onStale();return;}
    const target=document.createElement('div');target.className='surface-page-proposal';target.contentEditable='false';
    target.setAttribute('role','region');target.setAttribute('aria-label','Proposed page change');target.tabIndex=-1;
    const snapshotDoc=editor.state.doc;
    const key=new PluginKey('surfacePageProposal');const widgetKey=crypto.randomUUID();let warned=false;
    editor.registerPlugin(new Plugin({key,props:{decorations(state){
      if(!state.doc.eq(snapshotDoc))return DecorationSet.empty;
      return DecorationSet.create(state.doc,[Decoration.widget(current.current.position,()=>target,{key:widgetKey,side:1,ignoreSelection:true,stopEvent:()=>true})]);
    }},view:()=>({update(view){
      if(!warned&&!view.state.doc.eq(snapshotDoc)){warned=true;queueMicrotask(()=>current.current.onStale());}
    }})}));
    const dom=editor.view.dom;
    const owned=(event:DragEvent)=>event.dataTransfer?.getData(proposalDragType)===placementId;
    const over=(event:DragEvent)=>{if(event.dataTransfer?.types.includes(proposalDragType)){event.preventDefault();event.stopPropagation();}};
    const drop=(event:DragEvent)=>{
      if(!event.dataTransfer?.types.includes(proposalDragType))return;
      event.preventDefault();event.stopImmediatePropagation();
      if(!owned(event)||current.current.busy||!current.current.onMove||!editor.state.doc.eq(snapshotDoc)
        ||(event.target instanceof Node&&target.contains(event.target)))return;
      const point=editor.view.posAtCoords({left:event.clientX,top:event.clientY});
      if(!point)return;
      const resolved=editor.state.doc.resolve(point.pos);
      let next=point.pos;
      if(resolved.depth){
        const node=editor.view.nodeDOM(resolved.before(1));
        const rect=node instanceof Element?node.getBoundingClientRect():null;
        next=rect&&event.clientY<rect.top+rect.height/2?resolved.before(1):resolved.after(1);
      }
      current.current.onMove(next);
    };
    dom.addEventListener('dragover',over,true);dom.addEventListener('drop',drop,true);
    setHost(target);
    return ()=>{setHost(null);dom.removeEventListener('dragover',over,true);dom.removeEventListener('drop',drop,true);if(!editor.isDestroyed)editor.unregisterPlugin(key);};
  },[editor,editorJson,placementId]);
  useEffect(()=>{if(host&&!editor.isDestroyed)editor.view.dispatch(editor.state.tr.setMeta('surfacePageProposalPosition',position));},[editor,host,position]);
  useEffect(()=>{
    if(!host||!revealKey)return;
    const frame=requestAnimationFrame(()=>{host.scrollIntoView?.({block:'center',behavior:'auto'});host.focus({preventScroll:true});});
    return()=>cancelAnimationFrame(frame);
  },[host,revealKey]);
  return host?createPortal(<>
    {onMove?<div className="surface-page-proposal__placement">
      <button type="button" draggable={!busy} disabled={busy} aria-label="Drag suggestion to another place" title="Drag to another place on this page"
        onDragStart={event=>{if(busy||!placementId){event.preventDefault();return;}event.dataTransfer.setData(proposalDragType,placementId);event.dataTransfer.effectAllowed='move';}}>⠿ Move</button>
      <span>Starts at your captured caret. Drag it, or click a new caret and</span>
      <button type="button" disabled={busy} onClick={()=>{if(editor.state.selection.empty)onMove(editor.state.selection.from);}}>Place at caret</button>
    </div>:null}{children}
  </>,host):null;
}

/** One continuously editable rendered suggestion, using the shared document editor. */
export function SurfaceProposalReview({markdown,onChange,busy,error,onSave,onKeep,onDiscard}: {
  markdown:string;onChange:(text:string)=>void;busy:boolean;error:string|null;
  onSave:()=>void;onKeep:()=>void;onDiscard:()=>void;
}) {
  const [editor,setEditor]=useState<Editor|null>(null);
  const initial=useMemo(()=>markdownToTiptapDoc(markdown).doc,[]);
  const bind=useCallback((value:Editor|null)=>{
    setEditor(value);
    if(value){value.view.dom.setAttribute('role','textbox');value.view.dom.setAttribute('aria-label','Suggestion text');value.view.dom.setAttribute('aria-multiline','true');}
  },[]);
  useEffect(()=>{
    if(!editor||editor.isDestroyed)return;
    // Only external conflict resolution replaces content; own typing already matches.
    const next=markdownToTiptapDoc(markdown).doc;
    if(tiptapJsonToSemanticMarkdown(editor.getJSON())!==tiptapJsonToSemanticMarkdown(next))editor.commands.setContent(next,false);
  },[editor,markdown]);
  return <section aria-label="Suggestion review" className="surface-proposal-review">
    <header><strong>Proposed change</strong><span>Write here, then keep or discard</span></header>
    <div onKeyDownCapture={event=>{
      if(!editor||!(event.ctrlKey||event.metaKey))return;
      const end=event.key==='End'||(event.metaKey&&event.key==='ArrowDown');
      const start=event.key==='Home'||(event.metaKey&&event.key==='ArrowUp');
      if(!end&&!start)return;
      event.preventDefault();event.stopPropagation();
      const position=end?editor.state.doc.content.size-1:1;
      editor.commands.setTextSelection(event.shiftKey?{from:editor.state.selection.anchor,to:position}:position);
      editor.commands.scrollIntoView();editor.view.focus();
    }}><MarkdownEditorCore content={initial} editable={!busy} className="surface-proposal-review__editor" onEditorChange={bind}
      onUpdate={(json,_editor,meta)=>{if(!meta.programmatic)onChange(tiptapJsonToSemanticMarkdown(json));}}/></div>
    <div className="surface-proposal-review__actions">
      <button type="button" disabled={busy||!markdown.trim()} onClick={onSave}>Save suggestion</button>
      <button type="button" disabled={busy||!markdown.trim()} onClick={onKeep}>Keep on page</button>
      <button type="button" disabled={busy} onClick={onDiscard}>Discard suggestion</button>
    </div>
    <small>Only Keep changes the page. The page’s existing save behavior then applies.</small>
    {error?<p role="alert">{error}</p>:null}
  </section>;
}
