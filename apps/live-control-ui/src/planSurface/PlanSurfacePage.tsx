import { useCallback, useEffect, useState } from "react";

import { getPlanView } from "../api/liveApi";
import type { PlanViewProjection } from "../api/types";
import { AppChrome, type AppChromeTools } from "../chrome/AppChrome";
import { PlanSurfaceShell } from "./PlanSurfaceShell";

type LoadStatus = "loading" | "ready" | "error";

export function PlanSurfacePage() {
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);

  const refresh = useCallback(async () => {
    const response = await getPlanView();
    setPlanView(response);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      try {
        await refresh();
        if (!cancelled) setStatus("ready");
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
  }, [refresh]);

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
