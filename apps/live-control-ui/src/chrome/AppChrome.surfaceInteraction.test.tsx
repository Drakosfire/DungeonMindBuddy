import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { ROUTE_COMPATIBILITY_PUBLICATIONS } from "../agentInteraction/surfaceInteractionCompat";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { AppChrome } from "./AppChrome";

function IndexRouteChromeHarness({
  pageActions,
  editorTools,
}: {
  pageActions?: Parameters<typeof AppChrome>[0]["pageActions"];
  editorTools?: Parameters<typeof AppChrome>[0]["editorTools"];
}) {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
  return (
    <AppChrome activeRoute="index" pageActions={pageActions} editorTools={editorTools}>
      <main>content</main>
    </AppChrome>
  );
}

describe("AppChrome surface interaction bridge", () => {
  it("preserves existing DOM labels and grouping", () => {
    render(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness
          pageActions={[{ id: "launch", label: "Launch", onClick: () => {} }]}
          editorTools={{
            sections: [{
              id: "callouts",
              title: "Callouts",
              actions: [{ id: "note", label: "Note", onClick: () => {} }],
            }],
          }}
        />
      </AgentInteractionProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByText("Page tools")).toBeTruthy();
    expect(screen.getByText("Callouts")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Launch" })).toBeTruthy();
  });

  it("renders AppChrome actions under an active route lease publisher", () => {
    render(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness pageActions={[{ id: "launch", label: "Launch", onClick: vi.fn() }]} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByRole("button", { name: "Launch" })).toBeTruthy();
  });

  it("republishes same-id page action when callback identity changes", () => {
    const callback1 = vi.fn();
    const callback2 = vi.fn();
    const { rerender } = render(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness pageActions={[{ id: "launch", label: "Launch", onClick: callback1 }]} />
      </AgentInteractionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Launch" }));
    expect(callback1).toHaveBeenCalledTimes(1);
    expect(callback2).not.toHaveBeenCalled();

    rerender(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness pageActions={[{ id: "launch", label: "Launch", onClick: callback2 }]} />
      </AgentInteractionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Launch" }));
    expect(callback1).toHaveBeenCalledTimes(1);
    expect(callback2).toHaveBeenCalledTimes(1);
  });
});
