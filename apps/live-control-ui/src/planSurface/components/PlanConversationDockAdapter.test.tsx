import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { createPortal } from "react-dom";
import { describe, it, expect, vi } from "vitest";
import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider, useRegisterAskPluginPresence } from "../../agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "../../agentInteraction/AgentInteractionChrome";
import { PlanConversationDockAdapter, type PlanConversationPresentationHosts } from "./PlanConversationDockAdapter";

function Plugin({hosts}:{hosts:PlanConversationPresentationHosts}) {
  useRegisterAskPluginPresence(true);
  const [draft,setDraft]=useState("");
  return <>
    {hosts.composer&&createPortal(<label>Message Buddy<input value={draft} onChange={e=>setDraft(e.target.value)}/></label>,hosts.composer)}
    {hosts.messages&&createPortal(<p>Existing reply</p>,hosts.messages)}
    {hosts.context&&createPortal(<p>Full committed Plan context</p>,hosts.context)}
  </>;
}
function Fixture() {
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <PlanConversationDockAdapter contextLabel="Warehouse · Full saved Plan" reader={<textarea aria-label="Plan draft" defaultValue="Preparation"/>}>
      {hosts=><Plugin hosts={hosts}/>}
    </PlanConversationDockAdapter>
    <AgentInteractionChrome/>
  </AskPluginSlotProvider></AgentInteractionProvider>;
}
describe("PlanConversationDockAdapter",()=>{
  it("keeps reader and typed composer mounted while existing pane state expands and collapses",async()=>{
    const user=userEvent.setup();render(<Fixture/>);
    const input=await screen.findByLabelText("Message Buddy"),reader=screen.getByLabelText("Plan draft");
    await user.type(input,"Remember the sleepers");
    await waitFor(()=>expect(screen.getByRole("log")).toBeVisible());
    expect(screen.getByRole("separator", {name:"Resize Buddy conversation"})).toHaveAttribute("aria-valuenow", "220");
    await user.click(screen.getByRole("button",{name:"Collapse",exact:true}));
    expect(screen.getByLabelText("Message Buddy")).toBe(input);
    expect(input).toHaveValue("Remember the sleepers");
    expect(screen.getByLabelText("Plan draft")).toBe(reader);
    await user.click(screen.getByRole("button",{name:"Open",exact:true}));
    expect(screen.getByRole("log")).toHaveTextContent("Existing reply");
    expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Message Buddy")).toHaveLength(1);
    expect(screen.getAllByTestId("agent-interaction-open")).toHaveLength(1);
  });
  it("keeps the reader usable when no Ask host provider exists",()=>{
    render(<PlanConversationDockAdapter contextLabel="Plan" reader={<textarea aria-label="Unhosted Plan"/>}>{()=>null}</PlanConversationDockAdapter>);
    expect(screen.getByLabelText("Unhosted Plan")).toBeEnabled();
    expect(screen.queryByRole("log")).not.toBeInTheDocument();
  });
  it("uses inspectable context without opening another overlay or submitting a request",async()=>{
    const user=userEvent.setup();render(<Fixture/>);
    await screen.findByLabelText("Message Buddy");
    await user.click(screen.getByRole("button",{name:"Warehouse · Full saved Plan"}));
    expect(screen.getByText("Full committed Plan context")).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
