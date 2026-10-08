import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { ConversationDock } from "../../ui/ConversationDock";
import { useAskPluginSlotOptional } from "../../agentInteraction/AskPluginSlot";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import "./PlanConversationDockAdapter.css";

export interface PlanConversationPresentationHosts {
  header: HTMLElement | null;
  context: HTMLElement | null;
  messages: HTMLElement | null;
  composer: HTMLElement | null;
}

type AdapterProps = {
  reader:ReactNode;contextLabel:string;
  children:(hosts:PlanConversationPresentationHosts)=>ReactNode;
};
const absentHosts:PlanConversationPresentationHosts={header:null,context:null,messages:null,composer:null};
export function PlanConversationDockAdapter(props:AdapterProps) {
  const slot=useAskPluginSlotOptional();
  if (!slot) return <>{props.reader}{props.children(absentHosts)}</>;
  return <MountedPlanDock {...props} slot={slot}/>;
}
function MountedPlanDock({reader,contextLabel,children,slot}:AdapterProps & {slot:NonNullable<ReturnType<typeof useAskPluginSlotOptional>>}) {
  const {paneState,setPaneOpen}=useAgentInteraction();
  const management = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const dismissOutside = (event: globalThis.PointerEvent) => {
      if (management.current?.open && event.target instanceof Node && !management.current.contains(event.target)) management.current.open = false;
    };
    const dismissEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && management.current?.open) {
        event.preventDefault();
        event.stopPropagation();
        management.current.open = false;
        management.current.querySelector<HTMLElement>("summary")?.focus({ preventScroll: true });
      }
    };
    document.addEventListener("pointerdown", dismissOutside, true);
    document.addEventListener("keydown", dismissEscape, true);
    return () => {
      document.removeEventListener("pointerdown", dismissOutside, true);
      document.removeEventListener("keydown", dismissEscape, true);
    };
  }, []);
  useLayoutEffect(() => { if (!paneState.isOpen && management.current) management.current.open = false; }, [paneState.isOpen]);
  const {setLayoutOwner,setHostElement,setLauncherHost}=slot;
  const [hosts,setHosts]=useState<PlanConversationPresentationHosts>({header:null,context:null,messages:null,composer:null});
  const bind=useCallback((key:keyof PlanConversationPresentationHosts,node:HTMLElement|null)=>{
    setHosts(current=>current[key]===node?current:{...current,[key]:node});
  },[]);
  const header=useCallback((node:HTMLDivElement|null)=>bind("header",node),[bind]);
  const context=useCallback((node:HTMLDivElement|null)=>bind("context",node),[bind]);
  const messages=useCallback((node:HTMLDivElement|null)=>bind("messages",node),[bind]);
  const composer=useCallback((node:HTMLDivElement|null)=>{bind("composer",node);setHostElement(node);},[bind,setHostElement]);
  useLayoutEffect(()=>{setLayoutOwner("plan-workspace");return()=>{setLayoutOwner("chrome");setHostElement(null);setLauncherHost(null);};},[setLayoutOwner,setHostElement,setLauncherHost]);
  return <>
    <ConversationDock className="plan-conversation-dock" reader={reader} readerLabel="Plan workspace"
      conversationLabel="Saved World Plan conversation"
      title="Conversation" contextLabel="Context" collapseMode="launcher" fullscreenEnabled expanded={paneState.isOpen} onExpandedChange={setPaneOpen}
      initialHeight={360} minHeight={240}
      headerActions={<details ref={management} className="plan-conversation-dock__management" aria-label="Conversation options"><summary>Conversation options</summary><div ref={header}/></details>}
      launcher={<><div ref={setLauncherHost} className="plan-conversation-dock__launcher"/><span>Conversation</span></>}
      contextDetails={<><p className="plan-conversation-dock__scope">{contextLabel.replace(/\s*·\s*Full saved Plan$/, "")}</p><div ref={context}/></>}
      messages={<div ref={messages} className="plan-conversation-dock__messages"/>}
      composer={<div ref={composer} className="plan-conversation-dock__composer"/>}/>
    {children(hosts)}
  </>;
}
