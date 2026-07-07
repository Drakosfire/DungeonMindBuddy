import {
  GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS,
  areSameObjectRef,
  isIdentityLikeRelationshipPredicate,
  isKnownRelationshipType,
  relationshipPreviewCopy,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipDirection,
  type GraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import {
  GraphObjectAuthoringObjectRefPicker,
  type GraphObjectAuthoringInspectedNode,
} from "./GraphObjectAuthoringObjectRefPicker";
import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import type { GraphObjectAuthoringOverlapContext } from "./graphObjectAuthoringOverlap";

const CUSTOM_RELATIONSHIP_TYPE_VALUE = "__custom__";

const IDENTITY_PREDICATE_WARNING =
  'This looks like an identity/linking relationship. Use "Link existing" for aliases or duplicate objects; use Relationship for campaign facts like threatens, protects, owns, or travels with.';

const SAME_OBJECT_WARNING =
  "Source and target are the same object. Choose two different objects, or use Link existing if you are trying to connect an alias.";

function relationshipTypeSelectValue(relationshipType: string): string {
  return isKnownRelationshipType(relationshipType)
    ? relationshipType
    : CUSTOM_RELATIONSHIP_TYPE_VALUE;
}

export function GraphObjectAuthoringRelationshipForm({
  formState,
  onChange,
  proposals,
  existingNodes = [],
  scopeCandidates = [],
  overlapContext,
}: {
  formState: GraphObjectAuthoringRelationshipFormState;
  onChange: <K extends keyof GraphObjectAuthoringRelationshipFormState>(
    field: K,
    value: GraphObjectAuthoringRelationshipFormState[K],
  ) => void;
  proposals: GraphObjectAuthoringProposal[];
  existingNodes?: GraphObjectAuthoringInspectedNode[];
  scopeCandidates?: GraphReviewExistingObjectCandidate[];
  overlapContext?: GraphObjectAuthoringOverlapContext;
}) {
  const relationshipTypeSelect = relationshipTypeSelectValue(formState.relationshipType);
  const usingCustomRelationshipType = relationshipTypeSelect === CUSTOM_RELATIONSHIP_TYPE_VALUE;
  const selectedRelationshipOption = GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS.find(
    (option) => option.value === formState.relationshipType,
  );
  const previewSentence = relationshipPreviewCopy(formState);
  const sameObjectSelected = areSameObjectRef(
    formState.sourceObjectRef,
    formState.targetObjectRef,
  );
  const identityLikePredicate =
    usingCustomRelationshipType &&
    isIdentityLikeRelationshipPredicate(formState.relationshipType);

  return (
    <section className="graph-object-authoring-relationship-form" aria-label="Stage a relationship">
      <p className="graph-object-authoring-relationship-lede">
        Stage a relationship between two objects. This does not require a
        current text selection. Nothing is written until a later authoring
        step.
      </p>
      <GraphObjectAuthoringObjectRefPicker
        label="Source object"
        value={formState.sourceObjectRef}
        onChange={(ref) => onChange("sourceObjectRef", ref)}
        proposals={proposals}
        existingNodes={existingNodes}
        scopeCandidates={scopeCandidates}
        overlapContext={overlapContext}
      />
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-relationship-type">Relationship type</label>
        <select
          id="graph-object-authoring-relationship-type"
          value={relationshipTypeSelect}
          onChange={(event) => {
            const nextValue = event.target.value;
            if (nextValue === CUSTOM_RELATIONSHIP_TYPE_VALUE) {
              if (isKnownRelationshipType(formState.relationshipType)) {
                onChange("relationshipType", "");
              }
              return;
            }
            onChange("relationshipType", nextValue);
          }}
        >
          {GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
          <option value={CUSTOM_RELATIONSHIP_TYPE_VALUE}>Custom…</option>
        </select>
        {selectedRelationshipOption ? (
          <p className="graph-object-authoring-relationship-type-note">
            {selectedRelationshipOption.note} Example: {selectedRelationshipOption.example}
          </p>
        ) : null}
        {usingCustomRelationshipType ? (
          <input
            id="graph-object-authoring-relationship-type-custom"
            type="text"
            aria-label="Custom relationship type"
            placeholder="Type a custom campaign predicate, e.g. owes_debt_to"
            value={formState.relationshipType}
            onChange={(event) => onChange("relationshipType", event.target.value)}
          />
        ) : null}
        {identityLikePredicate ? (
          <p
            className="graph-object-authoring-relationship-warning"
            role="status"
            data-testid="graph-object-authoring-identity-predicate-warning"
          >
            {IDENTITY_PREDICATE_WARNING}
          </p>
        ) : null}
      </div>
      <GraphObjectAuthoringObjectRefPicker
        label="Target object"
        value={formState.targetObjectRef}
        onChange={(ref) => onChange("targetObjectRef", ref)}
        proposals={proposals}
        existingNodes={existingNodes}
        scopeCandidates={scopeCandidates}
        overlapContext={overlapContext}
      />
      <p
        className="graph-object-authoring-relationship-preview"
        aria-live="polite"
        data-testid="graph-object-authoring-relationship-preview"
      >
        Preview: {previewSentence}
      </p>
      {sameObjectSelected ? (
        <p
          className="graph-object-authoring-relationship-warning"
          role="status"
          data-testid="graph-object-authoring-same-object-warning"
        >
          {SAME_OBJECT_WARNING}
        </p>
      ) : null}
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-relationship-direction">Direction</label>
        <select
          id="graph-object-authoring-relationship-direction"
          value={formState.direction}
          onChange={(event) =>
            onChange("direction", event.target.value as GraphObjectAuthoringRelationshipDirection)
          }
        >
          <option value="directed">Directed (source → target)</option>
          <option value="undirected">Undirected</option>
        </select>
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-relationship-label">
          Label <span className="graph-object-authoring-optional">optional</span>
        </label>
        <input
          id="graph-object-authoring-relationship-label"
          type="text"
          value={formState.relationshipLabel}
          onChange={(event) => onChange("relationshipLabel", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-relationship-summary">
          Summary <span className="graph-object-authoring-optional">optional</span>
        </label>
        <textarea
          id="graph-object-authoring-relationship-summary"
          rows={2}
          value={formState.summary}
          onChange={(event) => onChange("summary", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-relationship-operator-note">
          Operator note <span className="graph-object-authoring-optional">optional</span>
        </label>
        <textarea
          id="graph-object-authoring-relationship-operator-note"
          rows={2}
          value={formState.operatorNote}
          onChange={(event) => onChange("operatorNote", event.target.value)}
        />
      </div>
    </section>
  );
}
