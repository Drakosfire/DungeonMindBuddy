import type { ThreatDraftCandidateRefV1, ThreatDraftV1 } from "../../api/types";
import { lineageSummary } from "./statblockRevisionAttempt";

export function ProposalHistoryPanel({
  draft,
  activeCandidateId,
  onSelectCandidate,
  onRefresh,
  refreshPending,
}: {
  draft: ThreatDraftV1;
  activeCandidateId: string | null;
  onSelectCandidate: (candidateId: string) => void;
  onRefresh: () => void;
  refreshPending: boolean;
}) {
  const refs = draft.candidate_refs ?? [];
  return (
    <section
      className="statblock-section statblock-proposal-history"
      data-testid="proposal-history-panel"
    >
      <div className="statblock-proposal-history__header">
        <h3>Proposal history</h3>
        <button type="button" onClick={onRefresh} disabled={refreshPending} data-testid="refresh-proposal-history">
          {refreshPending ? "Refreshing…" : "Refresh proposal history"}
        </button>
      </div>
      {refs.length === 0 ? (
        <p className="module-muted">No candidate refs on this ThreatDraft yet.</p>
      ) : (
        <ul className="statblock-proposal-history__list">
          {refs.map((ref) => (
            <ProposalHistoryRow
              key={ref.candidate_id}
              refEntry={ref}
              isCurrent={ref.candidate_id === activeCandidateId}
              onSelect={() => onSelectCandidate(ref.candidate_id)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function ProposalHistoryRow({
  refEntry,
  isCurrent,
  onSelect,
}: {
  refEntry: ThreatDraftCandidateRefV1;
  isCurrent: boolean;
  onSelect: () => void;
}) {
  return (
    <li
      className={
        isCurrent
          ? "statblock-proposal-history__row statblock-proposal-history__row--current"
          : "statblock-proposal-history__row"
      }
      data-testid={`proposal-history-row-${refEntry.candidate_id}`}
      data-candidate-status={refEntry.status}
      data-current={isCurrent ? "true" : "false"}
    >
      <button type="button" className="statblock-proposal-history__select" onClick={onSelect}>
        <code>{refEntry.candidate_id}</code>
      </button>
      <span className="statblock-proposal-history__meta">
        status <code>{refEntry.status}</code> · from draft v{refEntry.generated_from_draft_version} ·{" "}
        {refEntry.created_at}
      </span>
      <p className="module-muted statblock-proposal-history__lineage">{lineageSummary(refEntry.lineage)}</p>
      {isCurrent ? <p className="statblock-proposal-history__current">Currently loaded</p> : null}
    </li>
  );
}

export function ReviseWithAiPanel({
  candidateId,
  draftId,
  draftVersion,
  editorStateRevision,
  instructions,
  onInstructionsChange,
  preserveElementKeys,
  onPreserveElementKeysChange,
  onCreate,
  onResume,
  onStartNew,
  revisePending,
  showResume,
  showStartNew,
  disabled,
  createDisabled,
  statusMessage,
  errorMessage,
  mechanicsSaved,
  readOnlyInstructions,
}: {
  candidateId: string;
  draftId: string;
  draftVersion: number | null;
  editorStateRevision: number;
  instructions: string;
  onInstructionsChange: (value: string) => void;
  preserveElementKeys: boolean;
  onPreserveElementKeysChange: (value: boolean) => void;
  onCreate: () => void;
  onResume: () => void;
  onStartNew: () => void;
  revisePending: boolean;
  showResume: boolean;
  showStartNew: boolean;
  disabled: boolean;
  createDisabled?: boolean;
  statusMessage: string | null;
  errorMessage: string | null;
  mechanicsSaved: boolean;
  readOnlyInstructions?: boolean;
}) {
  return (
    <section className="statblock-section statblock-revise-panel" data-testid="revise-with-ai-panel">
      <h3>Revise with AI</h3>
      {mechanicsSaved ? (
        <p className="module-muted" data-testid="revise-mechanics-saved-boundary">
          Source: current unsaved working copy. Previously saved mechanics are unchanged.
        </p>
      ) : (
        <p className="module-muted">Source: current unsaved working copy.</p>
      )}
      <dl className="statblock-revise-source-disclosure">
        <div>
          <dt>Candidate</dt>
          <dd>
            <code>{candidateId}</code>
          </dd>
        </div>
        <div>
          <dt>ThreatDraft</dt>
          <dd>
            <code>{draftId}</code> v{draftVersion ?? "?"}
          </dd>
        </div>
        <div>
          <dt>Editor state revision</dt>
          <dd>
            <code>{editorStateRevision}</code>
          </dd>
        </div>
      </dl>
      <label className="statblock-create-field">
        <span className="statblock-create-field-label">Revision instructions (one per line)</span>
        <textarea
          value={instructions}
          onChange={(event) => onInstructionsChange(event.target.value)}
          rows={4}
          data-testid="revise-instructions"
          readOnly={readOnlyInstructions === true}
        />
      </label>
      <label className="statblock-revise-preserve-keys">
        <input
          type="checkbox"
          checked={preserveElementKeys}
          onChange={(event) => onPreserveElementKeysChange(event.target.checked)}
          data-testid="revise-preserve-element-keys"
          disabled={readOnlyInstructions === true}
        />
        Preserve element keys where possible
      </label>
      <div className="statblock-command-row">
        <button
          type="button"
          onClick={onCreate}
          disabled={disabled || createDisabled === true || revisePending}
          data-testid="revise-create-proposal"
        >
          {revisePending ? "Creating revised proposal…" : "Create revised proposal"}
        </button>
        {showResume ? (
          <button
            type="button"
            onClick={onResume}
            disabled={disabled || revisePending}
            data-testid="revise-resume-same"
          >
            Resume same revise
          </button>
        ) : null}
        {showStartNew ? (
          <button type="button" onClick={onStartNew} disabled={revisePending} data-testid="revise-start-new">
            Start new revise attempt
          </button>
        ) : null}
      </div>
      {statusMessage ? (
        <p className="statblock-command-status" role="status" data-testid="revise-status">
          {statusMessage}
        </p>
      ) : null}
      {errorMessage ? (
        <p className="statblock-command-error" role="alert" data-testid="revise-error">
          {errorMessage}
        </p>
      ) : null}
    </section>
  );
}

export function MechanicsSavedAppendBoundary() {
  return (
    <p className="module-muted statblock-sbw13-boundary" data-testid="sbw13-append-boundary">
      This proposal is not saved. Appending it as a new immutable mechanics revision is not available until
      SBW13.
    </p>
  );
}
