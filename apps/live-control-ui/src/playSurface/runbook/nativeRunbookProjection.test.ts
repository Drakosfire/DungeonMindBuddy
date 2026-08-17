import { describe, expect, it } from "vitest";

import type {
  PlayRunProgress,
  PlayRunRecord,
  PlayRunReferenceElement,
  PlayRunReferenceManifest,
  WorkspaceDocumentRecord,
  WorkspaceDocumentSnapshot,
} from "../../api/types";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { indexPlayableStructure } from "../../tiptap/playable/playableStructureIndex";
import {
  admitNativeRunbook,
  displayedSceneAndBeat,
  slicePlayableBodies,
} from "./nativeRunbookProjection";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ARTIFACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const CONTENT_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
const OTHER_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

const SIBLING_MARKDOWN = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
  "## Gate",
  "",
  "Scene intro unique.",
  "",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->",
  "### Approach",
  "",
  "Beat one prose UNIQUE.",
  "",
  "<!-- dmb-playable-element:v1 kind=choice id=choice:enter -->",
  "### Enter?",
  "",
  "Choice prose UNIQUE.",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:yes -->",
  "#### Yes",
  "",
  "Option prose UNIQUE.",
  "",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:inside -->",
  "### Inside",
  "",
  "Beat two prose.",
  "",
].join("\n");

const SIBLING_ELEMENTS: PlayRunReferenceElement[] = [
  { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
  { kind: "beat", element_id: "beat:inside", scene_id: "scene:gate" },
  { kind: "choice", element_id: "choice:enter", scene_id: "scene:gate" },
  { kind: "option", element_id: "option:yes", scene_id: "scene:gate", choice_id: "choice:enter" },
  { kind: "scene", element_id: "scene:gate" },
].sort((left, right) => left.element_id.localeCompare(right.element_id));

function progress(overrides: Partial<PlayRunProgress> = {}): PlayRunProgress {
  return {
    current_scene_id: null,
    current_beat_id: null,
    resolved_beat_ids: [],
    selections: {},
    notes_by_element_id: {},
    ...overrides,
  };
}

function runRecord(overrides: Partial<PlayRunRecord> = {}): PlayRunRecord {
  return {
    schema_version: "dmb_play_run_record_v1",
    run_id: RUN_ID,
    campaign_id: "longmont-c2",
    playable_artifact_id: ARTIFACT_ID,
    playable_revision: 3,
    playable_content_sha256: CONTENT_SHA,
    run_revision: 4,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
    progress: progress(),
    ...overrides,
  };
}

function workspaceRecord(overrides: Partial<WorkspaceDocumentRecord> = {}): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: ARTIFACT_ID,
    title: "North Gate Runbook",
    campaign_id: "longmont-c2",
    target_session: 23,
    kind: "runbook",
    target_relpath: "out/workspace/runbooks/north-gate.md",
    status: "active",
    content_status: "committed",
    revision: 3,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
    ...overrides,
  };
}

function snapshot(overrides: Partial<WorkspaceDocumentSnapshot> = {}): WorkspaceDocumentSnapshot {
  const record = overrides.record ?? workspaceRecord();
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown: SIBLING_MARKDOWN,
    content_sha256: CONTENT_SHA,
    file_fingerprint: "present",
    file_exists: true,
    loaded_revision: record.revision,
    ...overrides,
  };
}

function manifest(overrides: Partial<PlayRunReferenceManifest> = {}): PlayRunReferenceManifest {
  return {
    schema_version: "dmb_play_run_reference_manifest_v1",
    run_id: RUN_ID,
    playable_artifact_id: ARTIFACT_ID,
    playable_revision: 3,
    playable_content_sha256: CONTENT_SHA,
    elements: SIBLING_ELEMENTS,
    sealed_at: "2026-08-17T00:00:00Z",
    ...overrides,
  };
}

describe("slicePlayableBodies", () => {
  it("keeps sibling Beat/Choice/Option bodies disjoint through Scene → Beat → Choice → Option → Beat", () => {
    const imported = markdownToTiptapDoc(SIBLING_MARKDOWN);
    expect(imported.diagnostics).toEqual([]);
    const indexed = indexPlayableStructure(imported.doc);
    expect(indexed.status).toBe("ready");

    const slices = slicePlayableBodies(imported.doc);
    expect(slices.get("scene:gate")?.bodyText).toContain("Scene intro unique");
    expect(slices.get("scene:gate")?.bodyText).not.toContain("Beat one prose UNIQUE");

    expect(slices.get("beat:approach")?.bodyText).toBe("Beat one prose UNIQUE.");
    expect(slices.get("beat:approach")?.bodyText).not.toContain("Choice prose UNIQUE");

    expect(slices.get("choice:enter")?.bodyText).toBe("Choice prose UNIQUE.");
    expect(slices.get("choice:enter")?.bodyText).not.toContain("Beat one prose UNIQUE");
    expect(slices.get("choice:enter")?.bodyText).not.toContain("Option prose UNIQUE");

    expect(slices.get("option:yes")?.bodyText).toBe("Option prose UNIQUE.");
    expect(slices.get("option:yes")?.bodyText).not.toContain("Beat one prose UNIQUE");
    expect(slices.get("option:yes")?.bodyText).not.toContain("Choice prose UNIQUE");

    expect(slices.get("beat:inside")?.bodyText).toBe("Beat two prose.");
    expect(slices.get("beat:inside")?.bodyText).not.toContain("Choice prose UNIQUE");
    expect(slices.get("beat:inside")?.bodyText).not.toContain("Option prose UNIQUE");
  });
});

describe("admitNativeRunbook", () => {
  it("reaches READY when Run, sealed manifest, and workspace revision/SHA agree", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("ready");
    if (admitted.status !== "ready") throw new Error("expected ready");
    expect(admitted.scenes.map((scene) => scene.id)).toEqual(["scene:gate"]);
    expect(admitted.scenes[0]?.beats.map((beat) => beat.id)).toEqual([
      "beat:approach",
      "beat:inside",
    ]);
    expect(admitted.scenes[0]?.choices[0]?.id).toBe("choice:enter");
    expect(admitted.scenes[0]?.choices[0]?.options[0]?.id).toBe("option:yes");
    expect(admitted.currentIsPreview).toBe(true);
    expect(admitted.displayedSceneId).toBe("scene:gate");
    expect(admitted.previewSceneId).toBe("scene:gate");
  });

  it("blocks as rebase_required when the workspace revision is newer than the Run binding", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot({
        record: workspaceRecord({ revision: 4 }),
        loaded_revision: 4,
      }),
    });
    expect(admitted).toMatchObject({
      status: "rebase_required",
      reason: expect.stringMatching(/revision/i),
    });
    expect(admitted.status === "ready" ? admitted.scenes : []).toEqual([]);
  });

  it("blocks as rebase_required when the workspace digest differs from the Run binding", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot({ content_sha256: OTHER_SHA }),
    });
    expect(admitted.status).toBe("rebase_required");
    if (admitted.status === "ready") throw new Error("must not overlay stale Runtime on newer prose");
  });

  it("fails closed when the sealed manifest binding disagrees with the Run", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest({ playable_revision: 99 }),
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("integrity_failure");
  });

  it("fails closed when client P1 structure disagrees with the sealed manifest", () => {
    const extraManifest = manifest({
      elements: [
        ...SIBLING_ELEMENTS,
        { kind: "beat", element_id: "beat:ghost", scene_id: "scene:gate" },
      ].sort((left, right) => left.element_id.localeCompare(right.element_id)),
    });
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: extraManifest,
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status !== "integrity_failure") throw new Error("expected integrity failure");
    expect(admitted.reason).toMatch(/manifest/i);
  });

  it("fails closed when workspace kind is not runbook", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot({
        record: workspaceRecord({ kind: "worldbuilding_source" }),
      }),
    });
    expect(admitted.status).toBe("integrity_failure");
  });

  it("overlays current Scene/Beat from Runtime rather than authored order", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({
        progress: progress({
          current_scene_id: "scene:gate",
          current_beat_id: "beat:inside",
        }),
      }),
      manifest: manifest(),
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("ready");
    if (admitted.status !== "ready") throw new Error("expected ready");
    expect(admitted.displayedSceneId).toBe("scene:gate");
    expect(admitted.displayedBeatId).toBe("beat:inside");
    expect(admitted.currentIsPreview).toBe(false);
    expect(admitted.previewBeatId).toBe("beat:approach");
  });

  it("may preview the first authored Scene when current_scene_id is null without implying a write", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({ progress: progress() }),
      manifest: manifest(),
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("ready");
    if (admitted.status !== "ready") throw new Error("expected ready");
    expect(admitted.run.progress.current_scene_id).toBeNull();
    expect(admitted.run.progress.current_beat_id).toBeNull();
    expect(admitted.currentIsPreview).toBe(true);
    expect(admitted.displayedSceneId).toBe("scene:gate");
    expect(admitted.displayedBeatId).toBe("beat:approach");
  });
});

describe("displayedSceneAndBeat", () => {
  it("does not treat a preview Scene as Runtime current", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("ready");
    if (admitted.status !== "ready") throw new Error("expected ready");
    const displayed = displayedSceneAndBeat(admitted.scenes, admitted.run.progress);
    expect(displayed.currentIsPreview).toBe(true);
    expect(admitted.run.progress.current_scene_id).toBeNull();
  });
});
