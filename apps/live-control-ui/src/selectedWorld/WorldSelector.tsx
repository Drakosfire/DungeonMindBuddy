import { useCallback, useEffect, useRef, useState } from "react";

import { createWorldContainer, listWorldContainers } from "../api/liveApi";
import { getAppLocationSnapshot, navigatePrimaryAppHref } from "../chrome/appNavigation";
import type { WorldContainerRecord } from "../api/types";
import { SELECTED_WORLD_LOCATION_CHANGED_EVENT, useRetrySelectedWorld, useSelectedWorld } from "./SelectedWorldContext";
import { selectWorldFromLocation, worldScopedSurfaceHref } from "./worldSelectionNavigation";

export function WorldSelector({ compact = false, creationPath = "/plan" }: { compact?: boolean; creationPath?: string } = {}) {
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

  useEffect(() => {
    mounted.current = true;
    const markNavigation = () => { navigationChanged.current = true; };
    window.addEventListener("popstate", markNavigation);
    window.addEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, markNavigation);
    return () => {
      mounted.current = false;
      window.removeEventListener("popstate", markNavigation);
      window.removeEventListener(SELECTED_WORLD_LOCATION_CHANGED_EVENT, markNavigation);
    };
  }, []);

  const refresh = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const response = await listWorldContainers();
      setWorlds(response.records);
      setStatus("ready");
    } catch (reason) {
      setStatus("error");
      setError(reason instanceof Error ? reason.message : "World list is unavailable.");
    }
  }, []);

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
          {status === "ready" && worlds.length === 0 ? <p>No managed Worlds yet.</p> : null}
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
          <form onSubmit={(event) => {
            event.preventDefault();
            const name = newWorldName.trim();
            if (!name || creatingWorld) return;
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
          </form>
          <a href={worldScopedSurfaceHref("/build", selected.kind === "managed" ? selected.worldId : null)}>
            {selected.kind === "managed" ? "Open this World in Build" : "New World in Build"}
          </a>
          <p className="app-world-selector__hint">
            Creating a World reserves its identity. Initialize its first native graph through the reviewed Build workflow before editing it here.
          </p>
          {selected.kind === "error" ? (
            <button type="button" onClick={retrySelection}>Retry selection</button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
