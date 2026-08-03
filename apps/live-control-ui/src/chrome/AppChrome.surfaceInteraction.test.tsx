import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { ROUTE_COMPATIBILITY_PUBLICATIONS } from "../agentInteraction/surfaceInteractionCompat";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
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

function PublicationChromeHarness({
  publication,
  pageActions,
  editorTools,
}: {
  publication: SurfaceInteractionPublication;
  pageActions?: Parameters<typeof AppChrome>[0]["pageActions"];
  editorTools?: Parameters<typeof AppChrome>[0]["editorTools"];
}) {
  usePublishSurfaceInteraction(publication);
  const { surfaceInteractionPublication } = useAgentInteraction();
  const editTarget = surfaceInteractionPublication?.editCommands[0]?.target;
  return (
    <AppChrome activeRoute="index" pageActions={pageActions} editorTools={editorTools}>
      <main>
        <div data-testid="effective-surface">
          {surfaceInteractionPublication?.identity.surfaceId ?? "none"}
        </div>
        <div data-testid="edit-target">
          {editTarget ? `${editTarget.kind}:${editTarget.id}` : "none"}
        </div>
        <div data-testid="tool-ids">
          {(surfaceInteractionPublication?.tools.map((tool) => tool.id) ?? []).join(",")}
        </div>
      </main>
    </AppChrome>
  );
}

function makeSharedInstancePublication(
  surfaceId: string,
  label: string,
  canvas?: SurfaceInteractionPublication["canvas"],
): SurfaceInteractionPublication {
  return {
    ...ROUTE_COMPATIBILITY_PUBLICATIONS.index,
    surfaceId,
    label,
    identity: { surfaceId, instanceKey: "shared" },
    canvas: canvas ?? null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
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

  it("renders navbar write actions beside surface links", () => {
    const save = vi.fn();
    const publication = makeSharedInstancePublication("build", "Build", {
      canvasId: "markdown-canvas",
      workObject: { kind: "document", id: "doc-1" },
    });
    render(
      <AgentInteractionProvider>
        <PublicationChromeHarness
          publication={publication}
          editorTools={{
            navbarActions: [
              { id: "nav-edit", label: "Unlock editing", onClick: () => {} },
              { id: "nav-save", label: "Save", onClick: save },
            ],
          }}
        />
      </AgentInteractionProvider>,
    );

    expect(screen.getByRole("group", { name: "Surface navbar chrome" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("renders navbar graph status beside write actions", () => {
    render(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness
          editorTools={{
            navbarStatuses: [
              {
                id: "build-navbar-graph-status",
                label: "Graph · Loading…",
                tone: "loading",
              },
            ],
            navbarActions: [{ id: "nav-edit", label: "Unlock editing", onClick: () => {} }],
          }}
        />
      </AgentInteractionProvider>,
    );

    expect(screen.getByRole("status", { name: "Surface status" })).toBeTruthy();
    expect(screen.getByTestId("build-navbar-graph-status")).toHaveTextContent("Graph · Loading…");
    expect(screen.getByRole("button", { name: "Unlock editing" })).toBeTruthy();
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

  it("republishes Chrome fragment when surfaceId changes under a shared instanceKey", () => {
    const onClick = vi.fn();
    const publicationA = makeSharedInstancePublication("a", "Surface A");
    const publicationB = makeSharedInstancePublication("b", "Surface B");
    const pageActions = [{ id: "launch", label: "Launch", onClick }];

    const { rerender } = render(
      <AgentInteractionProvider>
        <PublicationChromeHarness publication={publicationA} pageActions={pageActions} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("effective-surface").textContent).toBe("a");
    expect(screen.getByTestId("tool-ids").textContent).toBe("launch");
    fireEvent.click(screen.getByRole("button", { name: "Launch" }));
    expect(onClick).toHaveBeenCalledTimes(1);

    rerender(
      <AgentInteractionProvider>
        <PublicationChromeHarness publication={publicationB} pageActions={pageActions} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("effective-surface").textContent).toBe("b");
    expect(screen.getByTestId("tool-ids").textContent).toBe("launch");
    fireEvent.click(screen.getByRole("button", { name: "Launch" }));
    expect(onClick).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Launch" })).not.toBeDisabled();
  });

  it("republishes Edit targets when the base Canvas work object changes under the same identity", () => {
    const onClick = vi.fn();
    const publicationA = makeSharedInstancePublication("doc", "Doc surface", {
      canvasId: "canvas-1",
      workObject: { kind: "document", id: "doc-a" },
    });
    const publicationB = makeSharedInstancePublication("doc", "Doc surface", {
      canvasId: "canvas-1",
      workObject: { kind: "document", id: "doc-b" },
    });
    const editorTools = {
      pinnedActions: [{ id: "bold", label: "Bold", onClick }],
    };

    const { rerender } = render(
      <AgentInteractionProvider>
        <PublicationChromeHarness
          publication={publicationA}
          editorTools={editorTools}
        />
      </AgentInteractionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByTestId("edit-target").textContent).toBe("document:doc-a");
    fireEvent.click(screen.getByRole("button", { name: "Bold" }));
    expect(onClick).toHaveBeenCalledTimes(1);

    rerender(
      <AgentInteractionProvider>
        <PublicationChromeHarness
          publication={publicationB}
          editorTools={editorTools}
        />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("edit-target").textContent).toBe("document:doc-b");
    fireEvent.click(screen.getByRole("button", { name: "Bold" }));
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  it("republishes when action id/label would collide under delimiter joining", () => {
    const shared = vi.fn();
    const { rerender } = render(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness
          pageActions={[{ id: "a", label: "b:e:c", onClick: shared }]}
        />
      </AgentInteractionProvider>,
    );
    expect(screen.getByRole("button", { name: "b:e:c" })).not.toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "b:e:c" }));
    expect(shared).toHaveBeenCalledTimes(1);

    rerender(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness
          pageActions={[{ id: "a:e:b", label: "c", onClick: shared }]}
        />
      </AgentInteractionProvider>,
    );
    const nextButton = screen.getByRole("button", { name: "c" });
    expect(nextButton).not.toBeDisabled();
    fireEvent.click(nextButton);
    expect(shared).toHaveBeenCalledTimes(2);
  });
});
