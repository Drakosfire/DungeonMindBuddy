import {createContext,useCallback,useContext,useEffect,useLayoutEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import type {Editor} from '@tiptap/core';
import type {AuthoredGraphReferenceV1} from '../../api/types';
import {GraphNodeChipRuntimeProvider} from '../../graphReference/GraphNodeChipRuntime';
import {NativeGraphObjectPreview} from '../../graphLens/NativeGraphObjectPreview';
import {readCurrentNativeObjectReference} from '../../graphLens/readCurrentNativeObjectReference';
import {isValidGraphNodeId} from '../../tiptap/references/runbookReferences';
import './WorldPlanGraphReferenceActivation.css';

interface ActivationValue {activateNode:(nodeId:string,trigger?:HTMLElement)=>void}
const ActivationContext=createContext<ActivationValue|null>(null);
export function useWorldPlanGraphReferenceActivation():ActivationValue {
 const value=useContext(ActivationContext);
 if(!value)throw new Error('World Plan Graph reference activation requires its provider.');
 return value;
}

export function WorldPlanGraphReferenceActivationProvider({worldId,ownerKey,editor,enabled,children}:{worldId:string;ownerKey:string;editor:Editor|null;enabled:boolean;children:ReactNode}) {
 const owner=useMemo(()=>({worldId,ownerKey,editor,enabled}),[worldId,ownerKey,editor,enabled]);
 const live=useRef<typeof owner|null>(null),read=useRef<AbortController|null>(null);
 const [request,setRequest]=useState<{owner:typeof owner;nodeId:string;reference:AuthoredGraphReferenceV1|null;error:string|null}|null>(null);
 const currentRequest=request?.owner===owner?request:null;
 const requestRef=useRef(currentRequest);requestRef.current=currentRequest;
 useLayoutEffect(()=>{live.current=owner;setRequest(null);return()=>{live.current=null;read.current?.abort();};},[owner]);
  const triggerRef = useRef<HTMLElement | null>(null);
  const triggerScopeRef = useRef<HTMLElement | null>(null);
  const triggerPageRef = useRef<HTMLElement | null>(null);
  const triggerPageIdentityRef = useRef<string | null>(null);
  const triggerNodeIdRef = useRef<string | null>(null);
  const triggerOrdinalRef = useRef<number>(0);
  const triggerOwnerWorldIdRef = useRef<string | null>(null);
  const triggerOwnerRef=useRef<typeof owner|null>(null);
  const readerScrollRef = useRef<number | null>(null);
  const clickedReferenceRef = useRef<HTMLElement | null>(null);
  const currentOwnerWorldIdRef = useRef(worldId);
  currentOwnerWorldIdRef.current = worldId;
  const closeButtonRef=useRef<HTMLButtonElement|null>(null);
  const hadRequestRef=useRef(false);
  const activateNode=useCallback(async(nodeId:string,trigger?:HTMLElement)=>{
    if(live.current!==owner||!owner.enabled)return;
    const clickedReference=clickedReferenceRef.current;clickedReferenceRef.current=null;
    if(!currentRequest) {
      const origin = trigger?.isConnected
        ? trigger
        : clickedReference?.isConnected
          ? clickedReference
          : typeof document !== "undefined" && document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null;
      triggerRef.current = origin;
      const scope = origin?.closest<HTMLElement>(
        ".world-plan-cards, .world-plan-document-view",
      ) ?? null;
      triggerScopeRef.current = scope;
      const page = scope?.closest<HTMLElement>(".world-owned-plan") ?? null;
      triggerPageRef.current = page;
      triggerPageIdentityRef.current = page?.dataset.planSurfaceIdentity ?? null;
      triggerNodeIdRef.current = nodeId;
      const matchingReferences = scope
        ? Array.from(scope.querySelectorAll<HTMLElement>("button.recap-node-token[data-graph-node-id]"))
          .filter((candidate) => candidate.dataset.graphNodeId === nodeId)
        : [];
      triggerOrdinalRef.current = Math.max(0, origin ? matchingReferences.indexOf(origin) : 0);
      triggerOwnerWorldIdRef.current = worldId;
      triggerOwnerRef.current=owner;
      readerScrollRef.current = window.scrollY;
    }
    read.current?.abort();const abort=new AbortController();read.current=abort;
    setRequest({owner,nodeId,reference:null,error:null});
    try {
      const reference=await readCurrentNativeObjectReference(worldId,nodeId,abort.signal);
      if(!abort.signal.aborted&&live.current===owner)setRequest({owner,nodeId,reference,error:null});
    } catch(error) {
      if(!abort.signal.aborted&&live.current===owner)setRequest({owner,nodeId,reference:null,error:error instanceof Error?error.message:'This object could not be opened.'});
    }
  },[owner,currentRequest,worldId]);
  useEffect(() => {
    const captureClickedReference = (event: MouseEvent) => {
      const target = event.target;
      const reference = target instanceof Element
        ? target.closest<HTMLElement>("button.recap-node-token[data-graph-node-id]")
        : null;
      const scope = reference?.closest<HTMLElement>(".world-plan-cards, .world-plan-document-view") ?? null;
      const visibleScope = scope && !scope.closest("[hidden]") && scope.getAttribute("aria-hidden") !== "true"
        ? scope
        : null;
      const capturedReference = reference && typeof reference.dataset.graphNodeId === "string"
        && isValidGraphNodeId(reference.dataset.graphNodeId)
        && visibleScope
        ? reference
        : null;
      clickedReferenceRef.current = capturedReference;
      if (capturedReference) {
        window.setTimeout(() => {
          if (clickedReferenceRef.current === capturedReference) clickedReferenceRef.current = null;
        }, 0);
      }
    };
    document.addEventListener("click", captureClickedReference, true);
    return () => document.removeEventListener("click", captureClickedReference, true);
  }, []);

  useEffect(()=>{
    if(currentRequest){hadRequestRef.current=true;closeButtonRef.current?.focus({preventScroll:true});return;}
    if (hadRequestRef.current) {
      hadRequestRef.current = false;
      const triggerOwnerWorldId = triggerOwnerWorldIdRef.current;
      const capturedOwner=triggerOwnerRef.current;
      if (triggerOwnerWorldId !== worldId || capturedOwner!==owner) return;
      let trigger = triggerRef.current;
      const scope = triggerScopeRef.current;
      if (!scope) {
        if (!trigger?.isConnected) trigger = null;
      } else if (scope.isConnected && !scope.closest("[hidden]") && scope.getAttribute("aria-hidden") !== "true") {
        if (!trigger?.isConnected && scope && triggerNodeIdRef.current) {
          const matchingReferences = Array.from(scope.querySelectorAll<HTMLElement>("button.recap-node-token[data-graph-node-id]"))
            .filter((candidate) => candidate.dataset.graphNodeId === triggerNodeIdRef.current)
          trigger = matchingReferences[triggerOrdinalRef.current] ?? null;
        }
      } else {
        const page = triggerPageRef.current;
        const pageIdentity = triggerPageIdentityRef.current;
        if (page?.isConnected && pageIdentity && page.dataset.planSurfaceIdentity === pageIdentity) {
          const toolbars = Array.from(page.ownerDocument.querySelectorAll<HTMLElement>("[data-plan-toolbar-identity]"))
            .filter((candidate) => candidate.dataset.planToolbarIdentity === pageIdentity && !candidate.closest("[hidden]"));
          trigger = toolbars.length === 1 ? toolbars[0]!.querySelector<HTMLElement>(
            '.world-plan-view-switch button[aria-pressed="true"]',
          ) : null;
        } else {
          trigger = null;
        }
      }
      window.setTimeout(() => {
        if (live.current===capturedOwner && currentOwnerWorldIdRef.current === triggerOwnerWorldId && requestRef.current === null && trigger?.isConnected) {
          if (readerScrollRef.current !== null && readerScrollRef.current !== window.scrollY) {
            window.scrollTo({ top: readerScrollRef.current, behavior: "auto" });
          }
          trigger.focus({ preventScroll: true });
        }
      }, 0);
    }
  }, [currentRequest, worldId, owner]);

  const close=useCallback(()=>{if(live.current!==owner)return;read.current?.abort();setRequest(null);},[owner]);
  const runtime=useMemo(()=>({nodeViews:{},activeNodeId:currentRequest?.nodeId??null,onSelectNode:()=>undefined,onSelectEditorNode:(nodeId:string,sourceEditor:Editor)=>{
    if(live.current===owner&&sourceEditor===owner.editor&&!sourceEditor.isDestroyed)void activateNode(nodeId);
  },exactGraphScope:null}),[owner,currentRequest?.nodeId,activateNode]);
  return <ActivationContext.Provider value={{activateNode}}><GraphNodeChipRuntimeProvider value={runtime}>
    {children}
    {currentRequest?.reference?<NativeGraphObjectPreview reference={currentRequest.reference} onClose={close}/>:currentRequest?<section className="world-plan-graph-reference-inspector" role="dialog" aria-modal="false" aria-label="World Graph object" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close();}}}>
      <header><h2>{currentRequest.nodeId}</h2><button ref={closeButtonRef} type="button" onClick={close} aria-label="Close object">Close</button></header>
      {currentRequest.error?<><p role="alert">{currentRequest.error}</p><button type="button" onClick={()=>void activateNode(currentRequest.nodeId)}>Retry object</button></>:<p role="status">Opening object…</p>}
    </section>:null}
  </GraphNodeChipRuntimeProvider></ActivationContext.Provider>;
}
