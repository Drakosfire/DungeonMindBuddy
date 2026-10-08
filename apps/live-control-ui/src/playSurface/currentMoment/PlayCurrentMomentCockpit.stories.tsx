import { useState } from "react";

import type {
  PlayRunReferenceManifestV2,
  WorldPlayRunRecordV2,
} from "../../api/types";
import { admitNativeRunbook } from "../runbook/nativeRunbookProjection";
import type { RunbookMutationStatus } from "../runbook/RunbookTableDeck";
import { BREACH_DOGFOOD_RUNBOOK_MARKDOWN } from "./breachDogfoodFixture";
import { PlayCurrentMomentCockpit } from "./PlayCurrentMomentCockpit";
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
    selections: {},
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
