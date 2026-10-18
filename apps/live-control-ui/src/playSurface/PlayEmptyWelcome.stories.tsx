import { useEffect, useState } from "react";

import { App } from "../App";
import type { ManagedWorldGraphProjectionResponse, WorldGraphProjection } from "../api/types";
import appStyles from "../styles.css?inline";
import "../ui/tokens.css";
import "./playSurface.css";

const worldId = "fixture-play-empty-first-use";
const nativeWorldId = "fixture-play-empty-native";

const graphProjection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: {
    worldId: nativeWorldId,
    campaignId: "",
    revisionId: "fixture-empty-world-head",
    headRevisionId: "fixture-empty-world-head",
    isHead: true,
    focus: { kind: "none", sessionId: null },
    admissibility: "gm",
    scopeMode: "world",
  },
  summary: {
    nodeCount: 0,
    relationshipCount: 0,
    attributeCount: 0,
    evidenceCount: 0,
    sourceArtifactCount: 0,
    projectionTruncated: false,
  },
  nodes: [],
  relationships: [],
  attributes: [],
  evidence: [],
  sourceArtifacts: [],
  diagnostics: [],
};

const graphResponse: ManagedWorldGraphProjectionResponse = {
  schema: "dmb_managed_world_graph_projection_v1",
  managedWorldId: worldId,
  nativeWorldId,
  bindingVersion: 1,
  projection: graphProjection,
};

type FixtureRequest = { method: string; path: string; kind: "read" | "query" | "write" };

function installEmptyWorldFixture(): () => void {
  const originalFetch = window.fetch;
  const requests: FixtureRequest[] = [];
  const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

  window.__dmbPlayEmptyFixtureRequests = requests;
  window.fetch = async (input, init) => {
    const requestUrl = input instanceof Request ? input.url : String(input);
    const url = new URL(requestUrl, window.location.href);
    const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
    const graphProjectionQuery = method === "POST" && url.pathname === "/api/live/world-graph/managed-projection";
    requests.push({ method, path: url.pathname, kind: graphProjectionQuery ? "query" : method === "GET" ? "read" : "write" });

    if (graphProjectionQuery) {
      const bodyText = typeof init?.body === "string" ? init.body : "{}";
      const body = JSON.parse(bodyText) as { managedWorldId?: string };
      if (body.managedWorldId !== worldId) {
        return json({ detail: "Synthetic Play fixture received an unexpected World query." }, 400);
      }
      return json(graphResponse);
    }
    if (method !== "GET") {
      return json({ detail: "Synthetic Play fixture rejects writes." }, 405);
    }

    if (url.pathname === "/api/live/world-containers") {
      return json({
        schema_version: "dmb_world_container_registry_v1",
        records: [{
          schema_version: "dmb_world_container_record_v1",
          world_id: worldId,
          name: "Lantern Hollow",
          source_root_relpath: "",
          created_at: "2026-10-15T00:00:00Z",
        }],
      });
    }
    if (url.pathname === "/api/live/agent/local-session") {
      return json({ status: "active", csrf_token: "fixture-only" });
    }
    if (url.pathname === `/api/live/agent/worlds/${worldId}/conversation`) {
      return json({
        schema: "dmb_agent_conversation_history_v1",
        world_id: worldId,
        conversation_state: "absent",
        conversation_id: null,
        active_conversation_id: null,
        pointer_revision: 0,
        turns: [],
        next_before_sequence: null,
      });
    }
    if (url.pathname === "/api/live/world-play-runs/v2") {
      return json({ schema_version: "dmb_world_play_runs_list_v2", records: [] });
    }
    if (url.pathname === "/api/live/workspace-documents/world-runbooks") {
      return json({
        schema_version: "dmb_world_owned_runbooks_list_v2",
        scope_mode: "world",
        world_id: worldId,
        records: [],
      });
    }
    return json({ detail: `Synthetic Play fixture has no response for ${url.pathname}.` }, 404);
  };

  return () => {
    window.fetch = originalFetch;
    delete window.__dmbPlayEmptyFixtureRequests;
  };
}

declare global {
  interface Window {
    __dmbPlayEmptyFixtureRequests?: FixtureRequest[];
  }
}

/** Full App shell over an isolated World with no Runs or Runbooks. */
export const AppShellFirstRun = () => {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const style = document.createElement("style");
    style.dataset.playEmptyFixture = "true";
    style.textContent = appStyles;
    document.head.append(style);
    const restoreFetch = installEmptyWorldFixture();
    window.history.replaceState({}, "", `/play?world=${worldId}&choose=1`);
    window.dispatchEvent(new PopStateEvent("popstate"));
    setReady(true);
    return () => {
      restoreFetch();
      style.remove();
    };
  }, []);
  return ready ? <App /> : null;
};
