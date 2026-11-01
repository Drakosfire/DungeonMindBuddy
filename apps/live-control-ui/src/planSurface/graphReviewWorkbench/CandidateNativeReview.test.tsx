import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CandidateNativeReview } from "./CandidateNativeReview";
import { getRecapNativeReview, type RecapNativeReview } from "../../api/recapNativeReviewApi";
import type { ExactRunCandidateProjection } from "../../api/exactRunCandidateProjectionApi";
vi.mock("../../api/recapNativeReviewApi", () => ({ getRecapNativeReview: vi.fn() }));
const inspect = vi.mocked(getRecapNativeReview);
function projection(): ExactRunCandidateProjection { return { runId: "run-a", runRevision: 5, runStatus: "reviewable", sourceArtifactId: "artifact:a", sourceSha256: "sha256:a", candidateSha256: "sha256:b", spanIndexSha256: "sha256:c", managedWorldId: "world-a", nativeWorldId: "native-a", bindingVersion: 3, campaignId: "campaign-a", sessionId: "session-8" } as ExactRunCandidateProjection; }
function reply(): RecapNativeReview { return { source_revision_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", native_context: { revision_id: "rev:current", source_authority_epoch: 23,
  domain_contract_ref: { domain_id: "world", domain_revision: "2", descriptor_sha256: "d".repeat(64) }, semantic_profile_ref: { profile_id: "game", profile_revision: "1", descriptor_sha256: "e".repeat(64) },
  source_admission: { state: "admitted", run_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", run_revision: 4, opening_state: "verified", failure_code: null },
  source_evidence: [{ evidence_ref_id: "ev:one", evidence_role: "support", opening: { status: "available", source_artifact_id: "src:one", source_revision_id: "srev:one", body_sha256: "a".repeat(64), span_start_byte: 0, span_end_byte: 7, span_text: "Exact source passage." } }],
  selections: [{ candidate_node_id: "ari", status: "ambiguous", search_is_advisory: true, alternatives: [{ entity_id: "ent:ari", identity_approved: false, status: "supported_facts" }] }],
} }; }
beforeEach(() => { inspect.mockReset(); inspect.mockResolvedValue(reply()); });
afterEach(cleanup);
it("reads only on explicit click, locks duplicate clicks and displays passages without approval", async () => {
  let finish!: (value: RecapNativeReview) => void; inspect.mockReturnValue(new Promise(resolve => { finish = resolve; }));
  render(<CandidateNativeReview projection={projection()} nodeId="ari"/>);
  expect(inspect).not.toHaveBeenCalled();
  const button = screen.getByRole("button", { name: "Compare with World" }); fireEvent.mouseEnter(button); fireEvent.focus(button);
  expect(inspect).not.toHaveBeenCalled(); fireEvent.click(button); fireEvent.click(button);
  expect(inspect).toHaveBeenCalledOnce(); expect(button).toBeDisabled();
  await act(async () => { finish(reply()); });
  expect(screen.getByText("Exact source passage.")).toBeInTheDocument();
  expect(screen.getByText(/does not approve claims/)).toBeInTheDocument();
  expect(screen.getByText(/other sources are not support/)).toBeInTheDocument();
  expect(screen.getByText("ent:ari · needs review")).toBeInTheDocument();
});
it.each(["not_found", "unavailable", "empty", "span_unavailable"])("explains %s without approval", async state => {
  const data = reply();
  if (state === "not_found") { data.native_context.source_admission = { state: "not_found" }; data.native_context.source_evidence = []; }
  if (state === "unavailable") { data.native_context.source_admission = { ...data.native_context.source_admission, state: "unavailable", run_id: "run", run_revision: 4, opening_state: "unavailable", failure_code: "unavailable" }; data.native_context.source_evidence = []; }
  if (state === "empty") data.native_context.source_evidence = [];
  if (state === "span_unavailable") data.native_context.source_evidence[0].opening = { status: "unavailable" };
  inspect.mockResolvedValue(data); render(<CandidateNativeReview projection={projection()} nodeId="ari"/>); fireEvent.click(screen.getByRole("button", { name: "Compare with World" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Refresh comparison" })).toBeEnabled());
  const phrase = state === "not_found" ? /not available for comparison yet/ : state === "unavailable" ? /availability is not verified/ : state === "empty" ? /No support passages/ : /could not be opened/;
  expect(screen.getByText(phrase)).toBeInTheDocument(); expect(screen.queryByText("Exact source passage.")).toBeNull();
});
it("clears current comparison if explicit refresh fails", async () => {
  render(<CandidateNativeReview projection={projection()} nodeId="ari"/>); fireEvent.click(screen.getByRole("button", { name: "Compare with World" }));
  await screen.findByText("Exact source passage."); inspect.mockRejectedValueOnce(new Error("World changed. Reload saved work."));
  fireEvent.click(screen.getByRole("button", { name: "Refresh comparison" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("World changed"); expect(screen.queryByText("Exact source passage.")).toBeNull();
});
it.each(["runId", "runRevision", "sourceArtifactId", "sourceSha256", "candidateSha256", "spanIndexSha256", "managedWorldId", "nativeWorldId", "bindingVersion", "campaignId", "sessionId"])("discards late response after %s A-B-A", async field => {
  const p = projection(); let finish!: (value: RecapNativeReview) => void; inspect.mockReturnValueOnce(new Promise(resolve => { finish = resolve; }));
  const ui = render(<CandidateNativeReview projection={p} nodeId="ari"/>); fireEvent.click(screen.getByRole("button", { name: "Compare with World" }));
  const changed = { ...p, [field]: typeof p[field as keyof ExactRunCandidateProjection] === "number" ? 9 : "other" };
  ui.rerender(<CandidateNativeReview projection={changed} nodeId="ari"/>); ui.rerender(<CandidateNativeReview projection={p} nodeId="ari"/>);
  await act(async () => { finish(reply()); });
  expect(screen.queryByText("Exact source passage.")).toBeNull(); expect(screen.getByRole("button", { name: "Compare with World" })).toBeEnabled(); expect(inspect).toHaveBeenCalledOnce();
});
it("discards late responses after changing node or unmount", async () => {
  let finish!: (value: RecapNativeReview) => void; inspect.mockReturnValueOnce(new Promise(resolve => { finish = resolve; }));
  const ui = render(<CandidateNativeReview projection={projection()} nodeId="ari"/>); fireEvent.click(screen.getByRole("button", { name: "Compare with World" }));
  ui.rerender(<CandidateNativeReview projection={projection()} nodeId="other"/>); ui.unmount(); await act(async () => { finish(reply()); }); expect(screen.queryByText("Exact source passage.")).toBeNull();
});
it("explains a promoted extraction without a read action", () => {
  render(<CandidateNativeReview projection={{ ...projection(), runStatus: "promoted" }} nodeId="ari"/>);
  expect(screen.getByText(/This saved extraction is promoted/)).toBeInTheDocument(); expect(screen.queryByRole("button")).toBeNull(); expect(inspect).not.toHaveBeenCalled();
});
