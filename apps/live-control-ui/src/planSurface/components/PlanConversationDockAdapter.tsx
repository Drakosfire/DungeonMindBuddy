import { useCallback, useLayoutEffect, useState, type ReactNode } from "react";
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
      headerActions={<><details className="plan-conversation-dock__management"><summary>More</summary><div ref={header}/></details></>}
      launcher={<><div ref={setLauncherHost} className="plan-conversation-dock__launcher"/><span>Conversation</span></>}
      contextDetails={<><p className="plan-conversation-dock__scope">{contextLabel.replace(/\s*·\s*Full saved Plan$/, "")}</p><div ref={context}/></>}
      messages={<div ref={messages} className="plan-conversation-dock__messages"/>}
      composer={<div ref={composer} className="plan-conversation-dock__composer"/>}/>
    {children(hosts)}
  </>;
}
