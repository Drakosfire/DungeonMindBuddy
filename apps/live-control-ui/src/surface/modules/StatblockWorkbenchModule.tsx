import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { generateThreatDraftCandidate, getStatblockCandidate } from "../../api/liveApi";
import type {
  GenerateThreatDraftCandidateResponseV1,
  ReadStatblockCandidateResponseV1,
} from "../../api/types";
import type { GeneratedStatblockCandidateV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { StatblockRenderer } from "../../statblocks/render/StatblockRenderer";

type LoadState =
  | { kind: "idle" }
  | { kind: "loading"; candidateId: string }
  | { kind: "success"; response: ReadStatblockCandidateResponseV1 }
  | {
      kind: "status";
      candidateId: string;
      status: Exclude<ReadStatblockCandidateResponseV1["status"], "active">;
      failureCategory: string | null;
      failureMessage: string | null;
    }
  | { kind: "error"; candidateId: string; message: string };

function readCandidateIdFromLocation(): string {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return params.get("candidateId")?.trim() ?? "";
}

function isIntegrityFailureCategory(category: string | null | undefined): boolean {
  if (!category) return false;
  return (
    category === "integrity_failure" ||
    category === "contract_failure" ||
    category.endsWith("_integrity_failure")
  );
}

export type CandidateStatusPresentation = {
  title: string;
  body: string;
  stateKind: "expired" | "missing" | "integrity_failure" | "dependency_unavailable";
};

export function presentCandidateStatus(
  status: Exclude<ReadStatblockCandidateResponseV1["status"], "active">,
  failureCategory: string | null | undefined,
): CandidateStatusPresentation {
  if (status === "expired") {
    return {
      title: "Candidate expired",
      stateKind: "expired",
      body: "This candidate has expired. The exact candidate ID is retained; generate a new candidate rather than falling back to mock or corpus output.",
    };
  }
  if (status === "missing") {
    return {
      title: "Candidate missing",
      stateKind: "missing",
      body: "No candidate exists for this exact ID. There is no fallback to another candidate, mock draft, or corpus file.",
    };
  }
  if (isIntegrityFailureCategory(failureCategory)) {
    return {
      title: "Candidate integrity failure",
      stateKind: "integrity_failure",
      body: "This candidate cannot be trusted because of a local contract or cache integrity failure. The exact candidate ID is retained; this is not a DungeonMindServer outage. Do not fall back to mock or corpus output.",
    };
  }
  return {
    title: "Candidate service unavailable",
    stateKind: "dependency_unavailable",
    body: "The candidate service is unavailable. Retry the exact ID; mock mechanics are not used as a fallback.",
  };
}

function CandidateStatusPanel({
  candidateId,
  status,
  failureCategory,
  failureMessage,
  onRetry,
}: {
  candidateId: string;
  status: Exclude<ReadStatblockCandidateResponseV1["status"], "active">;
  failureCategory: string | null;
  failureMessage: string | null;
  onRetry: () => void;
}) {
  const presentation = presentCandidateStatus(status, failureCategory);
  return (
    <section className="statblock-section" role="status" data-candidate-status={presentation.stateKind}>
      <h3>{presentation.title}</h3>
      <p>
        Exact ID retained: <code>{candidateId}</code>
      </p>
      <p className="module-muted">{presentation.body}</p>
      {failureCategory ? (
        <p className="module-muted">
          Category: <code>{failureCategory}</code>
          {failureMessage ? ` — ${failureMessage}` : ""}
        </p>
      ) : null}
      <button type="button" onClick={onRetry}>
        Retry exact candidate
      </button>
    </section>
  );
}

export function StatblockWorkbenchModule() {
  const [candidateIdInput, setCandidateIdInput] = useState(readCandidateIdFromLocation);
  const [draftIdInput, setDraftIdInput] = useState("");
  const [draftVersionInput, setDraftVersionInput] = useState("1");
  const [loadState, setLoadState] = useState<LoadState>({ kind: "idle" });
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [pendingGenerate, setPendingGenerate] = useState(false);

  const loadCandidate = useCallback(async (candidateId: string) => {
    const trimmed = candidateId.trim();
    if (!trimmed) {
      setLoadState({ kind: "error", candidateId: "", message: "Enter an exact candidate ID." });
      return;
    }
    setLoadState({ kind: "loading", candidateId: trimmed });
    setGenerateMessage(null);
    setGenerateError(null);
    try {
      const response = await getStatblockCandidate(trimmed);
      if (response.status === "active" && response.candidate) {
        setLoadState({ kind: "success", response });
        return;
      }
      setLoadState({
        kind: "status",
        candidateId: response.candidate_id || trimmed,
        status: response.status === "active" ? "missing" : response.status,
        failureCategory: response.failure_category ?? null,
        failureMessage: response.failure_message ?? null,
      });
    } catch (error) {
      setLoadState({
        kind: "error",
        candidateId: trimmed,
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }, []);

  useEffect(() => {
    const initial = readCandidateIdFromLocation();
    if (initial) {
      void loadCandidate(initial);
    }
  }, [loadCandidate]);

  const onSubmitCandidate = (event: FormEvent) => {
    event.preventDefault();
    void loadCandidate(candidateIdInput);
  };

  const onGenerateFromDraft = async (event: FormEvent) => {
    event.preventDefault();
    const draftId = draftIdInput.trim();
    const expectedVersion = Number(draftVersionInput);
    if (!draftId || !Number.isInteger(expectedVersion) || expectedVersion < 1) {
      setGenerateError("Provide a draft ID and expected draft version ≥ 1.");
      return;
    }
    setPendingGenerate(true);
    setGenerateError(null);
    setGenerateMessage(null);
    try {
      const response: GenerateThreatDraftCandidateResponseV1 = await generateThreatDraftCandidate(
        draftId,
        { expected_draft_version: expectedVersion },
      );
      if (response.outcome === "success" && response.candidate?.candidate_id) {
        const candidateId = response.candidate.candidate_id;
        setCandidateIdInput(candidateId);
        setGenerateMessage(
          `Generated ${candidateId}${
            response.cache_status ? ` (${response.cache_status})` : ""
          }. Loading structured review…`,
        );
        await loadCandidate(candidateId);
        return;
      }
      setGenerateError(
        response.failure_message ??
          response.failure_category ??
          "Generation failed without a typed candidate.",
      );
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : String(error));
    } finally {
      setPendingGenerate(false);
    }
  };

  const activeCandidate: GeneratedStatblockCandidateV1 | null =
    loadState.kind === "success" ? loadState.response.candidate ?? null : null;

  return (
    <div className="module-panel statblock-workbench" data-module-id="statblock_workbench">
      <header className="statblock-workbench-header">
        <div>
          <p className="eyebrow">Typed candidate review</p>
          <h2 className="module-title">Statblock Workbench</h2>
          <p className="module-muted">
            Displays mechanics only from a structured DungeonMind candidate definition and receipts.
            Mock generate, Markdown corpus drafts, and corpus promotion are not the normal review path.
          </p>
        </div>
        <span className="badge">sbw04-review</span>
      </header>

      <section className="statblock-section">
        <h3>Load exact candidate</h3>
        <form className="statblock-command-row" onSubmit={onSubmitCandidate}>
          <label>
            Candidate ID
            <input
              value={candidateIdInput}
              onChange={(event) => setCandidateIdInput(event.target.value)}
              placeholder="cand_…"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <button type="submit" disabled={loadState.kind === "loading"}>
            {loadState.kind === "loading" ? "Loading…" : "Load candidate"}
          </button>
        </form>
        <p className="module-muted">
          Optional deep link: <code>?candidateId=cand_…</code>
        </p>
      </section>

      <section className="statblock-section">
        <h3>Generate from ThreatDraft</h3>
        <form className="statblock-command-row" onSubmit={onGenerateFromDraft}>
          <label>
            Draft ID
            <input
              value={draftIdInput}
              onChange={(event) => setDraftIdInput(event.target.value)}
              placeholder="td_…"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <label>
            Expected version
            <input
              value={draftVersionInput}
              onChange={(event) => setDraftVersionInput(event.target.value)}
              inputMode="numeric"
            />
          </label>
          <button type="submit" disabled={pendingGenerate}>
            {pendingGenerate ? "Generating…" : "Generate candidate"}
          </button>
        </form>
        {generateMessage ? (
          <p className="statblock-command-status" role="status">
            {generateMessage}
          </p>
        ) : null}
        {generateError ? (
          <p className="statblock-command-error" role="alert">
            Unable to generate candidate: {generateError}
          </p>
        ) : null}
      </section>

      {loadState.kind === "idle" ? (
        <p className="module-muted">Load an exact candidate ID to review structured mechanics.</p>
      ) : null}

      {loadState.kind === "loading" ? (
        <p className="module-muted" role="status">
          Loading candidate <code>{loadState.candidateId}</code>…
        </p>
      ) : null}

      {loadState.kind === "error" ? (
        <p className="module-error" role="alert">
          Unable to load candidate{loadState.candidateId ? ` ${loadState.candidateId}` : ""}:{" "}
          {loadState.message}
        </p>
      ) : null}

      {loadState.kind === "status" ? (
        <CandidateStatusPanel
          candidateId={loadState.candidateId}
          status={loadState.status}
          failureCategory={loadState.failureCategory}
          failureMessage={loadState.failureMessage}
          onRetry={() => void loadCandidate(loadState.candidateId)}
        />
      ) : null}

      {activeCandidate ? <StatblockRenderer candidate={activeCandidate} mode="review" /> : null}
    </div>
  );
}
