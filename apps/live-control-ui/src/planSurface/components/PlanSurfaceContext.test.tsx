import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  SurfaceContextHost,
  SurfaceContextProvider,
} from "../../surfaceInteraction/contextHost";
import {
  fixturePlanDocumentDescriptor,
  fixtureWorkspaceDocumentRecord,
} from "../config/planSessionDescriptor";
import { PlanSurfaceContext } from "./PlanSurfaceContext";

const DOC_A = "11111111-1111-4111-8111-111111111111";

function renderPlanContext(overrides: Partial<Parameters<typeof PlanSurfaceContext>[0]> = {}) {
  const onSelect = vi.fn();
  const onRetryList = vi.fn();
  const onSubmit = vi.fn();

  render(
    <SurfaceContextProvider>
      <PlanSurfaceContext
        campaignId="longmont-c2"
        liveSession={22}
        memorySession={null}
        documents={[
          fixtureWorkspaceDocumentRecord({
            document_id: DOC_A,
            title: "C2 Session 23 Prep",
            target_session: 23,
          }),
        ]}
        listStatus="ready"
        activeDocument={fixturePlanDocumentDescriptor({
          documentId: DOC_A,
          title: "C2 Session 23 Prep",
          targetSession: 23,
        })}
        switching={false}
        switchError={null}
        onSelect={onSelect}
        onRetryList={onRetryList}
        createControlProps={{
          campaignId: "longmont-c2",
          campaignLabel: "Longmont C2",
          suggestedSession: 23,
          suggestedTitle: "C2 Session 23 Prep",
          onSubmit,
        }}
        {...overrides}
      />
      <SurfaceContextHost />
    </SurfaceContextProvider>,
  );

  return { onSelect, onRetryList, onSubmit };
}

describe("PlanSurfaceContext", () => {
  it("publishes PREP with selector, session badge, and create action in the context host", () => {
    renderPlanContext({
      saveStatusLabel: "Unsaved local changes",
    });

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).getByText("PREP")).toBeInTheDocument();
    expect(within(host).getByTestId("plan-document-select")).toHaveValue(DOC_A);
    expect(within(host).getByTestId("plan-canvas-title")).toHaveTextContent("C2 Session 23 Prep");
    expect(within(host).getByText("S23")).toBeInTheDocument();
    expect(within(host).getByTestId("plan-canvas-save-status")).toHaveTextContent(
      "Unsaved local changes",
    );
    expect(within(host).getByTestId("plan-document-create-open")).toHaveTextContent("+ New prep");
  });

  it("shows empty prep state and create action when no active document", () => {
    renderPlanContext({
      activeDocument: null,
      documents: [],
      listStatus: "ready",
    });

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).getByText("No prep loaded")).toBeInTheDocument();
    expect(within(host).queryByTestId("plan-document-select")).not.toBeInTheDocument();
    expect(within(host).getByTestId("plan-document-create-open")).toBeInTheDocument();
  });

  it("surfaces switching and switch errors in the PREP module", () => {
    renderPlanContext({
      switching: true,
      switchError: "Could not open the selected prep document.",
    });

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).getByText("Switching…")).toBeInTheDocument();
    expect(within(host).getByText(/Could not open the selected prep document/i)).toBeInTheDocument();
  });

  it("opens the new prep popover from the context bar", async () => {
    const user = userEvent.setup();
    renderPlanContext();

    const host = screen.getByTestId("surface-context-host");
    await user.click(within(host).getByTestId("plan-document-create-open"));

    expect(screen.getByTestId("surface-context-popover")).toBeInTheDocument();
    expect(screen.getByText("New prep")).toBeInTheDocument();
    expect(screen.getByTestId("plan-document-create-form")).toBeInTheDocument();
  });

  it("selects by exact documentId", async () => {
    const user = userEvent.setup();
    const DOC_B = "22222222-2222-4222-8222-222222222222";
    const { onSelect } = renderPlanContext({
      documents: [
        fixtureWorkspaceDocumentRecord({ document_id: DOC_A, title: "Prep A", target_session: 23 }),
        fixtureWorkspaceDocumentRecord({ document_id: DOC_B, title: "Prep B", target_session: 26 }),
      ],
    });

    const host = screen.getByTestId("surface-context-host");
    await user.selectOptions(within(host).getByTestId("plan-document-select"), DOC_B);
    expect(onSelect).toHaveBeenCalledWith(DOC_B);
  });
});
