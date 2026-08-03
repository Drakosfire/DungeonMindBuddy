import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useRef, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  AgentInteractionProvider,
  useAgentInteraction,
} from "../../agentInteraction/AgentInteractionProvider";
import {
  buildAppChromeCompatibilityFragment,
  ROUTE_COMPATIBILITY_PUBLICATIONS,
} from "../../agentInteraction/surfaceInteractionCompat";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import type { AppChromeAction } from "../../chrome/AppChrome";
import type { SurfaceConfig } from "../../planSurface/types";
import { fixturePlanSessionDescriptor } from "../../planSurface/config/planSessionDescriptor";
import { AgentInteractionProjectionTestHost } from "../../planSurface/projection/projectionTestHost";
import { buildSurfaceInteractionIdentity } from "../surfaceIdentity";
import type { SurfaceInteractionPublication, SurfaceInteractionToolContribution } from "../types";
import { ToolHost } from "./ToolHost";

function SurfaceRoutePublisher() {
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.surface);
  return null;
}

function NativeToolsPublisher({ publication }: { publication: SurfaceInteractionPublication }) {
  usePublishSurfaceInteraction(publication);
  return null;
}

function makeNativePublication(
  tools: readonly SurfaceInteractionToolContribution[],
  instanceParts: readonly (string | number | boolean | null)[] = ["tool-host"],
): SurfaceInteractionPublication {
  return {
    surfaceId: "test",
    label: "Test",
    identity: buildSurfaceInteractionIdentity({ surfaceId: "test", instanceParts }),
    canvas: null,
    agentContext: null,
    tools,
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
}

function makeTool(
  overrides: Partial<SurfaceInteractionToolContribution> &
    Pick<SurfaceInteractionToolContribution, "id" | "label">,
): SurfaceInteractionToolContribution {
  return {
    placement: {
      groupId: null,
      groupLabel: null,
      groupOrder: 0,
      itemOrder: 0,
    },
    availability: { status: "enabled" },
    activation: { kind: "command", invoke: vi.fn() },
    ...overrides,
  };
}

function renderToolHost(children: ReactNode) {
  return render(
    <AgentInteractionProvider>
      {children}
      <ToolHost />
    </AgentInteractionProvider>,
  );
}

describe("ToolHost", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when the effective publication has no tools", () => {
    const buildConfig: SurfaceConfig = {
      id: "build",
      label: "Build",
      context: null,
      tools: [],
      canvas: { documentId: null },
      theme: {},
    };

    renderToolHost(
      <AgentInteractionProjectionTestHost config={buildConfig}>
        <span>Build surface</span>
      </AgentInteractionProjectionTestHost>,
    );

    expect(screen.queryByTestId("surface-tool-host")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  });

  it("groups tools by placement order rather than label text", async () => {
    const user = userEvent.setup();
    const publication = makeNativePublication([
      makeTool({
        id: "z-item",
        label: "Zulu",
        placement: {
          groupId: "group-b",
          groupLabel: "Group B",
          groupOrder: 2,
          itemOrder: 0,
        },
      }),
      makeTool({
        id: "a-item",
        label: "Alpha",
        placement: {
          groupId: "group-a",
          groupLabel: "Group A",
          groupOrder: 1,
          itemOrder: 1,
        },
      }),
      makeTool({
        id: "b-item",
        label: "Bravo",
        placement: {
          groupId: "group-a",
          groupLabel: "Group A",
          groupOrder: 1,
          itemOrder: 0,
        },
      }),
    ]);

    renderToolHost(<NativeToolsPublisher publication={publication} />);

    await user.click(screen.getByRole("button", { name: "Tools" }));

    const drawer = screen.getByLabelText("Tools toolbar");
    const details = drawer.querySelectorAll(".app-tools-fold");
    expect(details).toHaveLength(2);
    expect(details[0]?.querySelector("summary")?.textContent).toBe("Group A");
    expect(details[1]?.querySelector("summary")?.textContent).toBe("Group B");

    const groupADetails = details[0] as HTMLElement;
    const groupAButtons = within(groupADetails).getAllByRole("button");
    expect(groupAButtons.map((button) => button.textContent?.replace(/\s+/g, " ").trim())).toEqual([
      "Bravo",
      "Alpha",
    ]);
  });

  it("does not activate disabled tools", async () => {
    const user = userEvent.setup();
    const invoke = vi.fn();
    const publication = makeNativePublication([
      makeTool({
        id: "disabled-tool",
        label: "Disabled",
        availability: { status: "disabled", disabledReason: "Not ready" },
        activation: { kind: "command", invoke },
      }),
    ]);

    renderToolHost(<NativeToolsPublisher publication={publication} />);

    await user.click(screen.getByRole("button", { name: "Tools" }));
    const disabledButton = screen.getByRole("button", { name: "Disabled" });
    expect(disabledButton).toBeDisabled();

    await user.click(disabledButton);
    expect(invoke).not.toHaveBeenCalled();
  });

  it("closes on Escape in capture phase and returns focus to the toggle", async () => {
    const user = userEvent.setup();
    const publication = makeNativePublication([
      makeTool({ id: "alpha", label: "Alpha" }),
    ]);

    renderToolHost(<NativeToolsPublisher publication={publication} />);

    const toggle = screen.getByRole("button", { name: "Tools" });
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    const stopImmediatePropagation = vi.spyOn(Event.prototype, "stopImmediatePropagation");
    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(toggle).toHaveAttribute("aria-expanded", "false");
    });
    expect(stopImmediatePropagation).toHaveBeenCalled();
    expect(document.activeElement).toBe(toggle);
  });

  it("disappears after the lease identity is replaced with an empty-tools surface", async () => {
    const user = userEvent.setup();
    const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });
    const planConfig: SurfaceConfig = {
      id: "plan",
      label: "Plan",
      context: {
        campaignId: sessionDescriptor.campaignId,
        headerLabel: sessionDescriptor.planningDocument.title,
        ingestSession: 21,
        liveSession: 22,
      },
      tools: [{ id: "recap", label: "Recap", size: "wide" }],
      canvas: { documentId: sessionDescriptor.planningDocument.documentId },
      theme: {},
      sessionDescriptor,
    };
    const buildConfig: SurfaceConfig = {
      id: "build",
      label: "Build",
      context: null,
      tools: [],
      canvas: { documentId: null },
      theme: {},
    };

    const { rerender } = render(
      <AgentInteractionProjectionTestHost config={planConfig}>
        <span>Plan</span>
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(await screen.findByRole("button", { name: "Tools" }));
    expect(screen.getByRole("button", { name: "Recap" })).toBeInTheDocument();

    rerender(
      <AgentInteractionProjectionTestHost config={buildConfig}>
        <span>Build</span>
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    expect(screen.queryByTestId("surface-tool-host")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tools" })).not.toBeInTheDocument();
  });

  it("runs the replacement invoke for a same-id command tool", async () => {
    const user = userEvent.setup();
    const invokeA = vi.fn();
    const invokeB = vi.fn();
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;

    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    function PageActionsBridge({ pageActions }: { pageActions: AppChromeAction[] }) {
      const { publishAppChromeCompatibility, surfaceInteractionBasePublication } = useAgentInteraction();
      const pageActionsRef = useRef(pageActions);
      pageActionsRef.current = pageActions;
      useEffect(() => {
        if (!surfaceInteractionBasePublication) return;
        return publishAppChromeCompatibility(
          buildAppChromeCompatibilityFragment({
            pageActions: pageActionsRef.current,
            editorTools: null,
            basePublication: surfaceInteractionBasePublication,
          }),
        );
      }, [pageActions, publishAppChromeCompatibility, surfaceInteractionBasePublication]);
      return null;
    }

    const { rerender } = render(
      <AgentInteractionProvider>
        <SurfaceRoutePublisher />
        <PageActionsBridge pageActions={[{ id: "inspector", label: "Inspector", onClick: invokeA }]} />
        <CaptureApi />
        <ToolHost />
      </AgentInteractionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Inspector" }));
    expect(invokeA).toHaveBeenCalledTimes(1);
    expect(invokeB).not.toHaveBeenCalled();

    rerender(
      <AgentInteractionProvider>
        <SurfaceRoutePublisher />
        <PageActionsBridge pageActions={[{ id: "inspector", label: "Inspector", onClick: invokeB }]} />
        <CaptureApi />
        <ToolHost />
      </AgentInteractionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Inspector" }));
    expect(invokeA).toHaveBeenCalledTimes(1);
    expect(invokeB).toHaveBeenCalledTimes(1);
    expect(hostApi).not.toBeNull();
  });

  it("opens projection tools through the host API and closes the launcher", async () => {
    const user = userEvent.setup();
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });
    const planConfig: SurfaceConfig = {
      id: "plan",
      label: "Plan",
      context: {
        campaignId: sessionDescriptor.campaignId,
        headerLabel: sessionDescriptor.planningDocument.title,
        ingestSession: 21,
        liveSession: 22,
      },
      tools: [{ id: "recap", label: "Recap", size: "wide" }],
      canvas: { documentId: sessionDescriptor.planningDocument.documentId },
      theme: {},
      sessionDescriptor,
    };

    render(
      <AgentInteractionProjectionTestHost config={planConfig}>
        <CaptureApi />
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    const toggle = await screen.findByRole("button", { name: "Tools" });
    await user.click(toggle);
    await user.click(screen.getByRole("button", { name: "Recap" }));

    await waitFor(() => {
      expect(hostApi!.active?.key).toBe("recap");
    });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
