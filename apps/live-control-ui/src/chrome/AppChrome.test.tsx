import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { PeekClaim, PeekRegionProvider } from "../surfaceInteraction/peekHost";
import { AppChrome } from "./AppChrome";

function renderIngestChrome(withPeek: boolean) {
  const onDismiss = vi.fn();
  const view = render(
    <AgentInteractionProvider>
      <PeekRegionProvider>
        <AppChrome activeRoute="ingest"><main>Recap center</main></AppChrome>
        <PeekClaim kind="world-object" active={withPeek} label="World object" onDismiss={onDismiss}>
          <p>World peek</p>
          <button type="button" onClick={onDismiss}>Close peek</button>
        </PeekClaim>
      </PeekRegionProvider>
    </AgentInteractionProvider>,
  );
  return { ...view, onDismiss };
}

function ResponsiveHarness() {
  const [open, setOpen] = useState(false);
  return (
    <AgentInteractionProvider>
      <PeekRegionProvider>
        <button type="button" onClick={() => setOpen(true)}>Open secondary</button>
        <AppChrome activeRoute="ingest">
          <main data-testid="recap-sentinel">
            Recap center
            <div data-testid="recap-scroll-region" />
          </main>
        </AppChrome>
        <PeekClaim kind="world-object" active={open} label="World object" onDismiss={() => setOpen(false)}>
          <p>World peek</p>
          <button type="button" onClick={() => setOpen(false)}>Close peek</button>
        </PeekClaim>
      </PeekRegionProvider>
    </AgentInteractionProvider>
  );
}

describe("AppChrome Ingest peek composition", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("keeps Nav outside the CENTER/PEEK workspace and collapses an empty Peek", () => {
    renderIngestChrome(false);
    const header = screen.getByTestId("app-chrome-header");
    const workspace = document.querySelector(".app-chrome-workspace");
    expect(header).not.toBeNull();
    expect(workspace).not.toBeNull();
    expect(workspace).not.toContainElement(header);
    expect(screen.getByText("Recap center")).toBeInTheDocument();
    expect(screen.getByTestId("app-peek-region")).toHaveAttribute("hidden");
  });

  it("measures the shared chrome edge and tracks wrapped navigation height", () => {
    const callbacks: ResizeObserverCallback[] = [];
    class TestResizeObserver implements ResizeObserver {
      constructor(callback: ResizeObserverCallback) {
        callbacks.push(callback);
      }
      observe(_target: Element, _options?: ResizeObserverOptions) {}
      unobserve(_target: Element) {}
      disconnect() {}
      takeRecords(): ResizeObserverEntry[] { return []; }
    }
    vi.stubGlobal("ResizeObserver", TestResizeObserver);

    const previousTop = document.documentElement.style.getPropertyValue("--app-chrome-top");
    const view = renderIngestChrome(false);
    const header = screen.getByTestId("app-chrome-header");
    let bottom = 142;
    vi.spyOn(header, "getBoundingClientRect").mockImplementation(() => ({
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: 900,
      bottom,
      width: 900,
      height: bottom,
      toJSON: () => ({}),
    }) as DOMRect);

    const measure = callbacks[callbacks.length - 1];
    expect(measure).toBeDefined();
    measure?.([], {} as ResizeObserver);
    expect(document.documentElement.style.getPropertyValue("--app-chrome-top")).toBe("142px");

    bottom = -18;
    measure?.([], {} as ResizeObserver);
    expect(document.documentElement.style.getPropertyValue("--app-chrome-top")).toBe("0px");

    bottom = 226;
    measure?.([], {} as ResizeObserver);
    expect(document.documentElement.style.getPropertyValue("--app-chrome-top")).toBe("226px");

    view.unmount();
    expect(document.documentElement.style.getPropertyValue("--app-chrome-top")).toBe(previousTop);
  });

  it("composes populated Peek beside the still-mounted CENTER", () => {
    const { onDismiss } = renderIngestChrome(true);
    expect(screen.getByText("Recap center")).toBeInTheDocument();
    expect(screen.getByTestId("app-peek-region")).not.toHaveAttribute("hidden");
    expect(screen.getByText("World peek")).toBeVisible();
    expect(screen.queryByTestId("secondary-context-dismiss")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "← Back" })).not.toBeInTheDocument();
    const workspace = document.querySelector(".app-chrome-workspace");
    expect(workspace?.querySelector(".app-chrome-center")).not.toBeNull();
    expect(workspace?.querySelector(".app-peek-region")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Close peek" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("keeps CENTER mounted and restores narrow reading position after the final dismiss", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    Object.defineProperty(window, "scrollY", { configurable: true, value: 432 });

    render(<ResponsiveHarness />);
    const sentinel = screen.getByTestId("recap-sentinel");
    const readingRegion = screen.getByTestId("recap-scroll-region");
    readingRegion.scrollTop = 275;
    fireEvent.scroll(readingRegion);
    await user.click(screen.getByRole("button", { name: "Open secondary" }));
    expect(sentinel).toBeInTheDocument();
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "auto" });
    readingRegion.scrollTop = 0;

    await user.click(screen.getByRole("button", { name: "Close peek" }));
    expect(sentinel).toBeInTheDocument();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 432, behavior: "auto" });
    expect(readingRegion.scrollTop).toBe(275);
  });
});
