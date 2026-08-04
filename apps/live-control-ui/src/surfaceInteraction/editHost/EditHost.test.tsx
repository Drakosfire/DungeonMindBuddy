import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { usePublishSurfaceInteraction } from "../../agentInteraction/usePublishSurfaceInteraction";
import { buildSurfaceInteractionIdentity } from "../surfaceIdentity";
import type {
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionPublication,
} from "../types";
import { EditHost, type LegacyEditPanelAttachment } from "./EditHost";

function makePublication(
  overrides: Partial<SurfaceInteractionPublication> = {},
): SurfaceInteractionPublication {
  return {
    surfaceId: "test",
    label: "Test",
    identity: buildSurfaceInteractionIdentity({ surfaceId: "test", instanceParts: ["edit-host"] }),
    canvas: {
      canvasId: "markdown-canvas",
      workObject: { kind: "document", id: "doc-1" },
    },
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
    ...overrides,
  };
}

function makeEdit(
  overrides: Partial<SurfaceInteractionEditCommandContribution> &
    Pick<SurfaceInteractionEditCommandContribution, "id" | "label">,
): SurfaceInteractionEditCommandContribution {
  return {
    placement: { groupId: null, groupLabel: null, groupOrder: 0, itemOrder: 0 },
    availability: { status: "enabled" },
    target: { kind: "document", id: "doc-1" },
    invoke: vi.fn(),
    ...overrides,
  };
}

function Publisher({ publication }: { publication: SurfaceInteractionPublication }) {
  usePublishSurfaceInteraction(publication);
  return null;
}

function renderEditHost(
  children: ReactNode,
  props: {
    layout?: "overlay" | "dock";
    legacyPanels?: readonly LegacyEditPanelAttachment[];
  } = {},
) {
  return render(
    <AgentInteractionProvider>
      {children}
      <EditHost
        layout={props.layout ?? "overlay"}
        legacyPanels={props.legacyPanels}
      />
    </AgentInteractionProvider>,
  );
}

describe("EditHost", () => {
  it("renders nothing when the effective publication has no matching edit inventory", () => {
    renderEditHost(<Publisher publication={makePublication()} />);
    expect(screen.queryByTestId("surface-edit-host")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("omits commands whose target does not match the canvas work object", async () => {
    const user = userEvent.setup();
    const matching = vi.fn();
    const mismatched = vi.fn();
    const publication = makePublication({
      editCommands: [
        makeEdit({ id: "save", label: "Save", invoke: matching }),
        makeEdit({
          id: "stale",
          label: "Stale",
          target: { kind: "document", id: "other" },
          invoke: mismatched,
        }),
      ],
    });

    renderEditHost(<Publisher publication={publication} />);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stale" })).not.toBeInTheDocument();
  });

  it("keeps the host open after invoking an Edit command", async () => {
    const user = userEvent.setup();
    const invoke = vi.fn();
    const publication = makePublication({
      editCommands: [makeEdit({ id: "save", label: "Save", invoke })],
    });

    renderEditHost(<Publisher publication={publication} />);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(invoke).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Close Edit" })).toBeInTheDocument();
    expect(screen.getByTestId("surface-edit-host")).toHaveClass("open");
  });

  it("closes on Escape and restores focus to the Edit toggle", async () => {
    const user = userEvent.setup();
    const publication = makePublication({
      editCommands: [makeEdit({ id: "save", label: "Save" })],
    });

    renderEditHost(<Publisher publication={publication} />);
    const toggle = screen.getByRole("button", { name: "Edit" });
    await user.click(toggle);

    const stopImmediatePropagation = vi.spyOn(Event.prototype, "stopImmediatePropagation");
    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(toggle).toHaveAttribute("aria-expanded", "false");
    });
    expect(stopImmediatePropagation).toHaveBeenCalled();
    expect(document.activeElement).toBe(toggle);
  });

  it("defaults dock layout open and overlay layout closed", () => {
    const publication = makePublication({
      editCommands: [makeEdit({ id: "save", label: "Save" })],
    });

    const { unmount } = renderEditHost(
      <Publisher publication={publication} />,
      { layout: "dock" },
    );
    expect(screen.getByRole("button", { name: "Close Edit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    unmount();

    renderEditHost(<Publisher publication={publication} />, { layout: "overlay" });
    expect(screen.getByRole("button", { name: "Edit" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Close Edit" })).not.toBeInTheDocument();
  });

  it("exposes aria-pressed and disabled reasons from contribution fields", async () => {
    const user = userEvent.setup();
    const publication = makePublication({
      editCommands: [
        makeEdit({
          id: "lock",
          label: "Lock",
          pressed: true,
        }),
        makeEdit({
          id: "save",
          label: "Save",
          placement: {
            groupId: null,
            groupLabel: null,
            groupOrder: 0,
            itemOrder: 1,
          },
          availability: { status: "disabled", disabledReason: "Nothing to save" },
        }),
      ],
    });

    renderEditHost(<Publisher publication={publication} />);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Lock" })).toHaveAttribute("aria-pressed", "true");
    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toBeDisabled();
    expect(save).toHaveAttribute("title", "Nothing to save");
  });

  it("renders matching legacy panels and panel-only groups", async () => {
    const user = userEvent.setup();
    const publication = makePublication({
      editCommands: [
        makeEdit({
          id: "note",
          label: "Note",
          placement: {
            groupId: "callouts",
            groupLabel: "Callouts",
            groupOrder: 0,
            itemOrder: 0,
            groupDefaultOpen: true,
          },
        }),
      ],
    });
    const legacyPanels: LegacyEditPanelAttachment[] = [
      {
        groupId: "callouts",
        groupLabel: "Callouts",
        groupOrder: 0,
        groupDefaultOpen: true,
        target: { kind: "document", id: "doc-1" },
        panel: <div data-testid="callouts-panel">Search</div>,
      },
      {
        groupId: "panel-only",
        groupLabel: "Panel Only",
        groupOrder: 1,
        target: { kind: "document", id: "doc-1" },
        panel: <div data-testid="panel-only">Only</div>,
      },
      {
        groupId: "mismatched",
        groupLabel: "Mismatched",
        groupOrder: 2,
        target: { kind: "document", id: "other" },
        panel: <div data-testid="mismatched-panel">Nope</div>,
      },
    ];

    renderEditHost(<Publisher publication={publication} />, { legacyPanels });
    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByTestId("callouts-panel")).toBeInTheDocument();
    expect(screen.getByTestId("panel-only")).toBeInTheDocument();
    expect(screen.queryByTestId("mismatched-panel")).not.toBeInTheDocument();
  });

  it("resets open state to layout default on work-object change", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [publication, setPublication] = useState(
        makePublication({
          editCommands: [makeEdit({ id: "save", label: "Save" })],
        }),
      );
      useEffect(() => {
        (window as unknown as { __setEditPub: typeof setPublication }).__setEditPub =
          setPublication;
      }, []);
      return (
        <>
          <Publisher publication={publication} />
          <EditHost layout="overlay" />
        </>
      );
    }

    render(
      <AgentInteractionProvider>
        <Harness />
      </AgentInteractionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Close Edit" })).toBeInTheDocument();

    (window as unknown as {
      __setEditPub: (publication: SurfaceInteractionPublication) => void;
    }).__setEditPub(
      makePublication({
        canvas: {
          canvasId: "markdown-canvas",
          workObject: { kind: "document", id: "doc-2" },
        },
        editCommands: [
          makeEdit({
            id: "save",
            label: "Save",
            target: { kind: "document", id: "doc-2" },
          }),
        ],
      }),
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Edit" })).toHaveAttribute(
        "aria-expanded",
        "false",
      );
    });
  });

  it("does not resurrect prior open state after inventory returns", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [publication, setPublication] = useState(
        makePublication({
          editCommands: [makeEdit({ id: "save", label: "Save" })],
        }),
      );
      useEffect(() => {
        (window as unknown as { __setEditPub: typeof setPublication }).__setEditPub =
          setPublication;
      }, []);
      return (
        <>
          <Publisher publication={publication} />
          <EditHost layout="overlay" />
        </>
      );
    }

    render(
      <AgentInteractionProvider>
        <Harness />
      </AgentInteractionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Close Edit" })).toBeInTheDocument();

    (window as unknown as {
      __setEditPub: (publication: SurfaceInteractionPublication) => void;
    }).__setEditPub(makePublication({ editCommands: [] }));

    await waitFor(() => {
      expect(screen.queryByTestId("surface-edit-host")).not.toBeInTheDocument();
    });

    (window as unknown as {
      __setEditPub: (publication: SurfaceInteractionPublication) => void;
    }).__setEditPub(
      makePublication({
        editCommands: [makeEdit({ id: "save", label: "Save" })],
      }),
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Edit" })).toHaveAttribute(
        "aria-expanded",
        "false",
      );
    });
    expect(screen.queryByRole("button", { name: "Close Edit" })).not.toBeInTheDocument();
  });
});
