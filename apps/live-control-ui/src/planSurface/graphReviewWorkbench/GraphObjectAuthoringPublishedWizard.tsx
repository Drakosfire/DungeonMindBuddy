import { useEffect, useRef, useState } from "react";

import type {
  GraphProjectionNodeView,
  GraphReviewExistingObjectCandidate,
} from "../../api/types";
import { GraphObjectAuthoringBindExistingPanel } from "./GraphObjectAuthoringBindExistingPanel";
import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import type { GraphObjectAuthoringInspectedNode } from "./GraphObjectAuthoringObjectRefPicker";
import { GraphObjectAuthoringObjectForm } from "./GraphObjectAuthoringObjectForm";
import { GraphObjectAuthoringOverlapWarnings } from "./GraphObjectAuthoringOverlapWarnings";
import { GraphObjectAuthoringRelationshipForm } from "./GraphObjectAuthoringRelationshipForm";
import { GraphObjectAuthoringSelectedSource } from "./GraphObjectAuthoringSelectedSource";
import { GraphObjectAuthoringStagingTray } from "./GraphObjectAuthoringStagingTray";
import { GraphObjectAuthoringVisibilitySection } from "./GraphObjectAuthoringVisibilitySection";
import type {
  GraphObjectAuthoringFormState,
  GraphObjectAuthoringLinkExistingOperation,
  GraphObjectAuthoringProposal,
  GraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import { canStageRelationshipForm } from "./graphObjectAuthoringDraft";
import type { GraphObjectAuthoringOverlapContext, GraphObjectAuthoringOverlapWarning } from "./graphObjectAuthoringOverlap";

export type PublishedLocalWizardStep = "resolve" | "details" | "relationship" | "review";

export interface GraphObjectAuthoringContextTab {
  key: string;
  label: string;
  selection: GraphAuthoringSelection;
}

export interface GraphObjectAuthoringPublishedWizardProps {
  selectedSource: GraphAuthoringSelection | null;
  formState: GraphObjectAuthoringFormState;
  proposals: GraphObjectAuthoringProposal[];
  onFormFieldChange: <K extends keyof GraphObjectAuthoringFormState>(
    field: K,
    value: GraphObjectAuthoringFormState[K],
  ) => void;
  onStageProposal: () => void;
  onRemoveProposal: (localProposalId: string) => void;
  onStartManualDraft?: () => void;
  bindSearchStatus: "idle" | "loading" | "ready" | "error";
  bindSearchError: string | null;
  scopeCandidates: GraphReviewExistingObjectCandidate[];
  governedScopeCandidates: GraphReviewExistingObjectCandidate[];
  onBindExisting: (
    candidate: GraphReviewExistingObjectCandidate,
    operation: GraphObjectAuthoringLinkExistingOperation,
  ) => boolean;
  bindingAlias: boolean;
  creatingObject: boolean;
  createObjectError: string | null;
  relationshipFormState?: GraphObjectAuthoringRelationshipFormState;
  onRelationshipFieldChange?: <K extends keyof GraphObjectAuthoringRelationshipFormState>(
    field: K,
    value: GraphObjectAuthoringRelationshipFormState[K],
  ) => void;
  onStageRelationshipProposal?: () => void;
  existingNodes: GraphObjectAuthoringInspectedNode[];
  projectionNodeViews?: Record<string, GraphProjectionNodeView>;
  governedWorldNodeViews?: Record<string, GraphProjectionNodeView> | null;
  overlapContext: GraphObjectAuthoringOverlapContext;
  objectFormOverlapWarnings: GraphObjectAuthoringOverlapWarning[];
  contextTabs?: GraphObjectAuthoringContextTab[];
  onSelectContextTab?: (selection: GraphAuthoringSelection) => void;
}

const STEP_ORDER: PublishedLocalWizardStep[] = [
  "resolve",
  "details",
  "relationship",
  "review",
];

const STEP_COPY: Record<PublishedLocalWizardStep, { title: string; hint: string }> = {
  resolve: {
    title: "Resolve the recap phrase",
    hint: "Decide whether this phrase is an existing identity or a new local object.",
  },
  details: {
    title: "Add object details",
    hint: "Confirm the local object draft before moving on.",
  },
  relationship: {
    title: "Add a relationship",
    hint: "Optional: describe how this object connects to another object.",
  },
  review: {
    title: "Review local draft",
    hint: "These proposals stay local to this campaign and focus session.",
  },
};

function contextTabKey(selection: GraphAuthoringSelection | null): string {
  if (!selection || !selection.selectedText.trim()) {
    return "new";
  }
  return `node:${selection.existingNodeId ?? selection.normalizedSelectedText.toLocaleLowerCase()}`;
}

export function GraphObjectAuthoringPublishedWizard({
  selectedSource,
  formState,
  proposals,
  onFormFieldChange,
  onStageProposal,
  onRemoveProposal,
  onStartManualDraft,
  bindSearchStatus,
  bindSearchError,
  scopeCandidates,
  governedScopeCandidates,
  onBindExisting,
  bindingAlias,
  creatingObject,
  createObjectError,
  relationshipFormState,
  onRelationshipFieldChange,
  onStageRelationshipProposal,
  existingNodes,
  projectionNodeViews,
  governedWorldNodeViews,
  overlapContext,
  objectFormOverlapWarnings,
  contextTabs = [],
  onSelectContextTab,
}: GraphObjectAuthoringPublishedWizardProps) {
  const [step, setStep] = useState<PublishedLocalWizardStep>("resolve");
  const [activeContextTab, setActiveContextTab] = useState("new");
  const previousSelectionKey = useRef<string | null>(null);
  const supportsRelationship = Boolean(
    relationshipFormState && onRelationshipFieldChange && onStageRelationshipProposal,
  );
  const canStage = Boolean(selectedSource && formState.label.trim());

  useEffect(() => {
    const selectionKey = selectedSource
      ? `${selectedSource.selectedText}:${selectedSource.existingNodeId ?? ""}`
      : null;
    if (selectionKey && selectionKey !== previousSelectionKey.current) {
      setActiveContextTab(contextTabKey(selectedSource));
      setStep(selectedSource?.selectedText.trim() ? "resolve" : "details");
    }
    previousSelectionKey.current = selectionKey;
  }, [selectedSource]);

  const stepIndex = STEP_ORDER.indexOf(step);
  const stepCopy = STEP_COPY[step];
  const canStageRelationship = Boolean(
    relationshipFormState && canStageRelationshipForm(relationshipFormState),
  );

  const handleBindExisting = (
    candidate: GraphReviewExistingObjectCandidate,
    operation: GraphObjectAuthoringLinkExistingOperation,
  ) => {
    if (onBindExisting(candidate, operation)) {
      setStep("review");
    }
  };

  const handleBack = () => {
    if (step === "details") {
      if (activeContextTab === "new" && selectedSource?.selectedText.trim()) {
        setActiveContextTab(contextTabKey(selectedSource));
        setStep("resolve");
      } else {
        setStep("resolve");
      }
    } else if (step === "relationship") {
      setStep(selectedSource ? "details" : "resolve");
    } else if (step === "review") {
      setStep(supportsRelationship ? "relationship" : selectedSource ? "details" : "resolve");
    }
  };

  const handleStageObject = () => {
    onStageProposal();
    setStep("relationship");
  };

  const handleStageRelationship = () => {
    onStageRelationshipProposal?.();
    setStep("review");
  };

  const currentNodeTab = selectedSource?.selectedText.trim()
    ? {
        key: contextTabKey(selectedSource),
        label: selectedSource.existingLabel?.trim() || selectedSource.selectedText.trim(),
        selection: selectedSource,
      }
    : null;
  const visibleContextTabs = [
    ...(currentNodeTab ? [currentNodeTab] : []),
    ...contextTabs.filter((tab) => tab.key !== currentNodeTab?.key),
  ];
  const openNewObjectTab = () => {
    setActiveContextTab("new");
    setStep("details");
  };
  const openContextTab = (tab: GraphObjectAuthoringContextTab) => {
    setActiveContextTab(tab.key);
    onSelectContextTab?.(tab.selection);
    setStep("resolve");
  };

  return (
    <div
      className="graph-object-authoring-published-wizard"
      data-testid="graph-object-authoring-published-wizard"
      data-wizard-step={step}
    >
      <header className="graph-object-authoring-wizard-sticky-header">
        <ol
          className="graph-object-authoring-wizard-progress"
          aria-label="Authoring steps (status only)"
          data-step-indicator="status"
        >
          {STEP_ORDER.map((stepName, index) => (
            <li
              key={stepName}
              className={stepName === step ? "is-current" : index < stepIndex ? "is-complete" : ""}
              aria-current={stepName === step ? "step" : undefined}
              data-step-name={stepName}
              data-step-state={stepName === step ? "current" : index < stepIndex ? "complete" : "upcoming"}
              title={`Step ${index + 1}: ${STEP_COPY[stepName].title}. ${STEP_COPY[stepName].hint}`}
            >
              <span className="graph-object-authoring-wizard-progress-index" aria-hidden="true">
                {index + 1}
              </span>
              <span className="graph-object-authoring-wizard-progress-sr-label">
                Step {index + 1}: {STEP_COPY[stepName].title}
              </span>
            </li>
          ))}
        </ol>

        <nav className="graph-object-authoring-context-tabs" aria-label="Authoring contexts">
          <button
            type="button"
            className={activeContextTab === "new" ? "is-active" : ""}
            aria-current={activeContextTab === "new" ? "page" : undefined}
            data-testid="graph-object-authoring-context-tab-new"
            onClick={openNewObjectTab}
          >
            New object
          </button>
          {visibleContextTabs.map((tab, index) => (
            <button
              key={tab.key}
              type="button"
              className={activeContextTab === tab.key ? "is-active" : ""}
              aria-current={activeContextTab === tab.key ? "page" : undefined}
              data-testid={index === 0 ? "graph-object-authoring-context-tab-current" : undefined}
              onClick={() => openContextTab(tab)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <header className="graph-object-authoring-wizard-header">
        <h4>Step {stepIndex + 1} · {stepCopy.title}</h4>
      </header>

      {step === "resolve" && activeContextTab !== "new" ? (
        <section className="graph-object-authoring-wizard-step" aria-label="Resolve recap phrase">
          {selectedSource ? (
            <GraphObjectAuthoringSelectedSource selection={selectedSource} compact />
          ) : (
            <div className="graph-object-authoring-surface-empty-state">
              <p className="graph-object-authoring-surface-empty-hint">
                Highlight a recap phrase or start a local object draft.
              </p>
              {onStartManualDraft ? (
                <div className="graph-object-authoring-surface-actions">
                  <button
                    type="button"
                    data-testid="graph-object-authoring-start-manual-draft-button"
                    onClick={() => {
                      onStartManualDraft();
                      setStep("details");
                    }}
                  >
                    Create new object
                  </button>
                </div>
              ) : null}
            </div>
          )}

          {selectedSource && selectedSource.selectedText.trim() ? (
            <GraphObjectAuthoringBindExistingPanel
              selectedText={selectedSource.selectedText}
              status={bindSearchStatus}
              error={bindSearchError}
              candidates={scopeCandidates}
              onBindExisting={handleBindExisting}
              binding={bindingAlias}
              governedWorldNodeViews={governedWorldNodeViews}
              wizardMode
              onChooseCreateNew={openNewObjectTab}
            />
          ) : null}
        </section>
      ) : null}

      {step === "details" || (activeContextTab === "new" && step === "resolve") ? (
        <section className="graph-object-authoring-wizard-step" aria-label="Add object details">
          {selectedSource ? <GraphObjectAuthoringSelectedSource selection={selectedSource} compact /> : null}
          {!selectedSource && onStartManualDraft ? (
            <div className="graph-object-authoring-surface-empty-state">
              <p className="graph-object-authoring-surface-empty-hint">
                Start a local object draft when there is no recap phrase to reuse.
              </p>
              <div className="graph-object-authoring-surface-actions">
                <button
                  type="button"
                  data-testid="graph-object-authoring-start-manual-draft-button"
                  onClick={() => onStartManualDraft()}
                >
                  Start new draft
                </button>
              </div>
            </div>
          ) : null}
          <div className="graph-object-authoring-object-details">
            <GraphObjectAuthoringObjectForm formState={formState} onChange={onFormFieldChange} />
            <GraphObjectAuthoringOverlapWarnings warnings={objectFormOverlapWarnings} />
            <GraphObjectAuthoringVisibilitySection
              visibility={formState.visibility}
              onChange={(visibility) => onFormFieldChange("visibility", visibility)}
            />
            {createObjectError ? (
              <p className="graph-object-authoring-prepare-commit-error" role="alert">
                {createObjectError}
              </p>
            ) : null}
          </div>
        </section>
      ) : null}

      {step === "relationship" ? (
        <section className="graph-object-authoring-wizard-step" aria-label="Add a relationship">
          {supportsRelationship && relationshipFormState && onRelationshipFieldChange ? (
            <>
              <GraphObjectAuthoringRelationshipForm
                formState={relationshipFormState}
                onChange={onRelationshipFieldChange}
                proposals={proposals}
                existingNodes={existingNodes}
                scopeCandidates={governedScopeCandidates}
                overlapContext={overlapContext}
                compactGuidance
              />
              <GraphObjectAuthoringVisibilitySection
                visibility={relationshipFormState.visibility}
                onChange={(visibility) => onRelationshipFieldChange("visibility", visibility)}
                fieldId="graph-object-authoring-relationship-visibility"
                fieldLabel="Relationship visibility"
                sectionLabel="Relationship visibility section"
              />
            </>
          ) : (
            <p className="graph-object-authoring-surface-empty-hint">
              No relationship draft is available. Continue to review the local object draft.
            </p>
          )}
        </section>
      ) : null}

      {step === "review" ? (
        <section
          className="graph-object-authoring-review-staged-memory graph-object-authoring-wizard-step"
          aria-label="Review staged memory"
          data-testid="graph-object-authoring-review-staged-memory"
        >
          <GraphObjectAuthoringStagingTray
            proposals={proposals}
            onRemove={onRemoveProposal}
            overlapContext={overlapContext}
            projectionNodeViews={projectionNodeViews}
            emptyMessage="No local proposals yet. Go back to choose an identity or add object details."
          />
        </section>
      ) : null}

      <nav className="graph-object-authoring-wizard-nav" aria-label="Authoring step navigation">
        <button
          type="button"
          className="graph-object-authoring-secondary-action"
          data-testid="graph-object-authoring-wizard-back"
          disabled={step === "resolve"}
          onClick={handleBack}
        >
          Back
        </button>

        {step === "resolve" && activeContextTab !== "new" ? (
          <>
            <button
              type="button"
              className="graph-object-authoring-secondary-action"
              data-testid="graph-object-authoring-wizard-next"
              onClick={openNewObjectTab}
            >
              Open New object tab
            </button>
            {supportsRelationship ? (
              <button
                type="button"
                className="graph-object-authoring-secondary-action"
                data-testid="graph-object-authoring-wizard-relationship"
                onClick={() => setStep("relationship")}
              >
                Author relationship instead
              </button>
            ) : null}
          </>
        ) : null}

        {step === "resolve" && activeContextTab === "new" && !selectedSource && supportsRelationship ? (
          <button
            type="button"
            className="graph-object-authoring-secondary-action"
            data-testid="graph-object-authoring-wizard-relationship"
            onClick={() => setStep("relationship")}
          >
            Author relationship instead
          </button>
        ) : null}

        {step === "details" ? (
          <button
            type="button"
            data-testid="graph-object-authoring-stage-button"
            disabled={!canStage || creatingObject}
            onClick={handleStageObject}
          >
            {creatingObject ? "Staging…" : "Stage object & continue"}
          </button>
        ) : null}

        {step === "relationship" ? (
          <>
            <button
              type="button"
              className="graph-object-authoring-secondary-action"
              data-testid="graph-object-authoring-skip-relationship"
              onClick={() => setStep("review")}
            >
              Skip relationship
            </button>
            <button
              type="button"
              data-testid="graph-object-authoring-stage-relationship-button"
              disabled={!supportsRelationship || !canStageRelationship}
              onClick={handleStageRelationship}
            >
              Stage relationship & review
            </button>
          </>
        ) : null}

        {step === "review" ? (
          <div
            className="graph-object-authoring-wizard-final-state"
            data-testid="graph-object-authoring-wizard-final-state"
          >
            <strong>Final step</strong>
            <span>Review or remove local drafts, then close Author Node when you’re done.</span>
          </div>
        ) : null}
      </nav>
    </div>
  );
}
