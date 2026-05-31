import { useCallback, useEffect, useState } from "react";

import { postRecapIngest } from "../api/recapIngestApi";
import type { RecapIngestStatus } from "../api/types";

import { inspectHintsForRecapSession, recapSourceSession } from "./corpusIngestDisplay";

export function useCorpusIngestStatus(campaignId: string, liveSession: number) {
  const recapSession = recapSourceSession(liveSession);
  const [result, setResult] = useState<RecapIngestStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const hints = inspectHintsForRecapSession(recapSession);
      const inspected = await postRecapIngest({
        operation: "inspect_status",
        campaign_id: campaignId,
        session: recapSession,
        ...hints,
      });
      setResult(inspected);
      setError(null);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Corpus status check failed");
    } finally {
      setLoading(false);
    }
  }, [campaignId, recapSession]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { result, loading, error, refresh, recapSession, liveSession };
}
