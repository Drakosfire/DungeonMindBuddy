import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  SurfaceContextHost,
  SurfaceContextProvider,
} from "../surfaceInteraction/contextHost";
import { fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import { BuildSurfaceContext } from "./BuildSurfaceContext";

const DOC_A = "11111111-1111-4111-8111-111111111111";

const sessionMock = vi.hoisted(() => ({
  current: null as null | {
    record: ReturnType<typeof fixtureWorkspaceDocumentRecord>;
    statusLabel: string;
    activeCommand: { id: string; documentId: string; startedAt: number } | null;
    updateDocumentMetadata: ReturnType<typeof vi.fn>;
  },
}));

vi.mock("../markdownCanvas/MarkdownCanvasSession", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../markdownCanvas/MarkdownCanvasSession")>();
  return {
    ...actual,
    useOptionalMarkdownCanvasSession: () => sessionMock.current,
  };
});

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
        {...overrides}
      />
      <SurfaceContextHost />
    </SurfaceContextProvider>,
  );

  return { onSelect, onCreate, onRetryList };
}

describe("BuildSurfaceContext", () => {
  beforeEach(() => {
    sessionMock.current = {
      record: fixtureWorkspaceDocumentRecord({
        document_id: DOC_A,
        title: "Faction Notes",
        campaign_id: "longmont-c1",
        kind: "worldbuilding_source",
        document_class: "faction",
      }),
      statusLabel: "Committed",
      activeCommand: null,
      updateDocumentMetadata: vi.fn(),
    };
  });

  it("publishes DOCUMENT with selector, badges, status, and Rename", () => {
    renderBuildContext();

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).getByText("DOCUMENT")).toBeInTheDocument();
    expect(within(host).getByTestId("build-document-select")).toHaveValue(DOC_A);
    expect(within(host).getByText("C1")).toBeInTheDocument();
    expect(within(host).getByText("faction")).toBeInTheDocument();
    expect(within(host).getByTestId("build-document-status")).toHaveTextContent("Committed");
    expect(within(host).getByTestId("build-document-rename-open")).toHaveTextContent("Rename");
    expect(within(host).getByTestId("build-document-create-open")).toHaveTextContent("+ New source");
  });

  it("shows empty state when no active record", () => {
    sessionMock.current = null;
    renderBuildContext({
      activeRecord: null,
      activeDocumentId: null,
      documents: [],
    });

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).getByText("No source loaded")).toBeInTheDocument();
    expect(within(host).getByRole("option", { name: "Choose source" })).toBeInTheDocument();
    expect(within(host).queryByTestId("build-document-rename-open")).not.toBeInTheDocument();
  });

  it("opens the new source popover", async () => {
    const user = userEvent.setup();
    renderBuildContext();

    const host = screen.getByTestId("surface-context-host");
    await user.click(within(host).getByTestId("build-document-create-open"));
    expect(screen.getByTestId("build-document-create-form")).toBeInTheDocument();
  });

  it("prefers live Canvas title over controller preflight title", () => {
    sessionMock.current = {
      record: fixtureWorkspaceDocumentRecord({
        document_id: DOC_A,
        title: "Renamed On Canvas",
        campaign_id: "longmont-c1",
        kind: "worldbuilding_source",
        document_class: "faction",
      }),
      statusLabel: "Unsaved changes",
      activeCommand: null,
      updateDocumentMetadata: vi.fn(),
    };
    renderBuildContext();
    expect(screen.getByTestId("build-canvas-title")).toHaveTextContent("Renamed On Canvas");
    expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved changes");
  });
});
