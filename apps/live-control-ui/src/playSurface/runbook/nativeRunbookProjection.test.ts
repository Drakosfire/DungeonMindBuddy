import { describe, expect, it } from "vitest";

import type {
  PlayRunProgress,
  PlayRunRecord,
  PlayRunReferenceElement,
  PlayRunReferenceManifest,
  PlayRunReferenceManifestV2,
  WorkspaceCommittedRevision,
} from "../../api/types";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";
import { indexPlayableStructure } from "../../tiptap/playable/playableStructureIndex";
import {
  admitNativeRunbook,
  displayedSceneAndBeat,
  isNativeRunbookReadyV1,
  isNativeRunbookReadyV2,
  overlayRuntimeOnDeck,
  slicePlayableBodies,
} from "./nativeRunbookProjection";
import {
  deriveAuthoredRelevance,
  deriveV2OpeningBeatId,
  deriveV2OpeningBeatIdFromMarkdown,
} from "./v2RuntimeProjection";

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

function committed(overrides: Partial<WorkspaceCommittedRevision> = {}): WorkspaceCommittedRevision {
  return {
    schema_version: "dmb_workspace_committed_revision_v1",
    document_id: ARTIFACT_ID,
    kind: "runbook",
    campaign_id: "longmont-c2",
    title: "North Gate Runbook",
    status: "active",
    object_revision: 3,
    work_revision_id: "11111111-1111-4111-8111-111111111111",
    revision_n: 3,
    markdown: SIBLING_MARKDOWN,
    content_sha256: CONTENT_SHA,
    has_divergent_working_copy: false,
    target_relpath: "out/workspace/runbooks/north-gate.md",
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
  });
});

describe("admitNativeRunbook", () => {
  it("reaches READY when Run, sealed manifest, and workspace revision/SHA agree", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      committed: committed(),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("expected v1 ready");
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
  });

  it("admits the bound revision_n after a newer object_revision exists", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      committed: committed({ object_revision: 18 }),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("expected v1 ready");
    expect(admitted.snapshot.loaded_revision).toBe(3);
    expect(admitted.run.playable_revision).toBe(3);
  });

  it("fails closed when the committed revision digest differs from the Run binding", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      committed: committed({ content_sha256: OTHER_SHA }),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("must not overlay mismatched Playable bytes");
  });

  it("fails closed when the sealed manifest binding disagrees with the Run", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest({ playable_revision: 99 }),
      committed: committed(),
    });
    expect(admitted.status).toBe("integrity_failure");
  });

  it("fails closed when a sealed v2 manifest is paired with v1 document bytes", () => {
    const v2Manifest: PlayRunReferenceManifestV2 = {
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: RUN_ID,
      playable_artifact_id: ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: CONTENT_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      beats: [
        { beat_id: "beat:hold-the-gate", beat_kind: "spine" },
        { beat_id: "beat:panic-breaks", beat_kind: "optional" },
      ],
      scenes: [{ scene_id: "scene:gate-line", beat_id: "beat:hold-the-gate" }],
      choices: [{
        choice_id: "choice:who-gets-through",
        beat_id: "beat:hold-the-gate",
        scene_id: "scene:gate-line",
      }],
      options: [{
        option_id: "option:cure-line-first",
        choice_id: "choice:who-gets-through",
      }],
      edges: [{
        option_id: "option:cure-line-first",
        effect: "activate",
        target_kind: "beat",
        target_id: "beat:panic-breaks",
      }],
    };
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: v2Manifest,
      committed: committed(),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("mixed v1 bytes / v2 manifest must not reach READY");
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
      committed: committed(),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status !== "integrity_failure") throw new Error("expected integrity failure");
    expect(admitted.reason).toMatch(/manifest/i);
  });

  it("fails closed when workspace kind is not runbook", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      committed: committed({ kind: "plan" }),
    });
    expect(admitted.status).toBe("integrity_failure");
  });

  it("fails closed when the workspace Runbook is discarded", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      committed: committed({ status: "discarded" }),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("discarded Runbook must not reach READY");
    expect(admitted.reason).toMatch(/discarded/i);
  });

  it("admits the bound revision even when a divergent WorkingCopy exists", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      committed: committed({ has_divergent_working_copy: true }),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("existing Run N must still project N");
    expect(admitted.snapshot.loaded_revision).toBe(3);
  });

  it("does not require a Runbook target file to admit the bound revision", () => {
    const admitted = admitNativeRunbook({
      run: runRecord(),
      manifest: manifest(),
      committed: committed({ target_relpath: null }),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("file path is metadata, not byte authority");
    expect(admitted.snapshot.file_exists).toBe(false);
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
      committed: committed(),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("expected v1 ready");
    expect(admitted.displayedSceneId).toBe("scene:gate");
    expect(admitted.displayedBeatId).toBe("beat:inside");
    expect(admitted.currentIsPreview).toBe(false);
    expect(admitted.previewBeatId).toBe("beat:approach");
  });

  it("may preview the first authored Scene when current_scene_id is null without implying a write", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({ progress: progress() }),
      manifest: manifest(),
      committed: committed(),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("expected v1 ready");
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
      committed: committed(),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("expected v1 ready");
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
      committed: committed(),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("expected v1 ready");
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
      committed: committed(),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV1(admitted)) throw new Error("expected v1 ready");
    const displayed = displayedSceneAndBeat(admitted.scenes, admitted.run.progress);
    expect(displayed.currentIsPreview).toBe(true);
    expect(admitted.run.progress.current_scene_id).toBeNull();
  });
});

const V2_MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:one beat_kind=spine -->",
  "## Beat 1",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:a -->",
  "### Scene A",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:x -->",
  "### Decision X",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:x1 activates=beat:two -->",
  "- Option X1",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:x2 suppresses=scene:b -->",
  "- Option X2",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:y -->",
  "### Decision Y",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:y1 suppresses=beat:two -->",
  "- Option Y1",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:two beat_kind=optional -->",
  "## Beat 2",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:b -->",
  "### Scene B",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:three beat_kind=spine -->",
  "## Beat 3",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:c -->",
  "### Scene C",
  "",
].join("\n");

const V2_ORDER_MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:z-opening beat_kind=spine -->",
  "## Opening",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:a-later beat_kind=spine -->",
  "## Later",
  "",
].join("\n");

function v2Manifest(): PlayRunReferenceManifestV2 {
  return {
    schema_version: "dmb_play_run_reference_manifest_v2",
    run_id: RUN_ID,
    playable_artifact_id: ARTIFACT_ID,
    playable_revision: 3,
    playable_content_sha256: CONTENT_SHA,
    sealed_at: "2026-08-17T00:00:00Z",
    beats: [
      { beat_id: "beat:one", beat_kind: "spine" },
      { beat_id: "beat:three", beat_kind: "spine" },
      { beat_id: "beat:two", beat_kind: "optional" },
    ],
    scenes: [
      { scene_id: "scene:a", beat_id: "beat:one" },
      { scene_id: "scene:b", beat_id: "beat:two" },
      { scene_id: "scene:c", beat_id: "beat:three" },
    ],
    choices: [
      { choice_id: "choice:x", beat_id: "beat:one" },
      { choice_id: "choice:y", beat_id: "beat:one" },
    ],
    options: [
      { option_id: "option:x1", choice_id: "choice:x" },
      { option_id: "option:x2", choice_id: "choice:x" },
      { option_id: "option:y1", choice_id: "choice:y" },
    ],
    edges: [
      { option_id: "option:x1", effect: "activate", target_kind: "beat", target_id: "beat:two" },
      { option_id: "option:x2", effect: "suppress", target_kind: "scene", target_id: "scene:b" },
      { option_id: "option:y1", effect: "suppress", target_kind: "beat", target_id: "beat:two" },
    ],
  };
}

describe("admitNativeRunbook v2", () => {
  it("admits a Beat-rooted READY deck against the exact pinned revision", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({
        progress: progress({ current_beat_id: "beat:one" }),
      }),
      manifest: v2Manifest(),
      committed: committed({ markdown: V2_MARKDOWN }),
    });
    expect(admitted.status).toBe("ready");
    if (!isNativeRunbookReadyV2(admitted)) throw new Error("expected v2 ready");
    expect(admitted.beats.map((beat) => beat.id)).toEqual(["beat:one", "beat:two", "beat:three"]);
    expect(admitted.currentBeatId).toBe("beat:one");
    expect(admitted.currentSceneId).toBeNull();
    expect(admitted.openingBeatId).toBe("beat:one");
    expect(admitted.beats[0]?.scenes.map((scene) => scene.id)).toEqual(["scene:a"]);
    expect(admitted.beats[0]?.choices[0]?.options.map((option) => option.id)).toEqual([
      "option:x1",
      "option:x2",
    ]);
    expect(admitted.run.progress).not.toHaveProperty("relevance");
    expect(admitted.relevanceByTargetId["beat:two"]).toBe("default");
  });

  it("refuses READY when v2 progress has not been seeded", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({ progress: progress() }),
      manifest: v2Manifest(),
      committed: committed({ markdown: V2_MARKDOWN }),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("empty v2 progress must not be READY");
    expect(admitted.reason).toMatch(/current_beat_id/);
  });

  it("chooses the opening Beat from document order, not id-sorted manifest arrays", () => {
    const orderManifest: PlayRunReferenceManifestV2 = {
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: RUN_ID,
      playable_artifact_id: ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: CONTENT_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      beats: [
        { beat_id: "beat:a-later", beat_kind: "spine" },
        { beat_id: "beat:z-opening", beat_kind: "spine" },
      ],
      scenes: [],
      choices: [],
      options: [],
      edges: [],
    };
    expect(orderManifest.beats.map((beat) => beat.beat_id)).toEqual([
      "beat:a-later",
      "beat:z-opening",
    ]);
    expect(deriveV2OpeningBeatIdFromMarkdown(V2_ORDER_MARKDOWN)).toBe("beat:z-opening");
    const admitted = admitNativeRunbook({
      run: runRecord({
        progress: progress({ current_beat_id: "beat:z-opening" }),
      }),
      manifest: orderManifest,
      committed: committed({ markdown: V2_ORDER_MARKDOWN }),
    });
    if (!isNativeRunbookReadyV2(admitted)) throw new Error("expected v2 ready");
    expect(admitted.openingBeatId).toBe("beat:z-opening");
    expect(admitted.beats.map((beat) => beat.id)).toEqual(["beat:z-opening", "beat:a-later"]);
  });

  it("fails closed when a current Scene belongs to a different Beat", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({
        progress: progress({
          current_beat_id: "beat:one",
          current_scene_id: "scene:b",
        }),
      }),
      manifest: v2Manifest(),
      committed: committed({ markdown: V2_MARKDOWN }),
    });
    expect(admitted.status).toBe("integrity_failure");
  });

  it("keeps a suppressed Scene addressable and derives activation over suppression", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({
        progress: progress({
          current_beat_id: "beat:two",
          current_scene_id: "scene:b",
          selections: {
            "choice:x": "option:x1",
            "choice:y": "option:y1",
          },
        }),
      }),
      manifest: v2Manifest(),
      committed: committed({ markdown: V2_MARKDOWN }),
    });
    if (!isNativeRunbookReadyV2(admitted)) throw new Error("expected v2 ready");
    expect(admitted.currentBeatId).toBe("beat:two");
    expect(admitted.currentSceneId).toBe("scene:b");
    expect(admitted.relevanceByTargetId["beat:two"]).toBe("emphasized");
    expect(admitted.beats.some((beat) => beat.id === "beat:two")).toBe(true);
    expect(admitted.beats.find((beat) => beat.id === "beat:two")?.scenes[0]?.id).toBe("scene:b");
    expect(JSON.stringify(admitted.run.progress)).not.toMatch(/emphasized|de-emphasized|relevance/);
  });

  it("fails closed on a zero-Beat v2 Playable", () => {
    const emptyManifest: PlayRunReferenceManifestV2 = {
      schema_version: "dmb_play_run_reference_manifest_v2",
      run_id: RUN_ID,
      playable_artifact_id: ARTIFACT_ID,
      playable_revision: 3,
      playable_content_sha256: CONTENT_SHA,
      sealed_at: "2026-08-17T00:00:00Z",
      beats: [],
      scenes: [],
      choices: [],
      options: [],
      edges: [],
    };
    const admitted = admitNativeRunbook({
      run: runRecord({ progress: progress({ current_beat_id: "beat:one" }) }),
      manifest: emptyManifest,
      committed: committed({ markdown: "# No playable Beats\n" }),
    });
    expect(admitted.status).toBe("integrity_failure");
    if (admitted.status === "ready") throw new Error("zero-Beat v2 must never be READY");
  });

  it("fails closed when the sealed v2 manifest does not match the pinned revision", () => {
    const admitted = admitNativeRunbook({
      run: runRecord({
        progress: progress({ current_beat_id: "beat:one" }),
      }),
      manifest: { ...v2Manifest(), playable_revision: 99 },
      committed: committed({ markdown: V2_MARKDOWN }),
    });
    expect(admitted.status).toBe("integrity_failure");
  });
});

describe("deriveAuthoredRelevance", () => {
  it("defaults when nothing is selected and never invents persisted branch state", () => {
    const relevance = deriveAuthoredRelevance(v2Manifest().edges, {}, ["beat:two", "scene:b"]);
    expect(relevance).toEqual({ "beat:two": "default", "scene:b": "default" });
  });

  it("emphasizes an activated target even when another selected Option suppresses it", () => {
    const relevance = deriveAuthoredRelevance(
      v2Manifest().edges,
      { "choice:x": "option:x1", "choice:y": "option:y1" },
      ["beat:two", "scene:b"],
    );
    expect(relevance["beat:two"]).toBe("emphasized");
  });
});

describe("deriveV2OpeningBeatId", () => {
  it("falls back to the first Beat when no spine exists", () => {
    expect(deriveV2OpeningBeatId({
      beatOrder: ["beat:optional-first", "beat:interrupt-second"],
      beats: [
        { beatId: "beat:optional-first", beatKind: "optional", order: 0, sceneOrder: [], choiceOrder: [] },
        { beatId: "beat:interrupt-second", beatKind: "interrupt", order: 1, sceneOrder: [], choiceOrder: [] },
      ],
      scenes: [],
      choices: [],
      options: [],
      elements: [],
    })).toBe("beat:optional-first");
  });
});
