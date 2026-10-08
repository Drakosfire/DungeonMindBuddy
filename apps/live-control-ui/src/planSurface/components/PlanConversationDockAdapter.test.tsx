import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    await user.click(await screen.findByRole("button",{name:"Open",exact:true}));
    const input=await screen.findByLabelText("Message Buddy"),reader=screen.getByLabelText("Plan draft");
    await user.type(input,"Remember the sleepers");
    await waitFor(()=>expect(screen.getByRole("log")).toBeVisible());
    expect(screen.getByRole("separator", {name:"Resize conversation"})).toHaveAttribute("aria-valuenow", "360");
    await user.click(screen.getByRole("button",{name:"Close conversation",exact:true}));
    expect(screen.getByLabelText("Message Buddy")).toBe(input);
    expect(input).toHaveValue("Remember the sleepers");
    expect(input).not.toBeVisible();
    expect(screen.queryByRole("log")).toBeNull();
    reader.focus();
    expect(screen.queryByRole("log")).toBeNull();
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
    await user.click(await screen.findByRole("button",{name:"Open",exact:true}));
    await user.click(screen.getByRole("button",{name:"Context"}));
    expect(screen.getByText("Full committed Plan context")).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});


it("uses the existing dragon entrance for fullscreen and full close without opening Edit or creating another composer", async()=>{
  const user=userEvent.setup();render(<Fixture/>);
  await user.click(await screen.findByRole("button",{name:"Open",exact:true}));
  const draft=screen.getByLabelText("Message Buddy");await user.type(draft,"Unsent plan question");
  await user.click(screen.getByRole("button",{name:"Expand conversation fullscreen"}));
  expect(screen.getByRole("dialog",{name:"Saved World Plan conversation"})).toContainElement(draft);
  await user.click(screen.getByRole("button",{name:"Restore conversation dock"}));
  await user.click(screen.getByRole("button",{name:"Close conversation"}));
  const entrance=screen.getByRole("button",{name:"Open",exact:true});expect(entrance).toHaveFocus();
  await user.keyboard("{Enter}");expect(draft).toHaveValue("Unsent plan question");expect(draft).toHaveFocus();
  expect(screen.getAllByLabelText("Message Buddy")).toHaveLength(1);
  expect(screen.queryByRole("button",{name:"Close Edit"})).toBeNull();
});


it.each([false, true])("dismisses More by pointer and keeps Close reachable (fullscreen=%s)", async fullscreen => {
  const user = userEvent.setup(); render(<Fixture/>);
  await user.click(await screen.findByRole("button", {name:"Open",exact:true}));
  if (fullscreen) await user.click(screen.getByRole("button", {name:"Expand conversation fullscreen"}));
  const summary = screen.getByText("Conversation options", {selector:"summary"});
  const details = summary.parentElement as HTMLDetailsElement;
  await user.click(summary); expect(details.open).toBe(true);
  await user.click(summary); expect(details.open).toBe(false);
  await user.click(summary);
  await user.click(screen.getByLabelText("Message Buddy")); expect(details.open).toBe(false);
  await user.click(summary);
  await user.click(screen.getByRole("button", {name:"Close conversation"}));
  expect(details.open).toBe(false); expect(screen.queryByRole("log")).toBeNull();
  await user.click(screen.getByRole("button", {name:"Open",exact:true}));
  expect(details.open).toBe(false);
  await user.click(summary); fireEvent.keyDown(summary, {key:"Escape"});
  expect(details.open).toBe(false); expect(summary).toHaveFocus();
});
