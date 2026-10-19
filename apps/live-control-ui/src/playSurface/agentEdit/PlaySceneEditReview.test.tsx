import { render, screen, fireEvent } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { usePlaySceneEdits } from "./PlaySceneEditReview";
import { listPlaySceneEdits, proposePlaySceneEdit, type PlaySceneEditRecord } from "../../api/playSceneEditApi";
vi.mock("../../api/playSceneEditApi", () => ({ listPlaySceneEdits: vi.fn(), proposePlaySceneEdit: vi.fn() }));
const record: PlaySceneEditRecord = { schema_version: "dmb_play_scene_edit_proposal_v1", world_id: "world", run_id: "run", proposal_id: "proposal", instruction: "Keep this proposal", status: "ready", failure_code: null, created_at: "", updated_at: "", basis: { run_revision: 2, scene_id: "scene:gate", content_basis: { edition_revision: 0, edition_revision_id: null, content_sha256: "a".repeat(64) }, origin: { playable_artifact_id: "origin", playable_revision: 1, playable_work_revision_id: "revision", playable_content_sha256: "a".repeat(64) }, scene_note_sha256: null }, result: { schema_version: "dmb_play_scene_edit_result_v1", before_markdown: "Before", replacement_markdown: "After", candidate_markdown: "After", candidate_sha256: "b".repeat(64), body_start_utf8: 0, body_end_utf8: 6, summary: "Historical scene edit", assumptions: [], model: "test", model_observed: true, model_latency_ms: 1, wall_latency_ms: 1 } };
function Harness() { return usePlaySceneEdits({ worldId: "world", runId: "run", bridge: null }).review; }
it("reopens inert reviews and checks pending outcomes using GET only", async () => {
  vi.mocked(listPlaySceneEdits).mockResolvedValue([{ ...record, status: "pending", result: null }]);
  const first = render(<Harness />);
  expect(await screen.findByText(/Generation has not confirmed/)).toBeInTheDocument();
  vi.mocked(listPlaySceneEdits).mockResolvedValue([record]);
  fireEvent.click(screen.getByRole("button", { name: "Refresh scene proposals" }));
  expect(await screen.findByText("Historical scene edit")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Apply to session copy" })).toBeDisabled();
  first.unmount();
  render(<Harness />);
  expect(await screen.findByText("Historical scene edit")).toBeInTheDocument();
  expect(proposePlaySceneEdit).not.toHaveBeenCalled();
});
