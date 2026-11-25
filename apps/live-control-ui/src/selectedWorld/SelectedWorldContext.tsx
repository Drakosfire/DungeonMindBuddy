import { clearGuestBuildSession, openGuestBuildWorld } from "../guestWorld/guestBuildSession";
import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { getExtractionRun, getHostedWorldContainer, getPlayRun, getWorldOwnedPlanSnapshot, getWorkspaceDocumentAny, listWorldContainers } from "../api/liveApi";
import { useHostedAuthStatus } from "../auth/HostedAuthGate";
import { normalizeAppPathname } from "../chrome/appNavigation";
import type { WorkspaceDocumentRecord, WorldContainerRecord, WorldOwnedPlanRecordV2 } from "../api/types";

type WorkspaceDocumentRecordAny = WorkspaceDocumentRecord | WorldOwnedPlanRecordV2;

export interface VerifiedManagedWorld {
  kind: "managed";
  worldId: string;
  name: string;
  documentId: string | null;
  graphStatus?: NonNullable<WorldContainerRecord["native_graph_binding"]>["status"];
}

export type SelectedWorldState =
  | { kind: "legacy" }
  | { kind: "loading"; requestedWorldId: string | null }
  | { kind: "error"; message: string }
  | VerifiedManagedWorld;

const SelectedWorldContext = createContext<SelectedWorldState>({ kind: "legacy" });
// Route/work admission is separate from the lifetime of an already verified World.
const SelectedWorldAdmissionContext = createContext<SelectedWorldState>({ kind: "legacy" });
const SelectedWorldRetryContext = createContext<() => void>(() => undefined);
export const SELECTED_WORLD_LOCATION_CHANGED_EVENT = "dmb:selected-world-location-changed";

export function announceSelectedWorldLocationChange(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SELECTED_WORLD_LOCATION_CHANGED_EVENT));
  }
}

/** This is a volatile read-through for existing pure Build admission helpers, not authority. */
let currentVerifiedManagedWorld: VerifiedManagedWorld | null = null;

export function getVerifiedManagedWorld(): VerifiedManagedWorld | null {
  return currentVerifiedManagedWorld;
}

export function requestedWorldSelection(locationSnapshot: string): {
  worldId: string | null;
  documentId: string | null;
  runId: string | null;
  extractionRunId: string | null;
  explicit: boolean;
} {
  const url = new URL(locationSnapshot, "http://localhost");
  const pathname = normalizeAppPathname(url.pathname);
  const explicit = url.searchParams.has("world");
  const worldId = url.searchParams.get("world")?.trim() || null;
  const documentId = ["/plan", "/build", "/ingest"].includes(pathname)
    ? url.searchParams.get("documentId")?.trim() || null
    : null;
  const runId = !explicit && pathname === "/play"
    ? url.searchParams.get("run")?.trim() || null
    : null;
  const extractionRunId = !explicit && !documentId && pathname === "/ingest"
    ? url.searchParams.get("extractionRunId")?.trim() || null
    : null;
  return { worldId, documentId, runId, extractionRunId, explicit };
}

function selectionIdentity(selection: ReturnType<typeof requestedWorldSelection>): string {
  return JSON.stringify([selection.explicit, selection.worldId, selection.documentId,
    selection.runId, selection.extractionRunId]);
}

export function verifyManagedWorldSelection(input: {
  requestedWorldId: string | null;
  document: WorkspaceDocumentRecordAny | null;
  worlds: readonly WorldContainerRecord[];
}): SelectedWorldState {
  const worldOwnedPlan = input.document?.schema_version === "dmb_world_owned_plan_record_v2";
  const page = input.document?.kind === "worldbuilding_source";
  const documentWorldId = input.document?.world_id?.trim()
    || (!worldOwnedPlan && !page && input.worlds.some((world) => world.world_id === input.document?.campaign_id)
      ? input.document?.campaign_id : null);
  const selectedId = input.requestedWorldId ?? documentWorldId;
  if (!selectedId) return { kind: "legacy" };
  const world = input.worlds.find((candidate) => candidate.world_id === selectedId);
  if (!world) return { kind: "error", message: `Unknown managed World: ${selectedId}` };
  if (input.document && (documentWorldId !== selectedId || (worldOwnedPlan
    ? input.document.kind !== "plan" || input.document.campaign_id !== null
    : !page && input.document.campaign_id !== selectedId))) {
    return { kind: "error", message: `Document ${input.document.document_id} does not belong to World ${selectedId}.` };
  }
  return {
    kind: "managed",
    worldId: world.world_id,
    name: world.name,
    documentId: input.document?.document_id ?? null,
    ...(world.native_graph_binding ? { graphStatus: world.native_graph_binding.status } : {}),
  };
}

export function SelectedWorldProvider({
  locationSnapshot,
  children,
}: {
  locationSnapshot: string;
  children: ReactNode;
}) {
  const auth = useHostedAuthStatus();
  const hosted = auth.status === "authenticated";
  const selection = requestedWorldSelection(locationSnapshot);
  const selectionKey = selectionIdentity(selection);
  const pathname = normalizeAppPathname(new URL(locationSnapshot, "http://localhost").pathname);
  const isHome = pathname === "/";
  const hostedPlanDocument = hosted && pathname === "/plan" && selection.documentId !== null;
  const [retryGeneration, setRetryGeneration] = useState(0);
  // Each selector transition owns fresh page admission, including A→B→A.
  const selectionScope = useMemo(() => ({ key: selectionKey }), [selectionKey, retryGeneration, isHome, hostedPlanDocument]);
  const [loaded, setLoaded] = useState<{ scope: typeof selectionScope; value: SelectedWorldState } | null>(null);
  const retry = useCallback(() => {
    setLoaded(null);
    setRetryGeneration((current) => current + 1);
  }, []);
  const continuedWorldOnly = selection.explicit && Boolean(selection.worldId)
    && !selection.documentId && !selection.runId && !selection.extractionRunId
    && loaded?.value.kind === "managed" && loaded.value.worldId === selection.worldId
    && (!isHome || loaded.scope === selectionScope);
  const admission = useMemo<SelectedWorldState>(() => continuedWorldOnly && loaded?.value.kind === "managed"
    ? { ...loaded.value, documentId: null }
    : !selection.explicit && !selection.documentId && !selection.runId && !selection.extractionRunId
    ? { kind: "legacy" }
    : loaded?.scope === selectionScope
      ? loaded.value
      : { kind: "loading", requestedWorldId: selection.worldId },
    [continuedWorldOnly, loaded, selectionScope]);
  const state = useMemo<SelectedWorldState>(() => admission.kind === "loading"
    && selection.explicit && selection.worldId && loaded?.value.kind === "managed"
    && loaded.value.worldId === selection.worldId
    ? { ...loaded.value, documentId: null }
    : admission, [admission, loaded, selection.explicit, selection.worldId]);

  useLayoutEffect(() => {
    if (loaded?.value.kind === "managed" && loaded.scope !== selectionScope
      && (!selection.explicit || selection.worldId !== loaded.value.worldId)) {
      // A committed World boundary ends eligibility of the previous receipt.
      // It cannot be reused if navigation returns before the new read settles.
      setLoaded(null);
    }
  }, [loaded, selectionScope, selection.explicit, selection.worldId]);

  // Retained World identity conveys no admission for incoming document selectors.
  currentVerifiedManagedWorld = state.kind === "managed" ? state : null;

  useEffect(() => () => { currentVerifiedManagedWorld = null; }, []);

  useEffect(() => {
    if (continuedWorldOnly && loaded?.value.kind === "managed") {
      if (loaded.scope !== selectionScope || loaded.value.documentId !== null) {
        setLoaded({ scope: selectionScope, value: { ...loaded.value, documentId: null } });
      }
      return;
    }
    if (!selection.explicit && !selection.documentId && !selection.runId && !selection.extractionRunId) return;
    const catalogRequest = new AbortController();
    let cancelled = false;
    void (async () => {
      try {
        if (selection.explicit && !selection.worldId) {
          setLoaded({ scope: selectionScope, value: { kind: "error", message: "World selection is empty." } });
          return;
        }
        const readDocument = async (documentId: string): Promise<WorkspaceDocumentRecordAny> => {
          if (!hostedPlanDocument) return getWorkspaceDocumentAny(documentId);
          // The hosted Plan read uses the snapshot route's exact ownership policy.
          const snapshot = await getWorldOwnedPlanSnapshot(documentId);
          const record = snapshot.record;
          if (snapshot.schema_version !== "dmb_workspace_document_snapshot_v2"
            || record?.schema_version !== "dmb_world_owned_plan_record_v2"
            || record.scope_mode !== "world"
            || record.document_id !== documentId) {
            throw new Error("The saved Plan could not be verified.");
          }
          return record;
        };
        const parallelHostedWorldId = hosted && !selection.runId && !selection.extractionRunId
          ? selection.worldId
          : null;
        const [document, resolvedWorld] = parallelHostedWorldId && selection.documentId
          ? await Promise.all([
            readDocument(selection.documentId),
            getHostedWorldContainer(parallelHostedWorldId, catalogRequest.signal),
          ])
          : [selection.documentId ? await readDocument(selection.documentId) : null, null] as const;
        if (cancelled) return;
        const worldOwnedPlan = document?.schema_version === "dmb_world_owned_plan_record_v2";
        // An exact Play link can arrive without a World query. Resolve the
        // server-owned Run before mounting Play, so its campaign cannot be
        // hydrated under the legacy C1/C2 shell by default.
        const run = selection.runId ? await getPlayRun(selection.runId) : null;
        if (cancelled) return;
        const extractionRun = selection.extractionRunId
          ? await getExtractionRun(selection.extractionRunId)
          : null;
        if (cancelled) return;
        const extractionCampaignId = extractionRun?.campaign_id?.trim() || null;
        if (extractionRun && !extractionCampaignId) {
          throw new Error(`Extraction Run ${selection.extractionRunId} has no campaign binding.`);
        }
        if (!selection.explicit && document && document.kind !== "worldbuilding_source" && !worldOwnedPlan && document.campaign_id !== null && /^longmont-c[12]$/.test(document.campaign_id)
          && (!document.world_id || document.world_id === "eldyrwild")) {
          if (!cancelled) setLoaded({ scope: selectionScope, value: { kind: "legacy" } });
          return;
        }
        if (!selection.explicit && run && /^longmont-c[12]$/.test(run.campaign_id)) {
          if (!cancelled) setLoaded({ scope: selectionScope, value: { kind: "legacy" } });
          return;
        }
        if (!selection.explicit && extractionCampaignId && /^longmont-c[12]$/.test(extractionCampaignId)) {
          if (!cancelled) setLoaded({ scope: selectionScope, value: { kind: "legacy" } });
          return;
        }
        const worlds = resolvedWorld ? [resolvedWorld]
          : hosted && selection.worldId
            ? [await getHostedWorldContainer(selection.worldId, catalogRequest.signal)]
            : (await listWorldContainers(catalogRequest.signal)).records;
        if (!cancelled) {
          const verified = verifyManagedWorldSelection({
            requestedWorldId: selection.worldId ?? run?.campaign_id ?? extractionCampaignId,
            document,
            worlds,
          });
          setLoaded({
            scope: selectionScope,
            value: verified,
          });
          if (verified.kind === "managed" && (selection.runId || selection.extractionRunId)
            && selectionIdentity(requestedWorldSelection(window.location.href)) === selectionKey) {
            // Run-only deep links need a stable World query before a chooser
            // transition removes the Run ID. Replace, never create a second
            // history entry for the same exact object.
            const canonical = new URL(window.location.href);
            canonical.searchParams.set("world", verified.worldId);
            window.history.replaceState({}, "", `${canonical.pathname}${canonical.search}${canonical.hash}`);
            announceSelectedWorldLocationChange();
          }
        }
      } catch (error) {
        catalogRequest.abort();
        if (!cancelled) {
          setLoaded({
            scope: selectionScope,
            value: {
              kind: "error",
              message: error instanceof Error ? error.message : "World selection could not be verified.",
            },
          });
        }
      }
    })();
    return () => { cancelled = true; catalogRequest.abort(); };
  }, [selectionScope, continuedWorldOnly, hosted, hostedPlanDocument]);

  return (
    <SelectedWorldRetryContext.Provider value={retry}>
      <SelectedWorldContext.Provider value={state}>
        <SelectedWorldAdmissionContext.Provider value={admission}>{children}</SelectedWorldAdmissionContext.Provider>
      </SelectedWorldContext.Provider>
    </SelectedWorldRetryContext.Provider>
  );
}

export function useSelectedWorld(): SelectedWorldState {
  return useContext(SelectedWorldContext);
}

/** Incoming page/selector admission. Persistent World owners must not be keyed by this status. */
export function useSelectedWorldAdmission(): SelectedWorldState {
  return useContext(SelectedWorldAdmissionContext);
}

export function useRetrySelectedWorld(): () => void {
  return useContext(SelectedWorldRetryContext);
}

/** Resolve guest Build through the same session that owns the Graph copy. */
export function GuestBuildWorldProvider({ locationSnapshot, children }: { locationSnapshot: string; children: ReactNode }) {
  const [state, setState] = useState<SelectedWorldState>({ kind: "loading", requestedWorldId: null });
  const [retryGeneration, setRetryGeneration] = useState(0);
  const guestWorldRef = useRef<string | null>(null);
  const retry = useCallback(() => setRetryGeneration(value => value + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading", requestedWorldId: null });
    void (async () => {
      try {
        const world = await openGuestBuildWorld(controller.signal);
        guestWorldRef.current = world.worldId;
        const selection = requestedWorldSelection(locationSnapshot);
        if (selection.explicit && selection.worldId !== world.worldId) throw new Error("This document belongs to another World.");
        if (selection.documentId) {
          const document = await getWorkspaceDocumentAny(selection.documentId);
          const pathname = new URL(locationSnapshot, "http://localhost").pathname;
          const expectedKind = pathname === "/plan" ? "plan" : "worldbuilding_source";
          if (document.kind !== expectedKind || document.world_id !== world.worldId) {
            throw new Error("This document belongs to another World.");
          }
        }
        if (!controller.signal.aborted) setState({ kind: "managed", worldId: world.worldId,
          name: world.name, documentId: selection.documentId, graphStatus: "active" });
      } catch (error) {
        if (!controller.signal.aborted) setState({ kind: "error", message: error instanceof Error ? error.message : "Guest World unavailable." });
      }
    })();
    return () => { controller.abort(); };
  }, [locationSnapshot, retryGeneration]);
  useEffect(() => () => {
    currentVerifiedManagedWorld = null;
    clearGuestBuildSession();
    // A sign-in transition can unmount this provider without leaving Build.
    // Do not carry a guest document selector into the signed-in World picker.
    const url = new URL(window.location.href);
    if ((url.pathname === "/build" || url.pathname === "/plan") && guestWorldRef.current &&
        (url.searchParams.get("world") === guestWorldRef.current || url.searchParams.get("campaign") === guestWorldRef.current)) {
      url.searchParams.delete("world");
      url.searchParams.delete("campaign");
      url.searchParams.delete("documentId");
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
      announceSelectedWorldLocationChange();
    }
  }, []);
  currentVerifiedManagedWorld = state.kind === "managed" ? state : null;
  return <SelectedWorldRetryContext.Provider value={retry}>
    <SelectedWorldContext.Provider value={state}>
      <SelectedWorldAdmissionContext.Provider value={state}>{children}</SelectedWorldAdmissionContext.Provider>
    </SelectedWorldContext.Provider>
  </SelectedWorldRetryContext.Provider>;
}
