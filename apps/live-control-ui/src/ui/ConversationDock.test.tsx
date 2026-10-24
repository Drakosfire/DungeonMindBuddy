import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConversationDock } from "./ConversationDock";

function Fixture({ expanded = false, onExpandedChange = vi.fn() } = {}) {
  const [draft, setDraft] = useState("");
  return <ConversationDock initialExpanded={expanded} initialHeight={320} minHeight={280} maxHeight={400}
    onExpandedChange={onExpandedChange} contextLabel="This scene"
    reader={<textarea aria-label="Reader draft" defaultValue="Preparation" />}
    messages={<div><p>Existing answer</p><textarea aria-label="Message annotation" defaultValue="Remember this" /></div>}
    contextDetails={<label>Scope<select aria-label="Context scope"><option>This scene</option><option>Whole Plan</option></select></label>}
    collapsedPreview={<span>Latest reply</span>}
    composer={<label>Message Buddy<input value={draft} onChange={e=>setDraft(e.currentTarget.value)} /></label>} />;
}

beforeEach(() => window.localStorage.setItem("buddy.conversation.placement", "side"));
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("ConversationDock", () => {
  it("defers context effects until requested and retains context state and updates after hiding", () => {
    const mounted = vi.fn(), unmounted = vi.fn();
    function Context({ label }: { label: string }) {
      useEffect(() => { mounted(); return unmounted; }, []);
      return <><p>{label}</p><input aria-label="Context query" defaultValue="" /></>;
    }
    const props = { reader: <input aria-label="Reader" defaultValue="Draft" />, messages: "Answer", composer: <input aria-label="Question" defaultValue="Unsent" />, initialExpanded: true };
    const view = render(<ConversationDock {...props} contextDetails={<Context label="Original scope" />} />);
    expect(mounted).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Context query")).toBeNull();
    const reader = screen.getByLabelText("Reader"), composer = screen.getByLabelText("Question");
    fireEvent.click(screen.getByTitle("Conversation options"));
    fireEvent.click(screen.getByRole("button", { name: "Show Context" }));
    expect(mounted).toHaveBeenCalledTimes(1);
    const query = screen.getByLabelText("Context query");
    fireEvent.change(query, { target: { value: "Saved search" } });
    fireEvent.click(screen.getByRole("button", { name: "Hide Context" }));
    view.rerender(<ConversationDock {...props} contextDetails={<Context label="Updated scope" />} />);
    fireEvent.click(screen.getByRole("button", { name: "Collapse" }));
    fireEvent.click(screen.getByRole("button", { name: "Open chat" }));
    fireEvent.click(screen.getByTitle("Conversation options"));
    fireEvent.click(screen.getByRole("button", { name: "Show Context" }));
    expect(screen.getByText("Updated scope")).toBeVisible();
    expect(screen.getByLabelText("Context query")).toBe(query);
    expect(query).toHaveValue("Saved search");
    expect(screen.getByLabelText("Reader")).toBe(reader);
    expect(screen.getByLabelText("Question")).toBe(composer);
    expect(composer).toHaveValue("Unsent");
    expect(mounted).toHaveBeenCalledTimes(1);
    expect(unmounted).not.toHaveBeenCalled();
  });

  it("adapts the floating workspace without remounting page or conversation drafts", () => {
    let geometry = {height:800,width:1200} as DOMRect;
    vi.spyOn(HTMLElement.prototype,"getBoundingClientRect").mockImplementation(()=>geometry);
    let resized!:()=>void;
    vi.stubGlobal("ResizeObserver",class {constructor(callback:()=>void){resized=callback;} observe(){} disconnect(){}});
    render(<ConversationDock reader={<textarea aria-label="Page draft" defaultValue="Authored work"/>}
      messages={<p>Existing discussion</p>} composer={<textarea aria-label="Conversation draft" defaultValue="My next thought"/>} initialExpanded minimumReaderHeight={0}/>);
    const page=screen.getByLabelText("Page draft"), draft=screen.getByLabelText("Conversation draft");
    const root=page.closest('.conversation-dock')!;
    expect(root).toHaveClass('has-reader');expect(root).not.toHaveClass('is-narrow');
    expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow','640');
    geometry={height:800,width:600} as DOMRect;
    act(()=>resized());
    expect(root).toHaveClass('is-narrow');
    expect(root).toHaveAttribute('data-placement','bottom');
    expect(root).toHaveAttribute('data-preferred-placement','side');
    expect(screen.getByRole('separator')).toHaveAttribute('aria-valuenow','496');
    expect(screen.getByLabelText('Page draft')).toBe(page);
    expect(screen.getByLabelText('Conversation draft')).toBe(draft);
    expect(draft).toHaveValue('My next thought');
  });

  it("uses accessible icons for fullscreen and close without removing their keyboard names", () => {
    render(<ConversationDock reader={<p>Plan</p>} messages={<p>Reply</p>} composer={<textarea aria-label="Message Buddy" />} collapseMode="launcher" fullscreenEnabled initialExpanded />);
    const fullscreen = screen.getByRole("button", { name: "Expand conversation fullscreen" });
    const close = screen.getByRole("button", { name: "Close conversation" });
    expect(fullscreen).toHaveTextContent("");
    expect(close).toHaveTextContent("");
    expect(fullscreen.querySelector('svg[aria-hidden="true"]')).not.toBeNull();
    expect(close.querySelector('svg[aria-hidden="true"]')).not.toBeNull();
    fireEvent.click(fullscreen);
    expect(screen.getByRole("button", { name: "Restore conversation dock" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(close);
    expect(screen.getByRole("button", { name: "Open conversation" })).toBeInTheDocument();
  });

  it("allows the conversation to grow beyond the old half-screen ceiling", () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({height:900} as DOMRect);
    render(<ConversationDock reader={<p>Plan</p>} messages={<p>Conversation</p>} composer={<textarea aria-label="Message Buddy" />} expanded />);
    const resize = screen.getByRole("separator", { name: "Resize Buddy conversation" });
    fireEvent.keyDown(resize, {key:"End"});
    expect(resize).toHaveAttribute("aria-valuemax", "708");
    expect(resize).toHaveAttribute("aria-valuenow", "708");
  });

  it("follows external launcher state without replacing the reader, draft or message position", () => {
    const change = vi.fn();
    const props = {reader:<input aria-label="Retained reader" defaultValue="Plan" />, messages:<p>Answer</p>, composer:<input aria-label="Retained draft" defaultValue="Question" />, onExpandedChange:change};
    const view = render(<ConversationDock {...props} expanded />);
    const reader = screen.getByLabelText("Retained reader");
    const draft = screen.getByLabelText("Retained draft");
    const messages = screen.getByRole("log");
    messages.scrollTop = 137;
    fireEvent.scroll(messages);
    fireEvent.click(screen.getByRole("button", {name:"Collapse"}));
    expect(change).toHaveBeenCalledWith(false);
    expect(screen.getByRole("log")).toBe(messages);
    view.rerender(<ConversationDock {...props} expanded={false} />);
    expect(screen.queryByRole("log")).toBeNull();
    messages.scrollTop = 0;
    view.rerender(<ConversationDock {...props} expanded />);
    expect(screen.getByLabelText("Retained reader")).toBe(reader);
    expect(screen.getByLabelText("Retained draft")).toBe(draft);
    expect(screen.getByRole("log")).toBe(messages);
    expect(messages.scrollTop).toBe(137);
  });
  it("lets each surface name its reading landmark without assuming a document", () => {
    render(<ConversationDock reader={<p>Encounter</p>} readerLabel="Encounter canvas" messages="Messages" composer={<input aria-label="Draft" />} />);
    expect(screen.getByRole("region", {name:"Encounter canvas"})).toHaveTextContent("Encounter");
    expect(screen.queryByLabelText("Document workspace")).toBeNull();
  });
  it("keeps reader and composer mounted while opening and collapsing conversation", async () => {
    const user = userEvent.setup();
    render(<Fixture />);
    const reader = screen.getByLabelText("Reader draft");
    const composer = screen.getByLabelText("Message Buddy");
    await user.type(composer, "A draft question");
    await user.type(reader, " stays local");
    await user.click(screen.getByRole("button", {name:"Open chat"}));
    const annotation = screen.getByLabelText("Message annotation");
    await user.type(annotation, " too");
    await user.click(screen.getByRole("button", {name:"Collapse"}));
    expect(screen.queryByRole("log")).toBeNull();
    await user.click(screen.getByRole("button", {name:"Open chat"}));
    expect(screen.getByLabelText("Reader draft")).toBe(reader);
    expect(screen.getByLabelText("Message Buddy")).toBe(composer);
    expect(composer).toHaveValue("A draft question");
    expect(reader).toHaveValue("Preparation stays local");
    expect(screen.getByLabelText("Message annotation")).toBe(annotation);
    expect(annotation).toHaveValue("Remember this too");
  });

  it("restores the message reading position after collapse and reopen", async () => {
    const user = userEvent.setup();
    render(<Fixture expanded />);
    const messages = screen.getByRole("log");
    messages.scrollTop = 137;
    fireEvent.scroll(messages);
    await user.click(screen.getByRole("button", {name:"Collapse"}));
    messages.scrollTop = 0;
    await user.click(screen.getByRole("button", {name:"Open chat"}));
    expect(screen.getByRole("log")).toBe(messages);
    expect(messages.scrollTop).toBe(137);
  });

  it("names context visibility explicitly and closes it on submit without clearing input", () => {
    render(<ConversationDock reader="Page" messages="Reply" initialExpanded contextLabel="context" contextDetails="Saved page" composer={<form><textarea defaultValue="Keep my draft" /><button type="submit">Send</button></form>} />);
    fireEvent.click(screen.getByTitle("Conversation options"));
    fireEvent.click(screen.getByRole("button", {name:"Show context"}));
    expect(screen.getByRole("button", {name:"Hide context"})).toHaveAttribute("aria-expanded","true");
    fireEvent.submit(screen.getByRole("textbox").closest("form")!);
    expect(screen.getByRole("button", {name:"Show context"})).toHaveAttribute("aria-expanded","false");
    expect(screen.getByRole("textbox")).toHaveValue("Keep my draft");
  });

  it("opens context without losing the chosen scope and hides it when collapsed", async () => {
    const user = userEvent.setup();
    const onExpandedChange = vi.fn();
    render(<Fixture onExpandedChange={onExpandedChange} />);
    await user.click(screen.getByTitle("Conversation options"));
    const context = screen.getByRole("button", {name:/This scene/});
    await user.click(context);
    expect(context).toHaveAttribute("aria-expanded", "true");
    expect(onExpandedChange).toHaveBeenCalledWith(true);
    const scope = screen.getByLabelText("Context scope");
    await user.selectOptions(scope, "Whole Plan");
    await user.click(context);
    expect(context).toHaveAttribute("aria-expanded", "false");
    await user.click(context);
    expect(screen.getByLabelText("Context scope")).toBe(scope);
    expect(scope).toHaveValue("Whole Plan");
    await user.click(screen.getByRole("button", {name:"Collapse"}));
    expect(context).toHaveAttribute("aria-expanded", "false");
  });

  it("clamps keyboard resizing at both bounds and expands a collapsed dock", () => {
    render(<Fixture />);
    const separator = screen.getByRole("separator", {name:"Resize Buddy conversation"});
    fireEvent.keyDown(separator, {key:"ArrowUp"});
    expect(separator).toHaveAttribute("aria-valuenow", "344");
    expect(screen.getByRole("button", {name:"Collapse"})).toBeInTheDocument();
    fireEvent.keyDown(separator, {key:"End"});
    fireEvent.keyDown(separator, {key:"ArrowUp"});
    expect(separator).toHaveAttribute("aria-valuenow", "400");
    fireEvent.keyDown(separator, {key:"Home"});
    fireEvent.keyDown(separator, {key:"ArrowDown"});
    expect(separator).toHaveAttribute("aria-valuenow", "280");
  });

  it("uses pointer capture and stops resizing after cancellation", () => {
    const oldPointer = window.PointerEvent;
    window.PointerEvent = MouseEvent as unknown as typeof PointerEvent;
    try {
      render(<Fixture expanded />);
      const separator = screen.getByRole("separator");
      const capture = vi.fn();
      Object.defineProperty(separator, "setPointerCapture", {value:capture, configurable:true});
      fireEvent.pointerDown(separator, {button:0, clientY:400});
      fireEvent.pointerDown(separator, {button:0, clientY:420});
      fireEvent.pointerMove(separator, {clientY:360});
      expect(capture).toHaveBeenCalledTimes(1);
      expect(separator).toHaveAttribute("aria-valuenow", "360");
      fireEvent.pointerCancel(separator);
      fireEvent.pointerMove(separator, {clientY:300});
      expect(separator).toHaveAttribute("aria-valuenow", "360");
    } finally {window.PointerEvent = oldPointer;}
  });

  it("reserves reader space when its owning container shrinks", () => {
    const rect = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({height:480} as DOMRect);
    render(<Fixture expanded />);
    const separator = screen.getByRole("separator");
    fireEvent.keyDown(separator, {key:"End"});
    expect(separator).toHaveAttribute("aria-valuemax", "304");
    expect(separator).toHaveAttribute("aria-valuenow", "304");
    rect.mockRestore();
  });

  it("does not add a context affordance when a caller supplies no context", () => {
    render(<ConversationDock reader="Reader" messages="Messages" composer={<input aria-label="Draft" />} />);
    expect(screen.queryByRole("button", {name:/Context/})).toBeNull();
    expect(screen.getByLabelText("Draft")).toBeInTheDocument();
    expect(screen.getByRole("region", {name:"Workspace content"})).toHaveTextContent("Reader");
  });

  it("updates bounds on container resize and disconnects its observer", () => {
    let callback: (() => void) | undefined;
    const observe = vi.fn(), disconnect = vi.fn();
    vi.stubGlobal("ResizeObserver", class { constructor(next: () => void) { callback = next; } observe = observe; disconnect = disconnect; });
    const rect = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({height:480} as DOMRect);
    const view = render(<Fixture expanded />);
    expect(observe).toHaveBeenCalledTimes(1);
    rect.mockReturnValue({height:360} as DOMRect);
    act(() => callback?.());
    expect(screen.getByRole("separator")).toHaveAttribute("aria-valuemax", "220");
    expect(screen.getByRole("separator")).toHaveAttribute("aria-valuenow", "220");
    view.unmount();
    expect(disconnect).toHaveBeenCalledTimes(1);
  });

  it("removes unavailable context without resetting the composer", async () => {
    const user = userEvent.setup();
    const composer = <input aria-label="Draft" defaultValue="Keep this" />;
    const view = render(<ConversationDock reader="Reader" messages="Messages" composer={composer} contextDetails="Source details" />);
    await user.click(screen.getByTitle("Conversation options"));
    await user.click(screen.getByRole("button", {name:/Context/}));
    const input = screen.getByLabelText("Draft");
    view.rerender(<ConversationDock reader="Reader" messages="Messages" composer={composer} contextDetails={null} />);
    expect(screen.queryByRole("button", {name:/Context/})).toBeNull();
    expect(screen.getByLabelText("Draft")).toBe(input);
    expect(input).toHaveValue("Keep this");
    expect(screen.getByRole("log")).toBeInTheDocument();
  });
});

it("preserves mounted drafts and reading position through fullscreen, restore, full close and keyboard entrance", async () => {
  const user = userEvent.setup();
  render(<ConversationDock title="Conversation" initialExpanded collapseMode="launcher" fullscreenEnabled
    reader={<input aria-label="Plan writing" defaultValue="Unsaved preparation" />}
    messages={<p>Retained reply</p>} composer={<textarea aria-label="Conversation writing" defaultValue="Unsent question" />} />);
  const reader = screen.getByLabelText("Plan writing"), draft = screen.getByLabelText("Conversation writing"), log = screen.getByRole("log");
  log.scrollTop = 93; fireEvent.scroll(log);
  await user.click(screen.getByRole("button", {name:"Expand conversation fullscreen"}));
  expect(screen.getByRole("dialog")).toContainElement(draft);
  expect(reader).not.toBeVisible(); expect(screen.getByRole("log")).toBe(log); expect(log.scrollTop).toBe(93);
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull(); expect(reader).toBeVisible();
  expect(screen.getByRole("button", {name:"Expand conversation fullscreen"})).toHaveFocus();
  await user.click(screen.getByRole("button", {name:"Close conversation"}));
  expect(screen.queryByRole("log")).toBeNull(); expect(draft).not.toBeVisible();
  const entrance = screen.getByRole("button", {name:"Open conversation"}); expect(entrance).toHaveFocus();
  reader.focus(); expect(screen.queryByRole("log")).toBeNull();
  entrance.focus(); await user.keyboard("{Enter}");
  expect(screen.getByLabelText("Conversation writing")).toBe(draft); expect(draft).toHaveValue("Unsent question"); expect(draft).toHaveFocus();
  expect(screen.getByLabelText("Plan writing")).toBe(reader); expect(log.scrollTop).toBe(93);
});


it("can omit the repeated visual heading while retaining conversation accessibility", () => {
  render(<ConversationDock title="Conversation" showTitle={false} initialExpanded fullscreenEnabled
    reader="Page" messages="Reply" composer={<input aria-label="Write" />} />);
  expect(screen.queryByText("Conversation", { selector: "strong" })).not.toBeInTheDocument();
  expect(screen.getByRole("separator", { name: "Resize conversation" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Expand conversation fullscreen" })).toBeInTheDocument();
});

it("keeps context and diagnostics behind one icon menu without losing draft state",async()=>{
  const user=userEvent.setup();
  render(<ConversationDock reader="Page" showTitle={false} initialExpanded fullscreenEnabled contextLabel="context" contextDetails={<input aria-label="Context filter"/>} messages="Reply" composer={<textarea aria-label="Draft" defaultValue="Keep this"/>} headerActions={<button aria-label="New conversation">+</button>} menuActions={<button>Explore Graph</button>}/>);
  expect(screen.queryByRole("button",{name:"Show context"})).toBeNull();
  expect(screen.queryByRole("button",{name:"Explore Graph"})).toBeNull();
  const menu=screen.getByTitle("Conversation options");
  expect(menu).not.toHaveTextContent("Conversation options");
  await user.click(menu);
  await user.click(screen.getByRole("checkbox",{name:"Technical details"}));
  expect(screen.getByRole("log").closest(".conversation-dock")).toHaveAttribute("data-diagnostics-visible","true");
  await user.click(screen.getByRole("button",{name:"Show context"}));
  expect(screen.getByLabelText("Context filter")).toBeVisible();
  expect(screen.getByLabelText("Draft")).toHaveValue("Keep this");
  fireEvent.keyDown(menu,{key:"Escape"});
  expect(menu.parentElement).not.toHaveAttribute("open");
  expect(menu).toHaveFocus();
});

it("owns placement choices, preserves mounted drafts and restores the remembered choice", () => {
 const props={reader:<input aria-label="Page draft" defaultValue="Page"/>,messages:<p>Answer</p>,composer:<textarea aria-label="Unsent" defaultValue="Keep this"/>,initialExpanded:true,fullscreenEnabled:true};
 const view=render(<ConversationDock {...props}/>);
 const draft=screen.getByLabelText('Unsent'), page=screen.getByLabelText('Page draft');
 fireEvent.click(screen.getByTitle('Conversation options'));
 for(const name of ['Bottom','Float','Side']) {
  fireEvent.click(screen.getByRole('button',{name,exact:true}));
  expect(view.container.firstChild).toHaveAttribute('data-placement',name.toLowerCase());
  expect(screen.getByLabelText('Unsent')).toBe(draft);
  expect(screen.getByLabelText('Page draft')).toBe(page);
 }
 fireEvent.click(screen.getByRole('button',{name:'Float',exact:true}));
 fireEvent.click(screen.getByRole('button',{name:'Expand conversation fullscreen'}));
 fireEvent.click(screen.getByRole('button',{name:'Restore conversation dock'}));
 expect(view.container.firstChild).toHaveAttribute('data-placement','float');
 expect(screen.getByLabelText('Unsent')).toHaveValue('Keep this');
 view.unmount();
 const next=render(<ConversationDock {...props}/>);
 expect(next.container.firstChild).toHaveAttribute('data-placement','float');
})

it("synchronizes placement across shared dock owners without replacing either composer", () => {
 render(<><ConversationDock reader="Page" initialExpanded messages="A" composer={<input aria-label="A"/>}/><ConversationDock reader={null} initialExpanded messages="B" composer={<input aria-label="B"/>}/></>);
 const drafts=[screen.getByLabelText('A'),screen.getByLabelText('B')];
 fireEvent.click(screen.getAllByTitle('Conversation options')[0]);
 fireEvent.click(screen.getByRole('button',{name:'Bottom',exact:true}));
 expect(document.querySelectorAll('[data-placement="bottom"]')).toHaveLength(2);
 expect(screen.getByLabelText('A')).toBe(drafts[0]);expect(screen.getByLabelText('B')).toBe(drafts[1]);
})
