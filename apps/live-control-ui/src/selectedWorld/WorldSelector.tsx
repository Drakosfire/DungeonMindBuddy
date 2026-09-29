import { useCallback, useState } from "react";

import { createWorldContainer, listWorldContainers } from "../api/liveApi";
import type { WorldContainerRecord } from "../api/types";
import { useRetrySelectedWorld, useSelectedWorld } from "./SelectedWorldContext";
import { selectWorldFromLocation, worldScopedSurfaceHref } from "./worldSelectionNavigation";

export function WorldSelector() {
  const selected = useSelectedWorld();
  const retrySelection = useRetrySelectedWorld();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [worlds, setWorlds] = useState<WorldContainerRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newWorldName, setNewWorldName] = useState("");
  const [creatingWorld, setCreatingWorld] = useState(false);

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

  return (
    <div className="app-world-selector" data-testid="world-selector">
      <button type="button" aria-expanded={open} onClick={() => {
        setOpen((current) => !current);
        if (!open) void refresh();
      }}>
        World: {selected.kind === "managed" ? selected.name : selected.kind === "legacy" ? "Choose" : "Unavailable"}
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
            setCreatingWorld(true);
            setError(null);
            void createWorldContainer({ name }).then((world) => {
              setWorlds((current) => [world, ...current.filter((item) => item.world_id !== world.world_id)]);
              setNewWorldName("");
              setOpen(false);
              window.history.pushState({}, "", `/plan?world=${encodeURIComponent(world.world_id)}`);
              window.dispatchEvent(new PopStateEvent("popstate"));
            }).catch((reason) => {
              setError(reason instanceof Error ? reason.message : "World could not be created.");
            }).finally(() => setCreatingWorld(false));
          }}>
            <label>
              New World name
              <input value={newWorldName} onChange={(event) => setNewWorldName(event.target.value)} />
            </label>
            <button type="submit" disabled={!newWorldName.trim() || creatingWorld}>
              {creatingWorld ? "Creating…" : "Create World and Plan"}
            </button>
          </form>
          <a href={worldScopedSurfaceHref("/build", selected.kind === "managed" ? selected.worldId : null)}>
            New World in Build
          </a>
          {selected.kind === "error" ? (
            <button type="button" onClick={retrySelection}>Retry selection</button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
