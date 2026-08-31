import { describe, expect, it } from "vitest";

import type { PlayRunProgress, PlayRunRecord } from "../../api/types";
import { admitNativeRunbook } from "../runbook/nativeRunbookProjection";
import type {
  NativeRunbookBeatV2,
  NativeRunbookChoiceV2,
  NativeRunbookReadyV2,
} from "../runbook/nativeRunbookProjection";
import { BREACH_DOGFOOD_RUNBOOK_MARKDOWN, breachDogfoodManifestV2 } from "./breachDogfoodFixture";
import {
  choiceBranchRelevance,
  choiceTargetIds,
  humanTitleForTarget,
  operableDecisions,
  optionInChoice,
  planClearSelection,
  planSelectOption,
  selectedOptionForChoice,
} from "./decisionInteractionModel";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ARTIFACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const CONTENT_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

function progress(overrides: Partial<PlayRunProgress> = {}): PlayRunProgress {
  return {
    current_scene_id: "scene:north-gate",
    current_beat_id: "beat:hold-breach",
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

function breachDeck(run: PlayRunRecord = runRecord()): NativeRunbookReadyV2 {
  const admitted = admitNativeRunbook({
    run,
    manifest: breachDogfoodManifestV2(run),
    committed: {
      schema_version: "dmb_workspace_committed_revision_v1",
      document_id: run.playable_artifact_id,
      kind: "runbook",
      campaign_id: "longmont-c2",
      title: "Breach Dogfood Runbook",
      status: "active",
      object_revision: run.playable_revision,
      work_revision_id: "11111111-1111-4111-8111-111111111111",
      revision_n: run.playable_revision,
      markdown: BREACH_DOGFOOD_RUNBOOK_MARKDOWN,
      content_sha256: run.playable_content_sha256,
      has_divergent_working_copy: false,
      target_relpath: null,
    },
  });
  if (admitted.status !== "ready" || admitted.grammar !== "v2") {
    throw new Error(`expected ready v2, got ${admitted.status}`);
  }
  return admitted;
}

function choice(
  overrides: Partial<NativeRunbookChoiceV2> & Pick<NativeRunbookChoiceV2, "id" | "sceneId">,
): NativeRunbookChoiceV2 {
  return {
    kind: "choice",
    title: overrides.title ?? overrides.id,
    bodyText: overrides.bodyText ?? "",
    beatId: overrides.beatId ?? "beat:hold-breach",
    options: overrides.options ?? [],
    ...overrides,
  };
}

function beatWithChoices(choices: NativeRunbookChoiceV2[]): NativeRunbookBeatV2 {
  return {
    kind: "beat",
    id: "beat:hold-breach",
    title: "Hold the Breach",
    bodyText: "",
    beatKind: "spine",
    relevance: "default",
    scenes: [],
    choices,
  };
}

describe("decisionInteractionModel", () => {
  const brood = choice({
    id: "choice:surviving-brood",
    sceneId: "scene:north-gate",
    title: "What do they do with the surviving brood?",
    options: [
      {
        kind: "option",
        id: "option:follow-brood",
        title: "Follow it",
        bodyText: "The party pursues the retreating creatures into the lower tunnels before reinforcements arrive.",
        choiceId: "choice:surviving-brood",
      },
      {
        kind: "option",
        id: "option:seal-breach",
        title: "Seal the breach",
        bodyText: "The immediate breach is contained, but the surviving creatures remain somewhere below.",
        choiceId: "choice:surviving-brood",
      },
    ],
  });
  const beatLevel = choice({
    id: "choice:beat-call",
    sceneId: null,
    title: "Who holds the wall?",
    options: [
      {
        kind: "option",
        id: "option:defenders",
        title: "The defenders",
        bodyText: "",
        choiceId: "choice:beat-call",
      },
    ],
  });
  const otherScene = choice({
    id: "choice:tunnel-fork",
    sceneId: "scene:tunnel-pursuit",
    title: "How do they chase?",
    options: [
      {
        kind: "option",
        id: "option:sprint",
        title: "Sprint",
        bodyText: "",
        choiceId: "choice:tunnel-fork",
      },
    ],
  });
  const holdBeat = beatWithChoices([beatLevel, brood, otherScene]);

  it("projects Beat-level and same-Scene Decisions when a Scene is current", () => {
    expect(operableDecisions(holdBeat, "scene:north-gate").map((entry) => entry.id)).toEqual([
      "choice:beat-call",
      "choice:surviving-brood",
    ]);
  });

  it("does not project a Decision associated with a different Scene", () => {
    expect(operableDecisions(holdBeat, "scene:north-gate").map((entry) => entry.id)).not.toContain(
      "choice:tunnel-fork",
    );
  });

  it("projects only unassociated Beat Decisions when no Scene is current", () => {
    expect(operableDecisions(holdBeat, null).map((entry) => entry.id)).toEqual(["choice:beat-call"]);
  });

  it("looks up the selected Option from Runtime selections", () => {
    const selected = selectedOptionForChoice(brood, { "choice:surviving-brood": "option:follow-brood" });
    expect(selected?.id).toBe("option:follow-brood");
    expect(selectedOptionForChoice(brood, {})).toBeNull();
  });

  it("uses the selected Option bodyText as consequence framing", () => {
    const selected = selectedOptionForChoice(brood, { "choice:surviving-brood": "option:seal-breach" });
    expect(selected?.bodyText).toBe(
      "The immediate breach is contained, but the surviving creatures remain somewhere below.",
    );
  });

  it("derives the Decision target set from every authored Option", () => {
    const deck = breachDeck();
    expect(choiceTargetIds(deck.beats[0]!.choices[0]!, deck.manifest.edges)).toEqual([
      "scene:tunnel-pursuit",
      "beat:lower-tunnels",
    ]);
  });

  it("resolves Follow it to Tunnel Pursuit and Lower Tunnels emphasized", () => {
    const deck = breachDeck(runRecord({
      progress: progress({ selections: { "choice:surviving-brood": "option:follow-brood" } }),
    }));
    expect(choiceBranchRelevance(deck, deck.beats[0]!.choices[0]!)).toEqual([
      { targetId: "scene:tunnel-pursuit", title: "Tunnel Pursuit", relevance: "emphasized" },
      { targetId: "beat:lower-tunnels", title: "Lower Tunnels", relevance: "emphasized" },
    ]);
  });

  it("resolves Seal the breach to Tunnel Pursuit de-emphasized and Lower Tunnels default", () => {
    const deck = breachDeck(runRecord({
      progress: progress({ selections: { "choice:surviving-brood": "option:seal-breach" } }),
    }));
    expect(choiceBranchRelevance(deck, deck.beats[0]!.choices[0]!)).toEqual([
      { targetId: "scene:tunnel-pursuit", title: "Tunnel Pursuit", relevance: "de-emphasized" },
      { targetId: "beat:lower-tunnels", title: "Lower Tunnels", relevance: "default" },
    ]);
  });

  it("uses final derived relevance when activation wins suppression", () => {
    const ready = breachDeck(runRecord({
      progress: progress({ selections: { "choice:surviving-brood": "option:seal-breach" } }),
    }));
    const withActivationWin: NativeRunbookReadyV2 = {
      ...ready,
      relevanceByTargetId: {
        ...ready.relevanceByTargetId,
        "scene:tunnel-pursuit": "emphasized",
      },
    };
    expect(choiceBranchRelevance(withActivationWin, withActivationWin.beats[0]!.choices[0]!)[0]).toEqual({
      targetId: "scene:tunnel-pursuit",
      title: "Tunnel Pursuit",
      relevance: "emphasized",
    });
  });

  it("fails closed on a cross-Choice Option lookup", () => {
    expect(optionInChoice(brood, "option:sprint")).toBeNull();
    expect(planSelectOption({ "choice:keep": "option:keep" }, brood, "option:sprint")).toEqual({
      kind: "invalid",
    });
    expect(selectedOptionForChoice(brood, { "choice:surviving-brood": "option:sprint" })).toBeNull();
  });

  it("plans select/change/clear without dropping unrelated selections", () => {
    const start = { "choice:keep": "option:keep" };
    expect(planSelectOption(start, brood, "option:follow-brood")).toEqual({
      kind: "write",
      selections: { "choice:keep": "option:keep", "choice:surviving-brood": "option:follow-brood" },
    });
    expect(planSelectOption(
      { ...start, "choice:surviving-brood": "option:follow-brood" },
      brood,
      "option:follow-brood",
    )).toEqual({ kind: "noop" });
    expect(planSelectOption(
      { ...start, "choice:surviving-brood": "option:follow-brood" },
      brood,
      "option:seal-breach",
    )).toEqual({
      kind: "write",
      selections: { "choice:keep": "option:keep", "choice:surviving-brood": "option:seal-breach" },
    });
    expect(planClearSelection(
      { ...start, "choice:surviving-brood": "option:seal-breach" },
      brood,
    )).toEqual({
      kind: "write",
      selections: { "choice:keep": "option:keep" },
    });
    expect(planClearSelection(start, brood)).toEqual({ kind: "noop" });
  });

  it("maps Beat and Scene target IDs to authored titles", () => {
    const deck = breachDeck();
    expect(humanTitleForTarget(deck, "beat:lower-tunnels")).toBe("Lower Tunnels");
    expect(humanTitleForTarget(deck, "scene:north-gate")).toBe("North Gate");
    expect(humanTitleForTarget(deck, "beat:unknown")).toBe("beat:unknown");
  });
});
