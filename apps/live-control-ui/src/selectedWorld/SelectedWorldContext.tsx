import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { getWorkspaceDocument, listWorldContainers } from "../api/liveApi";
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
  explicit: boolean;
} {
  const url = new URL(locationSnapshot, "http://localhost");
  const explicit = url.searchParams.has("world");
  const worldId = url.searchParams.get("world")?.trim() || null;
  const documentId = ["/plan", "/build", "/ingest"].includes(url.pathname)
    ? url.searchParams.get("documentId")?.trim() || null
    : null;
  return { worldId, documentId, explicit };
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
  const selectionKey = `${selection.explicit ? "explicit" : "inferred"}::${selection.worldId ?? ""}::${selection.documentId ?? ""}`;
  const [retryGeneration, setRetryGeneration] = useState(0);
  const [loaded, setLoaded] = useState<{ key: string; value: SelectedWorldState } | null>(null);
  const retry = useCallback(() => {
    setLoaded(null);
    setRetryGeneration((current) => current + 1);
  }, []);
  const state: SelectedWorldState = !selection.explicit && !selection.documentId
    ? { kind: "legacy" }
    : loaded?.key === selectionKey
      ? loaded.value
      : { kind: "loading", requestedWorldId: selection.worldId };

  // Never retain a previously verified world while a new route is resolving.
  currentVerifiedManagedWorld = state.kind === "managed" ? state : null;

  useEffect(() => () => { currentVerifiedManagedWorld = null; }, []);

  useEffect(() => {
    if (!selection.explicit && !selection.documentId) return;
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
        if (!selection.explicit && document && /^longmont-c[12]$/.test(document.campaign_id)
          && (!document.world_id || document.world_id === "eldyrwild")) {
          if (!cancelled) setLoaded({ key: selectionKey, value: { kind: "legacy" } });
          return;
        }
        const worldResponse = await listWorldContainers();
        if (!cancelled) {
          setLoaded({
            key: selectionKey,
            value: verifyManagedWorldSelection({
              requestedWorldId: selection.worldId,
              document,
              worlds: worldResponse.records,
            }),
          });
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
  }, [selectionKey, retryGeneration]);

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
