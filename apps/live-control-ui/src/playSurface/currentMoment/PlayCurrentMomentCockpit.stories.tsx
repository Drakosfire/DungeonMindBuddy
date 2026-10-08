import { useEffect, useState } from "react";

import { App } from "../../App";
import type {
  PlayRunReferenceManifestV2,
  WorldPlayRunRecordV2,
} from "../../api/types";
import { admitNativeRunbook } from "../runbook/nativeRunbookProjection";
import type { RunbookMutationStatus } from "../runbook/RunbookTableDeck";
import { BREACH_DOGFOOD_RUNBOOK_MARKDOWN } from "./breachDogfoodFixture";
import { PlayCurrentMomentCockpit } from "./PlayCurrentMomentCockpit";
import appStyles from "../../styles.css?inline";
import "../../ui/tokens.css";
import "../playSurface.css";

const run: WorldPlayRunRecordV2 = {
  schema_version: "dmb_world_play_run_record_v2",
  run_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  world_id: "elderwyld",
  playable_artifact_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  playable_revision: 3,
  playable_work_revision_id: "11111111-1111-4111-8111-111111111111",
  playable_content_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  run_revision: 4,
  created_at: "2026-10-08T00:00:00Z",
  updated_at: "2026-10-08T00:00:00Z",
  progress: {
    current_scene_id: "scene:north-gate",
    current_beat_id: "beat:hold-breach",
    resolved_beat_ids: [],
    selections: { "choice:surviving-brood": "option:seal-breach" },
    notes_by_element_id: {
      "scene:north-gate": "Keep the choice open. Ask what the group does before calling for initiative.",
    },
  },
};

const manifest: PlayRunReferenceManifestV2 = {
  schema_version: "dmb_play_run_reference_manifest_v2",
  run_id: run.run_id,
  playable_artifact_id: run.playable_artifact_id,
  playable_revision: run.playable_revision,
  playable_content_sha256: run.playable_content_sha256,
  sealed_at: run.created_at,
  beats: [
    { beat_id: "beat:hold-breach", beat_kind: "spine" },
    { beat_id: "beat:lower-tunnels", beat_kind: "optional" },
  ],
  scenes: [
    { scene_id: "scene:north-gate", beat_id: "beat:hold-breach" },
    { scene_id: "scene:tunnel-pursuit", beat_id: "beat:hold-breach" },
    { scene_id: "scene:lower-cistern", beat_id: "beat:lower-tunnels" },
  ],
  choices: [{
    choice_id: "choice:surviving-brood",
    beat_id: "beat:hold-breach",
    scene_id: "scene:north-gate",
  }],
  options: [
    { option_id: "option:follow-brood", choice_id: "choice:surviving-brood" },
    { option_id: "option:seal-breach", choice_id: "choice:surviving-brood" },
  ],
  edges: [
    {
      option_id: "option:follow-brood",
      effect: "activate",
      target_kind: "scene",
      target_id: "scene:tunnel-pursuit",
    },
    {
      option_id: "option:follow-brood",
      effect: "activate",
      target_kind: "beat",
      target_id: "beat:lower-tunnels",
    },
    {
      option_id: "option:seal-breach",
      effect: "suppress",
      target_kind: "scene",
      target_id: "scene:tunnel-pursuit",
    },
  ],
};

const admitted = admitNativeRunbook({
  run,
  manifest,
  committed: {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: run.world_id,
    document_id: run.playable_artifact_id,
    kind: "runbook",
    campaign_id: null,
    title: "The Last Hands of the Siege",
    status: "active",
    object_revision: run.playable_revision,
    work_revision_id: run.playable_work_revision_id,
    revision_n: run.playable_revision,
    markdown: BREACH_DOGFOOD_RUNBOOK_MARKDOWN,
    content_sha256: run.playable_content_sha256,
    has_divergent_working_copy: false,
    target_relpath: null,
  },
});

if (admitted.status !== "ready" || admitted.grammar !== "v2") {
  throw new Error("Play cockpit visual fixture requires a valid World V2 Runbook.");
}

export const ResponsiveCockpit = () => {
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  return (
    <main style={{ maxWidth: "1440px", marginInline: "auto", padding: "1rem" }}>
      <PlayCurrentMomentCockpit
        deck={admitted}
        mutationStatus={mutationStatus}
        onMutationStatus={setMutationStatus}
        onAuthoritativeRun={() => undefined}
      />
    </main>
  );
};

type PlayShellRequest = { method: string; path: string };

function installAppShellFixtureApi(): () => void {
  const originalFetch = window.fetch.bind(window);
  const requestLog: PlayShellRequest[] = [];
  const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
  const committed = {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: run.world_id,
    document_id: run.playable_artifact_id,
    kind: "runbook",
    campaign_id: null,
    title: "The Last Hands of the Siege",
    status: "active",
    object_revision: run.playable_revision,
    work_revision_id: run.playable_work_revision_id,
    revision_n: run.playable_revision,
    markdown: BREACH_DOGFOOD_RUNBOOK_MARKDOWN,
    content_sha256: run.playable_content_sha256,
    has_divergent_working_copy: false,
    target_relpath: null,
  };

  window.__dmbPlayShellFixtureRequests = requestLog;
  window.fetch = async (input, init) => {
    const requestUrl = input instanceof Request ? input.url : String(input);
    const url = new URL(requestUrl, window.location.href);
    const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
    requestLog.push({ method, path: url.pathname });
    if (
      method === "PUT"
      && url.pathname === "/api/live/world-play-runs/v2/active"
      && url.searchParams.get("world_id") === run.world_id
    ) {
      return json({
        schema_version: "dmb_world_play_active_run_v2",
        world_id: run.world_id,
        run_id: run.run_id,
        selected_at: run.created_at,
      });
    }
    if (method !== "GET") return json({ detail: "Synthetic Play fixture rejects writes." }, 405);

    if (url.pathname === "/api/live/world-containers") {
      return json({
        schema_version: "dmb_world_container_registry_v1",
        records: [{
          schema_version: "dmb_world_container_record_v1",
          world_id: run.world_id,
          name: "Elderwyld",
          source_root_relpath: "",
          created_at: run.created_at,
        }],
      });
    }
    if (url.pathname === `/api/live/world-play-runs/v2/${run.run_id}`) return json(run);
    if (url.pathname === `/api/live/world-play-runs/v2/${run.run_id}/reference-manifest`) {
      return json(manifest);
    }
    if (url.pathname === `/api/live/workspace-documents/${run.playable_artifact_id}/committed-revision/${run.playable_revision}`) {
      return json({ detail: "Synthetic fixture has no legacy Plan revision." }, 404);
    }
    const runbookRevisionPath = `/api/live/workspace-documents/world-runbooks/${run.playable_artifact_id}/committed-revision`;
    if (
      url.pathname === runbookRevisionPath
      || url.pathname === `${runbookRevisionPath}/${run.playable_revision}`
    ) {
      return json(committed);
    }
    return json({ detail: `Synthetic Play fixture has no GET response for ${url.pathname}.` }, 404);
  };

  return () => {
    window.fetch = originalFetch;
    delete window.__dmbPlayShellFixtureRequests;
  };
}

declare global {
  interface Window {
    __dmbPlayShellFixtureRequests?: PlayShellRequest[];
  }
}

/** Full route fixture: real App providers, World verification, Play route, and shared AppChrome. */
export const AppShellResponsiveCockpit = () => {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const style = document.createElement("style");
    style.dataset.playAppShellFixture = "true";
    style.textContent = appStyles;
    document.head.append(style);
    const restoreFetch = installAppShellFixtureApi();
    window.history.replaceState({}, "", `/play?world=${run.world_id}&run=${run.run_id}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
    setReady(true);
    return () => {
      restoreFetch();
      style.remove();
    };
  }, []);
  return ready ? <App /> : null;
};
