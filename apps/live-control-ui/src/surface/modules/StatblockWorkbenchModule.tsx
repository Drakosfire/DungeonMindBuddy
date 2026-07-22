import { FormEvent, useState } from "react";

import { getStatblockCandidate, LiveApiError } from "../../api/liveApi";
import type { ReadStatblockCandidateResponseV1 } from "../../api/types";
import { StatblockRenderer } from "../../statblocks/render/StatblockRenderer";

type WorkbenchStatus =
  | { kind: "idle" }
  | { kind: "loading"; candidateId: string }
  | { kind: "ready"; response: ReadStatblockCandidateResponseV1 }
  | { kind: "not_found"; candidateId: string; message: string }
  | { kind: "expired"; response: ReadStatblockCandidateResponseV1 }
  | { kind: "unavailable"; candidateId: string; message: string }
  | { kind: "contract_error"; candidateId: string; message: string };

function statusMessage(status: WorkbenchStatus): string | null {
  switch (status.kind) {
    case "loading":
      return `Loading candidate ${status.candidateId}…`;
    case "not_found":
      return status.message;
    case "expired":
      return `Candidate ${status.response.candidate_id} is expired.`;
    case "unavailable":
      return status.message;
    case "contract_error":
      return status.message;
    default:
      return null;
  }
}

export function StatblockWorkbenchModule() {
  const [candidateIdInput, setCandidateIdInput] = useState("");
  const [status, setStatus] = useState<WorkbenchStatus>({ kind: "idle" });

  const loadCandidate = async (candidateId: string) => {
    const cleaned = candidateId.trim();
    if (!cleaned) return;
    setStatus({ kind: "loading", candidateId: cleaned });
    try {
      const response = await getStatblockCandidate(cleaned);
      if (response.status === "expired") {
        setStatus({ kind: "expired", response });
        return;
      }
      if (response.status === "unavailable") {
        setStatus({
          kind: "unavailable",
          candidateId: cleaned,
          message:
            response.failure_message
            ?? `Candidate ${cleaned} is unavailable (${response.failure_category ?? "unknown"}).`,
        });
        return;
      }
      if (!response.candidate || typeof response.candidate !== "object") {
        setStatus({
          kind: "contract_error",
          candidateId: cleaned,
          message: `Candidate ${cleaned} response is missing a typed payload.`,
        });
        return;
      }
      setStatus({ kind: "ready", response });
    } catch (error) {
      if (error instanceof LiveApiError && error.status === 404) {
        setStatus({
          kind: "not_found",
          candidateId: cleaned,
          message: `Candidate ${cleaned} was not found.`,
        });
        return;
      }
      setStatus({
        kind: "unavailable",
        candidateId: cleaned,
        message:
          error instanceof Error
            ? error.message
            : `Candidate ${cleaned} could not be loaded.`,
      });
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void loadCandidate(candidateIdInput);
  };

  const activeCandidateId =
    status.kind === "ready" || status.kind === "expired"
      ? status.response.candidate_id
      : status.kind === "loading" || status.kind === "not_found" || status.kind === "unavailable" || status.kind === "contract_error"
        ? status.candidateId
        : null;

  const candidatePayload =
    status.kind === "ready" || status.kind === "expired"
      ? status.response.candidate
      : null;

  return (
    <section className="module-panel statblock-workbench" aria-label="Statblock candidate workbench">
      <header className="module-header">
        <h2>Statblock candidate review</h2>
        <p className="module-muted">
          Review one exact typed candidate through the shared semantic renderer. Mock generation and corpus promotion are no longer the normal path.
        </p>
      </header>

      <form className="statblock-action-row" onSubmit={onSubmit}>
        <label>
          Candidate ID
          <input
            value={candidateIdInput}
            onChange={(event) => setCandidateIdInput(event.target.value)}
            placeholder="cand_…"
            aria-label="Candidate ID"
          />
        </label>
        <button type="submit" disabled={status.kind === "loading" || !candidateIdInput.trim()}>
          {status.kind === "loading" ? "Loading…" : "Load candidate"}
        </button>
        {activeCandidateId ? (
          <button
            type="button"
            onClick={() => void loadCandidate(activeCandidateId)}
            disabled={status.kind === "loading"}
          >
            Reload
          </button>
        ) : null}
      </form>

      {statusMessage(status) ? (
        <p
          className={status.kind === "ready" ? "module-muted" : "statblock-command-error"}
          role={status.kind === "loading" || status.kind === "ready" ? undefined : "alert"}
        >
          {statusMessage(status)}
        </p>
      ) : null}

      {activeCandidateId ? (
        <p className="module-muted">
          Exact locator: <code>{activeCandidateId}</code>
        </p>
      ) : null}

      {status.kind === "ready" && candidatePayload ? (
        <StatblockRenderer candidate={candidatePayload} mode="review" />
      ) : null}

      {status.kind === "expired" && candidatePayload ? (
        <details>
          <summary>Expired candidate payload (read-only)</summary>
          <StatblockRenderer candidate={candidatePayload} mode="review" />
        </details>
      ) : null}
    </section>
  );
}
