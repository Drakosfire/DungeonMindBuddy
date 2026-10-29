import {useSyncExternalStore} from 'react';
import {TourNavigationRegistry,TourNavigationProvider,TourNavigationActions,useTourNavigationOwner,type NavigationScope} from '../guidedTour/Navigation';
import {getAppLocationSnapshot,subscribeAppLocation} from '../chrome/appNavigation';
import {useCombatProjection} from '../combat/combatProjection';
import {runPins} from '../guidedTour/ownerPins';
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { ToolHost } from "../surfaceInteraction/toolHost/ToolHost";
import { LegacyProjectionHostAdapter } from "../planSurface/projection/LegacyProjectionHostAdapter";
import { createHash, webcrypto } from "node:crypto";
import { getWorldPlayRunContent, putWorldPlayRunContentCommand } from "../api/playRunContentApi";
import type { PlayRunContent } from "./playRunContentTypes";
import { usePublishWorldPlayConversation } from "../agentInteraction/WorldAgentConversation";
import { act, fireEvent, render as rtlRender, screen, waitFor, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getPlayActiveRun,
  getWorldPlayActiveRun,
  getPlayRun,
  getCommittedWorkspaceRevision,
  getWorldOwnedPlanCommittedRevision,
  getWorldOwnedRunbookCommittedRevision,
  getWorldPlayRun,
  getWorldPlayRunReferenceManifest,
  listPlayRuns,
  listWorldPlayRuns,
  listWorldOwnedPlans,
  listWorldOwnedRunbooks,
  putPlayActiveRun,
  putWorldPlayActiveRun,
  putWorldPlayRunProgress,
  putWorldPlayRunRebase,
} from "../api/liveApi";
import { LiveApiError } from "../api/liveApi";
import type { WorldOwnedCommittedRevisionV2, WorldOwnedRunbookCommittedRevisionV2, WorldPlayRunRecordV2 } from "../api/types";
import { PlaySurfacePage } from "./PlaySurfacePage";
import { SurfaceContextHost, SurfaceContextProvider } from "../surfaceInteraction/contextHost";

// Read retained source/context through the same More action used by the UI.
function playDetails(testId: string) {
  if (!screen.queryByTestId(testId)) {
    const more = screen.getByRole("button", { name: "More Play controls" });
    if (more.getAttribute("aria-expanded") === "false") fireEvent.click(more);
  }
  return screen.getByTestId(testId);
}

function render(ui: ReactElement, options?: Omit<RenderOptions, "wrapper">) {
  return rtlRender(ui, { ...options, wrapper: ({ children }) => <AgentInteractionProvider><SurfaceContextProvider><SurfaceContextHost />{children}<ToolHost /><LegacyProjectionHostAdapter /></SurfaceContextProvider></AgentInteractionProvider> });
}

vi.mock('../combat/combatProjection',async original=>{const actual=await original<typeof import('../combat/combatProjection')>();return {...actual,useCombatProjection:vi.fn(actual.useCombatProjection)};});
vi.mock("../api/playRunContentApi", () => ({ getWorldPlayRunContent: vi.fn(), getWorldPlayRunContentCommand: vi.fn(), putWorldPlayRunContentCommand: vi.fn() }));
vi.mock("../agentInteraction/WorldAgentConversation", async original => ({
  ...await original<typeof import("../agentInteraction/WorldAgentConversation")>(), usePublishWorldPlayConversation: vi.fn(),
}));
const selectedWorldHarness = vi.hoisted(() => ({ worldId: "world-b", legacy: false }));

vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getRulesCatalog: vi.fn().mockResolvedValue({ schema: "dmb_rules_catalog_v1", sources: [] }),
  getPlayActiveRun: vi.fn(),
  getWorldPlayActiveRun: vi.fn(),
  getPlayRun: vi.fn(),
  getPlayRunReferenceManifest: vi.fn(),
  getCommittedWorkspaceRevision: vi.fn(),
  getWorldOwnedPlanCommittedRevision: vi.fn(),
  listPlayRuns: vi.fn(),
  getWorldOwnedRunbookCommittedRevision: vi.fn(),
  getWorldPlayRun: vi.fn(),
  getWorldPlayRunReferenceManifest: vi.fn(),
  listWorldPlayRuns: vi.fn(),
  listWorldOwnedPlans: vi.fn(),
  listWorldOwnedRunbooks: vi.fn(),
  putWorldPlayRunRebase: vi.fn(),
  putPlayActiveRun: vi.fn(),
  putWorldPlayActiveRun: vi.fn(),
  putWorldPlayRunProgress: vi.fn(),
}));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({
  useSelectedWorld: () => selectedWorldHarness.legacy ? {kind:"legacy"} : ({
    kind: "managed",
    worldId: selectedWorldHarness.worldId,
    name: `World ${selectedWorldHarness.worldId}`,
    documentId: null,
  }),
}));
vi.mock("../chrome/AppChrome", () => ({ AppChrome: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("../agentInteraction/usePublishAgentSurfaceContext", () => ({ usePublishAgentSurfaceContext: () => undefined }));
vi.mock("../graphLens", () => ({ useOptionalWorldGraphLens: () => null }));
vi.mock("./review/SessionReviewPanel",()=>({SessionReviewPanel:()=>null}));
vi.mock("./review/sessionReviewApi",()=>({readSessionReview:vi.fn().mockResolvedValue({review:null})}));
vi.mock("../shared/SurfaceWorldPicker", () => ({SurfaceWorldPicker: () => <div>Choose your World</div>}));
vi.mock("./StartRunPanel", () => ({ StartRunPanel: () => <div>Start Run</div> }));

const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const secondRunId = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const artifactId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const workRevisionId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const newerWorkRevisionId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const worldPlayableMarkdown = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:approach -->",
  "## Approach", "", "The wardens wait.", "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->",
  "### Gate", "", "A held north gate.", "",
].join("\n");

const shaA = createHash("sha256").update(worldPlayableMarkdown).digest("hex");
const shaB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

function worldActiveRun(run: string | null = runId, worldId = "world-b") {
  return {
    schema_version: "dmb_world_play_active_run_v2" as const,
    world_id: worldId,
    run_id: run,
    selected_at: run === null ? null : "2026-10-06T00:00:00Z",
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function worldRun(overrides: Partial<WorldPlayRunRecordV2> = {}): WorldPlayRunRecordV2 {
  return {
    schema_version: "dmb_world_play_run_record_v2",
    run_id: runId,
    world_id: "world-b",
    playable_artifact_id: artifactId,
    playable_revision: 1,
    playable_work_revision_id: workRevisionId,
    playable_content_sha256: shaA,
    run_revision: 1,
    created_at: "2026-09-30T00:00:00Z",
    updated_at: "2026-09-30T00:00:00Z",
    progress: {
      current_scene_id: "scene:gate",
      current_beat_id: "beat:approach",
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    },
    ...overrides,
  };
}

function worldCommitted(
  overrides: Partial<WorldOwnedRunbookCommittedRevisionV2> = {},
): WorldOwnedRunbookCommittedRevisionV2 {
  return {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: "world-b",
    document_id: artifactId,
    kind: "runbook",
    campaign_id: null,
    title: "North Gate",
    status: "active",
    object_revision: 1,
    work_revision_id: workRevisionId,
    revision_n: 1,
    markdown: worldPlayableMarkdown,
    content_sha256: shaA,
    has_divergent_working_copy: false,
    target_relpath: null,
    ...overrides,
  };
}

function mockReadyWorldRuns(runIds: string[] = [runId]) {
  vi.mocked(listWorldPlayRuns).mockResolvedValue({
    schema_version: "dmb_world_play_runs_list_v2",
    records: runIds.map((selectedRunId) => worldRun({ run_id: selectedRunId })),
  });
  vi.mocked(getWorldPlayRun).mockImplementation(async (selectedRunId) => worldRun({ run_id: selectedRunId }));
  vi.mocked(getWorldPlayRunReferenceManifest).mockImplementation(async (selectedRunId) => ({
    schema_version: "dmb_play_run_reference_manifest_v2",
    run_id: selectedRunId,
    playable_artifact_id: artifactId,
    playable_revision: 1,
    playable_content_sha256: shaA,
    beats: [{ beat_id: "beat:approach" }],
      scenes: [{ scene_id: "scene:gate", beat_id: "beat:approach" }],
      choices: [], options: [], edges: [],
    sealed_at: "2026-09-30T00:00:00Z",
  }));
  vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue(
    worldCommitted({ markdown: worldPlayableMarkdown }),
  );
}

describe("Play selected-World admission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    vi.stubGlobal("crypto", webcrypto);
    vi.mocked(getWorldPlayRunContent).mockImplementation(async (id, world) => {
      const result = vi.mocked(getWorldPlayRun).mock.results.at(-1);
      const run = result?.type === "return" ? await result.value : worldRun({ run_id: id, world_id: world });
      return { schema_version: "dmb_world_play_run_content_v1", world_id: world, run_id: id,
        origin: { playable_artifact_id: run.playable_artifact_id, playable_revision: run.playable_revision,
          playable_work_revision_id: run.playable_work_revision_id, playable_content_sha256: run.playable_content_sha256 },
        source: "pinned", edition_revision: 0, edition_revision_id: null, markdown: worldPlayableMarkdown,
        content_sha256: run.playable_content_sha256, structure_sha256: shaA,
        committed_at: "2026-10-18T00:00:00Z", observed_run_revision: run.run_revision };
    });
    vi.mocked(listWorldOwnedPlans).mockResolvedValue({ schema_version: "dmb_workspace_document_registry_v2", scope_mode: "world", world_id: "world-b", records: [] });
    vi.mocked(listWorldOwnedRunbooks).mockResolvedValue({ schema_version: "dmb_world_owned_runbooks_list_v2", scope_mode: "world", world_id: "world-b", records: [] });
    selectedWorldHarness.worldId = "world-b";
    selectedWorldHarness.legacy = false;
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockRejectedValue(new LiveApiError("Plan revision not found", 404));
    vi.mocked(listPlayRuns).mockResolvedValue({ records: [] } as Awaited<ReturnType<typeof listPlayRuns>>);
    vi.mocked(listWorldPlayRuns).mockResolvedValue({
      schema_version: "dmb_world_play_runs_list_v2",
      records: [],
    });
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
  });


  it.each(['same-surface','cross-surface'])('opens an admitted bound Run for %s guided inspection without persisting active selection',async route=>{
    mockReadyWorldRuns([runId]);
    const pins=runPins(worldRun()),scope:NavigationScope={worldId:'world-b',walkthroughId:'guided-run',epoch:0,step:'progress',index:8,bindings:{plan:pins.parent,run:pins.target}};
    const registry=new TourNavigationRegistry(()=>scope);
    function BuildOwner(){useTourNavigationOwner({worldId:'world-b',surface:'build',objectId:null,inspections:[]});return <p>Source surface</p>;}
    function Routed(){const location=useSyncExternalStore(subscribeAppLocation,getAppLocationSnapshot);return <>{location.startsWith('/build')?<BuildOwner/>:<PlaySurfacePage/>}<TourNavigationActions scope={scope} onOpened={()=>{}}/></>;}
    window.history.replaceState({},'',route==='cross-surface'?'/build?world=world-b':'/play?world=world-b&choose=1');
    render(<TourNavigationProvider registry={registry}><Routed/></TourNavigationProvider>);
    fireEvent.click(await screen.findByRole('button',{name:route==='cross-surface'?'Open Play':'Open the bound run',exact:true}));
    await screen.findByTestId('play-surface-ready');await act(async()=>{await Promise.resolve();});
    expect(new URLSearchParams(window.location.search).get('run')).toBe(runId);
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();expect(putWorldPlayRunProgress).not.toHaveBeenCalled();
    // Admission consumes only this read-only inspection intent. Explicit ordinary Load retains its normal semantics.
    fireEvent.click(screen.getByTestId('play-load-run'));
    fireEvent.click(await screen.findByTestId(`play-session-${runId}`));
    await waitFor(()=>expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith('world-b',runId));
  });
  it('refuses a newer bound Run on guided route entry before active-selection persistence',async()=>{
    mockReadyWorldRuns([runId]);const pins=runPins(worldRun()),scope:NavigationScope={worldId:'world-b',walkthroughId:'guided-run',epoch:0,step:'progress',index:8,bindings:{plan:pins.parent,run:pins.target}};
    const registry=new TourNavigationRegistry(()=>scope);registry.beginDestination(scope);
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun({run_revision:2}));
    render(<TourNavigationProvider registry={registry}><PlaySurfacePage/></TourNavigationProvider>);
    await screen.findByText(/exact bound Run version is unavailable/);expect(screen.queryByTestId('play-surface-ready')).not.toBeInTheDocument();expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });
  it("opens the shared Rules tool only on request without selecting or changing a Run", async () => {
    const { getRulesCatalog } = await import("../api/liveApi");
    window.history.replaceState({}, "", "/play?world=world-b&choose=1");
    render(<PlaySurfacePage />);
    expect(getRulesCatalog).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Tools", exact: true }));
    fireEvent.click(screen.getByRole("button", { name: "Rules Lookup", exact: true }));
    expect(await screen.findByText("No rules source is available.")).toBeInTheDocument();
    expect(getRulesCatalog).toHaveBeenCalledTimes(1);
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayRunProgress).not.toHaveBeenCalled();
    expect(putWorldPlayRunContentCommand).not.toHaveBeenCalled();
  });

  it.each(["<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->\n## Gate\n\n<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->\n### Approach\nLegacy scene.\n", "# Unmarked old source\n"])("rejects v1 manifest before content, active-pointer, rebase, progress or Agent publication (%#)", async markdown => {
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun());
    vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue(worldCommitted({ markdown }));
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v1", run_id: runId, playable_artifact_id: artifactId,
      playable_revision: 1, playable_content_sha256: shaA, sealed_at: "2026-09-30T00:00:00Z",
      elements: [{ kind: "scene", element_id: "scene:gate" }, { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" }],
    });
    render(<PlaySurfacePage />);
    expect(await screen.findByTestId("play-status-unsupported_playable")).toHaveTextContent("Play requires v2 markers");
    expect(screen.queryByTestId("play-surface-ready")).not.toBeInTheDocument();
    expect(getWorldPlayRunContent).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayRunProgress).not.toHaveBeenCalled();
    expect(putWorldPlayRunRebase).not.toHaveBeenCalled();
    expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.every(([value]) => value == null)).toBe(true);
  });

  it("explains Play at the exact root chooser without an inert Load or campaign creation form", async () => {
    selectedWorldHarness.legacy = true;
    vi.mocked(listPlayRuns).mockResolvedValue({records:[]} as never);
    window.history.replaceState({}, "", "/play?choose=1");
    render(<PlaySurfacePage/>);
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(screen.getByRole("heading",{name:"Bring your next session to life"})).toBeInTheDocument();
    expect(screen.getByText("Choose your World")).toBeInTheDocument();
    expect(screen.queryByTestId("play-load-run")).not.toBeInTheDocument();
    expect(screen.queryByText("Start Run")).not.toBeInTheDocument();
    expect(screen.queryByText(/No saved sessions yet/)).not.toBeInTheDocument();
  });
  it("offers the selected World's Plan workflow and omits Load while already choosing", async () => {
    window.history.replaceState({}, "", "/play?world=world-b&choose=1");
    render(<PlaySurfacePage/>);
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(screen.getByRole("link",{name:"Open a Plan →"})).toHaveAttribute("href","/plan?world=world-b");
    expect(screen.queryByTestId("play-load-run")).not.toBeInTheDocument();
  });
  it("aborts the previous World's run inventory when navigation changes", async () => {
    const first = deferred<Awaited<ReturnType<typeof listWorldPlayRuns>>>();
    let firstSignal: AbortSignal | undefined;
    vi.mocked(listWorldPlayRuns).mockImplementation((worldId, signal) => {
      if (worldId === "world-b") {
        firstSignal = signal;
        return first.promise;
      }
      return Promise.resolve({ schema_version: "dmb_world_play_runs_list_v2", records: [] });
    });
    window.history.replaceState({}, "", "/play?world=world-b&choose=1");
    const view = render(<PlaySurfacePage />);
    await waitFor(() => expect(firstSignal).toBeDefined());

    await act(async () => {
      selectedWorldHarness.worldId = "world-a";
      window.history.replaceState({}, "", "/play?world=world-a&choose=1");
      window.dispatchEvent(new PopStateEvent("popstate"));
      view.rerender(<PlaySurfacePage />);
    });

    expect(firstSignal?.aborted).toBe(true);
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    await act(async () => {
      first.resolve({ schema_version: "dmb_world_play_runs_list_v2", records: [worldRun()] });
      await first.promise;
    });
    expect(screen.queryByTestId(`play-session-${runId}`)).not.toBeInTheDocument();
  });
  it("puts the selected Plan's active session first with its title and notes, without creating anything", async () => {
    window.history.replaceState({}, "", `/play?world=world-b&choose=1&plan=${artifactId}`);
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun(runId));
    const active = worldRun({ progress: { ...worldRun().progress, notes_by_element_id: { "scene:gate": "The gate is sealed", "scene:empty": " " } } });
    const newer = worldRun({ run_id: secondRunId, updated_at: "2026-10-18T18:10:00Z" });
    const other = worldRun({ run_id: "ffffffff-ffff-4fff-8fff-ffffffffffff", playable_artifact_id: newerWorkRevisionId, updated_at: "2026-10-19T00:00:00Z" });
    vi.mocked(listWorldPlayRuns).mockResolvedValue({ schema_version: "dmb_world_play_runs_list_v2", records: [other, newer, active] });
    vi.mocked(listWorldOwnedPlans).mockResolvedValue({ schema_version: "dmb_workspace_document_registry_v2", scope_mode: "world", world_id: "world-b", records: [{
      schema_version: "dmb_world_owned_plan_record_v2", scope_mode: "world", document_id: artifactId,
      title: "Approach to Edge", campaign_id: null, world_id: "world-b", target_session: null,
      kind: "plan", target_relpath: null, status: "active", content_status: "committed", revision: 1,
      created_at: active.created_at, updated_at: active.updated_at,
    }] });
    render(<PlaySurfacePage />);
    expect(await screen.findByRole("heading", { name: "Approach to Edge" })).toBeInTheDocument();
    const resume = await screen.findByRole("link", { name: /Resume session · Approach to Edge/ });
    expect(resume).toHaveAttribute("href", expect.stringContaining(runId));
    expect(resume).toHaveTextContent("1 saved note");
    expect(resume).toHaveTextContent("Last played");
    expect(resume).not.toHaveTextContent(runId);
    expect(screen.getByText("Other sessions (1)").parentElement).not.toHaveAttribute("open");
    expect(screen.getByText("Sessions from other Plans (1)").parentElement).not.toHaveAttribute("open");
    expect(screen.getByText("Start a new session from this Plan").parentElement).not.toHaveAttribute("open");
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayRunProgress).not.toHaveBeenCalled();
    expect(screen.getAllByRole("link", { name: /Resume session/ })).toHaveLength(1);
  });

  it("keeps sessions usable when titles and active metadata fail, using the newest matching session", async () => {
    window.history.replaceState({}, "", `/play?world=world-b&choose=1&plan=${artifactId}`);
    vi.mocked(getWorldPlayActiveRun).mockRejectedValue(new Error("metadata unavailable"));
    vi.mocked(listWorldOwnedPlans).mockRejectedValue(new Error("titles unavailable"));
    vi.mocked(listWorldOwnedRunbooks).mockRejectedValue(new Error("titles unavailable"));
    vi.mocked(listWorldPlayRuns).mockResolvedValue({ schema_version: "dmb_world_play_runs_list_v2", records: [worldRun(), worldRun({ run_id: secondRunId, updated_at: "2026-10-18T18:10:00Z" })] });
    render(<PlaySurfacePage />);
    const resume = await screen.findByRole("link", { name: /Resume session · Saved session/ });
    expect(resume).toHaveAttribute("href", expect.stringContaining(secondRunId));
    expect(resume).not.toHaveTextContent(secondRunId);
    expect(screen.queryByText("Choose a Run")).not.toBeInTheDocument();
  });

  it("does not recommend an unrelated session when the selected Plan has never been played", async () => {
    window.history.replaceState({}, "", `/play?world=world-b&choose=1&plan=${newerWorkRevisionId}`);
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun(runId));
    vi.mocked(listWorldPlayRuns).mockResolvedValue({ schema_version: "dmb_world_play_runs_list_v2", records: [worldRun()] });
    render(<PlaySurfacePage />);
    expect(await screen.findByText("You haven’t played this Plan yet. Start a session below.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Resume session/ })).not.toBeInTheDocument();
    expect(screen.getByText("Start a new session from this Plan").parentElement).toHaveAttribute("open");
  });

  it("rejects a foreign World V2 Run without using campaign V1", async () => {
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun({ world_id: "world-a" }));
    render(<PlaySurfacePage />);
    expect(await screen.findByText(`Run ${runId} does not belong to World world-b.`)).toBeInTheDocument();
    expect(getWorldPlayRun).toHaveBeenCalledExactlyOnceWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("lists, selects, and resumes a World V2 Run from its exact World Runbook pin", async () => {
    const committed = worldCommitted({ markdown: worldPlayableMarkdown });
    window.history.replaceState({}, "", "/play?world=world-b&choose=1");
    vi.mocked(listWorldPlayRuns).mockResolvedValue({
      schema_version: "dmb_world_play_runs_list_v2",
      records: [worldRun()],
    });
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      beats: [{ beat_id: "beat:approach" }],
      scenes: [{ scene_id: "scene:gate", beat_id: "beat:approach" }],
      choices: [], options: [], edges: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue(committed);

    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    const listedRun = await screen.findByTestId(`play-session-${runId}`);
    expect(listedRun).toHaveTextContent("Resume session");
    expect(listedRun).not.toHaveTextContent(runId);
    await user.click(listedRun);

    const ready = await screen.findByTestId("play-surface-ready");
    expect(ready).toHaveAttribute("data-play-campaign-id", "");
    expect(await screen.findByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(playDetails("play-source-cue")).toHaveTextContent("Created from saved Runbook version 1");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(listWorldPlayRuns).toHaveBeenCalledExactlyOnceWith("world-b", expect.any(AbortSignal));
    expect(listPlayRuns).not.toHaveBeenCalled();
    expect(getWorldPlayRunReferenceManifest).toHaveBeenCalledWith(runId, "world-b");
    expect(getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledWith(artifactId, "world-b", 1, shaA);
    expect(getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledWith(artifactId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).toHaveBeenCalledWith("world-b", runId);
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("reenters the exact World Run through the scoped active pointer and validates its detail", async () => {
    const committed = worldCommitted({ markdown: worldPlayableMarkdown });
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      beats: [{ beat_id: "beat:approach" }],
      scenes: [{ scene_id: "scene:gate", beat_id: "beat:approach" }],
      choices: [], options: [], edges: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue(committed);

    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(getWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(getWorldPlayRun).toHaveBeenCalledTimes(2);
    expect(getWorldPlayRun).toHaveBeenNthCalledWith(1, runId, "world-b");
    expect(getWorldPlayRun).toHaveBeenNthCalledWith(2, runId, "world-b");
    expect(window.location.search).toBe(`?world=world-b&run=${runId}`);
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
    expect(getPlayActiveRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("selects the same Run again after another World pointer is read and the chooser is reopened", async () => {
    mockReadyWorldRuns([runId, secondRunId]);
    vi.mocked(getWorldPlayActiveRun).mockResolvedValueOnce(worldActiveRun(secondRunId));
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId));

    await act(async () => {
      window.history.pushState({}, "", "/play?world=world-b");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => expect(window.location.search).toBe(`?world=world-b&run=${secondRunId}`));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("play-load-run"));
    const firstRun = await screen.findByTestId(`play-session-${runId}`);
    await user.click(firstRun);
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();

    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2));
    expect(putWorldPlayActiveRun).toHaveBeenLastCalledWith("world-b", runId);
  });

  it("allows an explicit same-Run selection to retry after the active-pointer PUT fails", async () => {
    mockReadyWorldRuns([runId]);
    vi.mocked(putWorldPlayActiveRun)
      .mockRejectedValueOnce(new Error("pointer write failed"))
      .mockResolvedValue(worldActiveRun());
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-save-warning")).toHaveTextContent("pointer write failed");
    expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId);

    await user.click(screen.getByTestId("play-load-run"));
    await user.click(await screen.findByTestId(`play-session-${runId}`));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();

    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2));
    expect(putWorldPlayActiveRun).toHaveBeenLastCalledWith("world-b", runId);
  });

  it("does not repeat the active-pointer PUT when a same-Run progress update triggers re-admission", async () => {
    mockReadyWorldRuns([runId]);
    vi.mocked(putWorldPlayRunProgress).mockResolvedValue(worldRun({
      run_revision: 2,
      playable_revision: 2,
      playable_work_revision_id: newerWorkRevisionId,
      playable_content_sha256: shaB,
    }));
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId));
    await user.click(screen.getByRole("button", { name: /Notes · Gate/ }));
    fireEvent.change(screen.getByLabelText("Scene note"), { target: { value: "Trigger exact Run re-admission." } });
    await user.click(screen.getByRole("button", { name: "Save note now", exact: true }));

    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledTimes(2));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(putWorldPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId);
  });

  it("keeps a newer World selection fence when an older active-pointer PUT fails late", async () => {
    mockReadyWorldRuns([runId, secondRunId]);
    const firstSelection = deferred<Awaited<ReturnType<typeof putWorldPlayActiveRun>>>();
    vi.mocked(putWorldPlayActiveRun).mockImplementation(async (_worldId, selectedRunId) => {
      if (selectedRunId === runId) return firstSelection.promise;
      return worldActiveRun(selectedRunId);
    });
    vi.mocked(putWorldPlayRunProgress).mockResolvedValue(worldRun({
      run_id: secondRunId,
      run_revision: 2,
      playable_revision: 2,
      playable_work_revision_id: newerWorkRevisionId,
      playable_content_sha256: shaB,
    }));
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    const user = userEvent.setup();
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId));
    await user.click(screen.getByTestId("play-load-run"));
    await user.click(await screen.findByTestId(`play-session-${secondRunId}`));
    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();

    await act(async () => {
      firstSelection.reject(new Error("stale pointer PUT failed"));
    });
    await waitFor(() => expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2));
    expect(putWorldPlayActiveRun).toHaveBeenLastCalledWith("world-b", secondRunId);

    await user.click(screen.getByRole("button", { name: /Notes · Gate/ }));
    fireEvent.change(screen.getByLabelText("Scene note"), { target: { value: "Trigger exact Run re-admission." } });
    await user.click(screen.getByRole("button", { name: "Save note now", exact: true }));
    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledTimes(3));
    expect(putWorldPlayActiveRun).toHaveBeenCalledTimes(2);
  });

  it("keeps the exact saved Plan source cue at version 3 after the current Plan advances to 4", async () => {
    const planRun = worldRun({ playable_revision: 3, run_revision: 2, playable_work_revision_id: workRevisionId });
    const committedPlan: WorldOwnedCommittedRevisionV2 = {
      schema_version: "dmb_workspace_committed_revision_v2",
      scope_mode: "world",
      world_id: "world-b",
      campaign_id: null,
      document_id: artifactId,
      kind: "plan",
      title: "North Gate Plan",
      status: "discarded",
      object_revision: 9,
      work_revision_id: workRevisionId,
      revision_n: 3,
      markdown: worldPlayableMarkdown,
      content_sha256: shaA,
      has_divergent_working_copy: true,
      target_relpath: null,
    };
    vi.mocked(getWorldPlayRun).mockResolvedValue(planRun);
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 3,
      playable_content_sha256: shaA,
      beats: [{ beat_id: "beat:approach" }],
      scenes: [{ scene_id: "scene:gate", beat_id: "beat:approach" }],
      choices: [], options: [], edges: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    const currentPlan = {
      ...committedPlan,
      status: "active" as const,
      object_revision: 10,
      work_revision_id: newerWorkRevisionId,
      revision_n: 4,
      content_sha256: shaB,
    };
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockImplementation(async (_documentId, revisionN) => (
      revisionN === undefined ? currentPlan : committedPlan
    ));

    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-surface-ready")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(playDetails("play-source-cue")).toHaveTextContent("Created from saved Plan version 3");
    expect(screen.queryByText(/version 4/)).not.toBeInTheDocument();
    expect(getWorldOwnedPlanCommittedRevision).toHaveBeenCalledExactlyOnceWith(artifactId, 3);
    expect(getWorldOwnedRunbookCommittedRevision).not.toHaveBeenCalled();
    expect(putWorldPlayRunRebase).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b", runId);
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("keeps a chooser when World active detail belongs to another World", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun({ world_id: "world-a" }));
    render(<PlaySurfacePage />);
    await waitFor(() => expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument());
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(getPlayActiveRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("uses the empty World v2 pointer as an explicit chooser state", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun(null));
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayRun).not.toHaveBeenCalled();
    expect(getPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("does not navigate through an invalid World active pointer", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue({
      ...worldActiveRun(),
      run_id: "not-a-canonical-run-id",
    });
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-warning")).toHaveTextContent("malformed");
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("keeps the World chooser when the active pointer cannot be resolved in World V2", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    vi.mocked(getWorldPlayRun).mockRejectedValue(new Error("World detail unavailable"));
    render(<PlaySurfacePage />);

    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    expect(await screen.findByTestId("play-active-run-warning")).toHaveTextContent("Choose a Run explicitly");
    expect(window.location.search).toBe("?world=world-b");
    expect(getWorldPlayActiveRun).toHaveBeenCalledExactlyOnceWith("world-b");
    expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(putPlayActiveRun).not.toHaveBeenCalled();
    expect(putWorldPlayActiveRun).not.toHaveBeenCalled();
  });

  it("ignores a late World V2 detail after navigation returns to the chooser", async () => {
    let resolveWorldRun: ((run: WorldPlayRunRecordV2) => void) | null = null;
    vi.mocked(getWorldPlayRun).mockImplementation(() => new Promise((resolve) => {
      resolveWorldRun = resolve;
    }));
    vi.mocked(getWorldPlayActiveRun).mockResolvedValue(worldActiveRun());
    render(<PlaySurfacePage />);
    expect(await screen.findByTestId("play-status-loading")).toBeInTheDocument();

    await act(async () => {
      window.history.pushState({}, "", "/play?world=world-b&choose=1");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    await act(async () => {
      resolveWorldRun?.(worldRun());
    });

    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledWith(runId, "world-b"));
    expect(screen.queryByTestId("play-surface-ready")).not.toBeInTheDocument();
    expect(getWorldPlayRunReferenceManifest).not.toHaveBeenCalled();
    expect(getWorldOwnedRunbookCommittedRevision).not.toHaveBeenCalled();
    expect(getPlayRun).not.toHaveBeenCalled();
  });

  it("offers an explicit same-World rebase and keeps the exact Run on conflict", async () => {
    const exact = worldCommitted();
    const current = worldCommitted({
      object_revision: 2,
      work_revision_id: newerWorkRevisionId,
      revision_n: 2,
      content_sha256: shaB,
      markdown: "# New Gate\n",
    });
    vi.mocked(getWorldPlayRun).mockResolvedValue(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      beats: [{ beat_id: "beat:approach" }], scenes: [{ scene_id: "scene:gate", beat_id: "beat:approach" }], choices: [], options: [], edges: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision)
      .mockResolvedValueOnce(exact)
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(current);
    vi.mocked(putWorldPlayRunRebase).mockRejectedValue(new Error("revision changed"));
    vi.mocked(getWorldPlayRun).mockResolvedValueOnce(worldRun()).mockResolvedValueOnce(worldRun());

    const user = userEvent.setup();
    render(<PlaySurfacePage />);
    const rebase = await screen.findByTestId("play-world-run-rebase");
    expect(screen.getByText(/pinned to revision 1/)).toBeInTheDocument();
    await user.click(rebase);

    expect(putWorldPlayRunRebase).toHaveBeenCalledWith(runId, "world-b", {
      expected_run_revision: 1,
      target_playable_revision: 2,
      target_playable_content_sha256: shaB,
    });
    await waitFor(() => expect(screen.getByText(/revision changed/)).toBeInTheDocument());
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(getCommittedWorkspaceRevision).not.toHaveBeenCalled();
    expect(getWorldPlayRun).toHaveBeenCalledTimes(2);
  });

  it("does not adopt a completed World B rebase after the route switches to World A", async () => {
    const exact = worldCommitted();
    const current = worldCommitted({
      object_revision: 2,
      work_revision_id: newerWorkRevisionId,
      revision_n: 2,
      content_sha256: shaB,
      markdown: "# New Gate\n",
    });
    const pendingRebase = deferred<WorldPlayRunRecordV2>();
    vi.mocked(getWorldPlayRun).mockResolvedValueOnce(worldRun());
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      beats: [{ beat_id: "beat:approach" }], scenes: [{ scene_id: "scene:gate", beat_id: "beat:approach" }], choices: [], options: [], edges: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision)
      .mockResolvedValueOnce(exact)
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(current);
    vi.mocked(putWorldPlayRunRebase).mockReturnValueOnce(pendingRebase.promise);

    const user = userEvent.setup();
    const view = render(<PlaySurfacePage />);
    await user.click(await screen.findByTestId("play-world-run-rebase"));
    await waitFor(() => expect(putWorldPlayRunRebase).toHaveBeenCalledWith(runId, "world-b", {
      expected_run_revision: 1,
      target_playable_revision: 2,
      target_playable_content_sha256: shaB,
    }));

    await act(async () => {
      selectedWorldHarness.worldId = "world-a";
      window.history.replaceState({}, "", "/play?world=world-a&choose=1");
      window.dispatchEvent(new PopStateEvent("popstate"));
      view.rerender(<PlaySurfacePage />);
    });
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    await waitFor(() => expect(listWorldPlayRuns).toHaveBeenCalledWith("world-a", expect.any(AbortSignal)));

    await act(async () => {
      pendingRebase.resolve(worldRun({
        playable_revision: 2,
        playable_work_revision_id: newerWorkRevisionId,
        playable_content_sha256: shaB,
        run_revision: 2,
        rebased_from_run_revision: 1,
      }));
      await pendingRebase.promise;
    });

    expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument();
    expect(window.location.search).toBe("?world=world-a&choose=1");
    expect(getWorldPlayRun).toHaveBeenCalledExactlyOnceWith(runId, "world-b");
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(listPlayRuns).not.toHaveBeenCalled();
  });

  it("does not adopt World B after an uncertain rebase is confirmed by exact reconciliation", async () => {
    const exact = worldCommitted();
    const current = worldCommitted({
      object_revision: 2,
      work_revision_id: newerWorkRevisionId,
      revision_n: 2,
      content_sha256: shaB,
      markdown: "# New Gate\n",
    });
    const pendingRebase = deferred<WorldPlayRunRecordV2>();
    const pendingReconciliation = deferred<WorldPlayRunRecordV2>();
    vi.mocked(getWorldPlayRun)
      .mockResolvedValueOnce(worldRun())
      .mockReturnValueOnce(pendingReconciliation.promise);
    vi.mocked(getWorldPlayRunReferenceManifest).mockResolvedValue({
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: runId,
      playable_artifact_id: artifactId,
      playable_revision: 1,
      playable_content_sha256: shaA,
      beats: [{ beat_id: "beat:approach" }], scenes: [{ scene_id: "scene:gate", beat_id: "beat:approach" }], choices: [], options: [], edges: [],
      sealed_at: "2026-09-30T00:00:00Z",
    });
    vi.mocked(getWorldOwnedRunbookCommittedRevision)
      .mockResolvedValueOnce(exact)
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(current);
    vi.mocked(putWorldPlayRunRebase).mockReturnValueOnce(pendingRebase.promise);

    const user = userEvent.setup();
    const view = render(<PlaySurfacePage />);
    await user.click(await screen.findByTestId("play-world-run-rebase"));
    await waitFor(() => expect(putWorldPlayRunRebase).toHaveBeenCalledWith(runId, "world-b", {
      expected_run_revision: 1,
      target_playable_revision: 2,
      target_playable_content_sha256: shaB,
    }));

    await act(async () => {
      selectedWorldHarness.worldId = "world-a";
      window.history.replaceState({}, "", "/play?world=world-a&choose=1");
      window.dispatchEvent(new PopStateEvent("popstate"));
      view.rerender(<PlaySurfacePage />);
    });
    expect(await screen.findByTestId("play-run-chooser")).toBeInTheDocument();
    await waitFor(() => expect(listWorldPlayRuns).toHaveBeenCalledWith("world-a", expect.any(AbortSignal)));

    await act(async () => {
      pendingRebase.reject(new Error("rebase response lost"));
    });
    await waitFor(() => expect(getWorldPlayRun).toHaveBeenCalledTimes(2));
    await act(async () => {
      pendingReconciliation.resolve(worldRun({
        playable_revision: 2,
        playable_work_revision_id: newerWorkRevisionId,
        playable_content_sha256: shaB,
        run_revision: 2,
        rebased_from_run_revision: 1,
      }));
      await pendingReconciliation.promise;
    });

    expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument();
    expect(window.location.search).toBe("?world=world-a&choose=1");
    expect(getWorldPlayRun).toHaveBeenCalledTimes(2);
    expect(getPlayRun).not.toHaveBeenCalled();
    expect(listPlayRuns).not.toHaveBeenCalled();
  });
});

function effectiveFixture(world = "world-b", id = runId) {
  const markdown = "<!-- dmb-playable-element:v2 kind=beat id=beat:one -->\n## One\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\n### Gate\n\nOrigin prose.\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:hall -->\n### Hall\n\nHall prose.\n";
  const hash = (text: string) => createHash("sha256").update(text).digest("hex");
  const run = worldRun({ run_id: id, world_id: world, playable_content_sha256: hash(markdown),
    progress: { ...worldRun().progress, current_beat_id: "beat:one", current_scene_id: "scene:gate", notes_by_element_id: { "scene:gate": "Retained note" } } });
  const committed = { ...worldCommitted({ markdown, content_sha256: hash(markdown) }), world_id: world, kind: "plan" as const };
  const manifest = { schema_version: "dmb_play_run_reference_manifest_v2" as const, run_id: id, playable_artifact_id: artifactId,
    playable_revision: 1, playable_content_sha256: hash(markdown), sealed_at: "2026-10-18T00:00:00Z", beats: [{ beat_id: "beat:one" }],
    scenes: [{ scene_id: "scene:gate", beat_id: "beat:one" }, { scene_id: "scene:hall", beat_id: "beat:one" }], choices: [], options: [], edges: [] };
  const text = markdown.replace("Origin prose.", 'Session prose.\n\n| Item | Value |\n| --- | --- |\n| Gate | Open |\n\n> [!GM-NOTE]\n> Keep watch.\n\n![Map](dmb-media:dddddddd-dddd-4ddd-8ddd-dddddddddddd "dmb-image:v1 width=50 collapsed=false")');
  const content: PlayRunContent = { schema_version: "dmb_world_play_run_content_v1", world_id: world, run_id: id,
    origin: { playable_artifact_id: artifactId, playable_revision: 1, playable_work_revision_id: workRevisionId, playable_content_sha256: hash(markdown) },
    source: "edition", edition_revision: 2, edition_revision_id: newerWorkRevisionId, markdown: text, content_sha256: hash(text),
    structure_sha256: shaA, committed_at: "2026-10-18T01:00:00Z", observed_run_revision: 1 };
  return { run, committed, manifest, content, hash };
}
function mockEffectiveFixture() {
  vi.mocked(getWorldPlayRun).mockImplementation(async (id, world) => effectiveFixture(world, id).run);
  vi.mocked(getWorldPlayRunReferenceManifest).mockImplementation(async (id, world) => effectiveFixture(world, id).manifest);
  vi.mocked(getWorldOwnedPlanCommittedRevision).mockImplementation(async () => effectiveFixture(selectedWorldHarness.worldId).committed);
  vi.mocked(getWorldPlayRunContent).mockImplementation(async (id, world) => effectiveFixture(world, id).content);
}
describe("World session-copy projection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("crypto", webcrypto);
    window.localStorage.clear();
    selectedWorldHarness.worldId = "world-b";
    selectedWorldHarness.legacy = false;
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
    mockEffectiveFixture();
  });
  it("keeps a trashed session deep link out of the active workspace and offers recovery", async () => {
    const data=effectiveFixture();vi.mocked(getWorldPlayRun).mockResolvedValue({...data.run,lifecycle_status:"trashed"});
    render(<PlaySurfacePage />);
    expect(await screen.findByTestId("play-status-trashed")).toHaveTextContent("Session in Trash");
    expect(screen.queryByRole("button",{name:"Trash",exact:true})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"Edit session"})).not.toBeInTheDocument();
    expect(screen.queryByTestId("play-surface-ready")).not.toBeInTheDocument();
    expect(getWorldPlayRunContent).not.toHaveBeenCalled();
  });
  it("renders effective native text, tables, callouts and media with explicit provenance and exact saved-edition Agent registration", async () => {
    const data = effectiveFixture();
    render(<PlaySurfacePage />);
    await screen.findByTestId("play-surface-ready");
    expect(playDetails("play-source-cue")).toHaveTextContent("Session copy · revision 2");
    expect(screen.getByText("Session prose.")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Session copy Agent availability" })).not.toBeInTheDocument();
    expect(screen.queryByText("Origin prose.")).not.toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("Gate");
    expect(screen.getByText("Keep watch.")).toBeInTheDocument();
    expect(document.querySelector('[data-effective-content-sha256]')).toHaveAttribute("data-effective-content-sha256", data.content.content_sha256);
    expect(document.querySelector('[data-source-state="run-edition"]')).toHaveAttribute("data-work-revision-id", workRevisionId);
    expect(screen.getByTestId("scene-card-source-cue")).toHaveTextContent("Session copy · revision 2 · From Plan version 1");
    expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.at(-1)).toEqual([expect.objectContaining({ worldId: data.content.world_id, runId, runRevision: data.run.run_revision,
      contentBasis: { edition_revision: 2, edition_revision_id: data.content.edition_revision_id, content_sha256: data.content.content_sha256 } }), null]);
    expect(data.committed.markdown).toContain("Origin prose.");
  });
  it("blocks Buddy for unsaved and saving scene notes, then publishes the accepted Run revision", async () => {
    const data = effectiveFixture();
    const pending = deferred<WorldPlayRunRecordV2>();
    vi.mocked(putWorldPlayRunProgress).mockReturnValue(pending.promise);
    render(<PlaySurfacePage />);
    await screen.findByTestId("play-surface-ready");
    expect(vi.mocked(useCombatProjection).mock.calls.at(-1)?.[2]).toMatchObject({tourRun:runPins(data.run)});
    await userEvent.click(screen.getByRole("button", { name: /Notes · Gate/ }));
    fireEvent.change(screen.getByLabelText("Scene note"), { target: { value: "A new saved scene note." } });
    await waitFor(() => expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.at(-1)?.[0]).toBeNull());
    await waitFor(() => expect(putWorldPlayRunProgress).toHaveBeenCalled());
    expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.at(-1)?.[0]).toBeNull();
    expect(screen.getByRole("button", {name:"Delete",exact:true})).toBeDisabled();
    await act(async () => pending.resolve({ ...data.run, run_revision: data.run.run_revision + 1,
      progress: { ...data.run.progress, notes_by_element_id: { "scene:gate": "A new saved scene note." } } }));
    await waitFor(() => expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.at(-1)).toEqual([
      expect.objectContaining({ runRevision: data.run.run_revision + 1, contentBasis: expect.objectContaining({ edition_revision: 2 }) }), null,
    ]));
    expect(vi.mocked(useCombatProjection).mock.calls.at(-1)?.[2]).toMatchObject({tourRun:runPins({...data.run,run_revision:data.run.run_revision+1})});
  });
  it("keeps Buddy blocked while a recovered scene note draft hydrates", async () => {
    const first = render(<PlaySurfacePage />);
    await screen.findByTestId("play-surface-ready");
    await userEvent.click(screen.getByRole("button", { name: /Notes · Gate/ }));
    fireEvent.change(screen.getByLabelText("Scene note"), { target: { value: "Recovered unsaved note." } });
    first.unmount();
    vi.mocked(usePublishWorldPlayConversation).mockClear();
    render(<PlaySurfacePage />);
    await screen.findByTestId("play-surface-ready");
    await userEvent.click(screen.getByRole("button", { name: /Notes · Gate/ }));
    expect(screen.getByLabelText("Scene note")).toHaveValue("Recovered unsaved note.");
    expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.every(([context]) => context === null)).toBe(true);
  });
  it("retains the session copy after a progress/notes refresh and does not fetch a newer legacy source to demand rebase", async () => {
    const data = effectiveFixture();
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockRejectedValue(new LiveApiError("not Plan", 404));
    vi.mocked(getWorldOwnedRunbookCommittedRevision).mockResolvedValue({ ...data.committed, kind: "runbook" });
    vi.mocked(putWorldPlayRunProgress).mockImplementation(async (_id, _world, request) => ({ ...data.run, run_revision: 2, progress: request.progress }));
    const user = userEvent.setup();
    render(<PlaySurfacePage />);
    await screen.findByText("Session prose.");
    await user.click(screen.getByRole("button", { name: "Show scene: Hall", exact: true }));
    await user.click(screen.getByTestId("play-make-current"));
    await waitFor(() => expect(putWorldPlayRunProgress).toHaveBeenCalledOnce());
    expect(playDetails("play-source-cue")).toHaveTextContent("Session copy · revision 2");
    await user.click(screen.getByRole("button", { name: "Show scene: Gate", exact: true }));
    expect(await screen.findByText("Session prose.")).toBeInTheDocument();
    expect(getWorldOwnedRunbookCommittedRevision).toHaveBeenCalledTimes(1);
    expect(putWorldPlayRunRebase).not.toHaveBeenCalled();
    expect(vi.mocked(putWorldPlayRunProgress).mock.calls[0][2].progress.notes_by_element_id).toEqual(data.run.progress.notes_by_element_id);
  });
  it.each(["world", "origin", "hash", "missing"])("fails closed for %s content without rendering the original as fallback", async kind => {
    const data = effectiveFixture();
    if (kind === "missing") vi.mocked(getWorldPlayRunContent).mockRejectedValue(new LiveApiError("missing edition", 404));
    else vi.mocked(getWorldPlayRunContent).mockResolvedValue({ ...data.content,
      ...(kind === "world" ? { world_id: "foreign" } : kind === "origin" ? { origin: { ...data.content.origin, playable_revision: 99 } } : { markdown: "tampered" }) });
    render(<PlaySurfacePage />);
    await screen.findByTestId("play-status-integrity_failure");
    expect(screen.queryByText("Origin prose.")).not.toBeInTheDocument();
    expect(screen.queryByTestId("play-surface-ready")).not.toBeInTheDocument();
  });
  it("keeps an unmodified revision zero session on the original projection and Agent path", async () => {
    const data = effectiveFixture();
    vi.mocked(getWorldPlayRunContent).mockResolvedValue({ ...data.content, source: "pinned", edition_revision: 0, edition_revision_id: null,
      markdown: data.committed.markdown, content_sha256: data.run.playable_content_sha256 });
    render(<PlaySurfacePage />);
    expect(await screen.findByTestId("play-workspace-current")).toHaveTextContent("Origin prose.");
    expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.at(-1)?.[0]).toMatchObject({ runId, runRevision: 1 });
    expect(screen.queryByText(/Session copy · revision/)).not.toBeInTheDocument();
    expect(screen.queryByTestId("play-session-copy-agent-notice")).not.toBeInTheDocument();
  });
  it("shows the Agent limitation and gates sends as soon as an unsaved first session-copy draft exists", async () => {
    const data = effectiveFixture();
    vi.mocked(getWorldPlayRunContent).mockResolvedValue({ ...data.content, source: "pinned", edition_revision: 0, edition_revision_id: null,
      markdown: data.committed.markdown, content_sha256: data.run.playable_content_sha256 });
    const user = userEvent.setup();
    render(<PlaySurfacePage />);
    expect(await screen.findByTestId("play-workspace-current")).toHaveTextContent("Origin prose.");
    await user.click(screen.getByRole("button", { name: "Edit session" }));
    await user.click(screen.getByRole("button", { name: "Markdown" }));
    await user.type(screen.getByRole("textbox", { name: "Session copy Markdown" }), "\nFirst unsaved edit.");
    expect(await screen.findByRole("status", { name: "Session copy Agent availability" }))
      .toHaveTextContent("Save your session changes before asking Buddy.");
    expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.at(-1))
      .toEqual([null, expect.stringContaining("Save your session changes")]);
    expect(putWorldPlayRunProgress).not.toHaveBeenCalled();
    expect(screen.getByRole("button", {name:"Delete",exact:true})).toBeDisabled();
    expect(screen.queryByRole("button", {name:"Trash",exact:true})).not.toBeInTheDocument();
  });
  it("keeps the current scene and its note when an edited session copy is accepted", async () => {
    const data = effectiveFixture();
    const edited = data.content.markdown.replace("Session prose.", "Revised session prose.");
    const canonical = (value: unknown): string => Array.isArray(value) ? `[${value.map(canonical).join(",")}]`
      : typeof value === "object" && value !== null ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical((value as Record<string, unknown>)[key])}`).join(",")}}`
        : JSON.stringify(value) ?? "null";
    vi.mocked(getWorldPlayRun).mockResolvedValue({ ...data.run, progress: { ...data.run.progress,
      notes_by_element_id: { ...data.run.progress.notes_by_element_id, "scene:hall": "Keep this scene note." } } });
    vi.mocked(putWorldPlayRunProgress).mockImplementation(async (_id, _world, request) => ({ ...data.run, run_revision: 2, progress: request.progress }));
    vi.mocked(putWorldPlayRunContentCommand).mockImplementation(async (_run, _world, commandId, request) => ({
      schema_version: "dmb_world_play_run_content_receipt_v1", world_id: data.content.world_id, run_id: data.content.run_id,
      command_id: commandId, request_sha256: data.hash(canonical({ world_id: data.content.world_id, run_id: data.content.run_id, command_id: commandId, ...request })),
      origin: data.content.origin, expected_edition_revision: request.expected_edition_revision,
      expected_content_sha256: request.expected_content_sha256, accepted_edition_revision: request.expected_edition_revision + 1,
      accepted_edition_revision_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", accepted_content_sha256: data.hash(request.markdown),
      committed_at: "2026-10-18T02:00:00Z", observed_run_revision: 2,
    }));
    vi.mocked(getWorldPlayRunContent).mockImplementation(async () => putWorldPlayRunContentCommand.mock.calls.length
      ? { ...data.content, source: "edition", edition_revision: 3, edition_revision_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        markdown: edited, content_sha256: data.hash(edited), committed_at: "2026-10-18T02:00:00Z" }
      : data.content);

    const user = userEvent.setup();
    render(<PlaySurfacePage />);
    await screen.findByText("Session prose.");
    await user.click(screen.getByRole("button", { name: "Show scene: Hall", exact: true }));
    await user.click(screen.getByTestId("play-make-current"));
    await waitFor(() => expect(putWorldPlayRunProgress).toHaveBeenCalledOnce());
    await user.click(screen.getByRole("button", { name: "Edit session" }));
    await user.click(screen.getByRole("button", { name: "Markdown" }));
    const editor = screen.getByRole("textbox", { name: "Session copy Markdown" });
    fireEvent.change(editor, { target: { value: edited } });
    await waitFor(() => expect(putWorldPlayRunContentCommand).toHaveBeenCalledOnce(), { timeout: 5000 });
    expect(screen.getByRole("textbox", { name: "Session copy Markdown" })).toHaveValue(edited);
    expect(screen.getByTestId("play-current-moment-cockpit")).toHaveAttribute("data-current-scene-id", "scene:hall");
    await waitFor(() => expect(vi.mocked(usePublishWorldPlayConversation).mock.calls.at(-1)?.[0]).toMatchObject({ runId, runRevision: 2,
      contentBasis: { edition_revision: 3, edition_revision_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", content_sha256: data.hash(edited) } }));
    expect(screen.queryByTestId("play-session-copy-agent-notice")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Notes · Hall/ })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Notes · Hall/ }));
    expect(screen.getByLabelText("Scene note")).toHaveValue("Keep this scene note.");
    expect(putWorldPlayRunProgress).toHaveBeenCalledTimes(1);
  });
  it("fences late World A→B→A content and failures even when the Run ID repeats", async () => {
    const old = deferred<PlayRunContent>();
    vi.mocked(getWorldPlayRunContent).mockReturnValueOnce(old.promise);
    const view = render(<PlaySurfacePage />);
    await waitFor(() => expect(getWorldPlayRunContent).toHaveBeenCalledOnce());
    await act(async () => { selectedWorldHarness.worldId = "world-c"; window.history.pushState({}, "", `/play?world=world-c&run=${runId}`); window.dispatchEvent(new PopStateEvent("popstate")); view.rerender(<PlaySurfacePage />); });
    await screen.findByText("Session prose.");
    await act(async () => { selectedWorldHarness.worldId = "world-b"; window.history.pushState({}, "", `/play?world=world-b&run=${runId}`); window.dispatchEvent(new PopStateEvent("popstate")); view.rerender(<PlaySurfacePage />); });
    await waitFor(() => expect(getWorldPlayRunContent).toHaveBeenCalledTimes(3));
    await screen.findByText("Session prose.");
    await act(async () => old.reject(new LiveApiError("Stale A failure", 404)));
    expect(screen.getByText("Session prose.")).toBeInTheDocument();
    expect(screen.queryByText("Stale A failure")).not.toBeInTheDocument();
  });
});
