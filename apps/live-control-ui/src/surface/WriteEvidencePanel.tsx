import type { PatchArtifactMetadata, ProjectionWriteResult } from "../api/types";

export interface WriteEvidencePanelProps {
  result: ProjectionWriteResult;
  refreshedArtifactToken?: string | null;
  refreshError?: string | null;
}

function getPatchMetadata(result: ProjectionWriteResult): PatchArtifactMetadata["patch"] | null {
  const metadata = result.metadata;
  if (metadata == null || typeof metadata !== "object") {
    return null;
  }
  const patchRaw = (metadata as PatchArtifactMetadata).patch;
  if (patchRaw == null || typeof patchRaw !== "object") {
    return null;
  }
  return patchRaw;
}

export function WriteEvidencePanel({
  result,
  refreshedArtifactToken = null,
  refreshError = null,
}: WriteEvidencePanelProps) {
  const patch = getPatchMetadata(result);
  const hasRefreshError = typeof refreshError === "string" && refreshError.length > 0;
  const afterToken = patch?.file_state_token_after ?? null;
  const canCompareTokens =
    result.status === "accepted" &&
    typeof afterToken === "string" &&
    afterToken.length > 0 &&
    typeof refreshedArtifactToken === "string" &&
    refreshedArtifactToken.length > 0;
  const tokenMatch = canCompareTokens ? afterToken === refreshedArtifactToken : false;

  return (
    <section className="write-evidence-panel" aria-label="Write evidence panel">
      <h4 className="artifact-subtitle">Write evidence</h4>
      <p className="write-result-title">Status: {result.status}</p>

      {result.status === "accepted" ? (
        <p className="module-muted">Patch accepted.</p>
      ) : null}
      {result.status === "noop" ? (
        <p className="module-muted">No patch was applied.</p>
      ) : null}
      {result.status === "conflict" ? (
        <p className="module-muted">Patch not applied due to conflict.</p>
      ) : null}
      {result.status === "rejected" ? (
        <p className="module-muted">Patch not applied due to rejection.</p>
      ) : null}

      {result.events_appended.map((eventId) => (
        <p key={eventId} className="module-muted">
          Audit event: {eventId}
        </p>
      ))}
      {result.artifacts_changed.map((changed) => (
        <p key={`${changed.target_type}:${changed.target_id}`} className="module-muted">
          Changed artifact: {changed.target_type} {changed.target_id}
        </p>
      ))}
      {result.invalidations.map((invalidation, index) => (
        <p key={`${invalidation.projection_key}:${index}`} className="module-muted">
          Invalidated projection: {invalidation.projection_key}
        </p>
      ))}

      {patch?.source_path ? (
        <p className="module-muted">Source path: {patch.source_path}</p>
      ) : null}
      {patch?.file_state_token_before ? (
        <p className="module-muted">Before token: {patch.file_state_token_before}</p>
      ) : null}
      {patch?.file_state_token_after ? (
        <p className="module-muted">After token: {patch.file_state_token_after}</p>
      ) : null}
      {refreshedArtifactToken ? (
        <p className="module-muted">Refreshed token: {refreshedArtifactToken}</p>
      ) : null}
      {typeof patch?.replacement_count === "number" ? (
        <p className="module-muted">Replacement count: {patch.replacement_count}</p>
      ) : null}

      {result.status === "accepted" && hasRefreshError ? (
        <>
          <p className="module-error">
            Patch accepted, but refresh failed. The patch command returned accepted. Refresh the pane
            before making another patch.
          </p>
          <p className="module-muted">Refresh error: {refreshError}</p>
        </>
      ) : null}

      {result.status === "accepted" && !hasRefreshError && canCompareTokens && tokenMatch ? (
        <p className="module-muted">Verified: refreshed artifact matches patched state.</p>
      ) : null}

      {result.status === "accepted" && !hasRefreshError && canCompareTokens && !tokenMatch ? (
        <p className="module-error">
          Patch accepted, but refreshed artifact token did not match the write result. Refresh again
          before making another patch.
        </p>
      ) : null}

      {result.conflicts.map((conflict, index) => (
        <p key={`${conflict.conflict_type}:${index}`} className="module-muted">
          {conflict.conflict_type}: {conflict.message}
        </p>
      ))}
      {result.diagnostics.map((diag, index) => (
        <p key={`${diag}:${index}`} className="module-muted">
          {diag}
        </p>
      ))}
    </section>
  );
}
