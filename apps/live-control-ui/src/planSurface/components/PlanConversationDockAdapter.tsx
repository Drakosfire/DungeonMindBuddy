import { useCallback, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { ConversationDock } from "../../ui/ConversationDock";
import { useAskPluginSlotOptional } from "../../agentInteraction/AskPluginSlot";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import "./PlanConversationDockAdapter.css";
import "../../agentInteraction/WorldConversationPresentation.css";

export interface PlanConversationPresentationHosts {
  header: HTMLElement | null;
  newConversation?: HTMLElement | null;
  context: HTMLElement | null;
  messages: HTMLElement | null;
  composer: HTMLElement | null;
}

type AdapterProps = {
  reader:ReactNode;contextLabel:string;
  surface?: "plan" | "build";
  children:(hosts:PlanConversationPresentationHosts)=>ReactNode;
};
const absentHosts:PlanConversationPresentationHosts={header:null,newConversation:null,context:null,messages:null,composer:null};
export function DocumentConversationDock(props:AdapterProps) {
  const slot=useAskPluginSlotOptional();
  if (!slot) return <>{props.reader}{props.children(absentHosts)}</>;
  return <MountedPlanDock {...props} slot={slot}/>;
}
export const PlanConversationDockAdapter = DocumentConversationDock;

function MountedPlanDock({reader,contextLabel,children,slot,surface="plan"}:AdapterProps & {slot:NonNullable<ReturnType<typeof useAskPluginSlotOptional>>}) {
  const {paneState,setPaneOpen}=useAgentInteraction();
  const management = useRef<HTMLDetailsElement>(null);
  const {setLayoutOwner,setHostElement,setLauncherHost}=slot;
  const [hosts,setHosts]=useState<PlanConversationPresentationHosts>({header:null,newConversation:null,context:null,messages:null,composer:null});
  const bind=useCallback((key:keyof PlanConversationPresentationHosts,node:HTMLElement|null)=>{
    setHosts(current=>current[key]===node?current:{...current,[key]:node});
  },[]);
  const header=useCallback((node:HTMLDivElement|null)=>bind("header",node),[bind]);
  const newConversation=useCallback((node:HTMLDivElement|null)=>bind("newConversation",node),[bind]);
  const context=useCallback((node:HTMLDivElement|null)=>bind("context",node),[bind]);
  const messages=useCallback((node:HTMLDivElement|null)=>bind("messages",node),[bind]);
  const composer=useCallback((node:HTMLDivElement|null)=>{bind("composer",node);setHostElement(node);},[bind,setHostElement]);
  useLayoutEffect(()=>{setLayoutOwner("plan-workspace");return()=>{setLayoutOwner("chrome");setHostElement(null);setLauncherHost(null);};},[setLayoutOwner,setHostElement,setLauncherHost]);
  return <>
    <ConversationDock className="plan-conversation-dock" reader={reader} readerLabel={`${surface === "build" ? "Build" : "Plan"} workspace`}
      conversationLabel="World conversation"
      title="Conversation" showTitle={false} contextLabel="context" collapseMode="launcher" fullscreenEnabled expanded={paneState.isOpen} onExpandedChange={setPaneOpen}
      minHeight={280} minimumReaderHeight={0}
      headerActions={<div ref={newConversation} className="plan-conversation-dock__new-conversation"/>}
      menuRef={management} menuActions={<div ref={header}/>}
      launcher={<div ref={setLauncherHost} className="plan-conversation-dock__launcher"/>}
      contextDetails={<><p className="plan-conversation-dock__scope">{contextLabel.replace(/\s*·\s*Full saved Plan$/, "")}</p><div ref={context}/></>}
      messages={<div ref={messages} className="plan-conversation-dock__messages"/>}
      composer={<div ref={composer} className="plan-conversation-dock__composer"/>}/>
    {children(hosts)}
  </>;
}
