import {useCallback,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import type {Editor} from '@tiptap/core';
import {Plugin,PluginKey} from '@tiptap/pm/state';
import {Decoration,DecorationSet} from '@tiptap/pm/view';
import {MarkdownEditorCore} from '../tiptap/MarkdownEditorCore';
import {markdownToTiptapDoc} from '../tiptap/markdown/markdownToTiptap';
import {tiptapJsonToSemanticMarkdown} from '../tiptap/markdown/calloutMarkdown';
import './SurfacePageProposal.css';
import {startProposalDragScroll} from './proposalDragScroll';

const proposalDragType='application/x-dmb-page-proposal';
/** Page-adjacent review DOM never enters the author's document or undo history. */
export function SurfacePageProposal({editor,position,editorJson,children,onStale,onMove,placementId,revealKey=0,busy=false,focusOnReveal=true}: {
  editor:Editor;position:number;editorJson:string;children:ReactNode;onStale:()=>void;
  onMove?:(position:number)=>void;placementId?:string;revealKey?:number;busy?:boolean;focusOnReveal?:boolean;
}) {
  const [host,setHost]=useState<HTMLDivElement|null>(null);
  const [placing,setPlacing]=useState(false);
  const stopScroll=useRef<(()=>void)|null>(null);
  useEffect(()=>()=>stopScroll.current?.(),[editor,editorJson,placementId]);
  useEffect(()=>{if(busy){setPlacing(false);stopScroll.current?.();}},[busy]);
  const current=useRef({position,onStale,onMove,busy});current.current={position,onStale,onMove,busy};
  useEffect(()=>{
    if(editor.isDestroyed)return;
    setPlacing(false);
    if(JSON.stringify(editor.getJSON())!==editorJson){current.current.onStale();return;}
    const target=document.createElement('div');target.className='surface-page-proposal';target.contentEditable='false';
    target.setAttribute('role','region');target.setAttribute('aria-label','Proposed page change');target.tabIndex=-1;
    const snapshotDoc=editor.state.doc;
    const key=new PluginKey('surfacePageProposal');const widgetKey=crypto.randomUUID();let warned=false;
    editor.registerPlugin(new Plugin({key,props:{decorations(state){
      if(!state.doc.eq(snapshotDoc))return DecorationSet.empty;
      // A page object must not inherit a containing block's presentation (for
      // example a heading hidden because it supplies a named table's title).
      // This is only its visual anchor; Save still uses the captured exact caret.
      const anchor=state.doc.resolve(current.current.position);
      const visualPosition=anchor.depth?anchor.before(1):anchor.pos;
      return DecorationSet.create(state.doc,[Decoration.widget(visualPosition,()=>target,{key:widgetKey,side:1,ignoreSelection:true,stopEvent:()=>true})]);
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
  useEffect(()=>{
    if(!placing||!host||busy||editor.isDestroyed)return;
    const dom=editor.view.dom;
    dom.classList.add('is-suggestion-placement-target');
    const cancel=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){event.preventDefault();setPlacing(false);}
      if(event.key==='Enter'&&document.activeElement===dom&&editor.state.selection.empty){
        event.preventDefault();event.stopImmediatePropagation();setPlacing(false);
        current.current.onMove?.(editor.state.selection.from);
      }
    };
    const choose=(event:MouseEvent)=>{
      if(event.target instanceof Node&&host.contains(event.target))return;
      const point=editor.view.posAtCoords({left:event.clientX,top:event.clientY});
      if(!point)return;
      event.preventDefault();event.stopImmediatePropagation();
      setPlacing(false);
      current.current.onMove?.(point.pos);
    };
    dom.addEventListener('click',choose,true);document.addEventListener('keydown',cancel,true);
    return()=>{dom.classList.remove('is-suggestion-placement-target');dom.removeEventListener('click',choose,true);document.removeEventListener('keydown',cancel,true);};
  },[placing,host,busy,editor]);
  useEffect(()=>{if(host&&!editor.isDestroyed)editor.view.dispatch(editor.state.tr.setMeta('surfacePageProposalPosition',position));},[editor,host,position]);
  useEffect(()=>{
    if(!host||!revealKey)return;
    const frame=requestAnimationFrame(()=>{
      // The author may have started typing after reveal was scheduled.
      if(document.activeElement!==host&&host.contains(document.activeElement))return;
      host.scrollIntoView?.({block:'center',behavior:'auto'});if(focusOnReveal)host.focus({preventScroll:true});
    });
    return()=>cancelAnimationFrame(frame);
  },[host,revealKey,focusOnReveal]);
  return host?createPortal(<>
    {onMove?<div className="surface-page-proposal__placement">
      <button type="button" draggable={!busy} disabled={busy} aria-label="Drag suggestion" title="Drag to move; hold near the page edge to scroll"
        onDragStart={event=>{if(busy||!placementId){event.preventDefault();return;}setPlacing(false);stopScroll.current?.();stopScroll.current=startProposalDragScroll(editor.view.dom);event.dataTransfer.setData(proposalDragType,placementId);event.dataTransfer.effectAllowed='move';}}>⠿</button>
      <button type="button" disabled={busy} aria-pressed={placing} onClick={()=>setPlacing(value=>!value)}>{placing?'Cancel move':'Move'}</button>
      {placing?<span role="status">Scroll, then click where this should go. Esc cancels.</span>:null}
    </div>:null}{children}
  </>,host):null;
}

/** One continuously editable rendered suggestion, using the shared document editor. */
export function SurfaceProposalReview({markdown,onChange,busy,error,onSave,onDiscard}: {
  markdown:string;onChange:(text:string)=>void;busy:boolean;error:string|null;
  onSave:()=>void;onDiscard:()=>void;
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
    <header><strong>Suggestion</strong><button type="button" className="surface-proposal-review__dismiss" disabled={busy} aria-label="Dismiss suggestion" title="Dismiss suggestion" onClick={onDiscard}>×</button></header>
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
      <button type="button" disabled={busy||!markdown.trim()} onClick={onSave}>Save</button>
    </div>
    {error?<p role="alert">{error}</p>:null}
  </section>;
}
