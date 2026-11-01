import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import * as savedApi from "../api/savedRecapRunsApi";
import type { SavedRecapRun, SavedRecapRuns, SavedRecapSource } from "../api/savedRecapRunsApi";
import * as rawApi from "../api/recapIngestApi";
import * as admissionApi from "../api/nativeRecapSourceApi";
import * as liveApi from "../api/liveApi";
import { IngestionModule } from "./IngestionModule";
import type { RecapIngestStatus } from "../api/types";
vi.mock("../chrome/NativeGraphAccessControl", () => ({ NativeGraphAccessControl: ({ onChanged }: {
        onChanged: (available: boolean) => void;
    }) => <><button onClick={() => onChanged(false)}>Disconnect fixture access</button><button onClick={() => onChanged(true)}>Reconnect fixture access</button></> }));
vi.mock("../playSurface/review/SessionEvidencePicker", () => ({ SessionEvidencePicker: () => null }));
function row(runId = "run-a", runStatus = "reviewable", sessionId = "session-8"): SavedRecapRun { return { runId, runRevision: 5, runStatus, sourceArtifactId: `artifact:${runId}`, campaignId: "longmont-c1", sessionId, profileId: "recap_category_v2@2.0", createdAt: null, updatedAt: null, sourceRevisionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sourceSha256: "a".repeat(64), unavailableReason: null }; }
function scope(runs = [row()], managedWorldId = "elderwyld"): SavedRecapRuns { return { schema: "dmb_saved_recap_runs_v1", managedWorldId, nativeWorldId: managedWorldId, bindingVersion: 3, runs }; }
function source(s: SavedRecapRuns, r: SavedRecapRun, text = `Source for ${r.runId}.`): SavedRecapSource { return { schema: "dmb_saved_recap_source_v1", managedWorldId: s.managedWorldId, nativeWorldId: s.nativeWorldId, bindingVersion: s.bindingVersion, run: r, sourceProse: text }; }
function deferred<T>() { let resolve!: (value: T) => void; let reject!: (error: Error) => void; const promise = new Promise<T>((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
function mount(query = "", world = "elderwyld") { window.history.replaceState({}, "", `/ingest?world=${world}&campaign=longmont-c1&session=session-8${query}`); return render(<IngestionModule campaignId="longmont-c1" session={30} managedWorldId={world} initialSourceSession={8}/>); }
async function open(runId: string) { const user = userEvent.setup({ delay: null }); await user.selectOptions(await screen.findByLabelText("Saved extraction work"), runId); await user.click(screen.getByRole("button", { name: "Open saved extraction" })); }
beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    vi.spyOn(savedApi, "getSavedRecapRuns").mockResolvedValue(scope());
    vi.spyOn(savedApi, "getSavedRecapSource").mockImplementation(async (s, r) => source(s, r));
    vi.spyOn(rawApi, "postRecapIngest").mockImplementation(async (request) => ({ schema: "dmb_raw_recap_ingest_status_v1", campaign_id: request.campaign_id, session: request.session, status: "initialized", states: ["ingest_status_inspected"], paths: {}, authority: {}, warnings: [], errors: [], next_actions: [], ingest_report: {}, entity_spelling_audit: [] } as RecapIngestStatus));
    vi.spyOn(liveApi, "getRecapArtifacts").mockRejectedValue(new Error("File artifact discovery must not run"));
});
afterEach(() => vi.restoreAllMocks());
it("offers distinct same-session attempts and opens only the selected run without file inspection or Process", async () => {
    vi.mocked(savedApi.getSavedRecapRuns).mockResolvedValue(scope([row("older"), row("newer", "failed")]));
    mount();
    await waitFor(() => expect(screen.getByRole("option", { name: /newer/ })).toBeInTheDocument());
    expect(screen.getByLabelText("Saved extraction work")).toHaveValue("");
    const baseline = vi.mocked(rawApi.postRecapIngest).mock.calls.length;
    await open("newer");
    expect(await screen.findByText("Source for newer.")).toBeInTheDocument();
    expect(savedApi.getSavedRecapSource).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ runId: "newer", runStatus: "failed" }));
    expect(vi.mocked(rawApi.postRecapIngest).mock.calls).toHaveLength(baseline);
    expect(liveApi.getRecapArtifacts).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Process recap" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View extracted candidates" })).toBeDisabled();
    expect(new URLSearchParams(window.location.search).get("recapReviewRunId")).toBe("newer");
});
it("reloads an exact route from the catalog without inspecting files", async () => {
    mount("&view=recap&recapReviewRunId=run-a");
    expect(await screen.findByText("Source for run-a.")).toBeInTheDocument();
    expect(rawApi.postRecapIngest).not.toHaveBeenCalled();
    expect(liveApi.getRecapArtifacts).not.toHaveBeenCalled();
});
it("does not replace a missing exact run with another run for its session", async () => {
    mount("&view=recap&recapReviewRunId=missing");
    expect(await screen.findByText(/exact saved extraction run is not available/)).toBeInTheDocument();
    expect(savedApi.getSavedRecapSource).not.toHaveBeenCalled();
    expect(rawApi.postRecapIngest).not.toHaveBeenCalled();
});
it("keeps an incomplete run visible with a truthful unavailable reason", async () => {
    const r = { ...row("pending", "draft"), sourceRevisionId: null, sourceSha256: null, unavailableReason: "This run has no frozen source revision component." };
    vi.mocked(savedApi.getSavedRecapRuns).mockResolvedValue(scope([r]));
    mount();
    await waitFor(() => expect(screen.getByRole("option", { name: /pending/ })).toBeInTheDocument());
    const before = vi.mocked(rawApi.postRecapIngest).mock.calls.length;
    await open("pending");
    expect(await screen.findByText(r.unavailableReason)).toBeInTheDocument();
    expect(savedApi.getSavedRecapSource).not.toHaveBeenCalled();
    expect(vi.mocked(rawApi.postRecapIngest).mock.calls).toHaveLength(before);
});
it.each(["resolve", "reject"] as const)("preserves a raw draft when a source reply is late: %s", async (outcome) => {
    const pending = deferred<SavedRecapSource>();
    vi.mocked(savedApi.getSavedRecapSource).mockReturnValue(pending.promise);
    mount();
    const input = await screen.findByLabelText("Write or paste a recap");
    fireEvent.change(input, { target: { value: "My unfinished draft" } });
    fireEvent.change(screen.getByLabelText("Draft title (optional)"), { target: { value: "Campfire return" } });
    await open("run-a");
    await waitFor(() => expect(savedApi.getSavedRecapSource).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("button", { name: "Return to draft" }));
    expect(await screen.findByLabelText("Write or paste a recap")).toHaveValue("My unfinished draft");
    fireEvent.change(screen.getByLabelText("Write or paste a recap"), { target: { value: "Continued draft" } });
    await act(async () => { if (outcome === "resolve")
        pending.resolve(source(scope(), row(), "Stale source reply"));
    else
        pending.reject(new Error("Stale source rejection")); });
    expect(screen.getByLabelText("Write or paste a recap")).toHaveValue("Continued draft");
    expect(screen.queryByText("Stale source reply")).not.toBeInTheDocument();
});
it("drops the first source reply across same-session A→B→A selections", async () => {
    const pending = deferred<SavedRecapSource>();
    let first = true;
    vi.mocked(savedApi.getSavedRecapRuns).mockResolvedValue(scope([row(), row("run-b")]));
    vi.mocked(savedApi.getSavedRecapSource).mockImplementation(async (s, r) => { if (r.runId === "run-a" && first) {
        first = false;
        return pending.promise;
    } return source(s, r, `Latest ${r.runId}`); });
    mount();
    await waitFor(() => expect(screen.getByRole("option", { name: /run-b/ })).toBeInTheDocument());
    await open("run-a");
    await waitFor(() => expect(savedApi.getSavedRecapSource).toHaveBeenCalledTimes(1));
    await open("run-b");
    expect(await screen.findByText("Latest run-b")).toBeInTheDocument();
    await open("run-a");
    expect(await screen.findByText("Latest run-a")).toBeInTheDocument();
    await act(async () => pending.resolve(source(scope(), row(), "Old A reply")));
    expect(screen.queryByText("Old A reply")).not.toBeInTheDocument();
    expect(screen.getByText("Latest run-a")).toBeInTheDocument();
});
it("refreshes a failed catalog and reconnects a saved route without file status", async () => {
    vi.mocked(savedApi.getSavedRecapRuns).mockRejectedValueOnce(new Error("offline")).mockResolvedValue(scope());
    mount("&view=recap&recapReviewRunId=run-a");
    expect(await screen.findByText(/Saved extraction work could not be checked. Retry/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Refresh saved work" }));
    expect(await screen.findByText("Source for run-a.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Disconnect fixture access" }));
    expect(screen.queryByText("Source for run-a.")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reconnect fixture access" }));
    expect(await screen.findByText("Source for run-a.")).toBeInTheDocument();
    expect(rawApi.postRecapIngest).not.toHaveBeenCalled();
});
it("does not revive a catalog returned for a previous World", async () => {
    const old = deferred<SavedRecapRuns>();
    vi.mocked(savedApi.getSavedRecapRuns).mockImplementation(async (world) => world === "elderwyld" ? old.promise : scope([row("new-world")], world));
    const view = mount();
    await waitFor(() => expect(savedApi.getSavedRecapRuns).toHaveBeenCalled());
    window.history.replaceState({}, "", "/ingest?world=another-world&campaign=longmont-c1&session=session-8");
    view.rerender(<IngestionModule campaignId="longmont-c1" session={30} managedWorldId="another-world" initialSourceSession={8}/>);
    await waitFor(() => expect(screen.getByRole("option", { name: /new-world/ })).toBeInTheDocument());
    await act(async () => old.resolve(scope([row("old-world")])));
    expect(screen.queryByRole("option", { name: /old-world/ })).not.toBeInTheDocument();
});
it("starts a new recap from saved work without reprocessing or deleting another session's draft", async () => {
    window.localStorage.setItem("dmb.ingestion.longmont-c1.session.9", JSON.stringify({ version: 3, rawText: "Unfinished ninth session", recapSession: 9, slug: "", title: "Unfinished ninth session", showAdvanced: false, forceStage: false, forceRecap: false, ignoreDiskResume: false }));
    mount("&view=recap&recapReviewRunId=run-a");
    expect(await screen.findByText("Source for run-a.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "New recap" }));
    expect(await screen.findByLabelText("Write or paste a recap")).toHaveValue("");
    expect(screen.getByLabelText("Draft title (optional)")).toHaveValue("");
    expect(new URLSearchParams(window.location.search).has("view")).toBe(false);
    expect(JSON.parse(window.localStorage.getItem("dmb.ingestion.longmont-c1.session.9")!).rawText).toBe("Unfinished ninth session");
    expect(vi.mocked(rawApi.postRecapIngest).mock.calls.every(([request]) => request.operation === "inspect_status")).toBe(true);
});
it("refuses a reader route without an exact run ID rather than guessing from its session", async () => {
    mount("&view=recap");
    expect(await screen.findByText(/exact saved extraction run is not available/)).toBeInTheDocument();
    expect(savedApi.getSavedRecapSource).not.toHaveBeenCalled();
    expect(rawApi.postRecapIngest).not.toHaveBeenCalled();
});
it("drops a pending source when a mounted route moves to a different session", async () => {
    const pending = deferred<SavedRecapSource>();
    const next = row("session-nine", "reviewable", "session-9");
    vi.mocked(savedApi.getSavedRecapRuns).mockResolvedValue(scope([row(), next]));
    vi.mocked(savedApi.getSavedRecapSource).mockImplementation(async (s, r) => r.runId === "run-a" ? pending.promise : source(s, r));
    const view = mount("&view=recap&recapReviewRunId=run-a");
    await waitFor(() => expect(savedApi.getSavedRecapSource).toHaveBeenCalledTimes(1));
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c1&session=session-9&view=recap&recapReviewRunId=session-nine");
    view.rerender(<IngestionModule campaignId="longmont-c1" session={30} managedWorldId="elderwyld" initialSourceSession={9}/>);
    expect(await screen.findByText("Source for session-nine.")).toBeInTheDocument();
    await act(async () => pending.resolve(source(scope(), row(), "Old session eight")));
    expect(screen.queryByText("Old session eight")).not.toBeInTheDocument();
    expect(screen.getByText("Source for session-nine.")).toBeInTheDocument();
    expect(rawApi.postRecapIngest).not.toHaveBeenCalled();
});
it("does not choose a same-session run after changing the raw source session", async () => {
    vi.mocked(savedApi.getSavedRecapRuns).mockResolvedValue(scope([row(), row("nine", "reviewable", "session-9")]));
    mount();
    await waitFor(() => expect(screen.getByRole("option", { name: /nine/ })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Recap/source session"), { target: { value: "9" } });
    expect(screen.getByLabelText("Saved extraction work")).toHaveValue("");
    expect(savedApi.getSavedRecapSource).not.toHaveBeenCalled();
});
it("invalidates pending source reads when refreshing the same run revision", async () => {
    const pending = deferred<SavedRecapSource>();
    let first = true;
    vi.mocked(savedApi.getSavedRecapSource).mockImplementation(async (s, r) => { if (first) {
        first = false;
        return pending.promise;
    } return source(s, r, "Refreshed source"); });
    mount("&view=recap&recapReviewRunId=run-a");
    await waitFor(() => expect(savedApi.getSavedRecapSource).toHaveBeenCalledTimes(1));
    await userEvent.click(screen.getByRole("button", { name: "Refresh saved work" }));
    expect(await screen.findByText("Refreshed source")).toBeInTheDocument();
    await act(async () => pending.resolve(source(scope(), row(), "Before refresh")));
    expect(screen.queryByText("Before refresh")).not.toBeInTheDocument();
    expect(screen.getByText("Refreshed source")).toBeInTheDocument();
});
it("preserves a matching local draft across a cold saved-source route and reload", async () => {
    const key = "dmb.ingestion.longmont-c1.session.30";
    window.localStorage.setItem(key, JSON.stringify({ version: 3, rawText: "Cold retained draft", recapSession: 8, slug: "", title: "Cold draft title", showAdvanced: false, forceStage: false, forceRecap: false, ignoreDiskResume: false }));
    const view = mount("&view=recap&recapReviewRunId=run-a");
    expect(await screen.findByText("Source for run-a.")).toBeInTheDocument();
    view.unmount();
    mount("&view=recap&recapReviewRunId=run-a");
    expect(await screen.findByText("Source for run-a.")).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem(key)!).rawText).toBe("Cold retained draft");
    await userEvent.click(screen.getByRole("button", { name: "Return to draft" }));
    expect(await screen.findByLabelText("Write or paste a recap")).toHaveValue("Cold retained draft");
    expect(screen.getByLabelText("Draft title (optional)")).toHaveValue("Cold draft title");
});

it("cannot revive a pending catalog after access is revoked", async () => {
    const pending = deferred<SavedRecapRuns>();
    vi.mocked(savedApi.getSavedRecapRuns).mockReturnValueOnce(pending.promise).mockResolvedValue(scope([row("reconnected")]));
    mount("&view=recap&recapReviewRunId=run-a");
    await waitFor(() => expect(savedApi.getSavedRecapRuns).toHaveBeenCalledTimes(1));
    await userEvent.click(screen.getByRole("button", {name: "Disconnect fixture access"}));
    await act(async () => pending.resolve(scope()));
    expect(screen.queryByRole("option", {name: /run-a/})).not.toBeInTheDocument();
    expect(savedApi.getSavedRecapSource).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", {name: "Reconnect fixture access"}));
    expect(await screen.findByRole("option", {name: /reconnected/})).toBeInTheDocument();
});

it("mounts exact native source admission without automatically sending or disturbing a saved raw draft", async () => {
    const admit = vi.spyOn(admissionApi, "admitRecapSource").mockRejectedValue(new Error("Admission response lost"));
    mount();
    fireEvent.change(await screen.findByLabelText("Write or paste a recap"), { target: { value: "Retain this unfinished writing" } });
    await open("run-a");
    await screen.findByText("Source for run-a.");
    expect(admit).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Admit source", exact: true }));
    await screen.findByText("Admission response lost");
    expect(admit).toHaveBeenCalledExactlyOnceWith({ managedWorldId: "elderwyld", nativeWorldId: "elderwyld", bindingVersion: 3, campaignId: "longmont-c1", session: 8, sourceArtifactId: "artifact:run-a", sourceRevisionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", contentSha256: "a".repeat(64) });
    expect(rawApi.postRecapIngest).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Return to draft" }));
    expect(await screen.findByLabelText("Write or paste a recap")).toHaveValue("Retain this unfinished writing");
    expect(screen.queryByRole("button", { name: "Recover source admission" })).not.toBeInTheDocument();
    expect(admit).toHaveBeenCalledOnce();
});
