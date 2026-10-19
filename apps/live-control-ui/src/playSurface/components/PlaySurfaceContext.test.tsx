import { fireEvent, render, screen } from "@testing-library/react";
import { SurfaceContextHost, SurfaceContextProvider, SurfaceContextAction } from "../../surfaceInteraction/contextHost";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import { PlaySurfaceContext } from "./PlaySurfaceContext";
import { vi } from "vitest";

const identity = buildSurfaceInteractionIdentity({ surfaceId: "play", instanceParts: ["play", "world", "run-a", "plan", 3] });

describe("PlaySurfaceContext", () => {
  it("publishes owner contributions into the actual shared surface host and cleans them up", () => {
    const { rerender } = render(<SurfaceContextProvider>
      <SurfaceContextHost />
      <PlaySurfaceContext id="play-test-a" order={10} identity={identity}><SurfaceContextAction>Load</SurfaceContextAction></PlaySurfaceContext>
      <PlaySurfaceContext id="play-test-b" order={20} identity={identity}><SurfaceContextAction>Scenes</SurfaceContextAction></PlaySurfaceContext>
    </SurfaceContextProvider>);
    expect(screen.getByTestId("surface-context-host")).toHaveTextContent("Load");
    expect(screen.getByTestId("surface-context-host")).toHaveTextContent("Scenes");
    rerender(<SurfaceContextProvider><SurfaceContextHost /></SurfaceContextProvider>);
    expect(screen.queryByRole("button", { name: "Load" })).not.toBeInTheDocument();
  });

  it("keeps the exact active callback across A→B→A and releases the departed Run", () => {
    const invoke = vi.fn();
    function Producer({ runId }: { runId: string }) {
      const runIdentity = buildSurfaceInteractionIdentity({ surfaceId: "play", instanceParts: ["play", runId] });
      return <PlaySurfaceContext id="play-run-controls" order={20} identity={runIdentity}>
        <SurfaceContextAction onClick={() => invoke(runId)}>{`Inspect ${runId}`}</SurfaceContextAction>
      </PlaySurfaceContext>;
    }
    const view = render(<SurfaceContextProvider><SurfaceContextHost /><Producer runId="A" /></SurfaceContextProvider>);
    expect(screen.getByRole("button", { name: "Inspect A" })).toBeInTheDocument();
    view.rerender(<SurfaceContextProvider><SurfaceContextHost /><Producer runId="B" /></SurfaceContextProvider>);
    expect(screen.queryByRole("button", { name: "Inspect A" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Inspect B" }));
    view.rerender(<SurfaceContextProvider><SurfaceContextHost /><Producer runId="A" /></SurfaceContextProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Inspect A" }));
    expect(invoke.mock.calls).toEqual([["B"], ["A"]]);
  });
});
