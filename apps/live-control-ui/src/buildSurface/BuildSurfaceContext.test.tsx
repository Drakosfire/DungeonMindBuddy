import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  SurfaceContextHost,
  SurfaceContextProvider,
} from "../surfaceInteraction/contextHost";
import { fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import { BuildSurfaceContext } from "./BuildSurfaceContext";

const DOC_A = "11111111-1111-4111-8111-111111111111";

function renderBuildContext(
  overrides: Partial<Parameters<typeof BuildSurfaceContext>[0]> = {},
) {
  const onSelect = vi.fn();
  const onCreate = vi.fn();
  const onRetryList = vi.fn();

  render(
    <SurfaceContextProvider>
      <BuildSurfaceContext
        activeRecord={fixtureWorkspaceDocumentRecord({
          document_id: DOC_A,
          title: "Faction Notes",
          campaign_id: "longmont-c1",
          kind: "worldbuilding_source",
          document_class: "faction",
        })}
        activeDocumentId={DOC_A}
        documents={[
          fixtureWorkspaceDocumentRecord({
            document_id: DOC_A,
            title: "Faction Notes",
            campaign_id: "longmont-c1",
            kind: "worldbuilding_source",
          }),
        ]}
        listStatus="ready"
        loadStatus="ready"
        switching={false}
        switchError={null}
        creating={false}
        createError={null}
        activationError={null}
        selectDocument={onSelect}
        createDocument={onCreate}
        retryCreatedDocument={vi.fn()}
        refreshDocuments={onRetryList}
        creatableCampaignIds={["longmont-c1", "longmont-c2"]}
        suggestedCreateCampaignId="longmont-c1"
        authoringStatusLabel="Committed"
        setAuthoringStatusLabel={vi.fn()}
        {...overrides}
      />
      <SurfaceContextHost />
    </SurfaceContextProvider>,
  );

  return { onSelect, onCreate, onRetryList };
}

describe("BuildSurfaceContext", () => {
  it("publishes DOCUMENT with selector, badges, and status", () => {
    renderBuildContext();

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).getByText("DOCUMENT")).toBeInTheDocument();
    expect(within(host).getByTestId("build-document-select")).toHaveValue(DOC_A);
    expect(within(host).getByText("C1")).toBeInTheDocument();
    expect(within(host).getByText("faction")).toBeInTheDocument();
    expect(within(host).getByTestId("build-document-status")).toHaveTextContent("Committed");
    expect(within(host).getByTestId("build-document-create-open")).toHaveTextContent("+ New source");
  });

  it("shows empty state when no active record", () => {
    renderBuildContext({
      activeRecord: null,
      activeDocumentId: null,
      documents: [],
      authoringStatusLabel: null,
    });

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).getByText("No source loaded")).toBeInTheDocument();
    expect(within(host).getByRole("option", { name: "Choose source" })).toBeInTheDocument();
  });

  it("opens the new source popover", async () => {
    const user = userEvent.setup();
    renderBuildContext();

    const host = screen.getByTestId("surface-context-host");
    await user.click(within(host).getByTestId("build-document-create-open"));
    expect(screen.getByTestId("build-document-create-form")).toBeInTheDocument();
  });
});
