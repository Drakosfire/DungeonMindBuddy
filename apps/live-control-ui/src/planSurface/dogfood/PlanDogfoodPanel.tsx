import { useCallback, useEffect, useMemo, useState } from "react";

import type { PlanSessionDescriptor } from "../types";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
import { buildPlanDogfoodReport } from "./planDogfoodReport";
import {
  clearPlanDogfoodState,
  loadPlanDogfoodState,
  PLAN_DOGFOOD_CHECKLIST,
  savePlanDogfoodState,
  togglePlanDogfoodChecklistItem,
  updatePlanDogfoodNotes,
  type PlanDogfoodState,
} from "./planDogfoodState";

export interface PlanDogfoodPanelProps {
  sessionDescriptor: PlanSessionDescriptor;
  saveStatusLabel: string;
}

type CopyStatus = "idle" | "copied" | "error";

export function PlanDogfoodPanel({
  sessionDescriptor,
  saveStatusLabel,
}: PlanDogfoodPanelProps) {
  const { projection, projectionState, projectionError } = usePlanGraphReferenceResolver();
  const [collapsed, setCollapsed] = useState(false);
  const [state, setState] = useState<PlanDogfoodState>(() =>
    loadPlanDogfoodState(window.localStorage, sessionDescriptor),
  );
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");

  useEffect(() => {
    setState(loadPlanDogfoodState(window.localStorage, sessionDescriptor));
  }, [sessionDescriptor]);

  const persist = useCallback(
    (next: PlanDogfoodState) => {
      setState(next);
      savePlanDogfoodState(window.localStorage, sessionDescriptor, next);
    },
    [sessionDescriptor],
  );

  const reportMarkdown = useMemo(
    () =>
      buildPlanDogfoodReport({
        sessionDescriptor,
        checklist: PLAN_DOGFOOD_CHECKLIST,
        state,
        saveStatusLabel,
        graphSnapshot: projection?.snapshot ?? null,
        generatedAt: new Date().toISOString(),
      }),
    [sessionDescriptor, state, saveStatusLabel, projection?.snapshot],
  );

  const handleToggle = (itemId: string, checked: boolean) => {
    persist(togglePlanDogfoodChecklistItem(state, itemId, checked));
  };

  const handleNotesChange = (notes: string) => {
    persist(updatePlanDogfoodNotes(state, notes));
  };

  const handleReset = () => {
    clearPlanDogfoodState(window.localStorage, sessionDescriptor);
    setState(loadPlanDogfoodState(window.localStorage, sessionDescriptor));
    setCopyStatus("idle");
  };

  const handleCopyReport = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(reportMarkdown);
        setCopyStatus("copied");
        return;
      }
      throw new Error("Clipboard API unavailable");
    } catch {
      setCopyStatus("error");
    }
  };

  return (
    <section
      className="plan-dogfood-panel"
      aria-label="Dogfood checklist"
      data-testid="plan-dogfood-panel"
    >
      <header className="plan-dogfood-header">
        <div className="plan-dogfood-header-copy">
          <p className="plan-surface-kicker">Dogfood mode</p>
          <h2 className="plan-dogfood-title">Dogfood checklist</h2>
          <p className="plan-dogfood-subtitle">
            Use this to smoke-test real prep, saving, recovery, references, source preview, and prep
            memory.
          </p>
        </div>
        <button
          type="button"
          className="plan-dogfood-collapse"
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((value) => !value)}
        >
          {collapsed ? "Expand" : "Collapse"}
        </button>
      </header>

      {!collapsed ? (
        <div className="plan-dogfood-body">
          <ul className="plan-dogfood-checklist">
            {PLAN_DOGFOOD_CHECKLIST.map((item) => (
              <li key={item.id}>
                <label className="plan-dogfood-check-item">
                  <input
                    type="checkbox"
                    checked={Boolean(state.checked[item.id])}
                    onChange={(event) => handleToggle(item.id, event.target.checked)}
                  />
                  <span>{item.label}</span>
                </label>
              </li>
            ))}
          </ul>

          <section aria-label="World Graph snapshot" data-testid="plan-world-graph-snapshot">
            <p className="plan-surface-kicker">World Graph snapshot</p>
            {projection ? (
              <>
                <p>Revision: <code>{projection.snapshot.revisionId}</code></p>
                <p>
                  {projection.snapshot.worldId} · {projection.snapshot.campaignId} ·{" "}
                  {projection.snapshot.focus.kind === "session"
                    ? projection.snapshot.focus.sessionId
                    : "no focus"}
                </p>
              </>
            ) : (
              <p>
                {projectionState === "error"
                  ? `World Graph failed to load: ${projectionError ?? "unknown error"}`
                  : "World Graph unavailable."}
              </p>
            )}
          </section>

          <label className="plan-dogfood-notes-label" htmlFor="plan-dogfood-notes">
            Dogfood notes
          </label>
          <textarea
            id="plan-dogfood-notes"
            className="plan-dogfood-notes"
            value={state.notes}
            placeholder="What broke? What felt useful? What felt too graph-y? What did you expect to see but didn't?"
            rows={4}
            onChange={(event) => handleNotesChange(event.target.value)}
          />

          <div className="plan-dogfood-actions">
            <button type="button" className="plan-dogfood-copy" onClick={() => void handleCopyReport()}>
              Copy dogfood report
            </button>
            <button type="button" className="plan-dogfood-reset" onClick={handleReset}>
              Reset dogfood checklist
            </button>
          </div>

          {copyStatus === "copied" ? (
            <p className="plan-dogfood-status plan-dogfood-status-success" role="status">
              Dogfood report copied.
            </p>
          ) : null}
          {copyStatus === "error" ? (
            <div className="plan-dogfood-status plan-dogfood-status-error" role="alert">
              <p>Could not copy to clipboard. Use the report preview below.</p>
              <details className="plan-dogfood-report-preview">
                <summary>Report preview</summary>
                <pre>{reportMarkdown}</pre>
              </details>
            </div>
          ) : null}

          <p className="plan-dogfood-reset-note">
            Only clears dogfood checklist and notes. Does not change the prep board.
          </p>
        </div>
      ) : null}
    </section>
  );
}
