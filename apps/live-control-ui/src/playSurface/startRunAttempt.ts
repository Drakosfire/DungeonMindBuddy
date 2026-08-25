import { LiveApiError } from "../api/liveApi";
import type {
  CreatePlayRunRequest,
  PlayRunRecord,
  PlayRunReferenceManifest,
  WorkspaceCommittedRevision,
} from "../api/types";
import { CANONICAL_SHA256_RE, isCanonicalUuid } from "./runbook/nativeRunbookProjection";

export type StartRunBinding = {
  runId: string;
  playableArtifactId: string;
  expectedPlayableRevision: number;
  expectedPlayableContentSha256: string;
};

export type SnapshotPreflightReason =
  | "document_mismatch"
  | "not_runbook"
  | "discarded"
  | "uncommitted"
  | "missing_revision"
  | "missing_sha";

export type StartRunPhase = "fresh" | "replay_create" | "retry_seal";

export type StartRunDeps = {
  generateRunId: () => string;
  getCommittedRevision: (documentId: string) => Promise<WorkspaceCommittedRevision>;
  putRun: (runId: string, request: CreatePlayRunRequest) => Promise<PlayRunRecord>;
  getRun: (runId: string) => Promise<PlayRunRecord>;
  putManifest: (runId: string) => Promise<PlayRunReferenceManifest>;
  getManifest: (runId: string) => Promise<PlayRunReferenceManifest>;
};

export type StartRunResult =
  | {
    outcome: "ready";
    binding: StartRunBinding;
    run: PlayRunRecord;
    manifest: PlayRunReferenceManifest;
  }
  | { outcome: "blocked"; binding?: StartRunBinding; detail: string }
  | { outcome: "incomplete"; binding: StartRunBinding; run: PlayRunRecord; detail: string }
  | { outcome: "replay_create"; binding: StartRunBinding; detail: string };

function createBody(binding: StartRunBinding): CreatePlayRunRequest {
  return {
    playable_artifact_id: binding.playableArtifactId,
    expected_playable_revision: binding.expectedPlayableRevision,
    expected_playable_content_sha256: binding.expectedPlayableContentSha256,
  };
}

function errorStatus(error: unknown): number | null {
  return error instanceof LiveApiError ? error.status : null;
}

function errorDetail(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function preflightCommittedRunbookRevision(
  selectedDocumentId: string,
  committed: WorkspaceCommittedRevision,
): { ok: true; revision: number; sha: string } | { ok: false; reason: SnapshotPreflightReason; detail: string } {
  if (committed.document_id !== selectedDocumentId) {
    return {
      ok: false,
      reason: "document_mismatch",
      detail: "committed revision is not the selected Runbook",
    };
  }
  if (committed.kind !== "runbook") {
    return { ok: false, reason: "not_runbook", detail: "selected document is not a Runbook" };
  }
  if (committed.status !== "active") {
    return { ok: false, reason: "discarded", detail: "runbook workspace document is discarded" };
  }
  if (committed.has_divergent_working_copy) {
    return { ok: false, reason: "uncommitted", detail: "runbook workspace document is not committed" };
  }
  if (!Number.isInteger(committed.revision_n) || committed.revision_n <= 0) {
    return { ok: false, reason: "missing_revision", detail: "runbook has no exact committed revision" };
  }
  if (!CANONICAL_SHA256_RE.test(committed.content_sha256)) {
    return { ok: false, reason: "missing_sha", detail: "runbook committed revision has no exact content SHA" };
  }
  return { ok: true, revision: committed.revision_n, sha: committed.content_sha256 };
}

export function allocateStartRunId(generateRunId: () => string): { ok: true; runId: string } | { ok: false; detail: string } {
  const runId = generateRunId();
  if (!isCanonicalUuid(runId)) {
    return { ok: false, detail: "Start Run identity must be a canonical UUID." };
  }
  return { ok: true, runId };
}

export function bindStartRunAttempt(
  runId: string,
  selectedDocumentId: string,
  committed: WorkspaceCommittedRevision,
): { ok: true; binding: StartRunBinding } | { ok: false; reason: SnapshotPreflightReason; detail: string } {
  if (!isCanonicalUuid(runId) || !isCanonicalUuid(selectedDocumentId)) {
    return { ok: false, reason: "document_mismatch", detail: "Start Run identities must be canonical UUIDs." };
  }
  const preflight = preflightCommittedRunbookRevision(selectedDocumentId, committed);
  if (!preflight.ok) return preflight;
  return {
    ok: true,
    binding: {
      runId,
      playableArtifactId: selectedDocumentId,
      expectedPlayableRevision: preflight.revision,
      expectedPlayableContentSha256: preflight.sha,
    },
  };
}

export function sameIntendedRunBinding(run: PlayRunRecord, binding: StartRunBinding): boolean {
  return (
    run.run_id === binding.runId
    && run.playable_artifact_id === binding.playableArtifactId
    && run.playable_revision === binding.expectedPlayableRevision
    && run.playable_content_sha256 === binding.expectedPlayableContentSha256
  );
}

export function sameIntendedManifestBinding(
  manifest: PlayRunReferenceManifest,
  run: PlayRunRecord,
): boolean {
  return (
    manifest.run_id === run.run_id
    && manifest.playable_artifact_id === run.playable_artifact_id
    && manifest.playable_revision === run.playable_revision
    && manifest.playable_content_sha256 === run.playable_content_sha256
  );
}

export function confirmCreatedRun(
  run: PlayRunRecord,
  binding: StartRunBinding,
): { status: "continue_seal"; run: PlayRunRecord } | { status: "block"; detail: string } {
  if (!sameIntendedRunBinding(run, binding)) {
    return { status: "block", detail: "returned Run binding does not match this start attempt" };
  }
  return { status: "continue_seal", run };
}

async function reconcileUnknownCreate(
  binding: StartRunBinding,
  deps: StartRunDeps,
): Promise<StartRunResult | { outcome: "continue_seal"; run: PlayRunRecord }> {
  try {
    const found = await deps.getRun(binding.runId);
    const confirmed = confirmCreatedRun(found, binding);
    if (confirmed.status === "block") {
      return { outcome: "blocked", binding, detail: confirmed.detail };
    }
    return { outcome: "continue_seal", run: confirmed.run };
  } catch (error) {
    if (errorStatus(error) === 404) {
      return {
        outcome: "replay_create",
        binding,
        detail: "Run create outcome is unknown and the Run does not exist yet. Retry keeps this UUID.",
      };
    }
    return {
      outcome: "replay_create",
      binding,
      detail: `Run create outcome is unknown. Retry keeps UUID ${binding.runId}.`,
    };
  }
}

async function sealExactRun(
  binding: StartRunBinding,
  run: PlayRunRecord,
  deps: StartRunDeps,
): Promise<StartRunResult> {
  try {
    const manifest = await deps.putManifest(binding.runId);
    if (!sameIntendedManifestBinding(manifest, run)) {
      return {
        outcome: "incomplete",
        binding,
        run,
        detail: `Run ${binding.runId} was created; setup is incomplete because the sealed manifest does not match this Run.`,
      };
    }
    return { outcome: "ready", binding, run, manifest };
  } catch (error) {
    if (errorStatus(error) === 409) {
      return {
        outcome: "incomplete",
        binding,
        run,
        detail: `Run ${binding.runId} was created; setup is incomplete. The Runbook changed before the reference manifest could be sealed.`,
      };
    }
    try {
      const manifest = await deps.getManifest(binding.runId);
      if (sameIntendedManifestBinding(manifest, run)) {
        return { outcome: "ready", binding, run, manifest };
      }
      return {
        outcome: "incomplete",
        binding,
        run,
        detail: `Run ${binding.runId} was created; setup is incomplete because the sealed manifest does not match this Run.`,
      };
    } catch (reconcileError) {
      return {
        outcome: "incomplete",
        binding,
        run,
        detail: `Run ${binding.runId} was created; setup is incomplete. ${errorDetail(reconcileError, errorDetail(error, "Manifest seal could not be confirmed."))}`,
      };
    }
  }
}

export async function executeStartRunAttempt(input: {
  selectedDocumentId: string;
  attempt: StartRunBinding | null;
  phase: StartRunPhase;
  deps: StartRunDeps;
}): Promise<StartRunResult> {
  const { selectedDocumentId, deps } = input;
  let binding = input.attempt;

  if (input.phase === "fresh") {
    const allocated = allocateStartRunId(deps.generateRunId);
    if (!allocated.ok) return { outcome: "blocked", detail: allocated.detail };
    let committed: WorkspaceCommittedRevision;
    try {
      committed = await deps.getCommittedRevision(selectedDocumentId);
    } catch (error) {
      return {
        outcome: "blocked",
        detail: errorDetail(error, "Could not load the selected Runbook committed revision."),
      };
    }
    const bound = bindStartRunAttempt(allocated.runId, selectedDocumentId, committed);
    if (!bound.ok) return { outcome: "blocked", detail: bound.detail };
    binding = bound.binding;
  }

  if (binding == null) {
    return { outcome: "blocked", detail: "Start Run attempt is missing its Run UUID." };
  }
  if (binding.playableArtifactId !== selectedDocumentId) {
    return { outcome: "blocked", binding, detail: "this attempt is bound to a different Runbook" };
  }

  if (input.phase === "retry_seal") {
    let run: PlayRunRecord;
    try {
      run = await deps.getRun(binding.runId);
    } catch (error) {
      return { outcome: "blocked", binding, detail: errorDetail(error, "Could not reload the created Run.") };
    }
    const confirmed = confirmCreatedRun(run, binding);
    if (confirmed.status === "block") {
      return { outcome: "blocked", binding, detail: confirmed.detail };
    }
    return sealExactRun(binding, confirmed.run, deps);
  }

  let run: PlayRunRecord | null = null;
  try {
    run = await deps.putRun(binding.runId, createBody(binding));
  } catch (error) {
    if (errorStatus(error) === 409) {
      return {
        outcome: "blocked",
        binding,
        detail: errorDetail(error, "The Runbook changed before this exact Start Run could bind."),
      };
    }
    const reconciled = await reconcileUnknownCreate(binding, deps);
    if (reconciled.outcome !== "continue_seal") return reconciled;
    run = reconciled.run;
  }

  const confirmed = confirmCreatedRun(run, binding);
  if (confirmed.status === "block") {
    return { outcome: "blocked", binding, detail: confirmed.detail };
  }
  return sealExactRun(binding, confirmed.run, deps);
}
