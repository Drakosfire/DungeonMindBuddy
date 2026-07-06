import {
  GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipDirection,
  type GraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import {
  GraphObjectAuthoringObjectRefPicker,
  type GraphObjectAuthoringInspectedNode,
} from "./GraphObjectAuthoringObjectRefPicker";

export function GraphObjectAuthoringRelationshipForm({
  formState,
  onChange,
  proposals,
  existingNodes = [],
}: {
  formState: GraphObjectAuthoringRelationshipFormState;
  onChange: <K extends keyof GraphObjectAuthoringRelationshipFormState>(
    field: K,
    value: GraphObjectAuthoringRelationshipFormState[K],
  ) => void;
  proposals: GraphObjectAuthoringProposal[];
  existingNodes?: GraphObjectAuthoringInspectedNode[];
}) {
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
      />
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-relationship-type">Relationship type</label>
        <select
          id="graph-object-authoring-relationship-type"
          value={formState.relationshipType}
          onChange={(event) => onChange("relationshipType", event.target.value)}
        >
          {GRAPH_OBJECT_AUTHORING_RELATIONSHIP_TYPE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
      <GraphObjectAuthoringObjectRefPicker
        label="Target object"
        value={formState.targetObjectRef}
        onChange={(ref) => onChange("targetObjectRef", ref)}
        proposals={proposals}
        existingNodes={existingNodes}
      />
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
