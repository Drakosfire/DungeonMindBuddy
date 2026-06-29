import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getGoldReviewCompare,
  getGoldReviewEvidence,
  getGoldReviewSessions,
  LiveApiError,
} from "../../api/liveApi";
import type {
  GoldReviewCompareResponse,
  GoldReviewEvidenceDiffResponse,
  GoldReviewSessionSummary,
} from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { GraphGoldEvidenceDiff } from "./GraphGoldEvidenceDiff";
import { GraphGoldReviewMissTables } from "./GraphGoldReviewMissTables";
import { GraphGoldReviewRunPicker } from "./GraphGoldReviewRunPicker";
import { GraphGoldReviewScorecard } from "./GraphGoldReviewScorecard";
import { GraphGoldReviewSessionPicker } from "./GraphGoldReviewSessionPicker";
import {
  pickDefaultManifestPath,
  pickDefaultSession,
  requestedSessionFromLocation,
  syncGoldReviewUrl,
  type GoldReviewSelection,
} from "./graphGoldReviewUtils";

interface GraphGoldReviewModuleProps {
  context: PlanContextDescriptor;
}

export function GraphGoldReviewModule({ context }: GraphGoldReviewModuleProps) {
  const requestedSessionId = requestedSessionFromLocation();
  const fallbackSessionId = `session-${context.ingestSession}`;

  const [sessions, setSessions] = useState<GoldReviewSessionSummary[]>([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState(
    requestedSessionId ?? fallbackSessionId,
  );
  const [selectedManifestPath, setSelectedManifestPath] = useState<string | null>(null);
  const [compare, setCompare] = useState<GoldReviewCompareResponse | null>(null);
  const [compareStatus, setCompareStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [compareError, setCompareError] = useState<string | null>(null);
  const [selection, setSelection] = useState<GoldReviewSelection | null>(null);
  const [evidenceDiff, setEvidenceDiff] = useState<GoldReviewEvidenceDiffResponse | null>(null);
  const [evidenceStatus, setEvidenceStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  const selectedSession = useMemo(
    () => sessions.find((session) => session.session_id === selectedSessionId),
    [sessions, selectedSessionId],
  );

  useEffect(() => {
    let cancelled = false;
    setSessionsLoaded(false);
    setSessionsError(null);
    void getGoldReviewSessions()
      .then((response) => {
        if (cancelled) return;
        setSessions(response.sessions);
        const nextSessionId = pickDefaultSession(
          response.sessions,
          requestedSessionId,
          fallbackSessionId,
        );
        setSelectedSessionId(nextSessionId);
        const session = response.sessions.find((item) => item.session_id === nextSessionId);
        setSelectedManifestPath(pickDefaultManifestPath(session));
        setSessionsLoaded(true);
      })
      .catch((error) => {
        if (cancelled) return;
        setSessions([]);
        setSessionsError(error instanceof Error ? error.message : "Failed to load gold sessions.");
        setSessionsLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [fallbackSessionId, requestedSessionId]);

  const loadCompare = useCallback(async () => {
    if (!selectedSessionId) return;
    setCompareStatus("loading");
    setCompareError(null);
    setSelection(null);
    setEvidenceDiff(null);
    setEvidenceStatus("idle");
    setEvidenceError(null);
    try {
      const response = await getGoldReviewCompare({
        campaignId: context.campaignId,
        sessionId: selectedSessionId,
        manifestPath: selectedManifestPath ?? undefined,
      });
      setCompare(response);
      setCompareStatus("ready");
    } catch (error) {
      setCompare(null);
      setCompareStatus("error");
      if (error instanceof LiveApiError) {
        setCompareError(error.message);
        return;
      }
      setCompareError(error instanceof Error ? error.message : "Failed to load comparison.");
    }
  }, [context.campaignId, selectedManifestPath, selectedSessionId]);

  useEffect(() => {
    if (!sessionsLoaded) return;
    void loadCompare();
  }, [loadCompare, sessionsLoaded]);

  const handleSessionSelect = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    syncGoldReviewUrl(sessionId);
    const session = sessions.find((item) => item.session_id === sessionId);
    setSelectedManifestPath(pickDefaultManifestPath(session));
  };

  const handleSelection = (next: GoldReviewSelection) => {
    setSelection(next);
  };

  useEffect(() => {
    if (!selection || !selectedSessionId) return;
    let cancelled = false;
    setEvidenceStatus("loading");
    setEvidenceError(null);
    void getGoldReviewEvidence({
      campaignId: context.campaignId,
      sessionId: selectedSessionId,
      manifestPath: selectedManifestPath ?? undefined,
      objectKind: selection.objectKind,
      objectId: selection.objectId,
    })
      .then((response) => {
        if (cancelled) return;
        setEvidenceDiff(response);
        setEvidenceStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setEvidenceDiff(null);
        setEvidenceStatus("error");
        setEvidenceError(error instanceof Error ? error.message : "Failed to load evidence diff.");
      });
    return () => {
      cancelled = true;
    };
  }, [context.campaignId, selectedManifestPath, selectedSessionId, selection]);

  if (!sessionsLoaded) {
    return <p className="plan-projection-empty">Loading graph gold review…</p>;
  }

  return (
    <div className="graph-gold-review-root">
      <header className="graph-gold-review-header">
        <div>
          <p className="plan-surface-kicker">Developer tool</p>
          <h2>Graph Gold Review</h2>
          <p className="graph-gold-review-lede">
            Compare live graph-ingest output against hand-authored gold for sessions with fixtures.
          </p>
        </div>
        {selectedSession ? (
          <p className="graph-gold-review-meta">
            Gold fixture · <code>{selectedSession.gold_fixture_id}</code>
          </p>
        ) : null}
      </header>

      {sessionsError ? <p className="graph-gold-review-error">{sessionsError}</p> : null}

      <GraphGoldReviewSessionPicker
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        onSelect={handleSessionSelect}
      />

      <GraphGoldReviewRunPicker
        runs={selectedSession?.available_runs ?? []}
        selectedManifestPath={selectedManifestPath}
        onSelect={setSelectedManifestPath}
      />

      {compareStatus === "loading" ? (
        <p className="graph-gold-review-note">Loading gold vs live comparison…</p>
      ) : null}
      {compareError ? <p className="graph-gold-review-error">{compareError}</p> : null}

      <div className="graph-gold-review-layout">
        <div className="graph-gold-review-main">
          <GraphGoldReviewScorecard compare={compareStatus === "ready" ? compare : null} />
          <GraphGoldReviewMissTables
            compare={compareStatus === "ready" ? compare : null}
            selection={selection}
            onSelect={handleSelection}
          />
        </div>
        <aside className="graph-gold-review-inspector">
          <GraphGoldEvidenceDiff
            diff={evidenceStatus === "ready" ? evidenceDiff : null}
            loading={evidenceStatus === "loading"}
            error={evidenceError}
          />
        </aside>
      </div>
    </div>
  );
}
