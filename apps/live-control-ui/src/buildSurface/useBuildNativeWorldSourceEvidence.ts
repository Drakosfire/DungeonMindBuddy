import { useCallback, useEffect, useRef, useState } from "react";

import {
  admitNativeWorldSource,
  getNativeWorldSourceAdmissionStatus,
} from "../api/liveApi";
import type { NativeWorldSourceAdmissionStatus } from "../api/types";

export interface BuildNativeWorldSourceEvidenceState {
  status: NativeWorldSourceAdmissionStatus | null;
  loading: boolean;
  retrying: boolean;
  error: string | null;
  reload: () => Promise<void>;
  retry: () => Promise<void>;
}

export function useBuildNativeWorldSourceEvidence(
  documentId: string,
): BuildNativeWorldSourceEvidenceState {
  const [status, setStatus] = useState<NativeWorldSourceAdmissionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);

  const reload = useCallback(async () => {
    const current = ++generation.current;
    setLoading(true);
    setRetrying(false);
    setError(null);
    try {
      const result = await getNativeWorldSourceAdmissionStatus(documentId);
      if (generation.current === current) setStatus(result);
    } catch (caught) {
      if (generation.current === current) {
        setStatus(null);
        setError(caught instanceof Error ? caught.message : "Native source status is unavailable");
      }
    } finally {
      if (generation.current === current) setLoading(false);
    }
  }, [documentId]);

  const retry = useCallback(async () => {
    if (!status) {
      await reload();
      return;
    }
    const current = ++generation.current;
    const isCurrent = () => generation.current === current;
    setRetrying(true);
    setError(null);
    try {
      const result = await admitNativeWorldSource(
        documentId,
        status.loaded_revision,
        status.body_sha256,
      );
      if (isCurrent()) setStatus(result);
    } catch (caught) {
      if (isCurrent()) {
        setError(caught instanceof Error ? caught.message : "Native source admission is still pending");
        await reload();
      }
    } finally {
      if (isCurrent()) setRetrying(false);
    }
  }, [documentId, reload, status]);

  useEffect(() => {
    void reload();
    return () => {
      generation.current += 1;
    };
  }, [reload]);

  return {
    status: status?.document_id === documentId ? status : null,
    loading,
    retrying,
    error,
    reload,
    retry,
  };
}
