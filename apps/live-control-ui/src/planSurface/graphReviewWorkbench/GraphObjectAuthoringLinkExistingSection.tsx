import {
  GRAPH_OBJECT_AUTHORING_LINK_EXISTING_OPERATION_OPTIONS,
  type GraphObjectAuthoringLinkExistingFormState,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";
import {
  GraphObjectAuthoringObjectRefPicker,
  type GraphObjectAuthoringInspectedNode,
} from "./GraphObjectAuthoringObjectRefPicker";
import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import type { GraphObjectAuthoringOverlapContext } from "./graphObjectAuthoringOverlap";

export function GraphObjectAuthoringLinkExistingSection({
  selectedText,
  formState,
  onChange,
  proposals,
  existingNodes = [],
  scopeCandidates = [],
  overlapContext,
}: {
  selectedText: string;
  formState: GraphObjectAuthoringLinkExistingFormState;
  onChange: <K extends keyof GraphObjectAuthoringLinkExistingFormState>(
    field: K,
    value: GraphObjectAuthoringLinkExistingFormState[K],
  ) => void;
  proposals: GraphObjectAuthoringProposal[];
  existingNodes?: GraphObjectAuthoringInspectedNode[];
  scopeCandidates?: GraphReviewExistingObjectCandidate[];
  overlapContext?: GraphObjectAuthoringOverlapContext;
}) {
  return (
    <section className="graph-object-authoring-link-existing-section" aria-label="Link to existing object">
      <p className="graph-object-authoring-link-existing-lede">
        Treat “{selectedText}” as an alias or reference for an existing graph
        object. This is a local proposal, not an identity merge, and nothing
        is written yet.
      </p>
      <GraphObjectAuthoringObjectRefPicker
        label="Existing object"
        value={formState.existingObjectRef}
        onChange={(ref) => onChange("existingObjectRef", ref)}
        proposals={proposals}
        existingNodes={existingNodes}
        scopeCandidates={scopeCandidates}
        overlapContext={overlapContext}
      />
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-link-existing-operation">Operation</label>
        <select
          id="graph-object-authoring-link-existing-operation"
          value={formState.operation}
          onChange={(event) =>
            onChange(
              "operation",
              event.target.value as GraphObjectAuthoringLinkExistingFormState["operation"],
            )
          }
        >
          {GRAPH_OBJECT_AUTHORING_LINK_EXISTING_OPERATION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-link-existing-alias-text">
          Alias text <span className="graph-object-authoring-optional">optional</span>
        </label>
        <input
          id="graph-object-authoring-link-existing-alias-text"
          type="text"
          placeholder={selectedText}
          value={formState.aliasText}
          onChange={(event) => onChange("aliasText", event.target.value)}
        />
      </div>
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-link-existing-operator-note">
          Operator note <span className="graph-object-authoring-optional">optional</span>
        </label>
        <textarea
          id="graph-object-authoring-link-existing-operator-note"
          rows={2}
          value={formState.operatorNote}
          onChange={(event) => onChange("operatorNote", event.target.value)}
        />
      </div>
    </section>
  );
}
