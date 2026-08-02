import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentInteractionProvider } from "./agentInteraction/AgentInteractionProvider";
import { ROUTE_COMPATIBILITY_PUBLICATIONS } from "./agentInteraction/surfaceInteractionCompat";
import { usePublishSurfaceInteraction } from "./agentInteraction/usePublishSurfaceInteraction";
import { useAgentInteraction } from "./agentInteraction/useAgentInteraction";
import type { SurfaceInteractionPublication } from "./surfaceInteraction/types";

function RouteLeaseProbe({ publication }: { publication: SurfaceInteractionPublication | null }) {
  usePublishSurfaceInteraction(publication);
  const { surfaceInteractionPublication } = useAgentInteraction();
  return (
    <div data-testid="lease-probe">
      {surfaceInteractionPublication?.identity.surfaceId ?? "none"}
      :
      {surfaceInteractionPublication?.label ?? "empty"}
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
    expect(screen.getByTestId("lease-probe").textContent).toBe("index:Command Board");
  });

  it("binds an exact surface compatibility lease", () => {
    render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={ROUTE_COMPATIBILITY_PUBLICATIONS.surface} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("surface:Live Control");
  });

  it("binds an exact tiptap spike compatibility lease", () => {
    render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={ROUTE_COMPATIBILITY_PUBLICATIONS.tiptapCalloutSpike} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("tiptap-callout-spike:Tiptap Callout Spike");
  });

  it("binds explicit empty lease when publication is null", () => {
    render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={null} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("none:empty");
  });

  it("treats delimiter-colliding identities as distinct binds", () => {
    // Literal instance keys that collide under `${surfaceId}:${instanceKey}`:
    // "a:b"+"c" and "a"+"b:c" both join to "a:b:c".
    const publicationA: SurfaceInteractionPublication = {
      ...ROUTE_COMPATIBILITY_PUBLICATIONS.index,
      surfaceId: "a:b",
      label: "Identity A",
      identity: { surfaceId: "a:b", instanceKey: "c" },
    };
    const publicationB: SurfaceInteractionPublication = {
      ...ROUTE_COMPATIBILITY_PUBLICATIONS.index,
      surfaceId: "a",
      label: "Identity B",
      identity: { surfaceId: "a", instanceKey: "b:c" },
    };
    const { rerender } = render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={publicationA} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("a:b:Identity A");

    rerender(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={publicationB} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("a:Identity B");
  });

  it("binds when only surfaceId changes under an equal instanceKey", () => {
    const publicationA: SurfaceInteractionPublication = {
      ...ROUTE_COMPATIBILITY_PUBLICATIONS.index,
      surfaceId: "a",
      label: "Surface A",
      identity: { surfaceId: "a", instanceKey: "shared" },
    };
    const publicationB: SurfaceInteractionPublication = {
      ...ROUTE_COMPATIBILITY_PUBLICATIONS.index,
      surfaceId: "b",
      label: "Surface B",
      identity: { surfaceId: "b", instanceKey: "shared" },
    };
    const { rerender } = render(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={publicationA} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("a:Surface A");

    rerender(
      <AgentInteractionProvider>
        <RouteLeaseProbe publication={publicationB} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("lease-probe").textContent).toBe("b:Surface B");
  });
});
