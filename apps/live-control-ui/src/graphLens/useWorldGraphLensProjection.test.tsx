import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi, type ReactNode } from "vitest";
import { createElement } from "react";

import * as liveApi from "../api/liveApi";
import type { ManagedWorldGraphProjectionResponse, WorldGraphProjection } from "../api/types";
import { SelectedWorldProvider } from "../selectedWorld/SelectedWorldContext";
import {
  WorldGraphLensProvider,
  WorldGraphLensProjectionProvider as ProjectionProvider,
  useWorldGraphLensProjectionDemand,
  useOptionalWorldGraphLensInformationChannel,
  useWorldGraphLensProjection,
} from "./index";

function Demand({ children }: { children: ReactNode }) {
  useWorldGraphLensProjectionDemand(true);
  return children;
}
function WorldGraphLensProjectionProvider(props: Parameters<typeof ProjectionProvider>[0]) {
  return createElement(ProjectionProvider, props, createElement(Demand, null, props.children));
}

function headProjection(
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
  projectionOverrides: Partial<WorldGraphProjection> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "",
      revisionId: "rev-head",
      headRevisionId: "rev-head",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "world",
      ...snapshotOverrides,
    },
    summary: {
      nodeCount: 0,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes: [],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
    ...projectionOverrides,
  };
}

const worldRecord = (worldId: string) => ({
  schema_version: "dmb_world_container_record_v1" as const, world_id: worldId,
  name: worldId, source_root_relpath: `corpus/${worldId}`, created_at: "2026-01-01T00:00:00Z",
});
function managedProjection(
  snapshot: Partial<WorldGraphProjection["snapshot"]> = {},
  projection: Partial<WorldGraphProjection> = {},
): ManagedWorldGraphProjectionResponse {
  return { schema: "dmb_managed_world_graph_projection_v1", managedWorldId: "managed",
    nativeWorldId: "eldyrwild", bindingVersion: 1, projection: headProjection(snapshot, projection) };
}
let location = "http://localhost/plan?world=managed";
let refreshGeneration = "initial";
function wrapper({ children }: { children: ReactNode }) {
  return createElement(SelectedWorldProvider, { locationSnapshot: location },
    createElement(WorldGraphLensProvider, { planCampaignId: "longmont-c2" },
      createElement(WorldGraphLensProjectionProvider,
        { defaultCampaignId: "longmont-c2", revisionRefreshToken: refreshGeneration }, children)));
}
function withSelection(children: ReactNode) {
  return createElement(SelectedWorldProvider, { locationSnapshot: "http://localhost/plan?world=managed" }, children);
}

describe("WorldGraphLensProjectionProvider", () => {
  afterEach(() => expect(liveApi.postWorldGraphProjection).not.toHaveBeenCalled());
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(liveApi, "postWorldGraphProjection").mockRejectedValue(new Error("Retired projection must not be called"));
    location = "http://localhost/plan?world=managed";
    refreshGeneration = "initial";
    vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[worldRecord("managed"),worldRecord("other-managed")]});
    liveApi.setNativeGraphAccessToken(null);
    window.history.pushState({}, "", "/plan");
    vi.spyOn(liveApi, "getSourceSessions").mockResolvedValue([]);
  });

  it("marks verified managed head responses ready without a raw projection request", async () => {
    const raw = vi.spyOn(liveApi, "postWorldGraphProjection");
    const managed = vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(managedProjection());
    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });
    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.projection?.snapshot.revisionId).toBe("rev-head");
    expect(result.current.projectionError).toBeNull();
    expect(result.current.managedBinding).toEqual({managedWorldId:"managed",nativeWorldId:"eldyrwild",bindingVersion:1});
    expect(managed).toHaveBeenCalledTimes(1);
    expect(raw).not.toHaveBeenCalled();
  });

  it("fails closed when response campaign identity does not match the managed request", async () => {
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(managedProjection({ campaignId: "longmont-c1" }));
    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });
    await waitFor(() => expect(result.current.projectionState).toBe("error"));
    expect(result.current.projection).toBeNull();
    expect(result.current.managedBinding).toBeNull();
    expect(result.current.projectionError).toMatch(/campaign longmont-c1 does not match requested campaign/);
  });

  it.each(["/plan", "/ingest?campaign=longmont-c1&session=session-2", "/plan?campaigns=longmont-c1,longmont-c2"])(
    "refuses legacy projection demand without network IO at %s", async (path) => {
      location = `http://localhost${path}`;
      const raw = vi.spyOn(liveApi, "postWorldGraphProjection");
      const managed = vi.spyOn(liveApi, "postManagedWorldGraphProjection");
      const { result } = renderHook(() => ({projection:useWorldGraphLensProjection(),channel:useOptionalWorldGraphLensInformationChannel()}), { wrapper });
      await waitFor(() => expect(result.current.projection.projectionState).toBe("error"));
      expect(result.current.projection).toMatchObject({projection:null,managedBinding:null,nodeCount:0});
      expect(result.current.channel?.getSnapshot().state.status).toBe("unavailable");
      expect(raw).not.toHaveBeenCalled(); expect(managed).not.toHaveBeenCalled();
    },
  );

  it("ignores recap campaign selectors for a selected managed World", async () => {
    location = "http://localhost/ingest?world=managed&campaign=longmont-c1&session=session-2";
    const managed = vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(managedProjection());
    const raw = vi.spyOn(liveApi, "postWorldGraphProjection");
    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });
    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(managed).toHaveBeenCalledWith({schema:"dmb_managed_world_graph_projection_request_v1",managedWorldId:"managed",queryText:null,revisionPin:null},expect.any(AbortSignal));
    expect(result.current.request).toMatchObject({worldId:"managed",campaignId:"",scopeMode:"world",focus:{kind:"none",sessionId:null}});
    expect(raw).not.toHaveBeenCalled();
  });

  it("clears ready managed bytes and retires its channel when selection becomes legacy", async () => {
    const managed = vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(managedProjection({}, {nodes:[glowkindle]}));
    const raw = vi.spyOn(liveApi, "postWorldGraphProjection");
    const { result, rerender } = renderHook(() => useProjectionAndChannel(), { wrapper });
    await waitFor(() => expect(result.current.projection.projectionState).toBe("ready"));
    const retired = result.current.channel!;
    expect(result.current.projection.nodeCount).toBe(1);
    location = "http://localhost/plan"; rerender();
    expect(result.current.projection).toMatchObject({projection:null,managedBinding:null,nodeCount:0});
    expect(result.current.channel).not.toBe(retired);
    await waitFor(() => expect(result.current.projection.projectionState).toBe("error"));
    expect(result.current.channel?.getSnapshot().state).not.toHaveProperty("value");
    expect(retired.getSnapshot().state).not.toHaveProperty("value");
    expect(managed).toHaveBeenCalledTimes(1); expect(raw).not.toHaveBeenCalled();
  });

  it("requests a managed World without fabricating a campaign", async () => {
    const worldId = "of-conks-j1-fresh-rehearsal";
    window.history.pushState({}, "", `/plan?world=${worldId}`);
    vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [{
        schema_version: "dmb_world_container_record_v1",
        world_id: worldId,
        name: "Of Conks",
        source_root_relpath: "corpus/of-conks",
        created_at: "2026-01-01T00:00:00Z",
      }],
    });
    const spy = vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue({
      schema: "dmb_managed_world_graph_projection_v1",
      managedWorldId: worldId,
      nativeWorldId: "eldyrwild",
      bindingVersion: 1,
      projection: headProjection({ worldId: "eldyrwild", campaignId: "", scopeMode: "world" }),
    });
    const nativeSpy = vi.spyOn(liveApi, "postWorldGraphProjection");
    const managedWrapper = ({ children }: { children: ReactNode }) =>
      createElement(
        SelectedWorldProvider,
        { locationSnapshot: window.location.href },
        createElement(
          WorldGraphLensProvider,
          { planCampaignId: worldId },
          createElement(WorldGraphLensProjectionProvider, { defaultCampaignId: worldId }, children),
        ),
      );

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper: managedWrapper });
    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      schema: "dmb_managed_world_graph_projection_request_v1",
      managedWorldId: worldId,
    }), expect.any(AbortSignal));
    expect(spy).toHaveBeenCalledTimes(1);
    expect(nativeSpy).not.toHaveBeenCalled();
    expect(result.current.projection?.snapshot.worldId).toBe("eldyrwild");
    expect(result.current.projection?.snapshot.campaignId).toBe("");
    expect(result.current.managedBinding).toEqual({managedWorldId:worldId,nativeWorldId:"eldyrwild",bindingVersion:1});
  });

  it("retires the verified binding together with projection bytes during refresh", async () => {
    const worldId="elderwyld";
    window.history.pushState({},"",`/plan?world=${worldId}`);
    vi.spyOn(liveApi,"listWorldContainers").mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:worldId,name:"World",source_root_relpath:"corpus/world",created_at:"2026-01-01T00:00:00Z"}]});
    const packet:ManagedWorldGraphProjectionResponse={schema:"dmb_managed_world_graph_projection_v1",managedWorldId:worldId,nativeWorldId:"eldyrwild",bindingVersion:1,projection:headProjection({worldId:"eldyrwild",campaignId:"",scopeMode:"world"})};
    let finish!:(value:ManagedWorldGraphProjectionResponse)=>void;
    const spy=vi.spyOn(liveApi,"postManagedWorldGraphProjection").mockResolvedValueOnce(packet).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
    let refresh=0;
    const managedWrapper=({children}:{children:ReactNode})=>createElement(SelectedWorldProvider,{locationSnapshot:window.location.href},createElement(WorldGraphLensProvider,{planCampaignId:worldId},createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:worldId,revisionRefreshToken:refresh},children)));
    const {result,rerender}=renderHook(()=>useWorldGraphLensProjection(),{wrapper:managedWrapper});
    await waitFor(()=>expect(result.current.managedBinding?.bindingVersion).toBe(1));
    refresh=1;rerender();
    expect(result.current.projection).toBeNull();expect(result.current.managedBinding).toBeNull();
    await waitFor(()=>expect(spy).toHaveBeenCalledTimes(2));
    act(()=>finish({...packet,bindingVersion:2,projection:headProjection({worldId:"eldyrwild",campaignId:"",scopeMode:"world",revisionId:"rev-new",headRevisionId:"rev-new"})}));
    await waitFor(()=>expect(result.current.managedBinding?.bindingVersion).toBe(2));
    expect(result.current.projection?.snapshot.revisionId).toBe("rev-new");
  });

  it("retries a managed projection after the local Graph credential changes", async () => {
    const worldId = "elderwyld";
    window.history.pushState({}, "", `/plan?world=${worldId}`);
    vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [{
        schema_version: "dmb_world_container_record_v1",
        world_id: worldId,
        name: "Elderwyld",
        source_root_relpath: "corpus/elderwyld",
        created_at: "2026-01-01T00:00:00Z",
      }],
    });
    const successfulResponse: ManagedWorldGraphProjectionResponse = {
      schema: "dmb_managed_world_graph_projection_v1",
      managedWorldId: worldId,
      nativeWorldId: "eldyrwild",
      bindingVersion: 1,
      projection: headProjection({ worldId: "eldyrwild", campaignId: "", scopeMode: "world" }),
    };
    const managedProjectionSpy = vi.spyOn(liveApi, "postManagedWorldGraphProjection")
      .mockRejectedValueOnce(
        new liveApi.LiveApiError("Graph credential required", 401, { code: "graph_auth_required" }),
      )
      .mockResolvedValueOnce(successfulResponse);
    const managedWrapper = ({ children }: { children: ReactNode }) =>
      createElement(
        SelectedWorldProvider,
        { locationSnapshot: window.location.href },
        createElement(
          WorldGraphLensProvider,
          { planCampaignId: worldId },
          createElement(WorldGraphLensProjectionProvider, { defaultCampaignId: worldId }, children),
        ),
      );

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper: managedWrapper });
    await waitFor(() => expect(result.current.projectionState).toBe("error"));
    expect(managedProjectionSpy).toHaveBeenCalledTimes(1);

    act(() => liveApi.setNativeGraphAccessToken("test-local-graph-token"));

    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(managedProjectionSpy).toHaveBeenCalledTimes(2);
    expect(result.current.projection?.snapshot.worldId).toBe("eldyrwild");
  });

  it("rejects a managed projection envelope for a different selected World", async () => {
    const worldId = "elderwyld";
    window.history.pushState({}, "", `/plan?world=${worldId}`);
    vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [{
        schema_version: "dmb_world_container_record_v1",
        world_id: worldId,
        name: "Elderwyld",
        source_root_relpath: "corpus/elderwyld",
        created_at: "2026-01-01T00:00:00Z",
      }],
    });
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue({
      schema: "dmb_managed_world_graph_projection_v1",
      managedWorldId: "other-world",
      nativeWorldId: "eldyrwild",
      bindingVersion: 1,
      projection: headProjection({ worldId: "eldyrwild", campaignId: "", scopeMode: "world" }),
    });
    const managedWrapper = ({ children }: { children: ReactNode }) =>
      createElement(
        SelectedWorldProvider,
        { locationSnapshot: window.location.href },
        createElement(
          WorldGraphLensProvider,
          { planCampaignId: worldId },
          createElement(WorldGraphLensProjectionProvider, { defaultCampaignId: worldId }, children),
        ),
      );

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper: managedWrapper });
    await waitFor(() => expect(result.current.projectionState).toBe("error"));
    expect(result.current.projection).toBeNull();
    expect(result.current.managedBinding).toBeNull();
    expect(result.current.projectionError).toMatch(/does not match selected World elderwyld/);
  });

  it("fails closed when head claim is inconsistent", async () => {
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(
      managedProjection({ isHead: true, revisionId: "rev-a", headRevisionId: "rev-b" }),
    );

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });

    await waitFor(() => expect(result.current.projectionState).toBe("error"));
    expect(result.current.projection).toBeNull();
    expect(result.current.managedBinding).toBeNull();
    expect(result.current.projectionError).toMatch(/head claim is inconsistent/);
  });

  it("exposes exact request identity for consumers", async () => {
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(managedProjection());

    const { result } = renderHook(() => useWorldGraphLensProjection(), { wrapper });

    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.request).toEqual(
      expect.objectContaining({
        worldId: "managed",
        campaignId: "",
        scopeMode: "world",
        admissibility: "gm",
      }),
    );
    expect(result.current.requestKey).toEqual(expect.any(String));
  });

  it("clears ready bytes synchronously when revision refresh generation changes", async () => {
    let resolveSecond!: (value: ManagedWorldGraphProjectionResponse) => void;
    const secondDeferred = new Promise<ManagedWorldGraphProjectionResponse>((resolve) => {
      resolveSecond = resolve;
    });
    vi.spyOn(liveApi, "postManagedWorldGraphProjection")
      .mockResolvedValueOnce(managedProjection({ revisionId: "rev-1", headRevisionId: "rev-1" }))
      .mockReturnValueOnce(secondDeferred);

    let refreshToken = "r0";
    const { result, rerender } = renderHook(() => useWorldGraphLensProjection(), {
      wrapper: ({ children }: { children: ReactNode }) =>
        withSelection(createElement(
          WorldGraphLensProvider,
          { planCampaignId: "longmont-c2" },
          createElement(
            WorldGraphLensProjectionProvider,
            {
              defaultCampaignId: "longmont-c2",
              revisionRefreshToken: refreshToken,
            },
            children,
          ),
        )),
    });

    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.projection?.snapshot.revisionId).toBe("rev-1");
    const requestKey = result.current.requestKey;

    refreshToken = "r1";
    rerender();
    // Same request key, new refresh generation → fail-closed loading with null bytes.
    expect(result.current.requestKey).toBe(requestKey);
    expect(result.current.projectionState).toBe("loading");
    expect(result.current.projection).toBeNull();
    expect(result.current.managedBinding).toBeNull();

    await act(async () => {
      resolveSecond(managedProjection({ revisionId: "rev-2", headRevisionId: "rev-2" }));
    });
    await waitFor(() => expect(result.current.projectionState).toBe("ready"));
    expect(result.current.projection?.snapshot.revisionId).toBe("rev-2");
  });

  const glowkindle = {
    nodeId: "npc:glowkindle",
    label: "Glowkindle",
    kind: "npc",
    role: "merchant",
    aliases: ["Glow"],
    sourceDomains: ["recap"],
    evidenceBadges: [],
    adjacency: [],
    suggestedExpansions: [],
    anchoredToFocusSession: true,
    summary: "A friendly merchant.",
    campaignScope: "longmont-c2",
    evidenceRefIds: [],
    sourceArtifactIds: [],
  };

  function useProjectionAndChannel() {
    return {
      projection: useWorldGraphLensProjection(),
      channel: useOptionalWorldGraphLensInformationChannel(),
    };
  }

  it("publishes one Surface Information channel per exact request and disposes it on replacement", async () => {
    const spy = vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockImplementation(async (request) =>
      ({...managedProjection({
        campaignId: "",
        worldId: "eldyrwild",
        revisionId: "rev-managed",
        headRevisionId: "rev-managed",
      }),managedWorldId:request.managedWorldId}),
    );

    const { result, rerender } = renderHook(() => useProjectionAndChannel(), { wrapper });

    await waitFor(() => expect(result.current.channel).not.toBeNull());
    const first = result.current.channel!;
    expect(first.descriptor.authority).toBe("dungeonmind");
    expect(first.descriptor.providerId).toBe("world_graph_lens_projection");
    expect(first.descriptor.subject).toEqual({ kind: "world", id: "managed" });
    expect(first.descriptor.scope).toEqual(
      expect.arrayContaining([
        { kind: "scope_mode", id: "world" },
        { kind: "admissibility", id: "gm" },
      ]),
    );
    expect(JSON.stringify(first.descriptor)).not.toMatch(/rev-/);
    await waitFor(() => {
      const status = first.getSnapshot().state.status;
      expect(status === "empty" || status === "ready").toBe(true);
    });
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0]?.[0].managedWorldId).toBe("managed");

    const staleTicket = first.beginObservation({ publishLoading: false });
    act(() => {
      location = "http://localhost/plan?world=other-managed";
      rerender();
    });
    await waitFor(() => expect(result.current.channel).not.toBe(first));
    expect(result.current.channel).not.toBeNull();
    expect(result.current.channel!.descriptor.scope).toEqual(
      expect.arrayContaining([{ kind: "scope_mode", id: "world" }]),
    );
    await waitFor(() => {
      const status = result.current.channel?.getSnapshot().state.status;
      expect(status === "empty" || status === "ready").toBe(true);
    });
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[1]?.[0].managedWorldId).toBe("other-managed");
    expect(result.current.channel!.descriptor.subject).toEqual({kind:"world",id:"other-managed"});
    expect(
      first.commit(staleTicket!, {
        status: "ready",
        value: headProjection({}, { nodes: [glowkindle] }),
        revision: { kind: "exact", value: "rev-late" },
        provenance: [],
        inspectionTargets: [],
        diagnostics: [],
      }),
    ).toBe(false);
  });

  it("does not fetch World Graph on a disposed channel during descriptor replacement", async () => {
    let resolveFirst!: (value: ManagedWorldGraphProjectionResponse) => void;
    const firstDeferred = new Promise<ManagedWorldGraphProjectionResponse>((resolve) => {
      resolveFirst = resolve;
    });
    const spy = vi.spyOn(liveApi, "postManagedWorldGraphProjection")
      .mockReturnValueOnce(firstDeferred)
      .mockImplementation(async (request) =>
        ({...managedProjection({
          campaignId: "",
          worldId: "eldyrwild",
          revisionId: "rev-managed",
          headRevisionId: "rev-managed",
        }),managedWorldId:request.managedWorldId}),
      );

    const { result, rerender } = renderHook(() => useProjectionAndChannel(), { wrapper });
    await waitFor(() => expect(result.current.channel).not.toBeNull());
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0]?.[0].managedWorldId).toBe("managed");
    const first = result.current.channel!;

    act(() => {
      location = "http://localhost/plan?world=other-managed";
      rerender();
    });
    await waitFor(() => expect(result.current.channel).not.toBe(first));
    await waitFor(() => {
      const status = result.current.channel?.getSnapshot().state.status;
      expect(status === "empty" || status === "ready").toBe(true);
    });
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[1]?.[0].managedWorldId).toBe("other-managed");
    expect(result.current.channel!.descriptor.subject).toEqual({kind:"world",id:"other-managed"});

    await act(async () => {
      resolveFirst(
        managedProjection({
          campaignId: "",
          revisionId: "rev-late-c2",
          headRevisionId: "rev-late-c2",
        }),
      );
    });
    expect(spy).toHaveBeenCalledTimes(2);
    const live = result.current.channel!.getSnapshot();
    expect(live.state.status === "empty" || live.state.status === "ready").toBe(true);
    if (live.state.status === "empty" || live.state.status === "ready") {
      expect(live.state.revision).toEqual({ kind: "exact", value: "rev-managed" });
    }
  });

  it("rejects a late same-scope response on the Surface Information channel", async () => {
    let resolveA!: (value: ManagedWorldGraphProjectionResponse) => void;
    let resolveB!: (value: ManagedWorldGraphProjectionResponse) => void;
    const deferredA = new Promise<ManagedWorldGraphProjectionResponse>((resolve) => {
      resolveA = resolve;
    });
    const deferredB = new Promise<ManagedWorldGraphProjectionResponse>((resolve) => {
      resolveB = resolve;
    });
    vi.spyOn(liveApi, "postManagedWorldGraphProjection")
      .mockReturnValueOnce(deferredA)
      .mockReturnValueOnce(deferredB);

    let refreshToken = "r0";
    const { result, rerender } = renderHook(() => useProjectionAndChannel(), {
      wrapper: ({ children }: { children: ReactNode }) =>
        withSelection(createElement(
          WorldGraphLensProvider,
          { planCampaignId: "longmont-c2" },
          createElement(
            WorldGraphLensProjectionProvider,
            {
              defaultCampaignId: "longmont-c2",
              revisionRefreshToken: refreshToken,
            },
            children,
          ),
        )),
    });

    await waitFor(() => expect(result.current.channel).not.toBeNull());
    const retired = result.current.channel!;

    refreshToken = "r1";
    rerender();
    const channel = result.current.channel!;
    expect(channel).not.toBe(retired);
    expect(retired.getSnapshot().state.status).toBe("loading");
    const descriptor = channel.descriptor;

    await act(async () => {
      const campaignId = result.current.projection.request?.campaignId ?? "";
      resolveB(
        managedProjection(
          { campaignId, revisionId: "rev-B", headRevisionId: "rev-B" },
          { nodes: [glowkindle] },
        ),
      );
    });
    await waitFor(() => expect(channel.getSnapshot().state.status).toBe("ready"));
    const accepted = channel.getSnapshot();
    if (accepted.state.status === "ready") {
      expect(accepted.state.revision).toEqual({ kind: "exact", value: "rev-B" });
    }

    await act(async () => {
      const campaignId = result.current.projection.request?.campaignId ?? "";
      resolveA(
        managedProjection(
          { campaignId, revisionId: "rev-A", headRevisionId: "rev-A" },
          { nodes: [glowkindle] },
        ),
      );
    });
    expect(result.current.channel).toBe(channel);
    expect(channel.descriptor).toBe(descriptor);
    expect(channel.getSnapshot()).toBe(accepted);
    expect(channel.getSnapshot().generation).toBe(accepted.generation);
  });

  it("treats an equivalent verified refresh as a new observation generation", async () => {
    const payload = managedProjection(
      { revisionId: "rev-same", headRevisionId: "rev-same" },
      { nodes: [glowkindle] },
    );
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(payload);

    let refreshToken = "r0";
    const { result, rerender } = renderHook(() => useProjectionAndChannel(), {
      wrapper: ({ children }: { children: ReactNode }) =>
        withSelection(createElement(
          WorldGraphLensProvider,
          { planCampaignId: "longmont-c2" },
          createElement(
            WorldGraphLensProjectionProvider,
            {
              defaultCampaignId: "longmont-c2",
              revisionRefreshToken: refreshToken,
            },
            children,
          ),
        )),
    });

    await waitFor(() => expect(result.current.channel?.getSnapshot().state.status).toBe("ready"));
    const channel = result.current.channel!;
    const first = channel.getSnapshot();
    refreshToken = "r1";
    rerender();
    await waitFor(() => expect(channel.getSnapshot().generation).toBeGreaterThan(first.generation));
    expect(result.current.channel).not.toBe(channel);
    await waitFor(() => expect(result.current.channel?.getSnapshot().state.status).toBe("ready"));
    expect(channel.getSnapshot().state.status).toBe("loading");
  });

  it("does not introduce a second World Graph request path", async () => {
    const spy = vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(managedProjection());
    const { result, rerender } = renderHook(() => useProjectionAndChannel(), { wrapper });
    await waitFor(() => expect(result.current.projection.projectionState).toBe("ready"));
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
