import {
  GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS,
  type GraphObjectAuthoringVisibility,
} from "./graphObjectAuthoringDraft";

export function GraphObjectAuthoringVisibilitySection({
  visibility,
  onChange,
  fieldId = "graph-object-authoring-visibility",
  fieldLabel = "Visibility",
  sectionLabel = "Object visibility",
}: {
  visibility: GraphObjectAuthoringVisibility;
  onChange: (visibility: GraphObjectAuthoringVisibility) => void;
  fieldId?: string;
  fieldLabel?: string;
  sectionLabel?: string;
}) {
  const selectedOption = GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS.find(
    (option) => option.value === visibility,
  );

  return (
    <section className="graph-object-authoring-visibility-section" aria-label={sectionLabel}>
      <div className="graph-object-authoring-field">
        <label htmlFor={fieldId}>{fieldLabel}</label>
        <select
          id={fieldId}
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
