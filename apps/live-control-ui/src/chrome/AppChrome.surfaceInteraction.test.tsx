import { readFileSync } from "node:fs";
import { join } from "node:path";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { ROUTE_COMPATIBILITY_PUBLICATIONS } from "../agentInteraction/surfaceInteractionCompat";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { ToolHost } from "../surfaceInteraction/toolHost/ToolHost";
import { AppChrome } from "./AppChrome";

function openToolsDrawer() {
  fireEvent.click(screen.getByRole("button", { name: "Tools" }));
}

function IndexRouteChromeHarness({
  pageActions,
  editorTools,
}: {
  pageActions?: Parameters<typeof AppChrome>[0]["pageActions"];
  editorTools?: Parameters<typeof AppChrome>[0]["editorTools"];
}) {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
  return (
    <>
      <AppChrome activeRoute="index" pageActions={pageActions} editorTools={editorTools}>
        <main>content</main>
      </AppChrome>
      <ToolHost />
    </>
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
    <>
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
      <ToolHost />
    </>
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
  it("preserves Tool host page-tool grouping from AppChrome pageActions", () => {
    render(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness
          pageActions={[{ id: "launch", label: "Launch", onClick: () => {} }]}
        />
      </AgentInteractionProvider>,
    );

    openToolsDrawer();
    expect(screen.getAllByText("Page tools").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Launch" })).toBeTruthy();
  });

  it("preserves Edit host section labels from AppChrome editorTools via publication", () => {
    const publication = makeSharedInstancePublication("doc", "Doc surface", {
      canvasId: "canvas-1",
      workObject: { kind: "document", id: "doc-a" },
    });
    render(
      <AgentInteractionProvider>
        <PublicationChromeHarness
          publication={publication}
          editorTools={{
            sections: [{
              id: "callouts",
              title: "Callouts",
              defaultOpen: true,
              actions: [{ id: "note", label: "Note", onClick: () => {} }],
            }],
          }}
        />
      </AgentInteractionProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByText("Callouts")).toBeTruthy();
    expect(screen.getByTestId("surface-edit-host")).toBeInTheDocument();
  });

  it("renders AppChrome actions under an active route lease publisher", () => {
    render(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness pageActions={[{ id: "launch", label: "Launch", onClick: vi.fn() }]} />
      </AgentInteractionProvider>,
    );
    openToolsDrawer();
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
    openToolsDrawer();
    fireEvent.click(screen.getByRole("button", { name: "Launch" }));
    expect(callback1).toHaveBeenCalledTimes(1);
    expect(callback2).not.toHaveBeenCalled();

    rerender(
      <AgentInteractionProvider>
        <IndexRouteChromeHarness pageActions={[{ id: "launch", label: "Launch", onClick: callback2 }]} />
      </AgentInteractionProvider>,
    );
    openToolsDrawer();
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
    openToolsDrawer();
    fireEvent.click(screen.getByRole("button", { name: "Launch" }));
    expect(onClick).toHaveBeenCalledTimes(1);

    rerender(
      <AgentInteractionProvider>
        <PublicationChromeHarness publication={publicationB} pageActions={pageActions} />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("effective-surface").textContent).toBe("b");
    expect(screen.getByTestId("tool-ids").textContent).toBe("launch");
    openToolsDrawer();
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
    // Work-object change resets Edit host open state to the overlay default (closed).
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
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
    openToolsDrawer();
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
    openToolsDrawer();
    const nextButton = screen.getByRole("button", { name: "c" });
    expect(nextButton).not.toBeDisabled();
    fireEvent.click(nextButton);
    expect(shared).toHaveBeenCalledTimes(2);
  });

  it("keeps a singular EditHost: AppChrome source has no EditToolbox ownership", () => {
    const source = readFileSync(join(__dirname, "AppChrome.tsx"), "utf8");
    expect(source).not.toMatch(/\bEditToolbox\b/);
    expect(source).not.toMatch(/\bEditToolboxDrawer\b/);
    expect(source).not.toMatch(/\bGuardedActionButton\b/);
    expect(source).not.toMatch(/app-edit-toolbox-toggle/);
    expect(source).toMatch(/EditHost/);
    expect(source).toMatch(/legacyPanels/);
  });
});
