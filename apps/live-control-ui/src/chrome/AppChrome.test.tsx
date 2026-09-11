import { render, screen } from "@testing-library/react";
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
        <AppChrome activeRoute="ingest"><main data-testid="recap-sentinel">Recap center</main></AppChrome>
        <PeekClaim kind="world-object" active={open} label="World object" onDismiss={() => setOpen(false)}>
          <p>World peek</p>
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

  it("composes populated Peek beside the still-mounted CENTER", () => {
    const { onDismiss } = renderIngestChrome(true);
    expect(screen.getByText("Recap center")).toBeInTheDocument();
    expect(screen.getByTestId("app-peek-region")).not.toHaveAttribute("hidden");
    expect(screen.getByText("World peek")).toBeVisible();
    screen.getByTestId("secondary-context-dismiss").querySelector("button")?.click();
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
    await user.click(screen.getByRole("button", { name: "Open secondary" }));
    expect(sentinel).toBeInTheDocument();
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "auto" });

    await user.click(screen.getByTestId("secondary-context-dismiss").querySelector("button")!);
    expect(sentinel).toBeInTheDocument();
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 432, behavior: "auto" });
  });
});
