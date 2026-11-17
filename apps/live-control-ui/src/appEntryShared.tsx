import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { AgentInteractionProvider } from "./agentInteraction/AgentInteractionProvider";
import { useHostedAuthStatus } from "./auth/HostedAuthGate";
import { createManagedNativeGraphApi } from "./nativeGraphDemo/managedNativeGraphApi";
import { SurfaceContextProvider } from "./surfaceInteraction/contextHost";
import { PeekRegionProvider } from "./surfaceInteraction/peekHost";
import { deferredComponent } from "./ui/deferredComponent";

export const NativeGraphDemo = deferredComponent(
  () => import("./nativeGraphDemo/NativeGraphDemo").then(module => ({ default: module.NativeGraphDemo })),
  "Graph",
);

type GraphClient = ReturnType<typeof createManagedNativeGraphApi>["api"];
const WarmWorldGraph = createContext<GraphClient | null>(null);

export function WarmWorldGraphProvider({ worldId, children }: {
  worldId: string | null;
  children: ReactNode;
}) {
  const [current, setCurrent] = useState<{ worldId: string; api: GraphClient } | null>(null);
  useEffect(() => {
    if (!worldId) return;
    const owned = createManagedNativeGraphApi(worldId);
    const lifetime = new AbortController();
    let warmRead: ReturnType<GraphClient["readGraph"]> | undefined;
    let generation = 0;
    const readGraph: GraphClient["readGraph"] = signal => {
      const request = ++generation;
      const reading = owned.api.readGraph(signal
        ? AbortSignal.any([lifetime.signal, signal]) : lifetime.signal);
      void reading.then(graph => {
        if (request === generation && !lifetime.signal.aborted) warmRead = Promise.resolve(graph);
      }, () => {
        if (warmRead === reading) warmRead = undefined;
      });
      return reading;
    };
    const readInitialGraph = () => warmRead ?? (warmRead = readGraph());
    const rememberGraph = (graph: Awaited<ReturnType<GraphClient["readGraph"]>>) => {
      if (lifetime.signal.aborted) return;
      generation += 1;
      warmRead = Promise.resolve(graph);
    };
    readInitialGraph();
    setCurrent({ worldId, api: {
      ...owned.api, readGraph, readInitialGraph,
      async prepare(input) {
        const result = await owned.api.prepare(input);
        if (result.status === "already_exists") rememberGraph(result.graph);
        return result;
      },
      async confirm(operationId) {
        const result = await owned.api.confirm(operationId);
        if (result.status === "committed") rememberGraph(result.graph);
        return result;
      },
      async readOperation(operationId) {
        const result = await owned.api.readOperation(operationId);
        if (result.status === "committed" && result.graph) rememberGraph(result.graph);
        return result;
      },
    } });
    return () => {
      lifetime.abort();
      owned.invalidate();
    };
  }, [worldId]);

  return <WarmWorldGraph.Provider value={current?.worldId === worldId ? current.api : null}>
    {children}
  </WarmWorldGraph.Provider>;
}

export function ManagedWorldGraph({ worldTitle, stateScopeId }: {
  readonly worldTitle: string; readonly stateScopeId: string;
}) {
  const auth = useHostedAuthStatus();
  const api = useContext(WarmWorldGraph);
  return api
    ? <NativeGraphDemo api={api} embedded mode="managed" worldTitle={worldTitle} stateScopeId={stateScopeId} entityOnlyDetails={auth.status === "authenticated"} readOnly={auth.status === "authenticated"} />
    : <main className="app-status" role="status">Loading World graph…</main>;
}

export function IsolatedEntry({ children }: { readonly children: ReactNode }) {
  return (
    <AgentInteractionProvider>
      <SurfaceContextProvider>
        <PeekRegionProvider>
          {children}
        </PeekRegionProvider>
      </SurfaceContextProvider>
    </AgentInteractionProvider>
  );
}
