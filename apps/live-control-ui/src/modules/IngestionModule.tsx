import { useMemo, useState } from "react";

import { postRecapIngest } from "../api/recapIngestApi";
import type { RecapIngestStatus } from "../api/types";
import { AuthorityTransitionPanel } from "./AuthorityTransitionPanel";
import { IngestionStatusPanel } from "./IngestionStatusPanel";
import { SpellingAuditPanel } from "./SpellingAuditPanel";

interface IngestionModuleProps {
  campaignId: string;
  session: number;
}

type IngestionPaneState =
  | { status: "idle" }
  | { status: "previewing" }
  | { status: "preview_ready"; result: RecapIngestStatus }
  | { status: "applying" }
  | { status: "applied"; result: RecapIngestStatus }
  | { status: "breadcrumb_required"; result: RecapIngestStatus }
  | { status: "materializing" }
  | { status: "ready_for_planning_activation"; result: RecapIngestStatus }
  | { status: "error"; result?: RecapIngestStatus; message?: string };

function isNonGenericSlugOrTitle(slug: string, title: string): boolean {
  const normalizedSlug = slug.trim().toLowerCase().replace(/:$/, "");
  if (normalizedSlug && normalizedSlug !== "recap") {
    return true;
  }
  const normalizedTitle = title.trim();
  if (!normalizedTitle) {
    return false;
  }
  const match = normalizedTitle.match(/^Session\s+\d+\s*-\s*(.+)$/i);
  const tail = (match ? match[1] : normalizedTitle).trim().toLowerCase().replace(/:$/, "");
  return tail !== "" && tail !== "recap";
}

function hasState(result: RecapIngestStatus | null, state: string): boolean {
  return Boolean(result && result.states.includes(state));
}

export function IngestionModule({ campaignId, session }: IngestionModuleProps) {
  const [rawText, setRawText] = useState("");
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [forceStage, setForceStage] = useState(false);
  const [forceRecap, setForceRecap] = useState(false);
  const [retryAfterBreadcrumb, setRetryAfterBreadcrumb] = useState(false);
  const [state, setState] = useState<IngestionPaneState>({ status: "idle" });
  const [latestResult, setLatestResult] = useState<RecapIngestStatus | null>(null);
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const currentSignature = useMemo(
    () => JSON.stringify({ rawText: rawText.trim(), slug: slug.trim(), title: title.trim() }),
    [rawText, slug, title],
  );
  const previewInvalidated = previewSignature != null && previewSignature !== currentSignature;
  const busy = ["previewing", "applying", "materializing"].includes(state.status);
  const hasPreview =
    hasState(latestResult, "recap_preview_created") &&
    !previewInvalidated &&
    previewSignature === currentSignature;
  const genericGuardPass = isNonGenericSlugOrTitle(slug, title);
  const canMaterialize =
    !busy &&
    !!latestResult &&
    (hasState(latestResult, "breadcrumb_found") || retryAfterBreadcrumb);

  async function stagePreview() {
    setState({ status: "previewing" });
    try {
      const result = await postRecapIngest({
        operation: "stage_preview",
        campaign_id: campaignId,
        session,
        raw_text: rawText,
        slug: slug.trim() || undefined,
        title: title.trim() || undefined,
        force_stage: forceStage || undefined,
      });
      setLatestResult(result);
      setPreviewSignature(currentSignature);
      if (result.status === "breadcrumb_required") {
        setState({ status: "breadcrumb_required", result });
      } else {
        setState({ status: "preview_ready", result });
      }
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Stage + Preview failed",
      });
    }
  }

  async function applyNormalize() {
    setState({ status: "applying" });
    try {
      const result = await postRecapIngest({
        operation: "apply_normalize",
        campaign_id: campaignId,
        session,
        slug: slug.trim() || undefined,
        title: title.trim() || undefined,
        force_recap: forceRecap || undefined,
      });
      setLatestResult(result);
      if (result.status === "breadcrumb_required") {
        setState({ status: "breadcrumb_required", result });
      } else {
        setState({ status: "applied", result });
      }
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Apply + Normalize failed",
      });
    }
  }

  async function materializeSessionMemory() {
    setState({ status: "materializing" });
    try {
      const result = await postRecapIngest({
        operation: "materialize_session_memory",
        campaign_id: campaignId,
        session,
        slug: slug.trim() || undefined,
        title: title.trim() || undefined,
        check: true,
      });
      setLatestResult(result);
      if (result.status === "ready_for_planning_activation") {
        setState({ status: "ready_for_planning_activation", result });
      } else if (result.status === "breadcrumb_required") {
        setState({ status: "breadcrumb_required", result });
      } else {
        setState({ status: "applied", result });
      }
    } catch (error) {
      setState({
        status: "error",
        result: latestResult ?? undefined,
        message: error instanceof Error ? error.message : "Session memory materialization failed",
      });
    }
  }

  return (
    <div className="module-panel ingestion-module" data-module-id="ingestion">
      <h2 className="module-title">Raw Recap Ingestion</h2>
      <p className="module-muted">Operator prep tool over the PR92 ingestion orchestrator.</p>
      <p className="module-muted">
        Campaign: <strong>{campaignId}</strong> · Session: <strong>{session}</strong>
      </p>

      <label htmlFor="ingestion-slug">Slug</label>
      <input
        id="ingestion-slug"
        value={slug}
        onChange={(event) => setSlug(event.target.value)}
        placeholder="Mireward Road and Lysandro"
      />

      <label htmlFor="ingestion-title">Title (optional)</label>
      <input
        id="ingestion-title"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder="Session 22 - Mireward Road and Lysandro"
      />

      <label htmlFor="ingestion-raw-text">Raw recap text</label>
      <textarea
        id="ingestion-raw-text"
        value={rawText}
        onChange={(event) => setRawText(event.target.value)}
        rows={12}
        placeholder="Session 22 Recap&#10;&#10;The group turns their focus..."
      />

      <details>
        <summary>Advanced overwrite controls</summary>
        <label>
          <input
            type="checkbox"
            checked={showAdvanced}
            onChange={(event) => setShowAdvanced(event.target.checked)}
          />{" "}
          Enable overwrite toggles
        </label>
        {showAdvanced ? (
          <div className="ingestion-advanced-options">
            <label>
              <input
                type="checkbox"
                checked={forceStage}
                onChange={(event) => setForceStage(event.target.checked)}
              />{" "}
              Overwrite staged raw notes (`--force-stage`)
            </label>
            <label>
              <input
                type="checkbox"
                checked={forceRecap}
                onChange={(event) => setForceRecap(event.target.checked)}
              />{" "}
              Overwrite existing canonical recap (`--force-recap`)
            </label>
          </div>
        ) : null}
      </details>

      <div className="ingestion-actions">
        <button
          type="button"
          onClick={stagePreview}
          disabled={busy || rawText.trim().length === 0}
        >
          Stage + Preview
        </button>
        <button
          type="button"
          onClick={applyNormalize}
          disabled={busy || !hasPreview || !genericGuardPass}
        >
          Apply + Normalize
        </button>
        <button type="button" onClick={materializeSessionMemory} disabled={!canMaterialize}>
          Materialize Session Memory
        </button>
      </div>

      {latestResult?.status === "breadcrumb_required" ? (
        <label>
          <input
            type="checkbox"
            checked={retryAfterBreadcrumb}
            onChange={(event) => setRetryAfterBreadcrumb(event.target.checked)}
          />{" "}
          I added breadcrumb artifact; retry materialization.
        </label>
      ) : null}

      {previewInvalidated ? (
        <p className="module-muted">Preview invalidated by raw text/slug/title edits. Re-run Stage + Preview.</p>
      ) : null}
      {!genericGuardPass ? (
        <p className="module-muted">Apply is disabled until slug/title is non-generic.</p>
      ) : null}

      <IngestionStatusPanel result={latestResult} />
      <AuthorityTransitionPanel result={latestResult} />
      <SpellingAuditPanel result={latestResult} />

      {state.status === "error" ? (
        <p className="module-error">{state.message ?? "Ingestion operation failed."}</p>
      ) : null}
      {state.status === "ready_for_planning_activation" ? (
        <p className="module-success">ready_for_planning_activation</p>
      ) : null}
    </div>
  );
}
