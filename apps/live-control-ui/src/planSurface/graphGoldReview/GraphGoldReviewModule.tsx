import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getGoldReviewCompare,
  getGoldReviewEvidence,
  getGoldReviewSessions,
  getGoldReviewVocabularyAblation,
  LiveApiError,
} from "../../api/liveApi";
import type {
  GoldReviewCompareResponse,
  GoldReviewEvidenceDiffResponse,
  GoldReviewSessionSummary,
  VocabularyAblationDogfoodResponse,
} from "../../api/types";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import type { PlanContextDescriptor } from "../types";
import {
  resolveInitialReviewCampaignId,
  sessionsForReviewCampaign,
  syncReviewCampaignUrl,
} from "../sessionCampaignContext";
import { GraphGoldEvidenceDiff } from "./GraphGoldEvidenceDiff";
import { GraphGoldReviewMissTables } from "./GraphGoldReviewMissTables";
import { GraphGoldReviewRunPicker } from "./GraphGoldReviewRunPicker";
import { GraphGoldReviewScorecard } from "./GraphGoldReviewScorecard";
import { GraphGoldReviewSessionPicker } from "./GraphGoldReviewSessionPicker";
import { GraphGoldReviewVocabularyAblation } from "./GraphGoldReviewVocabularyAblation";
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
  const [selectedCampaignId, setSelectedCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
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
  const [vocabAblation, setVocabAblation] = useState<VocabularyAblationDogfoodResponse | null>(null);
  const [vocabStatus, setVocabStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [vocabError, setVocabError] = useState<string | null>(null);

  const campaignSessions = useMemo(
    () => sessionsForReviewCampaign(sessions, selectedCampaignId),
    [selectedCampaignId, sessions],
  );

  const selectedSession = useMemo(
    () => campaignSessions.find((session) => session.session_id === selectedSessionId),
    [campaignSessions, selectedSessionId],
  );

  const effectiveCampaignId = useMemo(() => {
    if (selectedSession?.campaign_id) {
      return selectedSession.campaign_id;
    }
    return selectedCampaignId;
  }, [selectedCampaignId, selectedSession?.campaign_id]);

  const showVocabularyAblation = selectedSessionId === "session-23";

  useEffect(() => {
    let cancelled = false;
    setSessionsLoaded(false);
    setSessionsError(null);
    void getGoldReviewSessions()
      .then((response) => {
        if (cancelled) return;
        setSessions(response.sessions);
        const initialCampaignId = resolveInitialReviewCampaignId(context.campaignId);
        const visibleSessions = sessionsForReviewCampaign(response.sessions, initialCampaignId);
        const nextSessionId = pickDefaultSession(
          visibleSessions,
          requestedSessionId,
          fallbackSessionId,
        );
        setSelectedCampaignId(initialCampaignId);
        setSelectedSessionId(nextSessionId);
        const session = visibleSessions.find((item) => item.session_id === nextSessionId);
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
  }, [context.campaignId, fallbackSessionId, requestedSessionId]);

  const loadCompare = useCallback(async () => {
    if (!selectedSessionId || !selectedSession) return;
    setCompareStatus("loading");
    setCompareError(null);
    setSelection(null);
    setEvidenceDiff(null);
    setEvidenceStatus("idle");
    setEvidenceError(null);
    try {
      const response = await getGoldReviewCompare({
        campaignId: effectiveCampaignId,
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
  }, [effectiveCampaignId, selectedManifestPath, selectedSession, selectedSessionId]);

  useEffect(() => {
    if (!sessionsLoaded) return;
    void loadCompare();
  }, [loadCompare, sessionsLoaded]);

  useEffect(() => {
    if (!sessionsLoaded || !showVocabularyAblation) {
      setVocabAblation(null);
      setVocabStatus("idle");
      setVocabError(null);
      return;
    }
    let cancelled = false;
    setVocabStatus("loading");
    setVocabError(null);
    void getGoldReviewVocabularyAblation({
      campaignId: effectiveCampaignId,
      sessionId: selectedSessionId,
    })
      .then((response) => {
        if (cancelled) return;
        setVocabAblation(response);
        setVocabStatus("ready");
      })
      .catch((error) => {
        if (cancelled) return;
        setVocabAblation(null);
        setVocabStatus("error");
        if (error instanceof LiveApiError) {
          setVocabError(error.message);
          return;
        }
        setVocabError(
          error instanceof Error ? error.message : "Failed to load vocabulary ablation dogfood.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [effectiveCampaignId, selectedSessionId, sessionsLoaded, showVocabularyAblation]);

  const handleCampaignSelect = (campaignId: string) => {
    setSelectedCampaignId(campaignId);
    syncReviewCampaignUrl(campaignId);
    const visibleSessions = sessionsForReviewCampaign(sessions, campaignId);
    const stillVisible = visibleSessions.some((session) => session.session_id === selectedSessionId);
    if (stillVisible) {
      syncGoldReviewUrl(selectedSessionId, campaignId);
      return;
    }
    const nextSessionId = pickDefaultSession(visibleSessions, null, fallbackSessionId);
    setSelectedSessionId(nextSessionId);
    const session = visibleSessions.find((item) => item.session_id === nextSessionId);
    setSelectedManifestPath(pickDefaultManifestPath(session));
    syncGoldReviewUrl(nextSessionId, campaignId);
  };

  const handleSessionSelect = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    syncGoldReviewUrl(sessionId, selectedCampaignId);
    const session = campaignSessions.find((item) => item.session_id === sessionId);
    setSelectedManifestPath(pickDefaultManifestPath(session));
  };

  const handleSelection = (next: GoldReviewSelection) => {
    setSelection(next);
  };

  useEffect(() => {
    if (!selection || !selectedSessionId || !selectedSession) return;
    let cancelled = false;
    setEvidenceStatus("loading");
    setEvidenceError(null);
    void getGoldReviewEvidence({
      campaignId: effectiveCampaignId,
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
  }, [effectiveCampaignId, selectedManifestPath, selectedSession, selectedSessionId, selection]);

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

      <div className="graph-gold-review-controls">
        <ReviewCampaignPicker selectedCampaignId={selectedCampaignId} onSelect={handleCampaignSelect} />
        <GraphGoldReviewSessionPicker
          sessions={campaignSessions}
          selectedSessionId={selectedSessionId}
          onSelect={handleSessionSelect}
        />
      </div>

      <GraphGoldReviewRunPicker
        runs={selectedSession?.available_runs ?? []}
        selectedManifestPath={selectedManifestPath}
        onSelect={setSelectedManifestPath}
      />

      {compareStatus === "loading" ? (
        <p className="graph-gold-review-note">Loading gold vs live comparison…</p>
      ) : null}
      {compareError ? <p className="graph-gold-review-error">{compareError}</p> : null}

      {showVocabularyAblation ? (
        <GraphGoldReviewVocabularyAblation
          data={vocabStatus === "ready" ? vocabAblation : null}
          loading={vocabStatus === "loading"}
          error={vocabError}
        />
      ) : null}

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
