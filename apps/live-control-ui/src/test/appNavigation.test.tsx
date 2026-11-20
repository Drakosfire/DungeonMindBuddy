import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import * as liveApi from "../api/liveApi";
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
    expect(isPrimaryAppPathname("/combat")).toBe(true);
    expect(isPrimaryAppPathname("/surface")).toBe(false);
    expect(isPrimaryAppHref("/combat")).toBe(true);
    expect(isPrimaryAppHref("/plan")).toBe(true);
  });

  it("preserves existing non-primary route fallbacks", () => {
    expect(appRouteFromPathname("/graph")).toBe("graph");
    expect(appRouteFromPathname("/surface")).toBe("surface");
    expect(appRouteFromPathname("/live-control")).toBe("index");
    expect(appRouteFromPathname("/tiptap-callout-spike")).toBe("index");
    expect(appRouteFromPathname("/unknown")).toBe("index");
    expect(appRouteFromPathname("/combat/")).toBe("combat");
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
    ).toBe(true);
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

  it("treats native Combat as a primary route", () => {
    expect(shouldInterceptPrimaryNavigationClick(clickLike(), anchorFor("/combat"))).toBe(true);
    expect(isPrimaryAppHref("/combat")).toBe(true);
  });
});

function commandBoardNav() {
  const nav = screen.getByRole("navigation", { name: "Command board navigation" });
  const toggle = within(nav).queryByRole("button", { name: "Open navigation" });
  if (toggle) fireEvent.click(toggle);
  return nav;
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
    const worlds = vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [{
        schema_version: "dmb_world_container_record_v1", world_id: "eldyrwild",
        name: "Eldyrwild", source_root_relpath: "", created_at: "2026-01-01T00:00:00Z",
      }],
    });
    try {
      window.history.pushState({}, "", "/plan");
      const plan = render(<App />);
      expect(await screen.findByRole("heading", { name: "Plan your next session" })).toBeInTheDocument();
      expect(await within(screen.getByRole("region", { name: "Choose your World" })).findByRole("link", { name: /Eldyrwild/ })).toHaveAttribute("href", "/plan?world=eldyrwild");
      expect(screen.queryByTestId("plan-canvas-title")).not.toBeInTheDocument();
      expect(window.location.pathname).toBe("/plan");
      plan.unmount();

      window.history.pushState({}, "", "/ingest");
      const ingest = render(<App />);
      expect(await screen.findByRole("heading", { name: "Give your World a little more to remember." })).toBeInTheDocument();
      expect(window.location.pathname).toBe("/ingest");
      ingest.unmount();

      window.history.pushState({}, "", "/build");
      const build = render(<App />);
      expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();
      expect(window.location.pathname).toBe("/build");
      build.unmount();

      window.history.pushState({}, "", "/play");
      const play = render(<App />);
      expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
      expect(await within(screen.getByRole("region", { name: "Choose your World" })).findByRole("link", { name: /Eldyrwild/ })).toHaveAttribute("href", "/play?world=eldyrwild&choose=1");
      expect(window.location.pathname).toBe("/play");
      play.unmount();

      window.history.pushState({}, "", "/");
      render(<App />);
      expect(await screen.findByRole("heading", { name: /Your world,\s*ready for the table\./ })).toBeInTheDocument();
      expect(window.location.pathname).toBe("/");
      expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    } finally {
      worlds.mockRestore();
    }
  });

  it("navigates local Surface and AppChrome primary links without replacing the document", async () => {
    const surface = vi.spyOn(liveApi, "getSurfaceSessionViews").mockResolvedValue({
      catalog: mockCatalog, layout: mockLayout, state: mockState,
      events: [], jobs: [], plan_view: mockPlanView,
    });
    const worlds = vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1", records: [],
    });
    const pushSpy = vi.spyOn(window.history, "pushState");
    const browserDocument = document;
    try {
      window.history.pushState({}, "", "/surface");
      render(<App />);
      expect(await screen.findByRole("button", { name: "Tools" })).toBeInTheDocument();
      expect(await screen.findByRole("textbox", { name: "Live query" })).toBeEnabled();
      expect(surface).toHaveBeenCalledTimes(1);

      const launcher = within(commandBoardNav()).getByRole("link", { name: "Plan" });
      expect(launcher).toHaveAttribute("href", "/plan");
      fireEvent.click(launcher);
      expect(await screen.findByRole("heading", { name: "Plan your next session" })).toBeInTheDocument();
      expect(window.location.pathname).toBe("/plan");

      // World entry and first-use Ingest have no registered Ask plugin (#701).
      expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
      fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Ingest" }));
      expect(await screen.findByRole("heading", { name: "Give your World a little more to remember." })).toBeInTheDocument();
      expect(window.location.pathname).toBe("/ingest");
      expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();

      fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Build" }));
      expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();
      expect(window.location.pathname).toBe("/build");

      fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Play" }));
      expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
      expect(window.location.pathname).toBe("/play");
      expect(within(commandBoardNav()).getByRole("link", { name: "Combat Tracker" })).toHaveAttribute("href", "/combat");

      fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Home" }));
      expect(await screen.findByRole("heading", { name: /Your world,\s*ready for the table\./ })).toBeInTheDocument();
      expect(window.location.pathname).toBe("/");
      expect(document).toBe(browserDocument);
      expect(pushSpy.mock.calls.some((call) => String(call[2]).includes("/combat"))).toBe(false);
    } finally {
      pushSpy.mockRestore();
      worlds.mockRestore();
      surface.mockRestore();
    }
  });

  it("replays primary routes on browser back/forward", async () => {
    const worlds = vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1", records: [],
    });
    try {
      window.history.pushState({}, "", "/build");
      render(<App />);
      expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();

      fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Ingest" }));
      expect(await screen.findByRole("heading", { name: "Give your World a little more to remember." })).toBeInTheDocument();
      fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Plan" }));
      expect(await screen.findByRole("heading", { name: "Plan your next session" })).toBeInTheDocument();
      fireEvent.click(within(commandBoardNav()).getByRole("link", { name: "Build" }));
      expect(await screen.findByTestId("build-surface-empty")).toBeInTheDocument();

      window.history.back();
      await waitFor(() => {
        expect(window.location.pathname).toBe("/plan");
        expect(screen.getByRole("heading", { name: "Plan your next session" })).toBeInTheDocument();
      });
      window.history.back();
      await waitFor(() => {
        expect(window.location.pathname).toBe("/ingest");
        expect(screen.getByRole("heading", { name: "Give your World a little more to remember." })).toBeInTheDocument();
      });
      window.history.forward();
      await waitFor(() => {
        expect(window.location.pathname).toBe("/plan");
        expect(screen.getByRole("heading", { name: "Plan your next session" })).toBeInTheDocument();
      });
    } finally {
      worlds.mockRestore();
    }
  });

  it("keeps /play?run= across Ingest navigation and back", async () => {
    const user = userEvent.setup();
    const worldId = "eldyrwild";
    const playQuery = `?world=${worldId}&run=${PLAY_RUN_ID}`;
    const worlds = vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [{
        schema_version: "dmb_world_container_record_v1", world_id: worldId,
        name: "Eldyrwild", source_root_relpath: "", created_at: "2026-01-01T00:00:00Z",
      }],
    });
    const nativeRun = vi.spyOn(liveApi, "getWorldPlayRun").mockRejectedValue(
      new liveApi.LiveApiError("not found", 404),
    );
    const planRead = vi.mocked(liveApi.getPlanView).mockResolvedValue({
      ...mockPlanView, world_id: worldId, campaign_id: worldId, session: 0,
    });
    try {
      window.history.pushState({}, "", `/play${playQuery}`);
      render(<App />);

      expect(await screen.findByTestId("play-status-miss")).toBeInTheDocument();
      expect(window.location.search).toBe(playQuery);
      expect(nativeRun).toHaveBeenCalledWith(PLAY_RUN_ID, worldId);
      expect(liveApi.getPlayRun).not.toHaveBeenCalled();

      const ingest = within(commandBoardNav()).getByRole("link", { name: "Ingest" });
      expect(ingest).toHaveAttribute("href", `/ingest?world=${worldId}`);
      await user.click(ingest);
      expect(await screen.findByRole("heading", { name: "Bring a source into the story." })).toBeInTheDocument();
      expect(planRead).toHaveBeenCalledWith(worldId, expect.any(AbortSignal));
      expect(window.location.pathname).toBe("/ingest");
      expect(window.location.search).toBe(`?world=${worldId}`);

      window.history.back();
      await waitFor(() => {
        expect(window.location.pathname).toBe("/play");
        expect(window.location.search).toBe(playQuery);
        expect(screen.getByTestId("play-status-miss")).toBeInTheDocument();
      });
      expect(liveApi.getPlayRun).not.toHaveBeenCalled();
    } finally {
      planRead.mockResolvedValue(mockPlanView);
      nativeRun.mockRestore();
      worlds.mockRestore();
    }
  });

  it("does not duplicate history when the active primary link is clicked again", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/ingest");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Give your World a little more to remember." })).toBeInTheDocument();

    const pushSpy = vi.spyOn(window.history, "pushState");
    const nav = commandBoardNav();
    await user.click(within(nav).getByRole("link", { name: "Ingest" }));
    expect(pushSpy).not.toHaveBeenCalled();
    expect(window.location.pathname).toBe("/ingest");
    pushSpy.mockRestore();
  });

  it("does not intercept right-click Combat or modifier-click primary links", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/ingest");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Give your World a little more to remember." })).toBeInTheDocument();
    const nav = commandBoardNav();
    const combat = within(nav).getByRole("link", { name: "Combat Tracker" });
    expect(combat).toHaveAttribute("href", "/combat");

    const pushSpy = vi.spyOn(window.history, "pushState");
    await user.pointer({ keys: "[MouseRight]", target: combat });
    expect(window.location.pathname).toBe("/ingest");

    const plan = within(nav).getByRole("link", { name: "Plan" });
    plan.dispatchEvent(
      new MouseEvent("click", { bubbles: true, cancelable: true, button: 0, ctrlKey: true }),
    );
    expect(window.location.pathname).toBe("/ingest");
    expect(pushSpy.mock.calls.some((call) => String(call[2]) === "/plan")).toBe(false);
    pushSpy.mockRestore();
  });
});

it('navigates exact statblock targets within the same World',()=>{
 window.history.replaceState({},'', '/statblock?world=elderwyld&draft=a&revision=one');
 expect(appRouteFromPathname('/statblock/')).toBe('statblock');expect(isPrimaryAppHref('/statblock?world=elderwyld&draft=a&revision=two')).toBe(true);
 navigatePrimaryAppHref('/statblock?world=elderwyld&draft=a&revision=two');
 expect(window.location.search).toBe('?world=elderwyld&draft=a&revision=two');
});
