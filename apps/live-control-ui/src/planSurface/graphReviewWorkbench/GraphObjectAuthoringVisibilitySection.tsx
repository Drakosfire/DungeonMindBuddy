import {
  GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS,
  type GraphObjectAuthoringVisibility,
} from "./graphObjectAuthoringDraft";

export function GraphObjectAuthoringVisibilitySection({
  visibility,
  onChange,
}: {
  visibility: GraphObjectAuthoringVisibility;
  onChange: (visibility: GraphObjectAuthoringVisibility) => void;
}) {
  const selectedOption = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.find(
    (option) => option.value === visibility,
  );

  return (
    <section className="graph-object-authoring-visibility-section" aria-label="Object visibility">
      <div className="graph-object-authoring-field">
        <label htmlFor="graph-object-authoring-visibility">Visibility</label>
        <select
          id="graph-object-authoring-visibility"
          value={visibility}
          onChange={(event) =>
            onChange(event.target.value as GraphObjectAuthoringVisibility)
          }
        >
          {GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {selectedOption?.note ? (
        <p className="graph-object-authoring-visibility-note">{selectedOption.note}</p>
      ) : null}
    </section>
  );
}
