import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import * as api from "../api/nativeRecapSourceApi";
import type { NativeRecapSourceStatus } from "../api/nativeRecapSourceApi";
import type { SavedRecapSource } from "../api/savedRecapRunsApi";
import { RecapSourceAdmission } from "./RecapSourceAdmission";
function source(world = "world-a"): SavedRecapSource {
  return { schema: "dmb_saved_recap_source_v1", managedWorldId: world, nativeWorldId: `native:${world}`, bindingVersion: 3,
    run: { runId: "extraction-a", runRevision: 5, runStatus: "reviewable", sourceArtifactId: "artifact:a", campaignId: "campaign-a", sessionId: "session-8", profileId: "recap", createdAt: null, updatedAt: null, sourceRevisionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sourceSha256: "a".repeat(64), unavailableReason: null }, sourceProse: "Exact saved prose." };
}
function status(state: NativeRecapSourceStatus["state"] = "admitted"): NativeRecapSourceStatus {
  const t = api.recapSourceTarget(source())!;
  return { schema_version: "dmb_native_recap_source_status_v2", state, run_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", run_revision: 4, managed_world_id: t.managedWorldId, native_world_id: t.nativeWorldId, binding_version: 3, campaign_id: t.campaignId, session_id: "session-8", app_source_artifact_id: t.sourceArtifactId, app_source_revision_id: t.sourceRevisionId, app_body_sha256: t.contentSha256, admission_id: "admission-a", admission_committed: state === "admitted", command_sha256: "b".repeat(64), published_revision_id: state === "admitted" ? "rev:a" : null, evidence_ref_id: state === "admitted" ? "evidence:a" : null, opening: { state: state === "admitted" ? "verified" : "not_checked" }, failure_code: null };
}
function deferred<T>() { let resolve!: (v: T) => void, reject!: (v: Error) => void; const promise = new Promise<T>((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
afterEach(() => vi.restoreAllMocks());
it("admits only on explicit action and never accepts extracted facts", async () => {
  const admit = vi.spyOn(api, "admitRecapSource").mockResolvedValue(status());
  render(<RecapSourceAdmission source={source()}/>);
  expect(admit).not.toHaveBeenCalled();
  expect(screen.getByText(/facts still need separate review and publication/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true }));
  expect(await screen.findByText("Source available as evidence.")).toBeInTheDocument();
  expect(admit).toHaveBeenCalledExactlyOnceWith(api.recapSourceTarget(source()));
});
it("keeps missing source UUID unavailable without sending anything", () => {
  const s = source(); s.run.sourceRevisionId = s.run.sourceSha256;
  const admit = vi.spyOn(api, "admitRecapSource"); render(<RecapSourceAdmission source={s}/>);
  expect(screen.getByText(/needs an exact revision and matching scope/)).toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument(); expect(admit).not.toHaveBeenCalled();
});
it("recovers the identical original source after a lost response and never auto retries", async () => {
  const admit = vi.spyOn(api, "admitRecapSource").mockRejectedValueOnce(new Error("Response lost")).mockResolvedValueOnce(status());
  render(<RecapSourceAdmission source={source()}/>);
  fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Response lost"); expect(admit).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: "Recover source admission" }));
  expect(await screen.findByText("Source available as evidence.")).toBeInTheDocument();
  expect(admit.mock.calls[0][0]).toEqual(admit.mock.calls[1][0]);
});
it("reopens the same server-owned request after unmount without adding browser storage", async () => {
  const admit = vi.spyOn(api, "admitRecapSource").mockRejectedValueOnce(new Error("Response lost")).mockResolvedValueOnce(status());
  const storage = vi.spyOn(Storage.prototype, "setItem");
  const view = render(<RecapSourceAdmission source={source()}/>);
  fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true })); await screen.findByRole("alert"); view.unmount();
  render(<RecapSourceAdmission source={source()}/>);
  expect(admit).toHaveBeenCalledOnce(); fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true }));
  await screen.findByText("Source available as evidence."); expect(admit.mock.calls[0][0]).toEqual(admit.mock.calls[1][0]); expect(storage).not.toHaveBeenCalled();
});
it.each(["reserved", "unknown", "conflict"] as const)("shows %s and resumes only with an explicit exact operation", async state => {
  const original = status(state);
  vi.spyOn(api, "admitRecapSource").mockResolvedValue(original);
  const inspect = vi.spyOn(api, "inspectRecapSource").mockResolvedValue(original);
  const resume = vi.spyOn(api, "resumeRecapSource").mockResolvedValue(status());
  render(<RecapSourceAdmission source={source()}/>); fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true }));
  await screen.findByRole("button", { name: "Resume exact source admission" }); expect(inspect).not.toHaveBeenCalled(); expect(resume).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Refresh source admission" })); await screen.findByRole("button", { name: "Resume exact source admission" });
  expect(inspect).toHaveBeenCalledExactlyOnceWith(api.recapSourceTarget(source()), original);
  fireEvent.click(screen.getByRole("button", { name: "Resume exact source admission" })); await screen.findByText("Source available as evidence.");
  expect(resume).toHaveBeenCalledExactlyOnceWith(api.recapSourceTarget(source()), original);
});
it("reports a committed source with an unavailable opening without resubmitting or claiming verified availability", async () => {
  const s: NativeRecapSourceStatus = { ...status(), state: "unavailable", opening: { state: "unavailable" }, failure_code: "native_recap_opening_unavailable" };
  vi.spyOn(api, "admitRecapSource").mockResolvedValue(s);
  const inspect = vi.spyOn(api, "inspectRecapSource").mockResolvedValue(status());
  render(<RecapSourceAdmission source={source()}/>); fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true }));
  expect(await screen.findByText(/committed; its opening is not verified/)).toBeInTheDocument();
  expect(screen.queryByText("Source available as evidence.")).not.toBeInTheDocument(); expect(screen.queryByRole("button", { name: /Resume/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Refresh source admission" })); await screen.findByText("Source available as evidence."); expect(inspect).toHaveBeenCalledOnce();
});
it("does not retain a verified badge after a later status transport failure", async () => {
  vi.spyOn(api, "admitRecapSource").mockResolvedValue(status());
  vi.spyOn(api, "inspectRecapSource").mockRejectedValue(new Error("Authority unavailable"));
  render(<RecapSourceAdmission source={source()}/>); fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true })); await screen.findByText("Source available as evidence.");
  fireEvent.click(screen.getByRole("button", { name: "Refresh source admission" })); await screen.findByRole("alert");
  expect(screen.queryByText("Source available as evidence.")).not.toBeInTheDocument(); expect(screen.queryByRole("button", { name: /Resume/ })).not.toBeInTheDocument();
});
it.each(["resolve", "reject"] as const)("drops an old A response across World A→B→A: %s", async outcome => {
  const old = deferred<NativeRecapSourceStatus>(); const admit = vi.spyOn(api, "admitRecapSource").mockReturnValue(old.promise);
  const view = render(<RecapSourceAdmission source={source()}/>); fireEvent.click(screen.getByRole("button", { name: "Admit source", exact: true }));
  view.rerender(<RecapSourceAdmission source={source("world-b")}/>); view.rerender(<RecapSourceAdmission source={source()}/>);
  await act(async () => { if (outcome === "resolve") old.resolve(status()); else old.reject(new Error("Old A failure")); });
  expect(screen.queryByText("Source available as evidence.")).not.toBeInTheDocument(); expect(screen.queryByText("Old A failure")).not.toBeInTheDocument(); expect(admit).toHaveBeenCalledOnce();
  expect(screen.getByRole("button", { name: "Admit source", exact: true })).toBeEnabled();
});
it("prevents a repeated click dispatch while one request is pending", async () => {
  const pending = deferred<NativeRecapSourceStatus>(); const admit = vi.spyOn(api, "admitRecapSource").mockReturnValue(pending.promise);
  render(<RecapSourceAdmission source={source()}/>); const button = screen.getByRole("button", { name: "Admit source", exact: true }); fireEvent.click(button); fireEvent.click(button);
  expect(admit).toHaveBeenCalledOnce(); await act(async () => pending.resolve(status()));
});
