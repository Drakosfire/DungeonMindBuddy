import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { getExtractionRun, getPlayRun, getWorkspaceDocument, listWorldContainers } from "../api/liveApi";
import type { WorkspaceDocumentRecord, WorldContainerRecord } from "../api/types";

export interface VerifiedManagedWorld {
  kind: "managed";
  worldId: string;
  name: string;
  documentId: string | null;
}

export type SelectedWorldState =
  | { kind: "legacy" }
  | { kind: "loading"; requestedWorldId: string | null }
  | { kind: "error"; message: string }
  | VerifiedManagedWorld;

const SelectedWorldContext = createContext<SelectedWorldState>({ kind: "legacy" });
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
  const explicit = url.searchParams.has("world");
  const worldId = url.searchParams.get("world")?.trim() || null;
  const documentId = ["/plan", "/build", "/ingest"].includes(url.pathname)
    ? url.searchParams.get("documentId")?.trim() || null
    : null;
  const runId = !explicit && url.pathname === "/play"
    ? url.searchParams.get("run")?.trim() || null
    : null;
  const extractionRunId = !explicit && !documentId && url.pathname === "/ingest"
    ? url.searchParams.get("extractionRunId")?.trim() || null
    : null;
  return { worldId, documentId, runId, extractionRunId, explicit };
}

export function verifyManagedWorldSelection(input: {
  requestedWorldId: string | null;
  document: WorkspaceDocumentRecord | null;
  worlds: readonly WorldContainerRecord[];
}): SelectedWorldState {
  const documentWorldId = input.document?.world_id?.trim()
    || (input.worlds.some((world) => world.world_id === input.document?.campaign_id)
      ? input.document?.campaign_id : null);
  const selectedId = input.requestedWorldId ?? documentWorldId;
  if (!selectedId) return { kind: "legacy" };
  const world = input.worlds.find((candidate) => candidate.world_id === selectedId);
  if (!world) return { kind: "error", message: `Unknown managed World: ${selectedId}` };
  if (input.document && (
    documentWorldId !== selectedId
    || input.document.campaign_id !== selectedId
  )) {
    return { kind: "error", message: `Document ${input.document.document_id} does not belong to World ${selectedId}.` };
  }
  return {
    kind: "managed",
    worldId: world.world_id,
    name: world.name,
    documentId: input.document?.document_id ?? null,
  };
}

export function SelectedWorldProvider({
  locationSnapshot,
  children,
}: {
  locationSnapshot: string;
  children: ReactNode;
}) {
  const selection = requestedWorldSelection(locationSnapshot);
  const selectionKey = `${selection.explicit ? "explicit" : "inferred"}::${selection.worldId ?? ""}::${selection.documentId ?? ""}::${selection.runId ?? ""}::${selection.extractionRunId ?? ""}`;
  const [retryGeneration, setRetryGeneration] = useState(0);
  const [loaded, setLoaded] = useState<{ key: string; value: SelectedWorldState } | null>(null);
  const retry = useCallback(() => {
    setLoaded(null);
    setRetryGeneration((current) => current + 1);
  }, []);
  const state: SelectedWorldState = !selection.explicit && !selection.documentId && !selection.runId && !selection.extractionRunId
    ? { kind: "legacy" }
    : loaded?.key === selectionKey
      ? loaded.value
      : { kind: "loading", requestedWorldId: selection.worldId };

  // Never retain a previously verified world while a new route is resolving.
  currentVerifiedManagedWorld = state.kind === "managed" ? state : null;

  useEffect(() => () => { currentVerifiedManagedWorld = null; }, []);

  useEffect(() => {
    if (!selection.explicit && !selection.documentId && !selection.runId && !selection.extractionRunId) return;
    let cancelled = false;
    void (async () => {
      try {
        if (selection.explicit && !selection.worldId) {
          setLoaded({ key: selectionKey, value: { kind: "error", message: "World selection is empty." } });
          return;
        }
        const document = selection.documentId
          ? await getWorkspaceDocument(selection.documentId)
          : null;
        // An exact Play link can arrive without a World query. Resolve the
        // server-owned Run before mounting Play, so its campaign cannot be
        // hydrated under the legacy C1/C2 shell by default.
        const run = selection.runId ? await getPlayRun(selection.runId) : null;
        const extractionRun = selection.extractionRunId
          ? await getExtractionRun(selection.extractionRunId)
          : null;
        const extractionCampaignId = extractionRun?.campaign_id?.trim() || null;
        if (extractionRun && !extractionCampaignId) {
          throw new Error(`Extraction Run ${selection.extractionRunId} has no campaign binding.`);
        }
        if (!selection.explicit && document && /^longmont-c[12]$/.test(document.campaign_id)
          && (!document.world_id || document.world_id === "eldyrwild")) {
          if (!cancelled) setLoaded({ key: selectionKey, value: { kind: "legacy" } });
          return;
        }
        if (!selection.explicit && run && /^longmont-c[12]$/.test(run.campaign_id)) {
          if (!cancelled) setLoaded({ key: selectionKey, value: { kind: "legacy" } });
          return;
        }
        if (!selection.explicit && extractionCampaignId && /^longmont-c[12]$/.test(extractionCampaignId)) {
          if (!cancelled) setLoaded({ key: selectionKey, value: { kind: "legacy" } });
          return;
        }
        const worldResponse = await listWorldContainers();
        if (!cancelled) {
          const verified = verifyManagedWorldSelection({
            requestedWorldId: selection.worldId ?? run?.campaign_id ?? extractionCampaignId,
            document,
            worlds: worldResponse.records,
          });
          setLoaded({
            key: selectionKey,
            value: verified,
          });
          if (verified.kind === "managed" && (selection.runId || selection.extractionRunId)
            && `${window.location.pathname}${window.location.search}${window.location.hash}` === locationSnapshot) {
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
        if (!cancelled) {
          setLoaded({
            key: selectionKey,
            value: {
              kind: "error",
              message: error instanceof Error ? error.message : "World selection could not be verified.",
            },
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [selectionKey, retryGeneration, locationSnapshot]);

  return (
    <SelectedWorldRetryContext.Provider value={retry}>
      <SelectedWorldContext.Provider value={state}>{children}</SelectedWorldContext.Provider>
    </SelectedWorldRetryContext.Provider>
  );
}

export function useSelectedWorld(): SelectedWorldState {
  return useContext(SelectedWorldContext);
}

export function useRetrySelectedWorld(): () => void {
  return useContext(SelectedWorldRetryContext);
}
