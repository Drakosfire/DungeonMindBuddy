import { createRef, useState } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Contents } from "./Contents";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const entries = [{ id: "one", title: "First scene", bodyText: "Retained draft preview" }];
it.each([false, true])("shares book, Escape, focus and retained selection with controlled=%s", controlled => {
  const selected = vi.fn();
  function Harness() {
    const [expanded, setExpanded] = useState(true);
    return <Contents entries={entries} selectedId="one" onSelect={selected} visible
      {...(controlled ? { expanded, onExpandedChange: setExpanded } : {})} />;
  }
  render(<Harness />);
  const toggle = screen.getByRole("button", { name: "Collapse Contents" });
  expect(toggle).toHaveTextContent("📖");
  expect(document.getElementById(toggle.getAttribute("aria-controls")!)).toContainElement(screen.getByRole("button", { name: "Show scene: First scene" }));
  fireEvent.keyDown(screen.getByRole("button", { name: "Show scene: First scene" }), { key: "Escape" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(toggle).toHaveFocus();
  expect(selected).not.toHaveBeenCalled();
  fireEvent.click(toggle);
  expect(screen.getByRole("button", { name: "Show scene: First scene" })).toHaveAttribute("aria-current", "true");
});
it.each([false, true])("dismisses after compact selection with controlled=%s", controlled => {
  vi.stubGlobal("matchMedia", () => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  const selected = vi.fn();
  const externalRef = createRef<HTMLButtonElement>();
  function Harness() {
    const [expanded, setExpanded] = useState(false);
    return <Contents entries={entries} selectedId="one" onSelect={selected} visible compact
      toggleRef={externalRef} {...(controlled ? { expanded, onExpandedChange: setExpanded } : {})} />;
  }
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "Expand Contents" }));
  fireEvent.click(screen.getByRole("button", { name: "Show scene: First scene" }));
  expect(selected).toHaveBeenCalledExactlyOnceWith("one");
  expect(externalRef.current).toHaveAttribute("aria-expanded", "false");
  expect(externalRef.current).toHaveFocus();
});
it("keeps desktop selection open and mounted panel IDs unique", () => {
  render(<><Contents entries={entries} selectedId="one" onSelect={vi.fn()} visible />
    <Contents entries={entries} selectedId="one" onSelect={vi.fn()} visible /></>);
  const decks = screen.getAllByRole("navigation", { name: "Contents" });
  const toggles = decks.map(deck => within(deck).getByRole("button", { name: "Collapse Contents" }));
  expect(toggles[0].getAttribute("aria-controls")).not.toBe(toggles[1].getAttribute("aria-controls"));
  fireEvent.click(within(decks[0]).getByRole("button", { name: "Show scene: First scene" }));
  expect(toggles[0]).toHaveAttribute("aria-expanded", "true");
});
it("returns focus to a visible surface opener when a compact overlay closes", () => {
  const opener = createRef<HTMLButtonElement>();
  function Harness() {
    const [expanded, setExpanded] = useState(true);
    return <><button ref={opener}>Surface opener</button><Contents entries={entries}
      selectedId="one" onSelect={vi.fn()} visible expanded={expanded}
      onExpandedChange={setExpanded} compact dismissFocusRef={opener} /></>;
  }
  render(<Harness />);
  fireEvent.keyDown(screen.getByRole("button", { name: "Show scene: First scene" }), { key: "Escape" });
  expect(opener.current).toHaveFocus();
  expect(screen.getByRole("button", { name: "Expand Contents" })).toHaveAttribute("aria-expanded", "false");
});

it("uses the visible fallback when the compact surface opener is hidden", () => {
  const hiddenOpener = createRef<HTMLButtonElement>();
  const fallback = createRef<HTMLButtonElement>();
  render(<><button ref={hiddenOpener} hidden>Hidden opener</button>
    <button ref={fallback}>More</button><Contents entries={entries} selectedId="one"
      onSelect={vi.fn()} visible compact expanded onExpandedChange={vi.fn()}
      dismissFocusRef={hiddenOpener} fallbackDismissFocusRef={fallback} /></>);
  fireEvent.keyDown(screen.getByRole("button", { name: "Collapse Contents" }), { key: "Escape" });
  expect(fallback.current).toHaveFocus();
});
