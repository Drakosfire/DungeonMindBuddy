import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import * as liveApi from "../api/liveApi";
import * as ingestRunCatalogApi from "../ingestSurface/ingestRunCatalogApi";
import { mockCatalog, mockLayout, mockPlanView, mockState } from "./fixtures";
import {
  appRouteFromPathname,
  getAppLocationSnapshot,
  isPrimaryAppHref,
  isPrimaryAppPathname,
  navigatePrimaryAppHref,
  normalizeAppPathname,
  shouldInterceptPrimaryNavigationClick,
  type NavigationClickLike,
} from "../chrome/appNavigation";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getSurface: vi.fn(),
    getEvents: vi.fn(),
    getJobs: vi.fn(),
    getPlanView: vi.fn(),
    getGraphIngestRuns: vi.fn(),
    getGoldReviewSessions: vi.fn(),
    getManualReviewBeds: vi.fn(),
    getCapabilities: vi.fn(),
    listWorkspaceDocuments: vi.fn(),
    getWorkspaceDocument: vi.fn(),
    getWorkspaceDocumentSnapshot: vi.fn(),
    getPlayActiveRun: vi.fn(),
    putPlayActiveRun: vi.fn(),
    getCommittedWorkspaceRevision: vi.fn(),
    createWorkspaceDocument: vi.fn(),
    postWorldGraphProjection: vi.fn(),
    listPlayRuns: vi.fn(),
    getPlayRun: vi.fn(),
    getPlayRunReferenceManifest: vi.fn(),
  };
});

vi.mock("../ingestSurface/ingestRunCatalogApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../ingestSurface/ingestRunCatalogApi")>();
  return {
    ...actual,
    getExtractionRunCatalog: vi.fn(),
  };
});

const PLAY_RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

function clickLike(
  overrides: Partial<NavigationClickLike> = {},
): NavigationClickLike {
  return {
    defaultPrevented: false,
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    preventDefault: vi.fn(),
    currentTarget: null,
    target: null,
    ...overrides,
  };
}

function anchorFor(href: string, extras?: { target?: string; download?: boolean }): HTMLAnchorElement {
  const anchor = document.createElement("a");
  anchor.setAttribute("href", href);
  if (extras?.target) anchor.target = extras.target;
  if (extras?.download) anchor.setAttribute("download", "file.html");
  document.body.appendChild(anchor);
  return anchor;
}

describe("appNavigation helpers", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    window.history.pushState({}, "", "/");
  });

  it("recognizes only the primary in-document pathnames", () => {
    expect(isPrimaryAppPathname("/")).toBe(true);
    expect(isPrimaryAppPathname("/plan")).toBe(true);
    expect(isPrimaryAppPathname("/play/")).toBe(true);
    expect(isPrimaryAppPathname("/ingest")).toBe(true);
    expect(isPrimaryAppPathname("/build")).toBe(true);
    expect(isPrimaryAppPathname("/combat")).toBe(false);
    expect(isPrimaryAppPathname("/surface")).toBe(false);
    expect(isPrimaryAppHref("/combat")).toBe(false);
    expect(isPrimaryAppHref("/plan")).toBe(true);
  });

  it("preserves existing non-primary route fallbacks", () => {
    expect(appRouteFromPathname("/surface")).toBe("surface");
    expect(appRouteFromPathname("/live-control")).toBe("surface");
    expect(appRouteFromPathname("/tiptap-callout-spike")).toBe("tiptap-callout-spike");
    expect(appRouteFromPathname("/unknown")).toBe("index");
    expect(normalizeAppPathname("/plan/")).toBe("/plan");
  });

  it("does not intercept modified, non-primary, download, or targeted clicks", () => {
    const plan = anchorFor("/plan");
    expect(shouldInterceptPrimaryNavigationClick(clickLike({ metaKey: true }), plan)).toBe(false);
    expect(shouldInterceptPrimaryNavigationClick(clickLike({ ctrlKey: true }), plan)).toBe(false);
    expect(shouldInterceptPrimaryNavigationClick(clickLike({ shiftKey: true }), plan)).toBe(false);
    expect(shouldInterceptPrimaryNavigationClick(clickLike({ altKey: true }), plan)).toBe(false);
    expect(shouldInterceptPrimaryNavigationClick(clickLike({ button: 1 }), plan)).toBe(false);
    expect(
      shouldInterceptPrimaryNavigationClick(clickLike({ defaultPrevented: true }), plan),
    ).toBe(false);
    expect(
      shouldInterceptPrimaryNavigationClick(clickLike(), anchorFor("/combat")),
    ).toBe(false);
    expect(
      shouldInterceptPrimaryNavigationClick(clickLike(), anchorFor("/plan", { target: "_blank" })),
    ).toBe(false);
    expect(
      shouldInterceptPrimaryNavigationClick(clickLike(), anchorFor("/plan", { download: true })),
    ).toBe(false);
    expect(shouldInterceptPrimaryNavigationClick(clickLike(), plan)).toBe(true);
  });

  it("pushes a new primary location and no-ops the already-active primary pathname", () => {
    const pushSpy = vi.spyOn(window.history, "pushState");
    window.history.pushState({}, "", "/ingest?session=session-25");
    pushSpy.mockClear();

    navigatePrimaryAppHref("/ingest");
    expect(pushSpy).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe("/ingest");
    expect(window.location.search).toBe("?session=session-25");

    navigatePrimaryAppHref("/plan");
    expect(pushSpy).toHaveBeenCalledTimes(1);
    expect(window.location.pathname).toBe("/plan");
    expect(getAppLocationSnapshot()).toBe("/plan");
    pushSpy.mockRestore();
  });

  it("leaves combat hrefs outside the intercept contract", () => {
    expect(shouldInterceptPrimaryNavigationClick(clickLike(), anchorFor("/combat"))).toBe(false);
    expect(isPrimaryAppHref("/combat")).toBe(false);
  });
});

function commandBoardNav() {
  return screen.getByRole("navigation", { name: "Command board navigation" });
}

describe("App same-document primary navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, "", "/");
    vi.mocked(liveApi.getSurface).mockResolvedValue({
      catalog: mockCatalog,
      layout: mockLayout,
      state: mockState,
    });
    vi.mocked(liveApi.getEvents).mockResolvedValue({ events: [] });
    vi.mocked(liveApi.getJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(liveApi.getPlanView).mockResolvedValue(mockPlanView);
    vi.mocked(liveApi.getGraphIngestRuns).mockResolvedValue({
      schema_version: "dmb_graph_ingest_run_registry_v1",
      version: "test",
      runs: [],
    });
    vi.mocked(ingestRunCatalogApi.getExtractionRunCatalog).mockResolvedValue({
      schema_version: "dmb_extraction_run_catalog_v1",
      runs: [],
    });
    vi.mocked(liveApi.getGoldReviewSessions).mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "test",
      sessions: [],
    });
    vi.mocked(liveApi.getManualReviewBeds).mockResolvedValue({
      schema_version: "dmb_graph_manual_review_beds_v1",
      version: "test",
      beds: [],
    });
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [],
    });
    vi.mocked(liveApi.getPlayActiveRun).mockRejectedValue(
      new liveApi.LiveApiError("active selection unavailable", 503),
    );
    vi.mocked(liveApi.getPlayRun).mockRejectedValue(
      new liveApi.LiveApiError("not found", 404),
    );
    vi.mocked(liveApi.listPlayRuns).mockResolvedValue({
      schema_version: "dmb_play_runs_list_v1",
      records: [],
    });
  });

  it("boots each primary URL from the current location without a prior in-app click", async () => {
    window.history.pushState({}, "", "/plan");
    const plan = render(<App />);
    expect(await screen.findByTestId("plan-canvas-title")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/plan");
    plan.unmount();

    window.history.pushState({}, "", "/ingest");
    const ingest = render(<App />);
    expect(await screen.findByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    ingest.unmount();

    window.history.pushState({}, "", "/build");
    const build = render(<App />);
    expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();
    build.unmount();

    window.history.pushState({}, "", "/play");
    const play = render(<App />);
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    play.unmount();

    window.history.pushState({}, "", "/");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Command Board" })).toBeInTheDocument();
  });

  it("navigates Index launcher and AppChrome primary links without replacing the document", async () => {
    const pushSpy = vi.spyOn(window.history, "pushState");
    render(<App />);

    const launcher = screen.getByRole("link", { name: /Prep surface/i });
    expect(launcher).toHaveAttribute("href", "/plan");
    fireEvent.click(launcher);
    expect(await screen.findByTestId("plan-canvas-title")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/plan");

    const chrome = screen.getByTestId("agent-interaction-chrome");
    fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Ingest" }));
    expect(await screen.findByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/ingest");
    expect(screen.getByTestId("agent-interaction-chrome")).toBe(chrome);

    fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Build" }));
    expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/build");

    fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Play" }));
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/play");

    fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Index" }));
    expect(await screen.findByRole("heading", { name: "Command Board" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
    expect(screen.getByRole("link", { name: /North Reach Gate tracker/i })).toHaveAttribute(
      "href",
      "/combat",
    );
    expect(pushSpy.mock.calls.some((call) => String(call[2]).includes("/combat"))).toBe(false);
    pushSpy.mockRestore();
  });

  it("replays primary routes on browser back/forward", async () => {
    render(<App />);

    fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Ingest" }));
    expect(await screen.findByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Plan" }));
    expect(await screen.findByTestId("plan-canvas-title")).toBeInTheDocument();
    fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Build" }));
    expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();

    window.history.back();
    await waitFor(() => {
      expect(window.location.pathname).toBe("/plan");
      expect(screen.getByTestId("plan-canvas-title")).toBeInTheDocument();
    });
    window.history.back();
    await waitFor(() => {
      expect(window.location.pathname).toBe("/ingest");
      expect(screen.getByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    });
    window.history.forward();
    await waitFor(() => {
      expect(window.location.pathname).toBe("/plan");
    });
  });

  it("keeps /play?run= across Ingest navigation and back", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", `/play?run=${PLAY_RUN_ID}`);
    render(<App />);

    expect(await screen.findByTestId("play-status-miss")).toBeInTheDocument();
    expect(window.location.search).toBe(`?run=${PLAY_RUN_ID}`);

    const nav = screen.getByRole("navigation", { name: "Command board navigation" });
    await user.click(within(nav).getByRole("link", { name: "Ingest" }));
    expect(await screen.findByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/ingest");
    expect(window.location.search).toBe("");

    window.history.back();
    await waitFor(() => {
      expect(window.location.pathname).toBe("/play");
      expect(window.location.search).toBe(`?run=${PLAY_RUN_ID}`);
    });
  });

  it("does not duplicate history when the active primary link is clicked again", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/ingest");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();

    const pushSpy = vi.spyOn(window.history, "pushState");
    const nav = screen.getByRole("navigation", { name: "Command board navigation" });
    await user.click(within(nav).getByRole("link", { name: "Ingest" }));
    expect(pushSpy).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe("/ingest");
    pushSpy.mockRestore();
  });

  it("does not intercept Combat Tracker or modifier-click primary links", async () => {
    const user = userEvent.setup();
    render(<App />);
    const nav = screen.getByRole("navigation", { name: "Command board navigation" });
    const combat = within(nav).getByRole("link", { name: "Combat Tracker" });
    expect(combat).toHaveAttribute("href", "/combat");

    const pushSpy = vi.spyOn(window.history, "pushState");
    await user.pointer({ keys: "[MouseRight]", target: combat });
    expect(window.location.pathname).toBe("/");

    const ingest = within(nav).getByRole("link", { name: "Ingest" });
    ingest.dispatchEvent(
      new MouseEvent("click", { bubbles: true, cancelable: true, button: 0, ctrlKey: true }),
    );
    expect(window.location.pathname).toBe("/");
    expect(pushSpy.mock.calls.some((call) => String(call[2]) === "/ingest")).toBe(false);
    pushSpy.mockRestore();
  });
});
