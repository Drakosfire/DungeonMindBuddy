import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { prepareWorldbuildingWritePlan } from "../../api/extractPromoteApi";
import { postManagedWorldGraphProjection } from "../../api/liveApi";
import type {
  ExactRunReviewAssertion,
  ExactRunReviewPackage,
  ManagedWorldGraphProjectionResponse,
  WorldbuildingDisposition,
  WorldbuildingDispositionDecision,
  WorldbuildingWritePlanResponse,
} from "../../api/types";
import "./GraphReviewWorldbuildingObservationReview.css";

type LocalDecision = WorldbuildingDispositionDecision | "undecided";
type CandidateDecisions = Record<string, {
  decision: LocalDecision;
  targetNodeId?: string;
}>;

interface GraphReviewWorldbuildingObservationReviewProps {
  review: ExactRunReviewPackage;
  managedWorldId: string | null;
}

const GRAPH_PROJECTION_SCHEMA = "dmb_managed_world_graph_projection_request_v1" as const;

interface WorldGraphPin {
  nativeWorldId: string;
  bindingVersion: number;
  revisionId: string;
}

function projectionError(
  response: ManagedWorldGraphProjectionResponse,
  expectedWorldId: string,
  pin?: WorldGraphPin,
): string | null {
  if (response.managedWorldId !== expectedWorldId) {
    return "The graph response belongs to a different selected World.";
  }
  if (pin && (response.nativeWorldId !== pin.nativeWorldId || response.bindingVersion !== pin.bindingVersion)) {
    return "The selected World binding changed during review. Refresh the snapshot before preparing.";
  }
  if (response.projection.snapshot.worldId !== response.nativeWorldId) {
    return "The graph response does not match its verified World binding.";
  }
  if (pin && response.projection.snapshot.revisionId !== pin.revisionId) {
    return "The graph search returned a different revision than the reviewed snapshot.";
  }
  if (!response.projection.snapshot.isHead) {
    return "The World Graph changed while this review was open. Refresh the snapshot before preparing.";
  }
  if (response.projection.snapshot.headRevisionId !== response.projection.snapshot.revisionId) {
    return "The World Graph changed while this review was open. Refresh the snapshot before preparing.";
  }
  return null;
}

function relationshipEndpoints(assertion: ExactRunReviewAssertion): [string, string] | null {
  if (assertion.kind !== "relationship") return null;
  const parts = assertion.summary.split("→").map((part) => part.trim());
  return parts.length === 2 && parts[0] && parts[1] ? [parts[0], parts[1]] : null;
}

function hasValidEvidence(assertion: ExactRunReviewAssertion, sourceArtifactId: string): boolean {
  return assertion.evidence.length > 0 && assertion.evidence.every((evidence) =>
    evidence.sourceArtifactId === sourceArtifactId
    && Boolean(evidence.sourceSpanRefId.trim())
    && (evidence.invalidAnchorQuotes?.length ?? 0) === 0,
  );
}

function isAcceptedNodeIdentity(decision: CandidateDecisions[string] | undefined): boolean {
  return decision?.decision === "create_new"
    || (decision?.decision === "bind_existing" && Boolean(decision.targetNodeId));
}

function decisionLabel(decision: LocalDecision): string {
  switch (decision) {
    case "create_new": return "Create new";
    case "bind_existing": return "Use existing";
    case "accept": return "Accept";
    case "reject": return "Reject";
    case "defer": return "Defer";
    default: return "Choose a decision";
  }
}

function plannedAssertionLabel(assertion: WorldbuildingWritePlanResponse["effect"]["acceptedProposals"][number]): string {
  return assertion.label?.trim() || assertion.predicate?.trim() || assertion.assertionKind;
}

function plannedAssertionDescription(assertion: WorldbuildingWritePlanResponse["effect"]["acceptedProposals"][number]): string | null {
  const value = assertion.value ?? {};
  const description = [value.summary, value.description, value.text]
    .find((item): item is string => typeof item === "string" && item.trim().length > 0);
  const endpoints = [assertion.subjectNodeId, assertion.targetNodeId]
    .filter((item): item is string => Boolean(item?.trim()));
  const route = endpoints.join(" → ");
  if (route && description) return `${route} · ${description}`;
  if (route) return route;
  return description ?? null;
}

export function GraphReviewWorldbuildingObservationReview({
  review,
  managedWorldId,
}: GraphReviewWorldbuildingObservationReviewProps) {
  const [decisions, setDecisions] = useState<CandidateDecisions>({});
  const [searchTerms, setSearchTerms] = useState<Record<string, string>>({});
  const [searchResults, setSearchResults] = useState<Record<string, ManagedWorldGraphProjectionResponse["projection"]["nodes"]>>({});
  const [searching, setSearching] = useState<Record<string, boolean>>({});
  const [graphStatus, setGraphStatus] = useState<"loading" | "ready" | "stale" | "error">("loading");
  const [graphError, setGraphError] = useState<string | null>(null);
  const [graphPin, setGraphPin] = useState<WorldGraphPin | null>(null);
  const [snapshotRefreshCount, setSnapshotRefreshCount] = useState(0);
  const [preparedPlan, setPreparedPlan] = useState<WorldbuildingWritePlanResponse | null>(null);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [preparing, setPreparing] = useState(false);
  const prepareGenerationRef = useRef(0);

  const objectAssertions = useMemo(
    () => review.assertions.filter((assertion) => assertion.kind === "object"),
    [review.assertions],
  );
  const assertionsById = useMemo(
    () => new Map(review.assertions.map((assertion) => [assertion.assertionId, assertion])),
    [review.assertions],
  );

  const prepareContextKey = JSON.stringify([
    review.runId,
    review.sourceArtifactId,
    review.sourceRevisionId,
    review.worldId,
    review.assertions.map((assertion) => assertion.assertionId),
    managedWorldId,
    graphPin?.nativeWorldId,
    graphPin?.bindingVersion,
    graphPin?.revisionId,
  ]);
  const prepareContextKeyRef = useRef(prepareContextKey);
  useLayoutEffect(() => {
    if (prepareContextKeyRef.current === prepareContextKey) return;
    prepareContextKeyRef.current = prepareContextKey;
    prepareGenerationRef.current += 1;
    setPreparedPlan(null);
    setPrepareError(null);
    setPreparing(false);
  }, [prepareContextKey]);

  useEffect(() => {
    setDecisions({});
    setSearchTerms({});
    setSearchResults({});
    setPreparedPlan(null);
    setPrepareError(null);
    setPreparing(false);
    setGraphPin(null);
    setGraphError(null);

    if (!managedWorldId) {
      setGraphStatus("error");
      setGraphError("Select a verified managed World before reviewing graph identities.");
      return;
    }
    let cancelled = false;
    setGraphStatus("loading");
    const queryText = objectAssertions[0]?.label ?? "source observation";
    void postManagedWorldGraphProjection({
      schema: GRAPH_PROJECTION_SCHEMA,
      managedWorldId,
      queryText,
    }).then((response) => {
      if (cancelled) return;
      const error = projectionError(response, managedWorldId);
      const candidateWorldError = review.worldId !== response.nativeWorldId
        ? (review.worldId
          ? "This exact candidate belongs to a different World. Select its source World to continue."
          : "This exact candidate has no verified World binding. Select its source World to continue.")
        : null;
      if (error || candidateWorldError) {
        const reason = error ?? candidateWorldError;
        setGraphStatus(reason?.includes("changed") || reason?.includes("binding") ? "stale" : "error");
        setGraphError(reason ?? "Could not verify the selected World Graph.");
        return;
      }
      setGraphPin({
        nativeWorldId: response.nativeWorldId,
        bindingVersion: response.bindingVersion,
        revisionId: response.projection.snapshot.revisionId,
      });
      setGraphStatus("ready");
      setGraphError(null);
    }).catch((error: unknown) => {
      if (cancelled) return;
      setGraphStatus("error");
      setGraphError(error instanceof Error ? error.message : "Could not load the selected World Graph revision.");
    });
    return () => { cancelled = true; };
  }, [managedWorldId, objectAssertions, review.runId, review.sourceArtifactId, review.sourceRevisionId, review.worldId, snapshotRefreshCount]);

  useEffect(() => {
    if (!managedWorldId || !graphPin || graphStatus !== "ready") return;
    const pending = objectAssertions.flatMap((assertion) => {
      const query = (searchTerms[assertion.assertionId] ?? "").trim();
      return decisions[assertion.assertionId]?.decision === "bind_existing" && query.length >= 2
        ? [{ assertionId: assertion.assertionId, query }]
        : [];
    });
    if (pending.length === 0) {
      setSearchResults({});
      setSearching({});
      return;
    }

    let cancelled = false;
    setSearching(Object.fromEntries(pending.map(({ assertionId }) => [assertionId, true])));
    const timer = window.setTimeout(() => {
      void Promise.all(pending.map(async ({ assertionId, query }) => {
        const response = await postManagedWorldGraphProjection({
          schema: GRAPH_PROJECTION_SCHEMA,
          managedWorldId,
          revisionPin: graphPin.revisionId,
          queryText: query,
        });
        return { assertionId, response };
      })).then((results) => {
        if (cancelled) return;
        const next: typeof searchResults = {};
        for (const { assertionId, response } of results) {
          const error = projectionError(response, managedWorldId, graphPin);
          if (error) {
            setGraphStatus(error.includes("changed") || error.includes("binding") ? "stale" : "error");
            setGraphError(error);
            setSearchResults({});
            setSearching({});
            return;
          }
          next[assertionId] = response.projection.nodes;
        }
        setSearchResults(next);
        setSearching({});
      }).catch((error: unknown) => {
        if (cancelled) return;
        setGraphError(error instanceof Error ? error.message : "Graph identity search failed.");
        setSearching({});
      });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [decisions, graphPin, graphStatus, managedWorldId, objectAssertions, searchTerms]);

  const missingDecisions = review.assertions.filter(
    (assertion) => !decisions[assertion.assertionId] || decisions[assertion.assertionId].decision === "undecided",
  );
  const invalidAcceptedEvidence = review.assertions.filter((assertion) => {
    const decision = decisions[assertion.assertionId]?.decision;
    return (decision === "accept" || decision === "create_new" || decision === "bind_existing")
      && !hasValidEvidence(assertion, review.sourceArtifactId);
  });
  const blockedObservations = review.assertions.filter((assertion) =>
    assertion.kind === "source_observation"
    && decisions[assertion.assertionId]?.decision === "accept"
    && !isAcceptedNodeIdentity(decisions[assertion.subjectCandidateNodeId ?? ""]),
  );
  const blockedRelationships = review.assertions.filter((assertion) => {
    const endpoints = relationshipEndpoints(assertion);
    return assertion.kind === "relationship"
      && decisions[assertion.assertionId]?.decision === "accept"
      && (!endpoints
        || endpoints.some((endpoint) => !isAcceptedNodeIdentity(decisions[endpoint])));
  });
  const invalidExistingTargets = objectAssertions.filter((assertion) => {
    const decision = decisions[assertion.assertionId];
    return decision?.decision === "bind_existing"
      && (!decision.targetNodeId
        || !(searchResults[assertion.assertionId] ?? []).some((node) => node.nodeId === decision.targetNodeId));
  });
  const hasAcceptedDecision = review.assertions.some((assertion) => {
    const decision = decisions[assertion.assertionId]?.decision;
    return decision === "create_new" || decision === "bind_existing" || decision === "accept";
  });
  const canPrepare = review.assertions.length > 0
    && missingDecisions.length === 0
    && invalidAcceptedEvidence.length === 0
    && blockedObservations.length === 0
    && blockedRelationships.length === 0
    && invalidExistingTargets.length === 0
    && hasAcceptedDecision
    && review.inspectionStatus === "ready"
    && graphStatus === "ready"
    && Boolean(graphPin)
    && !preparing;

  const updateDecision = (assertionId: string, decision: LocalDecision) => {
    prepareGenerationRef.current += 1;
    setPreparedPlan(null);
    setPrepareError(null);
    setDecisions((current) => ({
      ...current,
      [assertionId]: {
        decision,
        ...(decision === "bind_existing" ? { targetNodeId: current[assertionId]?.targetNodeId } : {}),
      },
    }));
  };

  const deferUndecided = () => {
    prepareGenerationRef.current += 1;
    setPreparedPlan(null);
    setPrepareError(null);
    setDecisions((current) => Object.fromEntries(review.assertions.map((assertion) => [
      assertion.assertionId,
      current[assertion.assertionId]?.decision && current[assertion.assertionId].decision !== "undecided"
        ? current[assertion.assertionId]
        : { decision: "defer" },
    ])));
  };

  const refreshSnapshot = () => {
    prepareGenerationRef.current += 1;
    setPreparing(false);
    setGraphStatus("loading");
    setGraphError(null);
    setGraphPin(null);
    setPreparedPlan(null);
    setPrepareError(null);
    setDecisions({});
    setSearchTerms({});
    setSearchResults({});
    setSnapshotRefreshCount((count) => count + 1);
  };

  const prepare = async () => {
    if (!canPrepare || !managedWorldId || !graphPin) return;
    if (review.assertions.some((assertion) => {
      const choice = decisions[assertion.assertionId];
      return !choice || choice.decision === "undecided";
    })) {
      setPrepareError("Every extracted assertion needs an explicit review decision.");
      return;
    }
    const dispositions: WorldbuildingDisposition[] = review.assertions.map((assertion) => {
      const choice = decisions[assertion.assertionId];
      if (!choice || choice.decision === "undecided") return { assertionId: assertion.assertionId, decision: "defer" };
      return {
        assertionId: assertion.assertionId,
        decision: choice.decision,
        ...(choice.decision === "bind_existing" ? { targetNodeId: choice.targetNodeId } : {}),
      };
    });
    const requestGeneration = ++prepareGenerationRef.current;
    const requestContextKey = prepareContextKey;
    const requestIsCurrent = () => requestGeneration === prepareGenerationRef.current
      && requestContextKey === prepareContextKeyRef.current;
    setPreparing(true);
    setPrepareError(null);
    setPreparedPlan(null);
    try {
      const plan = await prepareWorldbuildingWritePlan({
        runId: review.runId,
        expectedParentRevisionId: graphPin.revisionId,
        dispositions,
      });
      if (!requestIsCurrent()) return;
      if (plan.runId !== review.runId
        || plan.sourceArtifactId !== review.sourceArtifactId
        || plan.sourceRevisionId !== review.sourceRevisionId
        || plan.worldId !== graphPin.nativeWorldId
        || plan.sourceDomain !== "worldbuilding") {
        throw new Error("Prepared plan identity does not match the reviewed run and source.");
      }
      if (plan.confirmable !== false) {
        throw new Error("The server returned a confirmable plan. This review surface cannot publish it.");
      }
      if (plan.parentRevisionId !== graphPin.revisionId) {
        setGraphStatus("stale");
        throw new Error("The World Graph head changed. Refresh the snapshot and review decisions again.");
      }
      setPreparedPlan(plan);
    } catch (error) {
      if (requestIsCurrent()) {
        setPrepareError(error instanceof Error ? error.message : "Could not prepare the source review.");
      }
    } finally {
      if (requestIsCurrent()) setPreparing(false);
    }
  };

  const optionSets: Record<ExactRunReviewAssertion["kind"], Array<Exclude<LocalDecision, "undecided">>> = {
    object: ["create_new", "bind_existing", "reject", "defer"],
    relationship: ["accept", "reject", "defer"],
    source_observation: ["accept", "reject", "defer"],
  };

  return (
    <section className="graph-review-worldbuilding-observation-review" aria-label="Review extracted Worldbuilding facts">
      <header className="graph-review-worldbuilding-observation-review__header">
        <div>
          <p className="graph-review-worldbuilding-observation-review__eyebrow">Ingest review</p>
          <h3>Review extracted facts</h3>
          <p>Choose what belongs in the World Graph. Every observation stays tied to its exact source passage.</p>
        </div>
        <button type="button" onClick={deferUndecided} disabled={missingDecisions.length === 0 || preparing}>
          Defer undecided
        </button>
      </header>

      {review.inspectionStatus !== "ready" ? (
        <p className="graph-review-worldbuilding-observation-review__alert" role="alert">
          This exact candidate is {review.inspectionStatus?.replaceAll("_", " ") ?? "missing an inspection status"}. Inspect the evidence above; preparing is blocked.
        </p>
      ) : null}
      {graphStatus === "loading" ? <p role="status">Checking the selected World Graph revision…</p> : null}
      {graphError ? (
        <div className="graph-review-worldbuilding-observation-review__alert" role="alert">
          <p>{graphError}</p>
          {(graphStatus === "stale" || graphStatus === "error") && managedWorldId ? (
            <button type="button" onClick={refreshSnapshot}>Refresh graph snapshot and restart review</button>
          ) : null}
        </div>
      ) : null}

      {review.assertions.length === 0 ? <p>No extracted assertions are available to review.</p> : null}
      <ol className="graph-review-worldbuilding-observation-review__candidates">
        {review.assertions.map((assertion) => {
          const choice = decisions[assertion.assertionId]?.decision ?? "undecided";
          const subject = assertion.subjectCandidateNodeId
            ? assertionsById.get(assertion.subjectCandidateNodeId)
            : null;
          const endpoints = relationshipEndpoints(assertion);
          const acceptedSubject = Boolean(assertion.subjectCandidateNodeId
            && isAcceptedNodeIdentity(decisions[assertion.subjectCandidateNodeId]));
          const acceptedEndpoints = endpoints?.every((endpoint) => isAcceptedNodeIdentity(decisions[endpoint])) ?? false;
          return (
            <li key={assertion.assertionId} className="graph-review-worldbuilding-observation-review__candidate">
              <div className="graph-review-worldbuilding-observation-review__candidate-title">
                <div>
                  <span className="graph-review-worldbuilding-observation-review__kind">
                    {assertion.kind === "source_observation" ? "Source observation" : assertion.kind === "relationship" ? "Relationship" : "Object"}
                  </span>
                  <h4>{assertion.label}</h4>
                  {assertion.summary ? <p>{assertion.summary}</p> : null}
                </div>
                <span className={`graph-review-worldbuilding-observation-review__status is-${choice}`}>
                  {decisionLabel(choice)}
                </span>
              </div>

              {assertion.kind === "source_observation" ? (
                <p className="graph-review-worldbuilding-observation-review__dependency">
                  Subject: {subject?.label ?? assertion.subjectCandidateNodeId ?? "missing candidate subject"}
                  {acceptedSubject ? " · identity accepted" : " · choose create-new or existing identity above"}
                </p>
              ) : null}
              {assertion.kind === "relationship" ? (
                <p className="graph-review-worldbuilding-observation-review__dependency">
                  {endpoints ? `${assertionsById.get(endpoints[0])?.label ?? endpoints[0]} → ${assertionsById.get(endpoints[1])?.label ?? endpoints[1]}` : "Relationship endpoints could not be read"}
                  {acceptedEndpoints ? " · endpoints accepted" : " · accept only after both endpoint identities are chosen"}
                </p>
              ) : null}
              {!hasValidEvidence(assertion, review.sourceArtifactId) ? (
                <p className="graph-review-worldbuilding-observation-review__alert">
                  Acceptance is disabled because this candidate has no valid evidence bound to the exact source artifact and literal passage anchors.
                </p>
              ) : null}

              <details className="graph-review-worldbuilding-observation-review__evidence">
                <summary>Source evidence ({assertion.evidence.length})</summary>
                {assertion.evidence.length === 0 ? <p>No source evidence is attached. Acceptance is blocked.</p> : null}
                {assertion.evidence.map((evidence) => (
                  <article key={`${assertion.assertionId}:${evidence.sourceSpanRefId}`}>
                    <p><code>{evidence.sourceSpanRefId}</code>
                      {evidence.startLine != null ? ` · lines ${evidence.startLine}${evidence.endLine != null && evidence.endLine !== evidence.startLine ? `–${evidence.endLine}` : ""}` : ""}
                    </p>
                    {evidence.anchorQuotes.length ? <p>Quote: “{evidence.anchorQuotes.join(" · ")}”</p> : null}
                    {(evidence.invalidAnchorQuotes?.length ?? 0) > 0 ? (
                      <p className="graph-review-worldbuilding-observation-review__alert">
                        Nonliteral quote: {evidence.invalidAnchorQuotes?.join(" · ")}
                      </p>
                    ) : null}
                    <blockquote>{evidence.paragraphText || "Source paragraph unavailable"}</blockquote>
                  </article>
                ))}
              </details>

              <fieldset disabled={preparing || Boolean(preparedPlan)}>
                <legend>Decision</legend>
                <div className="graph-review-worldbuilding-observation-review__choices">
                  {optionSets[assertion.kind].map((decision) => {
                    const identityOrAcceptDecision = decision === "create_new"
                      || decision === "bind_existing"
                      || decision === "accept";
                    const blocked = (identityOrAcceptDecision && graphStatus !== "ready")
                      || (decision === "accept" && assertion.kind === "source_observation" && !acceptedSubject)
                      || (decision === "accept" && assertion.kind === "relationship" && !acceptedEndpoints)
                      || ((decision === "accept" || decision === "create_new" || decision === "bind_existing")
                        && !hasValidEvidence(assertion, review.sourceArtifactId));
                    return (
                      <label key={decision}>
                        <input
                          type="radio"
                          name={`decision-${assertion.assertionId}`}
                          value={decision}
                          checked={choice === decision}
                          disabled={blocked}
                          onChange={() => updateDecision(assertion.assertionId, decision)}
                        />
                        {decisionLabel(decision)}
                      </label>
                    );
                  })}
                </div>
                {choice === "bind_existing" && assertion.kind === "object" ? (
                  <div className="graph-review-worldbuilding-observation-review__identity-search">
                    <label>
                      Search existing {assertion.label}
                      <input
                        value={searchTerms[assertion.assertionId] ?? ""}
                        onChange={(event) => {
                          setPreparedPlan(null);
                          setPrepareError(null);
                          setSearchTerms((current) => ({ ...current, [assertion.assertionId]: event.target.value }));
                          setSearchResults((current) => {
                            const next = { ...current };
                            delete next[assertion.assertionId];
                            return next;
                          });
                          setDecisions((current) => ({ ...current, [assertion.assertionId]: { decision: "bind_existing" } }));
                        }}
                        placeholder="Type a name or alias"
                      />
                    </label>
                    {searching[assertion.assertionId] ? <p role="status">Searching this World…</p> : null}
                    {(searchResults[assertion.assertionId] ?? []).length ? (
                      <label>
                        Bind to
                        <select
                          value={decisions[assertion.assertionId]?.targetNodeId ?? ""}
                          onChange={(event) => setDecisions((current) => ({
                            ...current,
                            [assertion.assertionId]: { decision: "bind_existing", targetNodeId: event.target.value },
                          }))}
                        >
                          <option value="">Select the exact existing object</option>
                          {(searchResults[assertion.assertionId] ?? []).map((node) => (
                            <option key={node.nodeId} value={node.nodeId}>{node.label} · {node.kind}</option>
                          ))}
                        </select>
                      </label>
                    ) : (searchTerms[assertion.assertionId] ?? "").trim().length >= 2 && !searching[assertion.assertionId] ? (
                      <p>No matching objects in this World at the reviewed revision.</p>
                    ) : null}
                  </div>
                ) : null}
                {choice === "bind_existing" && assertion.kind === "object" && !decisions[assertion.assertionId]?.targetNodeId ? (
                  <p className="graph-review-worldbuilding-observation-review__alert">Select an exact graph object before preparing.</p>
                ) : null}
              </fieldset>
            </li>
          );
        })}
      </ol>

      {missingDecisions.length > 0 ? (
        <p className="graph-review-worldbuilding-observation-review__hint">
          {missingDecisions.length} candidate{missingDecisions.length === 1 ? "" : "s"} still need an explicit decision.
        </p>
      ) : null}
      {blockedObservations.length > 0 ? <p className="graph-review-worldbuilding-observation-review__alert">Accept each source observation only after its subject has a create-new or bind-existing identity decision.</p> : null}
      {blockedRelationships.length > 0 ? <p className="graph-review-worldbuilding-observation-review__alert">Accept each relationship only after both endpoint identities are accepted.</p> : null}
      {invalidAcceptedEvidence.length > 0 ? <p className="graph-review-worldbuilding-observation-review__alert">Accepted candidates need valid, source-matched evidence. Correct or defer the affected candidate.</p> : null}
      {invalidExistingTargets.length > 0 ? <p className="graph-review-worldbuilding-observation-review__alert">Choose an existing object from the verified World search results.</p> : null}

      <div className="graph-review-worldbuilding-observation-review__actions">
        <button type="button" onClick={() => void prepare()} disabled={!canPrepare}>
          {preparing ? "Preparing review…" : "Prepare review plan"}
        </button>
        <span>{graphPin ? `World ${graphPin.nativeWorldId} · graph revision ${graphPin.revisionId}` : "World Graph revision not verified"}</span>
      </div>
      {prepareError ? <p className="graph-review-worldbuilding-observation-review__alert" role="alert">{prepareError}</p> : null}
      {preparedPlan ? (
        <section className="graph-review-worldbuilding-observation-review__prepared" aria-label="Prepared review plan">
          <p className="graph-review-worldbuilding-observation-review__eyebrow">Prepared · graph unchanged</p>
          <h4>Review plan is ready</h4>
          <p>{preparedPlan.summary.createNewNodeCount} new objects · {preparedPlan.summary.bindExistingNodeCount} linked objects · {preparedPlan.summary.acceptedEdgeCount} relationships · {preparedPlan.summary.acceptedAssertionCount} accepted assertions</p>
          <p>
            World <code>{preparedPlan.worldId}</code> · parent revision <code>{preparedPlan.parentRevisionId}</code><br />
            Source <code>{preparedPlan.sourceArtifactId}</code> · revision <code>{preparedPlan.sourceRevisionId}</code>
          </p>
          <details>
            <summary>Prepared graph effects ({preparedPlan.effect.acceptedProposals.length} accepted · {preparedPlan.effect.rejectedAssertions.length} rejected · {preparedPlan.effect.deferredCandidateIds.length} deferred)</summary>
            {preparedPlan.effect.acceptedProposals.length ? (
              <ol>
                {preparedPlan.effect.acceptedProposals.map((assertion) => (
                  <li key={assertion.assertionId}>
                    <strong>{plannedAssertionLabel(assertion)}</strong>
                    <span> · {assertion.assertionKind}</span>
                    {plannedAssertionDescription(assertion) ? <p>{plannedAssertionDescription(assertion)}</p> : null}
                    {assertion.sourceArtifactId || assertion.sourceRevisionId ? (
                      <small>Supported by {assertion.sourceArtifactId ?? preparedPlan.sourceArtifactId} · {assertion.sourceRevisionId ?? preparedPlan.sourceRevisionId}</small>
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : <p>No accepted graph effects.</p>}
            {Object.keys(preparedPlan.effect.nodeIdMap).length ? (
              <p>Identity map: {Object.entries(preparedPlan.effect.nodeIdMap).map(([candidate, node]) => `${candidate} → ${node}`).join(" · ")}</p>
            ) : null}
            {preparedPlan.effect.decisionSnapshot.length ? (
              <details>
                <summary>Decision record ({preparedPlan.effect.decisionSnapshot.length})</summary>
                <ul>{preparedPlan.effect.decisionSnapshot.map((decision) => (
                  <li key={decision.assertionId}>
                    <code>{decision.assertionId}</code> · {decision.candidateKind} · {decision.decision}
                    {decision.targetNodeId ? ` · ${decision.targetNodeId}` : ""}
                  </li>
                ))}</ul>
              </details>
            ) : null}
          </details>
          <p className="graph-review-worldbuilding-observation-review__alert">
            The server marks this plan as non-confirmable. These decisions are not published to the World Graph.
          </p>
          <button type="button" onClick={() => setPreparedPlan(null)}>Revise decisions</button>
          {preparedPlan.diagnostics.length ? (
            <details>
              <summary>Plan diagnostics ({preparedPlan.diagnostics.length})</summary>
              <ul>{preparedPlan.diagnostics.map((diagnostic) => <li key={diagnostic}>{diagnostic}</li>)}</ul>
            </details>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
