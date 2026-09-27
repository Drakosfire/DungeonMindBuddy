import { useEffect, useState } from "react";

import { getPlanView } from "../api/liveApi";
import type { PlanViewProjection } from "../api/types";
import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { PlanSurfaceShell } from "./PlanSurfaceShell";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";

type LoadStatus = "loading" | "ready" | "error";

export function PlanSurfacePage() {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);
  const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      setPlanView(null);
      try {
        const response = await getPlanView(managedWorldId);
        if (!cancelled) {
          if (managedWorldId && (
            response.world_id !== managedWorldId
            || response.campaign_id !== managedWorldId
          )) {
            throw new Error(`Plan context does not match selected World ${managedWorldId}.`);
          }
          setPlanView(response);
          setStatus("ready");
        }
      } catch (loadError) {
        if (!cancelled) {
          setStatus("error");
          setError(loadError instanceof Error ? loadError.message : "Failed to load plan context");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [managedWorldId]);

  if (status === "loading") {
    return (
      <AppChrome activeRoute="plan">
        <main className="app-status">
          <p>Loading plan surface…</p>
        </main>
      </AppChrome>
    );
  }

  if (status === "error" || !planView) {
    return (
      <AppChrome activeRoute="plan">
        <main className="app-status app-error">
          <h1>Plan</h1>
          <p>{error ?? "Unable to load plan context."}</p>
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
      <PlanSurfaceShell planView={planView} onEditorToolsChange={setEditorTools} />
    </AppChrome>
  );
}
