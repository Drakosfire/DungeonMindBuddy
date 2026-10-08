import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { LiveApiError } from "../../api/liveApi";
import type {
  PlayRunProgress,
  PlayRunRecord,
  PlayRunReferenceManifestV2,
  WorldPlayRunRecordV2,
} from "../../api/types";
import { admitNativeRunbook, overlayRuntimeOnV2Ready } from "../runbook/nativeRunbookProjection";
import type { RunbookMutationStatus } from "../runbook/RunbookTableDeck";
import { PlayCurrentMomentCockpit } from "./PlayCurrentMomentCockpit";
import { BREACH_DOGFOOD_RUNBOOK_MARKDOWN, breachDogfoodManifestV2 } from "./breachDogfoodFixture";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const OTHER_RUN_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const ARTIFACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const CONTENT_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

const MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:survive beat_kind=spine -->",
  "## Survive the Current Breach",
  "",
  "Hold the mire until the wall is sealed.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:tunnel -->",
  "### Tunnel Breach",
  "",
  "Tunnel unique body.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->",
  "### North Gate",
  "",
  "North Gate unique body.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:courtyard -->",
  "### Courtyard",
  "",
  "Courtyard unique body.",
  "",
].join("\n");

const EMPTY_BEAT_MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:survive beat_kind=spine -->",
  "## Survive the Current Breach",
  "",
  "Hold the mire until the wall is sealed.",
  "",
].join("\n");

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    putPlayRunProgress: vi.fn(),
    getPlayRun: vi.fn(),
    putWorldPlayRunProgress: vi.fn(),
    getWorldPlayRun: vi.fn(),
  };
});

function progress(overrides: Partial<PlayRunProgress> = {}): PlayRunProgress {
  return {
    current_scene_id: null,
    current_beat_id: "beat:survive",
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

function worldRunRecord(overrides: Partial<WorldPlayRunRecordV2> = {}): WorldPlayRunRecordV2 {
  return {
    schema_version: "dmb_world_play_run_record_v2",
    run_id: RUN_ID,
    world_id: "longmont-c2",
    playable_artifact_id: ARTIFACT_ID,
    playable_revision: 3,
    playable_work_revision_id: "11111111-1111-4111-8111-111111111111",
    playable_content_sha256: CONTENT_SHA,
    run_revision: 4,
    created_at: "2026-09-30T00:00:00Z",
    updated_at: "2026-09-30T00:00:00Z",
    progress: progress(),
    ...overrides,
  };
}

function currentWorldRun(progressOverrides: Partial<PlayRunProgress> = {}): WorldPlayRunRecordV2 {
  return worldRunRecord({
    progress: progress({ current_scene_id: "scene:north-gate", ...progressOverrides }),
  });
}

function storedSceneNoteCache(): { key: string; value: Record<string, unknown> } | null {
  const key = Object.keys(localStorage).find((candidate) => candidate.startsWith("dmb.play.scene-note-draft.v1:"));
  if (!key) return null;
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  return { key, value: JSON.parse(raw) as Record<string, unknown> };
}

function v2Manifest(scenes: PlayRunReferenceManifestV2["scenes"]): PlayRunReferenceManifestV2 {
  return {
    schema_version: "dmb_play_run_reference_manifest_v2",
    run_id: RUN_ID,
    playable_artifact_id: ARTIFACT_ID,
    playable_revision: 3,
    playable_content_sha256: CONTENT_SHA,
    sealed_at: "2026-08-17T00:00:00Z",
    beats: [{ beat_id: "beat:survive", beat_kind: "spine" }],
    scenes,
    choices: [],
    options: [],
    edges: [],
  };
}

function readyDeck(run: PlayRunRecord = runRecord(), markdown: string = MARKDOWN) {
  const scenes = markdown === EMPTY_BEAT_MARKDOWN
    ? []
    : [
      { scene_id: "scene:tunnel", beat_id: "beat:survive" },
      { scene_id: "scene:north-gate", beat_id: "beat:survive" },
      { scene_id: "scene:courtyard", beat_id: "beat:survive" },
    ];
  const admitted = admitNativeRunbook({
    run: { ...run, run_id: run.run_id },
    manifest: { ...v2Manifest(scenes), run_id: run.run_id },
    committed: {
      schema_version: "dmb_workspace_committed_revision_v1",
      document_id: run.playable_artifact_id,
      kind: "runbook",
      campaign_id: "longmont-c2",
      title: "Mireward Breach",
      status: "active",
      object_revision: run.playable_revision,
      work_revision_id: "11111111-1111-4111-8111-111111111111",
      revision_n: run.playable_revision,
      markdown,
      content_sha256: run.playable_content_sha256,
      has_divergent_working_copy: false,
      target_relpath: "out/workspace/runbooks/mireward.md",
    },
  });
  if (admitted.status !== "ready") throw new Error(`expected ready, got ${admitted.status}`);
  if (admitted.grammar !== "v2") throw new Error("expected v2");
  return admitted;
}

function readyWorldDeck(run: WorldPlayRunRecordV2 = worldRunRecord()) {
  const scenes = [
    { scene_id: "scene:tunnel", beat_id: "beat:survive" },
    { scene_id: "scene:north-gate", beat_id: "beat:survive" },
    { scene_id: "scene:courtyard", beat_id: "beat:survive" },
  ];
  const admitted = admitNativeRunbook({
    run,
    manifest: {
      ...v2Manifest(scenes),
      run_id: run.run_id,
      playable_artifact_id: run.playable_artifact_id,
      playable_revision: run.playable_revision,
      playable_content_sha256: run.playable_content_sha256,
    },
    committed: {
      schema_version: "dmb_workspace_committed_revision_v2",
      scope_mode: "world",
      world_id: run.world_id,
      document_id: run.playable_artifact_id,
      kind: "runbook",
      campaign_id: null,
      title: "World Mireward Breach",
      status: "active",
      object_revision: run.playable_revision,
      work_revision_id: run.playable_work_revision_id,
      revision_n: run.playable_revision,
      markdown: MARKDOWN,
      content_sha256: run.playable_content_sha256,
      has_divergent_working_copy: false,
      target_relpath: null,
    },
  });
  if (admitted.status !== "ready" || admitted.grammar !== "v2") {
    throw new Error(`expected ready World v2 deck, got ${admitted.status}`);
  }
  return admitted;
}

function Harness({
  initialRun = runRecord(),
  markdown = MARKDOWN,
}: {
  initialRun?: PlayRunRecord;
  markdown?: string;
}) {
  const [deck, setDeck] = useState(() => readyDeck(initialRun, markdown));
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  return (
    <PlayCurrentMomentCockpit
      deck={deck}
      mutationStatus={mutationStatus}
      onMutationStatus={setMutationStatus}
      onAuthoritativeRun={(run) =>
        setDeck((current) => overlayRuntimeOnV2Ready(current, run) ?? current)
      }
    />
  );
}

function WorldHarness({ initialRun = worldRunRecord() }: { initialRun?: WorldPlayRunRecordV2 }) {
  const [deck, setDeck] = useState(() => readyWorldDeck(initialRun));
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  return (
    <PlayCurrentMomentCockpit
      deck={deck}
      mutationStatus={mutationStatus}
      onMutationStatus={setMutationStatus}
      onAuthoritativeRun={(run) =>
        setDeck((current) => overlayRuntimeOnV2Ready(current, run) ?? current)
      }
    />
  );
}

describe("PlayCurrentMomentCockpit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the persisted Scene as the central workspace", () => {
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Tunnel Breach");
    expect(screen.getByTestId("play-beat-context-disclosure")).toHaveAttribute("data-beat-id", "beat:survive");
    expect(screen.queryByTestId("play-workspace-beat-only")).not.toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("keeps authored current Beat context available while a Scene is active", async () => {
    const user = userEvent.setup();
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            current_scene_id: "scene:north-gate",
            resolved_beat_ids: ["beat:hold-breach"],
          }),
        })}
      />,
    );
    const context = screen.getByTestId("play-beat-context-disclosure");
    expect(context).toHaveAttribute("data-beat-id", "beat:hold-breach");
    expect(context).toHaveAttribute("data-beat-resolved", "true");
    expect(context).toHaveTextContent("spine · Resolved");
    await user.click(within(context).getByText("Hold the Breach"));
    expect(context).toHaveTextContent("Creatures have broken through the defensive wall.");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("places the active Scene before supporting rails in reading and keyboard order", () => {
    render(<Harness initialRun={runRecord({
      progress: progress({ current_scene_id: "scene:north-gate" }),
    })} />);

    const scene = screen.getByTestId("play-workspace-current");
    const beatToggle = screen.getByTestId("play-beat-context-toggle");
    const glanceToggle = screen.getByTestId("play-at-a-glance-toggle");
    expect(scene.compareDocumentPosition(beatToggle) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    expect(beatToggle.compareDocumentPosition(glanceToggle) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });

  it("renders admitted Scene body AST with references and authored block structure", () => {
    const markdown = MARKDOWN.replace(
      "Tunnel unique body.",
      [
        "A long warehouse paragraph names [Lysandra Ironveil](dmb-node:lysandra-ironveil) and preserves its inline reference.",
        "",
        "A second paragraph remains separate.",
        "",
        "- Inspect the loading bay",
        "- Check the upper windows",
        "",
        "> Read this aloud before the guards arrive.",
      ].join("\n"),
    );
    render(
      <Harness
        markdown={markdown}
        initialRun={runRecord({ progress: progress({ current_scene_id: "scene:tunnel" }) })}
      />,
    );
    const body = screen.getByTestId("play-workspace-current").querySelector(".play-scene-board-body");
    expect(body).toBeInTheDocument();
    expect(body?.querySelectorAll(":scope > p")).toHaveLength(2);
    expect(body?.querySelectorAll(":scope > ul > li")).toHaveLength(2);
    expect(body?.querySelector(":scope > blockquote")).toHaveTextContent(
      "Read this aloud before the guards arrive.",
    );
    const reference = body?.querySelector('[data-plan-card-reference="graph"]');
    expect(reference).toHaveTextContent("Lysandra Ironveil");
    expect(reference).toHaveAttribute("data-graph-node-id", "lysandra-ironveil");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("fails closed for unsafe or unknown captured body nodes and keeps legacy plain text readable", () => {
    const unsafeDeck = readyDeck(runRecord({
      progress: progress({ current_scene_id: "scene:tunnel" }),
    }));
    const scene = unsafeDeck.beats[0]?.scenes.find((entry) => entry.id === "scene:tunnel");
    if (!scene) throw new Error("expected fixture Scene");
    scene.bodyContent = [{
      type: "paragraph",
      content: [{
        type: "text",
        text: "unsafe link",
        marks: [{ type: "link", attrs: { href: "javascript:alert(1)" } }],
      }],
    }];
    scene.bodyText = "must not fall back when captured content is unsafe";
    const renderDeck = (deck: ReturnType<typeof readyDeck>) => (
      <PlayCurrentMomentCockpit
        deck={deck}
        mutationStatus="idle"
        onMutationStatus={() => undefined}
        onAuthoritativeRun={() => undefined}
      />
    );
    const { rerender } = render(renderDeck(unsafeDeck));
    expect(screen.getByRole("status")).toHaveTextContent("cannot be displayed safely");
    expect(screen.queryByText("must not fall back when captured content is unsafe")).not.toBeInTheDocument();

    const unknownDeck = readyDeck(runRecord({
      progress: progress({ current_scene_id: "scene:tunnel" }),
    }));
    const unknownScene = unknownDeck.beats[0]?.scenes.find((entry) => entry.id === "scene:tunnel");
    if (!unknownScene) throw new Error("expected fixture Scene");
    unknownScene.bodyContent = [{ type: "paragraph", content: [{ type: "unregisteredAuthoredNode", text: "unknown" }] }];
    rerender(renderDeck(unknownDeck));
    expect(screen.getByRole("status")).toHaveTextContent("cannot be displayed safely");
    expect(screen.queryByText("unknown")).not.toBeInTheDocument();

    unknownScene.bodyContent = [{
      type: "paragraph",
      content: [{ type: "text", text: "unknown mark", marks: [{ type: "unregisteredMark" }] }],
    }];
    rerender(renderDeck(unknownDeck));
    expect(screen.getByRole("status")).toHaveTextContent("cannot be displayed safely");
    expect(screen.queryByText("unknown mark")).not.toBeInTheDocument();

    const legacyDeck = readyDeck(runRecord({
      progress: progress({ current_scene_id: "scene:tunnel" }),
    }));
    const legacyScene = legacyDeck.beats[0]?.scenes.find((entry) => entry.id === "scene:tunnel");
    if (!legacyScene) throw new Error("expected fixture Scene");
    delete legacyScene.bodyContent;
    legacyScene.bodyText = "Legacy plain body remains readable.";
    rerender(renderDeck(legacyDeck));
    expect(screen.getByText("Legacy plain body remains readable.")).toBeInTheDocument();
  });

  it("does not fabricate a Scene when none is current", () => {
    render(<Harness />);
    expect(screen.getByTestId("play-workspace-beat-only")).toBeInTheDocument();
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("No Scene is current");
    expect(screen.queryByTestId("play-workspace-current")).not.toBeInTheDocument();
    expect(screen.queryByText("Tunnel unique body.")).not.toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("collapses Beat Context without writing progress", async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    const toggle = screen.getByTestId("play-beat-context-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-beat-collapsed", "true");
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-glance-collapsed", "false");
    expect(screen.getByTestId("play-beat-context")).toHaveClass("is-collapsed");
    expect(screen.queryByTestId("play-beat-context-title")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("collapses Recorded outcomes without writing progress", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const toggle = screen.getByTestId("play-at-a-glance-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-glance-collapsed", "true");
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-beat-collapsed", "false");
    expect(screen.getByTestId("play-at-a-glance")).toHaveClass("is-collapsed");
    expect(screen.queryByTestId("play-recorded-choices-empty")).not.toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("collapses both rails without occupying expanded column tracks", async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    const shell = screen.getByTestId("play-cockpit-shell");
    expect(shell).toHaveAttribute("data-beat-collapsed", "false");
    expect(shell).toHaveAttribute("data-glance-collapsed", "false");
    await user.click(screen.getByTestId("play-beat-context-toggle"));
    await user.click(screen.getByTestId("play-at-a-glance-toggle"));
    expect(shell).toHaveAttribute("data-beat-collapsed", "true");
    expect(shell).toHaveAttribute("data-glance-collapsed", "true");
    expect(screen.getByTestId("play-beat-context")).toHaveClass("is-collapsed");
    expect(screen.getByTestId("play-at-a-glance")).toHaveClass("is-collapsed");
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("shows scenes in the outline and keeps the current scene in the central workspace", () => {
    render(<Harness />);
    expect(screen.getByRole("navigation", { name: "Scenes in this Run" })).toHaveTextContent("Tunnel Breach");
    expect(screen.getByTestId("play-workspace-beat-only")).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("inspects another Scene without writing progress and labels inspection", async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Courtyard/ }));
    expect(screen.getByTestId("play-workspace-inspect")).toBeInTheDocument();
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent(/Viewing: .* · Courtyard/);
    expect(screen.getByTestId("play-inspect-current")).toHaveTextContent(/Run position: .* · Tunnel Breach/);
    expect(screen.getByRole("heading", { name: "Inspecting Courtyard" })).toBeInTheDocument();
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Tunnel Breach");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("lists Scenes from every Beat and only changes current position after explicit Make Current", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(
      breachRun({
        run_revision: 5,
        progress: breachProgress({
          current_beat_id: "beat:lower-tunnels",
          current_scene_id: "scene:lower-cistern",
        }),
      }),
    );
    render(<BreachHarness />);

    const lowerBeatScene = screen.getByRole("button", { name: /Lower Cistern/ });
    expect(lowerBeatScene).toBeInTheDocument();
    await user.click(lowerBeatScene);
    expect(screen.getByTestId("play-workspace-inspect")).toHaveTextContent("Inspecting Lower Cistern");
    expect(screen.getByTestId("play-inspect-current")).toHaveTextContent("Run position: Hold the Breach · North Gate");
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent("Viewing: Lower Tunnels · Lower Cistern");
    const viewingBeat = screen.getByTestId("play-beat-context-disclosure");
    expect(viewingBeat).toHaveAttribute("data-beat-id", "beat:lower-tunnels");
    expect(viewingBeat).toHaveAttribute("data-beat-resolved", "false");
    expect(viewingBeat).toHaveTextContent("optional · Not marked resolved");
    await user.click(within(viewingBeat).getByText("Lower Tunnels"));
    expect(viewingBeat).toHaveTextContent("Following the brood deeper turns the defense");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Make Lower Cistern current" }));
    await waitFor(() => expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1]).toEqual({
      expected_run_revision: 4,
      progress: expect.objectContaining({
        current_beat_id: "beat:lower-tunnels",
        current_scene_id: "scene:lower-cistern",
        selections: {},
        notes_by_element_id: {},
      }),
    });
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Lower Cistern");
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Water echoes below the broken gate.");
  });

  it("returns from inspection to the authoritative current moment", async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Courtyard/ }));
    await user.click(screen.getByTestId("play-workspace-back"));
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
    expect(screen.queryByTestId("play-workspace-inspect")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("play-beat-context-toggle")).toHaveFocus();
    });
  });

  it("restores inspection focus to the outline when the outline is collapsed", async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Courtyard/ }));
    await user.click(screen.getByTestId("play-beat-context-toggle"));
    expect(screen.getByTestId("play-beat-context-toggle")).toHaveAttribute("aria-expanded", "false");
    await user.click(screen.getByTestId("play-workspace-back"));
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
    await waitFor(() => {
      expect(screen.getByTestId("play-beat-context-toggle")).toHaveFocus();
    });
  });

  it("Make Current sends one CAS with Beat and Scene and preserves unrelated progress", async () => {
    const user = userEvent.setup();
    const initial = runRecord({
      progress: progress({
        resolved_beat_ids: ["beat:survive"],
        selections: { "choice:keep": "option:keep" },
        notes_by_element_id: { "scene:tunnel": "keep me" },
      }),
    });
    const updated = runRecord({
      run_revision: 5,
      progress: progress({
        current_scene_id: "scene:tunnel",
        resolved_beat_ids: ["beat:survive"],
        selections: { "choice:keep": "option:keep" },
        notes_by_element_id: { "scene:tunnel": "keep me" },
      }),
    });
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(updated);
    render(<Harness initialRun={initial} />);

    await user.click(screen.getByRole("button", { name: "Make Tunnel Breach current" }));

    await waitFor(() => expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[0]).toBe(RUN_ID);
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1]).toEqual({
      expected_run_revision: 4,
      progress: expect.objectContaining({
        current_beat_id: "beat:survive",
        current_scene_id: "scene:tunnel",
        resolved_beat_ids: ["beat:survive"],
        selections: { "choice:keep": "option:keep" },
        notes_by_element_id: { "scene:tunnel": "keep me" },
      }),
    });
    expect(await screen.findByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
  });

  it("does not double-submit Make Current while saving", async () => {
    const user = userEvent.setup();
    let resolvePut: (run: PlayRunRecord) => void = () => undefined;
    vi.mocked(liveApi.putPlayRunProgress).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePut = resolve;
        }),
    );
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "Make Tunnel Breach current" }));
    expect(await screen.findByTestId("play-saving")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Make North Gate current" }));
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    resolvePut(runRecord({
      run_revision: 5,
      progress: progress({ current_scene_id: "scene:tunnel" }),
    }));
    expect(await screen.findByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
  });

  it("does not claim the requested Scene after a 409", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new LiveApiError("CAS conflict", 409));
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(
      runRecord({
        run_revision: 9,
        progress: progress({ current_scene_id: "scene:north-gate" }),
      }),
    );
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "Make Tunnel Breach current" }));
    expect(await screen.findByTestId("play-cas-conflict")).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("North Gate unique body.");
    expect(screen.queryByTestId("play-workspace-current")).not.toHaveTextContent("Tunnel unique body.");
  });

  it("writes World current-Scene progress through V2 and reconciles with the same World", async () => {
    const user = userEvent.setup();
    const updated = worldRunRecord({
      run_revision: 9,
      progress: progress({ current_scene_id: "scene:tunnel" }),
    });
    vi.mocked(liveApi.putWorldPlayRunProgress).mockRejectedValue(new LiveApiError("CAS conflict", 409));
    vi.mocked(liveApi.getWorldPlayRun).mockResolvedValue(updated);
    render(<WorldHarness />);

    await user.click(screen.getByRole("button", { name: "Make Tunnel Breach current" }));

    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledWith(RUN_ID, "longmont-c2", {
      expected_run_revision: 4,
      progress: expect.objectContaining({
        current_beat_id: "beat:survive",
        current_scene_id: "scene:tunnel",
      }),
    });
    expect(await screen.findByTestId("play-cas-conflict")).toBeInTheDocument();
    expect(liveApi.getWorldPlayRun).toHaveBeenCalledWith(RUN_ID, "longmont-c2");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
    expect(liveApi.getPlayRun).not.toHaveBeenCalled();
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Tunnel Breach");
  });

  it("autosaves and acknowledges a World-owned marker-v2 Scene note through the fenced writer", async () => {
    const user = userEvent.setup();
    const updated = worldRunRecord({
      run_revision: 5,
      progress: progress({
        current_scene_id: "scene:north-gate",
        selections: { "choice:keep": "option:hold" },
        notes_by_element_id: {
          "scene:tunnel": "Keep the other Scene note.",
          "scene:north-gate": "Gate held until dawn.",
        },
      }),
    });
    vi.mocked(liveApi.putWorldPlayRunProgress).mockResolvedValue(updated);
    render(<WorldHarness initialRun={currentWorldRun({
      selections: { "choice:keep": "option:hold" },
      notes_by_element_id: { "scene:tunnel": "Keep the other Scene note." },
    })} />);

    await user.type(screen.getByLabelText("Scene note"), "Gate held until dawn.");

    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledWith(RUN_ID, "longmont-c2", {
      expected_run_revision: 4,
      progress: expect.objectContaining({
        current_scene_id: "scene:north-gate",
        selections: { "choice:keep": "option:hold" },
        notes_by_element_id: {
          "scene:tunnel": "Keep the other Scene note.",
          "scene:north-gate": "Gate held until dawn.",
        },
      }),
    });
    expect(await screen.findByText("Saved in this Run.")).toBeInTheDocument();
    expect(screen.getByLabelText("Scene note")).toHaveValue("Gate held until dawn.");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
    expect(storedSceneNoteCache()).toBeNull();
  });

  it("hydrates the Scene note from canonical Run progress without writing on mount", async () => {
    render(<WorldHarness initialRun={currentWorldRun({
      notes_by_element_id: { "scene:north-gate": "Canonical Run note." },
    })} />);

    expect(screen.getByLabelText("Scene note")).toHaveValue("Canonical Run note.");
    expect(screen.getByText("Saved in this Run.")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(liveApi.putWorldPlayRunProgress).not.toHaveBeenCalled();
    expect(storedSceneNoteCache()).toBeNull();
  });

  it("keeps the draft when a successful response does not contain the exact submitted note", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putWorldPlayRunProgress).mockResolvedValue(worldRunRecord({
      run_revision: 5,
      progress: progress({
        current_scene_id: "scene:north-gate",
        notes_by_element_id: { "scene:north-gate": "Different server note" },
      }),
    }));
    render(<WorldHarness initialRun={currentWorldRun()} />);
    await user.type(screen.getByLabelText("Scene note"), "Submitted draft");

    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(screen.getByLabelText("Scene note")).toHaveValue("Submitted draft");
    expect(screen.getByTestId("play-scene-note-status")).toHaveTextContent(
      "Not saved. Another update changed this Run",
    );
    expect(screen.queryByText("Saved in this Run.")).not.toBeInTheDocument();
    expect(storedSceneNoteCache()?.value.failure).toBe("unconfirmed");
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1);
  });

  it("retains a newer edit while an earlier Scene note snapshot is in flight", async () => {
    const user = userEvent.setup();
    const pending: Array<(run: WorldPlayRunRecordV2) => void> = [];
    vi.mocked(liveApi.putWorldPlayRunProgress).mockImplementation(() => new Promise((resolve) => {
      pending.push(resolve);
    }));
    render(<WorldHarness initialRun={currentWorldRun()} />);
    const note = screen.getByLabelText("Scene note");

    await user.type(note, "First");
    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    await user.type(note, " newer edit");
    expect(note).toHaveValue("First newer edit");
    expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1);

    const firstResponse = pending.shift();
    if (!firstResponse) throw new Error("expected the first note save to be pending");
    firstResponse(worldRunRecord({
      run_revision: 5,
      progress: progress({
        current_scene_id: "scene:north-gate",
        notes_by_element_id: { "scene:north-gate": "First" },
      }),
    }));

    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(2));
    expect(vi.mocked(liveApi.putWorldPlayRunProgress).mock.calls[1]?.[2]).toEqual({
      expected_run_revision: 5,
      progress: expect.objectContaining({
        notes_by_element_id: { "scene:north-gate": "First newer edit" },
      }),
    });
    const secondResponse = pending.shift();
    if (!secondResponse) throw new Error("expected the newer note save to be pending");
    secondResponse(worldRunRecord({
      run_revision: 6,
      progress: progress({
        current_scene_id: "scene:north-gate",
        notes_by_element_id: { "scene:north-gate": "First newer edit" },
      }),
    }));
    expect(await screen.findByText("Saved in this Run.")).toBeInTheDocument();
    expect(screen.getByLabelText("Scene note")).toHaveValue("First newer edit");
  });

  it("restores a newer draft as unknown when reloaded during an older in-flight save", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putWorldPlayRunProgress).mockImplementation(
      () => new Promise(() => undefined),
    );
    const firstMount = render(<WorldHarness initialRun={currentWorldRun()} />);
    const note = screen.getByLabelText("Scene note");
    await user.type(note, "First");
    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    await user.type(note, " newer edit");
    expect(note).toHaveValue("First newer edit");
    expect(storedSceneNoteCache()?.value.text).toBe("First newer edit");
    expect(storedSceneNoteCache()?.value.sentText).toBe("First");
    firstMount.unmount();

    render(<WorldHarness initialRun={currentWorldRun()} />);
    expect(screen.getByLabelText("Scene note")).toHaveValue("First newer edit");
    expect(screen.getByTestId("play-scene-note-status")).toHaveTextContent(
      "previous save result is unknown",
    );
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1);
  });

  it("ignores a late Scene note response after the Run's pinned Playable changes", async () => {
    const user = userEvent.setup();
    let resolveWrite: ((run: WorldPlayRunRecordV2) => void) | undefined;
    const onAuthoritativeRun = vi.fn();
    vi.mocked(liveApi.putWorldPlayRunProgress).mockImplementation(() => new Promise((resolve) => {
      resolveWrite = resolve;
    }));
    const initial = currentWorldRun();
    const view = render(
      <PlayCurrentMomentCockpit
        deck={readyWorldDeck(initial)}
        mutationStatus="idle"
        onMutationStatus={vi.fn()}
        onAuthoritativeRun={onAuthoritativeRun}
      />,
    );
    await user.type(screen.getByLabelText("Scene note"), "Bound to old Playable");
    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));

    const rebound = worldRunRecord({
      playable_revision: 4,
      playable_work_revision_id: "22222222-2222-4222-8222-222222222222",
      run_revision: 5,
      progress: progress({ current_scene_id: "scene:north-gate" }),
    });
    view.rerender(
      <PlayCurrentMomentCockpit
        deck={readyWorldDeck(rebound)}
        mutationStatus="idle"
        onMutationStatus={vi.fn()}
        onAuthoritativeRun={onAuthoritativeRun}
      />,
    );
    const acknowledge = resolveWrite;
    if (!acknowledge) throw new Error("expected the old-binding note write to be pending");
    acknowledge(worldRunRecord({
      run_revision: 5,
      progress: progress({
        current_scene_id: "scene:north-gate",
        notes_by_element_id: { "scene:north-gate": "Bound to old Playable" },
      }),
    }));

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(onAuthoritativeRun).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Scene note")).toHaveValue("");
    expect(screen.queryByText("Saved in this Run.")).not.toBeInTheDocument();
  });

  it("recovers an intentional empty browser draft without replaying it after reload", async () => {
    const user = userEvent.setup();
    const initial = currentWorldRun();
    const firstMount = render(<WorldHarness initialRun={initial} />);
    const note = screen.getByLabelText("Scene note");
    await user.type(note, "temporary");
    await user.clear(note);

    const cached = storedSceneNoteCache();
    expect(cached?.value.text).toBe("");
    expect(cached?.value.basisPresent).toBe(false);
    firstMount.unmount();

    const updated = worldRunRecord({
      run_revision: 5,
      progress: progress({ current_scene_id: "scene:north-gate", notes_by_element_id: { "scene:north-gate": "" } }),
    });
    vi.mocked(liveApi.putWorldPlayRunProgress).mockResolvedValue(updated);
    render(<WorldHarness initialRun={initial} />);
    expect(screen.getByLabelText("Scene note")).toHaveValue("");
    expect(await screen.findByText("Recovered browser draft; unsaved in this Run. Save it when ready.")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(liveApi.putWorldPlayRunProgress).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Save recovered note" }));
    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(vi.mocked(liveApi.putWorldPlayRunProgress).mock.calls[0]?.[2].progress.notes_by_element_id)
      .toEqual({ "scene:north-gate": "" });
    expect(await screen.findByText("Saved in this Run.")).toBeInTheDocument();
  });

  it.each([
    ["409 conflict", "conflict", new LiveApiError("CAS conflict", 409), true],
    ["422 rejection", "rejected", new LiveApiError("invalid progress", 422), true],
    ["unknown outcome", "unknown", new Error("network down"), true],
    ["unknown outcome with failed reread", "unknown", new Error("network down"), false],
  ] as const)("keeps a %s Scene note draft across reload without automatic replay", async (_label, failure, error, rereadSucceeds) => {
    const user = userEvent.setup();
    const serverRun = currentWorldRun({
      run_revision: 9,
      notes_by_element_id: { "scene:north-gate": "Server version" },
    });
    vi.mocked(liveApi.putWorldPlayRunProgress).mockRejectedValueOnce(error);
    if (rereadSucceeds) {
      vi.mocked(liveApi.getWorldPlayRun).mockResolvedValue(serverRun);
    } else {
      vi.mocked(liveApi.getWorldPlayRun).mockRejectedValue(new Error("Run reload failed"));
    }
    const firstMount = render(<WorldHarness initialRun={currentWorldRun()} />);
    await user.type(screen.getByLabelText("Scene note"), "Keep this local draft");
    await user.click(screen.getByRole("button", { name: "Save note now" }));
    await waitFor(() => expect(storedSceneNoteCache()?.value.failure).toBe(failure));
    expect(screen.getByLabelText("Scene note")).toHaveValue("Keep this local draft");
    expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1);
    firstMount.unmount();

    render(<WorldHarness initialRun={serverRun} />);
    expect(screen.getByLabelText("Scene note")).toHaveValue("Keep this local draft");
    expect(screen.getByTestId("play-scene-note-status")).toHaveTextContent(
      failure === "conflict" || !rereadSucceeds
        ? "Another update changed this Run"
        : failure === "unknown"
          ? "previous save result is unknown"
          : "Run rejected this note",
    );
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1);
  });

  it("quarantines a browser draft whose pinned Playable binding no longer matches", async () => {
    const user = userEvent.setup();
    const initial = currentWorldRun();
    const firstMount = render(<WorldHarness initialRun={initial} />);
    await user.type(screen.getByLabelText("Scene note"), "Old binding draft");
    const cached = storedSceneNoteCache();
    if (!cached) throw new Error("expected the browser draft cache");
    firstMount.unmount();
    localStorage.setItem(cached.key, JSON.stringify({ ...cached.value, playableRevision: 2 }));

    render(<WorldHarness initialRun={initial} />);
    expect(screen.getByLabelText("Scene note")).toHaveValue("");
    expect(await screen.findByTestId("play-scene-note-storage-warning")).toHaveTextContent(
      "belongs to a different or unreadable Run version and was not restored",
    );
    expect(liveApi.putWorldPlayRunProgress).not.toHaveBeenCalled();
  });

  it("keeps a local draft unsaved when the server note changed before autosave", async () => {
    const user = userEvent.setup();
    const initial = currentWorldRun({
      notes_by_element_id: { "scene:north-gate": "Original server note" },
    });
    const concurrent = worldRunRecord({
      run_revision: 5,
      progress: progress({
        current_scene_id: "scene:north-gate",
        notes_by_element_id: { "scene:north-gate": "Concurrent server note" },
      }),
    });
    const view = render(
      <PlayCurrentMomentCockpit
        deck={readyWorldDeck(initial)}
        mutationStatus="idle"
        onMutationStatus={vi.fn()}
        onAuthoritativeRun={vi.fn()}
      />,
    );
    await user.clear(screen.getByLabelText("Scene note"));
    await user.type(screen.getByLabelText("Scene note"), "Local note draft");

    view.rerender(
      <PlayCurrentMomentCockpit
        deck={readyWorldDeck(concurrent)}
        mutationStatus="idle"
        onMutationStatus={vi.fn()}
        onAuthoritativeRun={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Scene note")).toHaveValue("Local note draft");
    expect(screen.getByTestId("play-scene-note-status")).toHaveTextContent(
      "Another update changed this Run",
    );
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(liveApi.putWorldPlayRunProgress).not.toHaveBeenCalled();

    const acknowledged = worldRunRecord({
      run_revision: 6,
      progress: progress({
        current_scene_id: "scene:north-gate",
        notes_by_element_id: { "scene:north-gate": "Local note draft" },
      }),
    });
    vi.mocked(liveApi.putWorldPlayRunProgress).mockResolvedValue(acknowledged);
    await user.click(screen.getByRole("button", { name: "Save note after review" }));
    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(vi.mocked(liveApi.putWorldPlayRunProgress).mock.calls[0]?.[2]).toEqual({
      expected_run_revision: 5,
      progress: expect.objectContaining({
        notes_by_element_id: { "scene:north-gate": "Local note draft" },
      }),
    });
    expect(await screen.findByText("Saved in this Run.")).toBeInTheDocument();
  });

  it("warns on a corrupt recovery cache and keeps canonical progress editable", async () => {
    const user = userEvent.setup();
    const initial = currentWorldRun({
      notes_by_element_id: { "scene:north-gate": "Canonical note" },
    });
    const firstMount = render(<WorldHarness initialRun={initial} />);
    await user.clear(screen.getByLabelText("Scene note"));
    await user.type(screen.getByLabelText("Scene note"), "Local draft");
    const cached = storedSceneNoteCache();
    if (!cached) throw new Error("expected the browser draft cache");
    firstMount.unmount();
    localStorage.setItem(cached.key, "{invalid json");

    render(<WorldHarness initialRun={initial} />);
    expect(screen.getByLabelText("Scene note")).toHaveValue("Canonical note");
    expect(await screen.findByTestId("play-scene-note-storage-warning")).toHaveTextContent(
      "A browser note draft could not be read",
    );
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(liveApi.putWorldPlayRunProgress).not.toHaveBeenCalled();
  });

  it("keeps the in-memory Scene note editable when browser recovery storage fails", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putWorldPlayRunProgress).mockImplementation(
      () => new Promise(() => undefined),
    );
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota exceeded");
    });
    const firstMount = render(<WorldHarness initialRun={currentWorldRun()} />);
    const note = screen.getByLabelText("Scene note");
    await user.type(note, "In-memory note");
    expect(note).toHaveValue("In-memory note");
    expect(screen.getByTestId("play-scene-note-storage-warning")).toHaveTextContent(
      "Browser recovery storage is unavailable",
    );
    await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("play-scene-note-status")).toHaveTextContent("Saving note to this Run");
    firstMount.unmount();
  });

  it("reconciles an unknown mutation outcome from the exact Run", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new Error("network down"));
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(
      runRecord({
        progress: progress({ current_scene_id: "scene:tunnel" }),
      }),
    );
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Courtyard/ }));
    await user.click(screen.getByRole("button", { name: "Make Courtyard current" }));
    expect(await screen.findByTestId("play-unknown-outcome")).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Tunnel Breach");
    expect(screen.queryByRole("heading", { name: "Courtyard" })).not.toBeInTheDocument();
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent(/Viewing: .* · Courtyard/);
  });

  it("Back uses the new authoritative current Scene if Runtime changed during inspection", async () => {
    const user = userEvent.setup();
    const initial = runRecord({
      progress: progress({ current_scene_id: "scene:tunnel" }),
    });
    function LiveHarness() {
      const [deck, setDeck] = useState(() => readyDeck(initial));
      const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
      return (
        <>
          <button
            type="button"
            onClick={() =>
              setDeck((current) =>
                overlayRuntimeOnV2Ready(
                  current,
                  runRecord({
                    run_revision: 8,
                    progress: progress({ current_scene_id: "scene:north-gate" }),
                  }),
                ) ?? current
              )
            }
          >
            Simulate writer
          </button>
          <PlayCurrentMomentCockpit
            deck={deck}
            mutationStatus={mutationStatus}
            onMutationStatus={setMutationStatus}
            onAuthoritativeRun={(run) =>
              setDeck((current) => overlayRuntimeOnV2Ready(current, run) ?? current)
            }
          />
        </>
      );
    }
    render(<LiveHarness />);
    await user.click(screen.getByRole("button", { name: /Courtyard/ }));
    await user.click(screen.getByRole("button", { name: "Simulate writer" }));
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent(/Viewing: .* · Courtyard/);
    await user.click(screen.getByTestId("play-workspace-back"));
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("North Gate unique body.");
    expect(screen.queryByText("Tunnel unique body.")).not.toBeInTheDocument();
  });

  it("clears transient inspection state when the Run identity changes", async () => {
    const user = userEvent.setup();
    const first = readyDeck(runRecord({
      progress: progress({ current_scene_id: "scene:tunnel" }),
    }));
    const second = readyDeck(runRecord({
      run_id: OTHER_RUN_ID,
      progress: progress({ current_scene_id: "scene:courtyard" }),
    }));
    function SwitchHarness() {
      const [deck, setDeck] = useState(first);
      const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
      return (
        <>
          <button type="button" onClick={() => setDeck(second)}>Switch run</button>
          <PlayCurrentMomentCockpit
            deck={deck}
            mutationStatus={mutationStatus}
            onMutationStatus={setMutationStatus}
            onAuthoritativeRun={() => undefined}
          />
        </>
      );
    }
    render(<SwitchHarness />);
    await user.click(screen.getByRole("button", { name: /North Gate/ }));
    expect(screen.getByTestId("play-workspace-inspect")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Switch run" }));
    expect(screen.queryByTestId("play-workspace-inspect")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Courtyard unique body.");
  });

  it("shows a truthful empty Scene outline", () => {
    render(<Harness markdown={EMPTY_BEAT_MARKDOWN} />);
    expect(screen.getByRole("navigation", { name: "Scenes in this Run" })).toHaveTextContent("No scenes");
    expect(screen.getByTestId("play-scenes-empty")).toHaveTextContent(
      "No authored Scenes in this Beat.",
    );
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });
});

function breachProgress(overrides: Partial<PlayRunProgress> = {}): PlayRunProgress {
  return progress({
    current_beat_id: "beat:hold-breach",
    current_scene_id: "scene:north-gate",
    ...overrides,
  });
}

function breachRun(overrides: Partial<PlayRunRecord> = {}): PlayRunRecord {
  const { progress: progressOverride, ...rest } = overrides;
  return runRecord({
    ...rest,
    progress: breachProgress(progressOverride),
  });
}

function readyBreachDeck(run: PlayRunRecord = breachRun()) {
  const admitted = admitNativeRunbook({
    run: { ...run, run_id: run.run_id },
    manifest: { ...breachDogfoodManifestV2(run), run_id: run.run_id },
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
  if (admitted.status !== "ready") throw new Error(`expected ready, got ${admitted.status}`);
  if (admitted.grammar !== "v2") throw new Error("expected v2");
  return admitted;
}

function BreachHarness({ initialRun = breachRun() }: { initialRun?: PlayRunRecord }) {
  const [deck, setDeck] = useState(() => readyBreachDeck(initialRun));
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  return (
    <PlayCurrentMomentCockpit
      deck={deck}
      mutationStatus={mutationStatus}
      onMutationStatus={setMutationStatus}
      onAuthoritativeRun={(run) =>
        setDeck((current) => overlayRuntimeOnV2Ready(current, run) ?? current)
      }
    />
  );
}

describe("PlayCurrentMomentCockpit Decision interaction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the North Gate Decision inside the Scene board, not a rail", () => {
    render(<BreachHarness />);
    const board = screen.getByTestId("play-workspace-current");
    const decision = screen.getByTestId("play-decision");
    expect(board).toContainElement(decision);
    expect(screen.getByTestId("play-central-workspace")).toContainElement(decision);
    expect(screen.getByTestId("play-beat-context")).not.toContainElement(decision);
    expect(screen.getByTestId("play-at-a-glance")).not.toContainElement(decision);
    expect(screen.getByTestId("play-at-a-glance")).toHaveTextContent("Current selections and notes in this Run");
    expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument();
    expect(screen.getByTestId("play-decision-prompt")).toHaveTextContent(
      "What do they do with the surviving brood?",
    );
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Seal the breach" })).not.toBeChecked();
    expect(screen.queryByTestId("play-decision-consequence")).not.toBeInTheDocument();
    expect(screen.queryByTestId("play-decision-clear")).not.toBeInTheDocument();
  });

  it("projects saved choices and Scene notes into Recorded outcomes without writing progress", () => {
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            selections: { "choice:surviving-brood": "option:follow-brood" },
            notes_by_element_id: { "scene:north-gate": "The defenders are short on rope." },
          }),
        })}
      />,
    );

    const outcomes = screen.getByTestId("play-at-a-glance");
    expect(outcomes).toHaveTextContent("Saved choices & notes");
    expect(outcomes).toHaveTextContent("What do they do with the surviving brood?");
    expect(outcomes).toHaveTextContent("Follow it");
    expect(outcomes).toHaveTextContent("The defenders are short on rope.");
    expect(outcomes).toHaveTextContent("Current selections and notes in this Run");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("does not project the North Gate Decision when no Scene is current", () => {
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({ current_scene_id: null }),
        })}
      />,
    );
    expect(screen.getByTestId("play-workspace-beat-only")).toBeInTheDocument();
    expect(screen.queryByTestId("play-decision")).not.toBeInTheDocument();
  });

  it("does not project the North Gate Decision when another Scene is current", () => {
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({ current_scene_id: "scene:tunnel-pursuit" }),
        })}
      />,
    );
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel Pursuit");
    expect(screen.queryByTestId("play-decision")).not.toBeInTheDocument();
  });

  it("selects Follow it with one CAS and shows both emphasized branch rows after authority", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(
      breachRun({
        run_revision: 5,
        progress: breachProgress({
          resolved_beat_ids: ["beat:hold-breach"],
          selections: { "choice:keep": "option:keep", "choice:surviving-brood": "option:follow-brood" },
          notes_by_element_id: { "scene:north-gate": "keep me" },
        }),
      }),
    );
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            resolved_beat_ids: ["beat:hold-breach"],
            selections: { "choice:keep": "option:keep" },
            notes_by_element_id: { "scene:north-gate": "keep me" },
          }),
        })}
      />,
    );
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    await waitFor(() => expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1]).toEqual({
      expected_run_revision: 4,
      progress: expect.objectContaining({
        current_beat_id: "beat:hold-breach",
        current_scene_id: "scene:north-gate",
        resolved_beat_ids: ["beat:hold-breach"],
        selections: { "choice:keep": "option:keep", "choice:surviving-brood": "option:follow-brood" },
        notes_by_element_id: { "scene:north-gate": "keep me" },
      }),
    });
    expect(await screen.findByRole("radio", { name: "Follow it" })).toBeChecked();
    expect(screen.getByTestId("play-decision-consequence")).toHaveTextContent(
      "The party pursues the retreating creatures into the lower tunnels before reinforcements arrive.",
    );
    expect(screen.getByTestId("play-decision-relevance")).toHaveTextContent("Tunnel Pursuit — emphasized");
    expect(screen.getByTestId("play-decision-relevance")).toHaveTextContent("Lower Tunnels — emphasized");
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("North Gate");
    expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument();
  });

  it("does not show Follow as selected while the write is in flight", async () => {
    const user = userEvent.setup();
    let resolvePut: (run: PlayRunRecord) => void = () => undefined;
    vi.mocked(liveApi.putPlayRunProgress).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePut = resolve;
        }),
    );
    render(<BreachHarness />);
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    expect(await screen.findByTestId("play-saving")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
    expect(screen.queryByTestId("play-decision-consequence")).not.toBeInTheDocument();
    resolvePut(
      breachRun({
        run_revision: 5,
        progress: breachProgress({
          selections: { "choice:surviving-brood": "option:follow-brood" },
        }),
      }),
    );
    expect(await screen.findByRole("radio", { name: "Follow it" })).toBeChecked();
  });

  it("changes to Seal with one CAS and keeps Lower Tunnels as default", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(
      breachRun({
        run_revision: 6,
        progress: breachProgress({
          selections: { "choice:surviving-brood": "option:seal-breach" },
        }),
      }),
    );
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            selections: { "choice:surviving-brood": "option:follow-brood" },
          }),
        })}
      />,
    );
    expect(screen.getByRole("radio", { name: "Follow it" })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Seal the breach" }));
    await waitFor(() => expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1]).toEqual({
      expected_run_revision: 4,
      progress: expect.objectContaining({
        current_beat_id: "beat:hold-breach",
        current_scene_id: "scene:north-gate",
        selections: { "choice:surviving-brood": "option:seal-breach" },
      }),
    });
    expect(await screen.findByRole("radio", { name: "Seal the breach" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
    expect(screen.getByTestId("play-decision-consequence")).toHaveTextContent(
      "The immediate breach is contained, but the surviving creatures remain somewhere below.",
    );
    expect(screen.getByTestId("play-decision-relevance")).toHaveTextContent("Tunnel Pursuit — de-emphasized");
    expect(screen.getByTestId("play-decision-relevance")).toHaveTextContent("Lower Tunnels — default");
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("North Gate");
  });

  it("clears only this Decision key and removes consequence", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(
      breachRun({
        run_revision: 7,
        progress: breachProgress({
          selections: { "choice:keep": "option:keep" },
        }),
      }),
    );
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            selections: { "choice:keep": "option:keep", "choice:surviving-brood": "option:seal-breach" },
          }),
        })}
      />,
    );
    await user.click(screen.getByTestId("play-decision-clear"));
    await waitFor(() => expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1));
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1]).toEqual({
      expected_run_revision: 4,
      progress: expect.objectContaining({
        current_beat_id: "beat:hold-breach",
        current_scene_id: "scene:north-gate",
        selections: { "choice:keep": "option:keep" },
      }),
    });
    expect(await screen.findByRole("radio", { name: "Seal the breach" })).not.toBeChecked();
    expect(screen.queryByTestId("play-decision-consequence")).not.toBeInTheDocument();
    expect(screen.queryByTestId("play-decision-relevance")).not.toBeInTheDocument();
  });

  it("does not spend a second CAS when the selected Option is clicked again", async () => {
    const user = userEvent.setup();
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            selections: { "choice:surviving-brood": "option:follow-brood" },
          }),
        })}
      />,
    );
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("keeps a de-emphasized Tunnel Pursuit Inspectable and Make Current capable", async () => {
    const user = userEvent.setup();
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            selections: { "choice:surviving-brood": "option:seal-breach" },
          }),
        })}
      />,
    );
    const inspect = screen.getByRole("button", { name: /Tunnel Pursuit/ });
    expect(inspect).toBeEnabled();
    await user.click(inspect);
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent(/Viewing: .* · Tunnel Pursuit/);
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("North Gate");
    expect(screen.getByRole("button", { name: "Make Tunnel Pursuit current" })).toBeEnabled();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("returns from inspection to the authoritative North Gate Decision", async () => {
    const user = userEvent.setup();
    render(<BreachHarness />);
    await user.click(screen.getByRole("button", { name: /Tunnel Pursuit/ }));
    await user.click(screen.getByTestId("play-workspace-back"));
    expect(screen.getByTestId("play-workspace-current")).toContainElement(
      screen.getByTestId("play-decision"),
    );
    expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("collapses supporting chrome without writing Runtime or hiding the Scene Decision", async () => {
    const user = userEvent.setup();
    render(<BreachHarness />);
    await user.click(screen.getByTestId("play-beat-context-toggle"));
    await user.click(screen.getByTestId("play-at-a-glance-toggle"));
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-beat-collapsed", "true");
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-glance-collapsed", "true");
    expect(screen.getByTestId("play-workspace-current")).toContainElement(
      screen.getByTestId("play-decision"),
    );
    expect(screen.getByRole("radio", { name: "Follow it" })).toBeEnabled();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("restores selected Option and re-derived relevance from persisted Runtime", () => {
    render(
      <BreachHarness
        initialRun={breachRun({
          progress: breachProgress({
            selections: { "choice:surviving-brood": "option:follow-brood" },
          }),
        })}
      />,
    );
    expect(screen.getByRole("radio", { name: "Follow it" })).toBeChecked();
    expect(screen.getByTestId("play-decision-relevance")).toHaveTextContent("Tunnel Pursuit — emphasized");
    expect(screen.getByTestId("play-decision-relevance")).toHaveTextContent("Lower Tunnels — emphasized");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("exact-rereads a 409 Decision write and does not retry or claim the selection", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new LiveApiError("CAS conflict", 409));
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(breachRun({ run_revision: 9 }));
    render(<BreachHarness />);
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    expect(await screen.findByTestId("play-cas-conflict")).toBeInTheDocument();
    expect(screen.queryByTestId("play-progress-rejected")).not.toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
  });

  it("locks unknown when a 409 reread fails", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new LiveApiError("CAS conflict", 409));
    vi.mocked(liveApi.getPlayRun).mockRejectedValue(new Error("reread failed"));
    render(<BreachHarness />);
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    expect(await screen.findByTestId("play-unknown-outcome")).toHaveTextContent(
      "The exact Run could not be reloaded",
    );
    expect(screen.queryByTestId("play-cas-conflict")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-unknown-outcome")).not.toHaveTextContent("Reloaded the exact Run");
    expect(screen.getByRole("radio", { name: "Follow it" })).toBeDisabled();
  });

  it("exact-rereads a 422 Decision write as rejection, not conflict", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new LiveApiError("invalid option", 422));
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(breachRun({ run_revision: 4 }));
    render(<BreachHarness />);
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    expect(await screen.findByTestId("play-progress-rejected")).toHaveTextContent("Reloaded the exact Run");
    expect(screen.queryByTestId("play-cas-conflict")).not.toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Follow it" })).toBeEnabled();
  });

  it("does not claim reload when a 422 reread fails", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new LiveApiError("invalid option", 422));
    vi.mocked(liveApi.getPlayRun).mockRejectedValue(new Error("reread failed"));
    render(<BreachHarness />);
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    expect(await screen.findByTestId("play-unknown-outcome")).not.toHaveTextContent(
      "Reloaded the exact Run",
    );
    expect(screen.queryByTestId("play-progress-rejected")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Follow it" })).toBeDisabled();
  });

  it("exact-rereads an unknown Decision outcome and does not blind retry", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new Error("network down"));
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(breachRun());
    render(<BreachHarness />);
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    expect(await screen.findByTestId("play-unknown-outcome")).toHaveTextContent(
      "Reloaded the exact Run before further mutation",
    );
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
  });

  it("ignores a stale Decision write after the Run identity changes", async () => {
    const user = userEvent.setup();
    let resolvePut: (run: PlayRunRecord) => void = () => undefined;
    vi.mocked(liveApi.putPlayRunProgress).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePut = resolve;
        }),
    );
    const first = readyBreachDeck(breachRun());
    const second = readyBreachDeck(breachRun({
      run_id: OTHER_RUN_ID,
      progress: breachProgress({ current_scene_id: "scene:tunnel-pursuit" }),
    }));
    function SwitchHarness() {
      const [deck, setDeck] = useState(first);
      const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
      return (
        <>
          <button type="button" onClick={() => setDeck(second)}>Switch run</button>
          <PlayCurrentMomentCockpit
            deck={deck}
            mutationStatus={mutationStatus}
            onMutationStatus={setMutationStatus}
            onAuthoritativeRun={(run) =>
              setDeck((current) => overlayRuntimeOnV2Ready(current, run) ?? current)
            }
          />
        </>
      );
    }
    render(<SwitchHarness />);
    await user.click(screen.getByRole("radio", { name: "Follow it" }));
    await user.click(screen.getByRole("button", { name: "Switch run" }));
    resolvePut(
      breachRun({
        run_revision: 5,
        progress: breachProgress({
          selections: { "choice:surviving-brood": "option:follow-brood" },
        }),
      }),
    );
    expect(await screen.findByTestId("play-workspace-current")).toHaveTextContent("Tunnel Pursuit");
    expect(screen.queryByRole("radio", { name: "Follow it" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("play-decision-consequence")).not.toBeInTheDocument();
  });
});
