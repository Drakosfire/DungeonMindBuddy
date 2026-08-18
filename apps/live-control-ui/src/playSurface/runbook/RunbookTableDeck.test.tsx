import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import { LiveApiError } from "../../api/liveApi";
import type { PlayRunProgress, PlayRunRecord } from "../../api/types";
import { admitNativeRunbook, overlayRuntimeOnDeck } from "./nativeRunbookProjection";
import { RunbookTableDeck, type RunbookMutationStatus } from "./RunbookTableDeck";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ARTIFACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const CONTENT_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

const MARKDOWN = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
  "## Gate",
  "",
  "Scene intro.",
  "",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:approach -->",
  "### Approach",
  "",
  "Approach body.",
  "",
  "<!-- dmb-playable-element:v1 kind=choice id=choice:enter -->",
  "### Enter?",
  "",
  "Choice body.",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:yes -->",
  "#### Yes",
  "",
  "Yes body.",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:no -->",
  "#### No",
  "",
  "No body.",
  "",
  "<!-- dmb-playable-element:v1 kind=beat id=beat:inside -->",
  "### Inside",
  "",
  "Inside body.",
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

function readyDeck(run: PlayRunRecord = runRecord()) {
  const admitted = admitNativeRunbook({
    run,
    manifest: {
      schema_version: "dmb_play_run_reference_manifest_v1",
      run_id: run.run_id,
      playable_artifact_id: run.playable_artifact_id,
      playable_revision: run.playable_revision,
      playable_content_sha256: run.playable_content_sha256,
      sealed_at: "2026-08-17T00:00:00Z",
      elements: [
        { kind: "beat", element_id: "beat:approach", scene_id: "scene:gate" },
        { kind: "beat", element_id: "beat:inside", scene_id: "scene:gate" },
        { kind: "choice", element_id: "choice:enter", scene_id: "scene:gate" },
        { kind: "option", element_id: "option:no", scene_id: "scene:gate", choice_id: "choice:enter" },
        { kind: "option", element_id: "option:yes", scene_id: "scene:gate", choice_id: "choice:enter" },
        { kind: "scene", element_id: "scene:gate" },
      ],
    },
    snapshot: {
      schema_version: "dmb_workspace_document_snapshot_v1",
        record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: run.playable_artifact_id,
        title: "North Gate Runbook",
        campaign_id: "longmont-c2",
        target_session: 23,
        kind: "runbook",
        target_relpath: "out/workspace/runbooks/north-gate.md",
        status: "active",
        content_status: "committed",
        revision: run.playable_revision,
        created_at: "2026-08-17T00:00:00Z",
        updated_at: "2026-08-17T00:00:00Z",
      },
      markdown: MARKDOWN,
      content_sha256: run.playable_content_sha256,
      file_fingerprint: "present",
      file_exists: true,
      loaded_revision: run.playable_revision,
    },
  });
  if (admitted.status !== "ready") throw new Error(`expected ready, got ${admitted.status}`);
  return admitted;
}

function Harness({
  initialRun = runRecord(),
}: {
  initialRun?: PlayRunRecord;
}) {
  const [deck, setDeck] = useState(() => readyDeck(initialRun));
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  return (
    <RunbookTableDeck
      deck={deck}
      mutationStatus={mutationStatus}
      onMutationStatus={setMutationStatus}
      onAuthoritativeRun={(run) =>
        setDeck((current) => overlayRuntimeOnDeck(current, run) ?? current)
      }
    />
  );
}

describe("RunbookTableDeck", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("previews the first Scene without writing current_scene_id", async () => {
    render(<Harness />);
    expect(screen.getByTestId("play-preview-flag")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Gate" })).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).not.toHaveBeenCalled();
  });

  it("marks a Beat resolved with the exact current run_revision", async () => {
    const user = userEvent.setup();
    const updated = runRecord({
      run_revision: 5,
      progress: progress({ resolved_beat_ids: ["beat:approach"] }),
    });
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(updated);
    render(<Harness />);

    await user.click(screen.getByRole("checkbox", { name: "Resolved" }));

    await waitFor(() => {
      expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[0]).toBe(RUN_ID);
    expect(vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1]).toEqual({
      expected_run_revision: 4,
      progress: expect.objectContaining({
        resolved_beat_ids: ["beat:approach"],
        current_scene_id: null,
      }),
    });
  });

  it("changes only the named Choice selection", async () => {
    const user = userEvent.setup();
    const initial = runRecord({
      progress: progress({
        selections: { "choice:enter": "option:no" },
        notes_by_element_id: { "beat:approach": "keep me" },
      }),
    });
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(
      runRecord({
        run_revision: 5,
        progress: progress({
          selections: { "choice:enter": "option:yes" },
          notes_by_element_id: { "beat:approach": "keep me" },
        }),
      }),
    );
    render(<Harness initialRun={initial} />);

    await user.click(screen.getByRole("radio", { name: "Yes" }));
    await waitFor(() => expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1));
    const body = vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1];
    expect(body?.progress.selections).toEqual({ "choice:enter": "option:yes" });
    expect(body?.progress.notes_by_element_id).toEqual({ "beat:approach": "keep me" });
  });

  it("changes only the named element note", async () => {
    const user = userEvent.setup();
    const initial = runRecord({
      progress: progress({
        selections: { "choice:enter": "option:yes" },
        notes_by_element_id: { "beat:approach": "old", "scene:gate": "scene note" },
      }),
    });
    vi.mocked(liveApi.putPlayRunProgress).mockResolvedValue(
      runRecord({
        run_revision: 5,
        progress: progress({
          selections: { "choice:enter": "option:yes" },
          notes_by_element_id: { "beat:approach": "new note", "scene:gate": "scene note" },
        }),
      }),
    );
    render(<Harness initialRun={initial} />);

    const note = screen.getByLabelText("Note");
    await user.clear(note);
    await user.type(note, "new note");
    await user.click(screen.getByRole("button", { name: "Save note" }));

    await waitFor(() => expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1));
    const body = vi.mocked(liveApi.putPlayRunProgress).mock.calls[0]?.[1];
    expect(body?.progress.notes_by_element_id).toEqual({
      "beat:approach": "new note",
      "scene:gate": "scene note",
    });
    expect(body?.progress.selections).toEqual({ "choice:enter": "option:yes" });
  });

  it("does not silently retry or merge on CAS 409", async () => {
    const user = userEvent.setup();
    const serverRun = runRecord({
      run_revision: 9,
      progress: progress({ resolved_beat_ids: ["beat:inside"] }),
    });
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new LiveApiError("CAS conflict", 409));
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(serverRun);
    render(<Harness />);

    await user.click(screen.getByRole("checkbox", { name: "Resolved" }));

    expect(await screen.findByTestId("play-cas-conflict")).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.queryByRole("checkbox", { name: "Resolved" })).not.toBeInTheDocument();
    expect(screen.getByText(/Reloaded the exact Run/i)).toBeInTheDocument();
  });

  it("reconciles an unknown mutation outcome by reloading the exact Run", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.putPlayRunProgress).mockRejectedValue(new Error("network down"));
    vi.mocked(liveApi.getPlayRun).mockResolvedValue(
      runRecord({ run_revision: 4, progress: progress() }),
    );
    render(<Harness />);

    await user.click(screen.getByRole("checkbox", { name: "Resolved" }));

    expect(await screen.findByTestId("play-unknown-outcome")).toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
    expect(liveApi.getPlayRun).toHaveBeenCalledWith(RUN_ID);
    expect(screen.queryByRole("checkbox", { name: "Resolved" })).not.toBeInTheDocument();
  });

  it("discards a stale mutation completion after the Run identity changes", async () => {
    const user = userEvent.setup();
    let resolvePut: (run: PlayRunRecord) => void = () => undefined;
    vi.mocked(liveApi.putPlayRunProgress).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePut = resolve;
        }),
    );
    const { unmount } = render(<Harness />);
    await user.click(screen.getByRole("checkbox", { name: "Resolved" }));
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);

    unmount();
    render(
      <Harness
        initialRun={runRecord({
          run_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          progress: progress({ current_scene_id: "scene:gate", current_beat_id: "beat:inside" }),
        })}
      />,
    );

    resolvePut(
      runRecord({
        run_revision: 5,
        progress: progress({ resolved_beat_ids: ["beat:approach"] }),
      }),
    );

    expect(await screen.findByRole("button", { name: /Inside/ })).toBeInTheDocument();
    expect(screen.queryByTestId("play-cas-conflict")).not.toBeInTheDocument();
    expect(liveApi.putPlayRunProgress).toHaveBeenCalledTimes(1);
  });
});
