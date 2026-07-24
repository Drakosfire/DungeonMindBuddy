import { useState, type ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { GraphReviewWorkbenchHeaderWithActivity } from "./GraphReviewWorkbenchHeaderWithActivity";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";

describe("GraphReviewWorkbenchHeaderWithActivity", () => {
  it("does not infinite-loop when surface chrome publish re-renders the parent", async () => {
    const user = userEvent.setup();
    let publishCount = 0;

    function Host() {
      const [chrome, setChrome] = useState<ReactNode>(null);
      // Intentionally unstable — mirrors MemoryIngestPage re-creating inline
      // handlers after setSurfaceChrome triggers a parent render.
      const onOpenLoad = () => undefined;
      return (
        <div>
          <div data-testid="surface-chrome-slot">{chrome}</div>
          <GraphReviewWorkbenchHeaderWithActivity
            loaded
            sessionLabel="Session 23 · longmont-c2"
            onOpenLoad={onOpenLoad}
            sessionsLoaded
            hasAppliedLoad
            warmupStatus="idle"
            draftCampaignId="longmont-c2"
            draftSessionId="session-23"
            onSurfaceChromeChange={(next) => {
              publishCount += 1;
              setChrome(next);
            }}
          />
        </div>
      );
    }

    renderGraphReviewLiveHarness({ children: <Host /> });

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument(),
    );

    // A bounded publish/cleanup pair is fine; an infinite loop blows past this.
    expect(publishCount).toBeLessThan(10);

    await user.click(screen.getByRole("button", { name: "Load recap" }));
    expect(publishCount).toBeLessThan(10);
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
  });

  it("renders in-page when no surface chrome publisher is provided", () => {
    renderGraphReviewLiveHarness({
      children: (
        <GraphReviewWorkbenchHeaderWithActivity
          loaded={false}
          sessionLabel={null}
          onOpenLoad={vi.fn()}
          sessionsLoaded
          hasAppliedLoad={false}
          warmupStatus="idle"
          draftCampaignId="longmont-c2"
          draftSessionId="session-23"
        />
      ),
    });

    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
  });
});
