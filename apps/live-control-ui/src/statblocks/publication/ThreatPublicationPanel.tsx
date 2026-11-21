import { type ReactElement, useCallback, useEffect, useMemo, useState } from "react";

import type {
  ThreatDraftV1,
  ThreatPublicationCommitV1,
  ThreatPublicationIdentityResolutionV1,
  ThreatPublicationOperationV1,
  ThreatPublicationProposalV1,
} from "../../api/types";
import {
  getThreatIdentityResolution,
  getThreatPublicationCommit,
  getThreatPublicationOperation,
  getThreatPublicationProposal,
} from "../../api/liveApi";
import {
  parseThreatPublicationSession,
  threatPublicationSessionKey,
  type ThreatPublicationWorkbenchSessionV1,
} from "./threatPublicationSession";

/** Historical reads only. No classic publication mutation is exposed here. */
export type ThreatPublicationApi = {
  getThreatPublicationOperation: typeof getThreatPublicationOperation;
  getThreatIdentityResolution: typeof getThreatIdentityResolution;
  getThreatPublicationProposal: typeof getThreatPublicationProposal;
  getThreatPublicationCommit: typeof getThreatPublicationCommit;
};
export type ThreatPublicationDockTone = "info" | "error" | "success";
export interface ThreatPublicationDockAction {
  testId: string;
  label: string;
  disabled?: boolean;
  onClick: () => void;
}
export interface ThreatPublicationDockModel {
  status: string;
  tone: ThreatPublicationDockTone;
  actions: ThreatPublicationDockAction[];
}
export interface ThreatPublicationPanelProps {
  draft: ThreatDraftV1;
  api?: Partial<ThreatPublicationApi>;
  storage?: Storage;
  onDockModelChange?: (model: ThreatPublicationDockModel | null) => void;
}

type History = {
  scope: string;
  phase: "loading" | "empty" | "unresolved" | "recorded";
  pointer?: ThreatPublicationWorkbenchSessionV1;
  operation?: ThreatPublicationOperationV1;
  resolution?: ThreatPublicationIdentityResolutionV1;
  proposal?: ThreatPublicationProposalV1;
  commit?: ThreatPublicationCommitV1;
};
const UNRESOLVED = "History is unavailable or does not match the retained pointer. The original session remains unchanged and unresolved.";
function requireMatch(matches: boolean): asserts matches {
  if (!matches) throw new Error("Historical publication correspondence failed");
}

export function ThreatPublicationPanel({ draft, api, storage, onDockModelChange }: ThreatPublicationPanelProps): ReactElement {
  const scope = JSON.stringify([draft.draft_id, draft.world_id, draft.campaign_id]);
  const [attempt, setAttempt] = useState(0);
  const [history, setHistory] = useState<History>({ scope, phase: "loading" });
  const readers = useMemo<ThreatPublicationApi>(() => ({
    getThreatPublicationOperation, getThreatIdentityResolution,
    getThreatPublicationProposal, getThreatPublicationCommit, ...api,
  }), [api]);
  const reread = useCallback(() => setAttempt((value) => value + 1), []);
  // Mask a previous draft's data synchronously, before effect cleanup runs.
  const current: History = history.scope === scope ? history : { scope, phase: "loading" };

  useEffect(() => {
    let cancelled = false;
    setHistory({ scope, phase: "loading" });
    void (async () => {
      let pointer: ThreatPublicationWorkbenchSessionV1 | undefined;
      try {
        const source = storage ?? window.sessionStorage;
        const key = threatPublicationSessionKey(draft.draft_id);
        const raw = source.getItem(key);
        if (raw === null) {
          if (!cancelled) setHistory({ scope, phase: "empty" });
          return;
        }
        const value: unknown = JSON.parse(raw);
        const parsed = parseThreatPublicationSession(value);
        requireMatch(parsed !== null && typeof value === "object" && value !== null);
        const carried = value as Record<string, unknown>;
        requireMatch(parsed.draft_id === draft.draft_id
          && Number.isInteger(parsed.draft_version)
          && ["draft_id", "operation_id", "resolution_id", "proposal_id", "commit_id"].every(
            (field) => carried[field] === parsed[field as keyof ThreatPublicationWorkbenchSessionV1],
          )
          && [parsed.operation_id, parsed.resolution_id, parsed.proposal_id, parsed.commit_id].every(
            (id) => id === null || (id.trim().length > 0 && id === id.trim()),
          )
          && (!parsed.proposal_id || !!parsed.resolution_id)
          && (!parsed.commit_id || (!!parsed.proposal_id && !!parsed.resolution_id))
          && (parsed.stage !== "identity" || !!parsed.resolution_id)
          && (parsed.stage !== "proposal" || !!parsed.proposal_id)
          && (parsed.stage !== "commit" || !!parsed.commit_id));
        pointer = parsed;
        const exactPointer = () => {
          if (cancelled) return false;
          requireMatch(source.getItem(key) === raw);
          return true;
        };
        const response = await readers.getThreatPublicationOperation(pointer.draft_id, pointer.operation_id);
        if (!exactPointer()) return;
        const operation = response.operation;
        requireMatch(response.schema === "dmb_threat_publication_operation_response_v1"
          && response.draft_id === pointer.draft_id && !!operation);
        requireMatch(operation.schema === "dmb_threat_publication_operation_v1"
          && operation.operation_id === pointer.operation_id
          && operation.source_snapshot?.schema === "dmb_threat_publication_source_v1"
          && operation.source_snapshot.draft_id === pointer.draft_id
          && operation.source_snapshot.draft_version === pointer.draft_version
          && operation.source_snapshot.world_id === draft.world_id
          && operation.source_snapshot.campaign_id === draft.campaign_id
          && ["ready", "stale", "cancelled", "superseded"].includes(operation.state));
        let resolution: ThreatPublicationIdentityResolutionV1 | undefined;
        let proposal: ThreatPublicationProposalV1 | undefined;
        let commit: ThreatPublicationCommitV1 | undefined;
        if (pointer.resolution_id) {
          const result = await readers.getThreatIdentityResolution(pointer.draft_id, pointer.operation_id, pointer.resolution_id);
          if (!exactPointer()) return;
          requireMatch(result.schema === "dmb_threat_publication_identity_response_v1"
            && result.draft_id === pointer.draft_id && result.operation_id === pointer.operation_id && !!result.resolution);
          resolution = result.resolution;
          requireMatch(resolution.schema === "dmb_threat_publication_identity_resolution_v1"
            && resolution.resolution_id === pointer.resolution_id && resolution.draft_id === pointer.draft_id
            && resolution.operation_id === pointer.operation_id && resolution.source_digest === operation.source_digest
            && resolution.expected_parent_revision_id === operation.expected_parent_revision_id
            && ["active", "superseded"].includes(resolution.state));
        }
        if (pointer.proposal_id) {
          const result = await readers.getThreatPublicationProposal(pointer.draft_id, pointer.operation_id, pointer.proposal_id);
          if (!exactPointer()) return;
          requireMatch(result.schema === "dmb_threat_publication_proposal_response_v1"
            && result.draft_id === pointer.draft_id && result.operation_id === pointer.operation_id
            && result.resolution_id === pointer.resolution_id && !!result.proposal);
          proposal = result.proposal;
          requireMatch(proposal.schema === "dmb_threat_publication_proposal_v1"
            && proposal.proposal_id === pointer.proposal_id && proposal.draft_id === pointer.draft_id
            && proposal.operation_id === pointer.operation_id && proposal.resolution_id === pointer.resolution_id
            && proposal.source_digest === operation.source_digest
            && proposal.expected_parent_revision_id === operation.expected_parent_revision_id
            && proposal.resolution_request_digest === resolution?.request_digest
            && proposal.candidate_set_digest === resolution?.candidate_set_digest
            && ["active", "superseded"].includes(proposal.state));
        }
        if (pointer.commit_id) {
          const result = await readers.getThreatPublicationCommit(pointer.draft_id, pointer.operation_id, pointer.commit_id);
          if (!exactPointer()) return;
          requireMatch(result.schema === "dmb_threat_publication_commit_response_v1"
            && result.draft_id === pointer.draft_id && result.operation_id === pointer.operation_id
            && result.commit_id === pointer.commit_id && result.proposal_id === pointer.proposal_id && !!result.commit);
          commit = result.commit;
          requireMatch(commit.schema === "dmb_threat_publication_commit_v1"
            && commit.commit_id === pointer.commit_id && commit.draft_id === pointer.draft_id
            && commit.operation_id === pointer.operation_id && commit.proposal_id === pointer.proposal_id
            && commit.resolution_id === pointer.resolution_id && commit.world_id === draft.world_id
            && commit.campaign_id === draft.campaign_id && commit.source_digest === operation.source_digest
            && commit.expected_parent_revision_id === operation.expected_parent_revision_id
            && commit.proposal_request_digest === proposal?.request_digest
            && commit.resolution_request_digest === resolution?.request_digest
            && commit.candidate_set_digest === resolution?.candidate_set_digest
            && commit.sealed_proposal_digest === proposal?.sealed_proposal_digest
            && commit.expected_contribution_id === proposal?.expected_contribution_id
            && ["committing", "uncommitted", "ambiguous", "committed_unverified", "committed_verified"].includes(commit.state));
          requireMatch(!["committed_verified", "committed_unverified"].includes(commit.state)
            || (typeof commit.committed_revision_id === "string" && commit.committed_revision_id.trim().length > 0));
        }
        if (exactPointer()) setHistory({ scope, phase: "recorded", pointer, operation, resolution, proposal, commit });
      } catch {
        if (!cancelled) setHistory({ scope, phase: "unresolved", pointer });
      }
    })();
    return () => { cancelled = true; };
    // Draft/mechanics versions intentionally do not gate historical inspection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, readers, storage, attempt]);

  useEffect(() => {
    const changed = (event: StorageEvent) => {
      if (event.key === null || event.key === threatPublicationSessionKey(draft.draft_id)) {
        setHistory({ scope, phase: "loading" });
        reread();
      }
    };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  }, [draft.draft_id, scope, reread]);

  const status = current.phase === "loading" ? "Reading retained publication history…"
    : current.phase === "empty" ? "No retained publication pointer in this browser."
    : current.phase === "unresolved" ? UNRESOLVED
    : "Recorded publication history. No publication actions are available.";
  useEffect(() => {
    onDockModelChange?.({ status, tone: current.phase === "unresolved" ? "error" : "info",
      actions: [{ testId: "reread-publication-history", label: "Re-read history", disabled: current.phase === "loading", onClick: reread }] });
    return () => onDockModelChange?.(null);
  }, [onDockModelChange, status, current.phase, reread]);

  return <section data-testid="threat-publication-panel" aria-label="Classic Threat publication history">
    <h3>Classic publication is retired</h3>
    <p>Inspect retained records only. This view cannot publish, retry, cancel or clear the original session.</p>
    <p role="status" data-testid="publication-history-status">{status}</p>
    {current.pointer && <p>Retained draft version: {current.pointer.draft_version}. The current draft and mechanics may have changed.</p>}
    {current.phase === "recorded" && <div data-testid="publication-history-records">
      <p>Recorded operation state: {current.operation?.state}</p>
      {current.resolution && <p>Recorded identity state: {current.resolution.state}; decision: {current.resolution.decision}</p>}
      {current.proposal && <p>Recorded proposal state: {current.proposal.state}</p>}
      {current.commit && <p>Recorded commit state: {current.commit.state}; revision: {current.commit.committed_revision_id ?? "not recorded"}</p>}
      <p>Recorded states do not authorize a new write or release an uncertain submitted request.</p>
      <details><summary>Recorded references</summary>
        <p>Operation: {current.pointer?.operation_id}</p>
        {current.pointer?.resolution_id && <p>Identity: {current.pointer.resolution_id}</p>}
        {current.pointer?.proposal_id && <p>Proposal: {current.pointer.proposal_id}</p>}
        {current.pointer?.commit_id && <p>Commit: {current.pointer.commit_id}</p>}
        <p>Recorded mechanics: {current.operation?.source_snapshot.accepted_mechanics_ref?.statblock_id} / {current.operation?.source_snapshot.accepted_mechanics_ref?.revision_id}</p>
      </details>
    </div>}
    {!onDockModelChange && <button data-testid="reread-publication-history" disabled={current.phase === "loading"} onClick={reread}>Re-read history</button>}
  </section>;
}
