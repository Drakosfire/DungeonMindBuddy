import { useCallback, useEffect, useRef, useState } from "react";

import { useHostedAuthStatus } from "../auth/HostedAuthGate";

import { createWorldContainer, listWorldContainers } from "../api/liveApi";
import { getAppLocationSnapshot, navigatePrimaryAppHref } from "../chrome/appNavigation";
import type { WorldContainerRecord } from "../api/types";
import { SELECTED_WORLD_LOCATION_CHANGED_EVENT, useRetrySelectedWorld, useSelectedWorld } from "./SelectedWorldContext";
import { selectWorldFromLocation, worldScopedSurfaceHref } from "./worldSelectionNavigation";

export function WorldSelector({ compact = false, creationPath = "/plan" }: { compact?: boolean; creationPath?: string } = {}) {
  const auth = useHostedAuthStatus();
  const canList = auth.status === "local_operator" || auth.status === "authenticated" && auth.subject !== null;
  const selected = useSelectedWorld();
  const retrySelection = useRetrySelectedWorld();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [worlds, setWorlds] = useState<WorldContainerRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newWorldName, setNewWorldName] = useState("");
  const [creatingWorld, setCreatingWorld] = useState(false);
  const [hostedCreationAvailable, setHostedCreationAvailable] = useState(false);
  const navigationChanged = useRef(false);
  const mounted = useRef(false);
  const requestSequence = useRef(0);
  const authIdentity = `${auth.status}:${auth.subject ?? ""}`;
  const authGuard = useRef({ identity: authIdentity, epoch: 0 });
  if (authGuard.current.identity !== authIdentity) {
    authGuard.current = { identity: authIdentity, epoch: authGuard.current.epoch + 1 };
  }
  const canCreate = auth.status === "local_operator" ||
    (auth.status === "authenticated" && hostedCreationAvailable);

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

  useEffect(() => {
    requestSequence.current += 1;
    setCreatingWorld(false);
    setHostedCreationAvailable(false);
    setWorlds([]);
    setNewWorldName("");
    setError(null);
    setOpen(false);
    setStatus("idle");
  }, [authIdentity]);

  const refresh = useCallback(async () => {
    if (!canList) return;
    const sequence = ++requestSequence.current;
    setWorlds([]);
    setHostedCreationAvailable(false);
    setStatus("loading");
    setError(null);
    try {
      const response = await listWorldContainers();
      if (!mounted.current || sequence !== requestSequence.current) return;
      setWorlds(response.records);
      setHostedCreationAvailable(response.creation_available === true);
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
            const startingAuthEpoch = authGuard.current.epoch;
            let requestKey: string | undefined;
            let storageKey: string | undefined;
            if (auth.status === "authenticated" && auth.subject) {
              try {
                storageKey = `buddy:world-create:${encodeURIComponent(auth.subject)}:${encodeURIComponent(name)}`;
                const raw = window.sessionStorage.getItem(storageKey);
                const prior = raw ? JSON.parse(raw) as { name?: unknown; key?: unknown } : null;
                requestKey = prior?.name === name && typeof prior.key === "string" && /^[A-Za-z0-9_-]{16,128}$/.test(prior.key)
                  ? prior.key : crypto.randomUUID().replaceAll("-", "");
                window.sessionStorage.setItem(storageKey, JSON.stringify({ name, key: requestKey }));
              } catch {
                setError("World creation needs session storage for safe retries. Please enable it and try again.");
                return;
              }
            }
            navigationChanged.current = false;
            setCreatingWorld(true);
            setError(null);
            void createWorldContainer(requestKey ? { name, request_key: requestKey } : { name }).then((world) => {
              if (!mounted.current || authGuard.current.epoch !== startingAuthEpoch) return;
              if (storageKey) {
                try {
                  const current = JSON.parse(window.sessionStorage.getItem(storageKey) ?? "null") as { key?: unknown } | null;
                  if (current?.key === requestKey) window.sessionStorage.removeItem(storageKey);
                } catch { /* Completed result is authoritative. */ }
              }
              setNewWorldName("");
              setOpen(false);
              if (!navigationChanged.current && getAppLocationSnapshot() === startingLocation) {
                navigatePrimaryAppHref(worldScopedSurfaceHref(creationPath, world.world_id));
              }
            }).catch((reason) => {
              if (mounted.current && authGuard.current.epoch === startingAuthEpoch) setError(reason instanceof Error ? reason.message : "World could not be created.");
            }).finally(() => { if (mounted.current && authGuard.current.epoch === startingAuthEpoch) setCreatingWorld(false); });
          }}>
            <label>
              New World name
              <input value={newWorldName} maxLength={100} disabled={creatingWorld} onChange={(event) => setNewWorldName(event.target.value)} />
            </label>
            <button type="submit" disabled={!newWorldName.trim() || creatingWorld}>
              {creatingWorld ? "Creating…" : creationPath === "/" ? "Create World" : "Create World and Plan"}
            </button>
            {error && status !== "error" ? <p role="alert">{error}</p> : null}
          </form> : null}
          {canCreate ? <a href={worldScopedSurfaceHref("/build", selected.kind === "managed" ? selected.worldId : null)}>
            {selected.kind === "managed" ? "Open this World in Build" : "New World in Build"}
          </a> : null}
          <p className="app-world-selector__hint">
            {canCreate
              ? "Creating a World reserves its identity. Native graph initialization is not available in this explorer yet; compatible existing Worlds can be explored here. Open this World in Build to manage its content."
              : "Only existing Worlds already owned by your signed-in account and enabled on this deployment are listed. World creation is not available here."}
          </p>
          {selected.kind === "error" ? (
            <button type="button" onClick={retrySelection}>Retry selection</button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
