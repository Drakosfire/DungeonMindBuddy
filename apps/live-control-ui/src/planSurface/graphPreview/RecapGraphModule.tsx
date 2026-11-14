import { NativeGraphObjectDetails } from "../../graphLens/NativeGraphObjectDetails";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  LiveApiError,
  getRecapArtifacts,
  getNativeGraphCatalog,
  inspectNativeGraph,
  postWorldGraphRecapProjection,
  readPublishedNativeRecap,
} from "../../api/liveApi";
import type { RecapArtifactRecord, WorldGraphObjectProjectionResult, WorldGraphRecapProjection } from "../../api/types";
import { buildWorldGraphRecapProjectionRequest } from "../../worldGraph/worldGraphSurfaceContext";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import type { PlanContextDescriptor } from "../types";
import {
  defaultRecapSessionIdForCampaign,
  requestedRecapSessionIdFromLocation,
  resolveInitialReviewCampaignId,
  resolveSessionRecapContext,
} from "../../graphLens/sessionCampaignContext";
import {
  filterNumericRecapArtifactRecords,
  sortRecapArtifactRecords,
} from "./recapSessionLabels";
import { WorldGraphRecapProjectionView } from "./WorldGraphRecapProjection";

import { sameInspectionPin, type InspectionPin, type NativeGraphEntity } from "../../api/nativeGraphInspection";
import { loadCompleteWorldObject, completeWorldObjectRequest } from "../../graphReference/fullWorldObjectProjection";
import type { PublishedNativeRecap } from "../../api/nativeSourceInspection";
import { MarkdownDocumentReader } from "../../markdownReader/MarkdownDocumentReader";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";

type LoadStatus = "loading" | "ready" | "error";

interface LoadedRecapState {
  payload: WorldGraphRecapProjection;
  scope: {
    campaignId: string;
    sessionId: string;
  };
  record: RecapArtifactRecord | null;
}

interface RecapGraphModuleProps {
  context: PlanContextDescriptor;
}

const DOGFOOD_SESSION_OPTIONS = ["session-1", "session-21", "session-22", "session-23"];

function requestedSessionFromLocation(): string | null {
  return requestedRecapSessionIdFromLocation();
}

function syncRecapSurfaceUrl(campaignId: string, sessionId?: string) {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("campaign", campaignId);
  params.delete("scopeMode");
  params.delete("run");
  if (sessionId) {
    params.set("session", sessionId);
  }
  const path = window.location.pathname.replace(/\/+$/, "") || "/plan";
  const surfacePath = path === "/ingest" ? "/ingest" : "/plan";
  window.history.replaceState({}, "", `${surfacePath}?${params.toString()}`);
}

function recapUnavailableMessage(error: unknown, sessionId: string, campaignId: string): string {
  if (error instanceof LiveApiError) {
    if (error.status === 404 && error.code === "recap_markdown_unavailable") {
      return `Canonical normalized recap is unavailable for ${sessionId} in ${campaignId}.`;
    }
    if (error.status === 404 || error.status === 400) {
      return `Published World Graph recap is unavailable for ${sessionId} in ${campaignId}.`;
    }
    if (error.status === 422) {
      return error.message || "World Graph recap request was invalid for the selected context.";
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "Failed to load published World Graph recap.";
}

function NativeRecapObjects({ recap }: { recap: PublishedNativeRecap }) {
  const [objects, setObjects] = useState<{ id: string; label: string; ambiguous: boolean }[]>([]);
  const [object, setObject] = useState<WorldGraphObjectProjectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<{ entity: NativeGraphEntity; id: string; label: string } | null>(null);
  const selection = useRef(0);
  const pin = useMemo<InspectionPin>(() => ({
    ...recap.scope, scope_mode: "campaign", campaign_id: recap.campaign_id,
  }), [recap]);

  useEffect(() => {
    const controller = new AbortController();
    void getNativeGraphCatalog(pin, controller.signal).then(packet => {
      if (controller.signal.aborted) return;
      if (!sameInspectionPin(packet.scope, pin)) throw new Error("The recap graph pin changed.");
      const evidence = new Set(recap.evidence_ref_ids);
      const admitted = new Set(packet.catalogue.entities.map(entity => entity.entity_id));
      const labels = new Map<string, Set<string>>();
      for (const assertion of packet.assertions) {
        if (assertion.predicate === "dnd5e:name" && assertion.value.kind === "literal" &&
            typeof assertion.value.value === "string") {
          const names = labels.get(assertion.subject_entity_id) ?? new Set<string>();
          names.add(assertion.value.value);
          labels.set(assertion.subject_entity_id, names);
        }
      }
      const ids = new Set(packet.assertions
        .filter(assertion => admitted.has(assertion.subject_entity_id) &&
          assertion.metadata.evidence_ref_ids.some(id => evidence.has(id)))
        .map(assertion => assertion.subject_entity_id));
      setObjects(Array.from(ids, id => ({ id, label: [...(labels.get(id) ?? [])].sort().join(" / ") || id, ambiguous: (labels.get(id)?.size ?? 0) > 1 })));
      if (packet.catalogue.completeness.status === "partial") {
        setError("Some reviewed recap objects are unavailable.");
      }
    }).catch(reason => {
      if (!controller.signal.aborted) setError(recapUnavailableMessage(reason, recap.session_id, recap.campaign_id));
    });
    return () => { controller.abort(); selection.current += 1; };
  }, [pin, recap]);

  const open = async ({ id, label, ambiguous }: (typeof objects)[number]) => {
    const generation = ++selection.current;
    setObject(null);
    setDetail(null);
    setError(null);
    try {
      if (ambiguous) {
        const entity = await inspectNativeGraph(pin, { kind: "entity", entity_id: id });
        if (generation !== selection.current) return;
        if (entity.schema !== "dmb_native_graph_entity_v1" ||
            !sameInspectionPin(entity.scope, pin) || !entity.entity.found) {
          throw new Error("The reviewed object is unavailable at the recap revision.");
        }
        setDetail({ entity, id, label });
        return;
      }
      const result = await loadCompleteWorldObject(completeWorldObjectRequest({
        worldId: pin.managed_world_id, campaignId: recap.campaign_id,
        scopeMode: "campaign", revisionPin: pin.revision_id, nodeId: id,
        focus: { kind: "session", sessionId: recap.session_id, campaignId: recap.campaign_id },
      }), pin);
      if (generation !== selection.current) return;
      if (!result.found || result.snapshot?.revisionId !== pin.revision_id) {
        throw new Error("The reviewed object is unavailable at the recap revision.");
      }
      setObject(result);
    } catch (reason) {
      if (generation === selection.current) setError(recapUnavailableMessage(reason, recap.session_id, recap.campaign_id));
    }
  };

  return (
    <section aria-label="Reviewed recap objects">
      <h3>Reviewed recap objects</h3>
      {objects.map(row => (
        <button key={row.id} type="button" onClick={() => void open(row)}>{row.label}</button>
      ))}
      {error && <p role="alert">{error}</p>}
      {detail && (
        <section aria-label="Selected reviewed object">
          <NativeGraphObjectDetails detail={detail.entity} entityId={detail.id} label={detail.label} />
        </section>
      )}
      {object && (
        <section aria-label="Selected reviewed object">
          <h4>{objects.find(row => row.id === object.resolvedNodeId)?.label ?? object.resolvedNodeId}</h4>
          {object.sourceBindings?.map(binding => {
            if (typeof binding !== "object" || binding === null ||
                !("evidenceRefId" in binding) || typeof binding.evidenceRefId !== "string" ||
                !("excerpt" in binding) || typeof binding.excerpt !== "string" ||
                !recap.evidence_ref_ids.includes(binding.evidenceRefId)) return null;
            return <blockquote key={binding.evidenceRefId}>{binding.excerpt}</blockquote>;
          })}
        </section>
      )}
    </section>
  );
}

export function RecapGraphModule({ context }: RecapGraphModuleProps) {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const [nativeRecap, setNativeRecap] = useState<PublishedNativeRecap | null>(null);
  const requestedSessionId = requestedSessionFromLocation();
  const fallbackSessionId = `session-${context.ingestSession}`;
  const defaultSessionId = requestedSessionId ?? fallbackSessionId;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [sessionRecords, setSessionRecords] = useState<RecapArtifactRecord[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState(defaultSessionId);
  const [selectedCampaignId, setSelectedCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [draftSessionId, setDraftSessionId] = useState(defaultSessionId);
  const [draftCampaignId, setDraftCampaignId] = useState(() =>
    resolveInitialReviewCampaignId(context.campaignId),
  );
  const [readyRecapContext, setReadyRecapContext] = useState<{
    campaignId: string;
    sessionId: string;
  } | null>(null);
  const honorExplicitUrlSessionRef = useRef(requestedSessionId != null);
  const draftSessionIdRef = useRef(draftSessionId);
  draftSessionIdRef.current = draftSessionId;
  const initialLoadStartedRef = useRef(false);
  const loadGenerationRef = useRef(0);
  // Keep the payload and its server-owned source record together. The catalog
  // is a draft-selection aid and may change when the operator edits Campaign;
  // it must not invalidate the source authority for the recap currently on
  // screen before a replacement Load succeeds.
  const [loadedRecap, setLoadedRecap] = useState<LoadedRecapState | null>(null);

  const campaignSessionRecords = useMemo(
    () => sessionRecords.filter((record) => record.campaign_id === draftCampaignId),
    [draftCampaignId, sessionRecords],
  );

  const sessionOptions = useMemo(() => {
    const options = new Set(campaignSessionRecords.length > 0 ? [] : DOGFOOD_SESSION_OPTIONS);
    options.add(`session-${context.ingestSession}`);
    options.add(draftSessionId);
    if (honorExplicitUrlSessionRef.current && requestedSessionId) {
      options.add(requestedSessionId);
    }
    campaignSessionRecords.forEach((record) => options.add(record.session_id));
    return [...options].sort((left, right) => {
      const leftNum = Number.parseInt(left.replace("session-", ""), 10);
      const rightNum = Number.parseInt(right.replace("session-", ""), 10);
      return leftNum - rightNum;
    });
  }, [campaignSessionRecords, context.ingestSession, draftSessionId, requestedSessionId]);

  const loadRecapProjection = useCallback(async (
    campaignId: string,
    sessionId: string,
  ) => {
    const generation = ++loadGenerationRef.current;
    setStatus("loading");
    setError(null);
    const { campaignId: resolvedCampaignId } = resolveSessionRecapContext(
      sessionId,
      campaignId,
      sessionRecords,
    );
    if (managedWorldId) {
      try {
        const recap = await readPublishedNativeRecap(managedWorldId, resolvedCampaignId, sessionId);
        if (generation !== loadGenerationRef.current) return;
        setNativeRecap(recap);
        setStatus("ready");
      } catch (loadError) {
        if (generation !== loadGenerationRef.current) return;
        setError(recapUnavailableMessage(loadError, sessionId, resolvedCampaignId));
        setStatus("error");
      }
      return;
    }
    if (selectedWorld.kind !== "legacy") {
      setStatus("error");
      setError("The selected World is unavailable.");
      return;
    }
    const request = buildWorldGraphRecapProjectionRequest({
      campaignId: resolvedCampaignId,
      sessionId,
    });
    if (!request) {
      if (generation !== loadGenerationRef.current) {
        return;
      }
      setError(`World Graph mapping is unavailable for campaign ${resolvedCampaignId}.`);
      setStatus("error");
      return;
    }

    try {
      const projection = await postWorldGraphRecapProjection(request);
      if (generation !== loadGenerationRef.current) {
        return;
      }
      setLoadedRecap({
        payload: projection,
        scope: { campaignId: resolvedCampaignId, sessionId },
        record: sessionRecords.find(
          (record) =>
            record.campaign_id === resolvedCampaignId
            && record.session_id === sessionId,
        ) ?? null,
      });
      setStatus("ready");
    } catch (loadError) {
      if (generation !== loadGenerationRef.current) {
        return;
      }
      setError(recapUnavailableMessage(loadError, sessionId, resolvedCampaignId));
      setStatus("error");
    }
  }, [managedWorldId, selectedWorld.kind, sessionRecords]);

  useEffect(() => {
    let cancelled = false;
    setCatalogLoading(true);

    void getRecapArtifacts(draftCampaignId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setCatalogLoading(false);
        const records = sortRecapArtifactRecords(
          filterNumericRecapArtifactRecords(response.records),
        );
        setSessionRecords(records);
        const campaignRecords = records.filter((record) => record.campaign_id === draftCampaignId);
        const honorExplicitUrl = honorExplicitUrlSessionRef.current;
        const explicitSessionId = honorExplicitUrl ? requestedRecapSessionIdFromLocation() : null;
        const currentSessionId = draftSessionIdRef.current;
        const stillValid = campaignRecords.some((record) => record.session_id === currentSessionId);
        // Explicit hard-load ?session= reaches the recap endpoint unchanged, even when
        // the artifact listing is stale. Interactive campaign switch must not carry a
        // previous campaign's session into a campaign that does not offer it.
        const nextSessionId = honorExplicitUrl
          ? (explicitSessionId ?? defaultRecapSessionIdForCampaign(campaignRecords, fallbackSessionId))
          : (stillValid
            ? currentSessionId
            : defaultRecapSessionIdForCampaign(campaignRecords, fallbackSessionId));
        draftSessionIdRef.current = nextSessionId;
        setDraftSessionId(nextSessionId);
        if (!initialLoadStartedRef.current) {
          initialLoadStartedRef.current = true;
          setSelectedCampaignId(draftCampaignId);
          setSelectedSessionId(nextSessionId);
          syncRecapSurfaceUrl(draftCampaignId, nextSessionId);
          setReadyRecapContext({ campaignId: draftCampaignId, sessionId: nextSessionId });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCatalogLoading(false);
          setSessionRecords([]);
          const honorExplicitUrl = honorExplicitUrlSessionRef.current;
          const nextSessionId = honorExplicitUrl
            ? (requestedRecapSessionIdFromLocation() ?? fallbackSessionId)
            : fallbackSessionId;
          draftSessionIdRef.current = nextSessionId;
          setDraftSessionId(nextSessionId);
          if (!initialLoadStartedRef.current) {
            initialLoadStartedRef.current = true;
            setSelectedCampaignId(draftCampaignId);
            setSelectedSessionId(nextSessionId);
            syncRecapSurfaceUrl(draftCampaignId, nextSessionId);
            setReadyRecapContext({ campaignId: draftCampaignId, sessionId: nextSessionId });
          }
        }
      });

    return () => {
      cancelled = true;
    };
  }, [draftCampaignId, fallbackSessionId]);

  useEffect(() => {
    if (!readyRecapContext) {
      return;
    }
    if (readyRecapContext.campaignId !== selectedCampaignId) {
      return;
    }
    void loadRecapProjection(readyRecapContext.campaignId, readyRecapContext.sessionId);
  }, [loadRecapProjection, readyRecapContext, selectedCampaignId]);

  const handleCampaignSelect = (campaignId: string) => {
    honorExplicitUrlSessionRef.current = false;
    setDraftCampaignId(campaignId);
  };

  const handleSessionSelect = (sessionId: string) => {
    draftSessionIdRef.current = sessionId;
    setDraftSessionId(sessionId);
  };

  const handleLoad = () => {
    if (catalogLoading || !draftCampaignId || !draftSessionId) return;
    setSelectedCampaignId(draftCampaignId);
    setSelectedSessionId(draftSessionId);
    setReadyRecapContext({ campaignId: draftCampaignId, sessionId: draftSessionId });
    syncRecapSurfaceUrl(draftCampaignId, draftSessionId);
  };

  const authorableRecap =
    status === "ready" &&
    loadedRecap
      ? loadedRecap.payload
      : null;

  const reviewToolbar = (
    <div className="recap-reader-toolbar">
      <ReviewCampaignPicker selectedCampaignId={draftCampaignId} onSelect={handleCampaignSelect} />
      <label className="graph-preview-run-picker">
        <span>Focus session</span>
        <select value={draftSessionId} onChange={(event) => handleSessionSelect(event.target.value)}>
          {sessionOptions.map((sessionId) => (
            <option key={sessionId} value={sessionId}>
              {sessionId.replace("session-", "Session ")}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="primary recap-reader-load-button"
        onClick={handleLoad}
        disabled={catalogLoading || !draftCampaignId || !draftSessionId || status === "loading"}
      >
        {status === "loading" ? "Loading…" : "Load"}
      </button>
    </div>
  );

  if (status === "loading") {
    return (
      <div className="recap-reader-root">
        {reviewToolbar}
        <p className="plan-projection-empty">Loading published World Graph recap…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="recap-reader-root">
        {reviewToolbar}
        <p className="graph-preview-error" role="alert">
          {error ?? `Published World Graph recap is unavailable for ${selectedSessionId}.`}
        </p>
        <button type="button" onClick={handleLoad}>
          Load
        </button>
      </div>
    );
  }

  if (managedWorldId && nativeRecap?.scope.managed_world_id === managedWorldId &&
      nativeRecap.campaign_id === selectedCampaignId && nativeRecap.session_id === selectedSessionId) {
    return (
      <div className="recap-reader-root">
        {reviewToolbar}
        <MarkdownDocumentReader markdown={nativeRecap.source.body_text} />
        <NativeRecapObjects key={JSON.stringify([nativeRecap.scope, nativeRecap.campaign_id, nativeRecap.session_id])} recap={nativeRecap} />
      </div>
    );
  }

  if (selectedWorld.kind === "legacy" && authorableRecap) {
    return (
      <WorldGraphRecapProjectionView
        payload={authorableRecap}
        selectedSessionId={selectedSessionId}
        onSelectSession={handleSessionSelect}
        sessionOptions={sessionOptions}
        selectedCampaignId={selectedCampaignId}
        onSelectCampaign={handleCampaignSelect}
        draftCampaignId={draftCampaignId}
        draftSessionId={draftSessionId}
        onLoad={handleLoad}
        canLoad={!catalogLoading}
        recapRecord={loadedRecap?.record ?? null}
        onRefreshProjection={() => loadRecapProjection(selectedCampaignId, selectedSessionId)}
      />
    );
  }

  return (
    <div className="recap-reader-root">
      {reviewToolbar}
      <p className="plan-projection-empty">No published World Graph recap loaded.</p>
    </div>
  );
}
