import { useEffect, useState } from "react";
import { listWorldContainers } from "../api/liveApi";
import type { WorldContainerRecord } from "../api/types";

/** Read-only entry point: choosing a World navigates, and never creates a session. */
export function PlayWorldPicker() {
  const [worlds, setWorlds] = useState<WorldContainerRecord[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    void listWorldContainers().then(result => {
      if (!cancelled) { setWorlds(result.records); setStatus("ready"); }
    }).catch(() => { if (!cancelled) setStatus("error"); });
    return () => { cancelled = true; };
  }, [attempt]);
  return <section className="play-world-picker" aria-label="Choose your World">
    <h2>Choose your World</h2>
    <p>See its saved sessions, or open a Plan to start your next game.</p>
    {status === "loading" ? <p role="status">Loading Worlds…</p> : null}
    {status === "error" ? <div role="alert"><p>Worlds could not be loaded.</p><button onClick={() => setAttempt(value => value + 1)}>Retry World list</button></div> : null}
    {status === "ready" && worlds.length === 0 ? <p>No Worlds yet. <a href="/build">Create your World in Build</a>.</p> : null}
    {status === "ready" ? <ul className="play-world-list">{worlds.map(world => <li key={world.world_id}>
      <a href={`/play?world=${encodeURIComponent(world.world_id)}&choose=1`}><strong>{world.name}</strong><span>Open sessions →</span></a>
    </li>)}</ul> : null}
  </section>;
}
