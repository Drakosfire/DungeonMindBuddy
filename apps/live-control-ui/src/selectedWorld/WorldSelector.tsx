import { useCallback, useEffect, useRef, useState } from "react";

import { useHostedAuthStatus } from "../auth/HostedAuthGate";

import { createWorldContainer, listWorldContainers } from "../api/liveApi";
import { getAppLocationSnapshot, navigatePrimaryAppHref } from "../chrome/appNavigation";
import type { WorldContainerRecord } from "../api/types";
import { SELECTED_WORLD_LOCATION_CHANGED_EVENT, useRetrySelectedWorld, useSelectedWorld } from "./SelectedWorldContext";
import { selectWorldFromLocation, worldScopedSurfaceHref } from "./worldSelectionNavigation";

export function WorldSelector({ compact = false, creationPath = "/plan" }: { compact?: boolean; creationPath?: string } = {}) {
  const auth = useHostedAuthStatus();
  const canCreate = auth.status === "local_operator";
  const canList = canCreate || auth.status === "authenticated" && auth.subject !== null;
  const selected = useSelectedWorld();
  const retrySelection = useRetrySelectedWorld();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [worlds, setWorlds] = useState<WorldContainerRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newWorldName, setNewWorldName] = useState("");
  const [creatingWorld, setCreatingWorld] = useState(false);
  const navigationChanged = useRef(false);
  const mounted = useRef(false);
  const requestSequence = useRef(0);

  useEffect(() => {
    mounted.current = true;
    const markNavigation = () => { navigationChanged.current = true; };
    window.addEventListener("popstate", markNavigation);
    window.addEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, markNavigation);
    return () => {
      mounted.current = false;
      requestSequence.current += 1;
      window.removeEventListener("popstate", markNavigation);
      window.removeEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, markNavigation);
    };
  }, []);

  const refresh = useCallback(async () => {
    if (!canList) return;
    const sequence = ++requestSequence.current;
    setWorlds([]);
    setStatus("loading");
    setError(null);
    try {
      const response = await listWorldContainers();
      if (!mounted.current || sequence !== requestSequence.current) return;
      setWorlds(response.records);
      setStatus("ready");
    } catch (reason) {
      if (!mounted.current || sequence !== requestSequence.current) return;
      setStatus("error");
      setError(reason instanceof Error ? reason.message : "World list is unavailable.");
    }
  }, [canList]);

  if (!canList) return null;

  const worldLabel = selected.kind === "managed" ? selected.name : selected.kind === "legacy" ? "Choose" : "Unavailable";
  return (
    <div className="app-world-selector" data-testid="world-selector">
      <button type="button" aria-expanded={open} aria-label={compact ? `Switch World: ${worldLabel}` : undefined} title={compact ? `Switch World: ${worldLabel}` : undefined} onClick={() => {
        setOpen((current) => !current);
        if (!open) void refresh();
      }}>
        {compact ? <>{worldLabel} <span aria-hidden="true">▾</span></> : `World: ${worldLabel}`}
      </button>
      {open ? (
        <div className="app-world-selector__menu" aria-label="Select World">
          {status === "loading" ? <p role="status">Loading Worlds…</p> : null}
          {status === "error" ? (
            <div role="alert">
              <p>{error}</p>
              <button type="button" onClick={() => void refresh()}>Retry World list</button>
            </div>
          ) : null}
          {status === "ready" && worlds.length === 0 ? <p>{canCreate ? "No managed Worlds yet." : "No existing Worlds owned by this account are available on this deployment."}</p> : null}
          {status === "ready" ? worlds.map((world) => (
            <button
              key={world.world_id}
              type="button"
              aria-current={selected.kind === "managed" && selected.worldId === world.world_id ? "true" : undefined}
              onClick={() => {
                if (selected.kind !== "managed" || selected.worldId !== world.world_id) {
                  selectWorldFromLocation(world.world_id);
                }
                setOpen(false);
              }}
            >
              {world.name}
            </button>
          )) : null}
          {canCreate ? <form onSubmit={(event) => {
            event.preventDefault();
            const name = newWorldName.trim();
            if (!canCreate || !name || creatingWorld) return;
            const startingLocation = getAppLocationSnapshot();
            navigationChanged.current = false;
            setCreatingWorld(true);
            setError(null);
            void createWorldContainer({ name }).then((world) => {
              if (!mounted.current) return;
              setWorlds((current) => [world, ...current.filter((item) => item.world_id !== world.world_id)]);
              setNewWorldName("");
              setOpen(false);
              if (!navigationChanged.current && getAppLocationSnapshot() === startingLocation) {
                navigatePrimaryAppHref(worldScopedSurfaceHref(creationPath, world.world_id));
              }
            }).catch((reason) => {
              if (mounted.current) setError(reason instanceof Error ? reason.message : "World could not be created.");
            }).finally(() => { if (mounted.current) setCreatingWorld(false); });
          }}>
            <label>
              New World name
              <input value={newWorldName} onChange={(event) => setNewWorldName(event.target.value)} />
            </label>
            <button type="submit" disabled={!newWorldName.trim() || creatingWorld}>
              {creatingWorld ? "Creating…" : creationPath === "/" ? "Create World and open graph" : "Create World and Plan"}
            </button>
          </form> : null}
          {canCreate ? <a href={worldScopedSurfaceHref("/build", selected.kind === "managed" ? selected.worldId : null)}>
            {selected.kind === "managed" ? "Open this World in Build" : "New World in Build"}
          </a> : null}
          <p className="app-world-selector__hint">
            {canCreate
              ? "Creating a World reserves its identity. Native graph initialization is not available in this explorer yet; compatible existing Worlds can be explored here. Open this World in Build to manage its content."
              : "Only existing Worlds already owned by your signed-in account and enabled on this deployment are listed. Creating Worlds, assigning ownership, and initializing native graphs are not available here."}
          </p>
          {selected.kind === "error" ? (
            <button type="button" onClick={retrySelection}>Retry selection</button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
