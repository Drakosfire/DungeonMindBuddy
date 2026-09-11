import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { PeekClaim, PeekRegionProvider } from "../surfaceInteraction/peekHost";
import { AppChrome } from "./AppChrome";

function renderIngestChrome(withPeek: boolean) {
  return render(
    <AgentInteractionProvider>
      <PeekRegionProvider>
        <AppChrome activeRoute="ingest"><main>Recap center</main></AppChrome>
        <PeekClaim kind="world-object" active={withPeek}><p>World peek</p></PeekClaim>
      </PeekRegionProvider>
    </AgentInteractionProvider>,
  );
}

describe("AppChrome Ingest peek composition", () => {
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
    renderIngestChrome(true);
    expect(screen.getByText("Recap center")).toBeInTheDocument();
    expect(screen.getByTestId("app-peek-region")).not.toHaveAttribute("hidden");
    expect(screen.getByText("World peek")).toBeVisible();
  });
});
