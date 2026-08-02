import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentInteractionProvider } from "./agentInteraction/AgentInteractionProvider";
import { ROUTE_COMPATIBILITY_PUBLICATIONS } from "./agentInteraction/surfaceInteractionCompat";
import { usePublishSurfaceInteraction } from "./agentInteraction/usePublishSurfaceInteraction";
import { useAgentInteraction } from "./agentInteraction/useAgentInteraction";

function RouteLeaseProbe({ publication }: { publication: typeof ROUTE_COMPATIBILITY_PUBLICATIONS.index }) {
  usePublishSurfaceInteraction(publication);
  const { surfaceInteractionPublication } = useAgentInteraction();
  return (
    <div data-testid="lease-probe">
      {surfaceInteractionPublication?.identity.surfaceId ?? "none"}
    </div>
  );
}

describe("App surface route leases", () => {
  it("binds an exact index compatibility lease", () => {
    render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={ROUTE_COMPATIBILITY_PUBLICATIONS.index} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("index");
  });

  it("binds an exact surface compatibility lease", () => {
    render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={ROUTE_COMPATIBILITY_PUBLICATIONS.surface} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("surface");
  });

  it("binds an exact tiptap spike compatibility lease", () => {
    render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={ROUTE_COMPATIBILITY_PUBLICATIONS.tiptapCalloutSpike} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("tiptap-callout-spike");
  });
});
