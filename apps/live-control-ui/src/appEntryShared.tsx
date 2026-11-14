import { useEffect, useState, type ReactNode } from "react";
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

export function ManagedWorldGraph({ worldId, worldTitle, stateScopeId }: {
  readonly worldId: string; readonly worldTitle: string; readonly stateScopeId: string;
}) {
  const auth = useHostedAuthStatus();
  const [client, setClient] = useState<ReturnType<typeof createManagedNativeGraphApi> | null>(null);
  useEffect(() => {
    // Own the client within the effect lifetime, including StrictMode's setup /
    // cleanup rehearsal. Never resurrect an invalidated previous client.
    const owned = createManagedNativeGraphApi(worldId);
    const controller = new AbortController();
    // Start the selected World read while the Graph component loads.
    let initialRead: ReturnType<typeof owned.api.readGraph> | undefined =
      owned.api.readGraph(controller.signal);
    // The Graph may mount after the request has already failed.
    void initialRead.catch(() => {});
    setClient({
      ...owned,
      api: {
        ...owned.api,
        readGraph(signal) {
          const started = initialRead;
          initialRead = undefined;
          if (!started) return owned.api.readGraph(signal);
          if (signal?.aborted) controller.abort();
          const cancel = () => controller.abort();
          signal?.addEventListener("abort", cancel, { once: true });
          return started.finally(() => signal?.removeEventListener("abort", cancel));
        },
      },
    });
    return () => {
      controller.abort();
      owned.invalidate();
    };
  }, [worldId]);
  return client
    ? <NativeGraphDemo api={client.api} embedded mode="managed" worldTitle={worldTitle} stateScopeId={stateScopeId} entityOnlyDetails={auth.status === "authenticated"} readOnly={auth.status === "authenticated"} />
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
