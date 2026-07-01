import { useEffect, useMemo, useState } from "react";

import { LiveApiError, getManualReviewBed, getManualReviewBeds } from "../../api/liveApi";
import type {
  ManualReviewBedDetail,
  ManualReviewBedSummary,
  ManualReviewEdge,
  ManualReviewNode,
  ManualReviewVariantDetail,
} from "../../api/types";
import {
  ASSISTED_VARIANT,
  BASELINE_VARIANT,
  EDGE_PASS_NAME,
  NODE_PASS_NAMES,
  PASS_LABELS,
  VARIANT_LABELS,
  type ManualReviewPassId,
} from "./manualReviewPasses";

type LoadStatus = "loading" | "ready" | "error";

function bedLabel(bed: ManualReviewBedSummary): string {
  if (bed.source_label) {
    const fileName = bed.source_label.split("/").pop();
    return fileName ?? bed.bed_id;
  }
  return bed.bed_id;
}

function nodesForPass(variant: ManualReviewVariantDetail | undefined, pass: ManualReviewPassId): ManualReviewNode[] {
  if (!variant) return [];
  return variant.nodes.filter((node) => node.pass_name === pass);
}

function goldCounts(variant: ManualReviewVariantDetail | undefined): {
  missingNodes: string[];
  extraNodes: string[];
  missingEdges: string[];
} {
  const gold = variant?.gold_comparison ?? {};
  const asStrings = (value: unknown): string[] =>
    Array.isArray(value) ? value.map((entry) => String(entry)) : [];
  return {
    missingNodes: asStrings(gold.missing_gold_node_labels),
    extraNodes: asStrings(gold.extra_candidate_node_labels),
    missingEdges: asStrings(gold.missing_gold_edge_labels),
  };
}

function NodePill({ node }: { node: ManualReviewNode }) {
  return (
    <li className="manual-review-pill manual-review-pill-detailed">
      <div className="manual-review-pill-row">
        <span className="manual-review-pill-label">{node.label}</span>
        <span className="manual-review-pill-type">{node.node_type}</span>
        {node.confidence ? (
          <span className="manual-review-pill-confidence">confidence: {node.confidence}</span>
        ) : null}
        {node.importance ? (
          <span className="manual-review-pill-importance">importance: {node.importance}</span>
        ) : null}
      </div>
      {node.description ? <p className="manual-review-pill-description">{node.description}</p> : null}
      {node.anchor_quotes.length ? (
        <blockquote className="manual-review-pill-evidence">
          {node.anchor_quotes.map((quote, index) => (
            <span key={index}>&ldquo;{quote}&rdquo;</span>
          ))}
        </blockquote>
      ) : null}
    </li>
  );
}

function EdgePill({ edge }: { edge: ManualReviewEdge }) {
  return (
    <li className="manual-review-pill manual-review-pill-edge manual-review-pill-detailed">
      <div className="manual-review-pill-row">
        <span className="manual-review-pill-label">
          {edge.from_label ?? edge.from_node_id}{" "}
          <span className="manual-review-pill-predicate">{edge.relationship_type}</span>{" "}
          {edge.to_label ?? edge.to_node_id}
        </span>
      </div>
      <div className="manual-review-pill-row">
        {edge.predicate_family ? <span className="manual-review-pill-type">{edge.predicate_family}</span> : null}
        {edge.confidence ? (
          <span className="manual-review-pill-confidence">confidence: {edge.confidence}</span>
        ) : null}
      </div>
      {edge.anchor_quotes.length ? (
        <blockquote className="manual-review-pill-evidence">
          {edge.anchor_quotes.map((quote, index) => (
            <span key={index}>&ldquo;{quote}&rdquo;</span>
          ))}
        </blockquote>
      ) : null}
    </li>
  );
}

function PromptPanel({ pass, promptText }: { pass: ManualReviewPassId; promptText: string }) {
  return (
    <section className="manual-review-prompt-panel" aria-label="Vocabulary prompt for active pass">
      <header className="manual-review-column-header">
        <h4>Vocabulary prompt</h4>
        <span className="manual-review-column-meta">{PASS_LABELS[pass]} pass</span>
      </header>
      <pre className="manual-review-prompt-text">
        {promptText.trim() ? promptText : "(No vocabulary context rendered for this pass.)"}
      </pre>
    </section>
  );
}

function VariantColumn({
  variantName,
  variant,
  activePass,
}: {
  variantName: string;
  variant: ManualReviewVariantDetail | undefined;
  activePass: ManualReviewPassId;
}) {
  const isEdgePass = activePass === EDGE_PASS_NAME;
  const nodes = isEdgePass ? [] : nodesForPass(variant, activePass);
  const edges = isEdgePass ? variant?.edges ?? [] : [];
  const gold = goldCounts(variant);

  return (
    <div className="manual-review-column">
      <header className="manual-review-column-header">
        <h4>{VARIANT_LABELS[variantName] ?? variantName}</h4>
        <span className="manual-review-column-meta">
          {variant ? `${variant.node_count} nodes · ${variant.edge_count} edges total` : "no data"}
        </span>
      </header>

      {isEdgePass ? (
        <>
          <p className="manual-review-column-note">{edges.length} edges extracted</p>
          <ul className="manual-review-pill-list">
            {edges.map((edge) => (
              <EdgePill key={edge.edge_id} edge={edge} />
            ))}
            {edges.length === 0 ? <li className="manual-review-empty">No edges extracted.</li> : null}
          </ul>
        </>
      ) : (
        <>
          <p className="manual-review-column-note">{nodes.length} nodes for this pass</p>
          <ul className="manual-review-pill-list">
            {nodes.map((node) => (
              <NodePill key={node.node_id} node={node} />
            ))}
            {nodes.length === 0 ? <li className="manual-review-empty">No nodes extracted for this pass.</li> : null}
          </ul>
        </>
      )}

      {gold.missingNodes.length || gold.extraNodes.length || gold.missingEdges.length ? (
        <details className="manual-review-gold-panel">
          <summary>Gold reference (whole bed, not just this pass)</summary>
          {gold.missingNodes.length ? (
            <p>
              <strong>Missing gold nodes:</strong> {gold.missingNodes.join(", ")}
            </p>
          ) : null}
          {gold.extraNodes.length ? (
            <p>
              <strong>Extra nodes not in gold:</strong> {gold.extraNodes.join(", ")}
            </p>
          ) : null}
          {gold.missingEdges.length ? (
            <p>
              <strong>Missing gold edges:</strong> {gold.missingEdges.join(", ")}
            </p>
          ) : null}
        </details>
      ) : null}
    </div>
  );
}

export function ManualReviewModule() {
  const [beds, setBeds] = useState<ManualReviewBedSummary[]>([]);
  const [bedsStatus, setBedsStatus] = useState<LoadStatus>("loading");
  const [bedsError, setBedsError] = useState<string | null>(null);
  const [selectedBedId, setSelectedBedId] = useState<string | null>(null);

  const [bedDetail, setBedDetail] = useState<ManualReviewBedDetail | null>(null);
  const [detailStatus, setDetailStatus] = useState<LoadStatus>("loading");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [activePass, setActivePass] = useState<ManualReviewPassId>("actor_pass");

  useEffect(() => {
    let cancelled = false;
    setBedsStatus("loading");
    void getManualReviewBeds()
      .then((response) => {
        if (cancelled) return;
        setBeds(response.beds);
        setSelectedBedId((current) => current ?? response.beds[0]?.bed_id ?? null);
        setBedsStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setBedsStatus("error");
        setBedsError(error instanceof Error ? error.message : "Failed to load manual review beds.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedBedId) return;
    let cancelled = false;
    setDetailStatus("loading");
    setDetailError(null);
    void getManualReviewBed(selectedBedId)
      .then((response) => {
        if (cancelled) return;
        setBedDetail(response);
        setDetailStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setBedDetail(null);
        setDetailStatus("error");
        setDetailError(
          error instanceof LiveApiError || error instanceof Error
            ? error.message
            : "Failed to load manual review bed.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [selectedBedId]);

  const passTabs = useMemo<ManualReviewPassId[]>(() => [...NODE_PASS_NAMES, EDGE_PASS_NAME], []);

  const promptText =
    activePass === EDGE_PASS_NAME
      ? bedDetail?.edge_prompt_context ?? ""
      : bedDetail?.node_prompt_contexts[activePass] ?? "";

  return (
    <div className="manual-review-root">
      <header className="manual-review-header">
        <p className="plan-surface-kicker">Vocabulary ablation dogfood · developer tool</p>
        <h2>Baseline vs vocabulary-assisted graph review</h2>
        <p className="manual-review-lede">
          Prompt, baseline, and vocabulary-assisted extraction for the active pass — side by side. Read-only diagnostic surface, no writes.
        </p>
      </header>

      {bedsStatus === "loading" ? <p className="plan-projection-empty">Loading review beds…</p> : null}
      {bedsStatus === "error" ? <p className="graph-preview-error">{bedsError}</p> : null}

      {bedsStatus === "ready" ? (
        <div className="manual-review-bed-picker" role="tablist" aria-label="Vocabulary ablation beds">
          {beds.map((bed) => (
            <button
              key={bed.bed_id}
              type="button"
              role="tab"
              aria-selected={bed.bed_id === selectedBedId}
              className={
                bed.bed_id === selectedBedId ? "graph-gold-review-pill active" : "graph-gold-review-pill"
              }
              onClick={() => setSelectedBedId(bed.bed_id)}
            >
              {bedLabel(bed)}
            </button>
          ))}
        </div>
      ) : null}

      {detailStatus === "loading" ? <p className="plan-projection-empty">Loading bed detail…</p> : null}
      {detailStatus === "error" ? <p className="graph-preview-error">{detailError}</p> : null}

      {detailStatus === "ready" && bedDetail ? (
        <>
          <div className="manual-review-pass-tabs" role="tablist" aria-label="Extraction passes">
            {passTabs.map((pass) => (
              <button
                key={pass}
                type="button"
                role="tab"
                aria-selected={pass === activePass}
                className={pass === activePass ? "graph-gold-review-pill active" : "graph-gold-review-pill"}
                onClick={() => setActivePass(pass)}
              >
                {PASS_LABELS[pass]}
              </button>
            ))}
          </div>

          <PromptPanel pass={activePass} promptText={promptText} />

          <div className="manual-review-columns" aria-label="Baseline vs vocabulary-assisted extraction">
            <VariantColumn
              variantName={BASELINE_VARIANT}
              variant={bedDetail.variants[BASELINE_VARIANT]}
              activePass={activePass}
            />
            <VariantColumn
              variantName={ASSISTED_VARIANT}
              variant={bedDetail.variants[ASSISTED_VARIANT]}
              activePass={activePass}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
