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
  extractSceneListingsFromBody,
  omitHoistedSceneListings,
  overlayRuntimeOnDeck,
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

describe("extractSceneListingsFromBody", () => {
  it("reads the Scenes list from an admitted Beat body without a second Markdown parse", () => {
    const imported = markdownToTiptapDoc([
      "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
      "## Gate",
      "",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->",
      "### Approach",
      "",
      "Scenes",
      "",
      "- Save the townsman",
      "- Pull Baergrom",
      "",
      "World Tick : the hum begins.",
      "",
    ].join("\n"));
    expect(imported.diagnostics).toEqual([]);
    const slices = slicePlayableBodies(imported.doc);
    expect(extractSceneListingsFromBody(slices.get("beat:approach")?.bodyDoc)).toEqual([
      "Save the townsman",
      "Pull Baergrom",
    ]);
  });

  it("returns no listings when the Beat has no Scenes list", () => {
    const imported = markdownToTiptapDoc(SIBLING_MARKDOWN);
    const slices = slicePlayableBodies(imported.doc);
    expect(extractSceneListingsFromBody(slices.get("beat:approach")?.bodyDoc)).toEqual([]);
  });

  it("omits the hoisted Scenes list from the remaining Beat body", () => {
    const imported = markdownToTiptapDoc([
      "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
      "## Gate",
      "",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->",
      "### Approach",
      "",
      "Scenes",
      "",
      "- Save the townsman",
      "- Pull Baergrom",
      "",
      "World Tick : the hum begins.",
      "",
    ].join("\n"));
    const bodyDoc = slicePlayableBodies(imported.doc).get("beat:approach")?.bodyDoc;
    const remaining = omitHoistedSceneListings(bodyDoc);
    expect(extractSceneListingsFromBody(remaining)).toEqual([]);
    expect(JSON.stringify(remaining)).toContain("World Tick");
    expect(JSON.stringify(remaining)).not.toContain("Save the townsman");
  });
});

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

  it("ends a Beat body at an ordinary unmarked root H2 so later instructions stay outside that Beat", () => {
    const markdown = [
      "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
      "## Gate",
      "",
      "Scene intro unique.",
      "",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:breach -->",
      "### Beat: Breach",
      "",
      "Beat-specific prose",
      "",
      "### GM Note",
      "",
      "Keep this unmarked H3 inside the Beat.",
      "",
      "## Open questions",
      "",
      "- Does Tealeaf answer?",
      "- How much wall falls?",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    const slices = slicePlayableBodies(imported.doc);
    expect(slices.get("beat:breach")?.bodyText).toContain("Beat-specific prose");
    expect(slices.get("beat:breach")?.bodyText).toContain("Keep this unmarked H3 inside the Beat.");
    expect(slices.get("beat:breach")?.bodyText).not.toContain("Open questions");
    expect(slices.get("beat:breach")?.bodyText).not.toContain("Does Tealeaf answer");
    expect(slices.has("open-questions")).toBe(false);
    expect([...slices.keys()]).toEqual(["scene:gate", "beat:breach"]);

    const beatDoc = slices.get("beat:breach")?.bodyDoc;
    expect(beatDoc?.type).toBe("doc");
    expect(JSON.stringify(beatDoc)).toContain("Keep this unmarked H3 inside the Beat.");
    expect(JSON.stringify(beatDoc)).not.toContain("Open questions");
    expect(beatDoc?.content?.some((node) => node.type === "heading")).toBe(true);
  });

  it("wraps the admitted importedDoc body nodes without a second parse", () => {
    const imported = markdownToTiptapDoc(SIBLING_MARKDOWN);
    expect(imported.diagnostics).toEqual([]);
    const slices = slicePlayableBodies(imported.doc);
    const importedContent = (imported.doc as { content?: unknown[] }).content ?? [];
    const sceneIntro = importedContent.find((node) => JSON.stringify(node).includes("Scene intro unique"));
    const beatOne = importedContent.find((node) => JSON.stringify(node).includes("Beat one prose UNIQUE"));
    expect(sceneIntro).toBeDefined();
    expect(beatOne).toBeDefined();
    expect(slices.get("scene:gate")?.bodyDoc).not.toBe(imported.doc);
    expect(slices.get("scene:gate")?.bodyDoc.content?.[0]).toBe(sceneIntro);
    expect(slices.get("beat:approach")?.bodyDoc.content?.[0]).toBe(beatOne);
    expect(slices.get("beat:approach")?.bodyText).toBe("Beat one prose UNIQUE.");
  });

  it("keeps semantic callout nodes inside the Beat fragment in authored order", () => {
    const markdown = [
      "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
      "## Gate",
      "",
      "Scene intro unique.",
      "",
      "<!-- dmb-playable-element:v1 kind=beat id=beat:breach -->",
      "### Beat: Breach",
      "",
      "Beat-specific prose",
      "",
      "> [!GM-NOTE]",
      "> Stay behind the palisade.",
      "",
      "Closing sentence.",
      "",
    ].join("\n");
    const imported = markdownToTiptapDoc(markdown);
    expect(imported.diagnostics).toEqual([]);
    const slices = slicePlayableBodies(imported.doc);
    const types = (slices.get("beat:breach")?.bodyDoc.content ?? []).map((node) => node.type);
    expect(types).toEqual(["paragraph", "callout", "paragraph"]);
    expect(slices.get("beat:breach")?.bodyDoc.content?.[1]).toMatchObject({
      type: "callout",
      attrs: expect.objectContaining({ kind: "gm-note" }),
    });
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
    expect(admitted.importedDoc).toEqual(markdownToTiptapDoc(SIBLING_MARKDOWN).doc);
    expect(admitted.scenes[0]?.bodyDoc.type).toBe("doc");
    expect(admitted.scenes[0]?.beats[0]?.bodyDoc.content?.[0]).toEqual(
      slicePlayableBodies(admitted.importedDoc).get("beat:approach")?.bodyDoc.content?.[0],
    );
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
    expect("importedDoc" in admitted).toBe(false);
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

  it("fails closed when the workspace Runbook is discarded", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot({
        record: workspaceRecord({ status: "discarded" }),
      }),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("discarded Runbook must not reach READY");
    expect(admitted.reason).toMatch(/discarded/i);
  });

  it("fails closed when the workspace Runbook is uncommitted", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot({
        record: workspaceRecord({ content_status: "draft" }),
      }),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("uncommitted Runbook must not reach READY");
    expect(admitted.reason).toMatch(/not committed/i);
  });

  it("fails closed when the committed Runbook target file is missing", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot({ file_exists: false }),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("missing-target Runbook must not reach READY");
    expect(admitted.reason).toMatch(/missing/i);
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

describe("overlayRuntimeOnDeck", () => {
  it("overlays Runtime progress when the Playable binding is unchanged", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("ready");
    if (admitted.status !== "ready") throw new Error("expected ready");
    const overlaid = overlayRuntimeOnDeck(
      admitted,
      runRecord({
        run_revision: 9,
        progress: progress({
          current_scene_id: "scene:gate",
          current_beat_id: "beat:inside",
        }),
      }),
    );
    expect(overlaid).not.toBeNull();
    expect(overlaid?.run.run_revision).toBe(9);
    expect(overlaid?.displayedBeatId).toBe("beat:inside");
    expect(overlaid?.scenes[0]?.beats[0]?.bodyText).toBe("Beat one prose UNIQUE.");
  });

  it("refuses to overlay a rebased Run onto the still-admitted scenes", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      snapshot: snapshot(),
    });
    expect(admitted.status).toBe("ready");
    if (admitted.status !== "ready") throw new Error("expected ready");
    const rebased = runRecord({
      playable_revision: 4,
      playable_content_sha256: OTHER_SHA,
      run_revision: 10,
      progress: progress({ current_scene_id: "scene:gate", current_beat_id: "beat:inside" }),
    });
    expect(overlayRuntimeOnDeck(admitted, rebased)).toBeNull();
    expect(admitted.status).toBe("ready");
    expect(admitted.run.playable_revision).toBe(3);
    expect(admitted.scenes[0]?.beats[0]?.bodyText).toBe("Beat one prose UNIQUE.");
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
