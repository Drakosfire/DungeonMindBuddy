import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { PlayRunReferenceManifestV2, WorldPlayRunRecordV2 } from "../api/types";
import { WorldPlanCardProjection } from "../planSurface/components/WorldPlanCardProjection";
import { PlayCurrentMomentCockpit } from "../playSurface/currentMoment/PlayCurrentMomentCockpit";
import { admitNativeRunbook, overlayRuntimeOnV2Ready } from "../playSurface/runbook/nativeRunbookProjection";
import type { RunbookMutationStatus } from "../playSurface/runbook/RunbookTableDeck";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";

vi.mock("../api/liveApi", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/liveApi")>(),
  putWorldPlayRunProgress: vi.fn(),
  getWorldPlayRun: vi.fn(),
}));

const fixtureNames = ["Conks", "Sheep", "Session29"] as const;
const sha = "a".repeat(64);
const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const documentId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function fixture(name: typeof fixtureNames[number]) {
  const longTitle = name === "Sheep" ? `The ${"very long winding corridor ".repeat(8)}of Sheep` : `${name} opening`;
  const markdown = [
    "<!-- dmb-playable-element:v2 kind=beat id=beat:one beat_kind=spine -->",
    `## ${name} beat`,
    "The party must choose a path.",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:one -->",
    `### ${longTitle}`,
    `${name} authored opening body.`,
    "<!-- dmb-playable-element:v2 kind=choice id=choice:one scene=scene:one -->",
    `### ${name} opening decision?`,
    `${name} choice framing.`,
    "<!-- dmb-playable-element:v2 kind=option id=option:go -->",
    "- Go ahead",
    "  Enter the next chamber.",
    "<!-- dmb-playable-element:v2 kind=option id=option:stay -->",
    "- Stay here",
    "  Wait by the door.",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:two -->",
    `### ${name} second scene`,
    `${name} authored second body.`,
    "<!-- dmb-playable-element:v2 kind=choice id=choice:two scene=scene:two -->",
    `### ${name} second decision?`,
    `${name} second framing.`,
    "<!-- dmb-playable-element:v2 kind=option id=option:leave -->",
    "- Leave now",
    "  Walk out.",
  ].join("\n") + "\n";
  const run: WorldPlayRunRecordV2 = {
    schema_version: "dmb_world_play_run_record_v2", run_id: runId, world_id: "fixture-world",
    playable_artifact_id: documentId, playable_revision: 9,
    playable_work_revision_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    playable_content_sha256: sha, run_revision: 4,
    created_at: "2026-09-30T00:00:00Z", updated_at: "2026-09-30T00:00:00Z",
    progress: { current_beat_id: "beat:one", current_scene_id: "scene:one",
      resolved_beat_ids: ["beat:one"], selections: { "choice:one": "option:go" },
      notes_by_element_id: { "scene:one": "Opening note", "scene:two": "Second scene note" } },
  };
  const manifest: PlayRunReferenceManifestV2 = {
    schema_version: "dmb_play_run_reference_manifest_v2", run_id: runId,
    playable_artifact_id: documentId, playable_revision: 9, playable_content_sha256: sha,
    sealed_at: run.created_at, beats: [{ beat_id: "beat:one", beat_kind: "spine" }],
    scenes: [{ scene_id: "scene:one", beat_id: "beat:one" }, { scene_id: "scene:two", beat_id: "beat:one" }],
    choices: [{ choice_id: "choice:one", beat_id: "beat:one", scene_id: "scene:one" },
      { choice_id: "choice:two", beat_id: "beat:one", scene_id: "scene:two" }],
    options: [{ option_id: "option:go", choice_id: "choice:one" },
      { option_id: "option:stay", choice_id: "choice:one" },
      { option_id: "option:leave", choice_id: "choice:two" }], edges: [],
  };
  return { name, longTitle, markdown, run, manifest };
}

function PlayFixture({ data }: { data: ReturnType<typeof fixture> }) {
  const [deck, setDeck] = useState(() => {
    const admitted = admitNativeRunbook({ run: data.run, manifest: data.manifest, committed: {
      schema_version: "dmb_workspace_committed_revision_v2", scope_mode: "world", world_id: data.run.world_id,
      document_id: documentId, kind: "runbook", campaign_id: null, title: data.name,
      status: "active", object_revision: 9, work_revision_id: data.run.playable_work_revision_id,
      revision_n: 9, markdown: data.markdown, content_sha256: sha,
      has_divergent_working_copy: false, target_relpath: null,
    } });
    if (admitted.status !== "ready" || admitted.grammar !== "v2") throw new Error(`Fixture not ready: ${admitted.status}`);
    return admitted;
  });
  const [mutationStatus, setMutationStatus] = useState<RunbookMutationStatus>("idle");
  return <PlayCurrentMomentCockpit deck={deck} mutationStatus={mutationStatus}
    onMutationStatus={setMutationStatus}
    onAuthoritativeRun={(run) => setDeck((current) => overlayRuntimeOnV2Ready(current, run) ?? current)} />;
}

afterEach(() => { vi.clearAllMocks(); });

it.each(fixtureNames)("shows the %s Scene and its Choices through Plan focus and Play current/inspection", async (name) => {
  const data = fixture(name);
  const imported = markdownToTiptapDoc(data.markdown);
  expect(imported.diagnostics).toEqual([]);
  const plan = render(<div style={{ width: 320 }}><WorldPlanCardProjection
    worldId={data.run.world_id} documentId={documentId} document={imported.doc}
    markdown={data.markdown} sourceWarnings={[]} basis={{ status: "verified", revision: 9, contentSha256: sha }}
    isDirty={false} onReturnToDocument={() => {}} /></div>);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: `Open scene: ${data.longTitle}` }));
  const planCard = screen.getByTestId("world-plan-scene-reader").querySelector<HTMLElement>("[data-scene-card]");
  expect(planCard).toHaveAttribute("data-scene-id", "scene:one");
  expect(planCard).toHaveAttribute("data-content-sha256", sha);
  expect(planCard).toHaveTextContent(data.longTitle);
  expect(planCard).toHaveTextContent(`${name} authored opening body.`);
  expect(planCard).toHaveTextContent(`${name} opening decision?`);
  expect(planCard).toHaveTextContent("Go ahead");
  plan.unmount();

  render(<div style={{ width: 320 }}><PlayFixture data={data} /></div>);
  const current = screen.getByTestId("play-workspace-current");
  const currentCard = current.querySelector<HTMLElement>("[data-scene-card]");
  expect(currentCard).toHaveAttribute("data-scene-id", "scene:one");
  expect(currentCard).toHaveAttribute("data-work-revision-id", data.run.playable_work_revision_id);
  for (const text of [data.longTitle, `${name} authored opening body.`, `${name} opening decision?`, "Go ahead"]) {
    expect(currentCard).toHaveTextContent(text);
  }
  expect(within(current).getByRole("radio", { name: /Go ahead/ })).toBeChecked();

  const secondOutlineScene = screen.getAllByTestId("play-outline-scene")
    .find((button) => button.getAttribute("data-scene-id") === "scene:two");
  expect(secondOutlineScene).toBeDefined();
  await user.click(secondOutlineScene!);
  const inspected = screen.getByTestId("play-workspace-inspect");
  expect(inspected.querySelector("[data-scene-card]")).toHaveAttribute("data-scene-id", "scene:two");
  expect(inspected).toHaveTextContent(`${name} second decision?`);
  expect(inspected).toHaveTextContent("Leave now");
  expect(inspected).toHaveTextContent("Second scene note");
  expect(within(inspected).queryByRole("textbox")).not.toBeInTheDocument();
  expect(liveApi.putWorldPlayRunProgress).not.toHaveBeenCalled();
});

it("keeps Session29 inspection read-only until Make Current sends the exact Run CAS", async () => {
  const data = fixture("Session29");
  vi.mocked(liveApi.putWorldPlayRunProgress).mockResolvedValue({
    ...data.run, run_revision: 5,
    progress: { ...data.run.progress, current_scene_id: "scene:two" },
  });
  const user = userEvent.setup();
  render(<PlayFixture data={data} />);
  const secondOutlineScene = screen.getAllByTestId("play-outline-scene")
    .find((button) => button.getAttribute("data-scene-id") === "scene:two");
  await user.click(secondOutlineScene!);
  expect(liveApi.putWorldPlayRunProgress).not.toHaveBeenCalled();
  await user.click(screen.getByTestId("play-make-current"));
  await waitFor(() => expect(liveApi.putWorldPlayRunProgress).toHaveBeenCalledTimes(1));
  expect(vi.mocked(liveApi.putWorldPlayRunProgress).mock.calls[0]).toEqual([runId, data.run.world_id, {
    expected_run_revision: 4,
    progress: { ...data.run.progress, current_beat_id: "beat:one", current_scene_id: "scene:two" },
  }]);
});
