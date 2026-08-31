import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { LiveApiError } from "../../api/liveApi";
import type { PlayRunProgress, PlayRunRecord, PlayRunReferenceManifestV2 } from "../../api/types";
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

describe("PlayCurrentMomentCockpit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    expect(screen.queryByTestId("play-workspace-beat-only")).not.toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
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

  it("collapses At a Glance without writing progress", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const toggle = screen.getByTestId("play-at-a-glance-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-glance-collapsed", "true");
    expect(screen.getByTestId("play-cockpit-shell")).toHaveAttribute("data-beat-collapsed", "false");
    expect(screen.getByTestId("play-at-a-glance")).toHaveClass("is-collapsed");
    expect(screen.queryByTestId("play-at-a-glance-scenes")).not.toBeInTheDocument();
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

  it("opens the Scenes category in the central workspace without writing progress", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByTestId("play-at-a-glance-scenes")).toHaveTextContent("Scenes 3");
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    expect(screen.getByTestId("play-workspace-scenes")).toBeInTheDocument();
    expect(screen.getByTestId("play-scene-inventory")).toHaveTextContent("Tunnel Breach");
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
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    await user.click(screen.getByRole("button", { name: "Inspect Courtyard" }));
    expect(screen.getByTestId("play-workspace-inspect")).toBeInTheDocument();
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent("Inspecting: Courtyard");
    expect(screen.getByTestId("play-inspect-current")).toHaveTextContent("Current: Tunnel Breach");
    expect(screen.getByRole("heading", { name: "Inspecting Courtyard" })).toBeInTheDocument();
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Tunnel Breach");
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
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
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    await user.click(screen.getByRole("button", { name: "Inspect Courtyard" }));
    await user.click(screen.getByTestId("play-workspace-back"));
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
    expect(screen.queryByTestId("play-workspace-inspect")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("play-at-a-glance-scenes")).toHaveFocus();
    });
  });

  it("restores inspection focus to At a Glance when the Scenes launcher is unmounted", async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initialRun={runRecord({
          progress: progress({ current_scene_id: "scene:tunnel" }),
        })}
      />,
    );
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    await user.click(screen.getByRole("button", { name: "Inspect Courtyard" }));
    await user.click(screen.getByTestId("play-at-a-glance-toggle"));
    expect(screen.queryByTestId("play-at-a-glance-scenes")).not.toBeInTheDocument();
    await user.click(screen.getByTestId("play-workspace-back"));
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Tunnel unique body.");
    await waitFor(() => {
      expect(screen.getByTestId("play-at-a-glance-toggle")).toHaveFocus();
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
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    await user.click(screen.getByRole("button", { name: "Inspect Courtyard" }));
    await user.click(screen.getByRole("button", { name: "Make Courtyard current" }));
    expect(await screen.findByTestId("play-unknown-outcome")).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("Tunnel Breach");
    expect(screen.queryByRole("heading", { name: "Courtyard" })).not.toBeInTheDocument();
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent("Inspecting: Courtyard");
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
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    await user.click(screen.getByRole("button", { name: "Inspect Courtyard" }));
    await user.click(screen.getByRole("button", { name: "Simulate writer" }));
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent("Inspecting: Courtyard");
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
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    await user.click(screen.getByRole("button", { name: "Inspect North Gate" }));
    expect(screen.getByTestId("play-workspace-inspect")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Switch run" }));
    expect(screen.queryByTestId("play-workspace-inspect")).not.toBeInTheDocument();
    expect(screen.getByTestId("play-workspace-current")).toHaveTextContent("Courtyard unique body.");
  });

  it("shows a truthful empty Scene inventory", async () => {
    const user = userEvent.setup();
    render(<Harness markdown={EMPTY_BEAT_MARKDOWN} />);
    expect(screen.getByTestId("play-at-a-glance-scenes")).toHaveTextContent("Scenes 0");
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
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
    expect(screen.getByTestId("play-at-a-glance")).toHaveTextContent("Around this moment");
    expect(screen.getByTestId("play-at-a-glance-scenes")).toHaveTextContent("Scenes 2");
    expect(screen.getByRole("heading", { name: "North Gate" })).toBeInTheDocument();
    expect(screen.getByTestId("play-decision-prompt")).toHaveTextContent(
      "What do they do with the surviving brood?",
    );
    expect(screen.getByRole("radio", { name: "Follow it" })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Seal the breach" })).not.toBeChecked();
    expect(screen.queryByTestId("play-decision-consequence")).not.toBeInTheDocument();
    expect(screen.queryByTestId("play-decision-clear")).not.toBeInTheDocument();
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
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    const inventory = screen.getByTestId("play-scene-inventory").querySelector(
      '[data-scene-id="scene:tunnel-pursuit"]',
    );
    expect(inventory).toHaveTextContent("de-emphasized");
    const inspect = screen.getByRole("button", { name: "Inspect Tunnel Pursuit" });
    expect(inspect).toBeEnabled();
    await user.click(inspect);
    expect(screen.getByTestId("play-inspect-scene")).toHaveTextContent("Inspecting: Tunnel Pursuit");
    expect(screen.getByTestId("play-current-scene")).toHaveTextContent("North Gate");
    expect(screen.getByRole("button", { name: "Make Tunnel Pursuit current" })).toBeEnabled();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("returns from inspection to the authoritative North Gate Decision", async () => {
    const user = userEvent.setup();
    render(<BreachHarness />);
    await user.click(screen.getByTestId("play-at-a-glance-scenes"));
    await user.click(screen.getByRole("button", { name: "Inspect Tunnel Pursuit" }));
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
