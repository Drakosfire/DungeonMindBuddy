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
import { getRecapArtifacts } from "../../api/liveApi";
import type { RecapArtifactsListResponse } from "../../api/types";
import type { AppChromeAction } from "../../chrome/AppChrome";
import type { SurfaceConfig } from "../../planSurface/types";
import { fixturePlanSessionDescriptor } from "../../planSurface/config/planSessionDescriptor";
import { AgentInteractionProjectionTestHost } from "../../planSurface/projection/projectionTestHost";
import { LegacyProjectionHostAdapter } from "../../planSurface/projection/LegacyProjectionHostAdapter";
import { buildSurfaceInteractionIdentity } from "../surfaceIdentity";
import type { SurfaceInteractionPublication, SurfaceInteractionToolContribution } from "../types";
import { ToolHost } from "./ToolHost";

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    getRecapArtifacts: vi.fn(async () => ({ records: [] })),
  };
});

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
    vi.mocked(getRecapArtifacts).mockResolvedValue({ records: [] });
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
            editCommandTarget: null,
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
    const toolboxDrawer = screen.getByLabelText("Tools toolbar");
    await user.click(within(toolboxDrawer).getByRole("button", { name: "Recap" }));

    await waitFor(() => {
      expect(hostApi!.active?.key).toBe("recap");
    });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("treats delimiter-collision identities as distinct and closes the drawer on switch", async () => {
    const user = userEvent.setup();
    const identityA = buildSurfaceInteractionIdentity({
      surfaceId: "a",
      instanceParts: ["b\u001fc"],
    });
    const identityB = buildSurfaceInteractionIdentity({
      surfaceId: "a\u001fb",
      instanceParts: ["c"],
    });
    const publicationA = makeNativePublication(
      [makeTool({ id: "alpha", label: "Alpha" })],
      ["b\u001fc"],
    );
    publicationA.identity = identityA;
    publicationA.surfaceId = identityA.surfaceId;
    const publicationB = makeNativePublication(
      [makeTool({ id: "beta", label: "Beta" })],
      ["c"],
    );
    publicationB.identity = identityB;
    publicationB.surfaceId = identityB.surfaceId;

    function SwitchingPublisher({
      publication,
    }: {
      publication: SurfaceInteractionPublication;
    }) {
      usePublishSurfaceInteraction(publication);
      return null;
    }

    const { rerender } = render(
      <AgentInteractionProvider>
        <SwitchingPublisher publication={publicationA} />
        <ToolHost />
      </AgentInteractionProvider>,
    );

    const toggle = screen.getByRole("button", { name: "Tools" });
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Alpha" })).toBeInTheDocument();

    rerender(
      <AgentInteractionProvider>
        <SwitchingPublisher publication={publicationB} />
        <ToolHost />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    });
    const nextToggle = screen.getByRole("button", { name: "Tools" });
    expect(nextToggle).toHaveAttribute("aria-expanded", "false");
    await user.click(nextToggle);
    expect(screen.getByRole("button", { name: "Beta" })).toBeInTheDocument();
  });

  it("closes when tools become empty under the same identity and stays closed when tools return", async () => {
    const user = userEvent.setup();
    const identity = buildSurfaceInteractionIdentity({
      surfaceId: "test",
      instanceParts: ["empty-restore"],
    });
    const withTools = makeNativePublication([makeTool({ id: "alpha", label: "Alpha" })], ["empty-restore"]);
    withTools.identity = identity;
    const emptyTools: SurfaceInteractionPublication = {
      ...withTools,
      tools: [],
    };

    function Publisher({ publication }: { publication: SurfaceInteractionPublication }) {
      usePublishSurfaceInteraction(publication);
      return null;
    }

    const { rerender } = renderToolHost(<Publisher publication={withTools} />);

    const toggle = screen.getByRole("button", { name: "Tools" });
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    rerender(
      <AgentInteractionProvider>
        <Publisher publication={emptyTools} />
        <ToolHost />
      </AgentInteractionProvider>,
    );
    expect(screen.queryByTestId("surface-tool-host")).not.toBeInTheDocument();

    rerender(
      <AgentInteractionProvider>
        <Publisher publication={withTools} />
        <ToolHost />
      </AgentInteractionProvider>,
    );

    const restoredToggle = screen.getByRole("button", { name: "Tools" });
    expect(restoredToggle).toHaveAttribute("aria-expanded", "false");
  });

  it("routes the first Plan Recap click through adapter URL policy", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/plan");

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
        <LegacyProjectionHostAdapter />
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    await user.click(await screen.findByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Recap" }));

    await waitFor(() => {
      expect(window.location.search).toContain("tool=recap");
    });
  });

  it("does not restore toggle focus after a projection launch", async () => {
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

    render(
      <AgentInteractionProjectionTestHost config={planConfig}>
        <LegacyProjectionHostAdapter />
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    const toggle = await screen.findByRole("button", { name: "Tools" });
    await user.click(toggle);
    const toolboxDrawer = screen.getByLabelText("Tools toolbar");
    await user.click(within(toolboxDrawer).getByRole("button", { name: "Recap" }));

    await waitFor(() => {
      expect(toggle).toHaveAttribute("aria-expanded", "false");
    });
    expect(document.activeElement).not.toBe(toggle);
  });

  it("opens native publication projection tools without legacy projection surface", async () => {
    const user = userEvent.setup();
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    const publication = makeNativePublication([
      makeTool({
        id: "native-recap",
        label: "Native Recap",
        activation: { kind: "projection", projectionId: "native-recap" },
      }),
    ]);
    publication.projections = [
      {
        id: "native-recap",
        kind: "tool",
        preferredSize: "wide",
        bindingIds: [],
      },
    ];

    renderToolHost(
      <>
        <CaptureApi />
        <NativeToolsPublisher publication={publication} />
      </>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Native Recap" }));

    await waitFor(() => {
      expect(hostApi!.active?.key).toBe("native-recap");
    });
  });

  it("passes Tool id when it differs from activation.projectionId", async () => {
    const user = userEvent.setup();
    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    const publication = makeNativePublication([
      makeTool({
        id: "find-existing",
        label: "Find Existing",
        activation: { kind: "projection", projectionId: "graph-reference-search" },
      }),
    ]);
    publication.projections = [
      {
        id: "graph-reference-search",
        kind: "tool",
        preferredSize: "wide",
        bindingIds: [],
      },
    ];

    renderToolHost(
      <>
        <CaptureApi />
        <NativeToolsPublisher publication={publication} />
      </>,
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Find Existing" }));

    await waitFor(() => {
      expect(hostApi!.active).toEqual({
        kind: "tool",
        key: "graph-reference-search",
        size: "wide",
        title: "Find Existing",
      });
    });
    expect(screen.getByRole("button", { name: "Tools" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("keeps the launcher open until async compatibility activation settles", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/plan");

    let resolveLookup!: (value: RecapArtifactsListResponse) => void;
    vi.mocked(getRecapArtifacts).mockImplementation(
      () =>
        new Promise<RecapArtifactsListResponse>((resolve) => {
          resolveLookup = resolve;
        }),
    );

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
        <LegacyProjectionHostAdapter />
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    const toggle = await screen.findByRole("button", { name: "Tools" });
    await user.click(toggle);
    const toolboxDrawer = screen.getByLabelText("Tools toolbar");
    await user.click(within(toolboxDrawer).getByRole("button", { name: "Recap" }));

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(window.location.search).not.toContain("tool=recap");

    resolveLookup({ records: [] });

    await waitFor(() => {
      expect(toggle).toHaveAttribute("aria-expanded", "false");
    });
    await waitFor(() => {
      expect(window.location.search).toContain("tool=recap");
    });
  });

  it("keeps the launcher open and skips URL commit when async open loses tool auth", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/plan");

    let resolveLookup!: (value: RecapArtifactsListResponse) => void;
    vi.mocked(getRecapArtifacts).mockImplementation(
      () =>
        new Promise<RecapArtifactsListResponse>((resolve) => {
          resolveLookup = resolve;
        }),
    );

    const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });
    const withRecap: SurfaceConfig = {
      id: "plan",
      label: "Plan",
      context: {
        campaignId: sessionDescriptor.campaignId,
        headerLabel: sessionDescriptor.planningDocument.title,
        ingestSession: 21,
        liveSession: 22,
      },
      tools: [
        { id: "recap", label: "Recap", size: "wide" },
        { id: "statblock", label: "Statblock", size: "wide" },
      ],
      canvas: { documentId: sessionDescriptor.planningDocument.documentId },
      theme: {},
      sessionDescriptor,
    };
    const withoutRecap: SurfaceConfig = {
      ...withRecap,
      tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
    };

    let hostApi: ReturnType<typeof useAgentInteraction> | null = null;
    function CaptureApi() {
      hostApi = useAgentInteraction();
      return null;
    }

    const { rerender } = render(
      <AgentInteractionProjectionTestHost config={withRecap}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    const toggle = await screen.findByRole("button", { name: "Tools" });
    await user.click(toggle);
    const toolboxDrawer = screen.getByLabelText("Tools toolbar");
    await user.click(within(toolboxDrawer).getByRole("button", { name: "Recap" }));

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(window.location.search).not.toContain("tool=recap");

    // Same-identity update removes Recap but retains Statblock so the launcher stays mountable.
    rerender(
      <AgentInteractionProjectionTestHost config={withoutRecap}>
        <CaptureApi />
        <LegacyProjectionHostAdapter />
        <ToolHost />
      </AgentInteractionProjectionTestHost>,
    );

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Recap" })).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Statblock" })).toBeInTheDocument();

    resolveLookup({ records: [{ session_id: "session-23" } as RecapArtifactsListResponse["records"][number]] });

    await waitFor(() => {
      expect(hostApi!.active).toBeNull();
    });
    expect(document.body).not.toHaveClass("surface-projection-open");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByTestId("surface-tool-host")).toBeInTheDocument();
    expect(window.location.search).not.toContain("tool=recap");
    expect(window.location.search).not.toContain("session-23");

    await waitFor(() => {
      const active = document.activeElement;
      expect(active).not.toBeNull();
      expect(screen.getByTestId("surface-tool-host").contains(active)).toBe(true);
    });
  });
});
