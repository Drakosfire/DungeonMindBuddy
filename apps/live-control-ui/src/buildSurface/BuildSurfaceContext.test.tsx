import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import {
  SurfaceContextHost,
  SurfaceContextProvider,
} from "../surfaceInteraction/contextHost";
import { fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import type { MarkdownCanvasSessionValue } from "../markdownCanvas/MarkdownCanvasSession";
import { BuildSurfaceContext } from "./BuildSurfaceContext";

const recoveryDialogPrototype = Object.getPrototypeOf(document.createElement("dialog"));
const originalRecoveryShowModal = Object.getOwnPropertyDescriptor(recoveryDialogPrototype, "showModal");
beforeAll(() => Object.defineProperty(recoveryDialogPrototype, "showModal", { configurable: true, value(this: HTMLDialogElement) { this.setAttribute("open", ""); } }));
afterAll(() => {
  if (originalRecoveryShowModal) Object.defineProperty(recoveryDialogPrototype, "showModal", originalRecoveryShowModal);
  else Reflect.deleteProperty(recoveryDialogPrototype, "showModal");
});

const selectedWorldMock = vi.hoisted(() => ({ managed: false }));
vi.mock("../selectedWorld/SelectedWorldContext", async original => ({
  ...await original<typeof import("../selectedWorld/SelectedWorldContext")>(),
  useSelectedWorld: () => selectedWorldMock.managed ? {kind:"managed", worldId:"elderwyld", name:"Elderwyld", documentId:null} : {kind:"legacy"},
}));

const DOC_A = "11111111-1111-4111-8111-111111111111";

const sessionMock = vi.hoisted(() => ({
  current: null as MarkdownCanvasSessionValue | null,
}));

vi.mock("../markdownCanvas/MarkdownCanvasSession", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../markdownCanvas/MarkdownCanvasSession")>();
  return {
    ...actual,
    useOptionalMarkdownCanvasSession: () => sessionMock.current,
  };
});

const COMMITTED_AT = "2026-10-18T19:30:00.000Z";

function makeSession(overrides: Partial<MarkdownCanvasSessionValue> = {}): MarkdownCanvasSessionValue {
  const record = fixtureWorkspaceDocumentRecord({
    document_id: DOC_A,
    title: "Faction Notes",
    campaign_id: "longmont-c1",
    kind: "worldbuilding_source",
    document_class: "faction",
    content_status: "committed",
    revision: 1,
    updated_at: COMMITTED_AT,
  }) as MarkdownCanvasSessionValue["record"];
  const snapshot = {
    record,
    loaded_revision: 1,
    markdown: "# Faction Notes",
    content_sha256: "sha",
  } as MarkdownCanvasSessionValue["snapshot"];
  return {
    documentId: DOC_A,
    documentKey: `${DOC_A}:1`,
    phase: "ready_clean",
    record,
    snapshot,
    statusLabel: "Committed",
    dirty: false,
    error: null,
    saveDisabled: false,
    saveDisabledReason: null,
    saveMarkdown: vi.fn(),
    activeCommand: null,
    updateDocumentMetadata: vi.fn(),
    lookupAdmission: vi.fn(() => ({
      ok: true,
      envelope: {
        documentId: DOC_A,
        revision: 1,
        contentSha256: "sha",
        contentStatus: "committed" as const,
        documentKind: "worldbuilding_source" as const,
        surfaceId: "build" as const,
      },
    })),
    ...overrides,
  } as unknown as MarkdownCanvasSessionValue;
}

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
        destinationOptions={[
          {
            kind: "campaign",
            campaignId: "longmont-c1",
            worldId: "eldyrwild",
            label: "longmont-c1",
            value: "campaign:longmont-c1",
          },
          {
            kind: "campaign",
            campaignId: "longmont-c2",
            worldId: "eldyrwild",
            label: "longmont-c2",
            value: "campaign:longmont-c2",
          },
        ]}
        suggestedDestinationValue="campaign:longmont-c1"
        {...overrides}
      />
      <SurfaceContextHost />
    </SurfaceContextProvider>,
  );

  return { onSelect, onCreate, onRetryList };
}

describe("BuildSurfaceContext", () => {
  beforeEach(() => {
    selectedWorldMock.managed = false;
    sessionMock.current = makeSession();
  });

  it("explains blocked Save and exposes protected-draft review in the real navbar", async () => {
    const prepare = vi.fn(() => ({ documentId: DOC_A, fence: "fence", editorText: "Local draft", preservedMarkdown: "# Preserved source" }));
    Object.assign(sessionMock.current!, { dirty: true, phase: "ready_dirty", documentId: DOC_A,
      documentKey: `${DOC_A}:1`, exportedMarkdownAuthoritative: true, draftRecoveryAvailable: false,
      saveDisabled: true, saveDisabledReason: "Save is paused to protect a recovered draft.",
      prepareDraftRecovery: prepare, confirmDraftRecovery: vi.fn(), restoreDraftRecovery: vi.fn() });
    renderBuildContext();
    const save = screen.getByTestId("build-navbar-save");
    expect(save).toBeDisabled();
    expect(save).toHaveAccessibleDescription("Save is paused to protect a recovered draft.");
    await userEvent.click(screen.getByRole("button", { name: "Review protected draft", exact: true }));
    expect(prepare).toHaveBeenCalledOnce();
    expect(screen.getByRole("dialog", { name: "Review protected draft" })).toHaveTextContent("Local draft");
    expect(sessionMock.current!.saveMarkdown).not.toHaveBeenCalled();
  });

  it("places the explicit extraction portal slot inside the source navbar", () => {
    const attach = vi.fn();
    renderBuildContext({ extractionTargetRef: attach });
    const slot = within(screen.getByTestId("surface-context-host")).getByTestId("build-extraction-slot");
    expect(attach).toHaveBeenCalledWith(slot);
    expect(slot.closest(".build-surface-context__row")).not.toBeNull();
  });

  it("publishes DOCUMENT with selector, badges, status, and Rename", () => {
    renderBuildContext();

    const host = screen.getByTestId("surface-context-host");
    expect(within(host).queryByText("DOCUMENT")).not.toBeInTheDocument();
    expect(within(host).getByTestId("build-navbar-save")).toBeEnabled();
    expect(within(host).getByText("Source actions")).toBeInTheDocument();
    expect(within(host).getByTestId("build-document-select")).toHaveValue(DOC_A);
    expect(within(host).getByText("C1")).toBeInTheDocument();
    expect(within(host).getByText("faction")).toBeInTheDocument();
    const saveStatus = within(host).getByTestId("build-document-status");
    expect(saveStatus.querySelector('[data-save-state="saved"]')).not.toBeNull();
    expect(saveStatus.querySelector("time")).toHaveAttribute("dateTime", COMMITTED_AT);
    expect(within(host).getByTestId("build-document-rename-open")).toHaveTextContent("Rename");
    expect(within(host).getByTestId("build-document-create-open")).toHaveTextContent("+ New page");
  });

  it("saves through the existing document command from the navbar", async () => {
    const user = userEvent.setup();
    renderBuildContext();
    await user.click(screen.getByTestId("build-navbar-save"));
    expect(sessionMock.current!.saveMarkdown).toHaveBeenCalledTimes(1);
    expect(sessionMock.current!.updateDocumentMetadata).not.toHaveBeenCalled();
  });

  it("owns the durable save timestamp in the surface navbar", () => {
    renderBuildContext();

    const host = screen.getByTestId("surface-context-host");
    const status = within(host).getByTestId("build-document-status");
    expect(status.closest(".build-surface-context__row")).not.toBeNull();
    expect(status.querySelector('[data-save-state="saved"]')).not.toBeNull();
    expect(status.querySelector("time")).toHaveAttribute("dateTime", COMMITTED_AT);
    expect(status).not.toHaveTextContent("Committed");
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
    sessionMock.current = makeSession({
      record: fixtureWorkspaceDocumentRecord({
        document_id: DOC_A,
        title: "Renamed On Canvas",
        campaign_id: "longmont-c1",
        kind: "worldbuilding_source",
        document_class: "faction",
      }) as MarkdownCanvasSessionValue["record"],
      statusLabel: "Unsaved changes",
      documentKey: `${DOC_A}:2`,
      phase: "ready_dirty",
      dirty: true,
    });
    renderBuildContext({
      documents: [
        fixtureWorkspaceDocumentRecord({
          document_id: DOC_A,
          title: "Stale List Title",
          campaign_id: "longmont-c1",
          kind: "worldbuilding_source",
        }),
      ],
    });
    expect(screen.getByTestId("build-canvas-title")).toHaveTextContent("Renamed On Canvas");
    expect(screen.getByTestId("build-document-status")).toHaveTextContent("Unsaved changes");
    expect(
      within(screen.getByTestId("build-document-select")).getByRole("option", {
        name: "Renamed On Canvas",
      }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("build-document-select")).queryByRole("option", {
        name: "Stale List Title",
      }),
    ).not.toBeInTheDocument();
  });
});

it("admits Build trash only for a clean verified document in the selected World", () => {
  selectedWorldMock.managed = true;
  sessionMock.current = makeSession();
  renderBuildContext();
  expect(screen.getByRole("button",{name:"Delete",exact:true})).toBeEnabled();
  expect(screen.getByRole("button",{name:"Trash",exact:true})).toBeEnabled();
});
it("keeps Build deletion disabled while the source has unsaved edits", () => {
  selectedWorldMock.managed = true;
  sessionMock.current = makeSession({dirty:true, phase:"ready_dirty"});
  renderBuildContext();
  expect(screen.getByRole("button",{name:"Delete",exact:true})).toBeDisabled();
});
