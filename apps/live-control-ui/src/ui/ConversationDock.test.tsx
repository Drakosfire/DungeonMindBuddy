import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
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

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("ConversationDock", () => {
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

  it("opens context without losing the chosen scope and hides it when collapsed", async () => {
    const user = userEvent.setup();
    const onExpandedChange = vi.fn();
    render(<Fixture onExpandedChange={onExpandedChange} />);
    const context = screen.getByRole("button", {name:"This scene"});
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
    expect(separator).toHaveAttribute("aria-valuemax", "336");
    expect(separator).toHaveAttribute("aria-valuenow", "336");
    rect.mockRestore();
  });

  it("does not add a context affordance when a caller supplies no context", () => {
    render(<ConversationDock reader="Reader" messages="Messages" composer={<input aria-label="Draft" />} />);
    expect(screen.queryByRole("button", {name:/Context/})).toBeNull();
    expect(screen.getByLabelText("Draft")).toBeInTheDocument();
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
    expect(screen.getByRole("separator")).toHaveAttribute("aria-valuemax", "252");
    expect(screen.getByRole("separator")).toHaveAttribute("aria-valuenow", "252");
    view.unmount();
    expect(disconnect).toHaveBeenCalledTimes(1);
  });

  it("removes unavailable context without resetting the composer", async () => {
    const user = userEvent.setup();
    const composer = <input aria-label="Draft" defaultValue="Keep this" />;
    const view = render(<ConversationDock reader="Reader" messages="Messages" composer={composer} contextDetails="Source details" />);
    await user.click(screen.getByRole("button", {name:"Context"}));
    const input = screen.getByLabelText("Draft");
    view.rerender(<ConversationDock reader="Reader" messages="Messages" composer={composer} contextDetails={null} />);
    expect(screen.queryByRole("button", {name:"Context"})).toBeNull();
    expect(screen.getByLabelText("Draft")).toBe(input);
    expect(input).toHaveValue("Keep this");
    expect(screen.getByRole("log")).toBeInTheDocument();
  });
});
